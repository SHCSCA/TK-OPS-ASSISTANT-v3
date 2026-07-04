from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from common.time import utc_now
from common.http_errors import RuntimeHTTPException
from domain.models.device_workspace import BrowserInstance, DeviceWorkspace, DeviceWorkspaceLog, ExecutionBinding
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from schemas.accounts import AccountBindingDto, AccountBindingUpsertInput
from schemas.device_workspaces import (
    BrowserInstanceDto,
    BrowserInstanceWriteResultDto,
    DeviceWorkspaceBindingSummaryDto,
    DeviceWorkspaceCreateInput,
    DeviceWorkspaceDto,
    DeviceWorkspaceEnvironmentStatusDto,
    DeviceWorkspaceHealthSummaryDto,
    DeviceWorkspaceLogDto,
    DeviceWorkspaceUpdateInput,
    HealthCheckResultDto,
)
from services.browser_runtime import (
    BrowserLaunchResult,
    BrowserRuntime,
    BrowserRuntimeError,
    BrowserRuntimeHealth,
    LocalBrowserRuntime,
)
from services.ws_manager import ws_manager

log = logging.getLogger(__name__)


class DeviceWorkspaceService:
    def __init__(
        self,
        repository: DeviceWorkspaceRepository,
        *,
        browser_runtime: BrowserRuntime | None = None,
    ) -> None:
        self._repository = repository
        self._browser_runtime = browser_runtime or LocalBrowserRuntime()

    def list_workspaces(self) -> list[DeviceWorkspaceDto]:
        try:
            workspaces = self._repository.list_workspaces()
        except Exception as exc:
            log.exception("查询设备工作区列表失败")
            raise HTTPException(status_code=500, detail="查询设备工作区列表失败") from exc
        return [self._to_dto(item) for item in workspaces]

    def create_workspace(self, payload: DeviceWorkspaceCreateInput) -> DeviceWorkspaceDto:
        try:
            workspace = self._repository.create_workspace(
                payload.name.strip(),
                payload.root_path.strip(),
            )
        except Exception as exc:
            log.exception("创建设备工作区失败")
            raise HTTPException(status_code=500, detail="创建设备工作区失败") from exc
        return self._to_dto(workspace)

    def get_workspace(self, ws_id: str) -> DeviceWorkspaceDto:
        return self._to_dto(self._get_workspace_model(ws_id))

    def update_workspace(
        self,
        ws_id: str,
        payload: DeviceWorkspaceUpdateInput,
    ) -> DeviceWorkspaceDto:
        current = self._get_workspace_model(ws_id)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and isinstance(changes["name"], str):
            changes["name"] = changes["name"].strip()
        if "root_path" in changes and isinstance(changes["root_path"], str):
            changes["root_path"] = changes["root_path"].strip()
        try:
            workspace = self._repository.update_workspace(ws_id, **changes)
        except Exception as exc:
            log.exception("更新设备工作区失败")
            raise HTTPException(status_code=500, detail="更新设备工作区失败") from exc
        if workspace is None:
            raise HTTPException(status_code=404, detail="设备工作区不存在")
        if "status" in changes and current.status != workspace.status:
            self._broadcast_event(
                {
                    "type": "device.status.changed",
                    "workspaceId": workspace.id,
                    "status": workspace.status,
                    "previousStatus": current.status,
                    "updatedAt": workspace.updated_at.isoformat(),
                }
            )
        return self._to_dto(workspace)

    def delete_workspace(self, ws_id: str) -> None:
        try:
            deleted = self._repository.delete_workspace(ws_id)
        except Exception as exc:
            log.exception("删除设备工作区失败")
            raise HTTPException(status_code=500, detail="删除设备工作区失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="设备工作区不存在")

    def health_check(self, ws_id: str) -> HealthCheckResultDto:
        workspace = self._get_workspace_model(ws_id)
        environment_status = self._build_environment_status(workspace)
        binding_summary = self._build_binding_summary(ws_id)
        checked_at = self._now()
        workspace_status = "ready" if environment_status.errorCode is None else "error"
        message = (
            "工作区健康检查通过。"
            if workspace_status == "ready"
            else "工作区健康检查未通过。"
        )
        try:
            workspace = self._repository.update_workspace(
                ws_id,
                status=workspace_status,
                last_used_at=checked_at,
            )
            self._repository.append_log(
                workspace_id=ws_id,
                kind="health-check",
                level="info" if workspace_status == "ready" else "error",
                message=message,
                context_json=json.dumps(
                    {
                        "status": workspace_status,
                        "workspaceId": ws_id,
                        "checkedAt": checked_at.isoformat(),
                        "errorCode": environment_status.errorCode,
                        "errorMessage": environment_status.errorMessage,
                        "nextAction": environment_status.nextAction,
                        "environmentStatus": environment_status.model_dump(mode="json"),
                        "bindingSummary": binding_summary.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                ),
            )
        except Exception as exc:
            log.exception("设备工作区健康检查失败")
            raise HTTPException(status_code=500, detail="设备工作区健康检查失败") from exc
        if workspace is None:
            raise HTTPException(status_code=404, detail="设备工作区不存在")
        return HealthCheckResultDto(
            workspace_id=ws_id,
            status=workspace_status,
            checked_at=checked_at,
            errorCode=environment_status.errorCode,
            errorMessage=environment_status.errorMessage,
            nextAction=environment_status.nextAction,
            environmentStatus=environment_status,
            bindingSummary=binding_summary,
        )

    def list_logs(self, ws_id: str, *, since: str | None = None) -> list[DeviceWorkspaceLogDto]:
        self._get_workspace_model(ws_id)
        try:
            logs = self._repository.list_logs(ws_id, since=since)
        except Exception as exc:
            log.exception("查询工作区日志失败")
            raise HTTPException(status_code=500, detail="查询工作区日志失败") from exc
        return [self._to_log_dto(item) for item in logs]

    def list_bindings(self) -> list[AccountBindingDto]:
        try:
            bindings = self._repository.list_bindings()
        except Exception as exc:
            log.exception("查询绑定列表失败")
            raise HTTPException(status_code=500, detail="查询绑定列表失败") from exc
        return [self._to_binding_dto(binding) for binding in bindings]

    def get_binding(self, binding_id: str) -> AccountBindingDto:
        try:
            binding = self._repository.get_binding(binding_id)
        except Exception as exc:
            log.exception("查询绑定失败")
            raise HTTPException(status_code=500, detail="查询绑定失败") from exc
        if binding is None:
            raise HTTPException(status_code=404, detail="绑定不存在")
        return self._to_binding_dto(binding)

    def upsert_binding(
        self,
        account_id: str,
        payload: AccountBindingUpsertInput,
    ) -> AccountBindingDto:
        self._require_workspace(payload.browserInstanceId)
        try:
            binding = self._repository.upsert_binding(
                account_id=account_id,
                browser_instance_id=payload.browserInstanceId,
                status=payload.status,
                source=payload.source,
                metadata_json=payload.metadataJson,
            )
        except Exception as exc:
            log.exception("更新绑定失败")
            raise HTTPException(status_code=500, detail="更新绑定失败") from exc
        return self._to_binding_dto(binding)

    def delete_binding(self, binding_id: str) -> dict[str, bool]:
        try:
            deleted = self._repository.delete_binding(binding_id)
        except Exception as exc:
            log.exception("删除绑定失败")
            raise HTTPException(status_code=500, detail="删除绑定失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="绑定不存在")
        return {"deleted": True}

    def list_browser_instances(self, workspace_id: str) -> list[BrowserInstanceDto]:
        self._get_workspace_model(workspace_id)
        try:
            items = self._repository.list_browser_instances(workspace_id)
        except Exception as exc:
            log.exception("查询浏览器实例列表失败")
            raise HTTPException(status_code=500, detail="查询浏览器实例列表失败") from exc
        return [self._to_browser_instance_dto(item) for item in items]

    def create_browser_instance(
        self,
        workspace_id: str,
        *,
        name: str,
        profile_path: str,
    ) -> BrowserInstanceDto:
        workspace = self._get_workspace_model(workspace_id)
        resolved_profile = self._resolve_profile_path(workspace, profile_path)
        try:
            resolved_profile.mkdir(parents=True, exist_ok=True)
            instance = self._repository.create_browser_instance(
                workspace_id=workspace_id,
                name=name.strip(),
                profile_path=str(resolved_profile),
            )
        except Exception as exc:
            log.exception("创建浏览器实例失败")
            raise HTTPException(status_code=500, detail="创建浏览器实例失败") from exc
        return self._to_browser_instance_dto(instance)

    def get_browser_instance(self, workspace_id: str, instance_id: str) -> BrowserInstanceDto:
        return self._to_browser_instance_dto(self._get_browser_instance_model(workspace_id, instance_id))

    def start_browser_instance(self, workspace_id: str, instance_id: str) -> BrowserInstanceWriteResultDto:
        instance = self._get_browser_instance_model(workspace_id, instance_id)
        profile_path = Path(instance.profile_path)
        if not profile_path.exists():
            updated = self._update_browser_instance_status(
                workspace_id,
                instance_id,
                status="error",
                error_code="browser_instance.profile_missing",
                error_message="浏览器实例的 profile 目录不存在。",
                last_checked_at=self._now(),
            )
            return self._to_browser_write_result(
                updated,
                operation="start",
                process_boundary_verified=False,
                process_summary=self._process_summary(
                    alive=False,
                    process_id=updated.process_id,
                    debug_port=updated.debug_port,
                ),
            )

        existing_health = self._browser_runtime.health(
            process_id=instance.process_id,
            debug_port=instance.debug_port,
        )
        if existing_health.alive:
            updated = self._update_browser_instance_status(
                workspace_id,
                instance_id,
                status="running",
                error_code=None,
                error_message=None,
                runtime_evidence_json=self._dump_runtime_evidence(
                    {
                        "processId": instance.process_id,
                        "debugPort": instance.debug_port,
                        "debugHost": instance.debug_host,
                        "devtoolsUrl": existing_health.devtools_url,
                        "metadata": existing_health.metadata,
                    }
                ),
                last_started_at=instance.last_started_at or self._now(),
            )
            return self._to_browser_write_result(
                updated,
                operation="start",
                process_boundary_verified=True,
                process_summary=self._process_summary(
                    alive=True,
                    process_id=updated.process_id,
                    debug_port=updated.debug_port,
                ),
            )

        try:
            launch_result = self._browser_runtime.launch(profile_path=profile_path)
        except BrowserRuntimeError as exc:
            updated = self._update_browser_instance_status(
                workspace_id,
                instance_id,
                status="error",
                error_code=exc.error_code,
                error_message=exc.message,
                process_id=None,
                debug_port=None,
                debug_host=None,
                runtime_mode="metadata_only",
                runtime_evidence_json=self._dump_runtime_evidence(
                    {
                        "profilePath": str(profile_path),
                        "errorCode": exc.error_code,
                        "errorMessage": exc.message,
                    }
                ),
                last_checked_at=self._now(),
            )
            self._append_browser_log(
                workspace_id=workspace_id,
                kind="browser-start",
                level="error",
                message=exc.message,
                context={
                    "browserInstanceId": instance_id,
                    "errorCode": exc.error_code,
                },
            )
            return self._to_browser_write_result(
                updated,
                operation="start",
                process_boundary_verified=False,
                process_summary=self._process_summary(alive=False),
            )

        instance = self._update_browser_instance_status(
            workspace_id,
            instance_id,
            status="running",
            error_code=None,
            error_message=None,
            process_id=launch_result.process_id,
            debug_port=launch_result.debug_port,
            debug_host=launch_result.debug_host,
            runtime_mode="local_process",
            executable_path=launch_result.executable_path,
            runtime_evidence_json=self._dump_launch_evidence(launch_result),
            last_started_at=self._now(),
        )
        self._append_browser_log(
            workspace_id=workspace_id,
            kind="browser-start",
            level="info",
            message="浏览器实例已启动真实本地进程。",
            context={
                "browserInstanceId": instance_id,
                "processId": launch_result.process_id,
                "debugPort": launch_result.debug_port,
            },
        )
        return self._to_browser_write_result(
            instance,
            operation="start",
            process_boundary_verified=True,
            process_summary=self._process_summary(
                alive=True,
                process_id=launch_result.process_id,
                debug_port=launch_result.debug_port,
            ),
        )

    def stop_browser_instance(self, workspace_id: str, instance_id: str) -> BrowserInstanceWriteResultDto:
        current = self._get_browser_instance_model(workspace_id, instance_id)
        stop_result = self._browser_runtime.stop(process_id=current.process_id)
        if stop_result.error_code:
            instance = self._update_browser_instance_status(
                workspace_id,
                instance_id,
                status="error",
                error_code=stop_result.error_code,
                error_message=stop_result.error_message,
                last_checked_at=self._now(),
            )
            return self._to_browser_write_result(
                instance,
                operation="stop",
                process_boundary_verified=False,
                process_summary=self._process_summary(
                    alive=stop_result.alive,
                    process_id=current.process_id,
                    debug_port=current.debug_port,
                ),
            )
        instance = self._update_browser_instance_status(
            workspace_id,
            instance_id,
            status="stopped",
            error_code=None,
            error_message=None,
            process_id=None,
            debug_port=None,
            debug_host=None,
            runtime_evidence_json=self._dump_runtime_evidence(
                {
                    "stoppedProcessId": current.process_id,
                    "stoppedAt": self._now().isoformat(),
                }
            ),
            last_stopped_at=self._now(),
        )
        self._append_browser_log(
            workspace_id=workspace_id,
            kind="browser-stop",
            level="info",
            message="浏览器实例进程已停止。",
            context={
                "browserInstanceId": instance_id,
                "processId": current.process_id,
            },
        )
        return self._to_browser_write_result(
            instance,
            operation="stop",
            process_boundary_verified=not stop_result.alive,
            process_summary=self._process_summary(
                alive=stop_result.alive,
                process_id=current.process_id,
                debug_port=current.debug_port,
            ),
        )

    def health_check_browser_instance(
        self,
        workspace_id: str,
        instance_id: str,
    ) -> BrowserInstanceWriteResultDto:
        instance = self._get_browser_instance_model(workspace_id, instance_id)
        profile_path = Path(instance.profile_path)
        if not profile_path.exists():
            updated = self._update_browser_instance_status(
                workspace_id,
                instance_id,
                status="error",
                error_code="browser_instance.profile_missing",
                error_message="浏览器实例的 profile 目录不存在。",
                last_checked_at=self._now(),
            )
            return self._to_browser_write_result(
                updated,
                operation="health-check",
                process_boundary_verified=False,
                process_summary=self._process_summary(
                    alive=False,
                    process_id=updated.process_id,
                    debug_port=updated.debug_port,
                ),
            )

        health = self._browser_runtime.health(
            process_id=instance.process_id,
            debug_port=instance.debug_port,
        )
        if not health.alive:
            updated = self._update_browser_instance_status(
                workspace_id,
                instance_id,
                status="error",
                error_code=health.error_code or "browser_instance.process_missing",
                error_message=health.error_message or "浏览器进程不存在或已经退出。",
                runtime_evidence_json=self._dump_health_evidence(health),
                last_checked_at=self._now(),
            )
            return self._to_browser_write_result(
                updated,
                operation="health-check",
                process_boundary_verified=False,
                process_summary=self._process_summary(
                    alive=False,
                    process_id=instance.process_id,
                    debug_port=instance.debug_port,
                ),
            )

        updated = self._update_browser_instance_status(
            workspace_id,
            instance_id,
            status="ready",
            error_code=None,
            error_message=None,
            runtime_evidence_json=self._dump_health_evidence(health),
            last_checked_at=self._now(),
        )
        return self._to_browser_write_result(
            updated,
            operation="health-check",
            process_boundary_verified=True,
            process_summary=self._process_summary(
                alive=True,
                process_id=updated.process_id,
                debug_port=updated.debug_port,
            ),
        )

    def _get_workspace_model(self, ws_id: str) -> DeviceWorkspace:
        try:
            workspace = self._repository.get_workspace(ws_id)
        except Exception as exc:
            log.exception("查询设备工作区失败")
            raise HTTPException(status_code=500, detail="查询设备工作区失败") from exc
        if workspace is None:
            raise HTTPException(status_code=404, detail="设备工作区不存在")
        return workspace

    def _require_workspace(self, workspace_id: str) -> None:
        self._get_workspace_model(workspace_id)

    def _get_browser_instance_model(self, workspace_id: str, instance_id: str) -> BrowserInstance:
        self._get_workspace_model(workspace_id)
        try:
            instance = self._repository.get_browser_instance(workspace_id, instance_id)
        except Exception as exc:
            log.exception("查询浏览器实例失败")
            raise HTTPException(status_code=500, detail="查询浏览器实例失败") from exc
        if instance is None:
            raise HTTPException(status_code=404, detail="浏览器实例不存在")
        return instance

    def _update_browser_instance_status(
        self,
        workspace_id: str,
        instance_id: str,
        **changes: object,
    ) -> BrowserInstance:
        current = self._get_browser_instance_model(workspace_id, instance_id)
        try:
            instance = self._repository.update_browser_instance(workspace_id, instance_id, **changes)
        except Exception as exc:
            log.exception("更新浏览器实例失败")
            raise HTTPException(status_code=500, detail="更新浏览器实例失败") from exc
        if instance is None:
            raise HTTPException(status_code=404, detail="浏览器实例不存在")
        if current.status != instance.status:
            self._broadcast_event(
                {
                    "type": "browser-instance.status.changed",
                    "workspaceId": workspace_id,
                    "browserInstanceId": instance.id,
                    "status": instance.status,
                    "previousStatus": current.status,
                    "updatedAt": instance.updated_at.isoformat(),
                }
            )
        return instance

    def _resolve_profile_path(self, workspace: DeviceWorkspace, profile_path: str) -> Path:
        workspace_root = Path(workspace.root_path).resolve()
        candidate = Path(profile_path)
        if not candidate.is_absolute():
            candidate = workspace_root / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(workspace_root)
        except ValueError as exc:
            raise RuntimeHTTPException(
                status_code=400,
                detail="浏览器实例的 profile 目录必须落在工作区根目录内。",
                error_code="browser_instance.profile_outside_workspace",
            ) from exc
        return resolved

    def _broadcast_event(self, event: dict[str, object]) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        asyncio.create_task(ws_manager.broadcast(event))

    def _to_dto(self, workspace: DeviceWorkspace) -> DeviceWorkspaceDto:
        environment_status = self._build_environment_status(workspace)
        binding_summary = self._build_binding_summary(workspace.id)
        health_summary = self._build_health_summary(workspace.id, environment_status)
        return DeviceWorkspaceDto(
            id=workspace.id,
            name=workspace.name,
            root_path=workspace.root_path,
            status=workspace.status,
            error_count=workspace.error_count,
            last_used_at=workspace.last_used_at,
            environmentStatus=environment_status,
            bindingSummary=binding_summary,
            healthSummary=health_summary,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )

    def _to_log_dto(self, item: DeviceWorkspaceLog) -> DeviceWorkspaceLogDto:
        return DeviceWorkspaceLogDto(
            id=item.id,
            workspaceId=item.workspace_id,
            kind=item.kind,
            level=item.level,
            message=item.message,
            contextJson=item.context_json,
            createdAt=item.created_at,
        )

    def _to_binding_dto(self, binding: ExecutionBinding) -> AccountBindingDto:
        return AccountBindingDto(
            id=binding.id,
            accountId=binding.account_id,
            browserInstanceId=binding.device_workspace_id,
            status=binding.status,
            source=binding.source,
            maskedMetadataJson=_mask_sensitive_json(binding.metadata_json),
            createdAt=binding.created_at.isoformat(),
            updatedAt=binding.updated_at.isoformat(),
        )

    def _to_browser_instance_dto(self, item: BrowserInstance) -> BrowserInstanceDto:
        return BrowserInstanceDto(
            id=item.id,
            workspaceId=item.workspace_id,
            name=item.name,
            profilePath=item.profile_path,
            status=item.status,
            processId=item.process_id,
            debugPort=item.debug_port,
            debugHost=item.debug_host,
            runtimeMode=item.runtime_mode or "metadata_only",
            launchSupported=self._browser_runtime.launch_supported(),
            runtimeEvidence=self._parse_runtime_evidence(item.runtime_evidence_json),
            lastCheckedAt=item.last_checked_at,
            lastStartedAt=item.last_started_at,
            lastStoppedAt=item.last_stopped_at,
            errorCode=item.error_code,
            errorMessage=item.error_message,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )

    def _to_browser_write_result(
        self,
        item: BrowserInstance,
        *,
        operation: str,
        process_boundary_verified: bool,
        process_summary: dict[str, object],
    ) -> BrowserInstanceWriteResultDto:
        updated_at = item.updated_at.isoformat()
        return BrowserInstanceWriteResultDto(
            saved=True,
            updatedAt=updated_at,
            versionOrRevision=updated_at,
            objectSummary={
                "workspaceId": item.workspace_id,
                "browserInstanceId": item.id,
                "name": item.name,
            },
            browserInstance=self._to_browser_instance_dto(item),
            operation=operation,
            processBoundaryVerified=process_boundary_verified,
            processSummary=process_summary,
        )

    def _dump_launch_evidence(self, launch_result: BrowserLaunchResult) -> str:
        return self._dump_runtime_evidence(
            {
                "processId": launch_result.process_id,
                "debugHost": launch_result.debug_host,
                "debugPort": launch_result.debug_port,
                "executablePath": launch_result.executable_path,
                "devtoolsUrl": launch_result.devtools_url,
                "metadata": launch_result.metadata,
            }
        )

    def _dump_health_evidence(self, health: BrowserRuntimeHealth) -> str:
        return self._dump_runtime_evidence(
            {
                "alive": health.alive,
                "processId": health.process_id,
                "debugPort": health.debug_port,
                "devtoolsUrl": health.devtools_url,
                "errorCode": health.error_code,
                "errorMessage": health.error_message,
                "metadata": health.metadata,
            }
        )

    def _dump_runtime_evidence(self, payload: dict[str, object]) -> str:
        return json.dumps(payload, ensure_ascii=False)

    def _parse_runtime_evidence(self, raw_value: str | None) -> dict[str, object] | None:
        if not raw_value:
            return None
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _process_summary(
        self,
        *,
        alive: bool,
        process_id: int | None = None,
        debug_port: int | None = None,
    ) -> dict[str, object]:
        return {
            "pid": process_id,
            "debugPort": debug_port,
            "alive": alive,
        }

    def _append_browser_log(
        self,
        *,
        workspace_id: str,
        kind: str,
        level: str,
        message: str,
        context: dict[str, Any],
    ) -> None:
        try:
            self._repository.append_log(
                workspace_id=workspace_id,
                kind=kind,
                level=level,
                message=message,
                context_json=json.dumps(context, ensure_ascii=False),
            )
        except Exception:
            log.exception("写入浏览器实例日志失败")

    def _now(self):
        return utc_now()

    def _build_environment_status(
        self,
        workspace: DeviceWorkspace,
    ) -> DeviceWorkspaceEnvironmentStatusDto:
        root_path = Path(workspace.root_path)
        root_exists = root_path.exists()
        is_directory = root_path.is_dir()
        browser_instances = self._repository.list_browser_instances(workspace.id)
        browser_count = len(browser_instances)
        running_count = sum(1 for item in browser_instances if item.status == "running")
        has_browser_error = any(item.status == "error" for item in browser_instances)

        if not root_exists:
            return DeviceWorkspaceEnvironmentStatusDto(
                status="missing_root",
                rootPathExists=False,
                isDirectory=False,
                browserInstanceCount=browser_count,
                runningBrowserInstanceCount=running_count,
                errorCode="workspace.root_path_missing",
                errorMessage="工作区根目录不存在，当前无法执行任务。",
                nextAction="请修复工作区路径，或重新创建工作区。",
            )
        if not is_directory:
            return DeviceWorkspaceEnvironmentStatusDto(
                status="invalid_root",
                rootPathExists=True,
                isDirectory=False,
                browserInstanceCount=browser_count,
                runningBrowserInstanceCount=running_count,
                errorCode="workspace.root_path_invalid",
                errorMessage="工作区根路径不是目录，当前无法执行任务。",
                nextAction="请将工作区指向真实本地目录。",
            )
        if has_browser_error:
            return DeviceWorkspaceEnvironmentStatusDto(
                status="degraded",
                rootPathExists=True,
                isDirectory=True,
                browserInstanceCount=browser_count,
                runningBrowserInstanceCount=running_count,
                errorCode="workspace.browser_instance_error",
                errorMessage="工作区下存在异常浏览器实例，执行环境处于降级状态。",
                nextAction="请先修复异常浏览器实例，再继续执行任务。",
            )
        if browser_count == 0:
            return DeviceWorkspaceEnvironmentStatusDto(
                status="ready_without_browser",
                rootPathExists=True,
                isDirectory=True,
                browserInstanceCount=0,
                runningBrowserInstanceCount=0,
                errorCode=None,
                errorMessage="工作区已就绪，但还没有浏览器实例。",
                nextAction="如需执行发布或自动化，请先创建浏览器实例。",
            )
        return DeviceWorkspaceEnvironmentStatusDto(
            status="ready",
            rootPathExists=True,
            isDirectory=True,
            browserInstanceCount=browser_count,
            runningBrowserInstanceCount=running_count,
            errorCode=None,
            errorMessage=None,
            nextAction=None,
        )

    def _build_binding_summary(self, workspace_id: str) -> DeviceWorkspaceBindingSummaryDto:
        bindings = self._repository.list_bindings(browser_instance_id=workspace_id)
        account_ids = sorted({item.account_id for item in bindings})
        active_bindings = sum(1 for item in bindings if item.status == "active")
        return DeviceWorkspaceBindingSummaryDto(
            totalBindings=len(bindings),
            activeBindings=active_bindings,
            accountIds=account_ids,
        )

    def _build_health_summary(
        self,
        workspace_id: str,
        environment_status: DeviceWorkspaceEnvironmentStatusDto,
    ) -> DeviceWorkspaceHealthSummaryDto:
        latest_log = self._repository.get_latest_log(workspace_id, kind="health-check")
        if latest_log is None:
            return DeviceWorkspaceHealthSummaryDto(
                status="unknown",
                checkedAt=None,
                errorCode=environment_status.errorCode,
                errorMessage="尚未执行健康检查。",
                nextAction="请先执行一次健康检查。",
            )

        parsed_context: dict[str, object] = {}
        if latest_log.context_json:
            try:
                payload = json.loads(latest_log.context_json)
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict):
                parsed_context = payload

        return DeviceWorkspaceHealthSummaryDto(
            status=str(parsed_context.get("status") or "unknown"),
            checkedAt=latest_log.created_at,
            errorCode=_optional_text(parsed_context.get("errorCode")),
            errorMessage=_optional_text(parsed_context.get("errorMessage")),
            nextAction=_optional_text(parsed_context.get("nextAction")),
        )


def _mask_sensitive_json(metadata_json: str | None) -> str | None:
    if metadata_json is None:
        return None
    try:
        parsed = json.loads(metadata_json)
    except json.JSONDecodeError:
        return metadata_json
    return json.dumps(_mask_value(parsed), ensure_ascii=False)


def _mask_value(value: object) -> object:
    if isinstance(value, dict):
        masked: dict[str, object] = {}
        for key, item in value.items():
            lowered = key.lower()
            if any(token in lowered for token in ("cookie", "token", "secret", "password", "session")):
                masked[key] = "masked"
            else:
                masked[key] = _mask_value(item)
        return masked
    if isinstance(value, list):
        return [_mask_value(item) for item in value]
    return value


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
