from __future__ import annotations

import sys
from pathlib import Path

from services.execution_environments.browser_process import (
    BrowserProcessOwnershipService,
)

SUPPORT_ROOT = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "desktop"
    / "tests"
    / "e2e"
    / "support"
)
if str(SUPPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(SUPPORT_ROOT))

from e2e_browser_runtime import E2EControlledBrowserRuntime  # noqa: E402


def test_e2e_controlled_browser_passes_real_process_ownership(
    tmp_path: Path,
) -> None:
    runtime = E2EControlledBrowserRuntime()
    ownership = BrowserProcessOwnershipService(
        runtime_generation="e2e-test-generation"
    )
    profile_path = tmp_path / "browser-profile"
    nonce = ownership.create_marker(
        account_id="account-e2e",
        browser_instance_id="browser-e2e",
        profile_path=profile_path,
    )
    launch = runtime.launch(profile_path=profile_path)
    try:
        evidence = ownership.verify_launch(
            account_id="account-e2e",
            browser_instance_id="browser-e2e",
            profile_path=profile_path,
            nonce=nonce,
            launch=launch,
        )
        assert evidence.processId == launch.process_id
        assert evidence.debugPort == launch.debug_port
        assert runtime.health(
            process_id=launch.process_id,
            debug_port=launch.debug_port,
        ).alive
    finally:
        stopped = runtime.stop(process_id=launch.process_id)
        assert not stopped.alive
