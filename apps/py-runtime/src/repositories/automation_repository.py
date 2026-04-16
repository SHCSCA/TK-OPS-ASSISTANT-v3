from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now
from domain.models.automation import AutomationTask, AutomationTaskRun


class AutomationRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_tasks(
        self,
        *,
        status: str | None = None,
        type: str | None = None,
    ) -> list[AutomationTask]:
        with self._session_factory() as session:
            stmt = select(AutomationTask).order_by(AutomationTask.created_at.desc())
            if status is not None:
                stmt = stmt.where(AutomationTask.last_run_status == status)
            if type is not None:
                stmt = stmt.where(AutomationTask.type == type)
            tasks = session.scalars(stmt).all()
            session.expunge_all()
            return list(tasks)

    def create_task(self, task: AutomationTask) -> AutomationTask:
        with self._session_factory() as session:
            session.add(task)
            session.commit()
            session.refresh(task)
            session.expunge(task)
            return task

    def get_task(self, task_id: str) -> AutomationTask | None:
        with self._session_factory() as session:
            task = session.get(AutomationTask, task_id)
            if task is not None:
                session.expunge(task)
            return task

    def update_task(self, task_id: str, **kwargs: object) -> AutomationTask | None:
        with self._session_factory() as session:
            task = session.get(AutomationTask, task_id)
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
            task = session.get(AutomationTask, task_id)
            if task is None:
                return False
            session.delete(task)
            session.commit()
            return True

    def trigger_task(self, task_id: str) -> AutomationTaskRun | None:
        with self._session_factory() as session:
            task = session.get(AutomationTask, task_id)
            if task is None:
                return None
            now = utc_now()
            run = AutomationTaskRun(
                task_id=task_id,
                status="running",
                started_at=now,
                log_text="手动触发任务，等待执行器接管。",
            )
            task.run_count += 1
            task.last_run_at = now
            task.last_run_status = "running"
            task.updated_at = now
            session.add(run)
            session.commit()
            session.refresh(run)
            session.expunge(run)
            return run

    def list_runs(self, task_id: str, limit: int = 20) -> list[AutomationTaskRun]:
        with self._session_factory() as session:
            runs = session.scalars(
                select(AutomationTaskRun)
                .where(AutomationTaskRun.task_id == task_id)
                .order_by(AutomationTaskRun.created_at.desc())
                .limit(limit)
            ).all()
            session.expunge_all()
            return list(runs)
