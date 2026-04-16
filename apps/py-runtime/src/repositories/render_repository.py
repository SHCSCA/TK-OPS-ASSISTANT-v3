from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now
from domain.models.render import RenderTask


class RenderRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_tasks(self, *, status: str | None = None) -> list[RenderTask]:
        with self._session_factory() as session:
            stmt = select(RenderTask).order_by(RenderTask.created_at.desc())
            if status is not None:
                stmt = stmt.where(RenderTask.status == status)
            tasks = session.scalars(stmt).all()
            session.expunge_all()
            return list(tasks)

    def create_task(self, task: RenderTask) -> RenderTask:
        with self._session_factory() as session:
            session.add(task)
            session.commit()
            session.refresh(task)
            session.expunge(task)
            return task

    def get_task(self, task_id: str) -> RenderTask | None:
        with self._session_factory() as session:
            task = session.get(RenderTask, task_id)
            if task is not None:
                session.expunge(task)
            return task

    def update_task(self, task_id: str, **kwargs: object) -> RenderTask | None:
        with self._session_factory() as session:
            task = session.get(RenderTask, task_id)
            if task is None:
                return None
            for key, value in kwargs.items():
                setattr(task, key, value)
            task.updated_at = utc_now()
            session.commit()
            session.refresh(task)
            session.expunge(task)
            return task

    def delete_task(self, task_id: str) -> bool:
        with self._session_factory() as session:
            task = session.get(RenderTask, task_id)
            if task is None:
                return False
            session.delete(task)
            session.commit()
            return True

    def cancel_task(self, task_id: str) -> RenderTask | None:
        with self._session_factory() as session:
            task = session.get(RenderTask, task_id)
            if task is None:
                return None
            task.status = "cancelled"
            task.finished_at = utc_now()
            task.updated_at = task.finished_at
            session.commit()
            session.refresh(task)
            session.expunge(task)
            return task
