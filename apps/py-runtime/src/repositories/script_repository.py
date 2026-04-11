from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from persistence import connect_sqlite, initialize_schema


@dataclass(frozen=True, slots=True)
class StoredScriptVersion:
    project_id: str
    revision: int
    source: str
    content: str
    provider: str | None
    model: str | None
    ai_job_id: str | None
    created_at: str


class ScriptRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        initialize_schema(database_path)

    def list_versions(self, project_id: str) -> list[StoredScriptVersion]:
        with connect_sqlite(self._database_path) as connection:
            rows = connection.execute(
                '''
                SELECT project_id, revision, source, content, provider, model, ai_job_id, created_at
                FROM script_versions
                WHERE project_id = ?
                ORDER BY revision DESC
                ''',
                (project_id,),
            ).fetchall()

        return [self._to_version(row) for row in rows]

    def save_version(
        self,
        project_id: str,
        *,
        source: str,
        content: str,
        provider: str | None = None,
        model: str | None = None,
        ai_job_id: str | None = None,
    ) -> StoredScriptVersion:
        revision = self._next_revision(project_id)
        stored = StoredScriptVersion(
            project_id=project_id,
            revision=revision,
            source=source,
            content=content,
            provider=provider,
            model=model,
            ai_job_id=ai_job_id,
            created_at=_utc_now(),
        )
        with connect_sqlite(self._database_path) as connection:
            connection.execute(
                '''
                INSERT INTO script_versions (
                    project_id, revision, source, content, provider, model, ai_job_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    stored.project_id,
                    stored.revision,
                    stored.source,
                    stored.content,
                    stored.provider,
                    stored.model,
                    stored.ai_job_id,
                    stored.created_at,
                ),
            )
            connection.commit()

        return stored

    def _next_revision(self, project_id: str) -> int:
        with connect_sqlite(self._database_path) as connection:
            row = connection.execute(
                'SELECT COALESCE(MAX(revision), 0) AS revision FROM script_versions WHERE project_id = ?',
                (project_id,),
            ).fetchone()

        assert row is not None
        return int(row['revision']) + 1

    def _to_version(self, row) -> StoredScriptVersion:
        return StoredScriptVersion(
            project_id=str(row['project_id']),
            revision=int(row['revision']),
            source=str(row['source']),
            content=str(row['content']),
            provider=str(row['provider']) if row['provider'] else None,
            model=str(row['model']) if row['model'] else None,
            ai_job_id=str(row['ai_job_id']) if row['ai_job_id'] else None,
            created_at=str(row['created_at']),
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')
