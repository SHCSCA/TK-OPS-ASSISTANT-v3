from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import VideoDeconstructionArtifact, VideoStageRun, VideoTranscript


@dataclass(frozen=True, slots=True)
class StoredVideoStageRun:
    video_id: str
    stage_id: str
    status: str
    progress_pct: int
    result_summary: str | None
    error_message: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class StoredVideoTranscript:
    video_id: str
    language: str | None
    text: str
    provider: str
    model: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class StoredVideoDeconstructionArtifact:
    video_id: str
    artifact_type: str
    payload_json: str
    provider: str | None
    model: str | None
    created_at: str
    updated_at: str


class VideoDeconstructionRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_stage_runs(self, video_id: str) -> list[StoredVideoStageRun]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(VideoStageRun)
                .where(VideoStageRun.video_id == video_id)
                .order_by(VideoStageRun.stage_id.asc())
            ).all()
        return [self._to_stored(item) for item in rows]

    def get_stage_run(self, video_id: str, stage_id: str) -> StoredVideoStageRun | None:
        with self._session_factory() as session:
            row = session.get(VideoStageRun, {'video_id': video_id, 'stage_id': stage_id})
            if row is None:
                return None
            session.expunge(row)
        return self._to_stored(row)

    def upsert_stage_run(
        self,
        video_id: str,
        stage_id: str,
        *,
        status: str,
        progress_pct: int,
        result_summary: str | None = None,
        error_message: str | None = None,
    ) -> StoredVideoStageRun:
        with self._session_factory() as session:
            row = session.get(VideoStageRun, {'video_id': video_id, 'stage_id': stage_id})
            now = _utc_now()
            if row is None:
                row = VideoStageRun(
                    video_id=video_id,
                    stage_id=stage_id,
                    status=status,
                    progress_pct=progress_pct,
                    result_summary=result_summary,
                    error_message=error_message,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.status = status
                row.progress_pct = progress_pct
                row.result_summary = result_summary
                row.error_message = error_message
                row.updated_at = now
            session.commit()
            session.refresh(row)
            session.expunge(row)
        return self._to_stored(row)

    def get_transcript(self, video_id: str) -> StoredVideoTranscript | None:
        with self._session_factory() as session:
            row = session.get(VideoTranscript, video_id)
            if row is None:
                return None
            session.expunge(row)
        return self._to_transcript(row)

    def upsert_transcript(
        self,
        video_id: str,
        *,
        text: str,
        provider: str,
        model: str,
        language: str | None = None,
    ) -> StoredVideoTranscript:
        with self._session_factory() as session:
            row = session.get(VideoTranscript, video_id)
            now = _utc_now()
            if row is None:
                row = VideoTranscript(
                    video_id=video_id,
                    language=language,
                    text=text,
                    provider=provider,
                    model=model,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.language = language
                row.text = text
                row.provider = provider
                row.model = model
                row.updated_at = now
            session.commit()
            session.refresh(row)
            session.expunge(row)
        return self._to_transcript(row)

    def get_artifact(
        self,
        video_id: str,
        artifact_type: str,
    ) -> StoredVideoDeconstructionArtifact | None:
        with self._session_factory() as session:
            row = session.get(
                VideoDeconstructionArtifact,
                {'video_id': video_id, 'artifact_type': artifact_type},
            )
            if row is None:
                return None
            session.expunge(row)
        return self._to_artifact(row)

    def upsert_artifact(
        self,
        video_id: str,
        artifact_type: str,
        *,
        payload_json: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> StoredVideoDeconstructionArtifact:
        with self._session_factory() as session:
            row = session.get(
                VideoDeconstructionArtifact,
                {'video_id': video_id, 'artifact_type': artifact_type},
            )
            now = _utc_now()
            if row is None:
                row = VideoDeconstructionArtifact(
                    video_id=video_id,
                    artifact_type=artifact_type,
                    payload_json=payload_json,
                    provider=provider,
                    model=model,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.payload_json = payload_json
                row.provider = provider
                row.model = model
                row.updated_at = now
            session.commit()
            session.refresh(row)
            session.expunge(row)
        return self._to_artifact(row)

    def _to_stored(self, row: VideoStageRun) -> StoredVideoStageRun:
        return StoredVideoStageRun(
            video_id=row.video_id,
            stage_id=row.stage_id,
            status=row.status,
            progress_pct=row.progress_pct,
            result_summary=row.result_summary,
            error_message=row.error_message,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_transcript(self, row: VideoTranscript) -> StoredVideoTranscript:
        return StoredVideoTranscript(
            video_id=row.video_id,
            language=row.language,
            text=row.text,
            provider=row.provider,
            model=row.model,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_artifact(self, row: VideoDeconstructionArtifact) -> StoredVideoDeconstructionArtifact:
        return StoredVideoDeconstructionArtifact(
            video_id=row.video_id,
            artifact_type=row.artifact_type,
            payload_json=row.payload_json,
            provider=row.provider,
            model=row.model,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')
