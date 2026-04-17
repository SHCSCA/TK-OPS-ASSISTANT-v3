from __future__ import annotations

from fastapi import HTTPException

from repositories.dashboard_repository import DashboardRepository, StoredProject
from schemas.dashboard import CurrentProjectContextDto, DashboardSummaryDto, ProjectSummaryDto


class DashboardService:
    def __init__(self, repository: DashboardRepository) -> None:
        self._repository = repository

    def get_summary(self) -> DashboardSummaryDto:
        projects = self._repository.list_recent_projects()
        current_context = self._repository.get_current_project_context()
        current_project = None
        if current_context is not None:
            stored = self._repository.get_project(current_context.project_id)
            if stored is not None:
                current_project = CurrentProjectContextDto(
                    projectId=stored.id,
                    projectName=stored.name,
                    status=stored.status,
                )

        return DashboardSummaryDto(
            recentProjects=[self._to_summary(item) for item in projects],
            currentProject=current_project,
        )

    def create_project(self, *, name: str, description: str) -> ProjectSummaryDto:
        stored = self._repository.create_project(name=name, description=description)
        self._repository.set_current_project(stored.id)
        refreshed = self._repository.get_project(stored.id)
        assert refreshed is not None
        return self._to_summary(refreshed)

    def set_current_project(self, project_id: str) -> CurrentProjectContextDto:
        project = self._repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail='未找到项目。')

        self._repository.set_current_project(project_id)
        refreshed = self._repository.get_project(project_id)
        assert refreshed is not None
        return CurrentProjectContextDto(
            projectId=refreshed.id,
            projectName=refreshed.name,
            status=refreshed.status,
        )

    def get_current_project(self) -> CurrentProjectContextDto | None:
        current_context = self._repository.get_current_project_context()
        if current_context is None:
            return None

        project = self._repository.get_project(current_context.project_id)
        if project is None:
            return None

        return CurrentProjectContextDto(
            projectId=project.id,
            projectName=project.name,
            status=project.status,
        )

    def require_project(self, project_id: str) -> ProjectSummaryDto:
        project = self._repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail='未找到项目。')

        return self._to_summary(project)

    def update_project_versions(
        self,
        project_id: str,
        *,
        current_script_version: int | None = None,
        current_storyboard_version: int | None = None,
    ) -> ProjectSummaryDto:
        try:
            updated = self._repository.update_project_versions(
                project_id,
                current_script_version=current_script_version,
                current_storyboard_version=current_storyboard_version,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='未找到项目。') from exc

        return self._to_summary(updated)

    def _to_summary(self, stored: StoredProject) -> ProjectSummaryDto:
        return ProjectSummaryDto(
            id=stored.id,
            name=stored.name,
            description=stored.description,
            status=stored.status,
            currentScriptVersion=stored.current_script_version,
            currentStoryboardVersion=stored.current_storyboard_version,
            createdAt=stored.created_at,
            updatedAt=stored.updated_at,
            lastAccessedAt=stored.last_accessed_at,
        )
