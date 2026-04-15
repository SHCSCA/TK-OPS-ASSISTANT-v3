from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.assets import AssetCreateInput, AssetReferenceCreateInput, AssetUpdateInput
from schemas.envelope import ok_response
from services.asset_service import AssetService

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _svc(request: Request) -> AssetService:
    return request.app.state.asset_service  # type: ignore[no-any-return]


@router.get("")
def list_assets(
    request: Request,
    type: str | None = None,
    source: str | None = None,
    project_id: str | None = None,
    q: str | None = None,
) -> dict[str, object]:
    assets = _svc(request).list_assets(asset_type=type, source=source, project_id=project_id, q=q)
    return ok_response([a.model_dump(mode="json") for a in assets])


@router.post("")
def create_asset(payload: AssetCreateInput, request: Request) -> dict[str, object]:
    asset = _svc(request).create_asset(payload)
    return ok_response(asset.model_dump(mode="json"))


@router.get("/references/{ref_id}")
def get_reference(ref_id: str, request: Request) -> dict[str, object]:
    # placeholder – individual reference fetch; DELETE is below
    raise NotImplementedError


@router.delete("/references/{ref_id}")
def delete_asset_reference(ref_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).delete_reference(ref_id)
    return ok_response(result)


@router.get("/{asset_id}")
def get_asset(asset_id: str, request: Request) -> dict[str, object]:
    asset = _svc(request).get_asset(asset_id)
    return ok_response(asset.model_dump(mode="json"))


@router.patch("/{asset_id}")
def update_asset(asset_id: str, payload: AssetUpdateInput, request: Request) -> dict[str, object]:
    asset = _svc(request).update_asset(asset_id, payload)
    return ok_response(asset.model_dump(mode="json"))


@router.delete("/{asset_id}")
def delete_asset(asset_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).delete_asset(asset_id)
    return ok_response(result)


@router.get("/{asset_id}/references")
def list_asset_references(asset_id: str, request: Request) -> dict[str, object]:
    refs = _svc(request).list_references(asset_id)
    return ok_response([r.model_dump(mode="json") for r in refs])


@router.post("/{asset_id}/references")
def add_asset_reference(asset_id: str, payload: AssetReferenceCreateInput, request: Request) -> dict[str, object]:
    ref = _svc(request).add_reference(asset_id, payload)
    return ok_response(ref.model_dump(mode="json"))
