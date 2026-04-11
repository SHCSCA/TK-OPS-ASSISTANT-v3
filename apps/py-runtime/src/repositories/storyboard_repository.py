from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from persistence import connect_sqlite, initialize_schema


@dataclass(frozen=True, slots=True)
class StoredStoryboardVersion:
    project_id: str
    revision: int
    based_on_script_revision: int
    source: str
    scenes: list[dict[str, str]]
    provider: str | None
    model: str | None
    ai_job_id: str | None
    created_at: str


class StoryboardRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        initialize_schema(database_path)

    def list_versions(self, project_id: str) -> list[StoredStoryboardVersion]:
        with connect_sqlite(self._database_path) as connection:
            rows = connection.execute(
                '''
                SELECT project_id, revision, based_on_script_revision, source,
                       scenes_json, provider, model, ai_job_id, created_at
                FROM storyboard_versions
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
        based_on_script_revision: int,
        source: str,
        scenes: list[dict[str, str]],
        provider: str | None = None,
        model: str | None = None,
        ai_job_id: str | None = None,
    ) -> StoredStoryboardVersion:
        revision = self._next_revision(project_id)
        stored = StoredStoryboardVersion(
            project_id=project_id,
            revision=revision,
            based_on_script_revision=based_on_script_revision,
            source=source,
            scenes=scenes,
            provider=provider,
            model=model,
            ai_job_id=ai_job_id,
            created_at=_utc_now(),
        )
        with connect_sqlite(self._database_path) as connection:
            connection.execute(
                '''
                INSERT INTO storyboard_versions (
                    project_id, revision, based_on_script_revision, source,
                    scenes_json, provider, model, ai_job_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    stored.project_id,
                    stored.revision,
                    stored.based_on_script_revision,
                    stored.source,
                    json.dumps(stored.scenes, ensure_ascii=False),
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
                'SELECT COALESCE(MAX(revision), 0) AS revision FROM storyboard_versions WHERE project_id = ?',
                (project_id,),
            ).fetchone()

        assert row is not None
        return int(row['revision']) + 1

    def _to_version(self, row) -> StoredStoryboardVersion:
        return StoredStoryboardVersion(
            project_id=str(row['project_id']),
            revision=int(row['revision']),
            based_on_script_revision=int(row['based_on_script_revision']),
            source=str(row['source']),
            scenes=json.loads(str(row['scenes_json'])),
            provider=str(row['provider']) if row['provider'] else None,
            model=str(row['model']) if row['model'] else None,
            ai_job_id=str(row['ai_job_id']) if row['ai_job_id'] else None,
            created_at=str(row['created_at']),
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')
