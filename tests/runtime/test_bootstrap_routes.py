from __future__ import annotations

from fastapi.testclient import TestClient
from schemas.license import LicenseStatusDto


def test_initialize_directories_creates_runtime_paths_and_reports_status(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post("/api/bootstrap/initialize-directories")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    report = payload["data"]
    assert set(report) == {"rootDir", "databasePath", "status", "directories", "checkedAt"}
    assert report["status"] == "ok"
    assert report["rootDir"]
    assert report["databasePath"]
    assert report["directories"]
    for item in report["directories"]:
        assert set(item) == {
            "key",
            "label",
            "path",
            "exists",
            "writable",
            "status",
            "message",
        }
        assert item["path"]


def test_runtime_selfcheck_reports_structured_items(
    runtime_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "services.bootstrap_service._check_port_listening",
        lambda port: (True, f"端口 {port} 已处于监听状态"),
    )

    response = runtime_client.post("/api/bootstrap/runtime-selfcheck")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    report = payload["data"]
    assert set(report) == {"status", "runtimeVersion", "checkedAt", "items"}
    assert report["runtimeVersion"]
    assert report["status"] == "ok"
    assert report["items"]
    for item in report["items"]:
        assert set(item) == {
            "key",
            "label",
            "status",
            "detail",
            "errorCode",
            "checkedAt",
        }
        assert item["key"]


def test_runtime_selfcheck_warns_when_port_is_not_listening(
    runtime_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "services.bootstrap_service._check_port_listening",
        lambda port: (False, f"端口 {port} 未检测到目标服务"),
    )

    response = runtime_client.post("/api/bootstrap/runtime-selfcheck")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    port_item = next(item for item in payload["data"]["items"] if item["key"] == "port")
    assert port_item["status"] == "warning"
    assert port_item["errorCode"] == "runtime.port-not-listening"


def test_bootstrap_readiness_reports_license_blocker_and_next_action(
    runtime_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_client.app.state.bootstrap_service._license_service,
        "get_status",
        lambda request_id=None: LicenseStatusDto(
            active=False,
            restrictedMode=True,
            machineCode="machine-1",
            machineBound=False,
            licenseType="perpetual",
            maskedCode="",
            activatedAt=None,
        ),
    )
    monkeypatch.setattr(
        "services.bootstrap_service._check_port_listening",
        lambda port: (True, f"端口 {port} 已处于监听状态"),
    )

    response = runtime_client.get("/api/bootstrap/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    report = payload["data"]
    assert report["canContinue"] is False
    blockers = {item["key"]: item for item in report["blockers"]}
    assert "license" in blockers
    assert blockers["license"]["errorCode"] == "license.not_activated"
    assert blockers["license"]["affectedTarget"] == "许可证"
    assert blockers["license"]["nextStep"]
    assert blockers["license"]["action"] == {
        "key": "open-license-activation",
        "label": "前往激活",
    }
