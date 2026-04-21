from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now
from domain.models.automation import AutomationTask, AutomationTaskRun


_ACTIVE_RUN_STATUSES = {"queued", "running"}


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

    def set_enabled(self, task_id: str, enabled: bool) -> AutomationTask | None:
        return self.update_task(task_id, enabled=enabled)

    def delete_task(self, task_id: str) -> bool:
        with self._session_factory() as session:
            task = session.get(AutomationTask, task_id)
            if task is None:
                return False
            session.delete(task)
            session.commit()
            return True

    def create_run(
        self,
        task_id: str,
        *,
        status: str,
        log_text: str | None,
    ) -> AutomationTaskRun | None:
        with self._session_factory() as session:
            task = session.get(AutomationTask, task_id)
            if task is None:
                return None

            now = utc_now()
            run = AutomationTaskRun(
                task_id=task_id,
                status=status,
                started_at=now if status == "running" else None,
                finished_at=None,
                log_text=log_text,
            )
            task.run_count += 1
            task.last_run_at = now
            task.last_run_status = status
            task.updated_at = now
            session.add(run)
            session.commit()
            session.refresh(run)
            session.expunge(run)
            return run

    def update_run(
        self,
        run_id: str,
        *,
        status: str | None = None,
        started_at: object | None = None,
        finished_at: object | None = None,
        log_text: str | None = None,
        append_log_text: str | None = None,
    ) -> AutomationTaskRun | None:
        with self._session_factory() as session:
            run = session.get(AutomationTaskRun, run_id)
            if run is None:
                return None

            if status is not None:
                run.status = status
            if started_at is not None:
                run.started_at = started_at
            if finished_at is not None:
                run.finished_at = finished_at
            if log_text is not None:
                run.log_text = log_text
            if append_log_text:
                if run.log_text:
                    run.log_text = f"{run.log_text}\n{append_log_text}"
                else:
                    run.log_text = append_log_text

            task = session.get(AutomationTask, run.task_id)
            if task is not None:
                task.last_run_status = run.status
                task.last_run_at = finished_at if finished_at is not None else utc_now()
                task.updated_at = utc_now()

            session.commit()
            session.refresh(run)
            session.expunge(run)
            return run

    def get_run(self, run_id: str) -> AutomationTaskRun | None:
        with self._session_factory() as session:
            run = session.get(AutomationTaskRun, run_id)
            if run is not None:
                session.expunge(run)
            return run

    def get_latest_run(self, task_id: str) -> AutomationTaskRun | None:
        with self._session_factory() as session:
            run = session.scalars(
                select(AutomationTaskRun)
                .where(AutomationTaskRun.task_id == task_id)
                .order_by(
                    AutomationTaskRun.finished_at.desc(),
                    AutomationTaskRun.started_at.desc(),
                    AutomationTaskRun.created_at.desc(),
                )
                .limit(1)
            ).first()
            if run is not None:
                session.expunge(run)
            return run

    def get_active_run(self, task_id: str) -> AutomationTaskRun | None:
        with self._session_factory() as session:
            run = session.scalars(
                select(AutomationTaskRun)
                .where(AutomationTaskRun.task_id == task_id)
                .where(AutomationTaskRun.status.in_(_ACTIVE_RUN_STATUSES))
                .order_by(AutomationTaskRun.created_at.desc())
                .limit(1)
            ).first()
            if run is not None:
                session.expunge(run)
            return run

    def get_queue_position(self, run_id: str) -> int | None:
        with self._session_factory() as session:
            run = session.get(AutomationTaskRun, run_id)
            if run is None or run.status != "queued":
                return None
            queued_runs = session.scalars(
                select(AutomationTaskRun)
                .where(AutomationTaskRun.status == "queued")
                .order_by(AutomationTaskRun.created_at.asc())
            ).all()
            for index, item in enumerate(queued_runs, start=1):
                if item.id == run_id:
                    return index
            return None

    def list_runs(self, task_id: str, limit: int = 20) -> list[AutomationTaskRun]:
        with self._session_factory() as session:
            runs = session.scalars(
                select(AutomationTaskRun)
                .where(AutomationTaskRun.task_id == task_id)
                .order_by(
                    AutomationTaskRun.finished_at.desc(),
                    AutomationTaskRun.started_at.desc(),
                    AutomationTaskRun.created_at.desc(),
                )
                .limit(limit)
            ).all()
            session.expunge_all()
            return list(runs)
