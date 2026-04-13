from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import ScriptVersion


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
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_versions(self, project_id: str) -> list[StoredScriptVersion]:
        with self._session_factory() as session:
            versions = session.scalars(
                select(ScriptVersion)
                .where(ScriptVersion.project_id == project_id)
                .order_by(ScriptVersion.revision.desc())
            ).all()

        return [self._to_version(item) for item in versions]

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
        with self._session_factory() as session:
            revision = self._next_revision(session, project_id)
            version = ScriptVersion(
                project_id=project_id,
                revision=revision,
                source=source,
                content=content,
                provider=provider,
                model=model,
                ai_job_id=ai_job_id,
                created_at=_utc_now(),
            )
            session.add(version)
            session.commit()

        return self._to_version(version)

    def _next_revision(self, session: Session, project_id: str) -> int:
        current = session.scalar(
            select(func.coalesce(func.max(ScriptVersion.revision), 0)).where(
                ScriptVersion.project_id == project_id
            )
        )
        return int(current or 0) + 1

    def _to_version(self, version: ScriptVersion) -> StoredScriptVersion:
        return StoredScriptVersion(
            project_id=version.project_id,
            revision=version.revision,
            source=version.source,
            content=version.content,
            provider=version.provider,
            model=version.model,
            ai_job_id=version.ai_job_id,
            created_at=version.created_at,
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
