from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from errors import DomainError, ErrorCode
from repositories.account_connection_v1_repository import (
    AccountConnectionV1Repository,
)
from repositories.account_configuration_v1_repository import (
    AccountConfigurationV1Repository,
)
from repositories.account_workspace_v1_repository import (
    AccountWorkspaceV1Repository,
)
from repositories.knowledge_v1_repository import KnowledgeV1Repository
from repositories.knowledge_asset_v1_repository import (
    KnowledgeAssetV1Repository,
)
from repositories.mutation_idempotency_repository import (
    MutationIdempotencyRepository,
)
from services.accounts.idempotency import (
    MutationCommand,
    MutationIdempotencyService,
)
from services.events import RuntimeEventService
from services.tasks.errors import TaskCancellationRequested
from services.tasks.types import TaskCommitCoordinator

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AccountTransaction:
    session: Session
    accounts: AccountWorkspaceV1Repository
    connections: AccountConnectionV1Repository
    configuration: AccountConfigurationV1Repository
    knowledge: KnowledgeV1Repository
    knowledge_assets: KnowledgeAssetV1Repository
    idempotency: MutationIdempotencyRepository
    events: RuntimeEventService


@dataclass(frozen=True, slots=True)
class MutationWorkResult:
    response: Mapping[str, object]
    resource_type: str | None = None
    resource_id: str | None = None


@dataclass(frozen=True, slots=True)
class MutationExecution:
    response: dict[str, object]
    resource_type: str | None
    resource_id: str | None
    replayed: bool


class AccountUnitOfWork:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        event_service: RuntimeEventService,
        account_repository: AccountWorkspaceV1Repository | None = None,
        connection_repository: AccountConnectionV1Repository | None = None,
        configuration_repository: AccountConfigurationV1Repository | None = None,
        knowledge_repository: KnowledgeV1Repository | None = None,
        knowledge_asset_repository: KnowledgeAssetV1Repository | None = None,
        idempotency_repository: MutationIdempotencyRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._events = event_service
        self._accounts = account_repository or AccountWorkspaceV1Repository()
        self._connections = (
            connection_repository or AccountConnectionV1Repository()
        )
        self._configuration = (
            configuration_repository or AccountConfigurationV1Repository()
        )
        self._knowledge = knowledge_repository or KnowledgeV1Repository()
        self._knowledge_assets = (
            knowledge_asset_repository or KnowledgeAssetV1Repository()
        )
        self._idempotency = (
            idempotency_repository or MutationIdempotencyRepository()
        )

    @property
    def idempotency_repository(self) -> MutationIdempotencyRepository:
        return self._idempotency

    @contextmanager
    def read(self) -> Iterator[AccountTransaction]:
        with self._session_factory() as session:
            try:
                yield self._context(session)
            except DomainError:
                raise
            except SQLAlchemyError as exc:
                log.exception("账号读取事务失败")
                raise DomainError(
                    ErrorCode.INTERNAL_ERROR,
                    "账号数据读取失败，请稍后重试",
                    status_code=500,
                    loggable=True,
                ) from exc
            except Exception as exc:
                log.exception("账号读取事务发生未预期异常")
                raise DomainError(
                    ErrorCode.INTERNAL_ERROR,
                    "账号数据读取失败，请稍后重试",
                    status_code=500,
                    loggable=True,
                ) from exc

    @contextmanager
    def write(
        self,
        *,
        commit_coordinator: TaskCommitCoordinator | None = None,
    ) -> Iterator[AccountTransaction]:
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
            except DomainError:
                session.rollback()
                raise
            except IntegrityError:
                session.rollback()
                raise
            except SQLAlchemyError as exc:
                session.rollback()
                log.exception("账号数据库写事务失败")
                raise DomainError(
                    ErrorCode.INTERNAL_ERROR,
                    "账号数据保存失败，请稍后重试",
                    status_code=500,
                    loggable=True,
                ) from exc
            except Exception as exc:
                session.rollback()
                log.exception("账号写事务发生未预期异常")
                raise DomainError(
                    ErrorCode.INTERNAL_ERROR,
                    "账号数据保存失败，请稍后重试",
                    status_code=500,
                    loggable=True,
                ) from exc

    def _context(self, session: Session) -> AccountTransaction:
        return AccountTransaction(
            session=session,
            accounts=self._accounts,
            connections=self._connections,
            configuration=self._configuration,
            knowledge=self._knowledge,
            knowledge_assets=self._knowledge_assets,
            idempotency=self._idempotency,
            events=self._events,
        )


class AccountMutationExecutor:
    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        idempotency_service: MutationIdempotencyService,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._idempotency = idempotency_service

    def execute(
        self,
        command: MutationCommand,
        work: Callable[[AccountTransaction], MutationWorkResult],
    ) -> MutationExecution:
        try:
            with self._unit_of_work.write() as transaction:
                replay = self._idempotency.find_replay(
                    transaction.session,
                    command,
                )
                if replay is not None:
                    return MutationExecution(
                        response=replay.response,
                        resource_type=replay.resource_type,
                        resource_id=replay.resource_id,
                        replayed=True,
                    )
                result = work(transaction)
                stored = self._idempotency.store(
                    transaction.session,
                    command,
                    response=result.response,
                    resource_type=result.resource_type,
                    resource_id=result.resource_id,
                )
                return MutationExecution(
                    response=stored.response,
                    resource_type=stored.resource_type,
                    resource_id=stored.resource_id,
                    replayed=False,
                )
        except IntegrityError as exc:
            replay = self._resolve_race(command)
            if replay is not None:
                return replay
            log.exception(
                "账号普通写操作发生无法归因的完整性冲突",
                extra={"account_id": command.account_id},
            )
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "账号数据保存冲突，请刷新后重试",
                status_code=500,
                loggable=True,
            ) from exc

    def _resolve_race(
        self,
        command: MutationCommand,
    ) -> MutationExecution | None:
        with self._unit_of_work.read() as transaction:
            replay = self._idempotency.find_replay(
                transaction.session,
                command,
            )
            if replay is None:
                return None
            return MutationExecution(
                response=replay.response,
                resource_type=replay.resource_type,
                resource_id=replay.resource_id,
                replayed=True,
            )
