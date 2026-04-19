from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_video_deconstruction_stages_and_rerun(runtime_app, tmp_path: Path) -> None:
    client = TestClient(runtime_app)
    project_id = client.post(
        "/api/dashboard/projects",
        json={"name": "Video Stage Project", "description": "Stage tests"},
    ).json()["data"]["id"]
    video_path = tmp_path / "stage-test.mp4"
    video_path.write_bytes(b"\x00" * 4096)

    with patch("runtime_tasks.video_tasks.probe_video", return_value=None):
        import_response = client.post(
            f"/api/video-deconstruction/projects/{project_id}/import",
            json={"filePath": str(video_path)},
        )

    assert import_response.status_code == 200
    video_id = import_response.json()["data"]["id"]

    transcribe_response = client.post(f"/api/video-deconstruction/videos/{video_id}/transcribe")
    assert transcribe_response.status_code == 200
    transcript = transcribe_response.json()["data"]
    assert transcript["status"] == "provider_required"
    assert transcript["text"] is None

    stages_response = client.get(f"/api/video-deconstruction/videos/{video_id}/stages")
    assert stages_response.status_code == 200
    stages = stages_response.json()["data"]
    assert [item["stageId"] for item in stages] == [
        "import",
        "transcribe",
        "segment",
        "extract_structure",
    ]
    assert stages[0]["status"] in {"succeeded", "ready", "imported"}
    transcribe_stage = next(item for item in stages if item["stageId"] == "transcribe")
    assert transcribe_stage["status"] == "provider_required"
    assert transcribe_stage["resultSummary"] == "当前未接入可用转录 Provider，转录已阻塞；接入 Provider 后可重试。"
    assert transcribe_stage["errorMessage"] == transcribe_stage["resultSummary"]

    rerun_response = client.post(
        f"/api/video-deconstruction/videos/{video_id}/stages/transcribe/rerun"
    )
    assert rerun_response.status_code == 200
    task_payload = rerun_response.json()["data"]
    assert task_payload["taskType"] == "video-import-stage"
    assert task_payload["projectId"] == project_id

    rerun_stages_response = client.get(f"/api/video-deconstruction/videos/{video_id}/stages")
    assert rerun_stages_response.status_code == 200
    rerun_stages = rerun_stages_response.json()["data"]
    assert any(item["stageId"] == "transcribe" for item in rerun_stages)


def test_video_deconstruction_apply_to_project_persists_versions(runtime_app, tmp_path: Path) -> None:
    client = TestClient(runtime_app)
    project_id = client.post(
        "/api/dashboard/projects",
        json={"name": "Video Apply Project", "description": "Apply extraction"},
    ).json()["data"]["id"]
    video_path = tmp_path / "apply-project.mp4"
    video_path.write_bytes(b"\x00" * 4096)

    with patch("runtime_tasks.video_tasks.probe_video", return_value=None):
        import_response = client.post(
            f"/api/video-deconstruction/projects/{project_id}/import",
            json={"filePath": str(video_path)},
        )

    assert import_response.status_code == 200
    video_id = import_response.json()["data"]["id"]

    transcribe_response = client.post(f"/api/video-deconstruction/videos/{video_id}/transcribe")
    assert transcribe_response.status_code == 200
    assert transcribe_response.json()["data"]["status"] == "provider_required"

    blocked_segment_response = client.post(f"/api/video-deconstruction/videos/{video_id}/segment")
    assert blocked_segment_response.status_code == 409
    blocked_segment_payload = blocked_segment_response.json()
    assert blocked_segment_payload["ok"] is False
    assert blocked_segment_payload["error"] == "视频转录尚未成功，分段已阻塞；请先完成转录后重试。"
    assert blocked_segment_payload["error_code"] == "task.conflict"

    blocked_apply_response = client.post(
        f"/api/video-deconstruction/extractions/extraction-{video_id}/apply-to-project"
    )
    assert blocked_apply_response.status_code == 409
    blocked_apply_payload = blocked_apply_response.json()
    assert blocked_apply_payload["ok"] is False
    assert blocked_apply_payload["error"] == "视频结构提取尚未成功，无法应用到项目；请先完成结构提取后重试。"
    assert blocked_apply_payload["error_code"] == "task.conflict"

    runtime_app.state.video_deconstruction_repository.upsert_stage_run(
        video_id,
        "transcribe",
        status="succeeded",
        progress_pct=100,
        result_summary="manual-success",
        error_message=None,
    )

    segment_response = client.post(f"/api/video-deconstruction/videos/{video_id}/segment")
    assert segment_response.status_code == 200

    structure_response = client.post(f"/api/video-deconstruction/videos/{video_id}/extract-structure")
    assert structure_response.status_code == 200
    extraction_id = structure_response.json()["data"]["id"]

    apply_response = client.post(f"/api/video-deconstruction/extractions/{extraction_id}/apply-to-project")
    assert apply_response.status_code == 200
    apply_payload = apply_response.json()["data"]
    assert apply_payload["projectId"] == project_id
    assert apply_payload["scriptRevision"] == 1

    scripts = runtime_app.state.script_repository.list_versions(project_id)
    storyboards = runtime_app.state.storyboard_repository.list_versions(project_id)
    project = runtime_app.state.dashboard_repository.get_project(project_id)

    assert len(scripts) == 1
    assert scripts[0].source == "video_extraction"
    assert "来源视频" in scripts[0].content
    assert len(storyboards) == 1
    assert storyboards[0].source == "video_extraction"
    assert storyboards[0].based_on_script_revision == scripts[0].revision
    assert project is not None
    assert project.current_script_version == scripts[0].revision
    assert project.current_storyboard_version == storyboards[0].revision
