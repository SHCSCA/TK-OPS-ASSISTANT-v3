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
                .order_by(SubtitleTrack.updated_at.desc(), SubtitleTrack.created_at.desc())
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
        segments_json: str | None = None,
        status: str | None = None,
        style_json: str | None = None,
        metadata_json: str | None = None,
        updated_at: str | None = None,
    ) -> SubtitleTrack | None:
        with self._session_factory() as session:
            track = session.get(SubtitleTrack, track_id)
            if track is None:
                return None
            if segments_json is not None:
                track.segments_json = segments_json
            if style_json is not None:
                track.style_json = style_json
            if metadata_json is not None:
                track.metadata_json = metadata_json
            if status is not None:
                track.status = status
            if updated_at is not None:
                track.updated_at = updated_at
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
