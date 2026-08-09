from __future__ import annotations

import os
import sys
from pathlib import Path

RUNTIME_SOURCE = Path(__file__).resolve().parents[3] / "py-runtime" / "src"
if str(RUNTIME_SOURCE) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SOURCE))

from app.container import RuntimeDependencyOverrides
from app.factory import create_app
from e2e_browser_runtime import E2EControlledBrowserRuntime
from e2e_fault_controls import E2EFaultControls
from services.browser_runtime import BrowserRuntimeError
from services.accounts.tiktok_session_probe import TikTokSessionProbeResult


class E2ELoginBrowserNavigation:
    def __init__(self, fault_controls: E2EFaultControls) -> None:
        self._fault_controls = fault_controls

    def navigate(self, *, debug_port: int, url: str) -> None:
        if debug_port <= 0 or url != "https://www.tiktok.com/login":
            raise BrowserRuntimeError(
                "browser_instance.navigation_forbidden",
                "E2E 登录导航参数无效。",
            )
        self._fault_controls.wait_for_login_navigation()


class E2ETikTokSessionProbe:
    def probe(
        self,
        *,
        debug_port: int,
        timeout_seconds: int,
    ) -> TikTokSessionProbeResult:
        if debug_port <= 0 or timeout_seconds <= 0:
            raise RuntimeError("E2E 登录探测参数无效")
        return TikTokSessionProbeResult(
            authenticated=True,
            identity=os.environ["TK_OPS_E2E_TIKTOK_IDENTITY"],
        )

    def clear_session(
        self,
        *,
        debug_port: int,
        timeout_seconds: int,
    ) -> None:
        if debug_port <= 0 or timeout_seconds <= 0:
            raise RuntimeError("E2E 登出探测参数无效")


fault_controls = E2EFaultControls()
app = create_app(
    dependency_overrides=RuntimeDependencyOverrides(
        browser_runtime=E2EControlledBrowserRuntime(
            fault_controls=fault_controls,
        ),
        login_browser_runtime=E2ELoginBrowserNavigation(fault_controls),
        login_session_probe=E2ETikTokSessionProbe(),
    )
)


@app.post("/__e2e__/faults/browser-launch")
def arm_browser_launch_failure() -> dict[str, object]:
    fault_controls.arm_browser_launch_failure()
    return {"ok": True, "data": fault_controls.snapshot()}


@app.post("/__e2e__/faults/login-navigation/block")
def arm_login_navigation_block() -> dict[str, object]:
    fault_controls.arm_login_navigation_block()
    return {"ok": True, "data": fault_controls.snapshot()}


@app.post("/__e2e__/faults/login-navigation/release")
def release_login_navigation() -> dict[str, object]:
    fault_controls.release_login_navigation()
    return {"ok": True, "data": fault_controls.snapshot()}


@app.get("/__e2e__/faults")
def get_fault_state() -> dict[str, object]:
    return {"ok": True, "data": fault_controls.snapshot()}
