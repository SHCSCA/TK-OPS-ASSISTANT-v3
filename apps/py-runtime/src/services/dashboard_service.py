from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi import HTTPException

from repositories.dashboard_repository import DashboardRepository, StoredProject
from schemas.dashboard import (
    CurrentProjectContextDto,
    DashboardGreetingDto,
    DashboardHealthDto,
    DashboardHeroActionDto,
    DashboardHeroContextDto,
    DashboardHeroProjectDto,
    DashboardSummaryDto,
    ProjectSummaryDto,
)
from services.ws_manager import ws_manager


class DashboardService:
    def __init__(self, repository: DashboardRepository) -> None:
        self._repository = repository

    def get_summary(self) -> DashboardSummaryDto:
        projects = self._repository.list_recent_projects()
        current_context = self.get_current_project()
        current_project = None
        if current_context is not None:
            stored = self._repository.get_project(current_context.projectId)
            if stored is not None:
                current_project = DashboardHeroProjectDto(
                    id=stored.id,
                    name=stored.name,
                    status=stored.status,
                    lastEditedAt=stored.updated_at,
                )

        return DashboardSummaryDto(
            recentProjects=[self._to_summary(item) for item in projects],
            currentProject=current_context,
            greeting=self._build_greeting(),
            heroContext=DashboardHeroContextDto(
                currentProject=current_project,
                primaryAction=DashboardHeroActionDto(
                    label="继续项目" if current_project else "新建项目",
                    action="resume-project" if current_project else "create-project",
                    targetProjectId=current_project.id if current_project else None,
                ),
                pendingTasks=0,
                blockingIssues=0,
            ),
            todos=[],
            exceptions=[],
            health=DashboardHealthDto(
                runtimeStatus="online",
                aiProviderStatus="ready",
                taskBusStatus="idle",
            ),
            generatedAt=_utc_now(),
        )

    def create_project(self, *, name: str, description: str) -> ProjectSummaryDto:
        stored = self._repository.create_project(name=name, description=description)
        self.set_current_project(stored.id)
        refreshed = self._repository.get_project(stored.id)
        assert refreshed is not None
        return self._to_summary(refreshed)

    def set_current_project(
        self,
        project_id: str | None,
    ) -> CurrentProjectContextDto | None:
        if project_id is None:
            self._repository.clear_current_project()
            self._broadcast_context_changed(None)
            return None

        project = self._repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="未找到项目。")

        self._repository.set_current_project(project_id)
        refreshed = self._repository.get_project(project_id)
        assert refreshed is not None
        context = self._to_context(refreshed)
        self._broadcast_context_changed(context)
        return context

    def get_current_project(self) -> CurrentProjectContextDto | None:
        current_context = self._repository.get_current_project_context()
        if current_context is None or current_context.project_id is None:
            return None

        project = self._repository.get_project(current_context.project_id)
        if project is None:
            return None

        return self._to_context(project)

    def require_project(self, project_id: str) -> ProjectSummaryDto:
        project = self._repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="未找到项目。")

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
            raise HTTPException(status_code=404, detail="未找到项目。") from exc

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

    def _to_context(self, stored: StoredProject) -> CurrentProjectContextDto:
        return CurrentProjectContextDto(
            projectId=stored.id,
            projectName=stored.name,
            status=stored.status,
        )

    def _build_greeting(self) -> DashboardGreetingDto:
        hour = datetime.now(UTC).hour
        if hour < 6:
            title = "夜间创作"
        elif hour < 12:
            title = "上午进度"
        elif hour < 18:
            title = "下午推进"
        else:
            title = "晚间收口"

        return DashboardGreetingDto(
            title=title,
            subtitle="聚焦当前项目与核心任务。",
        )

    def _broadcast_context_changed(
        self,
        context: CurrentProjectContextDto | None,
    ) -> None:
        asyncio.run(
            ws_manager.broadcast(
                {
                    "type": "context.project.changed",
                    "payload": context.model_dump(mode="json") if context else None,
                }
            )
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
