from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import SubtitleTrack


class SubtitleRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_tracks(self, project_id: str) -> list[SubtitleTrack]:
        with self._session_factory() as session:
            tracks = session.scalars(
                select(SubtitleTrack)
                .where(SubtitleTrack.project_id == project_id)
                .order_by(SubtitleTrack.created_at.desc())
            ).all()
            session.expunge_all()
            return list(tracks)

    def create_track(self, track: SubtitleTrack) -> SubtitleTrack:
        with self._session_factory() as session:
            session.add(track)
            session.commit()
            session.refresh(track)
            session.expunge(track)
            return track

    def get_track(self, track_id: str) -> SubtitleTrack | None:
        with self._session_factory() as session:
            track = session.get(SubtitleTrack, track_id)
            if track is not None:
                session.expunge(track)
            return track

    def update_track(
        self,
        track_id: str,
        *,
        segments_json: str,
        status: str,
        style_json: str,
    ) -> SubtitleTrack | None:
        with self._session_factory() as session:
            track = session.get(SubtitleTrack, track_id)
            if track is None:
                return None
            track.segments_json = segments_json
            track.style_json = style_json
            track.status = status
            session.commit()
            session.refresh(track)
            session.expunge(track)
            return track

    def delete_track(self, track_id: str) -> bool:
        with self._session_factory() as session:
            track = session.get(SubtitleTrack, track_id)
            if track is None:
                return False
            session.delete(track)
            session.commit()
            return True
