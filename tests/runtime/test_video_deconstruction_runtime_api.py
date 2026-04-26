from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai.providers.errors import ProviderHTTPException
from ai.providers.speech_to_text_openai import SpeechToTextResult
from services.ai_text_generation_service import GeneratedTextResult
from services.video_deconstruction_prompt import (
    VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT,
    VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT,
)

PROVIDER_REQUIRED_MESSAGE = "当前未配置可用视频解析模型，视频解析已阻塞；请在 AI 与系统设置中配置支持视频输入的多模态模型后重试。"
SEGMENT_WITHOUT_TRANSCRIPT_MESSAGE = "未配置可用视频解析模型，已使用基础元数据生成画面分段。"
TRANSCRIPT_SKIPPED_BY_MULTIMODAL_MESSAGE = "多模态视频拆解已生成语音与画面时间轴，未单独执行转录。"
STRUCTURE_BLOCKED_MESSAGE = "视频分段尚未成功，结构提取已阻塞；请先完成分段后重试。"
APPLY_BLOCKED_MESSAGE = "视频结构提取尚未成功，无法应用到项目；请先完成结构提取后重试。"
def _stage_by_id(stages: list[dict[str, object]], stage_id: str) -> dict[str, object]:
    return next(item for item in stages if item["stageId"] == stage_id)


def _enable_video_transcription(client: TestClient) -> None:
    settings_response = client.get("/api/settings/ai-capabilities")
    capabilities = settings_response.json()["data"]["capabilities"]
    for item in capabilities:
        if item["capabilityId"] == "video_transcription":
            item["enabled"] = True
            item["provider"] = "openai"
            item["model"] = "whisper-1"
    update_response = client.put("/api/settings/ai-capabilities", json={"capabilities": capabilities})
    assert update_response.status_code == 200
    secret_response = client.put(
        "/api/settings/ai-capabilities/providers/openai/secret",
        json={"apiKey": "sk-test-video-transcription"},
    )
    assert secret_response.status_code == 200


def _enable_multimodal_asset_analysis(client: TestClient) -> None:
    settings_response = client.get("/api/settings/ai-capabilities")
    capabilities = settings_response.json()["data"]["capabilities"]
    for item in capabilities:
        if item["capabilityId"] == "asset_analysis":
            item["enabled"] = True
            item["provider"] = "volcengine"
            item["model"] = "doubao-seed-2.0-pro-260215"
        if item["capabilityId"] == "video_transcription":
            item["enabled"] = False
    update_response = client.put("/api/settings/ai-capabilities", json={"capabilities": capabilities})
    assert update_response.status_code == 200
    secret_response = client.put(
        "/api/settings/ai-capabilities/providers/volcengine/secret",
        json={
            "apiKey": "sk-test-volcengine",
            "baseUrl": "https://ark.cn-beijing.volces.com/api/v3",
        },
    )
    assert secret_response.status_code == 200


def _enable_multimodal_video_transcription_with_legacy_asset_analysis(client: TestClient) -> None:
    settings_response = client.get("/api/settings/ai-capabilities")
    capabilities = settings_response.json()["data"]["capabilities"]
    for item in capabilities:
        if item["capabilityId"] == "video_transcription":
            item["enabled"] = True
            item["provider"] = "volcengine"
            item["model"] = "doubao-seed-2-0-pro-260215"
        if item["capabilityId"] == "asset_analysis":
            item["enabled"] = True
            item["provider"] = "volcengine"
            item["model"] = "doubao-seed-1-6-vision-250815"
            item["agentRole"] = "素材分析师"
            item["systemPrompt"] = "# 素材分析 Agent\n\n请输出 Markdown 素材分析报告。"
            item["userPromptTemplate"] = "请分析以下素材内容：{{content}}"
    update_response = client.put("/api/settings/ai-capabilities", json={"capabilities": capabilities})
    assert update_response.status_code == 200
    secret_response = client.put(
        "/api/settings/ai-capabilities/providers/volcengine/secret",
        json={
            "apiKey": "sk-test-volcengine",
            "baseUrl": "https://ark.cn-beijing.volces.com/api/v3",
        },
    )
    assert secret_response.status_code == 200


def test_video_deconstruction_stages_surface_current_blocker(runtime_app, tmp_path: Path) -> None:
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
    import_stage = _stage_by_id(stages, "import")
    assert import_stage["canRerun"] is True
    assert import_stage["status"] == "failed_degraded"
    assert import_stage["errorCode"] == "media.ffprobe_unavailable"
    assert import_stage["nextAction"] == "请先修复 FFprobe 或媒体诊断配置后，再重新导入视频。"
    assert import_stage["isCurrent"] is True

    import_rerun_response = client.post(
        f"/api/video-deconstruction/videos/{video_id}/stages/import/rerun"
    )
    assert import_rerun_response.status_code == 200
    assert import_rerun_response.json()["data"]["taskType"] == "video-import-stage"

    transcribe_stage = _stage_by_id(stages, "transcribe")
    assert transcribe_stage["status"] == "provider_required"
    assert transcribe_stage["resultSummary"] == PROVIDER_REQUIRED_MESSAGE
    assert transcribe_stage["errorMessage"] == transcribe_stage["resultSummary"]
    assert transcribe_stage["errorCode"] == "provider.required"
    assert transcribe_stage["nextAction"] == "请先配置可用视频解析模型后重试。"
    assert transcribe_stage["canRetry"] is True
    assert transcribe_stage["canCancel"] is False
    assert transcribe_stage["isCurrent"] is False

    rerun_response = client.post(
        f"/api/video-deconstruction/videos/{video_id}/stages/transcribe/rerun"
    )
    assert rerun_response.status_code == 200
    task_payload = rerun_response.json()["data"]
    assert task_payload["taskType"] == "video-import-stage"
    assert task_payload["projectId"] == project_id
    assert task_payload["status"] == "queued"

    segment_response = client.post(f"/api/video-deconstruction/videos/{video_id}/segment")
    assert segment_response.status_code == 200
    assert segment_response.json()["data"][0]["transcriptText"] is None

    stages_after_segment = client.get(
        f"/api/video-deconstruction/videos/{video_id}/stages"
    ).json()["data"]
    segment_stage = _stage_by_id(stages_after_segment, "segment")
    assert segment_stage["stageId"] == "segment"
    assert segment_stage["status"] == "succeeded"
    assert segment_stage["resultSummary"] == SEGMENT_WITHOUT_TRANSCRIPT_MESSAGE
    assert segment_stage["errorMessage"] is None
    assert segment_stage["blockedByStageId"] is None

    structure_response = client.post(
        f"/api/video-deconstruction/videos/{video_id}/extract-structure"
    )
    assert structure_response.status_code == 200
    assert structure_response.json()["data"]["status"] == "succeeded"

    stages_after_structure_block = client.get(
        f"/api/video-deconstruction/videos/{video_id}/stages"
    ).json()["data"]
    structure_stage = _stage_by_id(stages_after_structure_block, "extract_structure")
    assert structure_stage["stageId"] == "extract_structure"
    assert structure_stage["status"] == "succeeded"
    assert structure_stage["errorMessage"] is None


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

    blocked_apply_response = client.post(
        f"/api/video-deconstruction/extractions/extraction-{video_id}/apply-to-project"
    )
    assert blocked_apply_response.status_code == 409
    blocked_apply_payload = blocked_apply_response.json()
    assert blocked_apply_payload["ok"] is False
    assert blocked_apply_payload["error"] == APPLY_BLOCKED_MESSAGE
    assert blocked_apply_payload["error_code"] == "task.conflict"

    deconstruct_response = client.post(f"/api/video-deconstruction/videos/{video_id}/deconstruct")
    assert deconstruct_response.status_code == 200
    extraction_payload = deconstruct_response.json()["data"]["structure"]
    extraction_id = extraction_payload["id"]
    assert extraction_payload["status"] == "succeeded"

    apply_response = client.post(f"/api/video-deconstruction/extractions/{extraction_id}/apply-to-project")
    assert apply_response.status_code == 200
    apply_payload = apply_response.json()["data"]
    assert apply_payload["projectId"] == project_id
    assert apply_payload["scriptRevision"] == 1
    assert apply_payload["status"] == "applied"

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


def test_video_deconstruction_transcribes_when_provider_is_configured(
    runtime_app,
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)
    _enable_video_transcription(client)

    def fake_transcribe(self, *, file_path: str, base_url: str, api_key: str | None, model: str, timeout_seconds: int = 120):
        assert Path(file_path).name == "transcribe-success.mp4"
        assert base_url == "https://api.openai.com/v1/responses"
        assert api_key == "sk-test-video-transcription"
        assert model == "whisper-1"
        return SpeechToTextResult(text="This cup kept my iced coffee cold all day.", language="en")

    monkeypatch.setattr(
        "ai.providers.speech_to_text_openai.OpenAICompatibleSpeechToTextProvider.transcribe",
        fake_transcribe,
    )

    project_id = client.post(
        "/api/dashboard/projects",
        json={"name": "Transcribe Success", "description": "Provider configured"},
    ).json()["data"]["id"]
    video_path = tmp_path / "transcribe-success.mp4"
    video_path.write_bytes(b"\x00" * 4096)

    with patch("runtime_tasks.video_tasks.probe_video", return_value=None):
        import_response = client.post(
            f"/api/video-deconstruction/projects/{project_id}/import",
            json={"filePath": str(video_path)},
        )

    video_id = import_response.json()["data"]["id"]
    response = client.post(f"/api/video-deconstruction/videos/{video_id}/transcribe")

    assert response.status_code == 200
    transcript = response.json()["data"]
    assert transcript["status"] == "succeeded"
    assert transcript["language"] == "en"
    assert transcript["text"] == "This cup kept my iced coffee cold all day."

    segment_response = client.post(f"/api/video-deconstruction/videos/{video_id}/segment")
    assert segment_response.status_code == 200
    assert segment_response.json()["data"][0]["transcriptText"] == transcript["text"]


def test_video_deconstruction_uses_multimodal_model_without_transcription(
    runtime_app,
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)
    _enable_multimodal_asset_analysis(client)

    captured: dict[str, object] = {}
    calls: list[str] = []
    generated_payload = {
        "segments": [
            {
                "startMs": 0,
                "endMs": 3000,
                "visual": "手持冰霸杯特写，阳光下冰块反光。",
                "speech": "This is my spring addiction.",
                "onscreenText": "Spring addiction",
                "shotType": "特写",
                "intent": "开头钩子",
            },
            {
                "startMs": 3000,
                "endMs": 6000,
                "visual": "冰块倒入杯中，慢动作展示碰撞。",
                "speech": "Ice that stays cold for hours.",
                "onscreenText": "Cold for hours",
                "shotType": "近景",
                "intent": "卖点证明",
            },
        ],
        "summary": {
            "topic": "Spring Iced Coffee",
            "hook": "冰块不化",
        },
    }

    def fake_generate_text(self, capability_id, variables, *, project_id=None, request_id=None, media_inputs=()):
        calls.append(capability_id)
        if capability_id == "video_transcription":
            raise ProviderHTTPException(
                status_code=400,
                detail="当前 AI 能力已停用。",
                error_code="ai_capability_disabled",
            )
        captured["capability_id"] = capability_id
        captured["variables"] = variables
        captured["project_id"] = project_id
        captured["media_inputs"] = media_inputs
        return GeneratedTextResult(
            text=json.dumps(generated_payload, ensure_ascii=False),
            provider="volcengine",
            model="doubao-seed-2.0-pro-260215",
            ai_job_id="job-video-1",
        )

    monkeypatch.setattr(
        "services.ai_text_generation_service.AITextGenerationService.generate_text",
        fake_generate_text,
    )

    project_id = client.post(
        "/api/dashboard/projects",
        json={"name": "Multimodal Deconstruction", "description": "Use video model"},
    ).json()["data"]["id"]
    video_path = tmp_path / "multimodal-success.mp4"
    video_path.write_bytes(b"\x00" * 4096)

    with patch("runtime_tasks.video_tasks.probe_video", return_value=None):
        import_response = client.post(
            f"/api/video-deconstruction/projects/{project_id}/import",
            json={"filePath": str(video_path)},
        )

    video_id = import_response.json()["data"]["id"]
    response = client.post(f"/api/video-deconstruction/videos/{video_id}/deconstruct")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert calls == ["video_transcription", "asset_analysis"]
    assert captured["capability_id"] == "asset_analysis"
    assert captured["project_id"] == project_id
    variables = captured["variables"]
    assert VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT in variables["assets"]
    assert VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT in variables["assets"]
    assert "脚本文案" in variables["assets"]
    assert "视频关键帧" in variables["assets"]
    assert "内容结构" in variables["assets"]
    assert "不要把文件名、视频时长、分辨率当作主题、脚本、关键帧或内容结构" in variables["assets"]
    assert "按同一时间段把画面内容、口播语音、屏幕字幕放在同一个 keyframe" in variables["assets"]
    assert variables["assets"] == variables["media_file"]
    media_inputs = captured["media_inputs"]
    assert len(media_inputs) == 1
    assert media_inputs[0].kind == "video"
    assert payload["transcript"]["status"] == "skipped"
    assert payload["segments"][0]["transcriptText"] == "This is my spring addiction."
    assert payload["segments"][1]["metadataJson"]
    assert "手持冰霸杯特写" in payload["segments"][0]["metadataJson"]
    assert payload["script"]["title"] == "Spring Iced Coffee"
    assert payload["script"]["fullText"] == "This is my spring addiction.\nIce that stays cold for hours."
    assert payload["script"]["lines"][0]["text"] == "This is my spring addiction."
    assert payload["keyframes"][0]["visual"] == "手持冰霸杯特写，阳光下冰块反光。"
    assert payload["keyframes"][0]["speech"] == "This is my spring addiction."
    assert payload["keyframes"][1]["onscreenText"] == "Cold for hours"
    assert payload["contentStructure"]["topic"] == "Spring Iced Coffee"
    assert payload["contentStructure"]["hook"] == "冰块不化"
    assert payload["contentStructure"]["reusableForStoryboard"][0] == "手持冰霸杯特写，阳光下冰块反光。"
    assert payload["source"] == {
        "provider": "volcengine",
        "model": "doubao-seed-2.0-pro-260215",
        "promptVersion": "video_deconstruction_result_v1",
    }

    stages = payload["stages"]
    transcribe_stage = _stage_by_id(stages, "transcribe")
    segment_stage = _stage_by_id(stages, "segment")
    assert transcribe_stage["status"] == "skipped"
    assert transcribe_stage["resultSummary"] == TRANSCRIPT_SKIPPED_BY_MULTIMODAL_MESSAGE
    assert segment_stage["status"] == "succeeded"
    assert "2 个画面语音对齐片段" in segment_stage["resultSummary"]

    stored_segments = client.get(f"/api/video-deconstruction/videos/{video_id}/segments").json()["data"]
    assert len(stored_segments) == 2
    assert stored_segments[1]["transcriptText"] == "Ice that stays cold for hours."

    result_response = client.get(f"/api/video-deconstruction/videos/{video_id}/result")
    assert result_response.status_code == 200
    result_payload = result_response.json()["data"]
    assert result_payload["script"]["fullText"] == payload["script"]["fullText"]
    assert result_payload["keyframes"][1]["visual"] == "冰块倒入杯中，慢动作展示碰撞。"
    assert result_payload["contentStructure"]["topic"] == "Spring Iced Coffee"


def test_video_deconstruction_prefers_configured_video_parser_over_legacy_asset_analysis(
    runtime_app,
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)
    _enable_multimodal_video_transcription_with_legacy_asset_analysis(client)

    calls: list[str] = []
    generated_payload = {
        "script": {
            "title": "汽配厂发动机产品推广",
            "language": "中英双语",
            "fullText": "they are very complete 它们非常完整",
            "lines": [
                {
                    "startMs": 0,
                    "endMs": 3000,
                    "text": "they are very complete 它们非常完整",
                    "type": "speech",
                }
            ],
        },
        "keyframes": [
            {
                "index": 1,
                "startMs": 0,
                "endMs": 3000,
                "visual": "人物站在发动机仓库前介绍库存。",
                "speech": "they are very complete 它们非常完整",
                "onscreenText": "they are very complete",
                "shotType": "中景",
                "camera": "固定",
                "intent": "开场展示库存规模",
            }
        ],
        "contentStructure": {
            "topic": "汽配商家推广自有工厂发动机产品",
            "hook": "发动机库存完整",
            "painPoints": [],
            "sellingPoints": ["库存完整"],
            "rhythm": ["开场展示"],
            "cta": "请选择我",
            "reusableForScript": ["they are very complete"],
            "reusableForStoryboard": ["人物站在发动机仓库前介绍库存。"],
            "risks": [],
        },
        "segments": [
            {
                "startMs": 0,
                "endMs": 3000,
                "visual": "人物站在发动机仓库前介绍库存。",
                "speech": "they are very complete 它们非常完整",
                "onscreenText": "they are very complete",
                "shotType": "中景",
                "intent": "开场展示库存规模",
            }
        ],
        "summary": {"topic": "汽配商家推广自有工厂发动机产品"},
    }

    def fake_generate_text(self, capability_id, variables, *, project_id=None, request_id=None, media_inputs=()):
        calls.append(capability_id)
        if capability_id == "asset_analysis":
            return GeneratedTextResult(
                text="# 素材分析报告\n\n这是旧 Markdown 报告，不是视频拆解 JSON。",
                provider="volcengine",
                model="doubao-seed-1-6-vision-250815",
                ai_job_id="job-legacy-asset",
            )
        return GeneratedTextResult(
            text=json.dumps(generated_payload, ensure_ascii=False),
            provider="volcengine",
            model="doubao-seed-2-0-pro-260215",
            ai_job_id="job-video-parser",
        )

    monkeypatch.setattr(
        "services.ai_text_generation_service.AITextGenerationService.generate_text",
        fake_generate_text,
    )

    project_id = client.post(
        "/api/dashboard/projects",
        json={"name": "Prefer Video Parser", "description": "Use configured video parser"},
    ).json()["data"]["id"]
    video_path = tmp_path / "prefer-video-parser.mp4"
    video_path.write_bytes(b"\x00" * 4096)

    with patch("runtime_tasks.video_tasks.probe_video", return_value=None):
        import_response = client.post(
            f"/api/video-deconstruction/projects/{project_id}/import",
            json={"filePath": str(video_path)},
        )

    video_id = import_response.json()["data"]["id"]
    response = client.post(f"/api/video-deconstruction/videos/{video_id}/deconstruct")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert calls[0] == "video_transcription"
    assert "asset_analysis" not in calls
    assert payload["script"]["title"] == "汽配厂发动机产品推广"
    assert payload["keyframes"][0]["visual"] == "人物站在发动机仓库前介绍库存。"
    assert payload["contentStructure"]["topic"] == "汽配商家推广自有工厂发动机产品"


def test_video_deconstruction_does_not_treat_file_metadata_as_standard_result(
    runtime_app,
    tmp_path: Path,
) -> None:
    client = TestClient(runtime_app)

    project_id = client.post(
        "/api/dashboard/projects",
        json={"name": "Metadata Only", "description": "No usable AI result"},
    ).json()["data"]["id"]
    video_path = tmp_path / "Download.mp4"
    video_path.write_bytes(b"\x00" * 4096)

    with patch("runtime_tasks.video_tasks.probe_video", return_value=None):
        import_response = client.post(
            f"/api/video-deconstruction/projects/{project_id}/import",
            json={"filePath": str(video_path)},
        )

    video_id = import_response.json()["data"]["id"]
    response = client.post(f"/api/video-deconstruction/videos/{video_id}/deconstruct")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["script"]["title"] == ""
    assert payload["script"]["fullText"] == ""
    assert payload["script"]["lines"] == []
    assert payload["keyframes"] == []
    assert payload["contentStructure"]["topic"] == ""
    assert payload["contentStructure"]["hook"] == ""
    assert payload["contentStructure"]["cta"] == ""
