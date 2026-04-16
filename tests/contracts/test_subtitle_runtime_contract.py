from __future__ import annotations

from fastapi.testclient import TestClient


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload["ok"] is True
    assert "data" in payload
    return payload["data"]


def test_subtitle_track_generation_blocks_without_provider_and_preserves_segments(
    runtime_client: TestClient,
) -> None:
    project_response = runtime_client.post(
        "/api/dashboard/projects",
        json={"name": "字幕项目", "description": "覆盖字幕对齐契约"},
    )
    project_id = _assert_ok(project_response.json())["id"]

    response = runtime_client.post(
        f"/api/subtitles/projects/{project_id}/tracks/generate",
        json={
            "sourceText": "第一段脚本\n\n第二段脚本",
            "language": "zh-CN",
            "stylePreset": "creator-default",
        },
    )

    assert response.status_code == 200
    result = _assert_ok(response.json())
    track = result["track"]
    assert track["projectId"] == project_id
    assert track["status"] == "blocked"
    assert track["source"] == "script"
    assert track["language"] == "zh-CN"
    assert track["style"]["preset"] == "creator-default"
    assert track["segments"] == [
        {
            "segmentIndex": 0,
            "text": "第一段脚本",
            "startMs": None,
            "endMs": None,
            "confidence": None,
            "locked": False,
        },
        {
            "segmentIndex": 1,
            "text": "第二段脚本",
            "startMs": None,
            "endMs": None,
            "confidence": None,
            "locked": False,
        },
    ]
    assert result["task"] is None
    assert "字幕对齐 Provider" in result["message"]

    list_response = runtime_client.get(f"/api/subtitles/projects/{project_id}/tracks")
    assert list_response.status_code == 200
    tracks = _assert_ok(list_response.json())
    assert [item["id"] for item in tracks] == [track["id"]]

    detail_response = runtime_client.get(f"/api/subtitles/tracks/{track['id']}")
    assert detail_response.status_code == 200
    assert _assert_ok(detail_response.json())["segments"][0]["text"] == "第一段脚本"


def test_subtitle_track_update_and_delete_use_runtime_envelope(
    runtime_client: TestClient,
) -> None:
    project_response = runtime_client.post(
        "/api/dashboard/projects",
        json={"name": "字幕校正项目", "description": "覆盖字幕保存和删除"},
    )
    project_id = _assert_ok(project_response.json())["id"]
    create_response = runtime_client.post(
        f"/api/subtitles/projects/{project_id}/tracks/generate",
        json={
            "sourceText": "需要校正的字幕",
            "language": "zh-CN",
            "stylePreset": "creator-default",
        },
    )
    track_id = _assert_ok(create_response.json())["track"]["id"]

    update_response = runtime_client.patch(
        f"/api/subtitles/tracks/{track_id}",
        json={
            "segments": [
                {
                    "segmentIndex": 0,
                    "text": "校正后的字幕",
                    "startMs": 0,
                    "endMs": 2100,
                    "confidence": None,
                    "locked": True,
                }
            ],
            "style": {
                "preset": "creator-default",
                "fontSize": 36,
                "position": "bottom",
                "textColor": "#FFFFFF",
                "background": "rgba(0,0,0,0.62)",
            },
        },
    )

    assert update_response.status_code == 200
    updated = _assert_ok(update_response.json())
    assert updated["segments"][0]["text"] == "校正后的字幕"
    assert updated["segments"][0]["locked"] is True
    assert updated["style"]["fontSize"] == 36

    delete_response = runtime_client.delete(f"/api/subtitles/tracks/{track_id}")
    assert delete_response.status_code == 200
    assert _assert_ok(delete_response.json()) is None


def test_subtitle_track_generation_rejects_empty_source_text(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post(
        "/api/subtitles/projects/project-1/tracks/generate",
        json={
            "sourceText": "   \n  ",
            "language": "zh-CN",
            "stylePreset": "creator-default",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert "字幕源文本为空" in payload["error"]
