from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now
from domain.models.account import Account
from domain.models.device_workspace import (
    BrowserInstance,
    DeviceWorkspace,
    ExecutionBinding,
)
from errors import DomainError, ErrorCode


@dataclass(frozen=True, slots=True)
class ExecutionEnvironmentAggregate:
    binding: ExecutionBinding
    browser: BrowserInstance
    workspace: DeviceWorkspace


class ExecutionEnvironmentV1Repository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ensure_draft(
        self,
        *,
        account_id: str,
        idempotency_key: str,
        name: str,
        workspace_display_name: str,
        root_ref: str,
        root_path: str,
        browser_kind: str,
    ) -> ExecutionEnvironmentAggregate:
        environment_id = _stable_id("env", account_id, idempotency_key)
        workspace_id = _stable_id("ws", account_id, idempotency_key)
        browser_id = _stable_id("browser", account_id, idempotency_key)
        with self._session_factory() as session:
            account = session.get(Account, account_id)
            if account is None:
                raise DomainError(
                    ErrorCode.ACCOUNT_NOT_FOUND,
                    "账号不存在，请刷新后重试",
                    status_code=404,
                )
            if account.status == "archived":
                raise DomainError(
                    ErrorCode.ACCOUNT_ARCHIVED,
                    "账号已归档，不能创建执行环境",
                    status_code=409,
                )
            existing = _load_aggregate(session, account_id, environment_id)
            if existing is not None:
                metadata = _read_metadata(existing.binding.metadata_json)
                if (
                    existing.workspace.root_ref != root_ref
                    or metadata.get("name") != name
                    or metadata.get("browserKind") != browser_kind
                ):
                    raise DomainError(
                        ErrorCode.REQUEST_CONFLICT,
                        "相同幂等键对应的执行环境请求内容不同",
                        status_code=409,
                    )
                _detach(session, existing)
                return existing
            workspace = DeviceWorkspace(
                id=workspace_id,
                account_id=account_id,
                name=name,
                root_path=root_path,
                root_ref=root_ref,
                ownership_state="owned",
                revision=1,
                error_code=None,
                error_log_id=None,
                status="provisioning",
                error_count=0,
            )
            browser = BrowserInstance(
                id=browser_id,
                account_id=account_id,
                workspace_id=workspace_id,
                name="Microsoft Edge" if browser_kind == "edge" else "Google Chrome",
                profile_path=str(Path(root_path) / "browser-profile"),
                status="starting",
                ownership_state="owned",
                revision=1,
                error_code=None,
                error_log_id=None,
                error_message=None,
            )
            binding = ExecutionBinding(
                id=environment_id,
                account_id=account_id,
                device_workspace_id=workspace_id,
                browser_instance_id=browser_id,
                status="provisioning",
                source="p0g",
                metadata_json=json.dumps(
                    {
                        "name": name,
                        "browserKind": browser_kind,
                        "workspaceDisplayName": workspace_display_name,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                revision=1,
                error_code=None,
                error_log_id=None,
                last_task_id=None,
                last_retry_of_task_id=None,
            )
            # 模型未声明 ORM 关系，按外键依赖顺序显式落库。
            session.add(workspace)
            session.flush()
            session.add(browser)
            session.flush()
            session.add(binding)
            session.commit()
            session.refresh(workspace)
            session.refresh(browser)
            session.refresh(binding)
            result = ExecutionEnvironmentAggregate(binding, browser, workspace)
            _detach(session, result)
            return result

    def list_owned(self, account_id: str) -> list[ExecutionEnvironmentAggregate]:
        with self._session_factory() as session:
            rows = session.execute(_aggregate_query(account_id)).all()
            results = [ExecutionEnvironmentAggregate(*row) for row in rows]
            for result in results:
                _detach(session, result)
            return results

    def get_owned(
        self,
        account_id: str,
        environment_id: str,
    ) -> ExecutionEnvironmentAggregate | None:
        with self._session_factory() as session:
            result = _load_aggregate(session, account_id, environment_id)
            if result is not None:
                _detach(session, result)
            return result

    def get_owned_including_deleted(
        self,
        account_id: str,
        environment_id: str,
    ) -> ExecutionEnvironmentAggregate | None:
        with self._session_factory() as session:
            row = session.execute(
                _aggregate_query(account_id, include_deleted=True).where(
                    ExecutionBinding.id == environment_id
                )
            ).one_or_none()
            result = ExecutionEnvironmentAggregate(*row) if row else None
            if result is not None:
                _detach(session, result)
            return result

    def mark_ready(
        self,
        *,
        account_id: str,
        environment_id: str,
        activate: bool,
        executable_path: str,
        process_id: int,
        debug_host: str,
        debug_port: int,
        runtime_evidence_json: str,
    ) -> int:
        with self._session_factory() as session:
            result = _require_aggregate(session, account_id, environment_id)
            if activate:
                for active in session.scalars(
                    select(ExecutionBinding).where(
                        ExecutionBinding.account_id == account_id,
                        ExecutionBinding.status == "active",
                        ExecutionBinding.id != environment_id,
                    )
                ):
                    active.status = "inactive"
                    active.revision += 1
            now = utc_now()
            result.workspace.status = "ready"
            result.workspace.error_code = None
            result.workspace.error_log_id = None
            result.workspace.revision += 1
            result.browser.status = "running"
            result.browser.process_id = process_id
            result.browser.debug_host = debug_host
            result.browser.debug_port = debug_port
            result.browser.executable_path = executable_path
            result.browser.runtime_evidence_json = runtime_evidence_json
            result.browser.last_checked_at = now
            result.browser.last_started_at = now
            result.browser.error_code = None
            result.browser.error_log_id = None
            result.browser.error_message = None
            result.browser.revision += 1
            result.binding.status = "active" if activate else "inactive"
            result.binding.error_code = None
            result.binding.error_log_id = None
            result.binding.revision += 1
            session.commit()
            return int(result.binding.revision)

    def record_task(
        self,
        *,
        account_id: str,
        environment_id: str,
        task_id: str,
        retry_of_task_id: str | None,
        expected_revision: int | None = None,
    ) -> int:
        with self._session_factory() as session:
            result = _require_aggregate(session, account_id, environment_id)
            if (
                expected_revision is not None
                and int(result.binding.revision) != expected_revision
            ):
                raise DomainError(
                    ErrorCode.REVISION_CONFLICT,
                    "执行环境状态已变化，请刷新后重试",
                    status_code=409,
                )
            result.binding.last_task_id = task_id
            result.binding.last_retry_of_task_id = retry_of_task_id
            if retry_of_task_id is not None:
                result.binding.status = "provisioning"
                result.binding.error_code = None
                result.binding.error_log_id = None
                result.workspace.status = "provisioning"
                result.workspace.error_code = None
                result.workspace.error_log_id = None
                result.workspace.revision += 1
                result.browser.status = "starting"
                result.browser.error_code = None
                result.browser.error_log_id = None
                result.browser.error_message = None
                result.browser.revision += 1
            result.binding.revision += 1
            session.commit()
            return int(result.binding.revision)

    def mark_failed(
        self,
        *,
        account_id: str,
        environment_id: str,
        error_code: str,
        error_log_id: str,
        browser_orphaned: bool = False,
    ) -> None:
        with self._session_factory() as session:
            result = _require_aggregate(session, account_id, environment_id)
            result.workspace.status = "failed"
            result.workspace.error_code = error_code
            result.workspace.error_log_id = error_log_id
            result.workspace.error_count += 1
            result.workspace.revision += 1
            result.browser.status = "orphaned" if browser_orphaned else "failed"
            result.browser.error_code = error_code
            result.browser.error_log_id = error_log_id
            result.browser.error_message = "执行环境创建失败，请查看日志后重试。"
            result.browser.revision += 1
            result.binding.status = "failed"
            result.binding.error_code = error_code
            result.binding.error_log_id = error_log_id
            result.binding.revision += 1
            session.commit()

    def mark_stopped_for_archive(
        self,
        *,
        account_id: str,
        environment_id: str,
    ) -> None:
        with self._session_factory() as session:
            result = _require_aggregate(session, account_id, environment_id)
            now = utc_now()
            result.workspace.status = "offline"
            result.workspace.revision += 1
            result.browser.status = "stopped"
            result.browser.process_id = None
            result.browser.debug_host = None
            result.browser.debug_port = None
            result.browser.last_stopped_at = now
            result.browser.error_code = None
            result.browser.error_log_id = None
            result.browser.error_message = None
            result.browser.revision += 1
            result.binding.status = "inactive"
            result.binding.error_code = None
            result.binding.error_log_id = None
            result.binding.revision += 1
            session.commit()

    def mark_cleanup_failed(
        self,
        *,
        account_id: str,
        environment_id: str,
        error_code: str,
        error_log_id: str,
        browser_orphaned: bool,
    ) -> None:
        with self._session_factory() as session:
            result = _require_aggregate(session, account_id, environment_id)
            result.workspace.status = "cleanup_failed"
            result.workspace.error_code = error_code
            result.workspace.error_log_id = error_log_id
            result.workspace.error_count += 1
            result.workspace.revision += 1
            if browser_orphaned:
                result.browser.status = "orphaned"
            result.browser.error_code = error_code
            result.browser.error_log_id = error_log_id
            result.browser.error_message = "归档清理失败，请人工检查后重试。"
            result.browser.revision += 1
            result.binding.status = "cleanup_failed"
            result.binding.error_code = error_code
            result.binding.error_log_id = error_log_id
            result.binding.revision += 1
            session.commit()

    def mark_checked(
        self,
        *,
        account_id: str,
        environment_id: str,
        healthy: bool,
        error_code: str | None = None,
        error_log_id: str | None = None,
    ) -> int:
        with self._session_factory() as session:
            result = _require_aggregate(session, account_id, environment_id)
            now = utc_now()
            result.browser.last_checked_at = now
            result.browser.error_code = error_code
            result.browser.error_log_id = error_log_id
            result.browser.error_message = (
                None if healthy else "执行环境检查失败，请查看日志后重试。"
            )
            if healthy and result.browser.status == "failed":
                result.browser.status = "running"
            elif not healthy:
                result.browser.status = "stopped"
                result.browser.process_id = None
                result.browser.debug_host = None
                result.browser.debug_port = None
                result.browser.last_stopped_at = now
            result.browser.revision += 1
            result.workspace.error_code = error_code
            result.workspace.error_log_id = error_log_id
            if not healthy:
                result.workspace.status = "offline"
            result.workspace.revision += 1
            result.binding.error_code = error_code
            result.binding.error_log_id = error_log_id
            if not healthy:
                result.binding.status = "failed"
            result.binding.revision += 1
            session.commit()
            return int(result.binding.revision)

    def mark_deleted(
        self,
        *,
        account_id: str,
        environment_id: str,
    ) -> int:
        with self._session_factory() as session:
            result = _require_aggregate(session, account_id, environment_id)
            now = utc_now()
            result.workspace.status = "offline"
            result.workspace.revision += 1
            result.browser.status = "stopped"
            result.browser.process_id = None
            result.browser.debug_host = None
            result.browser.debug_port = None
            result.browser.last_stopped_at = now
            result.browser.revision += 1
            result.binding.status = "deleted"
            result.binding.error_code = None
            result.binding.error_log_id = None
            result.binding.revision += 1
            session.commit()
            return int(result.binding.revision)


def _aggregate_query(account_id: str, *, include_deleted: bool = False):
    statement = (
        select(ExecutionBinding, BrowserInstance, DeviceWorkspace)
        .join(
            DeviceWorkspace,
            DeviceWorkspace.id == ExecutionBinding.device_workspace_id,
        )
        .join(
            BrowserInstance,
            BrowserInstance.id == ExecutionBinding.browser_instance_id,
        )
        .where(
            ExecutionBinding.account_id == account_id,
            DeviceWorkspace.account_id == account_id,
            BrowserInstance.account_id == account_id,
            BrowserInstance.workspace_id == DeviceWorkspace.id,
            DeviceWorkspace.ownership_state != "legacy_unclaimed",
        )
        .order_by(ExecutionBinding.updated_at.desc())
    )
    if not include_deleted:
        statement = statement.where(ExecutionBinding.status != "deleted")
    return statement


def _load_aggregate(
    session: Session,
    account_id: str,
    environment_id: str,
) -> ExecutionEnvironmentAggregate | None:
    row = session.execute(
        _aggregate_query(account_id).where(ExecutionBinding.id == environment_id)
    ).one_or_none()
    return ExecutionEnvironmentAggregate(*row) if row else None


def _require_aggregate(
    session: Session,
    account_id: str,
    environment_id: str,
) -> ExecutionEnvironmentAggregate:
    result = _load_aggregate(session, account_id, environment_id)
    if result is None:
        raise DomainError(
            ErrorCode.EXECUTION_ENVIRONMENT_NOT_FOUND,
            "执行环境不存在或不属于当前账号",
            status_code=404,
        )
    return result


def _stable_id(prefix: str, account_id: str, idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"{prefix}_{uuid5(NAMESPACE_URL, f'tk-ops:{account_id}:{prefix}:{digest}').hex}"


def _read_metadata(raw: str | None) -> dict[str, object]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _detach(session: Session, aggregate: ExecutionEnvironmentAggregate) -> None:
    session.expunge(aggregate.binding)
    session.expunge(aggregate.browser)
    session.expunge(aggregate.workspace)
