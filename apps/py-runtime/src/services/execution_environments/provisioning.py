from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from errors import DomainError, ErrorCode
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentV1Repository,
)
from services.browser_runtime import (
    BrowserLaunchResult,
    BrowserRuntime,
    BrowserRuntimeError,
)
from services.events import RuntimeEventDraft, RuntimeEventService
from services.execution_environments.browser_process import (
    BrowserProcessOwnershipError,
    BrowserOwnershipEvidence,
    BrowserProcessOwnershipService,
)
from services.execution_environments.workspace_root_resolver import (
    WorkspaceRootResolutionError,
    WorkspaceRootResolver,
)

log = logging.getLogger(__name__)

_WORKSPACE_DIRECTORIES = (
    "assets",
    "outputs",
    "tasks",
    "cache",
    ".tk-ops",
    "browser-profile",
)


class ExecutionEnvironmentProvisioner:
    def __init__(
        self,
        *,
        repository: ExecutionEnvironmentV1Repository,
        root_resolver: WorkspaceRootResolver,
        browser_runtime: BrowserRuntime,
        ownership_service: BrowserProcessOwnershipService,
        event_service: RuntimeEventService,
    ) -> None:
        self._repository = repository
        self._root_resolver = root_resolver
        self._browser_runtime = browser_runtime
        self._ownership_service = ownership_service
        self._events = event_service

    def provision(
        self,
        *,
        account_id: str,
        environment_id: str,
        root_ref: str,
        activate_when_ready: bool,
        task_id: str,
        event_type: str = "execution_environment.created",
    ) -> int:
        launch: BrowserLaunchResult | None = None
        ownership_evidence: BrowserOwnershipEvidence | None = None
        profile_path: Path | None = None
        browser_instance_id: str | None = None
        log_id = f"log_{uuid4().hex}"
        try:
            aggregate = self._repository.get_owned(account_id, environment_id)
            if aggregate is None:
                raise DomainError(
                    ErrorCode.EXECUTION_ENVIRONMENT_NOT_FOUND,
                    "执行环境不存在或不属于当前账号",
                    status_code=404,
                )
            browser_instance_id = aggregate.browser.id
            if aggregate.workspace.root_ref != root_ref:
                raise DomainError(
                    ErrorCode.EXECUTION_ENVIRONMENT_INVALID,
                    "执行环境的工作目录引用已变化，请重新创建任务",
                    status_code=409,
                )
            resolution = self._root_resolver.resolve(
                account_id=account_id,
                root_ref=root_ref,
            )
            root = resolution.path
            if Path(aggregate.workspace.root_path).resolve(strict=True) != root:
                raise DomainError(
                    ErrorCode.EXECUTION_ENVIRONMENT_INVALID,
                    "执行环境工作目录与授权引用不一致",
                    status_code=409,
                )
            _create_workspace_structure(root)
            profile_path = root / "browser-profile"
            nonce = self._ownership_service.create_marker(
                account_id=account_id,
                browser_instance_id=aggregate.browser.id,
                profile_path=profile_path,
            )
            launch = self._browser_runtime.launch(profile_path=profile_path)
            ownership_evidence = self._ownership_service.verify_launch(
                account_id=account_id,
                browser_instance_id=aggregate.browser.id,
                profile_path=profile_path,
                nonce=nonce,
                launch=launch,
            )
            revision = self._repository.mark_ready(
                account_id=account_id,
                environment_id=environment_id,
                activate=activate_when_ready,
                executable_path=launch.executable_path,
                process_id=launch.process_id,
                debug_host=launch.debug_host,
                debug_port=launch.debug_port,
                runtime_evidence_json=ownership_evidence.to_json(),
            )
            self._events.append_standalone(
                RuntimeEventDraft(
                    event_type=event_type,
                    topic=f"account:{account_id}:execution-environments",
                    account_id=account_id,
                    aggregate_type="execution_environment",
                    aggregate_id=environment_id,
                    task_id=task_id,
                    revision=revision,
                    payload={
                        "status": "active" if activate_when_ready else "inactive",
                        "invalidations": [
                            f"account:{account_id}:execution-environments",
                            f"account:{account_id}:tasks",
                        ],
                    },
                )
            )
            return revision
        except WorkspaceRootResolutionError as exc:
            self._mark_failure(
                account_id,
                environment_id,
                exc.error_code,
                log_id,
                self._compensate_browser(
                    account_id=account_id,
                    browser_instance_id=browser_instance_id,
                    profile_path=profile_path,
                    launch=launch,
                    evidence=ownership_evidence,
                ),
            )
            raise DomainError(
                ErrorCode(exc.error_code),
                str(exc),
                status_code=409,
                loggable=True,
            ) from exc
        except BrowserProcessOwnershipError as exc:
            self._mark_failure(
                account_id,
                environment_id,
                exc.error_code,
                log_id,
                True,
            )
            raise DomainError(
                ErrorCode.BROWSER_PROCESS_OWNERSHIP_UNPROVEN,
                str(exc),
                status_code=409,
                loggable=True,
            ) from exc
        except BrowserRuntimeError as exc:
            self._mark_failure(
                account_id,
                environment_id,
                "EXECUTION_ENVIRONMENT_PROVISION_FAILED",
                log_id,
                self._compensate_browser(
                    account_id=account_id,
                    browser_instance_id=browser_instance_id,
                    profile_path=profile_path,
                    launch=launch,
                    evidence=ownership_evidence,
                ),
            )
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_PROVISION_FAILED,
                exc.message,
                status_code=409,
                loggable=True,
            ) from exc
        except DomainError:
            self._mark_failure(
                account_id,
                environment_id,
                "EXECUTION_ENVIRONMENT_PROVISION_FAILED",
                log_id,
                self._compensate_browser(
                    account_id=account_id,
                    browser_instance_id=browser_instance_id,
                    profile_path=profile_path,
                    launch=launch,
                    evidence=ownership_evidence,
                ),
            )
            raise
        except Exception as exc:
            log.exception(
                "执行环境创建任务失败",
                extra={
                    "account_id": account_id,
                    "environment_id": environment_id,
                    "log_id": log_id,
                },
            )
            self._mark_failure(
                account_id,
                environment_id,
                "EXECUTION_ENVIRONMENT_PROVISION_FAILED",
                log_id,
                self._compensate_browser(
                    account_id=account_id,
                    browser_instance_id=browser_instance_id,
                    profile_path=profile_path,
                    launch=launch,
                    evidence=ownership_evidence,
                ),
            )
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_PROVISION_FAILED,
                "执行环境创建失败，请查看日志后重试",
                status_code=500,
                loggable=True,
            ) from exc

    def _compensate_browser(
        self,
        *,
        account_id: str,
        browser_instance_id: str | None,
        profile_path: Path | None,
        launch: BrowserLaunchResult | None,
        evidence: BrowserOwnershipEvidence | None,
    ) -> bool:
        if launch is None:
            return False
        if profile_path is None or evidence is None or browser_instance_id is None:
            return True
        try:
            self._ownership_service.verify_existing(
                account_id=account_id,
                browser_instance_id=browser_instance_id,
                profile_path=profile_path,
                process_id=launch.process_id,
                executable_path=launch.executable_path,
                debug_host=launch.debug_host,
                debug_port=launch.debug_port,
                runtime_evidence_json=evidence.to_json(),
            )
            result = self._browser_runtime.stop(process_id=launch.process_id)
            if result.alive:
                log.error(
                    "执行环境失败补偿后浏览器仍在运行",
                    extra={"browser_instance_id": browser_instance_id},
                )
                return True
            return False
        except Exception:
            log.exception(
                "执行环境失败补偿无法证明或停止浏览器进程",
                extra={"browser_instance_id": browser_instance_id},
            )
            return True

    def _mark_failure(
        self,
        account_id: str,
        environment_id: str,
        error_code: str,
        log_id: str,
        browser_orphaned: bool,
    ) -> None:
        try:
            self._repository.mark_failed(
                account_id=account_id,
                environment_id=environment_id,
                error_code=error_code,
                error_log_id=log_id,
                browser_orphaned=browser_orphaned,
            )
        except Exception:
            log.exception(
                "记录执行环境创建失败状态时发生异常",
                extra={
                    "account_id": account_id,
                    "environment_id": environment_id,
                    "log_id": log_id,
                },
            )


def _create_workspace_structure(root: Path) -> None:
    canonical_root = root.resolve(strict=True)
    for relative in _WORKSPACE_DIRECTORIES:
        candidate = root / relative
        candidate.mkdir(parents=True, exist_ok=True)
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(canonical_root):
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_INVALID,
                "工作目录包含越界重解析点，已停止创建",
                status_code=409,
            )
