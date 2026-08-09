from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from domain.models.account_configuration import (
    AccountConfigCopyRun,
    BrandKit,
    PositioningProfile,
)
from errors import DomainError, ErrorCode
from schemas.v1.accounts import (
    AccountConfigCopyResultDto,
    AccountCopyInput,
    AccountCopySkippedSectionDto,
)
from services.accounts.events import append_account_event
from services.accounts.guards import require_account, require_revision
from services.accounts.idempotency import MutationCommand
from services.accounts.json_codec import dump_json
from services.accounts.ports import AIRecipeCopyPort
from services.accounts.types import AccountStatus
from services.accounts.unit_of_work import (
    AccountMutationExecutor,
    AccountTransaction,
    MutationExecution,
    MutationWorkResult,
)

_COPY_SECTIONS = frozenset(
    {
        "positioning",
        "knowledgeRules",
        "brandKit",
        "aiRecipe",
        "publishDefaults",
    }
)


class AccountConfigCopyService:
    def __init__(
        self,
        mutation_executor: AccountMutationExecutor,
        *,
        ai_recipe_copy_port: AIRecipeCopyPort,
    ) -> None:
        self._mutations = mutation_executor
        self._ai_recipe_copy_port = ai_recipe_copy_port

    def copy(
        self,
        target_account_id: str,
        payload: AccountCopyInput,
        *,
        expected_revision: int,
        idempotency_key: str,
        operation_id: str,
    ) -> MutationExecution:
        sections = tuple(payload.sections)
        invalid = sorted(set(sections) - _COPY_SECTIONS)
        if invalid:
            raise DomainError(
                ErrorCode.ACCOUNT_COPY_SECTION_INVALID,
                "账号配置复制包含不允许的分区",
                status_code=422,
                meta={"invalidSections": invalid},
            )
        if payload.sourceAccountId == target_account_id:
            raise DomainError(
                ErrorCode.ACCOUNT_COPY_SOURCE_EQUALS_TARGET,
                "不能把账号配置复制给同一个账号",
                status_code=409,
            )
        command = MutationCommand(
            account_id=target_account_id,
            operation_name="account.config.copy",
            idempotency_key=idempotency_key,
            request_payload={
                "sourceAccountId": payload.sourceAccountId,
                "sections": list(sections),
                "expectedRevision": expected_revision,
            },
        )
        return self._mutations.execute(
            command,
            lambda transaction: self._copy(
                transaction,
                source_account_id=payload.sourceAccountId,
                target_account_id=target_account_id,
                sections=sections,
                expected_revision=expected_revision,
                operation_id=operation_id,
            ),
        )

    def _copy(
        self,
        transaction: AccountTransaction,
        *,
        source_account_id: str,
        target_account_id: str,
        sections: tuple[str, ...],
        expected_revision: int,
        operation_id: str,
    ) -> MutationWorkResult:
        transaction.accounts.acquire_write_lock(
            transaction.session,
            account_id=target_account_id,
        )
        source = require_account(
            source_account_id,
            transaction.session,
            transaction.accounts,
            allow_archived=True,
        )
        target = require_account(
            target_account_id,
            transaction.session,
            transaction.accounts,
        )
        del source
        require_revision(target, expected_revision)
        if target.status != AccountStatus.DRAFT.value:
            raise DomainError(
                ErrorCode.ACCOUNT_STATE_TRANSITION_INVALID,
                "配置只能复制到新建的草稿账号",
                status_code=409,
            )

        now = _utc_now_text()
        copied: list[str] = []
        skipped: list[AccountCopySkippedSectionDto] = []
        for section in sections:
            copied_section, reason_code = self._copy_section(
                transaction,
                source_account_id=source_account_id,
                target_account_id=target_account_id,
                section=section,
                now=now,
            )
            if copied_section:
                copied.append(section)
            else:
                skipped.append(
                    AccountCopySkippedSectionDto(
                        section=section,
                        reasonCode=reason_code or "SOURCE_SECTION_EMPTY",
                    )
                )

        updated = transaction.accounts.bump_revision(
            transaction.session,
            account_id=target_account_id,
            expected_revision=expected_revision,
            updated_at=now,
        )
        if updated is None:
            raise DomainError(
                ErrorCode.REVISION_CONFLICT,
                "目标账号已被更新，请重新加载后再复制",
                status_code=412,
            )
        run_id = f"copy_{uuid4().hex}"
        result = AccountConfigCopyResultDto(
            runId=run_id,
            sourceAccountId=source_account_id,
            targetAccountId=target_account_id,
            requestedSections=list(sections),
            copiedSections=copied,
            skippedSections=skipped,
            status="succeeded",
            targetRevision=int(updated.revision),
            completedAt=now,
        )
        transaction.configuration.add_copy_run(
            target_account_id,
            transaction.session,
            AccountConfigCopyRun(
                id=run_id,
                source_account_id=source_account_id,
                target_account_id=target_account_id,
                requested_sections_json=_dump_sections(sections),
                copied_sections_json=_dump_sections(tuple(copied)),
                skipped_sections_json=dump_json(
                    [
                        item.model_dump(mode="json")
                        for item in skipped
                    ]
                ),
                status="succeeded",
                operation_id=operation_id,
                error_code=None,
                error_log_id=None,
                created_at=now,
                completed_at=now,
            ),
        )
        invalidations = [
            f"account:{target_account_id}:detail",
            f"account:{target_account_id}:workspace",
            f"account:{target_account_id}:readiness",
        ]
        append_account_event(
            transaction,
            account_id=target_account_id,
            event_type="account.config.copied",
            aggregate_type="account",
            aggregate_id=target_account_id,
            revision=int(updated.revision),
            invalidations=invalidations,
            values={
                "sourceAccountId": source_account_id,
                "copiedSections": copied,
                "skippedSections": [
                    item.section for item in skipped
                ],
                "runId": run_id,
            },
        )
        return MutationWorkResult(
            response={
                "data": result.model_dump(mode="json"),
                "meta": {
                    "revision": int(updated.revision),
                    "invalidations": invalidations,
                },
            },
            resource_type="account_config_copy_run",
            resource_id=run_id,
        )

    def _copy_section(
        self,
        transaction: AccountTransaction,
        *,
        source_account_id: str,
        target_account_id: str,
        section: str,
        now: str,
    ) -> tuple[bool, str | None]:
        if section == "positioning":
            return self._copy_positioning(
                transaction,
                source_account_id=source_account_id,
                target_account_id=target_account_id,
                now=now,
            )
        if section == "knowledgeRules":
            return self._copy_knowledge_rules(
                transaction,
                source_account_id=source_account_id,
                target_account_id=target_account_id,
                now=now,
            )
        if section == "brandKit":
            return self._copy_brand_kit(
                transaction,
                source_account_id=source_account_id,
                target_account_id=target_account_id,
                now=now,
            )
        if section == "publishDefaults":
            return self._copy_publish_defaults(
                transaction,
                source_account_id=source_account_id,
                target_account_id=target_account_id,
                now=now,
            )
        decision = self._ai_recipe_copy_port.copy_active_recipe(
            transaction.session,
            source_account_id=source_account_id,
            target_account_id=target_account_id,
        )
        return decision.copied, decision.reason_code

    @staticmethod
    def _copy_positioning(
        transaction: AccountTransaction,
        *,
        source_account_id: str,
        target_account_id: str,
        now: str,
    ) -> tuple[bool, str | None]:
        source = transaction.configuration.get_active_positioning(
            source_account_id,
            transaction.session,
        )
        if source is None:
            return False, "POSITIONING_NOT_CONFIGURED"
        version = transaction.configuration.next_positioning_version(
            target_account_id,
            transaction.session,
        )
        transaction.configuration.add_positioning(
            target_account_id,
            transaction.session,
            PositioningProfile(
                id=f"pos_{uuid4().hex}",
                account_id=target_account_id,
                version=version,
                status="draft",
                audience_json=source.audience_json,
                content_pillars_json=source.content_pillars_json,
                voice_style_json=source.voice_style_json,
                prohibited_terms_json=source.prohibited_terms_json,
                publishing_constraints_json=(
                    source.publishing_constraints_json
                ),
                summary=source.summary,
                revision=1,
                created_at=now,
                activated_at=None,
            ),
        )
        activated = transaction.configuration.activate_positioning(
            target_account_id,
            transaction.session,
            version=version,
            activated_at=now,
        )
        if activated is None:
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "复制定位配置后无法激活新版本",
                status_code=500,
                loggable=True,
            )
        return True, None

    @staticmethod
    def _copy_knowledge_rules(
        transaction: AccountTransaction,
        *,
        source_account_id: str,
        target_account_id: str,
        now: str,
    ) -> tuple[bool, str | None]:
        source = transaction.knowledge.get_base(
            source_account_id,
            transaction.session,
        )
        target = transaction.knowledge.get_base(
            target_account_id,
            transaction.session,
        )
        if source is None or target is None:
            return False, "KNOWLEDGE_RULES_NOT_CONFIGURED"
        transaction.knowledge.update_rules(
            target_account_id,
            transaction.session,
            rules_json=source.rules_json,
            updated_at=now,
        )
        return True, None

    @staticmethod
    def _copy_brand_kit(
        transaction: AccountTransaction,
        *,
        source_account_id: str,
        target_account_id: str,
        now: str,
    ) -> tuple[bool, str | None]:
        source = transaction.configuration.get_active_brand_kit(
            source_account_id,
            transaction.session,
        )
        if source is None:
            return False, "BRAND_KIT_NOT_CONFIGURED"
        version = transaction.configuration.next_brand_kit_version(
            target_account_id,
            transaction.session,
        )
        transaction.configuration.add_and_activate_brand_kit(
            target_account_id,
            transaction.session,
            BrandKit(
                id=f"brand_{uuid4().hex}",
                account_id=target_account_id,
                version=version,
                status="active",
                visual_style_json=source.visual_style_json,
                colors_json=source.colors_json,
                fonts_json=source.fonts_json,
                logo_asset_refs_json=source.logo_asset_refs_json,
                voice_rules_json=source.voice_rules_json,
                revision=1,
                created_at=now,
                activated_at=now,
            ),
        )
        return True, None

    @staticmethod
    def _copy_publish_defaults(
        transaction: AccountTransaction,
        *,
        source_account_id: str,
        target_account_id: str,
        now: str,
    ) -> tuple[bool, str | None]:
        source = transaction.configuration.get_publish_defaults(
            source_account_id,
            transaction.session,
        )
        if source is None:
            return False, "PUBLISH_DEFAULTS_NOT_CONFIGURED"
        transaction.configuration.save_publish_defaults(
            target_account_id,
            transaction.session,
            values={
                "timezone": source.timezone,
                "privacy_level": source.privacy_level,
                "allow_comments": source.allow_comments,
                "allow_duet": source.allow_duet,
                "allow_stitch": source.allow_stitch,
                "caption_rules_json": source.caption_rules_json,
            },
            created_at=now,
            updated_at=now,
        )
        return True, None


def _dump_sections(sections: tuple[str, ...]) -> str:
    return dump_json(list(sections))


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace(
        "+00:00",
        "Z",
    )
