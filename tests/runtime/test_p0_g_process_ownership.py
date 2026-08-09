from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.browser_runtime import BrowserLaunchResult
from services.execution_environments.browser_process import (
    BrowserProcessOwnershipError,
    BrowserProcessOwnershipService,
)


def test_browser_ownership_requires_process_command_port_and_marker(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "chrome.exe"
    executable.write_bytes(b"browser")
    profile = tmp_path / "browser-profile"
    profile.mkdir()
    process = FakeProcess(executable, profile)
    service = BrowserProcessOwnershipService(
        runtime_generation="generation-1",
        process_factory=lambda _pid: process,
    )
    nonce = service.create_marker(
        account_id="account-a",
        browser_instance_id="browser-a",
        profile_path=profile,
    )

    evidence = service.verify_launch(
        account_id="account-a",
        browser_instance_id="browser-a",
        profile_path=profile,
        nonce=nonce,
        launch=BrowserLaunchResult(
            process_id=4321,
            debug_host="127.0.0.1",
            debug_port=49152,
            executable_path=str(executable),
        ),
    )

    payload = json.loads(evidence.to_json())
    assert payload["processId"] == 4321
    assert payload["debugPort"] == 49152
    assert str(profile) not in evidence.to_json()
    assert str(executable) not in evidence.to_json()


def test_browser_ownership_rejects_pid_reuse_or_wrong_profile(tmp_path: Path) -> None:
    executable = tmp_path / "chrome.exe"
    executable.write_bytes(b"browser")
    profile = tmp_path / "browser-profile"
    other_profile = tmp_path / "other-profile"
    profile.mkdir()
    other_profile.mkdir()
    process = FakeProcess(executable, other_profile)
    service = BrowserProcessOwnershipService(
        runtime_generation="generation-1",
        process_factory=lambda _pid: process,
    )
    nonce = service.create_marker(
        account_id="account-a",
        browser_instance_id="browser-a",
        profile_path=profile,
    )

    with pytest.raises(BrowserProcessOwnershipError):
        service.verify_launch(
            account_id="account-a",
            browser_instance_id="browser-a",
            profile_path=profile,
            nonce=nonce,
            launch=BrowserLaunchResult(
                process_id=4321,
                debug_host="127.0.0.1",
                debug_port=49152,
                executable_path=str(executable),
            ),
        )


class FakeProcess:
    pid = 4321

    def __init__(self, executable: Path, profile: Path) -> None:
        self._executable = executable
        self._profile = profile

    def cmdline(self) -> list[str]:
        return [
            str(self._executable),
            f"--user-data-dir={self._profile}",
            "--remote-debugging-port=49152",
        ]

    def create_time(self) -> float:
        return 1_787_000_000.0

    def exe(self) -> str:
        return str(self._executable)

    def net_connections(self, kind: str):
        assert kind == "tcp"
        return [
            SimpleNamespace(
                laddr=SimpleNamespace(ip="127.0.0.1", port=49152)
            )
        ]
