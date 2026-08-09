from __future__ import annotations

from typing import get_args

from sqlalchemy.dialects import sqlite

from repositories.account_connection_v1_repository import (
    _binding_candidates_query,
)
from schemas.v1.account_common import AccountDto
from schemas.v1.accounts import (
    AccountWorkspaceRouteId,
    BrowserInstanceSummaryDto,
    ConnectionCandidateDto,
    DeviceWorkspaceSummaryDto,
    ExecutionBindingSummaryDto,
)

_ACCOUNT_WORKSPACE_ROUTE_IDS = {
    "account_workspace_home",
    "account_strategy_knowledge",
    "account_script_topic",
    "account_storyboard_planning",
    "account_video_deconstruction",
    "account_batch_production",
    "account_content_library",
    "account_media_toolbox",
    "account_publishing",
    "account_review",
}


def test_account_dto_exposes_positioning_and_usage_without_optional_drift() -> None:
    fields = AccountDto.model_fields

    assert "positioningSummary" in fields
    assert fields["positioningSummary"].is_required()
    assert "lastUsedAt" in fields
    assert fields["lastUsedAt"].is_required()


def test_workspace_navigation_routes_are_closed_to_the_ten_account_entries() -> None:
    assert set(get_args(AccountWorkspaceRouteId)) == (
        _ACCOUNT_WORKSPACE_ROUTE_IDS
    )


def test_connection_candidate_dto_contains_only_safe_summaries() -> None:
    serialized_fields = set(ConnectionCandidateDto.model_fields)

    assert serialized_fields == {
        "deviceWorkspace",
        "browserInstance",
        "executionBinding",
        "environmentId",
        "eligibilityRevision",
    }
    nested_fields = (
        set(DeviceWorkspaceSummaryDto.model_fields)
        | set(BrowserInstanceSummaryDto.model_fields)
        | set(ExecutionBindingSummaryDto.model_fields)
    )
    banned_fields = {
        "rootPath",
        "profilePath",
        "metadata",
        "metadataJson",
        "credentialRef",
        "sessionRef",
        "executablePath",
    }
    assert banned_fields.isdisjoint(nested_fields)


def test_candidate_query_requires_complete_account_evidence_chain() -> None:
    compiled = _binding_candidates_query("account-a").compile(
        dialect=sqlite.dialect(),
        compile_kwargs={"literal_binds": True},
    )
    sql = " ".join(str(compiled).lower().split())

    required = {
        "execution_bindings.account_id = 'account-a'",
        "device_workspaces.account_id = 'account-a'",
        "browser_instances.account_id = 'account-a'",
        "execution_bindings.device_workspace_id = device_workspaces.id",
        "execution_bindings.browser_instance_id = browser_instances.id",
        "browser_instances.workspace_id = device_workspaces.id",
    }
    assert all(fragment in sql for fragment in required)
