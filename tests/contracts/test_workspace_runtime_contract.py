from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTES_SRC = REPO_ROOT / "apps" / "py-runtime" / "src" / "api" / "routes"

if str(ROUTES_SRC) not in sys.path:
    sys.path.insert(0, str(ROUTES_SRC))

from assets import router as assets_router
from workspace import router as workspace_router
from common.time import utc_now_iso
from domain.models import Asset
from domain.models import Base
from domain.models import Project
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.asset_repository import AssetRepository
from repositories.timeline_repository import TimelineRepository
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from repositories.subtitle_repository import SubtitleRepository
from repositories.voice_repository import VoiceRepository
from schemas.envelope import error_response
from services.task_manager import TaskManager
from services.asset_service import AssetService
from services.workspace_assembly import WorkspaceAssemblyService
from services.workspace_service import WorkspaceService


def _assert_ok(payload: dict[str, object]) -> object:
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    return payload["data"]


def _assert_timeline_shape(timeline: dict[str, object]) -> None:
    assert set(timeline) == {
        "id",
        "projectId",
        "name",
        "status",
        "durationSeconds",
        "source",
        "tracks",
        "createdAt",
        "updatedAt",
        "version",
        "assetReferenceStatus",
    }
    assert set(timeline["version"]) == {
        "versionToken",
        "updatedAt",
        "trackCount",
        "clipCount",
    }
    assert set(timeline["assetReferenceStatus"]) == {
        "totalClips",
        "readyClips",
        "processingClips",
        "failedClips",
        "missingReferenceClips",
        "manualClips",
        "referencedClips",
    }


@pytest.fixture
def runtime_client(tmp_path):
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        now = utc_now_iso()
        session.add(
            Project(
                id="project-workspace",
                name="剪辑工作台项目",
                description="",
                status="active",
                current_script_version=0,
                current_storyboard_version=0,
                created_at=now,
                updated_at=now,
                last_accessed_at=now,
            )
        )
        session.commit()
    repository = TimelineRepository(session_factory=session_factory)
    script_repository = ScriptRepository(session_factory=session_factory)
    storyboard_repository = StoryboardRepository(session_factory=session_factory)
    voice_repository = VoiceRepository(session_factory=session_factory)
    subtitle_repository = SubtitleRepository(session_factory=session_factory)
    workspace_service = WorkspaceService(repository, task_manager=TaskManager())
    workspace_assembly_service = WorkspaceAssemblyService(
        timeline_repository=repository,
        script_repository=script_repository,
        storyboard_repository=storyboard_repository,
        voice_repository=voice_repository,
        subtitle_repository=subtitle_repository,
        workspace_service=workspace_service,
    )

    app = FastAPI()
    app.state.workspace_service = workspace_service
    app.state.workspace_assembly_service = workspace_assembly_service
    app.include_router(workspace_router)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request, exc):  # type: ignore[no-untyped-def]
        message = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message, error_code=getattr(exc, "error_code", None)),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request, exc):  # type: ignore[no-untyped-def]
        return JSONResponse(
            status_code=500,
            content=error_response("系统内部错误，请稍后重试"),
        )

    return TestClient(app)


@pytest.fixture
def runtime_client_with_assets(tmp_path):
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        now = utc_now_iso()
        session.add(
            Project(
                id="project-workspace",
                name="剪辑工作台项目",
                description="",
                status="active",
                current_script_version=0,
                current_storyboard_version=0,
                created_at=now,
                updated_at=now,
                last_accessed_at=now,
            )
        )
        session.commit()
    repository = TimelineRepository(session_factory=session_factory)
    asset_repository = AssetRepository(session_factory=session_factory)
    script_repository = ScriptRepository(session_factory=session_factory)
    storyboard_repository = StoryboardRepository(session_factory=session_factory)
    voice_repository = VoiceRepository(session_factory=session_factory)
    subtitle_repository = SubtitleRepository(session_factory=session_factory)
    workspace_service = WorkspaceService(
        repository,
        asset_repository=asset_repository,
        task_manager=TaskManager(),
    )
    workspace_assembly_service = WorkspaceAssemblyService(
        timeline_repository=repository,
        script_repository=script_repository,
        storyboard_repository=storyboard_repository,
        voice_repository=voice_repository,
        subtitle_repository=subtitle_repository,
        workspace_service=workspace_service,
    )

    app = FastAPI()
    app.state.asset_repository = asset_repository
    app.state.asset_service = AssetService(asset_repository)
    app.state.workspace_service = workspace_service
    app.state.workspace_assembly_service = workspace_assembly_service
    app.include_router(assets_router)
    app.include_router(workspace_router)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request, exc):  # type: ignore[no-untyped-def]
        message = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
        return JSONResponse(status_code=exc.status_code, content=error_response(message))

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request, exc):  # type: ignore[no-untyped-def]
        return JSONResponse(
            status_code=500,
            content=error_response("系统内部错误，请稍后重试"),
        )

    client = TestClient(app)
    client.workspace_tmp_path = tmp_path  # type: ignore[attr-defined]
    return client


def _create_workspace_timeline(runtime_client: TestClient) -> tuple[str, str]:
    create_response = runtime_client.post(
        "/api/workspace/projects/project-workspace/timeline",
        json={"name": "主时间线"},
    )
    assert create_response.status_code == 201
    timeline = _assert_ok(create_response.json())["timeline"]
    assert timeline is not None
    return "project-workspace", timeline["id"]


def _seed_timeline_with_clip(runtime_client: TestClient) -> tuple[str, str, str]:
    project_id, timeline_id = _create_workspace_timeline(runtime_client)

    update_response = runtime_client.patch(
        f"/api/workspace/timelines/{timeline_id}",
        json={
            "name": "主时间线",
            "durationSeconds": 12,
            "tracks": [
                {
                    "id": "track-video",
                    "kind": "video",
                    "name": "主画面",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-video-1",
                            "trackId": "track-video",
                            "sourceType": "manual",
                            "sourceId": None,
                            "label": "开场镜头",
                            "startMs": 0,
                            "durationMs": 4200,
                            "inPointMs": 0,
                            "outPointMs": None,
                            "status": "ready",
                            "prompt": "开场钩子",
                            "resolution": {"width": 1920, "height": 1080},
                            "editableFields": ["label", "startMs", "durationMs", "prompt"],
                        }
                    ],
                },
                {
                    "id": "track-audio",
                    "kind": "audio",
                    "name": "配音",
                    "orderIndex": 1,
                    "locked": False,
                    "muted": False,
                    "clips": [],
                },
            ],
        },
    )
    assert update_response.status_code == 200
    return project_id, timeline_id, "clip-video-1"


def _create_magic_cut_suggestion(runtime_client: TestClient):
    project_id, timeline_id, _ = _seed_timeline_with_clip(runtime_client)
    workspace_service = runtime_client.app.state.workspace_service
    timeline = workspace_service._load_timeline(timeline_id)
    suggestion = workspace_service._magic_cut_suggestion_service.create_from_operations(
        project_id,
        timeline,
        [{"action": "trim", "clipId": "clip-video-1", "startMs": 0, "durationMs": 3000}],
        "建议压缩开场。",
        None,
    )
    return project_id, timeline_id, suggestion


def _seed_contract_asset(
    runtime_client: TestClient,
    *,
    asset_id: str,
    asset_type: str,
    name: str,
    file_name: str,
    duration_ms: int | None,
) -> Path:
    tmp_path = runtime_client.workspace_tmp_path  # type: ignore[attr-defined]
    asset_path = Path(tmp_path) / file_name
    asset_path.write_bytes(b"contract asset")
    now = utc_now_iso()
    runtime_client.app.state.asset_repository.create_asset(
        Asset(
            id=asset_id,
            name=name,
            type=asset_type,
            source="local",
            group_id=None,
            file_path=str(asset_path),
            file_size_bytes=asset_path.stat().st_size,
            duration_ms=duration_ms,
            thumbnail_path=None,
            thumbnail_generated_at=None,
            tags=None,
            project_id="project-workspace",
            metadata_json=None,
            created_at=now,
            updated_at=now,
        )
    )
    return asset_path


def test_workspace_timeline_contract_returns_empty_state(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/workspace/projects/project-empty/timeline")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert set(data) == {"timeline", "activeTask", "saveState", "message"}
    assert data["timeline"] is None
    assert data["activeTask"] is None
    assert data["saveState"] is None
    assert "没有时间线" in data["message"]


def test_workspace_assembly_contract_returns_sources_and_timeline(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post(
        "/api/workspace/projects/project-workspace/timeline/assemble",
        json={"mode": "merge_managed", "timelineName": "主时间线"},
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert set(data) == {"timeline", "activeTask", "saveState", "assemblyState", "message"}
    assert data["timeline"] is not None
    assert data["saveState"]["source"] == "assembly"
    assert set(data["assemblyState"]) == {"status", "sources", "issues"}
    assert data["assemblyState"]["status"] == "warning"
    assert isinstance(data["assemblyState"]["sources"], list)
    assert "未生成 AI 三轨" in data["message"]
    assert "补齐来源" in data["message"]


def test_workspace_timeline_get_contract_returns_warning_assembly_state_after_missing_sources(
    runtime_client: TestClient,
) -> None:
    assemble_response = runtime_client.post(
        "/api/workspace/projects/project-workspace/timeline/assemble",
        json={"mode": "merge_managed", "timelineName": "主时间线"},
    )
    assert assemble_response.status_code == 200

    response = runtime_client.get("/api/workspace/projects/project-workspace/timeline")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert set(data) == {"timeline", "activeTask", "saveState", "assemblyState", "message"}
    assert data["timeline"] is not None
    assert data["timeline"]["tracks"] == []
    assert data["assemblyState"]["status"] == "warning"
    assert set(data["assemblyState"]) == {"status", "sources", "issues"}
    assert [source["status"] for source in data["assemblyState"]["sources"]] == [
        "missing",
        "missing",
        "missing",
        "missing",
    ]
    assert "缺少可用脚本。" in data["assemblyState"]["issues"]
    assert "缺少可用分镜。" in data["assemblyState"]["issues"]
    assert "缺少可用配音轨。" in data["assemblyState"]["issues"]
    assert "缺少可用字幕轨。" in data["assemblyState"]["issues"]


def test_workspace_timeline_contract_creates_and_updates_draft(
    runtime_client: TestClient,
) -> None:
    project_id, timeline_id = _create_workspace_timeline(runtime_client)

    update_response = runtime_client.patch(
        f"/api/workspace/timelines/{timeline_id}",
        json={
            "name": "主时间线",
            "durationSeconds": 12,
            "tracks": [
                {
                    "id": "track-video-1",
                    "kind": "video",
                    "name": "视频轨1",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-video-1",
                            "trackId": "track-video-1",
                            "sourceType": "manual",
                            "sourceId": None,
                            "label": "开场镜头",
                            "startMs": 0,
                            "durationMs": 4200,
                            "inPointMs": 0,
                            "outPointMs": None,
                            "status": "ready",
                            "prompt": "开场钩子",
                            "resolution": {"width": 1920, "height": 1080},
                            "editableFields": ["label", "startMs", "durationMs", "prompt"],
                        }
                    ],
                }
            ],
        },
    )

    assert update_response.status_code == 200
    update_data = _assert_ok(update_response.json())
    assert set(update_data) == {"timeline", "activeTask", "saveState", "message"}
    timeline = update_data["timeline"]
    _assert_timeline_shape(timeline)
    assert timeline["projectId"] == project_id
    assert timeline["version"]["trackCount"] == 1
    assert timeline["version"]["clipCount"] == 1
    assert timeline["assetReferenceStatus"] == {
        "totalClips": 1,
        "readyClips": 1,
        "processingClips": 0,
        "failedClips": 0,
        "missingReferenceClips": 0,
        "manualClips": 1,
        "referencedClips": 0,
    }
    assert timeline["tracks"][0]["clips"][0]["prompt"] == "开场钩子"
    assert timeline["tracks"][0]["clips"][0]["resolution"]["width"] == 1920
    assert timeline["tracks"][0]["clips"][0]["editableFields"] == [
        "label",
        "startMs",
        "durationMs",
        "prompt",
    ]
    assert update_data["activeTask"] is None
    assert update_data["saveState"]["saved"] is True
    assert update_data["saveState"]["source"] == "save"


def test_workspace_clip_contract_returns_detail_with_metadata(
    runtime_client: TestClient,
) -> None:
    _, _, clip_id = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.get(f"/api/workspace/clips/{clip_id}")

    assert response.status_code == 200
    clip = _assert_ok(response.json())
    assert clip["id"] == clip_id
    assert clip["prompt"] == "开场钩子"
    assert clip["resolution"]["width"] == 1920
    assert clip["editableFields"] == ["label", "startMs", "durationMs", "prompt"]


def test_workspace_clip_contract_exposes_move_and_trim_routes(
    runtime_client: TestClient,
) -> None:
    routes = {
        (route.path, ",".join(sorted(route.methods)))
        for route in runtime_client.app.routes
        if hasattr(route, "methods")
    }

    assert ("/api/workspace/clips/{clip_id}/move", "POST") in routes
    assert ("/api/workspace/clips/{clip_id}/trim", "POST") in routes
    assert ("/api/workspace/timelines/{timeline_id}/clips/insert-asset", "POST") in routes


def test_workspace_clip_contract_moves_clip_atomically(
    runtime_client: TestClient,
) -> None:
    _, _, clip_id = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/clips/{clip_id}/move",
        json={"targetTrackId": "track-audio", "startMs": 5200},
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    timeline = data["timeline"]
    moved_clip = timeline["tracks"][1]["clips"][0]
    assert moved_clip["id"] == clip_id
    assert moved_clip["trackId"] == "track-audio"
    assert moved_clip["startMs"] == 5200
    assert timeline["tracks"][0]["clips"] == []
    assert data["saveState"]["source"] == "clip_move"


def test_workspace_clip_contract_trims_clip_atomically(
    runtime_client: TestClient,
) -> None:
    _, _, clip_id = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/clips/{clip_id}/trim",
        json={
            "startMs": 900,
            "durationMs": 3000,
            "inPointMs": 120,
            "outPointMs": 3120,
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    timeline = data["timeline"]
    clip = timeline["tracks"][0]["clips"][0]
    assert clip["startMs"] == 900
    assert clip["durationMs"] == 3000
    assert clip["inPointMs"] == 120
    assert clip["outPointMs"] == 3120
    assert data["saveState"]["source"] == "clip_trim"


def test_workspace_clip_contract_replaces_clip_atomically(
    runtime_client: TestClient,
) -> None:
    _, _, clip_id = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/clips/{clip_id}/replace",
        json={
            "sourceType": "voice_track",
            "sourceId": "voice-track-1",
            "label": "新镜头",
            "prompt": "请使用更稳定的语气",
            "resolution": {"width": 1280, "height": 720},
            "editableFields": ["label", "prompt"],
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    timeline = data["timeline"]
    clip = timeline["tracks"][0]["clips"][0]
    assert clip["sourceType"] == "voice_track"
    assert clip["sourceId"] == "voice-track-1"
    assert clip["label"] == "新镜头"
    assert clip["prompt"] == "请使用更稳定的语气"
    assert clip["resolution"]["height"] == 720
    assert timeline["assetReferenceStatus"] == {
        "totalClips": 1,
        "readyClips": 1,
        "processingClips": 0,
        "failedClips": 0,
        "missingReferenceClips": 0,
        "manualClips": 0,
        "referencedClips": 1,
    }
    assert data["saveState"]["source"] == "clip_replace"


def test_workspace_clip_contract_inserts_asset_clip(
    runtime_client_with_assets: TestClient,
) -> None:
    _, timeline_id, _ = _seed_timeline_with_clip(runtime_client_with_assets)
    _seed_contract_asset(
        runtime_client_with_assets,
        asset_id="asset-contract-video",
        asset_type="video",
        name="合约素材.mp4",
        file_name="contract-video.mp4",
        duration_ms=1800,
    )

    response = runtime_client_with_assets.post(
        f"/api/workspace/timelines/{timeline_id}/clips/insert-asset",
        json={
            "assetId": "asset-contract-video",
            "targetTrackId": "track-video",
            "startMs": 4300,
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert set(data) == {"timeline", "activeTask", "saveState", "message"}
    timeline = data["timeline"]
    _assert_timeline_shape(timeline)
    inserted_clip = timeline["tracks"][0]["clips"][1]
    assert inserted_clip["id"] == "asset-asset-contract-video-4300"
    assert inserted_clip["sourceType"] == "asset"
    assert inserted_clip["sourceId"] == "asset-contract-video"
    assert inserted_clip["label"] == "合约素材.mp4"
    assert inserted_clip["startMs"] == 4300
    assert inserted_clip["durationMs"] == 1800
    assert data["saveState"]["source"] == "clip_insert_asset"


def test_workspace_clip_contract_deletes_clip_atomically(
    runtime_client: TestClient,
) -> None:
    _, _, clip_id = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.delete(f"/api/workspace/clips/{clip_id}")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    timeline = data["timeline"]
    assert timeline["tracks"][0]["clips"] == []
    assert timeline["version"]["clipCount"] == 0
    assert data["saveState"]["source"] == "clip_delete"


def test_workspace_clip_contract_splits_clip_atomically(
    runtime_client: TestClient,
) -> None:
    _, _, clip_id = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/clips/{clip_id}/split",
        json={"splitAtMs": 1800},
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    clips = data["timeline"]["tracks"][0]["clips"]
    assert [clip["id"] for clip in clips] == ["clip-video-1", "clip-video-1-split-1800"]
    assert clips[0]["durationMs"] == 1800
    assert clips[0]["outPointMs"] == 1800
    assert clips[1]["startMs"] == 1800
    assert clips[1]["durationMs"] == 2400
    assert clips[1]["inPointMs"] == 1800
    assert clips[1]["outPointMs"] == 4200
    assert data["saveState"]["source"] == "clip_split"


def test_workspace_timeline_preview_returns_local_summary_from_real_timeline(
    runtime_client: TestClient,
) -> None:
    _, timeline_id, _ = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.get(f"/api/workspace/timelines/{timeline_id}/preview")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["timelineId"] == timeline_id
    assert data["status"] == "structure_only"
    assert data["previewMode"] == "manifest"
    assert data["media"] is None
    assert data["error"] is None
    assert data["previewUrl"] is not None

    prefix, encoded_payload = data["previewUrl"].split(",", 1)
    assert prefix.startswith("data:application/json")
    assert not prefix.startswith(("data:video", "data:audio"))
    preview_payload = json.loads(unquote(encoded_payload))
    assert preview_payload["timelineId"] == timeline_id
    assert preview_payload["trackCount"] == 2
    assert preview_payload["clipCount"] == 1
    assert preview_payload["tracks"][0]["kind"] == "video"
    assert preview_payload["tracks"][0]["clipCount"] == 1
    assert preview_payload["tracks"][1]["kind"] == "audio"


def test_workspace_timeline_preview_duration_uses_timeline_end_for_parallel_tracks(
    runtime_client: TestClient,
) -> None:
    project_id, timeline_id = _create_workspace_timeline(runtime_client)
    update_response = runtime_client.patch(
        f"/api/workspace/timelines/{timeline_id}",
        json={
            "name": "主时间线",
            "durationSeconds": 12,
            "tracks": [
                {
                    "id": "track-video",
                    "kind": "video",
                    "name": "主画面",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-video-1",
                            "trackId": "track-video",
                            "sourceType": "manual",
                            "sourceId": None,
                            "label": "开场镜头",
                            "startMs": 0,
                            "durationMs": 12000,
                            "inPointMs": 0,
                            "outPointMs": None,
                            "status": "ready",
                        }
                    ],
                },
                {
                    "id": "track-subtitle",
                    "kind": "subtitle",
                    "name": "字幕轨",
                    "orderIndex": 1,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-subtitle-1",
                            "trackId": "track-subtitle",
                            "sourceType": "subtitle_track",
                            "sourceId": None,
                            "label": "字幕片段",
                            "startMs": 0,
                            "durationMs": 12000,
                            "inPointMs": 0,
                            "outPointMs": None,
                            "status": "ready",
                        }
                    ],
                },
            ],
        },
    )
    assert update_response.status_code == 200

    response = runtime_client.get(f"/api/workspace/timelines/{timeline_id}/preview")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["previewUrl"] is not None
    _, encoded_payload = data["previewUrl"].split(",", 1)
    preview_payload = json.loads(unquote(encoded_payload))
    assert preview_payload["trackCount"] == 2
    assert preview_payload["clipCount"] == 2
    assert preview_payload["tracks"][0]["clipDurationMs"] == 12000
    assert preview_payload["tracks"][1]["clipDurationMs"] == 12000
    assert preview_payload["totalClipDurationMs"] == 12000


def test_workspace_timeline_preview_returns_registered_asset_media(
    runtime_client_with_assets: TestClient,
) -> None:
    _, timeline_id, _ = _seed_timeline_with_clip(runtime_client_with_assets)
    asset_path = _seed_contract_asset(
        runtime_client_with_assets,
        asset_id="asset-contract-preview",
        asset_type="video",
        name="可播放素材.mp4",
        file_name="contract-preview.mp4",
        duration_ms=1800,
    )
    insert_response = runtime_client_with_assets.post(
        f"/api/workspace/timelines/{timeline_id}/clips/insert-asset",
        json={
            "assetId": "asset-contract-preview",
            "targetTrackId": "track-video",
            "startMs": 4300,
        },
    )
    assert insert_response.status_code == 200

    response = runtime_client_with_assets.get(f"/api/workspace/timelines/{timeline_id}/preview")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "ready"
    assert data["previewMode"] == "media"
    assert data["media"]["kind"] == "video"
    assert data["media"]["mimeType"] == "video/mp4"
    assert data["media"]["durationMs"] == 1800
    assert data["media"]["url"].startswith("/api/assets/asset-contract-preview/media?token=")
    assert data["media"]["source"] == "asset:asset-contract-preview"
    assert data["media"]["expiresAt"] is None
    assert str(asset_path) not in data["media"]["url"]
    assert "file://" not in data["media"]["url"]
    assert data["error"] is None

    media_response = runtime_client_with_assets.get(data["media"]["url"])
    assert media_response.status_code == 200
    assert media_response.headers["content-type"].startswith("video/mp4")
    assert media_response.content == asset_path.read_bytes()

    denied_response = runtime_client_with_assets.get("/api/assets/asset-contract-preview/media")
    assert denied_response.status_code == 403


def test_workspace_timeline_preview_returns_registered_audio_media(
    runtime_client_with_assets: TestClient,
) -> None:
    _, timeline_id, _ = _seed_timeline_with_clip(runtime_client_with_assets)
    asset_path = _seed_contract_asset(
        runtime_client_with_assets,
        asset_id="asset-contract-audio-preview",
        asset_type="audio",
        name="可播放配音.mp3",
        file_name="contract-preview.mp3",
        duration_ms=2400,
    )
    insert_response = runtime_client_with_assets.post(
        f"/api/workspace/timelines/{timeline_id}/clips/insert-asset",
        json={
            "assetId": "asset-contract-audio-preview",
            "targetTrackId": "track-audio",
            "startMs": 0,
        },
    )
    assert insert_response.status_code == 200

    response = runtime_client_with_assets.get(f"/api/workspace/timelines/{timeline_id}/preview")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "ready"
    assert data["previewMode"] == "media"
    assert data["media"]["kind"] == "audio"
    assert data["media"]["mimeType"] == "audio/mpeg"
    assert data["media"]["durationMs"] == 2400
    assert data["media"]["url"].startswith("/api/assets/asset-contract-audio-preview/media?token=")
    assert data["media"]["source"] == "asset:asset-contract-audio-preview"
    assert data["error"] is None

    media_response = runtime_client_with_assets.get(data["media"]["url"])
    assert media_response.status_code == 200
    assert media_response.headers["content-type"].startswith("audio/mpeg")
    assert media_response.content == asset_path.read_bytes()


def test_workspace_timeline_preview_marks_missing_asset_media_unavailable(
    runtime_client_with_assets: TestClient,
) -> None:
    _, timeline_id, _ = _seed_timeline_with_clip(runtime_client_with_assets)
    asset_path = _seed_contract_asset(
        runtime_client_with_assets,
        asset_id="asset-contract-missing-preview",
        asset_type="video",
        name="缺失预览素材.mp4",
        file_name="contract-missing-preview.mp4",
        duration_ms=2200,
    )
    asset_path.unlink()
    update_response = runtime_client_with_assets.patch(
        f"/api/workspace/timelines/{timeline_id}",
        json={
            "name": "主时间线",
            "durationSeconds": 12,
            "tracks": [
                {
                    "id": "track-video",
                    "kind": "video",
                    "name": "主画面",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-missing-preview",
                            "trackId": "track-video",
                            "sourceType": "asset",
                            "sourceId": "asset-contract-missing-preview",
                            "label": "缺失预览素材",
                            "startMs": 0,
                            "durationMs": 2200,
                            "inPointMs": 0,
                            "outPointMs": 2200,
                            "status": "ready",
                        }
                    ],
                }
            ],
        },
    )
    assert update_response.status_code == 200

    response = runtime_client_with_assets.get(f"/api/workspace/timelines/{timeline_id}/preview")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "unavailable"
    assert data["previewMode"] == "unavailable"
    assert data["previewUrl"] is not None
    assert data["media"] is None
    assert data["error"] == {
        "code": "preview.asset_file_missing",
        "message": "时间线包含资产片段，但源文件不可用，已保留结构预览。",
    }
    _, encoded_payload = data["previewUrl"].split(",", 1)
    preview_payload = json.loads(unquote(encoded_payload))
    assert preview_payload["timelineId"] == timeline_id
    assert preview_payload["clipCount"] == 1


def test_workspace_timeline_precheck_returns_local_status_from_real_timeline(
    runtime_client: TestClient,
) -> None:
    _, timeline_id, _ = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.post(f"/api/workspace/timelines/{timeline_id}/precheck")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["timelineId"] == timeline_id
    assert data["status"] == "ready"
    assert data["issues"] == []
    assert data["issueDetails"] == []
    assert "通过" in data["message"]


def test_workspace_timeline_precheck_reports_real_issues_for_empty_tracks(
    runtime_client: TestClient,
) -> None:
    _, timeline_id = _create_workspace_timeline(runtime_client)

    response = runtime_client.post(f"/api/workspace/timelines/{timeline_id}/precheck")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["timelineId"] == timeline_id
    assert data["status"] == "warning"
    assert data["issues"]
    assert data["issueDetails"][0]["targetType"] == "timeline"
    assert data["issueDetails"][0]["targetId"] == timeline_id
    assert any("轨道" in issue for issue in data["issues"])


def test_workspace_timeline_precheck_keeps_issues_and_adds_issue_details(
    runtime_client: TestClient,
) -> None:
    project_id, timeline_id = _create_workspace_timeline(runtime_client)
    update_response = runtime_client.patch(
        f"/api/workspace/timelines/{timeline_id}",
        json={
            "name": "主时间线",
            "durationSeconds": 12,
            "tracks": [
                {
                    "id": "track-video",
                    "kind": "video",
                    "name": "主画面",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-zero-duration",
                            "trackId": "track-video",
                            "sourceType": "manual",
                            "sourceId": None,
                            "label": "零时长片段",
                            "startMs": 0,
                            "durationMs": 0,
                            "inPointMs": 0,
                            "outPointMs": None,
                            "status": "ready",
                            "prompt": None,
                            "resolution": None,
                            "editableFields": ["label", "startMs", "durationMs"],
                        }
                    ],
                }
            ],
        },
    )
    assert update_response.status_code == 200

    response = runtime_client.post(f"/api/workspace/timelines/{timeline_id}/precheck")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["timelineId"] == timeline_id
    assert data["status"] == "warning"
    assert data["issues"] == ["片段 零时长片段 的时长无效。"]
    assert data["issueDetails"] == [
        {
            "id": "clip-zero-duration-duration",
            "severity": "warning",
            "message": "片段 零时长片段 的时长无效。",
            "targetType": "clip",
            "targetId": "clip-zero-duration",
            "trackId": "track-video",
            "clipId": "clip-zero-duration",
            "suggestion": "请调整片段时长后重新预检。",
            "actionLabel": "定位片段",
        }
    ]


def test_workspace_ai_command_returns_real_taskbus_task(
    runtime_client: TestClient,
) -> None:
    project_id, timeline_id = _create_workspace_timeline(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/projects/{project_id}/ai-commands",
        json={
            "timelineId": timeline_id,
            "capabilityId": "timeline_analysis",
            "parameters": {"selectedClipId": "clip-video-1"},
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "queued"
    assert data["task"] is not None
    assert data["task"]["kind"] == "ai-workspace-command"
    assert data["task"]["projectId"] == project_id
    assert data["task"]["ownerRef"] == {"kind": "timeline", "id": timeline_id}


def test_workspace_magic_cut_without_ready_ai_service_returns_error_envelope(
    runtime_client: TestClient,
) -> None:
    project_id, timeline_id = _create_workspace_timeline(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/projects/{project_id}/ai-commands",
        json={
            "timelineId": timeline_id,
            "capabilityId": "magic_cut",
            "parameters": {"selectedClipId": "clip-video-1"},
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "智能粗剪 Provider 未配置，请先选择可用文本模型。"
    assert payload["error_code"] == "workspace.ai_command_precheck_failed"


def test_workspace_latest_magic_cut_suggestion_returns_null_when_empty(
    runtime_client: TestClient,
) -> None:
    project_id, timeline_id, _ = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.get(
        f"/api/workspace/projects/{project_id}/magic-cut-suggestions/latest",
        params={"timelineId": timeline_id},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": None}


def test_workspace_magic_cut_suggestion_apply_contract(
    runtime_client: TestClient,
) -> None:
    project_id, timeline_id, suggestion = _create_magic_cut_suggestion(runtime_client)

    latest_response = runtime_client.get(
        f"/api/workspace/projects/{project_id}/magic-cut-suggestions/latest",
        params={"timelineId": timeline_id},
    )
    latest = _assert_ok(latest_response.json())
    assert latest["id"] == suggestion.id
    assert latest["status"] == "pending_review"
    assert latest["operations"][0]["id"] == "suggestion-trim-clip-video-1-1"

    response = runtime_client.post(
        f"/api/workspace/magic-cut-suggestions/{suggestion.id}/apply",
        json={
            "operationIds": [],
            "confirmTimelineVersionToken": suggestion.timelineVersionToken,
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert set(data) == {"suggestion", "timeline", "appliedCount", "failedCount", "message"}
    assert data["suggestion"]["status"] == "applied"
    assert data["appliedCount"] == 1
    assert data["failedCount"] == 0
    assert data["timeline"]["tracks"][0]["clips"][0]["durationMs"] == 3000


def test_workspace_magic_cut_suggestion_dismiss_contract(
    runtime_client: TestClient,
) -> None:
    _, _, suggestion = _create_magic_cut_suggestion(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/magic-cut-suggestions/{suggestion.id}/dismiss",
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["suggestion"]["status"] == "dismissed"
    assert data["message"] == "已忽略本次智能粗剪建议，时间线未修改。"


def test_workspace_magic_cut_suggestion_error_code_envelope(
    runtime_client: TestClient,
) -> None:
    _, _, suggestion = _create_magic_cut_suggestion(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/magic-cut-suggestions/{suggestion.id}/apply",
        json={
            "operationIds": ["missing-operation"],
            "confirmTimelineVersionToken": suggestion.timelineVersionToken,
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "智能粗剪建议内容无效，请重新生成。"
    assert payload["error_code"] == "workspace.magic_cut_invalid_operation"


def test_workspace_magic_cut_suggestion_stale_token_error_code(
    runtime_client: TestClient,
) -> None:
    _, timeline_id, suggestion = _create_magic_cut_suggestion(runtime_client)
    runtime_client.patch(
        f"/api/workspace/timelines/{timeline_id}",
        json={
            "name": "主时间线",
            "durationSeconds": 13,
            "tracks": [
                {
                    "id": "track-video",
                    "kind": "video",
                    "name": "主画面",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-video-1",
                            "trackId": "track-video",
                            "sourceType": "manual",
                            "sourceId": None,
                            "label": "开场镜头",
                            "startMs": 0,
                            "durationMs": 4200,
                            "inPointMs": 0,
                            "outPointMs": None,
                            "status": "ready",
                            "prompt": "开场钩子",
                            "resolution": {"width": 1920, "height": 1080},
                            "editableFields": ["label", "startMs", "durationMs", "prompt"],
                        }
                    ],
                },
                {
                    "id": "track-audio",
                    "kind": "audio",
                    "name": "配音",
                    "orderIndex": 1,
                    "locked": False,
                    "muted": False,
                    "clips": [],
                },
            ],
        },
    )

    response = runtime_client.post(
        f"/api/workspace/magic-cut-suggestions/{suggestion.id}/apply",
        json={
            "operationIds": [],
            "confirmTimelineVersionToken": suggestion.timelineVersionToken,
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "时间线已变化，请重新生成智能粗剪建议。"
    assert payload["error_code"] == "workspace.magic_cut_timeline_changed"


def test_workspace_ai_command_precheck_failure_returns_error_envelope(
    runtime_client: TestClient,
) -> None:
    class DisabledMagicCutService:
        def validate_text_generation_ready(self, capability_id: str) -> None:
            assert capability_id == "magic_cut"
            from ai.providers.errors import ProviderHTTPException

            raise ProviderHTTPException(
                status_code=400,
                detail="智能粗剪能力未启用，请先在 AI 与系统设置中启用并保存。",
                error_code="ai_capability_disabled",
            )

        def generate_text(self, *args, **kwargs):  # pragma: no cover - 预检失败不应入队
            raise AssertionError("预检失败不应进入后台 AI 调用")

    project_id, timeline_id = _create_workspace_timeline(runtime_client)
    runtime_client.app.state.workspace_service._ai_text_generation_service = DisabledMagicCutService()

    response = runtime_client.post(
        f"/api/workspace/projects/{project_id}/ai-commands",
        json={
            "timelineId": timeline_id,
            "capabilityId": "magic_cut",
            "parameters": {"selectedClipId": "clip-video-1"},
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "智能粗剪能力未启用，请先在 AI 与系统设置中启用并保存。"
    assert payload["error_code"] == "workspace.ai_command_precheck_failed"
