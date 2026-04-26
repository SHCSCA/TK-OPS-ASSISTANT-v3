from __future__ import annotations

import json
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
    format: str
    document_json: dict[str, object] | None
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

    def get_version(self, project_id: str, revision: int) -> StoredScriptVersion | None:
        with self._session_factory() as session:
            version = session.get(ScriptVersion, {"project_id": project_id, "revision": revision})
            if version is None:
                return None
            session.expunge(version)
        return self._to_version(version)

    def save_version(
        self,
        project_id: str,
        *,
        source: str,
        content: str,
        format: str = "legacy_markdown",
        document_json: dict[str, object] | None = None,
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
                format=format,
                document_json=json.dumps(document_json, ensure_ascii=False) if document_json is not None else None,
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
            format=version.format or "legacy_markdown",
            document_json=_loads_json_object(version.document_json),
            provider=version.provider,
            model=version.model,
            ai_job_id=version.ai_job_id,
            created_at=version.created_at,
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _loads_json_object(payload: str | None) -> dict[str, object] | None:
    if not payload:
        return None
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None
