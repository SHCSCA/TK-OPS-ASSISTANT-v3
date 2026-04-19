from __future__ import annotations

from fastapi import APIRouter, Query, Request

from schemas.envelope import ok_response
from schemas.search import GlobalSearchResultDto
from services.search_service import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])


def _svc(request: Request) -> SearchService:
    return request.app.state.search_service  # type: ignore[no-any-return]


@router.get("")
def search_global(
    request: Request,
    q: str = Query(min_length=1),
    types: list[str] | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
) -> dict[str, object]:
    result = _svc(request).search(q, types=types, limit=limit)
    assert isinstance(result, GlobalSearchResultDto)
    return ok_response(result.model_dump(mode="json"))

