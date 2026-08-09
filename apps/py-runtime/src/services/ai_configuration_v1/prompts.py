from __future__ import annotations

from collections.abc import Mapping

from common.pagination import CursorPosition
from errors import DomainError, ErrorCode
from services.accounts.idempotency import MutationCommand

from .dto import prompt_summary_to_dto, prompt_version_to_dto
from .events import append_system_ai_event
from .mutation import (
    AIConfigurationMutationExecutor,
    AIResourceMutation,
)
from .unit_of_work import (
    AIConfigurationTransaction,
    AIConfigurationUnitOfWork,
)
from .prompt_queries import (
    _group_cursor_start,
    _group_prompt_rows,
    _load_prompt_summary_replay,
    _load_prompt_version_replay,
    _prompt_summary,
    _require_prompt_version,
    _require_prompt_versions,
    _revision_conflict,
    _utc_now,
)
from .prompt_validation import (
    _build_prompt_row,
    _normalize_prompt_profile,
    _normalize_prompt_version,
    _prompt_payload_hash,
    _safe_prompt_request,
)
from .validation import require_capability_key, require_profile_key


class PromptProfileService:
    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        mutations: AIConfigurationMutationExecutor,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._mutations = mutations

    def list_prompt_profiles(
        self,
        *,
        capability_key: str | None = None,
        status: str | None = None,
        cursor: CursorPosition | None = None,
        limit: int = 50,
    ) -> tuple[dict[str, object], CursorPosition | None]:
        if capability_key is not None:
            require_capability_key(capability_key)
        with self._unit_of_work.read() as transaction:
            rows = transaction.ai.prompts.list(
                transaction.session,
                capability_key=capability_key,
            )
            groups = _group_prompt_rows(rows, status=status)
            start = _group_cursor_start(groups, cursor)
            page = groups[start : start + limit]
            items = [
                prompt_summary_to_dto(
                    versions,
                    reference_count=sum(
                        transaction.ai.routes.count_by_prompt(
                            transaction.session,
                            row.id,
                        )
                        for row in versions
                    ),
                )
                for _, versions in page
            ]
            next_position = (
                CursorPosition(
                    sort_value=page[-1][0],
                    resource_id=page[-1][1][-1].id,
                )
                if start + limit < len(groups) and page
                else None
            )
            return (
                {"items": items, "totalKnown": len(groups)},
                next_position,
            )

    def get_prompt_profile(self, profile_key: str) -> dict[str, object]:
        profile_key = require_profile_key(
            profile_key,
            field="profileKey",
        )
        with self._unit_of_work.read() as transaction:
            rows = _require_prompt_versions(transaction, profile_key)
            return _prompt_summary(transaction, rows)

    def get_prompt_version(
        self,
        profile_key: str,
        version: int,
    ) -> dict[str, object]:
        with self._unit_of_work.read() as transaction:
            row = _require_prompt_version(
                transaction,
                profile_key,
                version,
            )
            return prompt_version_to_dto(row)

    def create_prompt_profile(
        self,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        normalized = _normalize_prompt_profile(payload)
        command = MutationCommand(
            account_id=None,
            operation_name="ai.prompt_profile.create",
            idempotency_key=idempotency_key,
            request_payload=_safe_prompt_request(normalized),
        )
        result = self._mutations.execute(
            command,
            work=lambda transaction: self._create_profile(
                transaction,
                normalized,
            ),
            replay_loader=_load_prompt_summary_replay,
        )
        return result

    def create_prompt_version(
        self,
        profile_key: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        profile_key = require_profile_key(
            profile_key,
            field="profileKey",
        )
        normalized = _normalize_prompt_version(payload)
        command = MutationCommand(
            account_id=None,
            operation_name="ai.prompt_version.create",
            idempotency_key=idempotency_key,
            request_payload={
                "profileKey": profile_key,
                "contentHash": _prompt_payload_hash(normalized),
                "createdFromVersion": normalized["createdFromVersion"],
                "expectedRevision": expected_revision,
            },
        )
        result = self._mutations.execute(
            command,
            work=lambda transaction: self._create_version(
                transaction,
                profile_key=profile_key,
                payload=normalized,
                expected_revision=expected_revision,
            ),
            replay_loader=_load_prompt_version_replay,
        )
        return result

    def activate_prompt_version(
        self,
        profile_key: str,
        version: int,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        profile_key = require_profile_key(
            profile_key,
            field="profileKey",
        )
        command = MutationCommand(
            account_id=None,
            operation_name="ai.prompt_version.activate",
            idempotency_key=idempotency_key,
            request_payload={
                "profileKey": profile_key,
                "version": version,
                "expectedRevision": expected_revision,
            },
        )
        result = self._mutations.execute(
            command,
            work=lambda transaction: self._activate(
                transaction,
                profile_key=profile_key,
                version=version,
                expected_revision=expected_revision,
            ),
            replay_loader=_load_prompt_summary_replay,
        )
        return result

    def _create_profile(
        self,
        transaction: AIConfigurationTransaction,
        payload: Mapping[str, object],
    ) -> AIResourceMutation:
        profile_key = str(payload["profileKey"])
        if transaction.ai.prompts.get_latest(
            transaction.session,
            profile_key,
        ) is not None:
            raise DomainError(
                ErrorCode.PROMPT_PROFILE_INVALID,
                "Prompt Profile 标识已存在，请创建新版本",
                status_code=422,
            )
        row = _build_prompt_row(
            payload,
            profile_key=profile_key,
            capability_key=str(payload["capabilityKey"]),
            version=1,
            created_from_id=None,
            revision=1,
        )
        transaction.ai.prompts.add(transaction.session, row)
        ai_revision = transaction.ai.revisions.increment(
            transaction.session
        )
        invalidations = ("prompts", "ai-summary")
        append_system_ai_event(
            transaction,
            event_type="prompt.profile.updated",
            resource_type="prompt_profile",
            resource_id=row.id,
            revision=ai_revision,
            invalidations=invalidations,
            values={
                "profileKey": row.profile_key,
                "version": row.version,
                "contentHash": row.content_hash,
            },
        )
        return AIResourceMutation(
            data=_prompt_summary(transaction, (row,)),
            resource_type="prompt_profile",
            resource_id=row.id,
            revision=int(row.revision),
            invalidations=invalidations,
        )

    def _create_version(
        self,
        transaction: AIConfigurationTransaction,
        *,
        profile_key: str,
        payload: Mapping[str, object],
        expected_revision: int,
    ) -> AIResourceMutation:
        versions = _require_prompt_versions(transaction, profile_key)
        aggregate_revision = max(int(row.revision) for row in versions)
        if aggregate_revision != expected_revision:
            raise _revision_conflict(aggregate_revision)
        source = _require_prompt_version(
            transaction,
            profile_key,
            int(payload["createdFromVersion"]),
        )
        version = transaction.ai.prompts.next_version(
            transaction.session,
            profile_key,
        )
        row = _build_prompt_row(
            payload,
            profile_key=profile_key,
            capability_key=source.capability_key,
            version=version,
            created_from_id=source.id,
            revision=aggregate_revision + 1,
        )
        transaction.ai.prompts.add(transaction.session, row)
        ai_revision = transaction.ai.revisions.increment(
            transaction.session
        )
        invalidations = ("prompts",)
        append_system_ai_event(
            transaction,
            event_type="prompt.profile.updated",
            resource_type="prompt_profile",
            resource_id=row.id,
            revision=ai_revision,
            invalidations=invalidations,
            values={
                "profileKey": row.profile_key,
                "version": row.version,
                "contentHash": row.content_hash,
            },
        )
        return AIResourceMutation(
            data=prompt_version_to_dto(row),
            resource_type="prompt_version",
            resource_id=row.id,
            revision=int(row.revision),
            invalidations=invalidations,
        )

    def _activate(
        self,
        transaction: AIConfigurationTransaction,
        *,
        profile_key: str,
        version: int,
        expected_revision: int,
    ) -> AIResourceMutation:
        versions = _require_prompt_versions(transaction, profile_key)
        aggregate_revision = max(int(row.revision) for row in versions)
        if aggregate_revision != expected_revision:
            raise _revision_conflict(aggregate_revision)
        target = _require_prompt_version(transaction, profile_key, version)
        activated = transaction.ai.prompts.activate(
            transaction.session,
            profile_key=profile_key,
            version=version,
            expected_revision=int(target.revision),
            next_revision=aggregate_revision + 1,
            activated_at=_utc_now(),
        )
        if activated is None:
            raise DomainError(
                ErrorCode.PROMPT_VERSION_IMMUTABLE,
                "Prompt 版本无法激活，请重新加载",
                status_code=409,
            )
        ai_revision = transaction.ai.revisions.increment(
            transaction.session
        )
        invalidations = ("prompts", "routes", "recipes")
        append_system_ai_event(
            transaction,
            event_type="prompt.profile.activated",
            resource_type="prompt_profile",
            resource_id=activated.id,
            revision=ai_revision,
            invalidations=invalidations,
            values={
                "profileKey": profile_key,
                "version": version,
                "contentHash": activated.content_hash,
            },
        )
        append_system_ai_event(
            transaction,
            event_type="ai.config.changed",
            resource_type="prompt_profile",
            resource_id=activated.id,
            revision=ai_revision,
            invalidations=invalidations,
        )
        return AIResourceMutation(
            data=_prompt_summary(
                transaction,
                transaction.ai.prompts.list_versions(
                    transaction.session,
                    profile_key,
                ),
            ),
            resource_type="prompt_profile",
            resource_id=activated.id,
            revision=int(activated.revision),
            invalidations=invalidations,
        )
