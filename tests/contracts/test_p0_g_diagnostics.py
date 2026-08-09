from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TAURI_ROOT = ROOT / "apps" / "desktop" / "src-tauri"


def test_supervisor_diagnostics_commands_are_registered() -> None:
    main_source = (TAURI_ROOT / "src" / "main.rs").read_text(encoding="utf-8")

    assert "get_runtime_supervisor_diagnostics" in main_source
    assert "export_runtime_supervisor_diagnostics" in main_source


def test_supervisor_diagnostic_payload_excludes_secrets_and_full_paths() -> None:
    source = (
        TAURI_ROOT / "src" / "runtime_supervisor" / "diagnostics.rs"
    ).read_text(encoding="utf-8")
    payload_definition = source.split(
        "pub struct SupervisorDiagnosticsDto", maxsplit=1
    )[1].split("pub struct SupervisorDiagnosticExportDto", maxsplit=1)[0]

    assert "session_token" not in payload_definition
    assert "license" not in payload_definition.lower()
    assert "environment" not in payload_definition.lower()
    assert "path:" not in payload_definition
    assert "artifact_sha256" in payload_definition
    assert "last_exit_code" in payload_definition
    assert "recent_logs" in payload_definition


def test_supervisor_bootstrap_config_has_owned_restart_and_diagnostic_defaults() -> None:
    config = json.loads(
        (
            TAURI_ROOT
            / "resources"
            / "runtime"
            / "runtime-supervisor.bootstrap.json"
        ).read_text(encoding="utf-8")
    )

    assert config["restart"] == {
        "maxAttempts": 3,
        "initialDelayMs": 500,
        "maxDelayMs": 5000,
    }
    assert config["diagnostics"] == {"tailLines": 200}


def test_bootstrap_error_screen_keeps_offline_diagnostic_actions() -> None:
    source = (
        ROOT
        / "apps"
        / "desktop"
        / "src"
        / "bootstrap"
        / "BootstrapErrorScreen.vue"
    ).read_text(encoding="utf-8")

    assert 'data-action="copy-runtime-diagnostics"' in source
    assert 'data-action="export-runtime-diagnostics"' in source
    assert "getDesktopRuntimeSupervisorDiagnostics" in source
    assert "exportDesktopRuntimeSupervisorDiagnostics" in source
