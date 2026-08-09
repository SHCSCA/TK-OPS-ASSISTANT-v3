from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import ParamSpec, TypeVar

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.models.account_connection import AccountConnection
from domain.models.device_workspace import (
    BrowserInstance,
    DeviceWorkspace,
    ExecutionBinding,
)
from repositories.account_connection_v1_queries import (
    ExecutionBindingResources,
    binding_candidates_query as _binding_candidates_query,
    binding_evidence_query as _binding_evidence_query,
    browser_for_workspace_query as _browser_for_workspace_query,
    browser_query as _browser_query,
    execute_connection_update as _execute_connection_update,
    existing_binding_query as _existing_binding_query,
    load_binding_evidence as _load_binding_evidence,
    workspace_query as _workspace_query,
)

log = logging.getLogger(__name__)

__all__ = [
    "AccountConnectionPersistenceError",
    "AccountConnectionResources",
    "AccountConnectionV1Repository",
    "ExecutionBindingResources",
    "_binding_candidates_query",
    "_binding_evidence_query",
    "_browser_for_workspace_query",
    "_browser_query",
    "_existing_binding_query",
    "_workspace_query",
]

_AUTH_STATUSES = frozenset({"unknown", "required", "valid", "expired", "failed"})
_HEALTH_STATUSES = frozenset(
    {"unknown", "checking", "ready", "attention", "failed"}
)

_P = ParamSpec("_P")
_R = TypeVar("_R")


def _log_database_errors(
    operation: str,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    def decorator(function: Callable[_P, _R]) -> Callable[_P, _R]:
        @wraps(function)
        def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            try:
                return function(*args, **kwargs)
            except SQLAlchemyError:
                log.exception("账号连接仓储数据库操作失败", extra={"operation": operation})
                raise

        return wrapped

    return decorator


class AccountConnectionPersistenceError(ValueError):
    """账号连接对象不满足持久化范围或字段约束。"""


@dataclass(frozen=True, slots=True)
class AccountConnectionResources:
    connection: AccountConnection
    execution_binding: ExecutionBinding | None
    device_workspace: DeviceWorkspace | None
    browser_instance: BrowserInstance | None


class AccountConnectionV1Repository:
    """持久化账号连接，并在每条查询中强制账号范围。"""

    @_log_database_errors("列出账号连接候选")
    def list_connection_candidates(
        self,
        account_id: str,
        session: Session,
    ) -> tuple[ExecutionBindingResources, ...]:
        rows = session.execute(
            _binding_candidates_query(account_id)
        ).all()
        candidates: list[ExecutionBindingResources] = []
        seen_pairs: set[tuple[str, str]] = set()
        for binding, workspace, browser in rows:
            pair = (workspace.id, browser.id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            candidates.append(
                ExecutionBindingResources(
                    execution_binding=binding,
                    device_workspace=workspace,
                    browser_instance=browser,
                )
            )
        return tuple(candidates)

    @_log_database_errors("读取设备工作区")
    def get_workspace(
        self,
        account_id: str,
        session: Session,
        *,
        workspace_id: str,
    ) -> DeviceWorkspace | None:
        return session.scalars(_workspace_query(account_id, workspace_id)).one_or_none()

    @_log_database_errors("读取浏览器实例")
    def get_browser_instance(
        self,
        account_id: str,
        session: Session,
        *,
        browser_instance_id: str,
    ) -> BrowserInstance | None:
        statement = _browser_query(account_id, browser_instance_id)
        return session.scalars(statement).one_or_none()

    @_log_database_errors("读取执行绑定")
    def resolve_active_binding(
        self,
        account_id: str,
        session: Session,
        *,
        binding_id: str,
    ) -> ExecutionBindingResources | None:
        return _load_binding_evidence(session, account_id, binding_id)

    @_log_database_errors("读取账号连接组合")
    def get_connection(
        self,
        account_id: str,
        session: Session,
    ) -> AccountConnectionResources | None:
        connection = session.scalars(
            select(AccountConnection).where(
                AccountConnection.account_id == account_id
            )
        ).one_or_none()
        if connection is None:
            return None
        binding_id = connection.active_execution_binding_id
        if binding_id is None:
            return AccountConnectionResources(
                connection=connection,
                execution_binding=None,
                device_workspace=None,
                browser_instance=None,
            )
        evidence = _load_binding_evidence(
            session,
            account_id,
            binding_id,
        )
        if evidence is None:
            log.warning(
                "账号连接引用的执行绑定证据不完整",
                extra={
                    "account_id": account_id,
                    "connection_id": connection.id,
                    "binding_id": binding_id,
                },
            )
            return AccountConnectionResources(
                connection=connection,
                execution_binding=None,
                device_workspace=None,
                browser_instance=None,
            )
        return AccountConnectionResources(
            connection=connection,
            execution_binding=evidence.execution_binding,
            device_workspace=evidence.device_workspace,
            browser_instance=evidence.browser_instance,
        )

    @_log_database_errors("新增账号连接")
    def add_connection(
        self,
        account_id: str,
        session: Session,
        connection: AccountConnection,
    ) -> AccountConnection:
        if account_id != connection.account_id:
            _raise_persistence_error(
                account_id,
                "账号连接与请求账号不一致",
            )
        _validate_connection_state(
            account_id,
            auth_status=connection.auth_status,
            health_status=connection.health_status,
            revision=connection.revision,
        )
        if connection.active_execution_binding_id is not None:
            evidence = _load_binding_evidence(
                session,
                account_id,
                connection.active_execution_binding_id,
            )
            if evidence is None:
                _raise_persistence_error(
                    account_id,
                    "账号连接引用的执行绑定与账号范围不一致",
                )
        session.add(connection)
        session.flush()
        return connection

    @_log_database_errors("更新账号连接状态")
    def update_connection_state(
        self,
        account_id: str,
        session: Session,
        *,
        connection_id: str,
        expected_revision: int,
        auth_status: str,
        health_status: str,
        last_checked_at: str | None,
        error_code: str | None,
        error_log_id: str | None,
        updated_at: str,
    ) -> AccountConnection | None:
        _validate_connection_state(
            account_id,
            auth_status=auth_status,
            health_status=health_status,
            revision=expected_revision,
        )
        return _execute_connection_update(
            session,
            account_id,
            connection_id,
            expected_revision=expected_revision,
            values={
                "auth_status": auth_status,
                "health_status": health_status,
                "last_checked_at": last_checked_at,
                "error_code": error_code,
                "error_log_id": error_log_id,
                "updated_at": updated_at,
            },
        )

    @_log_database_errors("选择现有执行绑定")
    def find_existing_execution_binding(
        self,
        account_id: str,
        session: Session,
        *,
        workspace_id: str,
        browser_instance_id: str,
    ) -> ExecutionBinding | None:
        return session.scalars(
            _existing_binding_query(
                account_id,
                workspace_id,
                browser_instance_id,
            )
        ).one_or_none()

    @_log_database_errors("设置活动执行绑定")
    def set_active_binding(
        self,
        account_id: str,
        session: Session,
        *,
        connection_id: str,
        binding_id: str,
        expected_revision: int,
        updated_at: str,
    ) -> AccountConnection | None:
        _require_positive_revision(account_id, expected_revision)
        if _load_binding_evidence(session, account_id, binding_id) is None:
            return None
        return _execute_connection_update(
            session,
            account_id,
            connection_id,
            expected_revision=expected_revision,
            values={
                "active_execution_binding_id": binding_id,
                "updated_at": updated_at,
            },
        )

    @_log_database_errors("激活账号执行环境")
    def activate_execution_binding(
        self,
        account_id: str,
        session: Session,
        *,
        binding_id: str,
    ) -> ExecutionBinding | None:
        evidence = _load_binding_evidence(session, account_id, binding_id)
        if evidence is None:
            return None
        session.execute(
            update(ExecutionBinding)
            .where(
                ExecutionBinding.account_id == account_id,
                ExecutionBinding.id != binding_id,
                ExecutionBinding.status == "active",
            )
            .values(
                status="inactive",
                revision=ExecutionBinding.revision + 1,
            )
        )
        session.flush()
        evidence.execution_binding.status = "active"
        evidence.execution_binding.revision += 1
        session.flush()
        return evidence.execution_binding

    @_log_database_errors("解除活动执行绑定")
    def clear_active_binding(
        self,
        account_id: str,
        session: Session,
        *,
        connection_id: str,
        expected_revision: int,
        updated_at: str,
    ) -> AccountConnection | None:
        _require_positive_revision(account_id, expected_revision)
        return _execute_connection_update(
            session,
            account_id,
            connection_id,
            expected_revision=expected_revision,
            values={
                "active_execution_binding_id": None,
                "updated_at": updated_at,
            },
        )


def _validate_connection_state(
    account_id: str,
    *,
    auth_status: str,
    health_status: str,
    revision: int,
) -> None:
    _require_positive_revision(account_id, revision)
    if auth_status not in _AUTH_STATUSES:
        _raise_persistence_error(account_id, "账号授权状态不符合持久化约束")
    if health_status not in _HEALTH_STATUSES:
        _raise_persistence_error(account_id, "账号连接健康状态不符合持久化约束")


def _require_positive_revision(account_id: str, revision: int) -> None:
    if (
        isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision < 1
    ):
        _raise_persistence_error(account_id, "账号连接修订号必须大于零")


def _raise_persistence_error(account_id: str, message: str) -> None:
    log.warning(
        "账号连接仓储拒绝不一致写入",
        extra={
            "account_id": account_id,
            "reason": message,
        },
    )
    raise AccountConnectionPersistenceError(message)
