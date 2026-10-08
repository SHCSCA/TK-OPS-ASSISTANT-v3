from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from domain.models.ai_configuration_v1 import CapabilityRoute
from errors import DomainError, ErrorCode
from services.ai_execution_v1.dependency_graph import resolve_route_dependencies

from .dependency_snapshots import (
    persist_dependency_snapshot,
    require_unchanged_dependency_snapshot,
)
from .dto import route_to_dto
from .mutation import AIResourceMutation
from .mutation_helpers import append_route_events, utc_now
from .query_helpers import require_route
from .route_revision_queries import (
    require_route_revision,
    route_revision_conflict,
    route_validation_dto,
)
from .route_revision_support import (
    build_route_revision,
    legacy_route_payload,
    route_revision_mirror,
    route_revision_to_dto,
)
from .unit_of_work import AIConfigurationTransaction


def create_route_revision(
    transaction: AIConfigurationTransaction,
    *,
    capability_key: str,
    payload: Mapping[str, object],
    expected_revision: int,
) -> AIResourceMutation:
    route = transaction.ai.routes.get(transaction.session, capability_key)
    now = utc_now()
    if route is None:
        if expected_revision != 0:
            raise route_revision_conflict(0)
        route = transaction.ai.routes.add(
            transaction.session,
            CapabilityRoute(
                id=f"route_{uuid4().hex}",
                capability_key=capability_key,
                primary_model_profile_id=None,
                fallback_model_profile_id=None,
                prompt_profile_id=None,
                enabled=False,
                validation_status="incomplete",
                validation_issues_json="[]",
                active_revision_id=None,
                revision=1,
                created_at=now,
                updated_at=now,
            ),
        )
    else:
        updated = transaction.ai.routes.bump_revision(
            transaction.session,
            capability_key,
            expected_revision=expected_revision,
            updated_at=now,
        )
        if updated is None:
            raise route_revision_conflict(int(route.revision))
        route = updated
    revision_row = transaction.ai.route_revisions.add(
        transaction.session,
        build_route_revision(
            route_id=route.id,
            capability_key=capability_key,
            revision=transaction.ai.route_revisions.next_revision(
                transaction.session,
                route.id,
            ),
            payload=payload,
        ),
    )
    _publish_route_change(transaction, route)
    return AIResourceMutation(
        data=route_revision_to_dto(revision_row),
        resource_type="capability_route_revision",
        resource_id=revision_row.id,
        revision=int(route.revision),
        invalidations=_ROUTE_INVALIDATIONS,
        replay_snapshot_safe=True,
    )


def validate_route_revision(
    transaction: AIConfigurationTransaction,
    *,
    capability_key: str,
    revision: int,
) -> AIResourceMutation:
    route = require_route(transaction, capability_key)
    row = require_route_revision(transaction, route.id, revision)
    resolution = resolve_route_dependencies(transaction, row)
    snapshot = persist_dependency_snapshot(
        transaction,
        owner_type="route",
        owner_id=route.id,
        owner_revision=int(row.revision),
        resolution=resolution,
    )
    attached = row.dependency_snapshot_id is None
    if attached:
        row = transaction.ai.route_revisions.attach_snapshot(
            transaction.session,
            revision_id=row.id,
            dependency_snapshot_id=snapshot.id,
        )
        if row is None:
            raise DomainError(
                ErrorCode.REQUEST_CONFLICT,
                "能力路由修订校验状态已变化",
                status_code=409,
            )
        updated_route = transaction.ai.routes.bump_revision(
            transaction.session,
            capability_key,
            expected_revision=int(route.revision),
            updated_at=utc_now(),
        )
        if updated_route is None:
            raise route_revision_conflict(int(route.revision))
        route = updated_route
    return AIResourceMutation(
        data=route_validation_dto(row, snapshot),
        resource_type="ai_dependency_snapshot",
        resource_id=snapshot.id,
        revision=int(route.revision),
        invalidations=("routes", "recipes"),
        replay_snapshot_safe=True,
    )


def activate_route_revision(
    transaction: AIConfigurationTransaction,
    *,
    capability_key: str,
    revision: int,
    expected_revision: int,
) -> AIResourceMutation:
    route = require_route(transaction, capability_key)
    if int(route.revision) != expected_revision:
        raise route_revision_conflict(int(route.revision))
    target = require_route_revision(transaction, route.id, revision)
    resolution = resolve_route_dependencies(transaction, target)
    require_unchanged_dependency_snapshot(
        transaction,
        snapshot_id=target.dependency_snapshot_id,
        current=resolution,
    )
    activated = transaction.ai.route_revisions.activate(
        transaction.session,
        route=route,
        target=target,
        expected_aggregate_revision=expected_revision,
        mirror_changes=route_revision_mirror(
            target,
            issues=resolution.issues,
        ),
        updated_at=utc_now(),
    )
    if activated is None:
        raise route_revision_conflict(int(route.revision))
    _publish_route_change(transaction, activated)
    return AIResourceMutation(
        data=route_to_dto(activated),
        resource_type="capability_route",
        resource_id=activated.id,
        revision=int(activated.revision),
        invalidations=_ROUTE_INVALIDATIONS,
        replay_snapshot_safe=True,
    )


def put_compatibility_route(
    transaction: AIConfigurationTransaction,
    *,
    capability_key: str,
    payload: Mapping[str, object],
    expected_revision: int,
) -> AIResourceMutation:
    """让旧 PUT 复用草稿、校验和激活的唯一生命周期。"""
    created = create_route_revision(
        transaction,
        capability_key=capability_key,
        payload=legacy_route_payload(payload),
        expected_revision=expected_revision,
    )
    route_revision = int(created.data["revision"])
    validated = validate_route_revision(
        transaction,
        capability_key=capability_key,
        revision=route_revision,
    )
    snapshot = validated.data["dependencySnapshot"]
    if not isinstance(snapshot, Mapping):
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "能力路由依赖快照格式异常",
            status_code=500,
            loggable=True,
        )
    route = require_route(transaction, capability_key)
    if snapshot.get("status") != "valid":
        target = require_route_revision(
            transaction,
            route.id,
            route_revision,
        )
        issues = snapshot.get("issues")
        safe_issues = (
            tuple(item for item in issues if isinstance(item, Mapping))
            if isinstance(issues, list)
            else ()
        )
        data = route_to_dto(route)
        mirror = route_revision_mirror(target, issues=safe_issues)
        data.update(
            {
                "primaryModelProfileId": mirror["primary_model_profile_id"],
                "fallbackModelProfileId": mirror["fallback_model_profile_id"],
                "promptProfileId": mirror["prompt_profile_id"],
                "enabled": mirror["enabled"],
                "validationStatus": "invalid",
                "validationIssues": list(safe_issues),
            }
        )
        return AIResourceMutation(
            data=data,
            resource_type="capability_route",
            resource_id=route.id,
            revision=int(route.revision),
            invalidations=_ROUTE_INVALIDATIONS,
            replay_snapshot_safe=True,
        )
    return activate_route_revision(
        transaction,
        capability_key=capability_key,
        revision=route_revision,
        expected_revision=int(route.revision),
    )


def validate_compatibility_route(
    transaction: AIConfigurationTransaction,
    *,
    capability_key: str,
) -> AIResourceMutation:
    """校验当前活动修订；无活动修订时校验最新可修复草稿。"""
    route = require_route(transaction, capability_key)
    target = (
        transaction.ai.route_revisions.get_by_id(
            transaction.session,
            route.active_revision_id,
        )
        if route.active_revision_id is not None
        else None
    )
    if target is None:
        rows = transaction.ai.route_revisions.list(
            transaction.session,
            route.id,
        )
        if not rows:
            raise DomainError(
                ErrorCode.CAPABILITY_ROUTE_INVALID,
                "能力路由尚无可校验修订",
                status_code=409,
            )
        target = rows[0]
    return validate_route_revision(
        transaction,
        capability_key=capability_key,
        revision=int(target.revision),
    )


def _publish_route_change(
    transaction: AIConfigurationTransaction,
    route: CapabilityRoute,
) -> None:
    ai_revision = transaction.ai.revisions.increment(transaction.session)
    append_route_events(
        transaction,
        row=route,
        ai_revision=ai_revision,
        invalidations=_ROUTE_INVALIDATIONS,
    )


_ROUTE_INVALIDATIONS = ("routes", "ai-summary", "recipes")


__all__ = [
    "activate_route_revision",
    "create_route_revision",
    "put_compatibility_route",
    "validate_compatibility_route",
    "validate_route_revision",
]
