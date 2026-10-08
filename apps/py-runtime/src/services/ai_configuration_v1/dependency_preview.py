from __future__ import annotations

from typing import Literal

from errors import DomainError, ErrorCode
from services.ai_execution_v1.dependency_graph import resolve_route_dependencies

from .dependency_snapshots import dependency_snapshot_to_dto
from .mutation_helpers import utc_now
from .template_dependencies import resolve_template_dependencies
from .unit_of_work import AIConfigurationUnitOfWork

DependencyOwnerType = Literal["route", "composition_template"]


class AIDependencyPreviewService:
    """只读解析当前配置依赖，不在 GET 请求中写入快照。"""

    def __init__(self, unit_of_work: AIConfigurationUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def preview(
        self,
        *,
        owner_type: DependencyOwnerType,
        owner_id: str,
        owner_revision: int,
    ) -> dict[str, object]:
        with self._unit_of_work.read() as transaction:
            if owner_type == "route":
                owner = transaction.ai.route_revisions.get(
                    transaction.session,
                    owner_id,
                    owner_revision,
                )
                resolution = (
                    resolve_route_dependencies(transaction, owner)
                    if owner is not None
                    else None
                )
            else:
                owner = transaction.ai.templates.get_by_id(
                    transaction.session,
                    owner_id,
                )
                resolution = (
                    resolve_template_dependencies(transaction, owner)
                    if owner is not None
                    and int(owner.version) == owner_revision
                    else None
                )
            if resolution is None:
                raise DomainError(
                    ErrorCode.AI_DEPENDENCY_INVALID,
                    "指定的 AI 配置版本不存在",
                    status_code=404,
                )
            existing = transaction.ai.dependency_snapshots.get_owner(
                transaction.session,
                owner_type=owner_type,
                owner_id=owner_id,
                owner_revision=owner_revision,
            )
            if (
                existing is not None
                and existing.content_hash == resolution.content_hash
            ):
                return dependency_snapshot_to_dto(existing)
            return {
                "id": f"preview_{resolution.content_hash[:24]}",
                "ownerType": owner_type,
                "ownerId": owner_id,
                "ownerRevision": owner_revision,
                "status": resolution.status,
                "contentHash": resolution.content_hash,
                "issues": list(resolution.issues),
                "repairActions": list(resolution.repair_actions),
                "createdAt": utc_now(),
            }


__all__ = ["AIDependencyPreviewService", "DependencyOwnerType"]
