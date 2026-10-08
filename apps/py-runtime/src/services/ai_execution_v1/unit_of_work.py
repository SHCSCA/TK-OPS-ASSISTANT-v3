from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from errors import DomainError, ErrorCode
from repositories.account_configuration_v1_repository import (
    AccountConfigurationV1Repository,
)
from repositories.account_workspace_v1_repository import (
    AccountWorkspaceV1Repository,
)
from repositories.ai_configuration_v1 import AIConfigurationV1Repository
from repositories.ai_execution_v1 import AIExecutionV1Repository
from repositories.knowledge_asset_v1_repository import (
    KnowledgeAssetV1Repository,
)
from repositories.knowledge_v1_repository import KnowledgeV1Repository
from repositories.runtime_task_repository import RuntimeTaskRepository
from services.events import RuntimeEventService
from services.tasks.errors import TaskCancellationRequested
from services.tasks.types import TaskCommitCoordinator

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AIExecutionTransaction:
    session: Session
    accounts: AccountWorkspaceV1Repository
    configuration: AccountConfigurationV1Repository
    ai: AIConfigurationV1Repository
    executions: AIExecutionV1Repository
    knowledge: KnowledgeV1Repository
    knowledge_assets: KnowledgeAssetV1Repository
    tasks: RuntimeTaskRepository
    events: RuntimeEventService


class AIExecutionUnitOfWork:
    """为执行、快照、任务和 outbox 提供同一事务边界。"""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        account_repository: AccountWorkspaceV1Repository,
        configuration_repository: AccountConfigurationV1Repository,
        ai_repository: AIConfigurationV1Repository,
        execution_repository: AIExecutionV1Repository,
        knowledge_repository: KnowledgeV1Repository,
        knowledge_asset_repository: KnowledgeAssetV1Repository,
        task_repository: RuntimeTaskRepository,
        event_service: RuntimeEventService,
    ) -> None:
        self._session_factory = session_factory
        self._accounts = account_repository
        self._configuration = configuration_repository
        self._ai = ai_repository
        self._executions = execution_repository
        self._knowledge = knowledge_repository
        self._knowledge_assets = knowledge_asset_repository
        self._tasks = task_repository
        self._events = event_service

    @contextmanager
    def read(self) -> Iterator[AIExecutionTransaction]:
        with self._session_factory() as session:
            try:
                yield self._context(session)
            except DomainError:
                raise
            except SQLAlchemyError as exc:
                log.exception("AI 执行数据读取失败")
                raise _storage_error("读取") from exc
            except Exception as exc:
                log.exception("AI 执行读取发生未预期异常")
                raise _storage_error("读取") from exc

    @contextmanager
    def write(
        self,
        *,
        commit_coordinator: TaskCommitCoordinator | None = None,
    ) -> Iterator[AIExecutionTransaction]:
        with self._session_factory() as session:
            try:
                yield self._context(session)
                if commit_coordinator is None:
                    session.commit()
                else:
                    commit_coordinator.commit(session.commit)
            except TaskCancellationRequested:
                session.rollback()
                raise
            except (DomainError, IntegrityError):
                session.rollback()
                raise
            except SQLAlchemyError as exc:
                session.rollback()
                log.exception("AI 执行数据库写入失败")
                raise _storage_error("保存") from exc
            except Exception as exc:
                session.rollback()
                log.exception("AI 执行写入发生未预期异常")
                raise _storage_error("保存") from exc

    def _context(self, session: Session) -> AIExecutionTransaction:
        return AIExecutionTransaction(
            session=session,
            accounts=self._accounts,
            configuration=self._configuration,
            ai=self._ai,
            executions=self._executions,
            knowledge=self._knowledge,
            knowledge_assets=self._knowledge_assets,
            tasks=self._tasks,
            events=self._events,
        )


def _storage_error(action: str) -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        f"AI 执行数据{action}失败，请稍后重试",
        status_code=500,
        loggable=True,
    )


__all__ = ["AIExecutionTransaction", "AIExecutionUnitOfWork"]
