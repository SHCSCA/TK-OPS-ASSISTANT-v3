from __future__ import annotations

import asyncio
import json
import logging

from fastapi import HTTPException

from domain.models.device_workspace import DeviceWorkspace, DeviceWorkspaceLog, ExecutionBinding
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from schemas.accounts import AccountBindingDto, AccountBindingUpsertInput
from schemas.device_workspaces import (
    DeviceWorkspaceCreateInput,
    DeviceWorkspaceDto,
    DeviceWorkspaceLogDto,
    DeviceWorkspaceUpdateInput,
    HealthCheckResultDto,
)
from services.ws_manager import ws_manager

log = logging.getLogger(__name__)


class DeviceWorkspaceService:
    def __init__(self, repository: DeviceWorkspaceRepository) -> None:
        self._repository = repository

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
        try:
            workspace = self._repository.get_workspace(ws_id)
        except Exception as exc:
            log.exception("查询设备工作区详情失败")
            raise HTTPException(status_code=500, detail="查询设备工作区详情失败") from exc
        if workspace is None:
            raise HTTPException(status_code=404, detail="设备工作区不存在")
        return self._to_dto(workspace)

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
                    "updatedAt": workspace.updated_at.isoformat()
                    if hasattr(workspace.updated_at, "isoformat")
                    else str(workspace.updated_at),
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
        try:
            result = self._repository.health_check(ws_id)
            self._repository.append_log(
                workspace_id=ws_id,
                kind="health-check",
                level="info",
                message="工作区健康检查完成",
                context_json=json.dumps(
                    {"status": workspace.status, "workspaceId": workspace.id},
                    ensure_ascii=False,
                ),
            )
        except Exception as exc:
            log.exception("设备工作区健康检查失败")
            raise HTTPException(status_code=500, detail="设备工作区健康检查失败") from exc
        if result is None:
            raise HTTPException(status_code=404, detail="设备工作区不存在")
        return HealthCheckResultDto(**result)

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

    def _broadcast_event(self, event: dict[str, object]) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        asyncio.create_task(ws_manager.broadcast(event))

    def _to_dto(self, workspace: DeviceWorkspace) -> DeviceWorkspaceDto:
        return DeviceWorkspaceDto(
            id=workspace.id,
            name=workspace.name,
            root_path=workspace.root_path,
            status=workspace.status,
            error_count=workspace.error_count,
            last_used_at=workspace.last_used_at,
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
            createdAt=binding.created_at.isoformat() if hasattr(binding.created_at, "isoformat") else str(binding.created_at),
            updatedAt=binding.updated_at.isoformat() if hasattr(binding.updated_at, "isoformat") else str(binding.updated_at),
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
