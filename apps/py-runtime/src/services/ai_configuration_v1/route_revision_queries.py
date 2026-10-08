from __future__ import annotations

from common.pagination import CursorPosition
from domain.models.ai_configuration_v1 import CapabilityRouteRevision
from domain.models.ai_execution_snapshot import AIDependencySnapshot
from errors import DomainError, ErrorCode

from .dependency_snapshots import dependency_snapshot_to_dto
from .dto import route_to_dto
from .route_revision_support import route_revision_to_dto
from .unit_of_work import AIConfigurationTransaction


def require_route_revision(
    transaction: AIConfigurationTransaction,
    route_id: str,
    revision: int,
) -> CapabilityRouteRevision:
    row = transaction.ai.route_revisions.get(
        transaction.session,
        route_id,
        revision,
    )
    if row is None:
        raise DomainError(
            ErrorCode.CAPABILITY_ROUTE_INVALID,
            "能力路由修订不存在",
            status_code=404,
        )
    return row


def route_validation_dto(
    row: CapabilityRouteRevision,
    snapshot: AIDependencySnapshot,
) -> dict[str, object]:
    return {
        "capabilityRouteId": row.capability_route_id,
        "capabilityKey": row.capability_key,
        "routeRevision": int(row.revision),
        "status": snapshot.status,
        "dependencySnapshot": dependency_snapshot_to_dto(snapshot),
    }


def load_revision_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
) -> dict[str, object]:
    if resource_type != "capability_route_revision":
        raise replay_invalid()
    row = transaction.ai.route_revisions.get_by_id(
        transaction.session,
        resource_id,
    )
    if row is None:
        raise replay_invalid()
    return route_revision_to_dto(row)


def load_snapshot_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
) -> dict[str, object]:
    if resource_type != "ai_dependency_snapshot":
        raise replay_invalid()
    row = transaction.ai.dependency_snapshots.get(
        transaction.session,
        resource_id,
    )
    if row is None or row.owner_type != "route":
        raise replay_invalid()
    revision = transaction.ai.route_revisions.get(
        transaction.session,
        row.owner_id,
        int(row.owner_revision),
    )
    if revision is None:
        raise replay_invalid()
    return route_validation_dto(revision, row)


def load_route_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
) -> dict[str, object]:
    if resource_type != "capability_route":
        raise replay_invalid()
    row = next(
        (
            item
            for item in transaction.ai.routes.list(transaction.session)
            if item.id == resource_id
        ),
        None,
    )
    if row is None:
        raise replay_invalid()
    return route_to_dto(row)


def revision_start(
    rows: tuple[CapabilityRouteRevision, ...],
    cursor: CursorPosition | None,
) -> int:
    if cursor is None:
        return 0
    for index, row in enumerate(rows):
        if row.id == cursor.resource_id and str(row.revision) == cursor.sort_value:
            return index + 1
    return len(rows)


def route_revision_conflict(current: int) -> DomainError:
    return DomainError(
        ErrorCode.REVISION_CONFLICT,
        "能力路由已被更新，请刷新后重试",
        status_code=412,
        meta={"currentRevision": current, "invalidations": ["routes"]},
    )


def replay_invalid() -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        "能力路由幂等记录异常",
        status_code=500,
        loggable=True,
    )


__all__ = [
    "load_revision_replay",
    "load_route_replay",
    "load_snapshot_replay",
    "require_route_revision",
    "revision_start",
    "route_revision_conflict",
    "route_validation_dto",
]
