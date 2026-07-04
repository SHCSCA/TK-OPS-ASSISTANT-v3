from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from schemas.device_workspaces import DeviceWorkspaceCreateInput
from services.browser_runtime import (
    BrowserLaunchResult,
    BrowserRuntime,
    BrowserRuntimeError,
    BrowserRuntimeHealth,
    LocalBrowserRuntime,
)
from services.device_workspace_service import DeviceWorkspaceService


@dataclass
class FakeBrowserRuntime(BrowserRuntime):
    alive: bool = False
    last_profile_path: str | None = None
    stopped_pid: int | None = None

    def launch(self, *, profile_path: Path) -> BrowserLaunchResult:
        self.alive = True
        self.last_profile_path = str(profile_path)
        return BrowserLaunchResult(
            process_id=43210,
            debug_host="127.0.0.1",
            debug_port=59321,
            executable_path="G:/fake-browser/fake-browser.exe",
            devtools_url="http://127.0.0.1:59321/json/version",
            metadata={"profilePath": str(profile_path), "kind": "fake-process"},
        )

    def health(self, *, process_id: int | None, debug_port: int | None) -> BrowserRuntimeHealth:
        return BrowserRuntimeHealth(
            alive=self.alive and process_id == 43210 and debug_port == 59321,
            process_id=process_id,
            debug_port=debug_port,
            error_code=None if self.alive else "browser_instance.process_missing",
            error_message=None if self.alive else "浏览器进程不存在或已经退出。",
        )

    def stop(self, *, process_id: int | None) -> BrowserRuntimeHealth:
        self.stopped_pid = process_id
        self.alive = False
        return BrowserRuntimeHealth(
            alive=False,
            process_id=process_id,
            debug_port=None,
        )

    def launch_supported(self) -> bool:
        return True


class MissingBrowserRuntime(FakeBrowserRuntime):
    def launch(self, *, profile_path: Path) -> BrowserLaunchResult:
        raise BrowserRuntimeError(
            "browser_instance.executable_missing",
            "未找到可用浏览器可执行文件，请在系统设置中配置浏览器路径。",
        )

    def launch_supported(self) -> bool:
        return False


class DevtoolsUnreachableBrowserRuntime(FakeBrowserRuntime):
    def health(self, *, process_id: int | None, debug_port: int | None) -> BrowserRuntimeHealth:
        return BrowserRuntimeHealth(
            alive=False,
            process_id=process_id,
            debug_port=debug_port,
            error_code="browser_instance.devtools_unreachable",
            error_message="浏览器调试端口不可达，无法确认该实例真实可用。",
            metadata={"processAlive": True, "devtoolsReachable": False},
        )


def _make_service(
    tmp_path: Path,
    *,
    browser_runtime: BrowserRuntime | None = None,
) -> DeviceWorkspaceService:
    engine = create_runtime_engine(tmp_path / 'runtime.db')
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repository = DeviceWorkspaceRepository(session_factory=session_factory)
    return DeviceWorkspaceService(repository, browser_runtime=browser_runtime)


def test_browser_instance_lifecycle_requires_real_workspace_and_profile_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser_runtime = FakeBrowserRuntime()
    service = _make_service(tmp_path, browser_runtime=browser_runtime)
    del monkeypatch

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
    assert started.operation == 'start'
    assert started.processBoundaryVerified is True
    assert started.processSummary['alive'] is True
    assert started.browserInstance.processId == 43210
    assert started.browserInstance.debugPort == 59321
    assert started.browserInstance.runtimeMode == 'local_process'
    assert started.browserInstance.launchSupported is True

    checked = service.health_check_browser_instance(workspace.id, created.id)
    assert checked.browserInstance.status == 'ready'
    assert checked.browserInstance.lastCheckedAt is not None
    assert checked.processBoundaryVerified is True

    stopped = service.stop_browser_instance(workspace.id, created.id)
    assert stopped.browserInstance.status == 'stopped'
    assert stopped.operation == 'stop'
    assert stopped.processBoundaryVerified is True
    assert stopped.processSummary['alive'] is False
    assert stopped.browserInstance.processId is None
    assert stopped.browserInstance.debugPort is None
    assert browser_runtime.stopped_pid == 43210

    items = service.list_browser_instances(workspace.id)
    assert [item.id for item in items] == [created.id]



def test_browser_health_check_marks_running_instance_error_when_process_is_missing(
    tmp_path: Path,
) -> None:
    browser_runtime = FakeBrowserRuntime()
    service = _make_service(tmp_path, browser_runtime=browser_runtime)
    workspace_root = tmp_path / 'workspace-browser-missing-process'
    workspace_root.mkdir(parents=True, exist_ok=True)
    workspace = service.create_workspace(
        DeviceWorkspaceCreateInput(name='Runtime Workspace', root_path=str(workspace_root))
    )
    created = service.create_browser_instance(
        workspace.id,
        name='Runtime Browser',
        profile_path=str(workspace_root / 'profiles' / 'runtime-browser'),
    )
    service.start_browser_instance(workspace.id, created.id)
    browser_runtime.alive = False

    checked = service.health_check_browser_instance(workspace.id, created.id)

    assert checked.browserInstance.status == 'error'
    assert checked.browserInstance.errorCode == 'browser_instance.process_missing'
    assert checked.processBoundaryVerified is False


def test_browser_health_check_rejects_process_without_devtools(
    tmp_path: Path,
) -> None:
    browser_runtime = DevtoolsUnreachableBrowserRuntime()
    service = _make_service(tmp_path, browser_runtime=browser_runtime)
    workspace_root = tmp_path / "workspace-browser-no-devtools"
    workspace_root.mkdir(parents=True, exist_ok=True)
    workspace = service.create_workspace(
        DeviceWorkspaceCreateInput(name="Runtime Workspace", root_path=str(workspace_root))
    )
    created = service.create_browser_instance(
        workspace.id,
        name="Runtime Browser",
        profile_path=str(workspace_root / "profiles" / "runtime-browser"),
    )
    service.start_browser_instance(workspace.id, created.id)

    checked = service.health_check_browser_instance(workspace.id, created.id)

    assert checked.browserInstance.status == "error"
    assert checked.browserInstance.errorCode == "browser_instance.devtools_unreachable"
    assert checked.processBoundaryVerified is False


def test_browser_start_does_not_mark_running_when_executable_is_missing(
    tmp_path: Path,
) -> None:
    service = _make_service(tmp_path, browser_runtime=MissingBrowserRuntime())
    workspace_root = tmp_path / 'workspace-browser-no-executable'
    workspace_root.mkdir(parents=True, exist_ok=True)
    workspace = service.create_workspace(
        DeviceWorkspaceCreateInput(name='Runtime Workspace', root_path=str(workspace_root))
    )
    created = service.create_browser_instance(
        workspace.id,
        name='Runtime Browser',
        profile_path=str(workspace_root / 'profiles' / 'runtime-browser'),
    )

    started = service.start_browser_instance(workspace.id, created.id)

    assert started.browserInstance.status == 'error'
    assert started.browserInstance.errorCode == 'browser_instance.executable_missing'
    assert started.browserInstance.launchSupported is False
    assert started.browserInstance.processId is None
    assert started.processBoundaryVerified is False


def test_local_browser_runtime_requires_devtools_port_for_health() -> None:
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    runtime = LocalBrowserRuntime()
    try:
        health = runtime.health(process_id=process.pid, debug_port=9)
    finally:
        process.terminate()
        process.wait(timeout=5)

    assert health.alive is False
    assert health.error_code == "browser_instance.devtools_unreachable"
    assert health.metadata["processAlive"] is True
    assert health.metadata["devtoolsReachable"] is False


def test_local_browser_runtime_maps_immediate_exit_to_launch_failed(tmp_path: Path) -> None:
    runtime = LocalBrowserRuntime(
        executable_path_provider=lambda: sys.executable,
        startup_grace_seconds=0.1,
    )

    with pytest.raises(BrowserRuntimeError) as exc_info:
        runtime.launch(profile_path=tmp_path / "profile")

    assert exc_info.value.error_code == "browser_instance.launch_failed"
