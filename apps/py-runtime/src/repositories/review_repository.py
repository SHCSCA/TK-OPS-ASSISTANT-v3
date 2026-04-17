from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now
from domain.models.review import ReviewSummary


class ReviewRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_summary(self, project_id: str) -> ReviewSummary | None:
        with self._session_factory() as session:
            summary = session.scalar(
                select(ReviewSummary).where(ReviewSummary.project_id == project_id)
            )
            if summary is not None:
                session.expunge(summary)
            return summary

    def upsert_summary(
        self,
        project_id: str,
        project_name: str | None = None,
        **stats: object,
    ) -> ReviewSummary:
        with self._session_factory() as session:
            summary = session.scalar(
                select(ReviewSummary).where(ReviewSummary.project_id == project_id)
            )
            now = utc_now()
            if summary is None:
                summary = ReviewSummary(project_id=project_id, project_name=project_name)
                session.add(summary)
            elif project_name is not None:
                summary.project_name = project_name
            for key, value in stats.items():
                setattr(summary, key, value)
            summary.updated_at = now
            session.commit()
            session.refresh(summary)
            session.expunge(summary)
            return summary

    def save_suggestions(self, project_id: str, suggestions_json: str) -> ReviewSummary:
        with self._session_factory() as session:
            summary = session.scalar(
                select(ReviewSummary).where(ReviewSummary.project_id == project_id)
            )
            if summary is None:
                summary = ReviewSummary(project_id=project_id)
                session.add(summary)
                session.flush()
            summary.suggestions_json = suggestions_json
            summary.updated_at = utc_now()
            session.commit()
            session.refresh(summary)
            session.expunge(summary)
            return summary

    def mark_analyzed(self, project_id: str) -> ReviewSummary:
        with self._session_factory() as session:
            summary = session.scalar(
                select(ReviewSummary).where(ReviewSummary.project_id == project_id)
            )
            if summary is None:
                summary = ReviewSummary(project_id=project_id)
                session.add(summary)
                session.flush()
            now = utc_now()
            summary.last_analyzed_at = now
            summary.updated_at = now
            session.commit()
            session.refresh(summary)
            session.expunge(summary)
            return summary

    def list_summaries(self) -> list[ReviewSummary]:
        with self._session_factory() as session:
            items = session.scalars(select(ReviewSummary)).all()
            session.expunge_all()
            return list(items)
