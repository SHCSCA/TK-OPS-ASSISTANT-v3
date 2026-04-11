from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from persistence import connect_sqlite, initialize_schema


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


class DashboardRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        initialize_schema(database_path)

    def list_recent_projects(self, *, limit: int = 10) -> list[StoredProject]:
        with connect_sqlite(self._database_path) as connection:
            rows = connection.execute(
                '''
                SELECT *
                FROM projects
                ORDER BY last_accessed_at DESC, updated_at DESC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()

        return [self._to_project(row) for row in rows]

    def create_project(self, *, name: str, description: str) -> StoredProject:
        now = _utc_now()
        stored = StoredProject(
            id=uuid4().hex,
            name=name.strip(),
            description=description.strip(),
            status='active',
            current_script_version=0,
            current_storyboard_version=0,
            created_at=now,
            updated_at=now,
            last_accessed_at=now,
        )
        with connect_sqlite(self._database_path) as connection:
            connection.execute(
                '''
                INSERT INTO projects (
                    id, name, description, status,
                    current_script_version, current_storyboard_version,
                    created_at, updated_at, last_accessed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    stored.id,
                    stored.name,
                    stored.description,
                    stored.status,
                    stored.current_script_version,
                    stored.current_storyboard_version,
                    stored.created_at,
                    stored.updated_at,
                    stored.last_accessed_at,
                ),
            )
            connection.commit()

        return stored

    def get_project(self, project_id: str) -> StoredProject | None:
        with connect_sqlite(self._database_path) as connection:
            row = connection.execute(
                'SELECT * FROM projects WHERE id = ?',
                (project_id,),
            ).fetchone()

        return self._to_project(row) if row is not None else None

    def set_current_project(self, project_id: str) -> StoredProjectContext:
        now = _utc_now()
        with connect_sqlite(self._database_path) as connection:
            connection.execute(
                '''
                INSERT INTO session_context (id, current_project_id, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    current_project_id = excluded.current_project_id,
                    updated_at = excluded.updated_at
                ''',
                (project_id, now),
            )
            connection.execute(
                '''
                UPDATE projects
                SET last_accessed_at = ?, updated_at = updated_at
                WHERE id = ?
                ''',
                (now, project_id),
            )
            connection.commit()

        return StoredProjectContext(project_id=project_id, updated_at=now)

    def get_current_project_context(self) -> StoredProjectContext | None:
        with connect_sqlite(self._database_path) as connection:
            row = connection.execute(
                'SELECT current_project_id, updated_at FROM session_context WHERE id = 1'
            ).fetchone()

        if row is None or row['current_project_id'] is None:
            return None

        return StoredProjectContext(
            project_id=str(row['current_project_id']),
            updated_at=str(row['updated_at']),
        )

    def update_project_versions(
        self,
        project_id: str,
        *,
        current_script_version: int | None = None,
        current_storyboard_version: int | None = None,
    ) -> StoredProject:
        current = self.get_project(project_id)
        if current is None:
            raise KeyError(project_id)

        updated = StoredProject(
            id=current.id,
            name=current.name,
            description=current.description,
            status=current.status,
            current_script_version=(
                current.current_script_version
                if current_script_version is None
                else current_script_version
            ),
            current_storyboard_version=(
                current.current_storyboard_version
                if current_storyboard_version is None
                else current_storyboard_version
            ),
            created_at=current.created_at,
            updated_at=_utc_now(),
            last_accessed_at=_utc_now(),
        )

        with connect_sqlite(self._database_path) as connection:
            connection.execute(
                '''
                UPDATE projects
                SET current_script_version = ?,
                    current_storyboard_version = ?,
                    updated_at = ?,
                    last_accessed_at = ?
                WHERE id = ?
                ''',
                (
                    updated.current_script_version,
                    updated.current_storyboard_version,
                    updated.updated_at,
                    updated.last_accessed_at,
                    project_id,
                ),
            )
            connection.commit()

        return updated

    def _to_project(self, row) -> StoredProject:
        return StoredProject(
            id=str(row['id']),
            name=str(row['name']),
            description=str(row['description']),
            status=str(row['status']),
            current_script_version=int(row['current_script_version']),
            current_storyboard_version=int(row['current_storyboard_version']),
            created_at=str(row['created_at']),
            updated_at=str(row['updated_at']),
            last_accessed_at=str(row['last_accessed_at']),
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')
