from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

SRC_DIR = Path(__file__).resolve().parents[2] / "apps" / "py-runtime" / "src"
ROUTES_DIR = SRC_DIR / "api" / "routes"
if str(ROUTES_DIR) not in sys.path:
    sys.path.insert(0, str(ROUTES_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from assets import router as assets_router
from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.asset_repository import AssetRepository
from schemas.assets import AssetCreateInput, AssetReferenceCreateInput
from schemas.envelope import error_response
from services.asset_service import AssetService


class RecordingTaskManager:
    def __init__(self) -> None:
        self.active_tasks: list[object] = []

    def list_active(self) -> list[object]:
        return list(self.active_tasks)

    def submit(self, **kwargs: object) -> object:
        task = type(
            "TaskInfo",
            (),
            {
                "id": kwargs.get("task_id"),
                "task_type": kwargs.get("task_type"),
                "status": "queued",
            },
        )()
        self.active_tasks.append(task)
        return task


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload["ok"] is True
    return payload["data"]


def _assert_asset_contract(asset: dict[str, object]) -> None:
    assert asset["id"]
    assert asset["name"]
    assert asset["sourceInfo"]["source"]
    assert asset["availability"]["status"]
    assert asset["referenceSummary"]["total"] >= 0
    assert isinstance(asset["referenceSummary"]["referenceTypes"], list)
    assert asset["thumbnailStatus"]["status"]


def _build_app(tmp_path: Path) -> FastAPI:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    repository = AssetRepository(session_factory=create_session_factory(engine))
    service = AssetService(repository, task_manager=RecordingTaskManager())

    source_file = tmp_path / "cover.png"
    source_file.write_bytes(b"cover-bytes")
    asset = service.create_asset(
        AssetCreateInput(
            name="cover.png",
            type="image",
            source="local",
            filePath=str(source_file),
            metadataJson='{"width":1080}',
        )
    )
    service.add_reference(
        asset.id,
        AssetReferenceCreateInput(
            referenceType="storyboard",
            referenceId="scene-1",
        ),
    )

    app = FastAPI()
    app.state.asset_service = service
    app.include_router(assets_router)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ):  # type: ignore[no-untyped-def]
        del request
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message),
        )

    return app


def test_assets_list_contract_returns_runtime_summaries(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/assets")

    assert response.status_code == 200
    assets = _assert_ok(response.json())
    assert len(assets) == 1
    _assert_asset_contract(assets[0])


def test_asset_detail_contract_returns_source_and_reference_summaries(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))
    asset_id = _assert_ok(client.get("/api/assets").json())[0]["id"]

    response = client.get(f"/api/assets/{asset_id}")

    assert response.status_code == 200
    asset = _assert_ok(response.json())
    _assert_asset_contract(asset)
    assert asset["sourceInfo"]["metadataSummary"] == {"width": 1080}
    assert asset["referenceSummary"]["blockingDelete"] is True


def test_asset_import_contract_returns_runtime_summaries(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    source_file = tmp_path / "clip.mp4"
    source_file.write_bytes(b"video-bytes")

    response = client.post(
        "/api/assets/import",
        json={
            "filePath": str(source_file),
            "type": "video",
            "source": "local",
            "metadataJson": '{"durationHint":1200}',
        },
    )

    assert response.status_code == 200
    asset = _assert_ok(response.json())
    _assert_asset_contract(asset)
    assert asset["availability"]["status"] == "ready"
    assert asset["sourceInfo"]["filePath"] == str(source_file)


def test_asset_references_contract_returns_existing_reference(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    asset_id = _assert_ok(client.get("/api/assets").json())[0]["id"]

    response = client.get(f"/api/assets/{asset_id}/references")

    assert response.status_code == 200
    refs = _assert_ok(response.json())
    assert len(refs) == 1
    assert refs[0]["referenceType"] == "storyboard"


def test_asset_delete_contract_returns_409_when_asset_is_referenced(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    asset_id = _assert_ok(client.get("/api/assets").json())[0]["id"]

    response = client.delete(f"/api/assets/{asset_id}")

    assert response.status_code == 409
    payload = response.json()
    assert payload["ok"] is False
    assert "资产存在引用" in payload["error"]
