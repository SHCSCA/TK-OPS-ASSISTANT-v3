from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from domain.models.runtime_task import RuntimeTask
from services.tasks.types import (
    NON_TERMINAL_STATUSES,
    RuntimeTaskRecord,
    TaskCompletionKind,
    TaskFailureKind,
    TaskScope,
    TaskStatus,
)

log = logging.getLogger(__name__)


class RuntimeTaskRepository:
    """以显式事务读写 Runtime 任务。"""

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        with self._session_factory() as session:
            try:
                yield session
                session.commit()
            except IntegrityError:
                session.rollback()
                raise
            except SQLAlchemyError:
                session.rollback()
                log.exception("Runtime 任务数据库事务失败")
                raise
            except Exception:
                session.rollback()
                log.exception("Runtime 任务事务发生未预期异常")
                raise

    def add(self, session: Session, task: RuntimeTask) -> RuntimeTaskRecord:
        session.add(task)
        session.flush()
        return self.to_record(task)

    def get_any(self, session: Session, task_id: str) -> RuntimeTask | None:
        return session.get(RuntimeTask, task_id)

    def get_scoped(
        self,
        session: Session,
        task_id: str,
        *,
        scope: TaskScope,
        account_id: str | None,
    ) -> RuntimeTask | None:
        statement = select(RuntimeTask).where(
            RuntimeTask.id == task_id,
            RuntimeTask.scope == scope.value,
        )
        if scope is TaskScope.ACCOUNT:
            statement = statement.where(RuntimeTask.account_id == account_id)
        else:
            statement = statement.where(RuntimeTask.account_id.is_(None))
        return session.scalars(statement).one_or_none()

    def get_record(self, task_id: str) -> RuntimeTaskRecord | None:
        with self.transaction() as session:
            task = self.get_any(session, task_id)
            return None if task is None else self.to_record(task)

    def get_scoped_record(
        self,
        task_id: str,
        *,
        scope: TaskScope,
        account_id: str | None,
    ) -> RuntimeTaskRecord | None:
        with self.transaction() as session:
            task = self.get_scoped(
                session,
                task_id,
                scope=scope,
                account_id=account_id,
            )
            return None if task is None else self.to_record(task)

    def list_non_terminal(self) -> list[RuntimeTaskRecord]:
        with self.transaction() as session:
            rows = session.scalars(
                select(RuntimeTask)
                .where(
                    RuntimeTask.status.in_(
                        tuple(status.value for status in NON_TERMINAL_STATUSES)
                    )
                )
                .order_by(RuntimeTask.created_at.asc())
            ).all()
            return [self.to_record(row) for row in rows]

    def list_system_tasks(self, *, limit: int = 200) -> list[RuntimeTaskRecord]:
        with self.transaction() as session:
            rows = session.scalars(
                select(RuntimeTask)
                .where(
                    RuntimeTask.scope == TaskScope.SYSTEM.value,
                    RuntimeTask.account_id.is_(None),
                )
                .order_by(RuntimeTask.created_at.desc(), RuntimeTask.id.desc())
                .limit(limit)
            ).all()
            return [self.to_record(row) for row in rows]

    def list_account_tasks(
        self,
        account_id: str,
        *,
        limit: int = 200,
    ) -> list[RuntimeTaskRecord]:
        with self.transaction() as session:
            rows = session.scalars(
                select(RuntimeTask)
                .where(
                    RuntimeTask.scope == TaskScope.ACCOUNT.value,
                    RuntimeTask.account_id == account_id,
                )
                .order_by(RuntimeTask.created_at.desc(), RuntimeTask.id.desc())
                .limit(limit)
            ).all()
            return [self.to_record(row) for row in rows]

    @staticmethod
    def acquire_write_lock(session: Session) -> None:
        """串行化同作用域单例任务的检查与创建。"""

        if session.get_bind().dialect.name == "sqlite":
            session.execute(text("UPDATE runtime_tasks SET revision = revision WHERE 0"))

    def find_active(
        self,
        session: Session,
        *,
        scope: TaskScope,
        account_id: str | None,
        task_type: str,
    ) -> RuntimeTask | None:
        statement = select(RuntimeTask).where(
            RuntimeTask.scope == scope.value,
            RuntimeTask.task_type == task_type,
            RuntimeTask.status.in_(
                tuple(status.value for status in NON_TERMINAL_STATUSES)
            ),
        )
        if scope is TaskScope.ACCOUNT:
            statement = statement.where(RuntimeTask.account_id == account_id)
        else:
            statement = statement.where(RuntimeTask.account_id.is_(None))
        return session.scalars(
            statement.order_by(RuntimeTask.created_at.asc()).limit(1)
        ).one_or_none()

    def transition(
        self,
        session: Session,
        task_id: str,
        *,
        expected_statuses: Sequence[TaskStatus],
        expected_revision: int | None = None,
        values: Mapping[str, object],
    ) -> RuntimeTaskRecord | None:
        predicates = [
            RuntimeTask.id == task_id,
            RuntimeTask.status.in_(
                tuple(status.value for status in expected_statuses)
            ),
        ]
        if expected_revision is not None:
            predicates.append(RuntimeTask.revision == expected_revision)
        statement = (
            update(RuntimeTask)
            .where(*predicates)
            .values(**values, revision=RuntimeTask.revision + 1)
            .returning(RuntimeTask)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        )
        row = session.scalars(statement).one_or_none()
        return None if row is None else self.to_record(row)

    @staticmethod
    def to_record(task: RuntimeTask) -> RuntimeTaskRecord:
        return RuntimeTaskRecord(
            id=task.id,
            scope=TaskScope(task.scope),
            account_id=task.account_id,
            task_type=task.task_type,
            status=TaskStatus(task.status),
            completion_kind=(
                TaskCompletionKind(task.completion_kind)
                if task.completion_kind is not None
                else None
            ),
            failure_kind=(
                TaskFailureKind(task.failure_kind)
                if task.failure_kind is not None
                else None
            ),
            progress=float(task.progress),
            cancellable=bool(task.cancellable),
            timeout_at=task.timeout_at,
            attempt=int(task.attempt),
            retry_of_task_id=task.retry_of_task_id,
            config_snapshot_json=task.config_snapshot_json,
            result_ref=task.result_ref,
            error_code=task.error_code,
            error_log_id=task.error_log_id,
            revision=int(task.revision),
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            updated_at=task.updated_at,
            idempotency_key_hash=task.idempotency_key_hash,
            request_hash=task.request_hash,
            handler_version=int(task.handler_version),
        )
