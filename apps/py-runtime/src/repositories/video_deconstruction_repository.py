from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import VideoStageRun


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


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')
