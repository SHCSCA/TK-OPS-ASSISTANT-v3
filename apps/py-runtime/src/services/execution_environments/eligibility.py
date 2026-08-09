from __future__ import annotations

import json

from common.time import utc_now_iso
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentAggregate,
)
from schemas.v1.execution_environments import (
    EligibilityIssueDto,
    ExecutionEnvironmentEligibilityDto,
)


def evaluate_environment(
    aggregate: ExecutionEnvironmentAggregate,
) -> ExecutionEnvironmentEligibilityDto:
    issues: list[EligibilityIssueDto] = []
    if aggregate.workspace.ownership_state != "owned":
        issues.append(
            EligibilityIssueDto(
                code="WORKSPACE_ROOT_REAUTHORIZATION_REQUIRED",
                message="工作目录需要重新授权。",
                recoveryAction="reauthorize_root",
            )
        )
    if aggregate.workspace.status != "ready":
        issues.append(
            EligibilityIssueDto(
                code="WORKSPACE_NOT_READY",
                message="账号工作目录尚未就绪。",
                recoveryAction="check_environment",
            )
        )
    if aggregate.browser.status != "running":
        issues.append(
            EligibilityIssueDto(
                code="BROWSER_NOT_RUNNING",
                message="浏览器尚未运行。",
                recoveryAction="start_environment",
            )
        )
    if not _ownership_verified(aggregate.browser.runtime_evidence_json):
        issues.append(
            EligibilityIssueDto(
                code="BROWSER_PROCESS_OWNERSHIP_UNPROVEN",
                message="浏览器进程所有权尚未验证。",
                recoveryAction="check_environment",
            )
        )
    return ExecutionEnvironmentEligibilityDto(
        eligible=not issues,
        blockingIssues=issues,
        checkedAt=utc_now_iso(),
        evidenceRevision=max(
            1,
            int(aggregate.binding.revision)
            + int(aggregate.browser.revision)
            + int(aggregate.workspace.revision),
        ),
    )


def _ownership_verified(raw: str | None) -> bool:
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return False
    return (
        isinstance(payload, dict)
        and payload.get("schemaVersion") == 1
        and payload.get("ownerMarkerVersion") == 1
        and payload.get("debugHost") == "127.0.0.1"
    )
