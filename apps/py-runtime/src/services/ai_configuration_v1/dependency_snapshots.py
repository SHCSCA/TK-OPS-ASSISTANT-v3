from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import uuid4

from domain.models.ai_execution_snapshot import AIDependencySnapshot
from errors import DomainError, ErrorCode
from services.ai_execution_v1.dependency_graph import DependencyResolution

from .json_codec import content_hash, dump_json, load_list
from .mutation_helpers import utc_now
from .unit_of_work import AIConfigurationTransaction


def persist_dependency_snapshot(
    transaction: AIConfigurationTransaction,
    *,
    owner_type: str,
    owner_id: str,
    owner_revision: int,
    resolution: DependencyResolution,
) -> AIDependencySnapshot:
    existing = transaction.ai.dependency_snapshots.get_owner(
        transaction.session,
        owner_type=owner_type,
        owner_id=owner_id,
        owner_revision=owner_revision,
    )
    if existing is not None:
        if existing.content_hash != resolution.content_hash:
            raise DomainError(
                ErrorCode.AI_DEPENDENCY_INVALID,
                "依赖已变化，请创建新的配置版本后重新校验",
                status_code=409,
            )
        return existing
    return transaction.ai.dependency_snapshots.add(
        transaction.session,
        AIDependencySnapshot(
            id=f"deps_{uuid4().hex}",
            owner_type=owner_type,
            owner_id=owner_id,
            owner_revision=owner_revision,
            status=resolution.status,
            graph_json=dump_json(resolution.graph),
            issues_json=dump_json(list(resolution.issues)),
            repair_actions_json=dump_json(list(resolution.repair_actions)),
            content_hash=resolution.content_hash,
            created_at=utc_now(),
        ),
    )


def require_unchanged_dependency_snapshot(
    transaction: AIConfigurationTransaction,
    *,
    snapshot_id: str | None,
    current: DependencyResolution,
) -> AIDependencySnapshot:
    if snapshot_id is None:
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "配置尚未生成依赖快照",
            status_code=409,
        )
    snapshot = transaction.ai.dependency_snapshots.get(
        transaction.session,
        snapshot_id,
    )
    if snapshot is None or snapshot.status != "valid":
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "配置依赖快照无效",
            status_code=409,
        )
    if current.status != "valid" or snapshot.content_hash != current.content_hash:
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "配置依赖已变化，请重新创建版本并校验",
            status_code=409,
            meta={"repairActions": dependency_snapshot_to_dto(snapshot)["repairActions"]},
        )
    return snapshot


def validation_resolution(
    *,
    owner_type: str,
    owner_id: str,
    owner_revision: int,
    graph: Mapping[str, object],
    issues: Sequence[Mapping[str, object]],
) -> DependencyResolution:
    normalized_issues = tuple(
        _normalize_issue(item, owner_type=owner_type, owner_id=owner_id)
        for item in issues
    )
    actions = tuple(_repair_actions(normalized_issues))
    status = (
        "invalid"
        if any(bool(item["blocking"]) for item in normalized_issues)
        else "valid"
    )
    normalized_graph = {
        "ownerType": owner_type,
        "ownerId": owner_id,
        "ownerRevision": owner_revision,
        **dict(graph),
    }
    digest = content_hash(
        {
            "status": status,
            "graph": normalized_graph,
            "issues": normalized_issues,
            "repairActions": actions,
        }
    )
    return DependencyResolution(
        graph=normalized_graph,
        issues=normalized_issues,
        repair_actions=actions,
        status=status,
        content_hash=digest,
    )


def dependency_snapshot_to_dto(
    row: AIDependencySnapshot,
) -> dict[str, object]:
    return {
        "id": row.id,
        "ownerType": row.owner_type,
        "ownerId": row.owner_id,
        "ownerRevision": int(row.owner_revision),
        "status": row.status,
        "contentHash": row.content_hash,
        "issues": load_list(row.issues_json, label="AI 依赖问题"),
        "repairActions": load_list(
            row.repair_actions_json,
            label="AI 依赖修复动作",
        ),
        "createdAt": row.created_at,
    }


def _normalize_issue(
    issue: Mapping[str, object],
    *,
    owner_type: str,
    owner_id: str,
) -> dict[str, object]:
    return {
        "code": str(issue.get("code", "AI_DEPENDENCY_INVALID")),
        "severity": str(issue.get("severity", "error")),
        "nodeType": str(issue.get("nodeType", owner_type)),
        "nodeId": issue.get("nodeId", owner_id),
        "path": str(issue.get("path", issue.get("field", ""))),
        "message": str(issue.get("message", "AI 依赖无效")),
        "blocking": bool(issue.get("blocking", True)),
        "evidenceRef": issue.get("evidenceRef"),
    }


def _repair_actions(
    issues: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    seen: set[str] = set()
    for issue in issues:
        code = str(issue["code"])
        if code in seen:
            continue
        seen.add(code)
        actions.append(
            {
                "kind": "navigate",
                "label": "修复 AI 依赖",
                "targetPage": "ai-system-settings",
                "targetSection": "dependencies",
                "targetResourceId": issue.get("nodeId"),
                "requiredAccountId": None,
            }
        )
    return actions


__all__ = [
    "dependency_snapshot_to_dto",
    "persist_dependency_snapshot",
    "require_unchanged_dependency_snapshot",
    "validation_resolution",
]
