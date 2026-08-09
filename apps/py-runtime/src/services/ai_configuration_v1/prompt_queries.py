from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime

from common.pagination import CursorPosition
from domain.models.ai_configuration_v1 import PromptProfile
from errors import DomainError, ErrorCode

from .dto import prompt_summary_to_dto, prompt_version_to_dto
from .unit_of_work import AIConfigurationTransaction

def _group_prompt_rows(
    rows: tuple[PromptProfile, ...],
    *,
    status: str | None,
) -> tuple[tuple[str, tuple[PromptProfile, ...]], ...]:
    grouped: dict[str, list[PromptProfile]] = defaultdict(list)
    for row in rows:
        grouped[row.profile_key].append(row)
    groups = []
    for key in sorted(grouped):
        versions = tuple(grouped[key])
        if status is not None and not any(
            row.status == status for row in versions
        ):
            continue
        groups.append((key, versions))
    return tuple(groups)


def _prompt_summary(
    transaction: AIConfigurationTransaction,
    rows: tuple[PromptProfile, ...],
) -> dict[str, object]:
    return prompt_summary_to_dto(
        rows,
        reference_count=sum(
            transaction.ai.routes.count_by_prompt(
                transaction.session,
                row.id,
            )
            for row in rows
        ),
    )


def _require_prompt_versions(
    transaction: AIConfigurationTransaction,
    profile_key: str,
) -> tuple[PromptProfile, ...]:
    rows = transaction.ai.prompts.list_versions(
        transaction.session,
        profile_key,
    )
    if not rows:
        raise DomainError(
            ErrorCode.PROMPT_PROFILE_NOT_FOUND,
            "Prompt Profile 不存在",
            status_code=404,
        )
    return rows


def _require_prompt_version(
    transaction: AIConfigurationTransaction,
    profile_key: str,
    version: int,
) -> PromptProfile:
    row = transaction.ai.prompts.get(
        transaction.session,
        profile_key=profile_key,
        version=version,
    )
    if row is None:
        raise DomainError(
            ErrorCode.PROMPT_VERSION_NOT_FOUND,
            "Prompt 版本不存在",
            status_code=404,
        )
    return row


def _load_prompt_summary_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
) -> Mapping[str, object]:
    if resource_type != "prompt_profile":
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "Prompt 幂等记录资源类型异常",
            status_code=500,
            loggable=True,
        )
    row = transaction.ai.prompts.get_by_id(
        transaction.session,
        resource_id,
    )
    if row is None:
        raise DomainError(
            ErrorCode.PROMPT_PROFILE_NOT_FOUND,
            "Prompt 幂等资源已不存在",
            status_code=404,
        )
    return _prompt_summary(
        transaction,
        _require_prompt_versions(transaction, row.profile_key),
    )


def _load_prompt_version_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
) -> Mapping[str, object]:
    if resource_type != "prompt_version":
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "Prompt 版本幂等记录资源类型异常",
            status_code=500,
            loggable=True,
        )
    row = transaction.ai.prompts.get_by_id(
        transaction.session,
        resource_id,
    )
    if row is None:
        raise DomainError(
            ErrorCode.PROMPT_VERSION_NOT_FOUND,
            "Prompt 幂等版本已不存在",
            status_code=404,
        )
    return prompt_version_to_dto(row)


def _group_cursor_start(
    groups: tuple[tuple[str, tuple[PromptProfile, ...]], ...],
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
        "Prompt 分页游标已失效，请重新加载",
        status_code=422,
    )


def _revision_conflict(current_revision: int) -> DomainError:
    return DomainError(
        ErrorCode.REVISION_CONFLICT,
        "Prompt Profile 已被更新，请重新加载后再试",
        status_code=412,
        meta={
            "currentRevision": current_revision,
            "invalidations": ["prompts"],
        },
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
