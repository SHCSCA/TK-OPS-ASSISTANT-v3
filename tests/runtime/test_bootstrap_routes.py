from __future__ import annotations

from fastapi.testclient import TestClient
from schemas.v1.bootstrap import LicenseBlockingIssueDto, LicenseStatusDto


def test_initialize_directories_creates_runtime_paths_and_reports_status(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.post(
        "/api/bootstrap/initialize-directories"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    report = payload["data"]
    assert set(report) == {"rootDir", "databasePath", "status", "directories", "checkedAt"}
    assert report["status"] == "ready"
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
        assert item["path"] == ""


def test_runtime_selfcheck_reports_structured_items(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.post(
        "/api/bootstrap/runtime-selfcheck"
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["ok"] is True
    report = payload["data"]
    assert set(report) == {"status", "runtimeVersion", "checkedAt", "items"}
    assert report["runtimeVersion"]
    assert report["status"] == "queued"
    assert len(report["items"]) == 1
    item = report["items"][0]
    assert set(item) == {
        "key",
        "label",
        "status",
        "detail",
        "errorCode",
        "checkedAt",
    }
    assert item["key"] == "persistent-task"
    assert item["status"] == "queued"
    assert "持久队列" in item["detail"]


def test_runtime_selfcheck_no_longer_returns_synchronous_port_results(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.post(
        "/api/bootstrap/runtime-selfcheck"
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["ok"] is True
    assert all(item["key"] != "port" for item in payload["data"]["items"])


def test_bootstrap_readiness_reports_license_blocker_and_next_action(
    runtime_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_client.app.state.bootstrap_v1_service,
        "get_license_status",
        lambda **_: LicenseStatusDto(
            status="missing",
            machineCode="TKOPS-ABCDE-FGHIJ-KLMNO-PQRST-TEST5",
            machineCodeMasked="TKOPS-…-TEST5",
            expiresAt=None,
            activatedAt=None,
            blockingIssue=LicenseBlockingIssueDto(
                code="LICENSE_MISSING",
                message="许可证尚未激活",
            ),
            revision=0,
        ),
    )

    response = runtime_client.get("/api/bootstrap/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    report = payload["data"]
    assert report["canContinue"] is False
    license_item = next(
        item for item in report["items"] if item["key"] == "license"
    )
    assert license_item["errorCode"] == "LICENSE_MISSING"
    assert license_item["action"] == {
        "key": "open-bootstrap",
        "label": "打开首启向导",
    }
    blocker = next(
        item
        for item in report["blockers"]
        if item["errorCode"] == "LICENSE_MISSING"
    )
    assert blocker["affectedTarget"] == "bootstrap"
    assert blocker["nextStep"]
    assert blocker["action"] == {
        "key": "open-bootstrap",
        "label": "打开首启向导",
    }
