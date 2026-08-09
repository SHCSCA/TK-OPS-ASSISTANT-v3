from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from domain.models.account_configuration import PositioningProfile
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.account_configuration import (
    PositioningDto,
    PositioningVersionDto,
    PositioningVersionInput,
    PositioningVersionSummaryDto,
)
from services.accounts.events import append_account_event
from services.accounts.guards import require_account, require_revision
from services.accounts.idempotency import MutationCommand
from services.accounts.json_codec import (
    content_hash,
    dump_json,
    load_json_list,
    load_json_object,
)
from services.accounts.unit_of_work import (
    AccountMutationExecutor,
    AccountTransaction,
    AccountUnitOfWork,
    MutationExecution,
    MutationWorkResult,
)


class AccountPositioningService:
    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        mutation_executor: AccountMutationExecutor,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._mutations = mutation_executor

    def get(self, account_id: str) -> PositioningDto:
        with self._unit_of_work.read() as transaction:
            account = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            profiles = transaction.configuration.list_positioning(
                account_id,
                transaction.session,
            )
            return _positioning_to_dto(
                account_id,
                profiles,
                account_revision=int(account.revision),
            )

    def get_version(
        self,
        account_id: str,
        version: int,
    ) -> PositioningVersionDto:
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            profile = transaction.configuration.get_positioning_version(
                account_id,
                transaction.session,
                version=version,
            )
            if profile is None:
                raise DomainError(
                    ErrorCode.POSITIONING_VERSION_NOT_FOUND,
                    "定位版本不存在或已归档",
                    status_code=404,
                )
            return _positioning_version_to_dto(profile)

    def create_version(
        self,
        account_id: str,
        payload: PositioningVersionInput,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> MutationExecution:
        _validate_positioning(payload)
        request_payload = payload.model_dump(mode="json")
        request_payload["expectedRevision"] = expected_revision
        command = MutationCommand(
            account_id=account_id,
            operation_name="account.positioning.version.create",
            idempotency_key=idempotency_key,
            request_payload=request_payload,
        )
        return self._mutations.execute(
            command,
            lambda transaction: self._create_version(
                transaction,
                account_id=account_id,
                payload=payload,
                expected_revision=expected_revision,
            ),
        )

    def activate_version(
        self,
        account_id: str,
        version: int,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> MutationExecution:
        command = MutationCommand(
            account_id=account_id,
            operation_name="account.positioning.version.activate",
            idempotency_key=idempotency_key,
            request_payload={
                "version": version,
                "expectedRevision": expected_revision,
            },
        )
        return self._mutations.execute(
            command,
            lambda transaction: self._activate_version(
                transaction,
                account_id=account_id,
                version=version,
                expected_revision=expected_revision,
            ),
        )

    @staticmethod
    def _create_version(
        transaction: AccountTransaction,
        *,
        account_id: str,
        payload: PositioningVersionInput,
        expected_revision: int,
    ) -> MutationWorkResult:
        transaction.accounts.acquire_write_lock(
            transaction.session,
            account_id=account_id,
        )
        account = require_account(
            account_id,
            transaction.session,
            transaction.accounts,
        )
        require_revision(account, expected_revision)
        now = _utc_now_text()
        version = transaction.configuration.next_positioning_version(
            account_id,
            transaction.session,
        )
        profile = PositioningProfile(
            id=f"pos_{uuid4().hex}",
            account_id=account_id,
            version=version,
            status="draft",
            audience_json=dump_json(payload.audience),
            content_pillars_json=dump_json(payload.contentPillars),
            voice_style_json=dump_json(payload.tone),
            prohibited_terms_json=dump_json(payload.prohibitedTopics),
            publishing_constraints_json=dump_json(
                payload.publishingConstraints
            ),
            summary=_build_positioning_summary(
                payload.audience,
                payload.contentPillars,
            ),
            revision=1,
            created_at=now,
            activated_at=None,
        )
        transaction.configuration.add_positioning(
            account_id,
            transaction.session,
            profile,
        )
        updated_account = transaction.accounts.bump_revision(
            transaction.session,
            account_id=account_id,
            expected_revision=expected_revision,
            updated_at=now,
        )
        if updated_account is None:
            raise DomainError(
                ErrorCode.REVISION_CONFLICT,
                "账号数据已被更新，请重新加载后再试",
                status_code=412,
            )
        dto = _positioning_version_to_dto(profile)
        invalidations = [
            f"account:{account_id}:positioning",
            f"account:{account_id}:workspace",
        ]
        append_account_event(
            transaction,
            account_id=account_id,
            event_type="positioning.version.created",
            aggregate_type="positioning_profile",
            aggregate_id=profile.id,
            revision=int(updated_account.revision),
            invalidations=invalidations,
            values={"version": profile.version, "status": profile.status},
        )
        return MutationWorkResult(
            response={
                "data": dto.model_dump(mode="json"),
                "meta": {
                    "revision": int(updated_account.revision),
                    "invalidations": invalidations,
                },
            },
            resource_type="positioning_profile",
            resource_id=profile.id,
        )

    @staticmethod
    def _activate_version(
        transaction: AccountTransaction,
        *,
        account_id: str,
        version: int,
        expected_revision: int,
    ) -> MutationWorkResult:
        transaction.accounts.acquire_write_lock(
            transaction.session,
            account_id=account_id,
        )
        account = require_account(
            account_id,
            transaction.session,
            transaction.accounts,
        )
        require_revision(account, expected_revision)
        now = _utc_now_text()
        profile = transaction.configuration.activate_positioning(
            account_id,
            transaction.session,
            version=version,
            activated_at=now,
        )
        if profile is None:
            raise DomainError(
                ErrorCode.POSITIONING_VERSION_NOT_FOUND,
                "定位版本不存在或已归档",
                status_code=404,
            )
        updated_account = transaction.accounts.bump_revision(
            transaction.session,
            account_id=account_id,
            expected_revision=expected_revision,
            updated_at=now,
        )
        if updated_account is None:
            raise DomainError(
                ErrorCode.REVISION_CONFLICT,
                "账号数据已被更新，请重新加载后再试",
                status_code=412,
            )
        profiles = transaction.configuration.list_positioning(
            account_id,
            transaction.session,
        )
        dto = _positioning_to_dto(
            account_id,
            profiles,
            account_revision=int(updated_account.revision),
        )
        invalidations = [
            f"account:{account_id}:positioning",
            f"account:{account_id}:workspace",
            f"account:{account_id}:readiness",
        ]
        append_account_event(
            transaction,
            account_id=account_id,
            event_type="positioning.version.activated",
            aggregate_type="positioning_profile",
            aggregate_id=profile.id,
            revision=int(updated_account.revision),
            invalidations=invalidations,
            values={"version": profile.version, "status": profile.status},
        )
        return MutationWorkResult(
            response={
                "data": dto.model_dump(mode="json"),
                "meta": {
                    "revision": int(updated_account.revision),
                    "invalidations": invalidations,
                },
            },
            resource_type="positioning_profile",
            resource_id=profile.id,
        )


def _positioning_to_dto(
    account_id: str,
    profiles: tuple[PositioningProfile, ...],
    *,
    account_revision: int,
) -> PositioningDto:
    active = next(
        (profile for profile in profiles if profile.status == "active"),
        None,
    )
    return PositioningDto(
        accountId=account_id,
        activeVersion=None if active is None else int(active.version),
        versions=[
            PositioningVersionSummaryDto(
                version=int(profile.version),
                status=profile.status,
                summary=_positioning_display_summary(profile),
                createdAt=profile.created_at,
            )
            for profile in profiles
        ],
        revision=account_revision,
    )


def _positioning_version_to_dto(
    profile: PositioningProfile,
) -> PositioningVersionDto:
    audience = load_json_object(
        profile.audience_json,
        resource_label="定位受众",
    )
    content_pillars = _string_list(
        load_json_list(
            profile.content_pillars_json,
            resource_label="定位内容支柱",
        ),
        resource_label="定位内容支柱",
    )
    tone = load_json_object(
        profile.voice_style_json,
        resource_label="定位表达风格",
    )
    prohibited_topics = _string_list(
        load_json_list(
            profile.prohibited_terms_json,
            resource_label="定位禁用主题",
        ),
        resource_label="定位禁用主题",
    )
    publishing_constraints = load_json_object(
        profile.publishing_constraints_json,
        resource_label="定位发布约束",
    )
    document = {
        "audience": audience,
        "contentPillars": content_pillars,
        "tone": tone,
        "prohibitedTopics": prohibited_topics,
        "publishingConstraints": publishing_constraints,
    }
    return PositioningVersionDto(
        id=profile.id,
        accountId=profile.account_id,
        version=int(profile.version),
        status=profile.status,
        summary=_build_positioning_summary(audience, content_pillars),
        createdAt=profile.created_at,
        audience=audience,
        contentPillars=content_pillars,
        tone=tone,
        prohibitedTopics=prohibited_topics,
        publishingConstraints=publishing_constraints,
        contentHash=content_hash(document),
        activatedAt=profile.activated_at,
        revision=int(profile.revision),
    )


def _string_list(values: list[object], *, resource_label: str) -> list[str]:
    if not all(isinstance(value, str) for value in values):
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            f"{resource_label}数据结构异常，请查看诊断日志",
            status_code=500,
            loggable=True,
        )
    return [value for value in values if isinstance(value, str)]


def _positioning_display_summary(profile: PositioningProfile) -> str:
    audience = load_json_object(
        profile.audience_json,
        resource_label="定位受众",
    )
    content_pillars = _string_list(
        load_json_list(
            profile.content_pillars_json,
            resource_label="定位内容支柱",
        ),
        resource_label="定位内容支柱",
    )
    return _build_positioning_summary(audience, content_pillars)


def _build_positioning_summary(
    audience: dict[str, object],
    content_pillars: list[str],
) -> str:
    audience_text = _audience_display_text(audience)
    pillars = [
        _truncate_display_text(value)
        for value in content_pillars
        if value.strip()
    ]
    preview = " / ".join(pillars[:3])
    if len(pillars) > 3:
        preview = f"{preview} 等 {len(pillars)} 个方向"
    if not preview:
        preview = "内容方向待补充"
    return _truncate_display_text(
        f"面向{audience_text} · {preview}",
        limit=160,
    )


def _audience_display_text(audience: dict[str, object]) -> str:
    description = audience.get("description")
    if isinstance(description, str) and description.strip():
        return _truncate_display_text(description)
    for key in sorted(audience):
        value = audience[key]
        if isinstance(value, str) and value.strip():
            return _truncate_display_text(value)
    return "目标受众已配置"


def _truncate_display_text(value: str, *, limit: int = 36) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1]}…"


def _validate_positioning(payload: PositioningVersionInput) -> None:
    field_errors: list[FieldError] = []
    pillars = [value.strip() for value in payload.contentPillars]
    prohibited = [value.strip() for value in payload.prohibitedTopics]
    if any(not value for value in pillars) or len(set(pillars)) != len(
        pillars
    ):
        field_errors.append(
            FieldError(
                field="contentPillars",
                code="invalid_content_pillars",
                message="内容支柱不能为空或重复",
            )
        )
    if any(not value for value in prohibited) or len(
        set(prohibited)
    ) != len(prohibited):
        field_errors.append(
            FieldError(
                field="prohibitedTopics",
                code="invalid_prohibited_topics",
                message="禁用主题不能为空或重复",
            )
        )
    if not payload.audience:
        field_errors.append(
            FieldError(
                field="audience",
                code="audience_required",
                message="必须描述目标受众",
            )
        )
    if not payload.tone:
        field_errors.append(
            FieldError(
                field="tone",
                code="tone_required",
                message="必须描述表达风格",
            )
        )
    if field_errors:
        raise DomainError(
            ErrorCode.POSITIONING_INVALID,
            "账号定位配置无效",
            status_code=422,
            field_errors=field_errors,
        )


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
