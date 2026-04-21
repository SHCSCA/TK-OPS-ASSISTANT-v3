from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.account_repository import AccountRepository
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from schemas.accounts import AccountCreateInput, AccountUpdateInput, AccountBindingUpsertInput
from schemas.device_workspaces import DeviceWorkspaceCreateInput, DeviceWorkspaceUpdateInput
from services.account_service import AccountService
from services.device_workspace_service import DeviceWorkspaceService


def _make_services(tmp_path: Path) -> tuple[AccountService, DeviceWorkspaceService, AccountRepository, DeviceWorkspaceRepository]:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    account_repository = AccountRepository(session_factory=session_factory)
    device_repository = DeviceWorkspaceRepository(session_factory=session_factory)
    return (
        AccountService(account_repository, binding_repository=device_repository),
        DeviceWorkspaceService(device_repository),
        account_repository,
        device_repository,
    )


@pytest.mark.asyncio
async def test_account_binding_upsert_masks_sensitive_metadata(tmp_path: Path) -> None:
    account_service, device_service, account_repository, _ = _make_services(tmp_path)
    account = account_service.create_account(AccountCreateInput(name="Creator A"))
    workspace = device_service.create_workspace(
        DeviceWorkspaceCreateInput(name="Main Browser", root_path=str(tmp_path / "browser"))
    )

    binding = account_service.upsert_binding(
        account.id,
        AccountBindingUpsertInput(
            browserInstanceId=workspace.id,
            status="active",
            source="manual",
            metadataJson='{"cookie":"abc","token":"secret","note":"ok"}',
        ),
    )

    assert binding.accountId == account.id
    assert binding.browserInstanceId == workspace.id
    assert binding.maskedMetadataJson is not None
    assert "abc" not in binding.maskedMetadataJson
    assert "secret" not in binding.maskedMetadataJson

    stored = account_service.get_binding(account.id)
    assert stored.accountId == account.id


@pytest.mark.asyncio
async def test_account_status_change_broadcasts_websocket_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account_service, _, _, _ = _make_services(tmp_path)
    broadcast_calls: list[dict[str, object]] = []

    async def _broadcast(message: dict[str, object]) -> None:
        broadcast_calls.append(message)

    monkeypatch.setattr("services.account_service.ws_manager.broadcast", _broadcast)

    account = account_service.create_account(AccountCreateInput(name="Creator B", status="active"))
    updated = account_service.update_account(
        account.id,
        AccountUpdateInput(status="paused"),
    )
    assert updated.status == "paused"

    await asyncio.sleep(0.05)
    assert broadcast_calls
    event = broadcast_calls[0]
    assert event["type"] == "account.status.changed"
    assert event["accountId"] == account.id
    assert event["status"] == "paused"


@pytest.mark.asyncio
async def test_workspace_status_change_broadcasts_and_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, device_service, _, _ = _make_services(tmp_path)
    broadcast_calls: list[dict[str, object]] = []

    async def _broadcast(message: dict[str, object]) -> None:
        broadcast_calls.append(message)

    monkeypatch.setattr("services.device_workspace_service.ws_manager.broadcast", _broadcast)

    workspace_root = tmp_path / "ws"
    workspace_root.mkdir()
    workspace = device_service.create_workspace(
        DeviceWorkspaceCreateInput(name="Workstation", root_path=str(workspace_root))
    )
    updated = device_service.update_workspace(
        workspace.id,
        DeviceWorkspaceUpdateInput(status="ready"),
    )
    assert updated.status == "ready"

    await asyncio.sleep(0.05)
    assert broadcast_calls
    assert broadcast_calls[0]["type"] == "device.status.changed"
    assert broadcast_calls[0]["workspaceId"] == workspace.id

    health = device_service.health_check(workspace.id)
    assert health.status == "ready"

    logs = device_service.list_logs(workspace.id)
    assert len(logs) >= 1
    assert any("健康" in entry.message or "health" in entry.message.lower() for entry in logs)


def test_account_publish_readiness_requires_username_before_publish(tmp_path: Path) -> None:
    account_service, _, _, _ = _make_services(tmp_path)

    account = account_service.create_account(
        AccountCreateInput(name="Creator C", status="active")
    )

    assert account.publishReadiness.canPublish is False
    assert account.publishReadiness.status == "action_required"
    assert account.publishReadiness.errorCode == "account.username_missing"
    assert account.publishReadiness.lastValidatedAt is None

    refreshed = account_service.refresh_stats(account.id)
    assert refreshed.publishReadiness.lastValidatedAt is not None
    assert refreshed.publishReadiness.status == "action_required"


def test_account_publish_readiness_reports_ready_with_active_binding(tmp_path: Path) -> None:
    account_service, device_service, _, _ = _make_services(tmp_path)
    workspace_root = tmp_path / "workspace-ready"
    workspace_root.mkdir()
    workspace = device_service.create_workspace(
        DeviceWorkspaceCreateInput(name="Ready Workspace", root_path=str(workspace_root))
    )
    account = account_service.create_account(
        AccountCreateInput(
            name="Creator D",
            status="active",
            username="creator_d",
            authExpiresAt="2099-01-01T00:00:00Z",
        )
    )

    account_service.upsert_binding(
        account.id,
        AccountBindingUpsertInput(
            browserInstanceId=workspace.id,
            status="active",
            source="manual",
        ),
    )

    refreshed = account_service.refresh_stats(account.id)

    assert refreshed.publishReadiness.canPublish is True
    assert refreshed.publishReadiness.status == "ready"
    assert refreshed.publishReadiness.errorCode is None
    assert refreshed.publishReadiness.binding is not None
    assert refreshed.publishReadiness.binding.browserInstanceId == workspace.id


def test_workspace_runtime_summary_reports_missing_root_and_health_error(
    tmp_path: Path,
) -> None:
    _, device_service, _, _ = _make_services(tmp_path)
    workspace = device_service.create_workspace(
        DeviceWorkspaceCreateInput(
            name="Broken Workspace",
            root_path=str(tmp_path / "missing-root"),
        )
    )

    summary = device_service.get_workspace(workspace.id)
    assert summary.environmentStatus.status == "missing_root"
    assert summary.environmentStatus.errorCode == "workspace.root_path_missing"
    assert summary.healthSummary.status == "unknown"

    health = device_service.health_check(workspace.id)
    assert health.status == "error"
    assert health.errorCode == "workspace.root_path_missing"
    assert health.environmentStatus.status == "missing_root"
    assert health.bindingSummary.totalBindings == 0


def test_workspace_runtime_summary_reports_bindings_and_ready_without_browser(
    tmp_path: Path,
) -> None:
    account_service, device_service, _, _ = _make_services(tmp_path)
    workspace_root = tmp_path / "workspace-no-browser"
    workspace_root.mkdir()
    workspace = device_service.create_workspace(
        DeviceWorkspaceCreateInput(
            name="Workspace No Browser",
            root_path=str(workspace_root),
        )
    )
    account = account_service.create_account(
        AccountCreateInput(
            name="Creator E",
            status="active",
            username="creator_e",
        )
    )
    account_service.upsert_binding(
        account.id,
        AccountBindingUpsertInput(
            browserInstanceId=workspace.id,
            status="active",
            source="manual",
        ),
    )

    summary = device_service.get_workspace(workspace.id)
    assert summary.environmentStatus.status == "ready_without_browser"
    assert summary.bindingSummary.totalBindings == 1
    assert summary.bindingSummary.activeBindings == 1
    assert summary.bindingSummary.accountIds == [account.id]

    health = device_service.health_check(workspace.id)
    assert health.status == "ready"
    assert health.environmentStatus.status == "ready_without_browser"
    assert health.bindingSummary.activeBindings == 1
