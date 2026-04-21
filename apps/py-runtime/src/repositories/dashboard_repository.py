from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import Project, SessionContext
from domain.models.base import generate_uuid


@dataclass(frozen=True, slots=True)
class StoredProject:
    id: str
    name: str
    description: str
    status: str
    current_script_version: int
    current_storyboard_version: int
    created_at: str
    updated_at: str
    last_accessed_at: str


@dataclass(frozen=True, slots=True)
class StoredProjectContext:
    project_id: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class DeletedProjectResult:
    project_id: str
    deleted_at: str
    cleared_current_project: bool


class DashboardRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_recent_projects(self, *, limit: int = 10) -> list[StoredProject]:
        with self._session_factory() as session:
            projects = session.scalars(
                select(Project)
                .where(Project.deleted_at.is_(None))
                .order_by(Project.last_accessed_at.desc(), Project.updated_at.desc())
                .limit(limit)
            ).all()

        return [self._to_project(item) for item in projects]

    def create_project(self, *, name: str, description: str) -> StoredProject:
        now = _utc_now()
        project = Project(
            id=generate_uuid(),
            name=name.strip(),
            description=description.strip(),
            status="active",
            current_script_version=0,
            current_storyboard_version=0,
            created_at=now,
            updated_at=now,
            last_accessed_at=now,
        )
        with self._session_factory() as session:
            session.add(project)
            session.commit()

        return self._to_project(project)

    def get_project(self, project_id: str) -> StoredProject | None:
        with self._session_factory() as session:
            project = session.scalar(
                select(Project)
                .where(Project.id == project_id)
                .where(Project.deleted_at.is_(None))
            )

        return self._to_project(project) if project is not None else None

    def set_current_project(self, project_id: str) -> StoredProjectContext:
        now = _utc_now()
        with self._session_factory() as session:
            context = session.get(SessionContext, 1)
            if context is None:
                context = SessionContext(
                    id=1,
                    current_project_id=project_id,
                    updated_at=now,
                )
                session.add(context)
            else:
                context.current_project_id = project_id
                context.updated_at = now

            project = session.get(Project, project_id)
            if project is not None:
                project.last_accessed_at = now
            session.commit()

        return StoredProjectContext(project_id=project_id, updated_at=now)

    def get_current_project_context(self) -> StoredProjectContext | None:
        with self._session_factory() as session:
            context = session.get(SessionContext, 1)

        if context is None or context.current_project_id is None:
            return None

        return StoredProjectContext(
            project_id=context.current_project_id,
            updated_at=context.updated_at,
        )

    def soft_delete_project(self, project_id: str) -> DeletedProjectResult:
        deleted_at = _utc_now()
        with self._session_factory() as session:
            project = session.get(Project, project_id)
            if project is None or project.deleted_at is not None:
                raise KeyError(project_id)

            context = session.get(SessionContext, 1)
            cleared_current_project = False
            if context is not None and context.current_project_id == project_id:
                context.current_project_id = None
                context.updated_at = deleted_at
                cleared_current_project = True

            project.deleted_at = deleted_at
            project.updated_at = deleted_at
            session.commit()

        return DeletedProjectResult(
            project_id=project_id,
            deleted_at=deleted_at,
            cleared_current_project=cleared_current_project,
        )

    def update_project_versions(
        self,
        project_id: str,
        *,
        current_script_version: int | None = None,
        current_storyboard_version: int | None = None,
    ) -> StoredProject:
        now = _utc_now()
        with self._session_factory() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise KeyError(project_id)

            if current_script_version is not None:
                project.current_script_version = current_script_version
            if current_storyboard_version is not None:
                project.current_storyboard_version = current_storyboard_version
            project.updated_at = now
            project.last_accessed_at = now
            session.commit()

        return self._to_project(project)

    def _to_project(self, project: Project) -> StoredProject:
        return StoredProject(
            id=project.id,
            name=project.name,
            description=project.description,
            status=project.status,
            current_script_version=project.current_script_version,
            current_storyboard_version=project.current_storyboard_version,
            created_at=project.created_at,
            updated_at=project.updated_at,
            last_accessed_at=project.last_accessed_at,
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
