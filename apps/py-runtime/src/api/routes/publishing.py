from __future__ import annotations

from fastapi import APIRouter, Request, status

from schemas.envelope import ok_response
from schemas.publishing import PublishPlanCreateInput, PublishPlanUpdateInput
from services.publishing_service import PublishingService

router = APIRouter(prefix="/api/publishing/plans", tags=["publishing"])


def _svc(request: Request) -> PublishingService:
    return request.app.state.publishing_service  # type: ignore[no-any-return]


@router.get("/")
def list_plans(request: Request, status: str | None = None) -> dict[str, object]:
    plans = _svc(request).list_plans(status=status)
    return ok_response([plan.model_dump(mode="json") for plan in plans])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_plan(payload: PublishPlanCreateInput, request: Request) -> dict[str, object]:
    plan = _svc(request).create_plan(payload)
    return ok_response(plan.model_dump(mode="json"))


@router.get("/{plan_id}")
def get_plan(plan_id: str, request: Request) -> dict[str, object]:
    plan = _svc(request).get_plan(plan_id)
    return ok_response(plan.model_dump(mode="json"))


@router.patch("/{plan_id}")
def update_plan(
    plan_id: str,
    payload: PublishPlanUpdateInput,
    request: Request,
) -> dict[str, object]:
    plan = _svc(request).update_plan(plan_id, payload)
    return ok_response(plan.model_dump(mode="json"))


@router.delete("/{plan_id}")
def delete_plan(plan_id: str, request: Request) -> dict[str, object]:
    _svc(request).delete_plan(plan_id)
    return ok_response({"deleted": True})


@router.post("/{plan_id}/precheck")
def precheck(plan_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).precheck(plan_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/{plan_id}/submit")
def submit(plan_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).submit(plan_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/{plan_id}/cancel")
def cancel(plan_id: str, request: Request) -> dict[str, object]:
    plan = _svc(request).cancel(plan_id)
    return ok_response(plan.model_dump(mode="json"))
