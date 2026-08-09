from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from errors import DomainError, ErrorCode
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentAggregate,
    ExecutionEnvironmentV1Repository,
)
from services.browser_runtime import BrowserRuntime
from services.events import RuntimeEventDraft, RuntimeEventService
from services.execution_environments.browser_process import (
    BrowserProcessOwnershipError,
    BrowserProcessOwnershipService,
)
from services.execution_environments.provisioning import (
    ExecutionEnvironmentProvisioner,
)

log = logging.getLogger(__name__)


class ExecutionEnvironmentActionService:
    def __init__(
        self,
        *,
        repository: ExecutionEnvironmentV1Repository,
        browser_runtime: BrowserRuntime,
        ownership_service: BrowserProcessOwnershipService,
        provisioner: ExecutionEnvironmentProvisioner,
        event_service: RuntimeEventService,
    ) -> None:
        self._repository = repository
        self._browser_runtime = browser_runtime
        self._ownership = ownership_service
        self._provisioner = provisioner
        self._events = event_service

    def start(
        self,
        *,
        account_id: str,
        environment_id: str,
        expected_revision: int,
        task_id: str,
    ) -> int:
        aggregate = self._require(account_id, environment_id)
        self._require_revision(aggregate, expected_revision)
        if aggregate.browser.status == "running":
            self._verify_ownership(account_id, aggregate)
            return int(aggregate.binding.revision)
        if aggregate.browser.status != "stopped":
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_INVALID,
                "只有已停止的执行环境可以重新启动",
                status_code=409,
            )
        return self._provisioner.provision(
            account_id=account_id,
            environment_id=environment_id,
            root_ref=aggregate.workspace.root_ref or "",
            activate_when_ready=False,
            task_id=task_id,
            event_type="execution_environment.started",
        )

    def stop(
        self,
        *,
        account_id: str,
        environment_id: str,
        expected_revision: int,
        task_id: str,
    ) -> int:
        aggregate = self._require(account_id, environment_id, include_deleted=True)
        if aggregate.binding.status == "deleted":
            return int(aggregate.binding.revision)
        if aggregate.browser.status == "stopped":
            revision = int(aggregate.binding.revision)
            self._emit(account_id, environment_id, task_id, revision, "stopped")
            return revision
        self._require_revision(aggregate, expected_revision)
        self._stop_owned_browser(account_id, aggregate)
        self._repository.mark_stopped_for_archive(
            account_id=account_id,
            environment_id=environment_id,
        )
        revision = self._current_revision(account_id, environment_id)
        self._emit(account_id, environment_id, task_id, revision, "stopped")
        return revision

    def check(
        self,
        *,
        account_id: str,
        environment_id: str,
        expected_revision: int,
        task_id: str,
    ) -> int:
        aggregate = self._require(account_id, environment_id)
        self._require_revision(aggregate, expected_revision)
        if aggregate.browser.status != "running":
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_NOT_ELIGIBLE,
                "执行环境未运行，请先启动后再检查",
                status_code=409,
            )
        self._verify_ownership(account_id, aggregate)
        health = self._browser_runtime.health(
            process_id=aggregate.browser.process_id,
            debug_port=aggregate.browser.debug_port,
        )
        if not health.alive:
            log_id = f"log_{uuid4().hex}"
            self._repository.mark_checked(
                account_id=account_id,
                environment_id=environment_id,
                healthy=False,
                error_code=(
                    health.error_code
                    or ErrorCode.EXECUTION_ENVIRONMENT_NOT_ELIGIBLE.value
                ),
                error_log_id=log_id,
            )
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_NOT_ELIGIBLE,
                health.error_message or "执行环境检查失败，请重试",
                status_code=409,
                loggable=True,
            )
        revision = self._repository.mark_checked(
            account_id=account_id,
            environment_id=environment_id,
            healthy=True,
        )
        self._emit(account_id, environment_id, task_id, revision, "checked")
        return revision

    def delete(
        self,
        *,
        account_id: str,
        environment_id: str,
        expected_revision: int,
        task_id: str,
    ) -> int:
        aggregate = self._require(account_id, environment_id, include_deleted=True)
        if aggregate.binding.status == "deleted":
            return int(aggregate.binding.revision)
        self._require_revision(aggregate, expected_revision)
        if aggregate.browser.status != "stopped":
            self._stop_owned_browser(account_id, aggregate)
        revision = self._repository.mark_deleted(
            account_id=account_id,
            environment_id=environment_id,
        )
        self._emit(account_id, environment_id, task_id, revision, "deleted")
        return revision

    def _stop_owned_browser(
        self,
        account_id: str,
        aggregate: ExecutionEnvironmentAggregate,
    ) -> None:
        self._verify_ownership(account_id, aggregate)
        stopped = self._browser_runtime.stop(process_id=aggregate.browser.process_id)
        if stopped.alive:
            log_id = f"log_{uuid4().hex}"
            self._repository.mark_cleanup_failed(
                account_id=account_id,
                environment_id=aggregate.binding.id,
                error_code=ErrorCode.EXECUTION_ENVIRONMENT_PROVISION_FAILED.value,
                error_log_id=log_id,
                browser_orphaned=False,
            )
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_PROVISION_FAILED,
                "受控浏览器未能停止，请查看日志后重试",
                status_code=409,
                loggable=True,
            )

    def _verify_ownership(
        self,
        account_id: str,
        aggregate: ExecutionEnvironmentAggregate,
    ) -> None:
        browser = aggregate.browser
        if (
            browser.process_id is None
            or browser.debug_host is None
            or browser.debug_port is None
            or not browser.executable_path
            or not browser.runtime_evidence_json
        ):
            self._ownership_failure(account_id, aggregate, None)
        try:
            self._ownership.verify_existing(
                account_id=account_id,
                browser_instance_id=browser.id,
                profile_path=Path(browser.profile_path),
                process_id=browser.process_id,
                executable_path=browser.executable_path,
                debug_host=browser.debug_host,
                debug_port=browser.debug_port,
                runtime_evidence_json=browser.runtime_evidence_json,
            )
        except BrowserProcessOwnershipError as exc:
            self._ownership_failure(account_id, aggregate, exc)

    def _ownership_failure(
        self,
        account_id: str,
        aggregate: ExecutionEnvironmentAggregate,
        cause: Exception | None,
    ) -> None:
        log_id = f"log_{uuid4().hex}"
        self._repository.mark_cleanup_failed(
            account_id=account_id,
            environment_id=aggregate.binding.id,
            error_code=ErrorCode.BROWSER_PROCESS_OWNERSHIP_UNPROVEN.value,
            error_log_id=log_id,
            browser_orphaned=True,
        )
        error = DomainError(
            ErrorCode.BROWSER_PROCESS_OWNERSHIP_UNPROVEN,
            "无法证明浏览器属于当前执行环境，已停止自动控制",
            status_code=409,
            loggable=True,
        )
        if cause is None:
            raise error
        raise error from cause

    def _require(
        self,
        account_id: str,
        environment_id: str,
        *,
        include_deleted: bool = False,
    ) -> ExecutionEnvironmentAggregate:
        aggregate = (
            self._repository.get_owned_including_deleted(account_id, environment_id)
            if include_deleted
            else self._repository.get_owned(account_id, environment_id)
        )
        if aggregate is None:
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_NOT_FOUND,
                "执行环境不存在或不属于当前账号",
                status_code=404,
            )
        return aggregate

    @staticmethod
    def _require_revision(
        aggregate: ExecutionEnvironmentAggregate,
        expected_revision: int,
    ) -> None:
        if int(aggregate.binding.revision) != expected_revision:
            raise DomainError(
                ErrorCode.REVISION_CONFLICT,
                "执行环境状态已变化，请刷新后重试",
                status_code=409,
            )

    def _current_revision(self, account_id: str, environment_id: str) -> int:
        return int(self._require(account_id, environment_id).binding.revision)

    def _emit(
        self,
        account_id: str,
        environment_id: str,
        task_id: str,
        revision: int,
        action: str,
    ) -> None:
        self._events.append_standalone_idempotent(
            RuntimeEventDraft(
                event_id=f"execution-{action}-{task_id}",
                event_type=f"execution_environment.{action}",
                topic=f"account:{account_id}:execution-environments",
                account_id=account_id,
                aggregate_type="execution_environment",
                aggregate_id=environment_id,
                task_id=task_id,
                revision=revision,
                payload={
                    "invalidations": [
                        f"account:{account_id}:execution-environments",
                        f"account:{account_id}:tasks",
                        f"account:{account_id}:connection",
                    ]
                },
            )
        )
