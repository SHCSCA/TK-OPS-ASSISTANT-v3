from __future__ import annotations

import json
import logging
import os
import signal
import socket
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from urllib.error import URLError
from urllib.request import urlopen

log = logging.getLogger(__name__)


class BrowserRuntimeError(RuntimeError):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass
class BrowserLaunchResult:
    process_id: int
    debug_host: str
    debug_port: int
    executable_path: str
    devtools_url: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class BrowserRuntimeHealth:
    alive: bool
    process_id: int | None = None
    debug_port: int | None = None
    devtools_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class BrowserRuntime(Protocol):
    def launch(self, *, profile_path: Path) -> BrowserLaunchResult:
        ...

    def health(
        self,
        *,
        process_id: int | None,
        debug_port: int | None,
    ) -> BrowserRuntimeHealth:
        ...

    def stop(self, *, process_id: int | None) -> BrowserRuntimeHealth:
        ...

    def launch_supported(self) -> bool:
        ...


class LocalBrowserRuntime:
    def __init__(
        self,
        *,
        executable_path_provider: Callable[[], str | None] | None = None,
        startup_grace_seconds: float = 2.0,
    ) -> None:
        self._executable_path_provider = executable_path_provider or (lambda: None)
        self._startup_grace_seconds = startup_grace_seconds
        self._processes: dict[int, subprocess.Popen[bytes]] = {}

    def launch(self, *, profile_path: Path) -> BrowserLaunchResult:
        executable_path = self._resolve_executable_path()
        debug_port = _allocate_local_port()
        profile_path.mkdir(parents=True, exist_ok=True)
        args = [
            executable_path,
            f"--user-data-dir={profile_path}",
            f"--remote-debugging-port={debug_port}",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ]
        try:
            process = subprocess.Popen(  # noqa: S603
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            log.exception("启动浏览器进程失败")
            raise BrowserRuntimeError(
                "browser_instance.launch_failed",
                "浏览器进程启动失败，请检查浏览器路径和本机执行权限。",
            ) from exc

        self._processes[process.pid] = process
        devtools_url, devtools_metadata = self._wait_for_devtools(process, debug_port)
        if process.poll() is not None:
            self._processes.pop(process.pid, None)
            raise BrowserRuntimeError(
                "browser_instance.launch_failed",
                "浏览器进程启动后立即退出，请检查浏览器路径和 profile 目录。",
            )
        if devtools_url is None:
            self._terminate_process(process)
            self._processes.pop(process.pid, None)
            raise BrowserRuntimeError(
                "browser_instance.launch_failed",
                "浏览器进程已启动，但无法连接调试端口，请检查浏览器是否支持远程调试。",
            )

        return BrowserLaunchResult(
            process_id=process.pid,
            debug_host="127.0.0.1",
            debug_port=debug_port,
            executable_path=executable_path,
            devtools_url=devtools_url,
            metadata={
                "args": args[1:],
                "profilePath": str(profile_path),
                **devtools_metadata,
            },
        )

    def health(
        self,
        *,
        process_id: int | None,
        debug_port: int | None,
    ) -> BrowserRuntimeHealth:
        if process_id is None:
            return BrowserRuntimeHealth(
                alive=False,
                error_code="browser_instance.process_missing",
                error_message="浏览器实例缺少进程 ID，无法确认真实运行状态。",
            )
        if not self._is_process_alive(process_id):
            return BrowserRuntimeHealth(
                alive=False,
                process_id=process_id,
                debug_port=debug_port,
                error_code="browser_instance.process_missing",
                error_message="浏览器进程不存在或已经退出。",
            )

        if debug_port is None:
            return BrowserRuntimeHealth(
                alive=False,
                process_id=process_id,
                error_code="browser_instance.devtools_unreachable",
                error_message="浏览器实例缺少调试端口，无法确认真实运行状态。",
                metadata={"processAlive": True, "devtoolsReachable": False},
            )

        devtools_url, metadata = self._probe_devtools(debug_port)
        if devtools_url is None:
            return BrowserRuntimeHealth(
                alive=False,
                process_id=process_id,
                debug_port=debug_port,
                error_code="browser_instance.devtools_unreachable",
                error_message="浏览器调试端口不可达，无法确认该实例真实可用。",
                metadata={"processAlive": True, **metadata},
            )
        return BrowserRuntimeHealth(
            alive=True,
            process_id=process_id,
            debug_port=debug_port,
            devtools_url=devtools_url,
            metadata={"processAlive": True, **metadata},
        )

    def stop(self, *, process_id: int | None) -> BrowserRuntimeHealth:
        if process_id is None:
            return BrowserRuntimeHealth(alive=False)
        process = self._processes.get(process_id)
        try:
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            elif self._is_process_alive(process_id):
                os.kill(process_id, signal.SIGTERM)
        except OSError as exc:
            log.exception("停止浏览器进程失败")
            return BrowserRuntimeHealth(
                alive=True,
                process_id=process_id,
                error_code="browser_instance.stop_failed",
                error_message="浏览器进程停止失败，请手动检查该工作区。",
            )
        finally:
            self._processes.pop(process_id, None)

        return BrowserRuntimeHealth(
            alive=self._is_process_alive(process_id),
            process_id=process_id,
        )

    def launch_supported(self) -> bool:
        try:
            self._resolve_executable_path()
        except BrowserRuntimeError:
            return False
        return True

    def _resolve_executable_path(self) -> str:
        configured = (self._executable_path_provider() or "").strip()
        candidates = [configured] if configured else []
        candidates.extend(_default_browser_candidates())
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if path.is_file():
                return str(path)
        raise BrowserRuntimeError(
            "browser_instance.executable_missing",
            "未找到可用浏览器可执行文件，请在系统设置中配置浏览器路径。",
        )

    def _is_process_alive(self, process_id: int) -> bool:
        process = self._processes.get(process_id)
        if process is not None:
            return process.poll() is None
        try:
            os.kill(process_id, 0)
        except OSError:
            return False
        return True

    def _wait_for_devtools(
        self,
        process: subprocess.Popen[bytes],
        debug_port: int,
    ) -> tuple[str | None, dict[str, object]]:
        deadline = time.monotonic() + self._startup_grace_seconds
        metadata: dict[str, object] = {"devtoolsReachable": False}
        while time.monotonic() <= deadline:
            if process.poll() is not None:
                return None, {"processExited": True, **metadata}
            devtools_url, metadata = self._probe_devtools(debug_port)
            if devtools_url is not None:
                return devtools_url, metadata
            time.sleep(0.05)
        return None, metadata

    def _terminate_process(self, process: subprocess.Popen[bytes]) -> None:
        try:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        except OSError:
            log.exception("清理浏览器进程失败")

    def _probe_devtools(self, debug_port: int) -> tuple[str | None, dict[str, object]]:
        url = f"http://127.0.0.1:{debug_port}/json/version"
        try:
            with urlopen(url, timeout=0.5) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError):
            return None, {"devtoolsReachable": False}
        if isinstance(payload, dict):
            websocket_url = payload.get("webSocketDebuggerUrl")
            return (
                str(websocket_url) if websocket_url else url,
                {"devtoolsReachable": True, "version": payload},
            )
        return None, {"devtoolsReachable": False}


def _allocate_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _default_browser_candidates() -> list[str]:
    program_files = [
        os.environ.get("PROGRAMFILES", ""),
        os.environ.get("PROGRAMFILES(X86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    relative_paths = [
        "Microsoft/Edge/Application/msedge.exe",
        "Google/Chrome/Application/chrome.exe",
        "Chromium/Application/chrome.exe",
    ]
    candidates: list[str] = []
    for root in program_files:
        if not root:
            continue
        for relative_path in relative_paths:
            candidates.append(str(Path(root) / relative_path))
    return candidates
