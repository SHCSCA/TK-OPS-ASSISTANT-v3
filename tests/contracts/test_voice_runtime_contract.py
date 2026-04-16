from __future__ import annotations

from fastapi.testclient import TestClient


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload["ok"] is True
    assert "data" in payload
    return payload["data"]


def test_voice_profiles_contract_returns_runtime_envelope(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/voice/profiles")

    assert response.status_code == 200
    profiles = _assert_ok(response.json())
    assert isinstance(profiles, list)
    assert profiles
    assert profiles[0]["id"] == "alloy-zh"
    assert profiles[0]["displayName"] == "清晰叙述"
    assert profiles[0]["provider"] == "pending_provider"


def test_voice_track_generation_blocks_without_provider_and_preserves_segments(
    runtime_client: TestClient,
) -> None:
    project_response = runtime_client.post(
        "/api/dashboard/projects",
        json={"name": "配音项目", "description": "覆盖配音中心契约"},
    )
    project_id = _assert_ok(project_response.json())["id"]

    response = runtime_client.post(
        f"/api/voice/projects/{project_id}/tracks/generate",
        json={
            "profileId": "alloy-zh",
            "sourceText": "第一段脚本\n\n第二段脚本",
            "speed": 1.0,
            "pitch": 0,
            "emotion": "calm",
        },
    )

    assert response.status_code == 200
    result = _assert_ok(response.json())
    track = result["track"]
    assert track["projectId"] == project_id
    assert track["status"] == "blocked"
    assert track["provider"] == "pending_provider"
    assert track["filePath"] is None
    assert track["segments"] == [
        {
            "segmentIndex": 0,
            "text": "第一段脚本",
            "startMs": None,
            "endMs": None,
            "audioAssetId": None,
        },
        {
            "segmentIndex": 1,
            "text": "第二段脚本",
            "startMs": None,
            "endMs": None,
            "audioAssetId": None,
        },
    ]
    assert result["task"] is None
    assert "TTS Provider" in result["message"]

    list_response = runtime_client.get(f"/api/voice/projects/{project_id}/tracks")
    assert list_response.status_code == 200
    tracks = _assert_ok(list_response.json())
    assert [item["id"] for item in tracks] == [track["id"]]

    detail_response = runtime_client.get(f"/api/voice/tracks/{track['id']}")
    assert detail_response.status_code == 200
    assert _assert_ok(detail_response.json())["segments"][0]["text"] == "第一段脚本"

    delete_response = runtime_client.delete(f"/api/voice/tracks/{track['id']}")
    assert delete_response.status_code == 200
    assert _assert_ok(delete_response.json()) is None


def test_voice_track_generation_rejects_empty_source_text(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post(
        "/api/voice/projects/project-1/tracks/generate",
        json={
            "profileId": "alloy-zh",
            "sourceText": "   \n  ",
            "speed": 1.0,
            "pitch": 0,
            "emotion": "calm",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert "脚本文本为空" in payload["error"]
