from __future__ import annotations

import hashlib
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
        "p0-h-real-provider-execution",
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


def test_p0_h_real_provider_evidence_binds_all_release_artifacts() -> None:
    policy_module = REPOSITORY_ROOT / "scripts" / "release-evidence-policy.mjs"
    script = (
        f'import {{ artifactBoundEvidence }} from {json.dumps(policy_module.as_uri())};'
        'process.stdout.write(JSON.stringify('
        'artifactBoundEvidence["p0-h-real-provider-execution"]));'
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert json.loads(result.stdout) == [
        "desktop",
        "sidecar",
        "installer",
        "portable",
    ]


def test_p0_h_real_provider_evidence_accepts_only_strict_allowlist() -> None:
    evidence = _real_provider_evidence()
    assert _validate_p0_h_evidence(evidence).returncode == 0

    controlled = {**evidence, "evidenceKind": "p0h_controlled_contract"}
    assert _validate_p0_h_evidence(controlled).returncode != 0

    leaked = {**evidence, "credential": "sk-this-must-never-pass-1234567890"}
    assert _validate_p0_h_evidence(leaked).returncode != 0


def test_p0_h_real_provider_evidence_requires_pricing_revision_for_estimate() -> None:
    evidence = _real_provider_evidence()
    evidence["execution"]["cost"] = {
        "micros": 8,
        "currency": "USD",
        "source": "estimated",
    }

    assert _validate_p0_h_evidence(evidence).returncode != 0


def test_p0_h_runtime_evidence_is_reduced_to_release_allowlist() -> None:
    digest = "B" * 64
    runtime_evidence = {
        "ok": True,
        "data": {
            "executionId": "aiexec_test",
            "accountId": "acc_test",
            "capabilityKey": "script_generation",
            "finalStatus": "succeeded",
            "snapshotHash": digest,
            "provider": {
                "adapterType": "openai_compatible",
                "providerRefHash": digest,
                "modelIdHash": digest,
                "validationRunHash": digest,
                "validationStage": "real_small_call",
                "validationStatus": "verified",
            },
            "responseIdHash": digest,
            "durationMs": 120,
            "usageReported": True,
            "jobs": [],
            "usage": [
                {
                    "inputUnits": 2,
                    "outputUnits": 3,
                    "totalUnits": 5,
                    "costMicros": 8,
                    "currency": "USD",
                    "costSource": "estimated",
                    "pricingRevision": 2,
                }
            ],
            "outputs": [
                {
                    "kind": "json",
                    "contentHash": digest,
                    "byteSize": 32,
                    "schemaStatus": "valid",
                    "quarantined": False,
                }
            ],
            "errors": [],
        },
    }
    manifest = {
        "version": "0.5.0",
        "artifacts": [
            {"kind": kind, "sha256": digest}
            for kind in ("desktop", "sidecar", "installer", "portable")
        ],
    }
    module = REPOSITORY_ROOT / "scripts" / "p0-h-real-provider-evidence.mjs"
    script = (
        f'import {{ buildP0HRealProviderEvidence }} from {json.dumps(module.as_uri())};'
        f"const runtimeEvidence = {json.dumps(runtime_evidence)};"
        f"const manifest = {json.dumps(manifest)};"
        "process.stdout.write(JSON.stringify("
        "buildP0HRealProviderEvidence(runtimeEvidence, manifest)));"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    evidence = json.loads(result.stdout)

    assert evidence["evidenceKind"] == "p0h_openai_compatible_real_execution"
    assert evidence["execution"]["cost"] == {
        "micros": 8,
        "currency": "USD",
        "source": "estimated",
        "pricingRevision": 2,
    }
    assert "accountId" not in evidence
    assert "executionId" not in evidence


def test_p0_h_manual_evidence_entrypoint_and_release_flag_exist() -> None:
    manual_script = REPOSITORY_ROOT / "tests" / "manual" / "p0-h-real-provider-evidence.ps1"
    release_script = REPOSITORY_ROOT / "scripts" / "build-windows-release.mjs"

    assert manual_script.is_file()
    assert "--target-ai-evidence" in release_script.read_text(encoding="utf-8")


def test_p0_h_evidence_attaches_without_rebuilding_artifacts(tmp_path: Path) -> None:
    artifacts: list[dict[str, object]] = []
    bindings: dict[str, str] = {}
    for kind in ("desktop", "sidecar", "installer", "portable"):
        artifact = tmp_path / f"{kind}.bin"
        artifact.write_bytes(f"fixed-{kind}".encode("utf-8"))
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest().upper()
        bindings[kind] = digest
        artifacts.append(
            {
                "kind": kind,
                "path": artifact.name,
                "size": artifact.stat().st_size,
                "sha256": digest,
            }
        )
    manifest_path = tmp_path / "release-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "version": "0.5.0",
                "channel": "test",
                "tests": [],
                "artifacts": artifacts,
            }
        ),
        encoding="utf-8",
    )
    evidence_path = tmp_path / "manual-evidence.json"
    evidence = _real_provider_evidence()
    evidence["artifactBindings"] = bindings
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    evidence_root = tmp_path / "evidence"
    module = REPOSITORY_ROOT / "scripts" / "attach-p0-h-release-evidence.mjs"
    script = (
        f'import {{ attachP0HReleaseEvidence }} from {json.dumps(module.as_uri())};'
        "attachP0HReleaseEvidence({"
        'channel:"test",'
        f"evidencePath:{json.dumps(str(evidence_path))},"
        f"evidenceRoot:{json.dumps(str(evidence_root))},"
        f"manifestPath:{json.dumps(str(manifest_path))},"
        f"repoRoot:{json.dumps(str(tmp_path))},"
        'version:"0.5.0"});'
    )
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    attached = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert attached["artifacts"] == artifacts
    assert attached["tests"][0]["id"] == "p0-h-real-provider-execution"
    assert attached["tests"][0]["artifactBindings"] == bindings


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


def _validate_p0_h_evidence(evidence: dict[str, object]) -> subprocess.CompletedProcess[str]:
    module = REPOSITORY_ROOT / "scripts" / "p0-h-real-provider-evidence.mjs"
    bindings = evidence["artifactBindings"]
    script = (
        f'import {{ validateP0HRealProviderEvidence }} from {json.dumps(module.as_uri())};'
        f"const evidence = {json.dumps(evidence)};"
        f"const bindings = {json.dumps(bindings)};"
        'validateP0HRealProviderEvidence(evidence, '
        '{expectedVersion:"0.5.0",expectedArtifactBindings:bindings});'
    )
    return subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _real_provider_evidence() -> dict[str, object]:
    digest = "A" * 64
    return {
        "schemaVersion": 1,
        "evidenceKind": "p0h_openai_compatible_real_execution",
        "appVersion": "0.5.0",
        "artifactBindings": {
            "desktop": digest,
            "sidecar": digest,
            "installer": digest,
            "portable": digest,
        },
        "provider": {
            "adapterType": "openai_compatible",
            "providerRefHash": digest,
            "modelIdHash": digest,
            "validationRunHash": digest,
        },
        "execution": {
            "capabilityKey": "script_generation",
            "finalStatus": "succeeded",
            "snapshotHash": digest,
            "responseIdHash": digest,
            "outputHash": digest,
            "durationMs": 100,
            "usage": {"inputUnits": 2, "outputUnits": 3, "totalUnits": 5},
            "cost": {"micros": 8, "currency": "USD", "source": "reported"},
            "responseSummary": {
                "outputType": "json",
                "schemaValid": True,
                "byteSize": 32,
            },
        },
        "redaction": {"passed": True, "schemaAllowlistPassed": True},
    }
