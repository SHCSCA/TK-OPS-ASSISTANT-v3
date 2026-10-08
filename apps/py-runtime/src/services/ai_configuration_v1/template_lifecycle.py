from __future__ import annotations

from errors import DomainError, ErrorCode

from .dependency_snapshots import (
    dependency_snapshot_to_dto,
    persist_dependency_snapshot,
    require_unchanged_dependency_snapshot,
)
from .events import append_system_ai_event
from .mutation import AIResourceMutation
from .template_dependencies import resolve_template_dependencies
from .template_queries import (
    _append_template_event,
    _require_template_version,
    _require_template_versions,
    _revision_conflict,
    _template_summary,
    _utc_now,
)
from .template_validation import _template_validation
from .unit_of_work import AIConfigurationTransaction


def validate_template_version(
    transaction: AIConfigurationTransaction,
    *,
    template_key: str,
    version: int,
) -> AIResourceMutation:
    row = _require_template_version(transaction, template_key, version)
    validation = _template_validation(transaction, row)
    resolution = resolve_template_dependencies(
        transaction,
        row,
        validation=validation,
    )
    snapshot = persist_dependency_snapshot(
        transaction,
        owner_type="composition_template",
        owner_id=row.id,
        owner_revision=int(row.version),
        resolution=resolution,
    )
    if row.dependency_snapshot_id is None:
        updated = transaction.ai.templates.attach_dependency_snapshot(
            transaction.session,
            template_id=row.id,
            dependency_snapshot_id=snapshot.id,
            expected_revision=int(row.revision),
        )
        if updated is None:
            raise DomainError(
                ErrorCode.REQUEST_CONFLICT,
                "合成模板校验状态已变化，请重试",
                status_code=409,
            )
        row = updated
    elif row.dependency_snapshot_id != snapshot.id:
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "合成模板依赖快照冲突，请创建新版本",
            status_code=409,
        )
    validation["dependencySnapshot"] = dependency_snapshot_to_dto(snapshot)
    invalidations = ("composition-templates", "recipes")
    append_system_ai_event(
        transaction,
        event_type="composition.template.updated",
        resource_type="composition_template",
        resource_id=row.id,
        revision=int(row.revision),
        invalidations=invalidations,
        values={
            "templateKey": row.template_key,
            "version": row.version,
            "validationStatus": validation["validationStatus"],
        },
    )
    return AIResourceMutation(
        data=validation,
        resource_type="composition_template_validation",
        resource_id=row.id,
        revision=int(row.revision),
        invalidations=invalidations,
        replay_snapshot_safe=True,
    )


def activate_template_version(
    transaction: AIConfigurationTransaction,
    *,
    template_key: str,
    version: int,
    expected_revision: int,
) -> AIResourceMutation:
    versions = _require_template_versions(transaction, template_key)
    aggregate_revision = max(int(row.revision) for row in versions)
    if aggregate_revision != expected_revision:
        raise _revision_conflict(aggregate_revision)
    target = _require_template_version(transaction, template_key, version)
    current = resolve_template_dependencies(transaction, target)
    require_unchanged_dependency_snapshot(
        transaction,
        snapshot_id=target.dependency_snapshot_id,
        current=current,
    )
    activated = transaction.ai.templates.activate(
        transaction.session,
        template_key=template_key,
        version=version,
        expected_revision=int(target.revision),
        next_revision=aggregate_revision + 1,
        activated_at=_utc_now(),
    )
    if activated is None:
        raise _revision_conflict(aggregate_revision)
    ai_revision = transaction.ai.revisions.increment(transaction.session)
    invalidations = ("composition-templates", "recipes")
    _append_template_event(
        transaction,
        row=activated,
        event_type="composition.template.activated",
        ai_revision=ai_revision,
        invalidations=invalidations,
    )
    append_system_ai_event(
        transaction,
        event_type="ai.config.changed",
        resource_type="composition_template",
        resource_id=activated.id,
        revision=ai_revision,
        invalidations=invalidations,
    )
    return AIResourceMutation(
        data=_template_summary(
            transaction,
            transaction.ai.templates.list_versions(
                transaction.session,
                template_key,
            ),
        ),
        resource_type="composition_template",
        resource_id=activated.id,
        revision=int(activated.revision),
        invalidations=invalidations,
    )


__all__ = ["activate_template_version", "validate_template_version"]
