from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now_iso
from domain.models.base import generate_uuid
from domain.models.magic_cut import MagicCutSuggestionDraft


class MagicCutSuggestionRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_pending(
        self,
        project_id: str,
        timeline_id: str,
        summary: str,
        operations_json: str,
        timeline_version_token: str,
        ai_job_id: str | None,
    ) -> MagicCutSuggestionDraft:
        return self.create(
            project_id=project_id,
            timeline_id=timeline_id,
            status="pending_review",
            summary=summary,
            operations_json=operations_json,
            timeline_version_token=timeline_version_token,
            ai_job_id=ai_job_id,
        )

    def create_failed_parse(
        self,
        project_id: str,
        timeline_id: str,
        summary: str,
        timeline_version_token: str,
        ai_job_id: str | None,
    ) -> MagicCutSuggestionDraft:
        return self.create(
            project_id=project_id,
            timeline_id=timeline_id,
            status="failed_parse",
            summary=summary,
            operations_json="[]",
            timeline_version_token=timeline_version_token,
            ai_job_id=ai_job_id,
        )

    def create(
        self,
        *,
        project_id: str,
        timeline_id: str,
        status: str,
        summary: str,
        operations_json: str,
        timeline_version_token: str,
        ai_job_id: str | None,
    ) -> MagicCutSuggestionDraft:
        now = utc_now_iso()
        draft = MagicCutSuggestionDraft(
            id=generate_uuid(),
            project_id=project_id,
            timeline_id=timeline_id,
            ai_job_id=ai_job_id,
            status=status,
            summary=summary,
            operations_json=operations_json,
            timeline_version_token=timeline_version_token,
            created_at=now,
            updated_at=now,
            applied_at=None,
        )
        with self._session_factory() as session:
            session.add(draft)
            session.commit()
            session.refresh(draft)
            session.expunge(draft)
            return draft

    def get_latest(self, project_id: str, timeline_id: str) -> MagicCutSuggestionDraft | None:
        with self._session_factory() as session:
            draft = session.scalars(
                select(MagicCutSuggestionDraft)
                .where(
                    MagicCutSuggestionDraft.project_id == project_id,
                    MagicCutSuggestionDraft.timeline_id == timeline_id,
                )
                .order_by(MagicCutSuggestionDraft.created_at.desc())
                .limit(1)
            ).first()
            if draft is not None:
                session.expunge(draft)
            return draft

    def get_by_id(self, suggestion_id: str) -> MagicCutSuggestionDraft | None:
        with self._session_factory() as session:
            draft = session.get(MagicCutSuggestionDraft, suggestion_id)
            if draft is not None:
                session.expunge(draft)
            return draft

    def mark_applied(self, suggestion_id: str, applied_at: str) -> MagicCutSuggestionDraft | None:
        return self._update_status(suggestion_id, "applied", applied_at=applied_at)

    def mark_dismissed(self, suggestion_id: str) -> MagicCutSuggestionDraft | None:
        with self._session_factory() as session:
            draft = session.get(MagicCutSuggestionDraft, suggestion_id)
            if draft is None:
                return None
            draft.status = "dismissed"
            draft.operations_json = "[]"
            draft.updated_at = utc_now_iso()
            session.commit()
            session.refresh(draft)
            session.expunge(draft)
            return draft

    def _update_status(
        self,
        suggestion_id: str,
        status: str,
        *,
        applied_at: str | None,
    ) -> MagicCutSuggestionDraft | None:
        with self._session_factory() as session:
            draft = session.get(MagicCutSuggestionDraft, suggestion_id)
            if draft is None:
                return None
            now = utc_now_iso()
            draft.status = status
            draft.updated_at = now
            if applied_at is not None:
                draft.applied_at = applied_at
            session.commit()
            session.refresh(draft)
            session.expunge(draft)
            return draft
