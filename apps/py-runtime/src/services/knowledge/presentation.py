from __future__ import annotations

from domain.models.knowledge import (
    AccountKnowledgeBase,
    KnowledgeSnapshot,
    KnowledgeSource,
)
from errors import DomainError, ErrorCode
from schemas.v1.knowledge import (
    KnowledgeDto,
    KnowledgeRulesPatchInput,
    KnowledgeSnapshotDto,
    KnowledgeSourceDto,
    KnowledgeSourceEvidenceDto,
)
from services.accounts.json_codec import (
    load_json_list,
    load_json_object,
)
from services.accounts.readiness import knowledge_readiness
from services.accounts.types import ReadinessItem


def knowledge_to_dto(
    account_id: str,
    knowledge_base: AccountKnowledgeBase,
    *,
    source_counts: dict[str, int],
    latest_snapshot_id: str | None,
    account_revision: int,
) -> KnowledgeDto:
    rules = _rules_from_json(knowledge_base.rules_json)
    return KnowledgeDto(
        accountId=account_id,
        rules=rules,
        rulesVersion=int(knowledge_base.rules_version),
        sourceCounts=source_counts,
        latestSnapshotId=latest_snapshot_id,
        readiness=_readiness_to_dict(
            knowledge_readiness(knowledge_base)
        ),
        revision=account_revision,
    )


def source_to_dto(source: KnowledgeSource) -> KnowledgeSourceDto:
    removed = source.deleted_at is not None
    return KnowledgeSourceDto(
        id=source.id,
        accountId=source.account_id,
        kind=source.kind,
        sourceMode=source.source_mode,
        title=source.name,
        status="removed" if removed else source.status,
        controlledRef=(
            source.source_ref if source.source_mode == "file" else None
        ),
        sourceUrl=(
            source.source_url if source.source_mode == "url" else None
        ),
        contentHash=source.content_hash,
        indexedAt=(
            source.updated_at
            if (
                source.status == "ready"
                and source.deleted_at is None
                and source.content_hash is not None
            )
            else None
        ),
        removedAt=source.deleted_at,
        errorCode=source.error_code,
        logId=source.error_log_id,
        revision=int(source.revision),
    )


def snapshot_to_dto(
    snapshot: KnowledgeSnapshot,
) -> KnowledgeSnapshotDto:
    manifest = load_json_list(
        snapshot.source_manifest_json,
        resource_label="知识快照来源清单",
    )
    evidence: list[KnowledgeSourceEvidenceDto] = []
    for item in manifest:
        if not isinstance(item, dict):
            raise _snapshot_structure_error()
        source_id = item.get("sourceId")
        content_hash = item.get("contentHash")
        indexed_revision = item.get("indexedRevision")
        if (
            not isinstance(source_id, str)
            or not isinstance(content_hash, str)
            or len(content_hash) != 64
            or isinstance(indexed_revision, bool)
            or not isinstance(indexed_revision, int)
            or indexed_revision < 1
        ):
            raise _snapshot_structure_error()
        evidence.append(
            KnowledgeSourceEvidenceDto(
                sourceId=source_id,
                contentHash=content_hash,
                indexedRevision=indexed_revision,
            )
        )
    return KnowledgeSnapshotDto(
        id=snapshot.id,
        accountId=snapshot.account_id,
        label=snapshot.label,
        sourceIds=[item.sourceId for item in evidence],
        sourceEvidence=evidence,
        rulesVersion=int(snapshot.rules_version),
        contentHash=snapshot.content_hash,
        createdAt=snapshot.created_at,
    )


def _rules_from_json(value: str) -> KnowledgeRulesPatchInput:
    rules = load_json_object(value, resource_label="知识规则")
    expected_keys = {
        "inclusionRules",
        "exclusionRules",
        "citationPolicy",
    }
    if set(rules) != expected_keys or not all(
        isinstance(rules[key], dict) for key in expected_keys
    ):
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "知识规则数据结构异常，请查看诊断日志",
            status_code=500,
            loggable=True,
        )
    return KnowledgeRulesPatchInput.model_validate(rules)


def _readiness_to_dict(item: ReadinessItem) -> dict[str, object]:
    action = item.suggested_action
    return {
        "status": item.status.value,
        "label": item.label,
        "errorCode": item.error_code,
        "logId": item.log_id,
        "checkedAt": item.checked_at,
        "suggestedAction": (
            None
            if action is None
            else {
                "actionKey": action.action_key.value,
                "label": action.label,
                "routeId": action.route_id,
                "section": action.section,
                "taskId": action.task_id,
            }
        ),
    }


def _snapshot_structure_error() -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        "知识快照来源清单损坏，请查看诊断日志",
        status_code=500,
        loggable=True,
    )
