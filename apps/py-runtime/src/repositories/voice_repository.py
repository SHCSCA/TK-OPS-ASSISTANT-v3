from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import VoiceTrack
from common.time import utc_now_iso


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

    def update_track(
        self,
        track_id: str,
        *,
        file_path: str | None = None,
        status: str | None = None,
        provider: str | None = None,
        segments_json: str | None = None,
        config_json: str | None = None,
        version: int | None = None,
        bump_version: bool = False,
        updated_at: str | None = None,
    ) -> VoiceTrack | None:
        with self._session_factory() as session:
            track = session.get(VoiceTrack, track_id)
            if track is None:
                return None
            if file_path is not None:
                track.file_path = file_path
            if status is not None:
                track.status = status
            if provider is not None:
                track.provider = provider
            if segments_json is not None:
                track.segments_json = segments_json
            if config_json is not None:
                track.config_json = config_json
            if bump_version:
                track.version = int(track.version or 0) + 1
            elif version is not None:
                track.version = version
            if (
                file_path is not None
                or status is not None
                or provider is not None
                or segments_json is not None
                or config_json is not None
                or bump_version
                or version is not None
            ):
                track.updated_at = updated_at or utc_now_iso()
            session.commit()
            session.refresh(track)
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
