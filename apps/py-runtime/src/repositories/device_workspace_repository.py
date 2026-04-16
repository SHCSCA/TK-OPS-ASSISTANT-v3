from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now
from domain.models.device_workspace import DeviceWorkspace


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
