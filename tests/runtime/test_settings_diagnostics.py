from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_settings_diagnostics_returns_system_check_report(
    monkeypatch,
    runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    monkeypatch.setattr(
        "services.settings_service.get_ffprobe_availability",
        lambda: type(
            "FfprobeAvailabilityStub",
            (),
            {
                "status": "ready",
                "path": "C:/TK-OPS/resources/bin/ffprobe/windows-x64/ffprobe.exe",
                "source": "bundled",
                "version": "ffprobe version test",
                "error_code": None,
                "error_message": None,
            },
        )(),
    )

    response = runtime_client.get("/api/settings/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["overallStatus"] in {"ready", "warning"}
    assert data["checkedAt"]
    assert data["databasePath"] == str(runtime_data_dir / "runtime.db")
    assert {item["id"] for item in data["items"]} >= {
        "license.status",
        "runtime.health",
        "database.sqlite",
        "directory.workspace",
        "directory.cache",
        "directory.logs",
        "media.ffprobe",
        "ai.provider",
        "ai.video_transcription",
        "websocket.task_bus",
    }
    ffprobe_item = next(item for item in data["items"] if item["id"] == "media.ffprobe")
    assert ffprobe_item["status"] == "ready"
    assert ffprobe_item["summary"] == "已检测到 FFprobe。"
    assert "bundled" in ffprobe_item["detail"]
    video_analysis_item = next(item for item in data["items"] if item["id"] == "ai.video_transcription")
    assert video_analysis_item["status"] == "warning"
    assert video_analysis_item["summary"] == "视频解析模型未启用。"


def test_settings_diagnostics_marks_ffprobe_warning_when_tool_is_missing(
    monkeypatch,
    runtime_client: TestClient,
) -> None:
    monkeypatch.setattr(
        "services.settings_service.get_ffprobe_availability",
        lambda: type(
            "FfprobeAvailabilityStub",
            (),
            {
                "status": "unavailable",
                "path": None,
                "source": "fallback",
                "version": None,
                "error_code": "media.ffprobe_unavailable",
                "error_message": "FFprobe 未安装或未配置到可执行路径。",
            },
        )(),
    )

    response = runtime_client.get("/api/settings/diagnostics")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["overallStatus"] == "warning"
    ffprobe_item = next(item for item in data["items"] if item["id"] == "media.ffprobe")
    assert ffprobe_item["status"] == "warning"
    assert ffprobe_item["actionLabel"] == "准备媒体工具"


def test_settings_diagnostics_rejects_unconnected_transcription_provider(
    runtime_client: TestClient,
) -> None:
    settings_response = runtime_client.get("/api/settings/ai-capabilities")
    capabilities = settings_response.json()["data"]["capabilities"]
    for item in capabilities:
        if item["capabilityId"] == "video_transcription":
            item.update(
                {
                    "enabled": True,
                    "provider": "volcengine_asr",
                    "model": "volcengine-asr",
                }
            )

    update_response = runtime_client.put(
        "/api/settings/ai-capabilities",
        json={"capabilities": capabilities},
    )
    assert update_response.status_code == 400
    assert update_response.json()["ok"] is False


def test_settings_diagnostics_accepts_multimodal_video_transcription_model(
    runtime_client: TestClient,
) -> None:
    settings_response = runtime_client.get("/api/settings/ai-capabilities")
    capabilities = settings_response.json()["data"]["capabilities"]
    for item in capabilities:
        if item["capabilityId"] == "asset_analysis":
            item["enabled"] = False
        if item["capabilityId"] == "video_transcription":
            item.update(
                {
                    "enabled": True,
                    "provider": "volcengine",
                    "model": "doubao-seed-2.0-pro",
                }
            )

    update_response = runtime_client.put(
        "/api/settings/ai-capabilities",
        json={"capabilities": capabilities},
    )
    assert update_response.status_code == 200
    secret_response = runtime_client.put(
        "/api/settings/ai-capabilities/providers/volcengine/secret",
        json={"apiKey": "sk-test", "baseUrl": "https://ark.cn-beijing.volces.com/api/v3"},
    )
    assert secret_response.status_code == 200

    response = runtime_client.get("/api/settings/diagnostics")

    assert response.status_code == 200
    video_analysis_item = next(
        item for item in response.json()["data"]["items"]
        if item["id"] == "ai.video_transcription"
    )
    assert video_analysis_item["status"] == "ready"
    assert video_analysis_item["summary"] == "视频解析模型已配置。"
    assert "doubao-seed-2.0-pro" in video_analysis_item["detail"]
