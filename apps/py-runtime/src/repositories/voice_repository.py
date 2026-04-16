from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import VoiceTrack


class VoiceRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_tracks(self, project_id: str) -> list[VoiceTrack]:
        with self._session_factory() as session:
            tracks = session.scalars(
                select(VoiceTrack)
                .where(VoiceTrack.project_id == project_id)
                .order_by(VoiceTrack.created_at.desc())
            ).all()
            session.expunge_all()
            return list(tracks)

    def create_track(self, track: VoiceTrack) -> VoiceTrack:
        with self._session_factory() as session:
            session.add(track)
            session.commit()
            session.refresh(track)
            session.expunge(track)
            return track

    def get_track(self, track_id: str) -> VoiceTrack | None:
        with self._session_factory() as session:
            track = session.get(VoiceTrack, track_id)
            if track is not None:
                session.expunge(track)
            return track

    def delete_track(self, track_id: str) -> bool:
        with self._session_factory() as session:
            track = session.get(VoiceTrack, track_id)
            if track is None:
                return False
            session.delete(track)
            session.commit()
            return True
