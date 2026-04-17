from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now
from domain.models.device_workspace import BrowserInstance, DeviceWorkspace, ExecutionBinding


class DeviceWorkspaceRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_workspaces(self) -> list[DeviceWorkspace]:
        with self._session_factory() as session:
            items = session.scalars(
                select(DeviceWorkspace).order_by(DeviceWorkspace.created_at.desc())
            ).all()
            session.expunge_all()
            return list(items)

    def create_workspace(self, name: str, root_path: str) -> DeviceWorkspace:
        with self._session_factory() as session:
            workspace = DeviceWorkspace(name=name, root_path=root_path)
            session.add(workspace)
            session.commit()
            session.refresh(workspace)
            session.expunge(workspace)
            return workspace

    def get_workspace(self, ws_id: str) -> DeviceWorkspace | None:
        with self._session_factory() as session:
            workspace = session.get(DeviceWorkspace, ws_id)
            if workspace is not None:
                session.expunge(workspace)
            return workspace

    def update_workspace(self, ws_id: str, **kwargs: object) -> DeviceWorkspace | None:
        with self._session_factory() as session:
            workspace = session.get(DeviceWorkspace, ws_id)
            if workspace is None:
                return None
            for key, value in kwargs.items():
                setattr(workspace, key, value)
            workspace.updated_at = utc_now()
            session.commit()
            session.refresh(workspace)
            session.expunge(workspace)
            return workspace

    def delete_workspace(self, ws_id: str) -> bool:
        with self._session_factory() as session:
            workspace = session.get(DeviceWorkspace, ws_id)
            if workspace is None:
                return False
            session.delete(workspace)
            session.commit()
            return True

    def health_check(self, ws_id: str) -> dict[str, object] | None:
        with self._session_factory() as session:
            workspace = session.get(DeviceWorkspace, ws_id)
            if workspace is None:
                return None
            checked_at = utc_now()
            workspace.status = "online" if Path(workspace.root_path).is_dir() else "offline"
            workspace.last_used_at = checked_at
            workspace.updated_at = checked_at
            session.commit()
            return {
                "workspace_id": workspace.id,
                "status": workspace.status,
                "checked_at": checked_at,
            }

    def list_browser_instances(
        self,
        *,
        workspace_id: str | None = None,
    ) -> list[BrowserInstance]:
        with self._session_factory() as session:
            stmt = select(BrowserInstance).order_by(BrowserInstance.created_at.desc())
            if workspace_id is not None:
                stmt = stmt.where(BrowserInstance.workspace_id == workspace_id)
            items = session.scalars(stmt).all()
            session.expunge_all()
            return list(items)

    def create_browser_instance(self, instance: BrowserInstance) -> BrowserInstance:
        with self._session_factory() as session:
            session.add(instance)
            session.commit()
            session.refresh(instance)
            session.expunge(instance)
            return instance

    def get_browser_instance(self, instance_id: str) -> BrowserInstance | None:
        with self._session_factory() as session:
            instance = session.get(BrowserInstance, instance_id)
            if instance is not None:
                session.expunge(instance)
            return instance

    def browser_instance_has_bindings(self, instance_id: str) -> bool:
        with self._session_factory() as session:
            binding = session.scalar(
                select(ExecutionBinding).where(
                    ExecutionBinding.browser_instance_id == instance_id
                )
            )
            return binding is not None

    def delete_browser_instance(self, instance_id: str) -> bool:
        with self._session_factory() as session:
            instance = session.get(BrowserInstance, instance_id)
            if instance is None:
                return False
            session.delete(instance)
            session.commit()
            return True

    def list_bindings(
        self,
        *,
        account_id: str | None = None,
        device_workspace_id: str | None = None,
    ) -> list[ExecutionBinding]:
        with self._session_factory() as session:
            stmt = select(ExecutionBinding).order_by(ExecutionBinding.created_at.desc())
            if account_id is not None:
                stmt = stmt.where(ExecutionBinding.account_id == account_id)
            if device_workspace_id is not None:
                stmt = stmt.where(
                    ExecutionBinding.device_workspace_id == device_workspace_id
                )
            items = session.scalars(stmt).all()
            session.expunge_all()
            return list(items)

    def create_binding(self, binding: ExecutionBinding) -> ExecutionBinding:
        with self._session_factory() as session:
            session.add(binding)
            session.commit()
            session.refresh(binding)
            session.expunge(binding)
            return binding

    def delete_binding(self, binding_id: str) -> bool:
        with self._session_factory() as session:
            binding = session.get(ExecutionBinding, binding_id)
            if binding is None:
                return False
            session.delete(binding)
            session.commit()
            return True
