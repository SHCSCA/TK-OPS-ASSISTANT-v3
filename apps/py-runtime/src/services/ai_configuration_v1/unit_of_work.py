from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from errors import DomainError, ErrorCode
from repositories.account_workspace_v1_repository import (
    AccountWorkspaceV1Repository,
)
from repositories.ai_configuration_v1 import AIConfigurationV1Repository
from repositories.mutation_idempotency_repository import (
    MutationIdempotencyRepository,
)
from services.events import RuntimeEventService
from services.tasks.errors import TaskCancellationRequested
from services.tasks.types import TaskCommitCoordinator

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AIConfigurationTransaction:
    session: Session
    ai: AIConfigurationV1Repository
    accounts: AccountWorkspaceV1Repository
    idempotency: MutationIdempotencyRepository
    events: RuntimeEventService


class AIConfigurationUnitOfWork:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        repository: AIConfigurationV1Repository,
        event_service: RuntimeEventService,
        account_repository: AccountWorkspaceV1Repository | None = None,
        idempotency_repository: MutationIdempotencyRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository
        self._events = event_service
        self._accounts = account_repository or AccountWorkspaceV1Repository()
        self._idempotency = (
            idempotency_repository or MutationIdempotencyRepository()
        )

    @property
    def idempotency_repository(self) -> MutationIdempotencyRepository:
        return self._idempotency

    @contextmanager
    def read(self) -> Iterator[AIConfigurationTransaction]:
        with self._session_factory() as session:
            try:
                yield self._context(session)
            except DomainError:
                raise
            except SQLAlchemyError as exc:
                log.exception("AI 配置读取事务失败")
                raise DomainError(
                    ErrorCode.INTERNAL_ERROR,
                    "AI 配置读取失败，请稍后重试",
                    status_code=500,
                    loggable=True,
                ) from exc
            except Exception as exc:
                log.exception("AI 配置读取发生未预期异常")
                raise DomainError(
                    ErrorCode.INTERNAL_ERROR,
                    "AI 配置读取失败，请稍后重试",
                    status_code=500,
                    loggable=True,
                ) from exc

    @contextmanager
    def write(
        self,
        *,
        commit_coordinator: TaskCommitCoordinator | None = None,
    ) -> Iterator[AIConfigurationTransaction]:
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
                log.exception("AI 配置数据库写事务失败")
                raise DomainError(
                    ErrorCode.INTERNAL_ERROR,
                    "AI 配置保存失败，请稍后重试",
                    status_code=500,
                    loggable=True,
                ) from exc
            except Exception as exc:
                session.rollback()
                log.exception("AI 配置写事务发生未预期异常")
                raise DomainError(
                    ErrorCode.INTERNAL_ERROR,
                    "AI 配置保存失败，请稍后重试",
                    status_code=500,
                    loggable=True,
                ) from exc

    def _context(self, session: Session) -> AIConfigurationTransaction:
        return AIConfigurationTransaction(
            session=session,
            ai=self._repository,
            accounts=self._accounts,
            idempotency=self._idempotency,
            events=self._events,
        )

