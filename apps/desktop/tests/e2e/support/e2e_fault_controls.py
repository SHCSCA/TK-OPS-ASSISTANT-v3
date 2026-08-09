from __future__ import annotations

import threading

from services.browser_runtime import BrowserRuntimeError


class E2EFaultControls:
    """只在 E2E Runtime 中提供可审计、一次性的故障控制。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fail_next_browser_launch = False
        self._block_next_login_navigation = False
        self._navigation_started = threading.Event()
        self._navigation_release = threading.Event()

    def arm_browser_launch_failure(self) -> None:
        with self._lock:
            self._fail_next_browser_launch = True

    def consume_browser_launch_failure(self) -> None:
        with self._lock:
            should_fail = self._fail_next_browser_launch
            self._fail_next_browser_launch = False
        if should_fail:
            raise BrowserRuntimeError(
                "browser_instance.launch_failed",
                "E2E 已注入一次受控浏览器启动失败。",
            )

    def arm_login_navigation_block(self) -> None:
        with self._lock:
            self._block_next_login_navigation = True
            self._navigation_started.clear()
            self._navigation_release.clear()

    def wait_for_login_navigation(self, *, timeout_seconds: float = 30.0) -> None:
        with self._lock:
            should_block = self._block_next_login_navigation
            self._block_next_login_navigation = False
        if not should_block:
            return
        self._navigation_started.set()
        if not self._navigation_release.wait(timeout_seconds):
            raise BrowserRuntimeError(
                "browser_instance.navigation_timeout",
                "E2E 登录导航未在限定时间内释放。",
            )

    def release_login_navigation(self) -> None:
        self._navigation_release.set()

    def snapshot(self) -> dict[str, bool]:
        with self._lock:
            return {
                "browserLaunchFailureArmed": self._fail_next_browser_launch,
                "loginNavigationBlockArmed": self._block_next_login_navigation,
                "loginNavigationStarted": self._navigation_started.is_set(),
                "loginNavigationReleased": self._navigation_release.is_set(),
            }
