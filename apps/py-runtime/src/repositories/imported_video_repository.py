from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import ImportedVideo


class ImportedVideoRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, video: ImportedVideo) -> ImportedVideo:
        with self._session_factory() as session:
            session.add(video)
            session.commit()

        return video

    def list_by_project(self, project_id: str) -> list[ImportedVideo]:
        with self._session_factory() as session:
            videos = session.scalars(
                select(ImportedVideo)
                .where(ImportedVideo.project_id == project_id)
                .order_by(ImportedVideo.created_at.desc())
            ).all()

        return list(videos)

    def delete(self, video_id: str) -> bool:
        with self._session_factory() as session:
            video = session.get(ImportedVideo, video_id)
            if video is None:
                return False
            session.delete(video)
            session.commit()
            return True
