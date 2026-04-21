from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.dashboard import CreateProjectInput, SetCurrentProjectInput
from schemas.envelope import ok_response
from services.dashboard_service import DashboardService

router = APIRouter(prefix='/api/dashboard', tags=['dashboard'])


def get_dashboard_service(request: Request) -> DashboardService:
    dashboard_service = request.app.state.dashboard_service
    assert isinstance(dashboard_service, DashboardService)
    return dashboard_service


@router.get('/summary')
def get_dashboard_summary(request: Request) -> dict[str, object]:
    summary = get_dashboard_service(request).get_summary()
    return ok_response(summary.model_dump(mode='json'))


@router.post('/projects')
def create_project(payload: CreateProjectInput, request: Request) -> dict[str, object]:
    project = get_dashboard_service(request).create_project(
        name=payload.name,
        description=payload.description,
    )
    return ok_response(project.model_dump(mode='json'))


@router.delete('/projects/{project_id}')
def delete_project(project_id: str, request: Request) -> dict[str, object]:
    result = get_dashboard_service(request).delete_project(project_id)
    return ok_response(result.model_dump(mode='json'))


@router.get('/context')
def get_current_project_context(request: Request) -> dict[str, object]:
    context = get_dashboard_service(request).get_current_project()
    return ok_response(context.model_dump(mode='json') if context else None)


@router.put('/context')
def set_current_project_context(
    payload: SetCurrentProjectInput,
    request: Request,
) -> dict[str, object]:
    context = get_dashboard_service(request).set_current_project(payload.projectId)
    return ok_response(context.model_dump(mode='json'))
