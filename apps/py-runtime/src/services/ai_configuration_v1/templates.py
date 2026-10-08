from __future__ import annotations

from collections.abc import Mapping

from common.pagination import CursorPosition
from errors import DomainError, ErrorCode
from services.accounts.idempotency import MutationCommand

from .dto import template_version_to_dto
from .mutation import (
    AIConfigurationMutationExecutor,
    AIResourceMutation,
)
from .unit_of_work import (
    AIConfigurationTransaction,
    AIConfigurationUnitOfWork,
)
from .template_queries import (
    _append_template_event,
    _group_cursor_start,
    _group_template_rows,
    _load_template_summary_replay,
    _load_template_validation_replay,
    _load_template_version_replay,
    _require_template_version,
    _require_template_versions,
    _revision_conflict,
    _template_summary,
)
from .template_lifecycle import (
    activate_template_version,
    validate_template_version,
)
from .template_validation import (
    _build_template_row,
    _normalize_template_profile,
    _normalize_template_version,
    _template_payload_hash,
)
from .validation import require_profile_key, require_template_type


class CompositionTemplateService:
    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        mutations: AIConfigurationMutationExecutor,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._mutations = mutations

    def list_composition_templates(
        self,
        *,
        template_type: str | None = None,
        status: str | None = None,
        cursor: CursorPosition | None = None,
        limit: int = 50,
    ) -> tuple[dict[str, object], CursorPosition | None]:
        if template_type is not None:
            require_template_type(template_type)
        with self._unit_of_work.read() as transaction:
            rows = transaction.ai.templates.list(
                transaction.session,
                template_type=template_type,
            )
            groups = _group_template_rows(rows, status=status)
            start = _group_cursor_start(groups, cursor)
            page = groups[start : start + limit]
            items = [
                _template_summary(transaction, versions)
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

    def get_composition_template(
        self,
        template_key: str,
    ) -> dict[str, object]:
        template_key = require_profile_key(
            template_key,
            field="templateKey",
        )
        with self._unit_of_work.read() as transaction:
            return _template_summary(
                transaction,
                _require_template_versions(transaction, template_key),
            )

    def get_composition_template_version(
        self,
        template_key: str,
        version: int,
    ) -> dict[str, object]:
        with self._unit_of_work.read() as transaction:
            return template_version_to_dto(
                _require_template_version(
                    transaction,
                    template_key,
                    version,
                )
            )

    def create_composition_template(
        self,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        normalized = _normalize_template_profile(payload)
        command = MutationCommand(
            account_id=None,
            operation_name="ai.composition_template.create",
            idempotency_key=idempotency_key,
            request_payload={
                "templateKey": normalized["templateKey"],
                "contentHash": _template_payload_hash(normalized),
            },
        )
        result = self._mutations.execute(
            command,
            work=lambda transaction: self._create_template(
                transaction,
                normalized,
            ),
            replay_loader=_load_template_summary_replay,
        )
        return result

    def create_composition_template_version(
        self,
        template_key: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        template_key = require_profile_key(
            template_key,
            field="templateKey",
        )
        normalized = _normalize_template_version(payload)
        command = MutationCommand(
            account_id=None,
            operation_name="ai.composition_template_version.create",
            idempotency_key=idempotency_key,
            request_payload={
                "templateKey": template_key,
                "contentHash": _template_payload_hash(normalized),
                "createdFromVersion": normalized["createdFromVersion"],
                "expectedRevision": expected_revision,
            },
        )
        result = self._mutations.execute(
            command,
            work=lambda transaction: self._create_version(
                transaction,
                template_key=template_key,
                payload=normalized,
                expected_revision=expected_revision,
            ),
            replay_loader=_load_template_version_replay,
        )
        return result

    def validate_composition_template_version(
        self,
        template_key: str,
        version: int,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        template_key = require_profile_key(
            template_key,
            field="templateKey",
        )
        command = MutationCommand(
            account_id=None,
            operation_name="ai.composition_template_version.validate",
            idempotency_key=idempotency_key,
            request_payload={
                "templateKey": template_key,
                "version": version,
            },
        )
        result = self._mutations.execute(
            command,
            work=lambda transaction: validate_template_version(
                transaction,
                template_key=template_key,
                version=version,
            ),
            replay_loader=_load_template_validation_replay,
        )
        return result

    def activate_composition_template_version(
        self,
        template_key: str,
        version: int,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        template_key = require_profile_key(
            template_key,
            field="templateKey",
        )
        command = MutationCommand(
            account_id=None,
            operation_name="ai.composition_template_version.activate",
            idempotency_key=idempotency_key,
            request_payload={
                "templateKey": template_key,
                "version": version,
                "expectedRevision": expected_revision,
            },
        )
        result = self._mutations.execute(
            command,
            work=lambda transaction: activate_template_version(
                transaction,
                template_key=template_key,
                version=version,
                expected_revision=expected_revision,
            ),
            replay_loader=_load_template_summary_replay,
        )
        return result

    def _create_template(
        self,
        transaction: AIConfigurationTransaction,
        payload: Mapping[str, object],
    ) -> AIResourceMutation:
        template_key = str(payload["templateKey"])
        if transaction.ai.templates.get_latest(
            transaction.session,
            template_key,
        ) is not None:
            raise DomainError(
                ErrorCode.COMPOSITION_TEMPLATE_INVALID,
                "合成模板标识已存在，请创建新版本",
                status_code=422,
            )
        row = _build_template_row(
            payload,
            template_key=template_key,
            template_type=str(payload["templateType"]),
            version=1,
            created_from_id=None,
            revision=1,
        )
        transaction.ai.templates.add(transaction.session, row)
        ai_revision = transaction.ai.revisions.increment(
            transaction.session
        )
        invalidations = ("composition-templates",)
        _append_template_event(
            transaction,
            row=row,
            event_type="composition.template.updated",
            ai_revision=ai_revision,
            invalidations=invalidations,
        )
        return AIResourceMutation(
            data=_template_summary(transaction, (row,)),
            resource_type="composition_template",
            resource_id=row.id,
            revision=int(row.revision),
            invalidations=invalidations,
        )

    def _create_version(
        self,
        transaction: AIConfigurationTransaction,
        *,
        template_key: str,
        payload: Mapping[str, object],
        expected_revision: int,
    ) -> AIResourceMutation:
        versions = _require_template_versions(transaction, template_key)
        aggregate_revision = max(int(row.revision) for row in versions)
        if aggregate_revision != expected_revision:
            raise _revision_conflict(aggregate_revision)
        source = _require_template_version(
            transaction,
            template_key,
            int(payload["createdFromVersion"]),
        )
        row = _build_template_row(
            payload,
            template_key=template_key,
            template_type=source.template_type,
            version=transaction.ai.templates.next_version(
                transaction.session,
                template_key,
            ),
            created_from_id=source.id,
            revision=aggregate_revision + 1,
        )
        transaction.ai.templates.add(transaction.session, row)
        ai_revision = transaction.ai.revisions.increment(
            transaction.session
        )
        invalidations = ("composition-templates",)
        _append_template_event(
            transaction,
            row=row,
            event_type="composition.template.updated",
            ai_revision=ai_revision,
            invalidations=invalidations,
        )
        return AIResourceMutation(
            data=template_version_to_dto(row),
            resource_type="composition_template_version",
            resource_id=row.id,
            revision=int(row.revision),
            invalidations=invalidations,
        )
