from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

PROVIDER_REQUIRED_MESSAGE = "当前未配置可用视频解析模型，视频解析已阻塞；请在 AI 与系统设置中配置支持视频输入的多模态模型后重试。"
SEGMENT_WITHOUT_TRANSCRIPT_MESSAGE = "未配置可用视频解析模型，已使用基础元数据生成画面分段。"
STRUCTURE_BLOCKED_MESSAGE = "视频分段尚未成功，结构提取已阻塞；请先完成分段后重试。"
APPLY_BLOCKED_MESSAGE = "视频结构提取尚未成功，无法应用到项目；请先完成结构提取后重试。"
STAGE_KEYS = {
    "stageId",
    "label",
    "status",
    "progressPct",
    "resultSummary",
    "errorMessage",
    "errorCode",
    "nextAction",
    "blockedByStageId",
    "activeTaskId",
    "activeTaskStatus",
    "activeTaskProgress",
    "activeTaskMessage",
    "canCancel",
    "canRetry",
    "isCurrent",
    "updatedAt",
    "canRerun",
}
TASK_KEYS = {
    "id",
    "taskType",
    "projectId",
    "status",
    "progress",
    "message",
    "createdAt",
    "updatedAt",
}
def _stage_by_id(stages: list[dict[str, object]], stage_id: str) -> dict[str, object]:
    return next(item for item in stages if item["stageId"] == stage_id)


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
    assert [item["stageId"] for item in stages_payload["data"]] == [
        "import",
        "transcribe",
        "segment",
        "extract_structure",
    ]
    assert all(set(item) == STAGE_KEYS for item in stages_payload["data"])

    import_stage = _stage_by_id(stages_payload["data"], "import")
    transcribe_stage = _stage_by_id(stages_payload["data"], "transcribe")
    segment_stage = _stage_by_id(stages_payload["data"], "segment")
    structure_stage = _stage_by_id(stages_payload["data"], "extract_structure")

    assert import_stage["canRerun"] is True
    assert import_stage["errorCode"] == "media.ffprobe_unavailable"
    assert import_stage["nextAction"] == "请先修复 FFprobe 或媒体诊断配置后，再重新导入视频。"
    assert import_stage["isCurrent"] is True
    assert import_stage["canRetry"] is False
    assert transcribe_stage["status"] == "provider_required"
    assert transcribe_stage["resultSummary"] == PROVIDER_REQUIRED_MESSAGE
    assert transcribe_stage["errorMessage"] == PROVIDER_REQUIRED_MESSAGE
    assert transcribe_stage["errorCode"] == "provider.required"
    assert transcribe_stage["nextAction"] == "请先配置可用视频解析模型后重试。"
    assert transcribe_stage["blockedByStageId"] is None
    assert transcribe_stage["canCancel"] is False
    assert transcribe_stage["canRetry"] is True
    assert transcribe_stage["isCurrent"] is False
    assert transcribe_stage["canRerun"] is True
    assert segment_stage["canRerun"] is True
    assert structure_stage["canRerun"] is True

    import_rerun_response = client.post(
        f"/api/video-deconstruction/videos/{video_id}/stages/import/rerun"
    )
    assert import_rerun_response.status_code == 200
    assert import_rerun_response.json()["data"]["taskType"] == "video-import-stage"

    rerun_response = client.post(
        f"/api/video-deconstruction/videos/{video_id}/stages/transcribe/rerun"
    )
    assert rerun_response.status_code == 200
    rerun_payload = rerun_response.json()
    assert set(rerun_payload) == {"ok", "data"}
    assert set(rerun_payload["data"]) == TASK_KEYS
    assert rerun_payload["data"]["taskType"] == "video-import-stage"
    assert rerun_payload["data"]["projectId"] == project_id
    assert rerun_payload["data"]["status"] == "queued"


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

    segment_response = client.post(f"/api/video-deconstruction/videos/{video_id}/segment")
    assert segment_response.status_code == 200
    segments = segment_response.json()["data"]
    assert len(segments) == 1
    assert segments[0]["transcriptText"] is None

    stages_after_segment = client.get(
        f"/api/video-deconstruction/videos/{video_id}/stages"
    ).json()["data"]
    segment_stage = _stage_by_id(stages_after_segment, "segment")
    assert segment_stage["stageId"] == "segment"
    assert segment_stage["status"] == "succeeded"
    assert segment_stage["resultSummary"] == SEGMENT_WITHOUT_TRANSCRIPT_MESSAGE
    assert segment_stage["errorMessage"] is None
    assert segment_stage["blockedByStageId"] is None
    assert segment_stage["isCurrent"] is False

    structure_response = client.post(
        f"/api/video-deconstruction/videos/{video_id}/extract-structure"
    )
    assert structure_response.status_code == 200
    extraction = structure_response.json()["data"]
    assert extraction["status"] == "succeeded"

    stages_after_structure = client.get(
        f"/api/video-deconstruction/videos/{video_id}/stages"
    ).json()["data"]
    structure_stage = _stage_by_id(stages_after_structure, "extract_structure")
    assert structure_stage["stageId"] == "extract_structure"
    assert structure_stage["status"] == "succeeded"
    assert structure_stage["errorMessage"] is None

    blocked_apply_response = client.post(
        f"/api/video-deconstruction/extractions/extraction-{video_id}/apply-to-project"
    )
    assert blocked_apply_response.status_code == 200

    deconstruct_response = client.post(f"/api/video-deconstruction/videos/{video_id}/deconstruct")
    assert deconstruct_response.status_code == 200
    deconstruct_payload = deconstruct_response.json()["data"]
    assert set(deconstruct_payload) == {
        "videoId",
        "transcript",
        "segments",
        "structure",
        "stages",
        "script",
        "keyframes",
        "contentStructure",
        "source",
    }
    assert deconstruct_payload["transcript"]["status"] == "provider_required"
    assert deconstruct_payload["structure"]["status"] == "succeeded"
    assert set(deconstruct_payload["script"]) == {"title", "language", "fullText", "lines"}
    assert set(deconstruct_payload["contentStructure"]) == {
        "topic",
        "hook",
        "painPoints",
        "sellingPoints",
        "rhythm",
        "cta",
        "reusableForScript",
        "reusableForStoryboard",
        "risks",
    }
    assert set(deconstruct_payload["source"]) == {"provider", "model", "promptVersion"}

    segment_response = client.get(f"/api/video-deconstruction/videos/{video_id}/segments")
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
    assert extraction["status"] == "succeeded"
    assert extraction["scriptJson"] is not None
    assert extraction["storyboardJson"] is not None

    fetch_structure_response = client.get(f"/api/video-deconstruction/videos/{video_id}/structure")
    assert fetch_structure_response.status_code == 200
    assert fetch_structure_response.json()["data"]["id"] == extraction["id"]

    result_response = client.get(f"/api/video-deconstruction/videos/{video_id}/result")
    assert result_response.status_code == 200
    result_payload = result_response.json()["data"]
    assert result_payload["videoId"] == video_id
    assert set(result_payload) == {
        "videoId",
        "transcript",
        "segments",
        "structure",
        "stages",
        "script",
        "keyframes",
        "contentStructure",
        "source",
    }

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
