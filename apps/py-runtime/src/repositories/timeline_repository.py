from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now_iso
from domain.models.base import generate_uuid
from domain.models.timeline import Timeline


class TimelineRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_all(self) -> list[Timeline]:
        with self._session_factory() as session:
            timelines = session.scalars(
                select(Timeline).order_by(Timeline.updated_at.desc())
            ).all()
            session.expunge_all()
            return list(timelines)

    def get_by_id(self, timeline_id: str) -> Timeline | None:
        with self._session_factory() as session:
            timeline = session.get(Timeline, timeline_id)
            if timeline is not None:
                session.expunge(timeline)
            return timeline

    def get_current_for_project(self, project_id: str) -> Timeline | None:
        with self._session_factory() as session:
            timeline = session.scalars(
                select(Timeline)
                .where(Timeline.project_id == project_id)
                .order_by(Timeline.updated_at.desc())
                .limit(1)
            ).first()
            if timeline is not None:
                session.expunge(timeline)
            return timeline

    def create_empty(self, project_id: str, name: str) -> Timeline:
        now = utc_now_iso()
        timeline = Timeline(
            id=generate_uuid(),
            project_id=project_id,
            name=name,
            status="draft",
            duration_seconds=None,
            tracks_json="[]",
            source="manual",
            created_at=now,
            updated_at=now,
        )
        with self._session_factory() as session:
            session.add(timeline)
            session.commit()
            session.refresh(timeline)
            session.expunge(timeline)
            return timeline

    def update_timeline(
        self,
        timeline_id: str,
        *,
        name: str | None,
        duration_seconds: float | None,
        tracks_json: str,
    ) -> Timeline | None:
        with self._session_factory() as session:
            timeline = session.get(Timeline, timeline_id)
            if timeline is None:
                return None

            if name is not None:
                timeline.name = name
            timeline.duration_seconds = duration_seconds
            timeline.tracks_json = tracks_json
            timeline.updated_at = utc_now_iso()
            session.commit()
            session.refresh(timeline)
            session.expunge(timeline)
            return timeline
