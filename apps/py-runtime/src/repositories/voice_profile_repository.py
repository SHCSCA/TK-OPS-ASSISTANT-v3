from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import VoiceProfile


class VoiceProfileRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_profiles(self) -> list[VoiceProfile]:
        with self._session_factory() as session:
            profiles = session.scalars(
                select(VoiceProfile).order_by(VoiceProfile.created_at.asc())
            ).all()
            session.expunge_all()
            return list(profiles)

    def get_profile(self, profile_id: str) -> VoiceProfile | None:
        with self._session_factory() as session:
            profile = session.get(VoiceProfile, profile_id)
            if profile is not None:
                session.expunge(profile)
            return profile

    def create_profile(self, profile: VoiceProfile) -> VoiceProfile:
        with self._session_factory() as session:
            session.add(profile)
            session.commit()
            session.refresh(profile)
            session.expunge(profile)
            return profile

    def upsert_profile(self, profile: VoiceProfile) -> VoiceProfile:
        with self._session_factory() as session:
            existing = session.get(VoiceProfile, profile.id)
            if existing is None:
                session.add(profile)
                session.commit()
                session.refresh(profile)
                session.expunge(profile)
                return profile

            existing.provider = profile.provider
            existing.voice_id = profile.voice_id
            existing.display_name = profile.display_name
            existing.locale = profile.locale
            existing.tags_json = profile.tags_json
            existing.enabled = profile.enabled
            existing.updated_at = profile.updated_at
            session.commit()
            session.refresh(existing)
            session.expunge(existing)
            return existing
