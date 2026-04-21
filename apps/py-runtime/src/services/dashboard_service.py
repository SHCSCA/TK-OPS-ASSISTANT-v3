from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException

from common.http_errors import RuntimeHTTPException
from repositories.dashboard_repository import DashboardRepository, StoredProject
from schemas.dashboard import (
    DashboardCurrentActionDto,
    DashboardPendingItemDto,
    DashboardRiskItemDto,
    DashboardRiskSummaryDto,
    CurrentProjectContextDto,
    DashboardSummaryDto,
    DashboardTaskDto,
    DeleteProjectResultDto,
    ProjectSummaryDto,
)
from services.task_manager import TaskManager


class DashboardService:
    def __init__(
        self,
        repository: DashboardRepository,
        *,
        task_manager: TaskManager | None = None,
    ) -> None:
        self._repository = repository
        self._task_manager = task_manager

    def get_summary(self) -> DashboardSummaryDto:
        generated_at = _utc_now()
        projects = self._repository.list_recent_projects()
        current_context = self._repository.get_current_project_context()
        current_project = None
        current_project_summary = None
        if current_context is not None:
            stored = self._repository.get_project(current_context.project_id)
            if stored is not None:
                current_project_summary = stored
                current_project = CurrentProjectContextDto(
                    projectId=stored.id,
                    projectName=stored.name,
                    status=stored.status,
                )

        recent_tasks = self._build_recent_tasks()
        pending_items = self._build_pending_items(
            projects=projects,
            current_project=current_project_summary,
            recent_tasks=recent_tasks,
        )
        risk_items = self._build_risk_items(
            current_project=current_project_summary,
            recent_tasks=recent_tasks,
        )
        current_action = self._build_current_action(
            projects=projects,
            current_project=current_project_summary,
            recent_tasks=recent_tasks,
        )

        return DashboardSummaryDto(
            recentProjects=[self._to_summary(item) for item in projects],
            currentProject=current_project,
            recentTasks=recent_tasks,
            pendingItems=pending_items,
            riskSummary=DashboardRiskSummaryDto(
                total=len(risk_items),
                blocking=sum(1 for item in risk_items if item.level == "danger"),
                items=risk_items,
            ),
            currentAction=current_action,
            generatedAt=generated_at,
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
            raise HTTPException(status_code=404, detail="未找到项目。")

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

    def delete_project(self, project_id: str) -> DeleteProjectResultDto:
        active_task = self._find_active_project_task(project_id)
        if active_task is not None:
            raise RuntimeHTTPException(
                status_code=409,
                detail="当前项目仍有未完成任务，暂时不能删除。",
                error_code="project.delete_blocked",
                details={
                    "next_action": "请先等待任务完成，或取消相关长任务后再删除项目。",
                    "task_id": active_task.id,
                    "status": active_task.status,
                },
            )

        try:
            deleted = self._repository.soft_delete_project(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="未找到项目。") from exc

        return DeleteProjectResultDto(
            deleted=True,
            projectId=deleted.project_id,
            clearedCurrentProject=deleted.cleared_current_project,
            deletedAt=deleted.deleted_at,
        )

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

    def _build_recent_tasks(self) -> list[DashboardTaskDto]:
        if self._task_manager is None:
            return []

        tasks = sorted(
            self._task_manager.list_active(),
            key=lambda item: getattr(item, "updated_at", ""),
            reverse=True,
        )
        return [
            DashboardTaskDto(
                taskId=getattr(task, "id"),
                taskType=getattr(task, "task_type"),
                projectId=getattr(task, "project_id"),
                status=getattr(task, "status"),
                progress=int(getattr(task, "progress")),
                message=getattr(task, "message"),
                createdAt=getattr(task, "created_at"),
                updatedAt=getattr(task, "updated_at"),
            )
            for task in tasks[:10]
        ]

    def _build_pending_items(
        self,
        *,
        projects: list[StoredProject],
        current_project: StoredProject | None,
        recent_tasks: list[DashboardTaskDto],
    ) -> list[DashboardPendingItemDto]:
        pending_items: list[DashboardPendingItemDto] = []

        if current_project is None:
            if projects:
                pending_items.append(
                    DashboardPendingItemDto(
                        id="select-current-project",
                        kind="project_context",
                        title="选择一个当前项目",
                        detail="当前还没有选中的项目上下文，先打开一个真实项目再继续主链路。",
                        action="select-project",
                        targetProjectId=projects[0].id,
                    )
                )
            else:
                pending_items.append(
                    DashboardPendingItemDto(
                        id="create-first-project",
                        kind="project_bootstrap",
                        title="创建第一个项目",
                        detail="创作总览还没有可继续的项目，先创建项目再进入脚本和分镜主链路。",
                        action="create-project",
                    )
                )
            return pending_items

        current_project_tasks = [
            task
            for task in recent_tasks
            if task.projectId == current_project.id
        ]
        if current_project_tasks:
            active_task = current_project_tasks[0]
            pending_items.append(
                DashboardPendingItemDto(
                    id=f"task-{active_task.taskId}",
                    kind="active_task",
                    title="当前项目有正在处理的任务",
                    detail=f"{active_task.taskType} 正处于 {active_task.status}，先处理当前任务再继续下一步。",
                    action="open-task",
                    targetProjectId=current_project.id,
                    targetTaskId=active_task.taskId,
                )
            )

        if current_project.current_script_version == 0:
            pending_items.append(
                DashboardPendingItemDto(
                    id="script-bootstrap",
                    kind="script",
                    title="先完成脚本版本",
                    detail="当前项目还没有脚本版本，先进入脚本与选题中心生成或保存第一版脚本。",
                    action="open-scripts",
                    targetProjectId=current_project.id,
                )
            )
        elif current_project.current_storyboard_version == 0:
            pending_items.append(
                DashboardPendingItemDto(
                    id="storyboard-bootstrap",
                    kind="storyboard",
                    title="继续分镜规划",
                    detail="脚本版本已经存在，但分镜版本仍为空，下一步应完成分镜规划。",
                    action="open-storyboards",
                    targetProjectId=current_project.id,
                )
            )

        return pending_items

    def _build_risk_items(
        self,
        *,
        current_project: StoredProject | None,
        recent_tasks: list[DashboardTaskDto],
    ) -> list[DashboardRiskItemDto]:
        risk_items: list[DashboardRiskItemDto] = []
        if current_project is None:
            return risk_items

        current_project_tasks = [
            task
            for task in recent_tasks
            if task.projectId == current_project.id
        ]
        for task in current_project_tasks:
            if task.status == "blocked":
                risk_items.append(
                    DashboardRiskItemDto(
                        id=f"blocked-{task.taskId}",
                        level="danger",
                        title="当前项目存在阻塞任务",
                        detail=f"{task.taskType} 已阻塞，先处理该任务后再继续项目推进。",
                        targetProjectId=current_project.id,
                        targetTaskId=task.taskId,
                    )
                )

        if current_project_tasks:
            active_task = current_project_tasks[0]
            risk_items.append(
                DashboardRiskItemDto(
                    id=f"delete-guard-{active_task.taskId}",
                    level="warning",
                    title="当前项目暂不支持删除",
                    detail="项目仍有未完成任务，删除操作会被后端阻断。",
                    targetProjectId=current_project.id,
                    targetTaskId=active_task.taskId,
                )
            )

        return risk_items

    def _build_current_action(
        self,
        *,
        projects: list[StoredProject],
        current_project: StoredProject | None,
        recent_tasks: list[DashboardTaskDto],
    ) -> DashboardCurrentActionDto:
        if current_project is None:
            if projects:
                return DashboardCurrentActionDto(
                    label="打开最近项目",
                    action="select-project",
                    targetProjectId=projects[0].id,
                )
            return DashboardCurrentActionDto(
                label="创建第一个项目",
                action="create-project",
            )

        current_project_tasks = [
            task
            for task in recent_tasks
            if task.projectId == current_project.id
        ]
        if current_project_tasks:
            active_task = current_project_tasks[0]
            return DashboardCurrentActionDto(
                label="继续当前任务",
                action="open-task",
                targetProjectId=current_project.id,
                targetTaskId=active_task.taskId,
            )

        if current_project.current_script_version == 0:
            return DashboardCurrentActionDto(
                label="去写脚本",
                action="open-scripts",
                targetProjectId=current_project.id,
            )

        if current_project.current_storyboard_version == 0:
            return DashboardCurrentActionDto(
                label="继续分镜规划",
                action="open-storyboards",
                targetProjectId=current_project.id,
            )

        return DashboardCurrentActionDto(
            label="进入 AI 剪辑工作台",
            action="open-workspace",
            targetProjectId=current_project.id,
        )

    def _find_active_project_task(self, project_id: str):  # type: ignore[no-untyped-def]
        if self._task_manager is None:
            return None

        for task in self._task_manager.list_active():
            if task.project_id == project_id and task.status in {"queued", "running", "blocked"}:
                return task
        return None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
