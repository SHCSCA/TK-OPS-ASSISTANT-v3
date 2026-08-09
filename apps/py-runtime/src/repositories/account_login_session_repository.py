from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models.account import Account
from domain.models.account_connection import AccountConnection
from domain.models.account_login_session import AccountLoginSession
from domain.models.device_workspace import BrowserInstance, ExecutionBinding
from errors import DomainError, ErrorCode

log = logging.getLogger(__name__)
ACTIVE_STATES = ("preparing", "waiting_user", "probing")


@dataclass(frozen=True, slots=True)
class LoginSessionAggregate:
    login_session: AccountLoginSession
    connection: AccountConnection
    binding: ExecutionBinding
    browser: BrowserInstance


class AccountLoginSessionRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ensure(
        self,
        *,
        account_id: str,
        idempotency_key: str,
        timeout_seconds: int,
    ) -> LoginSessionAggregate:
        session_id = _stable_session_id(account_id, idempotency_key)
        try:
            with self._session_factory() as database:
                existing = self._load(database, account_id, session_id)
                if existing is not None:
                    _detach(database, existing)
                    return existing
                account = database.get(Account, account_id)
                connection = database.scalar(
                    select(AccountConnection).where(
                        AccountConnection.account_id == account_id
                    )
                )
                if account is None or connection is None:
                    raise DomainError(
                        ErrorCode.ACCOUNT_CONNECTION_REQUIRED,
                        "请先绑定可用执行环境，再开始登录",
                        status_code=409,
                    )
                binding_id = connection.active_execution_binding_id
                if binding_id is None:
                    raise DomainError(
                        ErrorCode.ACCOUNT_CONNECTION_REQUIRED,
                        "请先绑定可用执行环境，再开始登录",
                        status_code=409,
                    )
                active = database.scalar(
                    select(AccountLoginSession).where(
                        AccountLoginSession.account_id == account_id,
                        AccountLoginSession.state.in_(ACTIVE_STATES),
                    )
                )
                if active is not None:
                    aggregate = self._load(database, account_id, active.id)
                    if aggregate is None:
                        raise DomainError(
                            ErrorCode.LOGIN_SESSION_STATE_CONFLICT,
                            "当前登录尝试状态不完整，请取消后重试",
                            status_code=409,
                        )
                    _detach(database, aggregate)
                    return aggregate
                binding = database.get(ExecutionBinding, binding_id)
                browser = (
                    database.get(BrowserInstance, binding.browser_instance_id)
                    if binding is not None and binding.browser_instance_id
                    else None
                )
                if (
                    binding is None
                    or binding.account_id != account_id
                    or browser is None
                    or browser.account_id != account_id
                    or browser.workspace_id != binding.device_workspace_id
                ):
                    raise DomainError(
                        ErrorCode.EXECUTION_BINDING_INVALID,
                        "账号执行环境证据不完整，请重新绑定",
                        status_code=409,
                    )
                now = datetime.now(UTC)
                login_session = AccountLoginSession(
                    id=session_id,
                    account_id=account_id,
                    execution_binding_id=binding.id,
                    browser_instance_id=browser.id,
                    state="preparing",
                    prepare_task_id=None,
                    probe_task_id=None,
                    expected_identity=_normalize_identity(account.username),
                    detected_identity=None,
                    expires_at=_time_text(now + timedelta(seconds=timeout_seconds)),
                    error_code=None,
                    error_log_id=None,
                    revision=1,
                    created_at=_time_text(now),
                    updated_at=_time_text(now),
                )
                database.add(login_session)
                database.commit()
                result = LoginSessionAggregate(
                    login_session,
                    connection,
                    binding,
                    browser,
                )
                _detach(database, result)
                return result
        except DomainError:
            raise
        except Exception:
            log.exception("创建账号登录尝试失败", extra={"account_id": account_id})
            raise

    def get_owned(
        self,
        account_id: str,
        session_id: str,
    ) -> LoginSessionAggregate | None:
        with self._session_factory() as database:
            result = self._load(database, account_id, session_id)
            if result is not None:
                _detach(database, result)
            return result

    def get_latest_for_account(
        self,
        account_id: str,
    ) -> LoginSessionAggregate | None:
        with self._session_factory() as database:
            session_id = database.scalar(
                select(AccountLoginSession.id)
                .where(AccountLoginSession.account_id == account_id)
                .order_by(AccountLoginSession.updated_at.desc())
                .limit(1)
            )
            result = (
                self._load(database, account_id, session_id)
                if session_id is not None
                else None
            )
            if result is not None:
                _detach(database, result)
            return result

    def set_task(
        self,
        *,
        account_id: str,
        session_id: str,
        task_kind: str,
        task_id: str,
    ) -> AccountLoginSession:
        with self._session_factory() as database:
            aggregate = self._require(database, account_id, session_id)
            if task_kind == "prepare":
                aggregate.login_session.prepare_task_id = task_id
            elif task_kind == "probe":
                aggregate.login_session.probe_task_id = task_id
            else:
                raise ValueError("登录任务类型无效")
            _touch(aggregate.login_session)
            database.commit()
            database.refresh(aggregate.login_session)
            database.expunge(aggregate.login_session)
            return aggregate.login_session

    def mark_waiting(self, *, account_id: str, session_id: str) -> None:
        self._set_state(account_id, session_id, state="waiting_user")

    def begin_probe(self, *, account_id: str, session_id: str) -> LoginSessionAggregate:
        with self._session_factory() as database:
            aggregate = self._require(database, account_id, session_id)
            if aggregate.login_session.expires_at <= _time_text(datetime.now(UTC)):
                aggregate.login_session.state = "timed_out"
                _touch(aggregate.login_session)
                database.commit()
                raise DomainError(
                    ErrorCode.LOGIN_SESSION_EXPIRED,
                    "登录尝试已超时，请重新开始登录",
                    status_code=409,
                )
            if aggregate.login_session.state != "waiting_user":
                raise DomainError(
                    ErrorCode.LOGIN_SESSION_STATE_CONFLICT,
                    "当前登录状态不能开始探测，请刷新后重试",
                    status_code=409,
                )
            aggregate.login_session.state = "probing"
            _touch(aggregate.login_session)
            database.commit()
            _detach(database, aggregate)
            return aggregate

    def complete_probe(
        self,
        *,
        account_id: str,
        session_id: str,
        detected_identity: str,
        session_ref: str,
    ) -> None:
        with self._session_factory() as database:
            aggregate = self._require(database, account_id, session_id)
            aggregate.login_session.state = "completed"
            aggregate.login_session.detected_identity = detected_identity
            aggregate.login_session.error_code = None
            aggregate.login_session.error_log_id = None
            _touch(aggregate.login_session)
            aggregate.connection.session_ref = session_ref
            aggregate.connection.auth_status = "valid"
            aggregate.connection.health_status = "ready"
            aggregate.connection.last_checked_at = _time_text(datetime.now(UTC))
            aggregate.connection.error_code = None
            aggregate.connection.error_log_id = None
            aggregate.connection.revision += 1
            aggregate.connection.updated_at = _time_text(datetime.now(UTC))
            database.commit()

    def mark_probe_failed(
        self,
        *,
        account_id: str,
        session_id: str,
        error_code: str,
        error_log_id: str | None,
        retryable: bool,
        detected_identity: str | None = None,
    ) -> None:
        with self._session_factory() as database:
            aggregate = self._require(database, account_id, session_id)
            aggregate.login_session.state = "waiting_user" if retryable else "failed"
            aggregate.login_session.detected_identity = detected_identity
            aggregate.login_session.error_code = error_code
            aggregate.login_session.error_log_id = error_log_id
            _touch(aggregate.login_session)
            aggregate.connection.auth_status = "required"
            aggregate.connection.health_status = "attention"
            aggregate.connection.error_code = error_code
            aggregate.connection.error_log_id = error_log_id
            aggregate.connection.revision += 1
            aggregate.connection.updated_at = _time_text(datetime.now(UTC))
            database.commit()

    def cancel(self, *, account_id: str, session_id: str) -> LoginSessionAggregate:
        with self._session_factory() as database:
            aggregate = self._require(database, account_id, session_id)
            if aggregate.login_session.state in {"completed", "cancelled"}:
                _detach(database, aggregate)
                return aggregate
            aggregate.login_session.state = "cancelled"
            _touch(aggregate.login_session)
            aggregate.connection.auth_status = "required"
            aggregate.connection.health_status = "attention"
            aggregate.connection.revision += 1
            aggregate.connection.updated_at = _time_text(datetime.now(UTC))
            database.commit()
            _detach(database, aggregate)
            return aggregate

    def mark_cancel_incomplete(
        self,
        *,
        account_id: str,
        session_id: str,
        error_log_id: str,
    ) -> None:
        with self._session_factory() as database:
            aggregate = self._require(database, account_id, session_id)
            if aggregate.login_session.state in {"completed", "cancelled"}:
                return
            aggregate.login_session.state = "failed"
            aggregate.login_session.error_code = (
                ErrorCode.LOGIN_SESSION_CANCEL_INCOMPLETE.value
            )
            aggregate.login_session.error_log_id = error_log_id
            _touch(aggregate.login_session)
            aggregate.connection.auth_status = "required"
            aggregate.connection.health_status = "attention"
            aggregate.connection.error_code = (
                ErrorCode.LOGIN_SESSION_CANCEL_INCOMPLETE.value
            )
            aggregate.connection.error_log_id = error_log_id
            aggregate.connection.revision += 1
            aggregate.connection.updated_at = _time_text(datetime.now(UTC))
            database.commit()

    def logout(self, *, account_id: str) -> str | None:
        with self._session_factory() as database:
            connection = database.scalar(
                select(AccountConnection).where(
                    AccountConnection.account_id == account_id
                )
            )
            if connection is None:
                raise DomainError(
                    ErrorCode.ACCOUNT_CONNECTION_REQUIRED,
                    "账号尚未建立连接",
                    status_code=409,
                )
            previous = connection.session_ref
            connection.session_ref = None
            connection.auth_status = "required"
            connection.health_status = "attention"
            connection.error_code = ErrorCode.ACCOUNT_PLATFORM_AUTH_REQUIRED.value
            connection.error_log_id = None
            connection.revision += 1
            connection.updated_at = _time_text(datetime.now(UTC))
            database.commit()
            return previous

    def _set_state(self, account_id: str, session_id: str, *, state: str) -> None:
        with self._session_factory() as database:
            aggregate = self._require(database, account_id, session_id)
            aggregate.login_session.state = state
            aggregate.login_session.error_code = None
            aggregate.login_session.error_log_id = None
            _touch(aggregate.login_session)
            database.commit()

    @staticmethod
    def _load(
        database: Session,
        account_id: str,
        session_id: str,
    ) -> LoginSessionAggregate | None:
        row = database.execute(
            select(
                AccountLoginSession,
                AccountConnection,
                ExecutionBinding,
                BrowserInstance,
            )
            .join(
                AccountConnection,
                AccountConnection.account_id == AccountLoginSession.account_id,
            )
            .join(
                ExecutionBinding,
                ExecutionBinding.id == AccountLoginSession.execution_binding_id,
            )
            .join(
                BrowserInstance,
                BrowserInstance.id == AccountLoginSession.browser_instance_id,
            )
            .where(
                AccountLoginSession.id == session_id,
                AccountLoginSession.account_id == account_id,
                AccountConnection.account_id == account_id,
                ExecutionBinding.account_id == account_id,
                BrowserInstance.account_id == account_id,
                AccountConnection.active_execution_binding_id == ExecutionBinding.id,
                ExecutionBinding.browser_instance_id == BrowserInstance.id,
            )
        ).one_or_none()
        return LoginSessionAggregate(*row) if row else None

    def _require(
        self,
        database: Session,
        account_id: str,
        session_id: str,
    ) -> LoginSessionAggregate:
        result = self._load(database, account_id, session_id)
        if result is None:
            raise DomainError(
                ErrorCode.LOGIN_SESSION_NOT_FOUND,
                "登录尝试不存在或不属于当前账号",
                status_code=404,
            )
        return result


def _stable_session_id(account_id: str, idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"login_{uuid5(NAMESPACE_URL, f'tk-ops:{account_id}:{digest}').hex}"


def _normalize_identity(value: str | None) -> str:
    return (value or "").strip().removeprefix("@").lower()


def _time_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _touch(login_session: AccountLoginSession) -> None:
    login_session.revision += 1
    login_session.updated_at = _time_text(datetime.now(UTC))


def _detach(database: Session, aggregate: LoginSessionAggregate) -> None:
    for value in (
        aggregate.login_session,
        aggregate.connection,
        aggregate.binding,
        aggregate.browser,
    ):
        database.expunge(value)


def session_secret_payload(aggregate: LoginSessionAggregate, identity: str) -> str:
    return json.dumps(
        {
            "schemaVersion": 1,
            "accountId": aggregate.login_session.account_id,
            "executionBindingId": aggregate.binding.id,
            "browserInstanceId": aggregate.browser.id,
            "identity": identity,
            "probedAt": _time_text(datetime.now(UTC)),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
