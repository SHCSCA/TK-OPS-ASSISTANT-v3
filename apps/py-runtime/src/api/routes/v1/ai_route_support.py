from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Annotated, TypeVar, cast

from fastapi import Path, Request
from pydantic import BaseModel, ValidationError

from api.dependencies.pagination import PaginationParams
from api.dependencies.request_context import RequestContext
from common.identifiers import STABLE_ID_PATTERN_TEXT
from common.pagination import CursorPosition
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.envelope import ok_response
from schemas.v1.tasks import TaskAcceptedDto
from services.tasks.types import RuntimeTaskRecord

OutputModelT = TypeVar("OutputModelT", bound=BaseModel)
StablePathId = Annotated[
    str,
    Path(
        min_length=1,
        max_length=128,
        pattern=STABLE_ID_PATTERN_TEXT,
    ),
]
PositiveVersionPath = Annotated[int, Path(ge=1)]


def resolve_ai_service(request: Request, service_name: str) -> object:
    for state_name in (
        "ai_configuration",
        "ai_configuration_service",
        "ai_configuration_v1_service",
    ):
        direct_bundle = getattr(request.app.state, state_name, None)
        service = getattr(direct_bundle, service_name, None)
        if service is not None:
            return service

    container = getattr(request.app.state, "runtime_container", None)
    services = getattr(container, "services", None)
    bundle = getattr(services, "ai_configuration", None)
    service = getattr(bundle, service_name, None)
    if service is not None:
        return service

    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "AI 配置服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={
            "operation": "ai.configuration.route.resolve_service",
            "service": service_name,
        },
    )


def require_idempotency_key(context: RequestContext) -> str:
    if context.idempotency_key is not None:
        return context.idempotency_key
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "写操作必须提供 Idempotency-Key",
        status_code=422,
        field_errors=[
            FieldError(
                field="Idempotency-Key",
                code="required",
                message="必须提供幂等键",
            )
        ],
    )


def payload_dict(payload: BaseModel) -> dict[str, object]:
    return cast(
        dict[str, object],
        payload.model_dump(
            mode="json",
            by_alias=True,
            exclude_unset=True,
        ),
    )


def read_response(
    result: object,
    dto_type: type[OutputModelT],
) -> dict[str, object]:
    data, _ = _unpack_result(result)
    dto = _validate_dto(data, dto_type)
    return ok_response(dto.model_dump(mode="json", by_alias=True))


def mutation_response(
    result: object,
    dto_type: type[OutputModelT],
    *,
    invalidations: Sequence[str],
) -> dict[str, object]:
    data, service_meta = _unpack_result(result)
    dto = _validate_dto(data, dto_type)
    meta = _merge_meta(
        service_meta,
        invalidations=invalidations,
        data=dto,
    )
    return ok_response(
        dto.model_dump(mode="json", by_alias=True),
        meta=meta,
    )


def page_response(
    result: object,
    dto_type: type[OutputModelT],
    *,
    pagination: PaginationParams,
    scope: str,
    resource_kind: str,
    filters: Mapping[str, object],
) -> dict[str, object]:
    page_data, next_position = _unpack_page(result)
    dto = _validate_dto(page_data, dto_type)
    next_cursor = _encode_next_cursor(
        next_position,
        pagination=pagination,
        scope=scope,
        resource_kind=resource_kind,
        filters=filters,
    )
    return ok_response(
        dto.model_dump(mode="json", by_alias=True),
        meta={"nextCursor": next_cursor},
    )


def list_response(
    result: object,
    item_type: type[OutputModelT],
) -> dict[str, object]:
    data, _ = _unpack_result(result)
    if not isinstance(data, Sequence) or isinstance(
        data,
        (str, bytes),
    ):
        raise _invalid_service_output()
    validated = [_validate_dto(item, item_type) for item in data]
    return ok_response(
        [
            item.model_dump(mode="json", by_alias=True)
            for item in validated
        ]
    )


def task_accepted_response(
    result: object,
    *,
    invalidations: Sequence[str],
) -> dict[str, object]:
    data, service_meta = _unpack_result(result)
    dto = _task_accepted_dto(data)
    meta = _merge_meta(
        service_meta,
        invalidations=invalidations,
        data=dto,
    )
    return ok_response(dto.model_dump(mode="json"), meta=meta)


def _validate_dto(
    value: object,
    dto_type: type[OutputModelT],
) -> OutputModelT:
    if isinstance(value, dto_type):
        return value
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", by_alias=True)
    elif not isinstance(value, Mapping):
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            value = to_dict()
    try:
        return dto_type.model_validate(value, from_attributes=True)
    except ValidationError as exc:
        raise _invalid_service_output() from exc


def _unpack_result(
    result: object,
) -> tuple[object, Mapping[str, object] | None]:
    if isinstance(result, Mapping):
        data = result.get("data")
        meta = result.get("meta")
        if data is not None and (meta is None or isinstance(meta, Mapping)):
            return data, cast(Mapping[str, object] | None, meta)
        return result, None

    data = getattr(result, "data", None)
    meta = getattr(result, "meta", None)
    if data is not None and (meta is None or isinstance(meta, Mapping)):
        derived_meta = dict(cast(Mapping[str, object], meta or {}))
        revision = getattr(result, "revision", None)
        if isinstance(revision, int) and not isinstance(revision, bool):
            derived_meta.setdefault("revision", revision)
        result_invalidations = getattr(result, "invalidations", None)
        if (
            isinstance(result_invalidations, Sequence)
            and not isinstance(result_invalidations, (str, bytes))
        ):
            derived_meta.setdefault(
                "invalidations",
                [
                    item
                    for item in result_invalidations
                    if isinstance(item, str)
                ],
            )
        return data, derived_meta or None
    return result, None


def _unpack_page(result: object) -> tuple[object, object | None]:
    if isinstance(result, tuple) and len(result) == 2:
        return result[0], result[1]
    data, meta = _unpack_result(result)
    if meta is None:
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "AI 配置分页结果结构异常，请查看诊断日志",
            status_code=500,
            loggable=True,
        )
    return data, meta.get("nextCursor")


def _encode_next_cursor(
    value: object | None,
    *,
    pagination: PaginationParams,
    scope: str,
    resource_kind: str,
    filters: Mapping[str, object],
) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, CursorPosition):
        return pagination.encode_cursor(
            value,
            scope=scope,
            resource_kind=resource_kind,
            filters=filters,
        )
    raise DomainError(
        ErrorCode.INTERNAL_ERROR,
        "AI 配置分页游标结构异常，请查看诊断日志",
        status_code=500,
        loggable=True,
    )


def _task_accepted_dto(value: object) -> TaskAcceptedDto:
    try:
        if isinstance(value, TaskAcceptedDto):
            return value
        if isinstance(value, RuntimeTaskRecord):
            return TaskAcceptedDto.from_record(value)
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json", by_alias=True)
        elif not isinstance(value, Mapping):
            to_dict = getattr(value, "to_dict", None)
            if callable(to_dict):
                value = to_dict()

        if not isinstance(value, Mapping):
            return TaskAcceptedDto.model_validate(
                value,
                from_attributes=True,
            )
        normalized = {
            "taskId": value.get("taskId", value.get("id")),
            "scope": _enum_value(value.get("scope")),
            "accountId": value.get(
                "accountId",
                value.get("account_id"),
            ),
            "taskType": value.get("taskType", value.get("task_type")),
            "status": _enum_value(value.get("status", "queued")),
            "cancellable": value.get("cancellable"),
            "createdAt": value.get(
                "createdAt",
                value.get("created_at"),
            ),
        }
        return TaskAcceptedDto.model_validate(normalized)
    except ValidationError as exc:
        raise _invalid_service_output() from exc


def _merge_meta(
    service_meta: Mapping[str, object] | None,
    *,
    invalidations: Sequence[str],
    data: BaseModel,
) -> dict[str, object]:
    meta = dict(service_meta or {})
    service_invalidations = meta.get("invalidations")
    merged_invalidations: list[str] = []
    if isinstance(service_invalidations, Sequence) and not isinstance(
        service_invalidations,
        (str, bytes),
    ):
        merged_invalidations.extend(
            item
            for item in service_invalidations
            if isinstance(item, str)
        )
    for item in invalidations:
        if item not in merged_invalidations:
            merged_invalidations.append(item)
    meta["invalidations"] = merged_invalidations

    if "revision" not in meta:
        revision = getattr(data, "revision", None)
        if revision is None:
            revision = getattr(data, "providerRevision", None)
        if isinstance(revision, int):
            meta["revision"] = revision
    return meta


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _invalid_service_output() -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        "AI 配置服务返回结构异常，请查看诊断日志",
        status_code=500,
        loggable=True,
    )


__all__ = [
    "PositiveVersionPath",
    "StablePathId",
    "list_response",
    "mutation_response",
    "page_response",
    "payload_dict",
    "read_response",
    "require_idempotency_key",
    "resolve_ai_service",
    "task_accepted_response",
]
