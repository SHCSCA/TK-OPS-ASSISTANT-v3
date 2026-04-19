from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_video_deconstruction_stages_and_rerun_contract(runtime_app, tmp_path: Path) -> None:
    client = TestClient(runtime_app)
    project_id = client.post(
        "/api/dashboard/projects",
        json={"name": "Video Contract", "description": "Stage contract"},
    ).json()["data"]["id"]
    video_path = tmp_path / "contract-video.mp4"
    video_path.write_bytes(b"\x00" * 4096)

    with patch("runtime_tasks.video_tasks.probe_video", return_value=None):
        import_response = client.post(
            f"/api/video-deconstruction/projects/{project_id}/import",
            json={"filePath": str(video_path)},
        )

    video_id = import_response.json()["data"]["id"]

    transcribe_response = client.post(f"/api/video-deconstruction/videos/{video_id}/transcribe")
    assert transcribe_response.status_code == 200
    assert transcribe_response.json()["data"]["status"] == "provider_required"

    stages_response = client.get(f"/api/video-deconstruction/videos/{video_id}/stages")
    assert stages_response.status_code == 200
    stages_payload = stages_response.json()
    assert set(stages_payload) == {"ok", "data"}
    assert isinstance(stages_payload["data"], list)
    assert set(stages_payload["data"][0]) == {
        "stageId",
        "label",
        "status",
        "progressPct",
        "resultSummary",
        "errorMessage",
        "updatedAt",
        "canRerun",
    }

    rerun_response = client.post(
        f"/api/video-deconstruction/videos/{video_id}/stages/transcribe/rerun"
    )
    assert rerun_response.status_code == 200
    rerun_payload = rerun_response.json()
    assert set(rerun_payload) == {"ok", "data"}
    assert set(rerun_payload["data"]) == {
        "id",
        "taskType",
        "projectId",
        "status",
        "progress",
        "message",
        "createdAt",
        "updatedAt",
    }


def test_video_deconstruction_documented_routes_contract(runtime_app, tmp_path: Path) -> None:
    client = TestClient(runtime_app)
    project_id = client.post(
        "/api/dashboard/projects",
        json={"name": "Video Documented Contract", "description": "Doc route contract"},
    ).json()["data"]["id"]
    video_path = tmp_path / "documented-contract.mp4"
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
    assert set(transcript) == {
        "id",
        "videoId",
        "language",
        "text",
        "status",
        "createdAt",
        "updatedAt",
    }
    assert transcript["text"] is None
    assert transcript["status"] == "provider_required"

    fetch_transcript_response = client.get(f"/api/video-deconstruction/videos/{video_id}/transcript")
    assert fetch_transcript_response.status_code == 200
    assert fetch_transcript_response.json()["data"]["id"] == transcript["id"]

    stages_response = client.get(f"/api/video-deconstruction/videos/{video_id}/stages")
    assert stages_response.status_code == 200
    transcribe_stage = next(
        item for item in stages_response.json()["data"] if item["stageId"] == "transcribe"
    )
    assert transcribe_stage["status"] == "provider_required"
    assert transcribe_stage["errorMessage"] == transcribe_stage["resultSummary"]

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
    segments = segment_response.json()["data"]
    assert len(segments) == 1
    assert set(segments[0]) == {
        "id",
        "videoId",
        "segmentIndex",
        "startMs",
        "endMs",
        "label",
        "transcriptText",
        "metadataJson",
        "createdAt",
    }

    fetch_segments_response = client.get(f"/api/video-deconstruction/videos/{video_id}/segments")
    assert fetch_segments_response.status_code == 200
    assert fetch_segments_response.json()["data"][0]["id"] == segments[0]["id"]

    structure_response = client.post(f"/api/video-deconstruction/videos/{video_id}/extract-structure")
    assert structure_response.status_code == 200
    extraction = structure_response.json()["data"]
    assert set(extraction) == {
        "id",
        "videoId",
        "status",
        "scriptJson",
        "storyboardJson",
        "createdAt",
        "updatedAt",
    }
    assert extraction["scriptJson"] is not None
    assert extraction["storyboardJson"] is not None

    fetch_structure_response = client.get(f"/api/video-deconstruction/videos/{video_id}/structure")
    assert fetch_structure_response.status_code == 200
    assert fetch_structure_response.json()["data"]["id"] == extraction["id"]

    apply_response = client.post(
        f"/api/video-deconstruction/extractions/{extraction['id']}/apply-to-project"
    )
    assert apply_response.status_code == 200
    applied = apply_response.json()["data"]
    assert set(applied) == {
        "projectId",
        "extractionId",
        "scriptRevision",
        "status",
        "message",
    }
    assert applied["projectId"] == project_id
    assert applied["status"] == "applied"
