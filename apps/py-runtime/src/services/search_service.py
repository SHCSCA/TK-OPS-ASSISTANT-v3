from __future__ import annotations

import re
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now_iso
from domain.models import (
    Account,
    Asset,
    AutomationTask,
    DeviceWorkspace,
    Project,
    RenderTask,
    ScriptVersion,
)
from schemas.search import (
    GlobalSearchResultDto,
    SearchAccountResultDto,
    SearchAssetResultDto,
    SearchProjectResultDto,
    SearchScriptResultDto,
    SearchTaskResultDto,
    SearchWorkspaceResultDto,
)

SUPPORTED_TYPES = (
    "projects",
    "scripts",
    "tasks",
    "assets",
    "accounts",
    "workspaces",
)


class SearchService:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def search(
        self,
        q: str,
        *,
        types: list[str] | None = None,
        limit: int = 5,
    ) -> GlobalSearchResultDto:
        keyword = q.strip()
        if not keyword:
            raise HTTPException(status_code=422, detail="搜索关键词不能为空")

        selected_types = self._normalize_types(types)

        return GlobalSearchResultDto(
            projects=self._search_projects(keyword, limit) if "projects" in selected_types else [],
            scripts=self._search_scripts(keyword, limit) if "scripts" in selected_types else [],
            tasks=self._search_tasks(keyword, limit) if "tasks" in selected_types else [],
            assets=self._search_assets(keyword, limit) if "assets" in selected_types else [],
            accounts=self._search_accounts(keyword, limit) if "accounts" in selected_types else [],
            workspaces=self._search_workspaces(keyword, limit) if "workspaces" in selected_types else [],
        )

    def _normalize_types(self, types: list[str] | None) -> set[str]:
        if not types:
            return set(SUPPORTED_TYPES)

        selected: set[str] = set()
        for raw_value in types:
            for value in raw_value.split(","):
                normalized = value.strip().lower()
                if not normalized:
                    continue
                if normalized not in SUPPORTED_TYPES:
                    raise HTTPException(status_code=422, detail=f"不支持的搜索类型: {normalized}")
                selected.add(normalized)
        return selected or set(SUPPORTED_TYPES)

    def _search_projects(self, q: str, limit: int) -> list[SearchProjectResultDto]:
        pattern = f"%{q}%"
        with self._session_factory() as session:
            rows = session.scalars(
                select(Project)
                .where(or_(Project.name.ilike(pattern), Project.description.ilike(pattern)))
                .order_by(Project.updated_at.desc(), Project.last_accessed_at.desc())
                .limit(limit)
            ).all()
        return [
            SearchProjectResultDto(
                id=row.id,
                name=row.name,
                subtitle=self._build_subtitle(row.description, row.status),
                updatedAt=row.updated_at,
            )
            for row in rows
        ]

    def _search_scripts(self, q: str, limit: int) -> list[SearchScriptResultDto]:
        pattern = f"%{q}%"
        with self._session_factory() as session:
            rows = session.execute(
                select(Project, ScriptVersion)
                .join(ScriptVersion, ScriptVersion.project_id == Project.id)
                .where(
                    or_(
                        Project.name.ilike(pattern),
                        Project.description.ilike(pattern),
                        ScriptVersion.content.ilike(pattern),
                    )
                )
                .order_by(ScriptVersion.created_at.desc())
                .limit(limit)
            ).all()
        result: list[SearchScriptResultDto] = []
        for project, version in rows:
            result.append(
                SearchScriptResultDto(
                    id=f"{project.id}:{version.revision}",
                    projectId=project.id,
                    title=self._script_title(version.content, project.name),
                    snippet=self._script_snippet(version.content),
                    updatedAt=version.created_at,
                )
            )
        return result

    def _search_tasks(self, q: str, limit: int) -> list[SearchTaskResultDto]:
        pattern = f"%{q}%"
        render_rows = self._search_render_tasks(pattern, limit)
        automation_rows = self._search_automation_tasks(pattern, limit)
        merged = sorted(
            [*render_rows, *automation_rows],
            key=lambda item: item[0],
            reverse=True,
        )
        return [item[1] for item in merged[:limit]]

    def _search_render_tasks(
        self,
        pattern: str,
        limit: int,
    ) -> list[tuple[str, SearchTaskResultDto]]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(RenderTask)
                .where(
                    or_(
                        RenderTask.project_name.ilike(pattern),
                        RenderTask.project_id.ilike(pattern),
                        RenderTask.preset.ilike(pattern),
                        RenderTask.format.ilike(pattern),
                        RenderTask.status.ilike(pattern),
                    )
                )
                .order_by(RenderTask.updated_at.desc())
                .limit(limit)
            ).all()
        return [
            (
                self._format_datetime(row.updated_at),
                SearchTaskResultDto(
                    id=row.id,
                    kind="render",
                    label=row.project_name or f"渲染任务 {row.id}",
                    status=row.status,
                    updatedAt=self._format_datetime(row.updated_at),
                ),
            )
            for row in rows
        ]

    def _search_automation_tasks(
        self,
        pattern: str,
        limit: int,
    ) -> list[tuple[str, SearchTaskResultDto]]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(AutomationTask)
                .where(
                    or_(
                        AutomationTask.name.ilike(pattern),
                        AutomationTask.type.ilike(pattern),
                        AutomationTask.last_run_status.ilike(pattern),
                    )
                )
                .order_by(AutomationTask.updated_at.desc())
                .limit(limit)
            ).all()
        return [
            (
                self._format_datetime(row.updated_at),
                SearchTaskResultDto(
                    id=row.id,
                    kind="automation",
                    label=f"{row.name} · {row.type}",
                    status=row.last_run_status or ("enabled" if row.enabled else "disabled"),
                    updatedAt=self._format_datetime(row.updated_at),
                ),
            )
            for row in rows
        ]

    def _search_assets(self, q: str, limit: int) -> list[SearchAssetResultDto]:
        pattern = f"%{q}%"
        with self._session_factory() as session:
            rows = session.scalars(
                select(Asset)
                .where(
                    or_(
                        Asset.name.ilike(pattern),
                        Asset.tags.ilike(pattern),
                        Asset.metadata_json.ilike(pattern),
                    )
                )
                .order_by(Asset.updated_at.desc())
                .limit(limit)
            ).all()
        return [
            SearchAssetResultDto(
                id=row.id,
                name=row.name,
                type=row.type,
                thumbnailUrl=row.thumbnail_path,
                updatedAt=row.updated_at,
            )
            for row in rows
        ]

    def _search_accounts(self, q: str, limit: int) -> list[SearchAccountResultDto]:
        pattern = f"%{q}%"
        with self._session_factory() as session:
            rows = session.scalars(
                select(Account)
                .where(
                    or_(
                        Account.name.ilike(pattern),
                        Account.username.ilike(pattern),
                        Account.tags.ilike(pattern),
                        Account.notes.ilike(pattern),
                    )
                )
                .order_by(Account.updated_at.desc())
                .limit(limit)
            ).all()
        return [
            SearchAccountResultDto(
                id=row.id,
                name=row.name,
                status=row.status,
            )
            for row in rows
        ]

    def _search_workspaces(self, q: str, limit: int) -> list[SearchWorkspaceResultDto]:
        pattern = f"%{q}%"
        with self._session_factory() as session:
            rows = session.scalars(
                select(DeviceWorkspace)
                .where(
                    or_(
                        DeviceWorkspace.name.ilike(pattern),
                        DeviceWorkspace.root_path.ilike(pattern),
                        DeviceWorkspace.status.ilike(pattern),
                    )
                )
                .order_by(DeviceWorkspace.updated_at.desc())
                .limit(limit)
            ).all()
        return [
            SearchWorkspaceResultDto(
                id=row.id,
                name=row.name,
                status=row.status,
            )
            for row in rows
        ]

    def _build_subtitle(self, description: str, status: str) -> str:
        trimmed = description.strip()
        if trimmed:
            return trimmed
        return f"状态：{status}"

    def _script_title(self, content: str, fallback: str) -> str:
        first_line = self._first_line(content)
        return first_line or fallback

    def _script_snippet(self, content: str) -> str:
        normalized = re.sub(r"\s+", " ", content).strip()
        return normalized[:140]

    def _first_line(self, content: str) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped[:80]
        return ""

    def _format_datetime(self, value: datetime) -> str:
        return value.isoformat().replace("+00:00", "Z")
