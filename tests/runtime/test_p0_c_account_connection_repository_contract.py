from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy.dialects import sqlite
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import repositories.account_connection_v1_repository as repository_module
from domain.models.account_connection import AccountConnection
from domain.models.device_workspace import (
    BrowserInstance,
    DeviceWorkspace,
    ExecutionBinding,
)
from repositories.account_connection_v1_repository import (
    AccountConnectionPersistenceError,
    AccountConnectionV1Repository,
    ExecutionBindingResources,
)


class _ScalarResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def one_or_none(self) -> object | None:
        return self._value


class _RowResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def one_or_none(self) -> object | None:
        return self._value


class _FakeSession:
    def __init__(
        self,
        *,
        scalar_values: list[object | None] | None = None,
        row_values: list[object | None] | None = None,
    ) -> None:
        self.scalar_values = list(scalar_values or [])
        self.row_values = list(row_values or [])
        self.scalar_statements: list[object] = []
        self.row_statements: list[object] = []
        self.added: list[object] = []
        self.flush_count = 0

    def scalars(self, statement: object) -> _ScalarResult:
        self.scalar_statements.append(statement)
        value = self.scalar_values.pop(0) if self.scalar_values else None
        return _ScalarResult(value)

    def execute(self, statement: object) -> _RowResult:
        self.row_statements.append(statement)
        value = self.row_values.pop(0) if self.row_values else None
        return _RowResult(value)

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flush_count += 1


class _FailingSession:
    def scalars(self, _statement: object) -> _ScalarResult:
        raise SQLAlchemyError("database unavailable")


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_public_repository_methods_put_account_id_before_session() -> None:
    public_methods = {
        name: member
        for name, member in inspect.getmembers(
            AccountConnectionV1Repository,
            predicate=inspect.isfunction,
        )
        if not name.startswith("_")
    }
    assert public_methods
    for method in public_methods.values():
        parameters = tuple(inspect.signature(method).parameters)
        assert parameters[:3] == ("self", "account_id", "session")


def test_resource_queries_filter_account_and_real_resource_ids() -> None:
    workspace_sql = _sql(
        repository_module._workspace_query("account-a", "workspace-a")
    )
    assert "device_workspaces.account_id = 'account-a'" in workspace_sql
    assert "device_workspaces.id = 'workspace-a'" in workspace_sql

    browser_sql = _sql(
        repository_module._browser_for_workspace_query(
            "account-a",
            "browser-a",
            "workspace-a",
        )
    )
    assert "browser_instances.account_id = 'account-a'" in browser_sql
    assert "browser_instances.id = 'browser-a'" in browser_sql
    assert "browser_instances.workspace_id = 'workspace-a'" in browser_sql
    assert "device_workspaces.account_id = 'account-a'" in browser_sql
    assert "device_workspaces.id = 'workspace-a'" in browser_sql


def test_binding_queries_require_the_complete_account_evidence_chain() -> None:
    evidence_sql = _sql(
        repository_module._binding_evidence_query(
            "account-a",
            "binding-a",
        )
    )
    required_fragments = {
        "execution_bindings.account_id = 'account-a'",
        "execution_bindings.id = 'binding-a'",
        "device_workspaces.account_id = 'account-a'",
        "browser_instances.account_id = 'account-a'",
        "execution_bindings.device_workspace_id = device_workspaces.id",
        "execution_bindings.browser_instance_id = browser_instances.id",
        "browser_instances.workspace_id = device_workspaces.id",
    }
    assert all(fragment in evidence_sql for fragment in required_fragments)

    reusable_sql = _sql(
        repository_module._existing_binding_query(
            "account-a",
            "workspace-a",
            "browser-a",
        )
    )
    assert "execution_bindings.device_workspace_id = 'workspace-a'" in reusable_sql
    assert "execution_bindings.browser_instance_id = 'browser-a'" in reusable_sql
    assert "browser_instances.workspace_id = 'workspace-a'" in reusable_sql
    assert "device_workspaces.id = 'workspace-a'" in reusable_sql


def test_existing_binding_selection_never_creates_or_mutates_resources() -> None:
    repository = AccountConnectionV1Repository()
    missing_session = _FakeSession(scalar_values=[None])
    missing = repository.find_existing_execution_binding(
        "account-a",
        cast(Session, missing_session),
        workspace_id="workspace-a",
        browser_instance_id="browser-a",
    )
    assert missing is None
    assert missing_session.added == []
    assert missing_session.flush_count == 0

    existing = _binding()
    existing.status = "reserved"
    existing.source = "runtime-supervisor"
    existing.metadata_json = '{"owner":"supervisor"}'
    session = _FakeSession(scalar_values=[existing])
    binding = repository.find_existing_execution_binding(
        "account-a",
        cast(Session, session),
        workspace_id="workspace-a",
        browser_instance_id="browser-a",
    )
    assert binding is existing
    assert binding.status == "reserved"
    assert binding.source == "runtime-supervisor"
    assert binding.metadata_json == '{"owner":"supervisor"}'
    assert session.added == []
    assert session.flush_count == 0


def test_connection_writes_reject_scope_and_status_mismatches() -> None:
    repository = AccountConnectionV1Repository()
    session = cast(Session, _FakeSession())
    connection = _connection(account_id="account-a")

    _assert_persistence_error(
        lambda: repository.add_connection("account-b", session, connection),
        "账号连接与请求账号不一致",
    )
    _assert_persistence_error(
        lambda: repository.update_connection_state(
            "account-a",
            session,
            connection_id="connection-a",
            expected_revision=1,
            auth_status="invented",
            health_status="ready",
            last_checked_at=None,
            error_code=None,
            error_log_id=None,
            updated_at="2026-07-26T00:00:00Z",
        ),
        "账号授权状态不符合持久化约束",
    )


def test_clear_binding_is_scoped_cas_and_never_deletes_audit_rows() -> None:
    repository = AccountConnectionV1Repository()
    session = _FakeSession(scalar_values=[None])
    result = repository.clear_active_binding(
        "account-a",
        cast(Session, session),
        connection_id="connection-a",
        expected_revision=4,
        updated_at="2026-07-26T00:00:00Z",
    )
    assert result is None
    statement_sql = _sql(session.scalar_statements[0])
    assert "update account_connections" in statement_sql
    assert "account_connections.account_id = 'account-a'" in statement_sql
    assert "account_connections.id = 'connection-a'" in statement_sql
    assert "account_connections.revision = 4" in statement_sql
    assert "active_execution_binding_id=null" in statement_sql

    module_source = inspect.getsource(repository_module)
    assert "session.delete" not in module_source
    assert "domain.models.execution" not in module_source
    assert "DeviceWorkspace(" not in module_source
    assert "BrowserInstance(" not in module_source


def test_binding_resolution_requires_complete_evidence() -> None:
    binding = _binding()
    workspace = _workspace()
    browser = _browser()
    session = _FakeSession(row_values=[(binding, workspace, browser)])
    resources = AccountConnectionV1Repository().resolve_active_binding(
        "account-a",
        cast(Session, session),
        binding_id="binding-a",
    )
    assert resources == ExecutionBindingResources(
        execution_binding=binding,
        device_workspace=workspace,
        browser_instance=browser,
    )

    incomplete_session = _FakeSession(row_values=[None])
    assert (
        AccountConnectionV1Repository().resolve_active_binding(
            "account-a",
            cast(Session, incomplete_session),
            binding_id="binding-a",
        )
        is None
    )


def test_incomplete_active_evidence_is_returned_as_unbound_resources() -> None:
    connection = _connection(account_id="account-a")
    connection.active_execution_binding_id = "binding-a"
    session = _FakeSession(
        scalar_values=[connection],
        row_values=[None],
    )
    resources = AccountConnectionV1Repository().get_connection(
        "account-a",
        cast(Session, session),
    )
    assert resources is not None
    assert resources.connection is connection
    assert resources.execution_binding is None
    assert resources.device_workspace is None
    assert resources.browser_instance is None


def test_database_failures_are_logged_in_chinese_and_reraised() -> None:
    handler = _ListHandler()
    logger = repository_module.log
    previous_level = logger.level
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)
    try:
        try:
            AccountConnectionV1Repository().get_workspace(
                "account-a",
                cast(Session, _FailingSession()),
                workspace_id="workspace-a",
            )
        except SQLAlchemyError:
            pass
        else:
            raise AssertionError("数据库异常必须继续抛给事务边界")
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    assert handler.records
    assert handler.records[-1].getMessage() == "账号连接仓储数据库操作失败"
    assert getattr(handler.records[-1], "operation") == "读取设备工作区"


def _sql(statement: Any) -> str:
    compiled = statement.compile(
        dialect=sqlite.dialect(),
        compile_kwargs={"literal_binds": True},
    )
    return " ".join(str(compiled).lower().split())


def _workspace() -> DeviceWorkspace:
    return DeviceWorkspace(
        id="workspace-a",
        account_id="account-a",
        name="工作区",
        root_path="workspace-ref",
        status="ready",
        error_count=0,
    )


def _browser() -> BrowserInstance:
    return BrowserInstance(
        id="browser-a",
        account_id="account-a",
        workspace_id="workspace-a",
        name="浏览器",
        profile_path="profile-ref",
        status="stopped",
    )


def _binding() -> ExecutionBinding:
    observed_at = datetime(2026, 7, 26, tzinfo=UTC)
    return ExecutionBinding(
        id="binding-a",
        account_id="account-a",
        device_workspace_id="workspace-a",
        browser_instance_id="browser-a",
        status="active",
        source="account-v1",
        metadata_json=None,
        created_at=observed_at,
        updated_at=observed_at,
    )


def _connection(*, account_id: str) -> AccountConnection:
    return AccountConnection(
        id="connection-a",
        account_id=account_id,
        credential_ref=None,
        session_ref=None,
        auth_status="unknown",
        health_status="unknown",
        active_execution_binding_id=None,
        last_checked_at=None,
        error_code=None,
        error_log_id=None,
        revision=1,
        created_at="2026-07-26T00:00:00Z",
        updated_at="2026-07-26T00:00:00Z",
    )


def _assert_persistence_error(
    action: Callable[[], object],
    expected_message: str,
) -> None:
    try:
        action()
    except AccountConnectionPersistenceError as exc:
        assert str(exc) == expected_message
    else:
        raise AssertionError("不一致写入必须被仓储拒绝")
