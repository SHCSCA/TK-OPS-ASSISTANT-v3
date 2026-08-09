from __future__ import annotations

import json
import logging
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from services.browser_runtime import (
    BrowserLaunchResult,
    BrowserRuntimeError,
    BrowserRuntimeHealth,
)

from e2e_fault_controls import E2EFaultControls

log = logging.getLogger(__name__)


class E2EControlledBrowserRuntime:
    """启动可审计的本地测试进程，避免依赖测试机浏览器状态。"""

    def __init__(
        self,
        *,
        fault_controls: E2EFaultControls | None = None,
        startup_timeout_seconds: float = 5.0,
    ) -> None:
        self._fault_controls = fault_controls
        self._startup_timeout_seconds = startup_timeout_seconds
        self._processes: dict[int, subprocess.Popen[bytes]] = {}
        self._python_executable = Path(
            getattr(sys, "_base_executable", sys.executable)
        ).resolve(strict=True)
        self._helper_path = Path(__file__).with_name(
            "controlled_browser_process.py"
        )

    def launch(self, *, profile_path: Path) -> BrowserLaunchResult:
        if self._fault_controls is not None:
            self._fault_controls.consume_browser_launch_failure()
        profile_path.mkdir(parents=True, exist_ok=True)
        debug_port = _allocate_local_port()
        command = [
            str(self._python_executable),
            str(self._helper_path),
            f"--user-data-dir={profile_path}",
            f"--remote-debugging-port={debug_port}",
        ]
        try:
            process = subprocess.Popen(  # noqa: S603
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if sys.platform == "win32"
                    else 0
                ),
            )
            self._processes[process.pid] = process
            devtools_url = self._wait_for_ready(process, debug_port)
        except OSError as exc:
            log.exception("启动 E2E 受控浏览器进程失败")
            raise BrowserRuntimeError(
                "browser_instance.launch_failed",
                "E2E 受控浏览器进程启动失败。",
            ) from exc
        if devtools_url is None:
            self._terminate(process)
            raise BrowserRuntimeError(
                "browser_instance.launch_failed",
                "E2E 受控浏览器未在限定时间内就绪。",
            )
        return BrowserLaunchResult(
            process_id=process.pid,
            debug_host="127.0.0.1",
            debug_port=debug_port,
            executable_path=str(self._python_executable),
            devtools_url=devtools_url,
            metadata={"kind": "e2e-controlled-process"},
        )

    def health(
        self,
        *,
        process_id: int | None,
        debug_port: int | None,
    ) -> BrowserRuntimeHealth:
        process = self._processes.get(process_id or -1)
        alive = (
            process is not None
            and process.poll() is None
            and debug_port is not None
            and _probe_devtools(debug_port) is not None
        )
        return BrowserRuntimeHealth(
            alive=alive,
            process_id=process_id,
            debug_port=debug_port,
            devtools_url=(
                _probe_devtools(debug_port)
                if alive and debug_port is not None
                else None
            ),
            error_code=(
                None if alive else "browser_instance.process_missing"
            ),
            error_message=(
                None if alive else "E2E 受控浏览器进程不存在或不可达。"
            ),
        )

    def stop(self, *, process_id: int | None) -> BrowserRuntimeHealth:
        process = self._processes.pop(process_id or -1, None)
        if process is not None:
            self._terminate(process)
        return BrowserRuntimeHealth(
            alive=process is not None and process.poll() is None,
            process_id=process_id,
        )

    def launch_supported(self) -> bool:
        return self._helper_path.is_file() and self._python_executable.is_file()

    def navigate(self, *, debug_port: int, url: str) -> None:
        if debug_port <= 0 or not url.startswith("https://www.tiktok.com/"):
            raise BrowserRuntimeError(
                "browser_instance.navigation_forbidden",
                "E2E 受控浏览器导航参数无效。",
            )

    def _wait_for_ready(
        self,
        process: subprocess.Popen[bytes],
        debug_port: int,
    ) -> str | None:
        deadline = time.monotonic() + self._startup_timeout_seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                return None
            devtools_url = _probe_devtools(debug_port)
            if devtools_url is not None:
                return devtools_url
            time.sleep(0.05)
        return None

    def _terminate(self, process: subprocess.Popen[bytes]) -> None:
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
        except OSError:
            log.exception("停止 E2E 受控浏览器进程失败")
        finally:
            self._processes.pop(process.pid, None)


def _allocate_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _probe_devtools(debug_port: int) -> str | None:
    try:
        with urlopen(  # noqa: S310
            f"http://127.0.0.1:{debug_port}/json/version",
            timeout=0.5,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("webSocketDebuggerUrl")
    return value if isinstance(value, str) and value else None
