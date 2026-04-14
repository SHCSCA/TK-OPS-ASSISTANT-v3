from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_video_deconstruction_import_and_list_contract(runtime_app, tmp_path: Path) -> None:
    client = TestClient(runtime_app)
    project_id = client.post(
        "/api/dashboard/projects",
        json={"name": "Video Contract", "description": "import"},
    ).json()["data"]["id"]
    video_path = tmp_path / "contract.mp4"
    video_path.write_bytes(b"\x00" * 4096)

    with patch("services.video_import_service.probe_video", return_value=None):
        import_response = client.post(
            f"/api/video-deconstruction/projects/{project_id}/import",
            json={"filePath": str(video_path)},
        )

    assert import_response.status_code == 200
    payload = import_response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {
        "id",
        "projectId",
        "filePath",
        "fileName",
        "fileSizeBytes",
        "durationSeconds",
        "width",
        "height",
        "frameRate",
        "codec",
        "status",
        "errorMessage",
        "createdAt",
    }
    assert payload["data"]["status"] == "imported"

    list_response = client.get(f"/api/video-deconstruction/projects/{project_id}/videos")

    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["ok"] is True
    assert listed["data"][0]["id"] == payload["data"]["id"]
