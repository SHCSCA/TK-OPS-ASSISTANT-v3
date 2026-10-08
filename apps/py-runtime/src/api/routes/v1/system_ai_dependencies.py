from __future__ import annotations

from typing import Annotated, Literal, Protocol, cast

from fastapi import APIRouter, Depends, Query, Request

from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import RequestContext, get_request_context
from api.routes.v1.ai_route_support import read_response, resolve_ai_service
from schemas.v1.ai_common import AISuccessEnvelope
from schemas.v1.ai_dependencies import DependencySnapshotDto

router = APIRouter(
    prefix="/api/v1/system/ai-dependencies",
    tags=["v1-system-ai-dependencies"],
    dependencies=[Depends(require_active_license)],
)


class AIDependencyPreviewServiceProtocol(Protocol):
    def preview(
        self,
        *,
        owner_type: Literal["route", "composition_template"],
        owner_id: str,
        owner_revision: int,
    ) -> object: ...


@router.get(
    "",
    response_model=AISuccessEnvelope[DependencySnapshotDto],
    response_model_exclude_unset=True,
)
def get_ai_dependency_preview(
    request: Request,
    owner_type: Annotated[
        Literal["route", "composition_template"],
        Query(alias="ownerType"),
    ],
    owner_id: Annotated[
        str,
        Query(alias="ownerId", min_length=1, max_length=128),
    ],
    owner_revision: Annotated[
        int,
        Query(alias="ownerRevision", ge=1),
    ],
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).preview(
        owner_type=owner_type,
        owner_id=owner_id,
        owner_revision=owner_revision,
    )
    return read_response(result, DependencySnapshotDto)


def _service(request: Request) -> AIDependencyPreviewServiceProtocol:
    return cast(
        AIDependencyPreviewServiceProtocol,
        resolve_ai_service(request, "dependencies"),
    )
