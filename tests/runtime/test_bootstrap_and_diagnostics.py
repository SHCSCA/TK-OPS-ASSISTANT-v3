from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.logging import log_event


def test_initialize_directories_creates_expected_runtime_folders(
    runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    response = runtime_client.post("/api/bootstrap/initialize-directories")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["rootDir"] == str(runtime_data_dir)
    assert payload["status"] == "ok"
    assert payload["databasePath"] == str(runtime_data_dir / "runtime.db")

    directories = {item["key"]: item for item in payload["directories"]}
    assert {"workspace", "cache", "exports", "logs", "projects", "assets", "licenses"}.issubset(
        directories
    )

    for item in directories.values():
        path = Path(item["path"])
        assert path.exists()
        assert path.is_dir()
        assert item["writable"] is True


def test_runtime_selfcheck_reports_ready_checks(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post("/api/bootstrap/runtime-selfcheck")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "ok"

    checks = {item["key"]: item for item in payload["items"]}
    assert set(checks) == {"port", "version", "dependencies", "database"}
    assert all(item["status"] == "ok" for item in checks.values())
    assert checks["version"]["detail"]


def test_runtime_logs_support_kind_filter_and_paging(
    runtime_app,
    runtime_client: TestClient,
) -> None:
    current_config = runtime_client.get("/api/settings/config").json()["data"]
    runtime_client.put(
        "/api/settings/config",
        json={
            "runtime": current_config["runtime"],
            "paths": current_config["paths"],
            "logging": current_config["logging"],
            "ai": current_config["ai"],
        },
    )
    log_event(
        "system",
        "bootstrap.selfcheck.executed",
        context={"scope": "bootstrap"},
        request_id="req-bootstrap",
    )

    audit_response = runtime_client.get("/api/settings/logs", params={"kind": "audit"})
    assert audit_response.status_code == 200
    audit_items = audit_response.json()["data"]["items"]
    assert audit_items
    assert all(item["kind"] == "audit" for item in audit_items)

    paged_response = runtime_client.get("/api/settings/logs", params={"limit": 1})
    assert paged_response.status_code == 200
    paged_payload = paged_response.json()["data"]
    assert len(paged_payload["items"]) == 1
    assert "nextCursor" in paged_payload


def test_diagnostics_export_writes_bundle_under_configured_export_dir(
    runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    export_dir = runtime_data_dir / "exports-next"
    log_dir = runtime_data_dir / "logs-next"
    update_payload = {
        "runtime": {
            "mode": "test",
            "workspaceRoot": str(runtime_data_dir / "workspace"),
        },
        "paths": {
            "cacheDir": str(runtime_data_dir / "cache-next"),
            "exportDir": str(export_dir),
            "logDir": str(log_dir),
        },
        "logging": {"level": "INFO"},
        "ai": {
            "provider": "openai",
            "model": "gpt-5.4",
            "voice": "alloy",
            "subtitleMode": "balanced",
        },
    }
    runtime_client.put("/api/settings/config", json=update_payload)
    log_event("audit", "diagnostics.bundle.prepare", request_id="req-diagnostics")

    response = runtime_client.post("/api/settings/diagnostics/export")

    assert response.status_code == 200
    payload = response.json()["data"]
    bundle_path = Path(payload["bundlePath"])
    assert bundle_path.exists()
    assert bundle_path.parent == export_dir / "diagnostics"
    assert {entry["name"] for entry in payload["entries"]} >= {
        "settings.json",
        "health.json",
        "diagnostics.json",
        "runtime.jsonl",
    }

    with ZipFile(bundle_path) as archive:
        names = set(archive.namelist())
        assert {"settings.json", "health.json", "diagnostics.json", "runtime.jsonl"} <= names
