from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_MODULE = REPOSITORY_ROOT / "scripts" / "release-source-snapshot.mjs"


def test_source_snapshot_detects_content_change_with_unchanged_git_status(
    tmp_path: Path,
) -> None:
    _initialize_repository(tmp_path)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("first\n", encoding="utf-8")
    first = _snapshot(tmp_path)
    tracked.write_text("second\n", encoding="utf-8")
    second = _snapshot(tmp_path)

    assert first["statusSha256"] == second["statusSha256"]
    assert first["trackedDiffSha256"] != second["trackedDiffSha256"]
    assert first["sourceSnapshotSha256"] != second["sourceSnapshotSha256"]


def test_source_snapshot_binds_untracked_file_content(tmp_path: Path) -> None:
    _initialize_repository(tmp_path)
    untracked = tmp_path / "evidence.json"
    untracked.write_text('{"result":"first"}\n', encoding="utf-8")
    first = _snapshot(tmp_path)
    untracked.write_text('{"result":"second"}\n', encoding="utf-8")
    second = _snapshot(tmp_path)

    assert first["statusSha256"] == second["statusSha256"]
    assert first["untrackedContentSha256"] != second["untrackedContentSha256"]
    assert first["sourceSnapshotSha256"] != second["sourceSnapshotSha256"]


def test_production_evidence_policy_contains_all_hardening_gates() -> None:
    policy_module = REPOSITORY_ROOT / "scripts" / "release-evidence-policy.mjs"
    script = (
        f'import {{ productionTestIds }} from {json.dumps(policy_module.as_uri())};'
        "process.stdout.write(JSON.stringify(productionTestIds));"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert set(json.loads(result.stdout)) == {
        "runtime-full",
        "desktop-active",
        "desktop-typecheck",
        "rust-tauri",
        "playwright-first-run",
        "playwright-account-workspace",
        "sidecar-smoke",
        "windows-gui-smoke",
        "windows-installer-smoke",
        "packaged-license-activation",
        "target-tiktok-supervised-login",
    }


def test_gui_smoke_evidence_binds_desktop_and_portable_artifacts() -> None:
    policy_module = REPOSITORY_ROOT / "scripts" / "release-evidence-policy.mjs"
    script = (
        f'import {{ artifactBoundEvidence }} from {json.dumps(policy_module.as_uri())};'
        'process.stdout.write(JSON.stringify(artifactBoundEvidence["windows-gui-smoke"]));'
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert json.loads(result.stdout) == ["desktop", "portable"]


def _initialize_repository(directory: Path) -> None:
    _git(directory, "init")
    _git(directory, "config", "user.email", "manifest-test@example.invalid")
    _git(directory, "config", "user.name", "Manifest Test")
    (directory / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(directory, "add", "tracked.txt")
    _git(directory, "commit", "-m", "baseline")


def _snapshot(directory: Path) -> dict[str, object]:
    script = (
        f'import {{ collectSourceSnapshot }} from {json.dumps(SNAPSHOT_MODULE.as_uri())};'
        f"process.stdout.write(JSON.stringify(collectSourceSnapshot({json.dumps(str(directory))})));"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPOSITORY_ROOT,
    )
    return json.loads(result.stdout)


def _git(directory: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *arguments],
        check=True,
        capture_output=True,
        cwd=directory,
    )
