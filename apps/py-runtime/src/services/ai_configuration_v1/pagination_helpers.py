from __future__ import annotations

from collections.abc import Callable

from common.pagination import CursorPosition
from domain.models.ai_configuration_v1 import (
    CapabilityRoute,
    ModelProfile,
    ProviderProfile,
)
from errors import DomainError, ErrorCode


def provider_page(
    rows: tuple[ProviderProfile, ...],
    cursor: CursorPosition | None,
    limit: int,
) -> tuple[tuple[ProviderProfile, ...], CursorPosition | None]:
    start = 0
    if cursor is not None:
        for index, row in enumerate(rows):
            if (
                row.id == cursor.resource_id
                and row.updated_at == cursor.sort_value
            ):
                start = index + 1
                break
        else:
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "Provider 分页游标已失效，请重新加载",
                status_code=422,
            )
    page = rows[start : start + limit]
    has_more = start + limit < len(rows)
    next_position = (
        CursorPosition(
            sort_value=page[-1].updated_at,
            resource_id=page[-1].id,
        )
        if has_more and page
        else None
    )
    return tuple(page), next_position


def model_page(
    rows: tuple[ModelProfile, ...],
    cursor: CursorPosition | None,
    limit: int,
) -> tuple[tuple[ModelProfile, ...], CursorPosition | None]:
    start = _model_row_start(rows, cursor, lambda row: row.updated_at)
    page = rows[start : start + limit]
    has_more = start + limit < len(rows)
    return (
        tuple(page),
        CursorPosition(
            sort_value=page[-1].updated_at,
            resource_id=page[-1].id,
        )
        if has_more and page
        else None,
    )


def model_capability_page(
    rows: tuple[dict[str, object], ...],
    cursor: CursorPosition | None,
    limit: int,
) -> tuple[tuple[dict[str, object], ...], CursorPosition | None]:
    start = 0
    if cursor is not None:
        for index, row in enumerate(rows):
            if (
                row.get("modelProfileId") == cursor.resource_id
                and row.get("capabilityKey") == cursor.sort_value
            ):
                start = index + 1
                break
        else:
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "模型能力分页游标已失效，请重新加载",
                status_code=422,
            )
    page = rows[start : start + limit]
    has_more = start + limit < len(rows)
    last_id = page[-1].get("modelProfileId") if page else None
    return (
        tuple(page),
        CursorPosition(
            sort_value=str(page[-1].get("capabilityKey")),
            resource_id=str(last_id),
        )
        if has_more and page and isinstance(last_id, str)
        else None,
    )


def route_cursor_start(
    rows: tuple[CapabilityRoute, ...],
    cursor: CursorPosition | None,
) -> int:
    if cursor is None:
        return 0
    for index, row in enumerate(rows):
        if (
            row.id == cursor.resource_id
            and row.capability_key == cursor.sort_value
        ):
            return index + 1
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "能力路由分页游标已失效，请重新加载",
        status_code=422,
    )


def _model_row_start(
    rows: tuple[ModelProfile, ...],
    cursor: CursorPosition | None,
    sort_value: Callable[[ModelProfile], str],
) -> int:
    if cursor is None:
        return 0
    for index, row in enumerate(rows):
        if (
            row.id == cursor.resource_id
            and sort_value(row) == cursor.sort_value
        ):
            return index + 1
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "模型分页游标已失效，请重新加载",
        status_code=422,
    )
