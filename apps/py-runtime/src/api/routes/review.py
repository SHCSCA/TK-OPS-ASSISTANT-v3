from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import ok_response
from schemas.review import ReviewSummaryUpdateInput
from services.review_service import ReviewService

router = APIRouter(prefix="/api/review", tags=["review"])


def _svc(request: Request) -> ReviewService:
    return request.app.state.review_service  # type: ignore[no-any-return]


@router.get("/projects/{project_id}/summary")
def get_summary(project_id: str, request: Request) -> dict[str, object]:
    summary = _svc(request).get_summary(project_id)
    return ok_response(summary.model_dump(mode="json"))


@router.post("/projects/{project_id}/analyze")
def analyze(project_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).analyze(project_id)
    return ok_response(result.model_dump(mode="json"))


@router.patch("/projects/{project_id}/summary")
def update_summary(
    project_id: str,
    payload: ReviewSummaryUpdateInput,
    request: Request,
) -> dict[str, object]:
    summary = _svc(request).update_summary(project_id, payload)
    return ok_response(summary.model_dump(mode="json"))
