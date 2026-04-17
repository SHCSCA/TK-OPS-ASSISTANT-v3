from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from domain.models.video_deconstruction import (
    VideoSegment,
    VideoStructureExtraction,
    VideoTranscript,
)


class VideoDeconstructionRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_transcript(self, video_id: str) -> VideoTranscript | None:
        with self._session_factory() as session:
            transcript = session.scalar(
                select(VideoTranscript).where(VideoTranscript.imported_video_id == video_id)
            )
            if transcript is not None:
                session.expunge(transcript)
            return transcript

    def save_transcript(self, transcript: VideoTranscript) -> VideoTranscript:
        with self._session_factory() as session:
            existing = session.scalar(
                select(VideoTranscript).where(
                    VideoTranscript.imported_video_id == transcript.imported_video_id
                )
            )
            if existing is None:
                session.add(transcript)
                target = transcript
            else:
                existing.language = transcript.language
                existing.text = transcript.text
                existing.status = transcript.status
                target = existing
            session.commit()
            session.refresh(target)
            session.expunge(target)
            return target

    def replace_segments(
        self,
        video_id: str,
        segments: list[VideoSegment],
    ) -> list[VideoSegment]:
        with self._session_factory() as session:
            session.execute(
                delete(VideoSegment).where(VideoSegment.imported_video_id == video_id)
            )
            session.add_all(segments)
            session.commit()
            for item in segments:
                session.refresh(item)
            session.expunge_all()
            return list(segments)

    def list_segments(self, video_id: str) -> list[VideoSegment]:
        with self._session_factory() as session:
            items = session.scalars(
                select(VideoSegment)
                .where(VideoSegment.imported_video_id == video_id)
                .order_by(VideoSegment.segment_index.asc())
            ).all()
            session.expunge_all()
            return list(items)

    def get_structure_by_video(self, video_id: str) -> VideoStructureExtraction | None:
        with self._session_factory() as session:
            structure = session.scalar(
                select(VideoStructureExtraction).where(
                    VideoStructureExtraction.imported_video_id == video_id
                )
            )
            if structure is not None:
                session.expunge(structure)
            return structure

    def get_structure(self, extraction_id: str) -> VideoStructureExtraction | None:
        with self._session_factory() as session:
            structure = session.get(VideoStructureExtraction, extraction_id)
            if structure is not None:
                session.expunge(structure)
            return structure

    def save_structure(self, structure: VideoStructureExtraction) -> VideoStructureExtraction:
        with self._session_factory() as session:
            existing = session.scalar(
                select(VideoStructureExtraction).where(
                    VideoStructureExtraction.imported_video_id == structure.imported_video_id
                )
            )
            if existing is None:
                session.add(structure)
                target = structure
            else:
                existing.status = structure.status
                existing.script_json = structure.script_json
                existing.storyboard_json = structure.storyboard_json
                target = existing
            session.commit()
            session.refresh(target)
            session.expunge(target)
            return target
