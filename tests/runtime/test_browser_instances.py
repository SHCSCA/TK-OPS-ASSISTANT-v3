from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from schemas.device_workspaces import DeviceWorkspaceCreateInput
from services.device_workspace_service import DeviceWorkspaceService


def _make_service(tmp_path: Path) -> DeviceWorkspaceService:
    engine = create_runtime_engine(tmp_path / 'runtime.db')
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repository = DeviceWorkspaceRepository(session_factory=session_factory)
    return DeviceWorkspaceService(repository)


@pytest.mark.asyncio
async def test_browser_instance_lifecycle_requires_real_workspace_and_profile_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_service(tmp_path)
    broadcast_calls: list[dict[str, object]] = []

    async def _broadcast(message: dict[str, object]) -> None:
        broadcast_calls.append(message)

    monkeypatch.setattr('services.device_workspace_service.ws_manager.broadcast', _broadcast)

    workspace_root = tmp_path / 'workspace-browser-runtime'
    workspace_root.mkdir(parents=True, exist_ok=True)
    workspace = service.create_workspace(
        DeviceWorkspaceCreateInput(name='Runtime Workspace', root_path=str(workspace_root))
    )

    created = service.create_browser_instance(
        workspace.id,
        name='Runtime Browser',
        profile_path=str(workspace_root / 'profiles' / 'runtime-browser'),
    )
    assert created.workspaceId == workspace.id
    assert created.status == 'stopped'
    assert Path(created.profilePath).exists()

    started = service.start_browser_instance(workspace.id, created.id)
    assert started.browserInstance.status == 'running'

    checked = service.health_check_browser_instance(workspace.id, created.id)
    assert checked.browserInstance.status == 'ready'
    assert checked.browserInstance.lastCheckedAt is not None

    stopped = service.stop_browser_instance(workspace.id, created.id)
    assert stopped.browserInstance.status == 'stopped'

    items = service.list_browser_instances(workspace.id)
    assert [item.id for item in items] == [created.id]

    await asyncio.sleep(0.05)
    assert broadcast_calls
    assert any(item['type'] == 'browser-instance.status.changed' for item in broadcast_calls)
