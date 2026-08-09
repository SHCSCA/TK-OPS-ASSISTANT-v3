from __future__ import annotations

from datetime import UTC, datetime

from errors import ErrorCode
from repositories.account_connection_v1_repository import (
    AccountConnectionResources,
    ExecutionBindingResources,
)
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentAggregate,
)
from schemas.v1.accounts import (
    BrowserInstanceSummaryDto,
    ConnectionCandidateDto,
    ConnectionCheckSummaryDto,
    ConnectionDto,
    DeviceWorkspaceSummaryDto,
    ExecutionBindingSummaryDto,
)
from services.execution_environments.eligibility import evaluate_environment


def connection_candidate_to_dto(
    resources: ExecutionBindingResources,
) -> ConnectionCandidateDto:
    workspace = resources.device_workspace
    browser = resources.browser_instance
    binding = resources.execution_binding
    eligibility = evaluate_environment(
        ExecutionEnvironmentAggregate(binding, browser, workspace)
    )
    return ConnectionCandidateDto(
        environmentId=binding.id,
        eligibilityRevision=eligibility.evidenceRevision,
        deviceWorkspace=DeviceWorkspaceSummaryDto(
            id=workspace.id,
            name=workspace.name,
            status=workspace.status,
        ),
        browserInstance=BrowserInstanceSummaryDto(
            id=browser.id,
            name=browser.name,
            status=browser.status,
            lastCheckedAt=_optional_datetime_text(browser.last_checked_at),
        ),
        executionBinding=ExecutionBindingSummaryDto(
            id=binding.id,
            status=binding.status,
            deviceWorkspaceId=binding.device_workspace_id,
            browserInstanceId=browser.id,
        ),
    )


def connection_to_dto(
    account_id: str,
    resources: AccountConnectionResources | None,
    *,
    account_revision: int,
) -> ConnectionDto:
    if resources is None:
        return ConnectionDto(
            accountId=account_id,
            authStatus="required",
            healthStatus="unknown",
            deviceWorkspace=None,
            browserInstance=None,
            executionBinding=None,
            lastCheck=None,
            revision=account_revision,
        )
    connection = resources.connection
    workspace = resources.device_workspace
    browser = resources.browser_instance
    binding = resources.execution_binding
    evidence_missing = (
        connection.active_execution_binding_id is not None
        and (workspace is None or browser is None or binding is None)
    )
    return ConnectionDto(
        accountId=account_id,
        authStatus=connection.auth_status,
        healthStatus=connection.health_status,
        deviceWorkspace=(
            None
            if workspace is None
            else DeviceWorkspaceSummaryDto(
                id=workspace.id,
                name=workspace.name,
                status=workspace.status,
            )
        ),
        browserInstance=(
            None
            if browser is None
            else BrowserInstanceSummaryDto(
                id=browser.id,
                name=browser.name,
                status=browser.status,
                lastCheckedAt=_optional_datetime_text(
                    browser.last_checked_at
                ),
            )
        ),
        executionBinding=(
            None
            if binding is None or binding.browser_instance_id is None
            else ExecutionBindingSummaryDto(
                id=binding.id,
                status=binding.status,
                deviceWorkspaceId=binding.device_workspace_id,
                browserInstanceId=binding.browser_instance_id,
            )
        ),
        lastCheck=ConnectionCheckSummaryDto(
            status=(
                "attention"
                if evidence_missing
                else connection.health_status
            ),
            checkedAt=connection.last_checked_at,
            errorCode=(
                ErrorCode.EXECUTION_BINDING_INVALID.value
                if evidence_missing
                else connection.error_code
            ),
            logId=connection.error_log_id,
        ),
        revision=account_revision,
    )


def _optional_datetime_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
