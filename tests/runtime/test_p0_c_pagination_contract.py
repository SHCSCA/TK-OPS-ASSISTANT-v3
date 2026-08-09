from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from fastapi import FastAPI
from starlette.requests import Request

from api.dependencies.pagination import (
    PAGINATION_CURSOR_MAX_LENGTH,
    PaginationParams,
    get_pagination,
    parse_pagination,
)
from api.routes.v1.accounts import _normalize_account_query
from common.pagination import CursorPosition, PaginationCursorCodec
from errors import DomainError, ErrorCode
from services.config import ConfigBusService, ConfigBusSnapshot
from services.config.schema import (
    DEFAULT_VALUES,
    WRITABLE_RULES,
    validate_config_relationships,
)


class _SnapshotConfigBus(ConfigBusService):
    def __init__(self, snapshot: ConfigBusSnapshot) -> None:
        self._snapshot = snapshot
        self.prefixes: list[str | None] = []

    def get(self, *, prefix: str | None = None) -> ConfigBusSnapshot:
        self.prefixes.append(prefix)
        return self._snapshot


class _NoWriteConfigRepository:
    def load(self) -> None:
        return None

    def save_if_revision(self, *_args: object, **_kwargs: object) -> object:
        raise AssertionError("非法分页关系不应进入配置保存")


def test_pagination_defaults_are_owned_by_config_schema() -> None:
    assert DEFAULT_VALUES["api.paginationDefaultLimit"] == 50
    assert DEFAULT_VALUES["api.paginationMaxLimit"] == 200
    assert DEFAULT_VALUES["api.mutationIdempotencyTtlSeconds"] == 604_800
    assert WRITABLE_RULES["api.paginationDefaultLimit"].validator(50)
    assert WRITABLE_RULES["api.paginationMaxLimit"].validator(200)
    assert WRITABLE_RULES["api.mutationIdempotencyTtlSeconds"].validator(
        604_800
    )
    assert validate_config_relationships(DEFAULT_VALUES) == []


def test_relationship_validator_preserves_timeout_contract() -> None:
    errors = validate_config_relationships(
        {
            "runtime.taskTimeoutSeconds": 20,
            "runtime.taskMaxTimeoutSeconds": 10,
        }
    )

    assert [item.to_dict() for item in errors] == [
        {
            "field": "values.runtime.taskMaxTimeoutSeconds",
            "code": "invalid_relationship",
            "message": "任务最大超时不得小于默认任务超时",
        }
    ]


def test_relationship_validator_rejects_invalid_pagination_pair() -> None:
    errors = validate_config_relationships(
        {
            "api.paginationDefaultLimit": 201,
            "api.paginationMaxLimit": 200,
        }
    )

    assert [item.to_dict() for item in errors] == [
        {
            "field": "values.api.paginationMaxLimit",
            "code": "invalid_relationship",
            "message": "API 最大分页条数不得小于默认分页条数",
        }
    ]


def test_config_bus_update_uses_schema_relationship_validator() -> None:
    service = ConfigBusService(_NoWriteConfigRepository())

    with pytest.raises(DomainError) as captured:
        service.update(
            {"api.paginationDefaultLimit": 201},
            expected_revision=0,
            request_id="req_pagination_relationship",
            operation_id="op_pagination_relationship",
        )

    assert captured.value.error_code == ErrorCode.REQUEST_VALIDATION_FAILED.value
    assert captured.value.status_code == 422
    assert captured.value.field_errors[0].to_dict() == {
        "field": "values.api.paginationMaxLimit",
        "code": "invalid_relationship",
        "message": "API 最大分页条数不得小于默认分页条数",
    }


def test_parse_pagination_uses_default_and_preserves_opaque_cursor() -> None:
    params = parse_pagination(
        _snapshot(),
        cursor="opaque.cursor.payload",
    )

    assert params == PaginationParams(
        cursor="opaque.cursor.payload",
        limit=50,
    )
    with pytest.raises(FrozenInstanceError):
        setattr(params, "limit", 99)


def test_parse_pagination_accepts_limit_within_configured_maximum() -> None:
    params = parse_pagination(_snapshot(), limit=125)

    assert params.limit == 125
    assert params.cursor is None


def test_cursor_codec_round_trips_bound_position() -> None:
    codec = PaginationCursorCodec()
    filters = {"kind": "document", "status": "ready"}
    position = CursorPosition(
        sort_value="2026-07-26T10:20:30Z",
        resource_id="source_01",
    )

    cursor = codec.encode(
        position,
        scope="account_01",
        resource_kind="knowledge.sources",
        filter_fingerprint=codec.fingerprint(filters),
    )

    assert codec.decode(
        cursor,
        scope="account_01",
        resource_kind="knowledge.sources",
        filter_fingerprint=codec.fingerprint(filters),
    ) == position


@pytest.mark.parametrize(
    ("raw_query", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("  creator  ", "creator"),
        ("creator", "creator"),
    ],
)
def test_account_query_filter_is_normalized_before_cursor_binding(
    raw_query: str | None,
    expected: str | None,
) -> None:
    assert _normalize_account_query(raw_query) == expected


@pytest.mark.parametrize(
    ("scope", "filters"),
    [
        ("account_02", {"kind": "document", "status": "ready"}),
        ("account_01", {"kind": "video", "status": "ready"}),
    ],
)
def test_pagination_params_rejects_cross_scope_or_filter_cursor(
    scope: str,
    filters: dict[str, str],
) -> None:
    codec = PaginationCursorCodec()
    original_filters = {"kind": "document", "status": "ready"}
    cursor = codec.encode(
        CursorPosition(
            sort_value="2026-07-26T10:20:30Z",
            resource_id="source_01",
        ),
        scope="account_01",
        resource_kind="knowledge.sources",
        filter_fingerprint=codec.fingerprint(original_filters),
    )
    params = PaginationParams(cursor=cursor, limit=50, codec=codec)

    with pytest.raises(DomainError) as captured:
        params.decode_cursor(
            scope=scope,
            resource_kind="knowledge.sources",
            filters=filters,
        )

    assert captured.value.error_code == ErrorCode.REQUEST_VALIDATION_FAILED.value
    assert captured.value.status_code == 422
    assert captured.value.field_errors[0].to_dict() == {
        "field": "cursor",
        "code": "invalid_scoped_cursor",
        "message": "请重新从当前资源与筛选条件的第一页加载",
    }


def test_parse_pagination_rejects_limit_above_configured_maximum() -> None:
    with pytest.raises(DomainError) as captured:
        parse_pagination(_snapshot(), limit=201)

    assert captured.value.error_code == ErrorCode.REQUEST_VALIDATION_FAILED.value
    assert captured.value.status_code == 422
    assert [item.to_dict() for item in captured.value.field_errors] == [
        {
            "field": "limit",
            "code": "limit_exceeded",
            "message": "分页条数不能超过配置上限 200",
        }
    ]


@pytest.mark.parametrize(
    "cursor",
    [
        "",
        " ",
        " cursor",
        "cursor ",
        "x" * (PAGINATION_CURSOR_MAX_LENGTH + 1),
    ],
)
def test_parse_pagination_rejects_invalid_cursor_boundary(cursor: str) -> None:
    with pytest.raises(DomainError) as captured:
        parse_pagination(_snapshot(), cursor=cursor)

    assert captured.value.error_code == ErrorCode.REQUEST_VALIDATION_FAILED.value
    assert captured.value.field_errors[0].field == "cursor"
    assert captured.value.field_errors[0].code == "invalid_cursor"


def test_parse_pagination_rejects_invalid_config_snapshot() -> None:
    with pytest.raises(DomainError) as captured:
        parse_pagination(_snapshot(default_limit=300, maximum_limit=200))

    assert captured.value.error_code == ErrorCode.INTERNAL_ERROR.value
    assert captured.value.status_code == 500
    assert captured.value.loggable is True


def test_fastapi_dependency_reads_current_config_snapshot() -> None:
    app = FastAPI()
    config_bus = _SnapshotConfigBus(_snapshot(default_limit=75))
    app.state.config_bus_service = config_bus
    request = Request({"type": "http", "app": app})

    params = get_pagination(request, cursor="cursor.v1", limit=None)

    assert params == PaginationParams(cursor="cursor.v1", limit=75)
    assert config_bus.prefixes == ["api.pagination"]


def _snapshot(
    *,
    default_limit: int = 50,
    maximum_limit: int = 200,
) -> ConfigBusSnapshot:
    return ConfigBusSnapshot(
        values={
            "api.paginationDefaultLimit": default_limit,
            "api.paginationMaxLimit": maximum_limit,
        },
        writable_keys=(),
        restart_required_keys=(),
        revision=1,
    )
