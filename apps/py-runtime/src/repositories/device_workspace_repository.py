from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now
from domain.models.device_workspace import DeviceWorkspace, DeviceWorkspaceLog, ExecutionBinding


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
            workspace.last_used_at = checked_at
            workspace.updated_at = checked_at
            session.commit()
            return {
                "workspace_id": workspace.id,
                "status": workspace.status,
                "checked_at": checked_at,
            }

    # --- Bindings ---

    def list_bindings(
        self,
        *,
        account_id: str | None = None,
        browser_instance_id: str | None = None,
    ) -> list[ExecutionBinding]:
        with self._session_factory() as session:
            stmt = select(ExecutionBinding).order_by(ExecutionBinding.created_at.desc())
            if account_id is not None:
                stmt = stmt.where(ExecutionBinding.account_id == account_id)
            if browser_instance_id is not None:
                stmt = stmt.where(ExecutionBinding.device_workspace_id == browser_instance_id)
            items = session.scalars(stmt).all()
            session.expunge_all()
            return list(items)

    def get_binding(self, binding_id: str) -> ExecutionBinding | None:
        with self._session_factory() as session:
            binding = session.get(ExecutionBinding, binding_id)
            if binding is not None:
                session.expunge(binding)
            return binding

    def get_binding_for_account(self, account_id: str) -> ExecutionBinding | None:
        with self._session_factory() as session:
            binding = session.scalar(
                select(ExecutionBinding)
                .where(ExecutionBinding.account_id == account_id)
                .order_by(ExecutionBinding.updated_at.desc())
            )
            if binding is not None:
                session.expunge(binding)
            return binding

    def upsert_binding(
        self,
        *,
        account_id: str,
        browser_instance_id: str,
        status: str = "active",
        source: str | None = None,
        metadata_json: str | None = None,
    ) -> ExecutionBinding:
        with self._session_factory() as session:
            binding = session.scalar(
                select(ExecutionBinding).where(ExecutionBinding.account_id == account_id)
            )
            now = utc_now()
            if binding is None:
                binding = ExecutionBinding(
                    account_id=account_id,
                    device_workspace_id=browser_instance_id,
                    status=status,
                    source=source,
                    metadata_json=metadata_json,
                )
                session.add(binding)
            else:
                binding.device_workspace_id = browser_instance_id
                binding.status = status
                binding.source = source
                binding.metadata_json = metadata_json
                binding.updated_at = now
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

    # --- Logs ---

    def list_logs(self, workspace_id: str, *, since: str | None = None) -> list[DeviceWorkspaceLog]:
        with self._session_factory() as session:
            stmt = select(DeviceWorkspaceLog).where(DeviceWorkspaceLog.workspace_id == workspace_id)
            if since is not None:
                stmt = stmt.where(DeviceWorkspaceLog.created_at > since)
            logs = session.scalars(stmt.order_by(DeviceWorkspaceLog.created_at.asc())).all()
            session.expunge_all()
            return list(logs)

    def append_log(
        self,
        *,
        workspace_id: str,
        kind: str,
        level: str,
        message: str,
        context_json: str | None = None,
    ) -> DeviceWorkspaceLog:
        with self._session_factory() as session:
            log_entry = DeviceWorkspaceLog(
                workspace_id=workspace_id,
                kind=kind,
                level=level,
                message=message,
                context_json=context_json,
            )
            session.add(log_entry)
            session.commit()
            session.refresh(log_entry)
            session.expunge(log_entry)
            return log_entry
