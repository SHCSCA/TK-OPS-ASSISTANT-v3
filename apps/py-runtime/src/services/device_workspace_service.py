from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import HTTPException

from domain.models.device_workspace import BrowserInstance, DeviceWorkspace, ExecutionBinding
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from schemas.device_workspaces import (
    BrowserInstanceCreateInput,
    BrowserInstanceDto,
    DeviceWorkspaceCreateInput,
    DeviceWorkspaceDto,
    DeviceWorkspaceUpdateInput,
    ExecutionBindingCreateInput,
    ExecutionBindingDto,
    HealthCheckResultDto,
)

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
        try:
            result = self._repository.health_check(ws_id)
        except Exception as exc:
            log.exception("设备工作区健康检查失败")
            raise HTTPException(status_code=500, detail="设备工作区健康检查失败") from exc
        if result is None:
            raise HTTPException(status_code=404, detail="设备工作区不存在")
        return HealthCheckResultDto(**result)

    def list_browser_instances(
        self,
        *,
        workspace_id: str | None = None,
    ) -> list[BrowserInstanceDto]:
        try:
            items = self._repository.list_browser_instances(workspace_id=workspace_id)
        except Exception as exc:
            log.exception("查询浏览器实例列表失败")
            raise HTTPException(status_code=500, detail="查询浏览器实例列表失败") from exc
        return [self._to_browser_instance_dto(item) for item in items]

    def create_browser_instance(self, payload: BrowserInstanceCreateInput) -> BrowserInstanceDto:
        self.get_workspace(payload.workspace_id)
        instance = BrowserInstance(
            id=str(uuid4()),
            workspace_id=payload.workspace_id,
            name=payload.name.strip(),
            profile_path=payload.profile_path.strip(),
            browser_type=payload.browser_type,
            status="stopped",
        )
        try:
            saved = self._repository.create_browser_instance(instance)
        except Exception as exc:
            log.exception("创建浏览器实例失败")
            raise HTTPException(status_code=500, detail="创建浏览器实例失败") from exc
        return self._to_browser_instance_dto(saved)

    def delete_browser_instance(self, instance_id: str) -> dict[str, bool]:
        try:
            instance = self._repository.get_browser_instance(instance_id)
        except Exception as exc:
            log.exception("查询浏览器实例失败")
            raise HTTPException(status_code=500, detail="查询浏览器实例失败") from exc
        if instance is None:
            raise HTTPException(status_code=404, detail="浏览器实例不存在")

        try:
            has_bindings = self._repository.browser_instance_has_bindings(instance_id)
        except Exception as exc:
            log.exception("查询浏览器实例绑定失败")
            raise HTTPException(status_code=500, detail="查询浏览器实例绑定失败") from exc
        if has_bindings:
            raise HTTPException(
                status_code=409,
                detail="该浏览器实例仍被绑定使用，请先解除绑定。",
            )

        try:
            deleted = self._repository.delete_browser_instance(instance_id)
        except Exception as exc:
            log.exception("删除浏览器实例失败")
            raise HTTPException(status_code=500, detail="删除浏览器实例失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="浏览器实例不存在")
        return {"deleted": True}

    def list_bindings(
        self,
        *,
        account_id: str | None = None,
        device_workspace_id: str | None = None,
    ) -> list[ExecutionBindingDto]:
        try:
            items = self._repository.list_bindings(
                account_id=account_id,
                device_workspace_id=device_workspace_id,
            )
        except Exception as exc:
            log.exception("查询执行绑定列表失败")
            raise HTTPException(status_code=500, detail="查询执行绑定列表失败") from exc
        return [self._to_binding_dto(item) for item in items]

    def create_binding(self, payload: ExecutionBindingCreateInput) -> ExecutionBindingDto:
        self.get_workspace(payload.device_workspace_id)
        if payload.browser_instance_id is not None:
            try:
                instance = self._repository.get_browser_instance(payload.browser_instance_id)
            except Exception as exc:
                log.exception("查询浏览器实例失败")
                raise HTTPException(status_code=500, detail="查询浏览器实例失败") from exc
            if instance is None:
                raise HTTPException(status_code=404, detail="浏览器实例不存在")
            if instance.workspace_id != payload.device_workspace_id:
                raise HTTPException(status_code=409, detail="浏览器实例不属于当前工作区")

        binding = ExecutionBinding(
            id=str(uuid4()),
            account_id=payload.account_id,
            device_workspace_id=payload.device_workspace_id,
            browser_instance_id=payload.browser_instance_id,
            status="active",
            source=payload.source,
            metadata_json=payload.metadata_json,
        )
        try:
            saved = self._repository.create_binding(binding)
        except Exception as exc:
            log.exception("创建执行绑定失败")
            raise HTTPException(status_code=500, detail="创建执行绑定失败") from exc
        return self._to_binding_dto(saved)

    def delete_binding(self, binding_id: str) -> dict[str, bool]:
        try:
            deleted = self._repository.delete_binding(binding_id)
        except Exception as exc:
            log.exception("删除执行绑定失败")
            raise HTTPException(status_code=500, detail="删除执行绑定失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="执行绑定不存在")
        return {"deleted": True}

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

    def _to_browser_instance_dto(self, instance: BrowserInstance) -> BrowserInstanceDto:
        return BrowserInstanceDto(
            id=instance.id,
            workspace_id=instance.workspace_id,
            name=instance.name,
            profile_path=instance.profile_path,
            browser_type=instance.browser_type,
            status=instance.status,
            last_seen_at=instance.last_seen_at,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
        )

    def _to_binding_dto(self, binding: ExecutionBinding) -> ExecutionBindingDto:
        return ExecutionBindingDto(
            id=binding.id,
            account_id=binding.account_id,
            device_workspace_id=binding.device_workspace_id,
            browser_instance_id=binding.browser_instance_id,
            status=binding.status,
            source=binding.source,
            metadata_json=binding.metadata_json,
            created_at=binding.created_at,
            updated_at=binding.updated_at,
        )
