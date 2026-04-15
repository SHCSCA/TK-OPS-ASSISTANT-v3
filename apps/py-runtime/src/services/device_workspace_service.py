from __future__ import annotations

import logging

from fastapi import HTTPException

from domain.models.device_workspace import DeviceWorkspace
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from schemas.device_workspaces import (
    DeviceWorkspaceCreateInput,
    DeviceWorkspaceDto,
    DeviceWorkspaceUpdateInput,
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
