from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import AIJobRecord
from domain.models.base import generate_uuid


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
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_running(
        self,
        *,
        project_id: str | None,
        capability_id: str,
        provider: str,
        model: str,
    ) -> StoredAIJobRecord:
        job = AIJobRecord(
            id=generate_uuid(),
            capability_id=capability_id,
            provider=provider,
            model=model,
            status="running",
            error=None,
            duration_ms=None,
            project_id=project_id,
            provider_request_id=None,
            created_at=_utc_now(),
            completed_at=None,
        )
        with self._session_factory() as session:
            session.add(job)
            session.commit()

        return self._to_record(job)

    def mark_succeeded(self, job_id: str, *, duration_ms: int) -> StoredAIJobRecord:
        return self._update(job_id, status="succeeded", error=None, duration_ms=duration_ms)

    def mark_failed(self, job_id: str, *, error: str, duration_ms: int) -> StoredAIJobRecord:
        return self._update(job_id, status="failed", error=error, duration_ms=duration_ms)

    def list_recent(
        self,
        *,
        project_id: str,
        capability_ids: tuple[str, ...],
        limit: int = 5,
    ) -> list[StoredAIJobRecord]:
        if not capability_ids:
            return []

        with self._session_factory() as session:
            rows = session.scalars(
                select(AIJobRecord)
                .where(
                    AIJobRecord.project_id == project_id,
                    AIJobRecord.capability_id.in_(capability_ids),
                )
                .order_by(AIJobRecord.created_at.desc())
                .limit(limit)
            ).all()

        return [self._to_record(row) for row in rows]

    def _update(
        self,
        job_id: str,
        *,
        status: str,
        error: str | None,
        duration_ms: int,
    ) -> StoredAIJobRecord:
        completed_at = _utc_now()
        with self._session_factory() as session:
            job = session.get(AIJobRecord, job_id)
            assert job is not None
            job.status = status
            job.error = error
            job.duration_ms = duration_ms
            job.completed_at = completed_at
            session.commit()

        return self._to_record(job)

    def _to_record(self, row: AIJobRecord) -> StoredAIJobRecord:
        return StoredAIJobRecord(
            id=row.id,
            capability_id=row.capability_id,
            provider=row.provider,
            model=row.model,
            status=row.status,
            error=row.error,
            duration_ms=row.duration_ms,
            project_id=row.project_id,
            created_at=row.created_at,
            completed_at=row.completed_at,
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
