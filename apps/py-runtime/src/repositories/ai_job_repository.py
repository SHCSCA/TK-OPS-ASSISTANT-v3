from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from persistence import connect_sqlite, initialize_schema


@dataclass(frozen=True, slots=True)
class StoredAIJobRecord:
    id: str
    capability_id: str
    provider: str
    model: str
    status: str
    error: str | None
    duration_ms: int | None
    project_id: str | None
    created_at: str
    completed_at: str | None


class AIJobRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        initialize_schema(database_path)

    def create_running(
        self,
        *,
        project_id: str | None,
        capability_id: str,
        provider: str,
        model: str,
    ) -> StoredAIJobRecord:
        stored = StoredAIJobRecord(
            id=uuid4().hex,
            capability_id=capability_id,
            provider=provider,
            model=model,
            status='running',
            error=None,
            duration_ms=None,
            project_id=project_id,
            created_at=_utc_now(),
            completed_at=None,
        )
        with connect_sqlite(self._database_path) as connection:
            connection.execute(
                '''
                INSERT INTO ai_job_records (
                    id, project_id, capability_id, provider, model, status,
                    error, duration_ms, provider_request_id, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    stored.id,
                    stored.project_id,
                    stored.capability_id,
                    stored.provider,
                    stored.model,
                    stored.status,
                    stored.error,
                    stored.duration_ms,
                    None,
                    stored.created_at,
                    stored.completed_at,
                ),
            )
            connection.commit()

        return stored

    def mark_succeeded(self, job_id: str, *, duration_ms: int) -> StoredAIJobRecord:
        return self._update(job_id, status='succeeded', error=None, duration_ms=duration_ms)

    def mark_failed(self, job_id: str, *, error: str, duration_ms: int) -> StoredAIJobRecord:
        return self._update(job_id, status='failed', error=error, duration_ms=duration_ms)

    def list_recent(
        self,
        *,
        project_id: str,
        capability_ids: tuple[str, ...],
        limit: int = 5,
    ) -> list[StoredAIJobRecord]:
        placeholders = ','.join('?' for _ in capability_ids)
        with connect_sqlite(self._database_path) as connection:
            rows = connection.execute(
                f'''
                SELECT id, capability_id, provider, model, status,
                       error, duration_ms, project_id, created_at, completed_at
                FROM ai_job_records
                WHERE project_id = ?
                  AND capability_id IN ({placeholders})
                ORDER BY created_at DESC
                LIMIT ?
                ''',
                (project_id, *capability_ids, limit),
            ).fetchall()

        return [self._to_record(row) for row in rows]

    def _update(self, job_id: str, *, status: str, error: str | None, duration_ms: int) -> StoredAIJobRecord:
        completed_at = _utc_now()
        with connect_sqlite(self._database_path) as connection:
            connection.execute(
                '''
                UPDATE ai_job_records
                SET status = ?, error = ?, duration_ms = ?, completed_at = ?
                WHERE id = ?
                ''',
                (status, error, duration_ms, completed_at, job_id),
            )
            row = connection.execute(
                '''
                SELECT id, capability_id, provider, model, status,
                       error, duration_ms, project_id, created_at, completed_at
                FROM ai_job_records
                WHERE id = ?
                ''',
                (job_id,),
            ).fetchone()
            connection.commit()

        assert row is not None
        return self._to_record(row)

    def _to_record(self, row) -> StoredAIJobRecord:
        return StoredAIJobRecord(
            id=str(row['id']),
            capability_id=str(row['capability_id']),
            provider=str(row['provider']),
            model=str(row['model']),
            status=str(row['status']),
            error=str(row['error']) if row['error'] else None,
            duration_ms=int(row['duration_ms']) if row['duration_ms'] is not None else None,
            project_id=str(row['project_id']) if row['project_id'] else None,
            created_at=str(row['created_at']),
            completed_at=str(row['completed_at']) if row['completed_at'] else None,
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')
