from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import Account, Asset, DeviceWorkspace, Project, ScriptVersion
from schemas.search import (
    GlobalSearchResultDto,
    SearchAccountResultDto,
    SearchAssetResultDto,
    SearchProjectResultDto,
    SearchScriptResultDto,
    SearchTaskResultDto,
    SearchWorkspaceResultDto,
)
from services.task_manager import TaskManager


class SearchService:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        task_manager: TaskManager,
    ) -> None:
        self._session_factory = session_factory
        self._task_manager = task_manager

    def search(
        self,
        *,
        query: str,
        types: set[str] | None = None,
        limit: int = 5,
    ) -> GlobalSearchResultDto:
        resolved_types = types or {
            "projects",
            "scripts",
            "tasks",
            "assets",
            "accounts",
            "workspaces",
        }
        pattern = f"%{query.strip()}%"

        with self._session_factory() as session:
            projects = (
                self._search_projects(session, pattern, limit)
                if "projects" in resolved_types
                else []
            )
            scripts = (
                self._search_scripts(session, pattern, limit)
                if "scripts" in resolved_types
                else []
            )
            assets = (
                self._search_assets(session, pattern, limit)
                if "assets" in resolved_types
                else []
            )
            accounts = (
                self._search_accounts(session, pattern, limit)
                if "accounts" in resolved_types
                else []
            )
            workspaces = (
                self._search_workspaces(session, pattern, limit)
                if "workspaces" in resolved_types
                else []
            )

        tasks = (
            self._search_tasks(query, limit)
            if "tasks" in resolved_types
            else []
        )

        return GlobalSearchResultDto(
            projects=projects,
            scripts=scripts,
            tasks=tasks,
            assets=assets,
            accounts=accounts,
            workspaces=workspaces,
        )

    def _search_projects(
        self,
        session: Session,
        pattern: str,
        limit: int,
    ) -> list[SearchProjectResultDto]:
        items = session.scalars(
            select(Project)
            .where(or_(Project.name.ilike(pattern), Project.description.ilike(pattern)))
            .order_by(Project.updated_at.desc())
            .limit(limit)
        ).all()
        return [
            SearchProjectResultDto(
                id=item.id,
                name=item.name,
                subtitle=item.description,
                updatedAt=item.updated_at,
            )
            for item in items
        ]

    def _search_scripts(
        self,
        session: Session,
        pattern: str,
        limit: int,
    ) -> list[SearchScriptResultDto]:
        items = session.scalars(
            select(ScriptVersion)
            .where(ScriptVersion.content.ilike(pattern))
            .order_by(ScriptVersion.created_at.desc())
            .limit(limit)
        ).all()
        return [
            SearchScriptResultDto(
                id=f"{item.project_id}:{item.revision}",
                projectId=item.project_id,
                title=_script_title(item.content),
                snippet=_script_snippet(item.content),
                updatedAt=item.created_at,
            )
            for item in items
        ]

    def _search_assets(
        self,
        session: Session,
        pattern: str,
        limit: int,
    ) -> list[SearchAssetResultDto]:
        items = session.scalars(
            select(Asset)
            .where(or_(Asset.name.ilike(pattern), Asset.tags.ilike(pattern)))
            .order_by(Asset.updated_at.desc())
            .limit(limit)
        ).all()
        return [
            SearchAssetResultDto(
                id=item.id,
                name=item.name,
                type=item.type,
                thumbnailUrl=item.thumbnail_path,
                updatedAt=item.updated_at,
            )
            for item in items
        ]

    def _search_accounts(
        self,
        session: Session,
        pattern: str,
        limit: int,
    ) -> list[SearchAccountResultDto]:
        items = session.scalars(
            select(Account)
            .where(or_(Account.name.ilike(pattern), Account.username.ilike(pattern)))
            .order_by(Account.updated_at.desc())
            .limit(limit)
        ).all()
        return [
            SearchAccountResultDto(
                id=item.id,
                name=item.name,
                status=item.status,
            )
            for item in items
        ]

    def _search_workspaces(
        self,
        session: Session,
        pattern: str,
        limit: int,
    ) -> list[SearchWorkspaceResultDto]:
        items = session.scalars(
            select(DeviceWorkspace)
            .where(
                or_(
                    DeviceWorkspace.name.ilike(pattern),
                    DeviceWorkspace.root_path.ilike(pattern),
                )
            )
            .order_by(DeviceWorkspace.updated_at.desc())
            .limit(limit)
        ).all()
        return [
            SearchWorkspaceResultDto(
                id=item.id,
                name=item.name,
                status=item.status,
            )
            for item in items
        ]

    def _search_tasks(self, query: str, limit: int) -> list[SearchTaskResultDto]:
        normalized = query.strip().lower()
        results: list[SearchTaskResultDto] = []
        for item in self._task_manager.list_tasks():
            haystacks = [
                item.kind or "",
                item.label or "",
                item.message or "",
            ]
            if not any(normalized in part.lower() for part in haystacks):
                continue
            results.append(
                SearchTaskResultDto(
                    id=item.id,
                    kind=item.kind or "generic",
                    label=item.label or item.message or "任务",
                    status=item.status,
                    updatedAt=item.updated_at,
                )
            )
            if len(results) >= limit:
                break
        return results


def _script_title(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:80]
    return "未命名脚本"


def _script_snippet(content: str) -> str:
    compact = " ".join(part.strip() for part in content.splitlines() if part.strip())
    return compact[:160]


def _to_iso(value: datetime | str | None) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return ""
