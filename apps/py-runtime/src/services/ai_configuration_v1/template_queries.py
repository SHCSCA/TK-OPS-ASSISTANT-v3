from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime

from common.pagination import CursorPosition
from domain.models.ai_configuration_v1 import CompositionTemplateProfile
from errors import DomainError, ErrorCode

from .dto import template_summary_to_dto, template_version_to_dto
from .events import append_system_ai_event
from .template_validation import _template_validation
from .unit_of_work import AIConfigurationTransaction

def _group_template_rows(
    rows: tuple[CompositionTemplateProfile, ...],
    *,
    status: str | None,
) -> tuple[
    tuple[str, tuple[CompositionTemplateProfile, ...]],
    ...,
]:
    grouped: dict[str, list[CompositionTemplateProfile]] = defaultdict(list)
    for row in rows:
        grouped[row.template_key].append(row)
    return tuple(
        (key, tuple(grouped[key]))
        for key in sorted(grouped)
        if status is None
        or any(row.status == status for row in grouped[key])
    )


def _template_summary(
    transaction: AIConfigurationTransaction,
    rows: tuple[CompositionTemplateProfile, ...],
) -> dict[str, object]:
    return template_summary_to_dto(
        rows,
        reference_count=sum(
            transaction.ai.recipes.count_template_references(
                transaction.session,
                row.id,
            )
            for row in rows
        ),
    )


def _require_template_versions(
    transaction: AIConfigurationTransaction,
    template_key: str,
) -> tuple[CompositionTemplateProfile, ...]:
    rows = transaction.ai.templates.list_versions(
        transaction.session,
        template_key,
    )
    if not rows:
        raise DomainError(
            ErrorCode.COMPOSITION_TEMPLATE_NOT_FOUND,
            "合成模板不存在",
            status_code=404,
        )
    return rows


def _require_template_version(
    transaction: AIConfigurationTransaction,
    template_key: str,
    version: int,
) -> CompositionTemplateProfile:
    row = transaction.ai.templates.get(
        transaction.session,
        template_key=template_key,
        version=version,
    )
    if row is None:
        raise DomainError(
            ErrorCode.COMPOSITION_TEMPLATE_VERSION_NOT_FOUND,
            "合成模板版本不存在",
            status_code=404,
        )
    return row


def _load_template_summary_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
) -> Mapping[str, object]:
    if resource_type != "composition_template":
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "合成模板幂等记录资源类型异常",
            status_code=500,
            loggable=True,
        )
    row = transaction.ai.templates.get_by_id(
        transaction.session,
        resource_id,
    )
    if row is None:
        raise DomainError(
            ErrorCode.COMPOSITION_TEMPLATE_NOT_FOUND,
            "合成模板幂等资源已不存在",
            status_code=404,
        )
    return _template_summary(
        transaction,
        _require_template_versions(transaction, row.template_key),
    )


def _load_template_version_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
) -> Mapping[str, object]:
    if resource_type != "composition_template_version":
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "合成模板版本幂等记录资源类型异常",
            status_code=500,
            loggable=True,
        )
    row = transaction.ai.templates.get_by_id(
        transaction.session,
        resource_id,
    )
    if row is None:
        raise DomainError(
            ErrorCode.COMPOSITION_TEMPLATE_VERSION_NOT_FOUND,
            "合成模板幂等版本已不存在",
            status_code=404,
        )
    return template_version_to_dto(row)


def _load_template_validation_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
) -> Mapping[str, object]:
    if resource_type != "composition_template_validation":
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "合成模板校验幂等记录资源类型异常",
            status_code=500,
            loggable=True,
        )
    row = transaction.ai.templates.get_by_id(
        transaction.session,
        resource_id,
    )
    if row is None:
        raise DomainError(
            ErrorCode.COMPOSITION_TEMPLATE_VERSION_NOT_FOUND,
            "合成模板校验版本已不存在",
            status_code=404,
        )
    return _template_validation(transaction, row)


def _append_template_event(
    transaction: AIConfigurationTransaction,
    *,
    row: CompositionTemplateProfile,
    event_type: str,
    ai_revision: int,
    invalidations: tuple[str, ...],
) -> None:
    append_system_ai_event(
        transaction,
        event_type=event_type,
        resource_type="composition_template",
        resource_id=row.id,
        revision=ai_revision,
        invalidations=invalidations,
        values={
            "templateKey": row.template_key,
            "version": row.version,
            "contentHash": row.content_hash,
        },
    )


def _group_cursor_start(
    groups: tuple[
        tuple[str, tuple[CompositionTemplateProfile, ...]],
        ...,
    ],
    cursor: CursorPosition | None,
) -> int:
    if cursor is None:
        return 0
    for index, (key, versions) in enumerate(groups):
        if key == cursor.sort_value and any(
            row.id == cursor.resource_id for row in versions
        ):
            return index + 1
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "合成模板分页游标已失效，请重新加载",
        status_code=422,
    )


def _revision_conflict(current_revision: int) -> DomainError:
    return DomainError(
        ErrorCode.REVISION_CONFLICT,
        "合成模板已被更新，请重新加载后再试",
        status_code=412,
        meta={
            "currentRevision": current_revision,
            "invalidations": ["composition-templates"],
        },
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
