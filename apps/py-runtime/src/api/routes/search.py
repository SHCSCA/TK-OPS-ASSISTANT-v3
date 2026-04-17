from __future__ import annotations

from fastapi import APIRouter, Query, Request

from schemas.envelope import ok_response
from services.search_service import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])


def get_search_service(request: Request) -> SearchService:
    search_service = request.app.state.search_service
    assert isinstance(search_service, SearchService)
    return search_service


@router.get("")
def search_runtime(
    request: Request,
    q: str = Query(min_length=1),
    types: str | None = None,
    limit: int = Query(default=5, ge=1, le=20),
) -> dict[str, object]:
    resolved_types = {item.strip() for item in types.split(",")} if types else None
    result = get_search_service(request).search(
        query=q,
        types=resolved_types,
        limit=limit,
    )
    return ok_response(result.model_dump(mode="json"))
