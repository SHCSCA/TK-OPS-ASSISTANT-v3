from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import StoryboardVersion


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
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_versions(self, project_id: str) -> list[StoredStoryboardVersion]:
        with self._session_factory() as session:
            versions = session.scalars(
                select(StoryboardVersion)
                .where(StoryboardVersion.project_id == project_id)
                .order_by(StoryboardVersion.revision.desc())
            ).all()

        return [self._to_version(item) for item in versions]

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
        with self._session_factory() as session:
            revision = self._next_revision(session, project_id)
            version = StoryboardVersion(
                project_id=project_id,
                revision=revision,
                based_on_script_revision=based_on_script_revision,
                source=source,
                scenes_json=json.dumps(scenes, ensure_ascii=False),
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
            select(func.coalesce(func.max(StoryboardVersion.revision), 0)).where(
                StoryboardVersion.project_id == project_id
            )
        )
        return int(current or 0) + 1

    def _to_version(self, version: StoryboardVersion) -> StoredStoryboardVersion:
        return StoredStoryboardVersion(
            project_id=version.project_id,
            revision=version.revision,
            based_on_script_revision=version.based_on_script_revision,
            source=version.source,
            scenes=json.loads(version.scenes_json),
            provider=version.provider,
            model=version.model,
            ai_job_id=version.ai_job_id,
            created_at=version.created_at,
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
