from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, and_, select, update
from sqlalchemy.orm import Session

from domain.models.account_connection import AccountConnection
from domain.models.device_workspace import (
    BrowserInstance,
    DeviceWorkspace,
    ExecutionBinding,
)


@dataclass(frozen=True, slots=True)
class ExecutionBindingResources:
    execution_binding: ExecutionBinding
    device_workspace: DeviceWorkspace
    browser_instance: BrowserInstance


def workspace_query(
    account_id: str,
    workspace_id: str,
) -> Select[tuple[DeviceWorkspace]]:
    return select(DeviceWorkspace).where(
        DeviceWorkspace.account_id == account_id,
        DeviceWorkspace.id == workspace_id,
    )


def browser_query(
    account_id: str,
    browser_instance_id: str,
) -> Select[tuple[BrowserInstance]]:
    return (
        select(BrowserInstance)
        .join(
            DeviceWorkspace,
            BrowserInstance.workspace_id == DeviceWorkspace.id,
        )
        .where(
            BrowserInstance.account_id == account_id,
            BrowserInstance.id == browser_instance_id,
            DeviceWorkspace.account_id == account_id,
        )
    )


def browser_for_workspace_query(
    account_id: str,
    browser_instance_id: str,
    workspace_id: str,
) -> Select[tuple[BrowserInstance]]:
    return browser_query(account_id, browser_instance_id).where(
        BrowserInstance.workspace_id == workspace_id,
        DeviceWorkspace.id == workspace_id,
    )


def binding_evidence_query(
    account_id: str,
    binding_id: str,
) -> Select[tuple[ExecutionBinding, DeviceWorkspace, BrowserInstance]]:
    return (
        select(ExecutionBinding, DeviceWorkspace, BrowserInstance)
        .join(
            DeviceWorkspace,
            and_(
                DeviceWorkspace.id == ExecutionBinding.device_workspace_id,
                DeviceWorkspace.account_id == account_id,
            ),
        )
        .join(
            BrowserInstance,
            and_(
                BrowserInstance.id == ExecutionBinding.browser_instance_id,
                BrowserInstance.account_id == account_id,
                BrowserInstance.workspace_id == DeviceWorkspace.id,
            ),
        )
        .where(
            ExecutionBinding.account_id == account_id,
            ExecutionBinding.id == binding_id,
            ExecutionBinding.device_workspace_id == DeviceWorkspace.id,
            ExecutionBinding.browser_instance_id == BrowserInstance.id,
        )
    )


def binding_candidates_query(
    account_id: str,
) -> Select[tuple[ExecutionBinding, DeviceWorkspace, BrowserInstance]]:
    return (
        select(ExecutionBinding, DeviceWorkspace, BrowserInstance)
        .join(
            DeviceWorkspace,
            and_(
                DeviceWorkspace.id == ExecutionBinding.device_workspace_id,
                DeviceWorkspace.account_id == account_id,
            ),
        )
        .join(
            BrowserInstance,
            and_(
                BrowserInstance.id == ExecutionBinding.browser_instance_id,
                BrowserInstance.account_id == account_id,
                BrowserInstance.workspace_id == DeviceWorkspace.id,
            ),
        )
        .where(
            ExecutionBinding.account_id == account_id,
            ExecutionBinding.device_workspace_id == DeviceWorkspace.id,
            ExecutionBinding.browser_instance_id == BrowserInstance.id,
        )
        .order_by(
            ExecutionBinding.updated_at.desc(),
            ExecutionBinding.id.desc(),
        )
    )


def existing_binding_query(
    account_id: str,
    workspace_id: str,
    browser_instance_id: str,
) -> Select[tuple[ExecutionBinding]]:
    return (
        select(ExecutionBinding)
        .join(
            DeviceWorkspace,
            ExecutionBinding.device_workspace_id == DeviceWorkspace.id,
        )
        .join(
            BrowserInstance,
            ExecutionBinding.browser_instance_id == BrowserInstance.id,
        )
        .where(
            ExecutionBinding.account_id == account_id,
            ExecutionBinding.device_workspace_id == workspace_id,
            ExecutionBinding.browser_instance_id == browser_instance_id,
            DeviceWorkspace.account_id == account_id,
            DeviceWorkspace.id == workspace_id,
            BrowserInstance.account_id == account_id,
            BrowserInstance.id == browser_instance_id,
            BrowserInstance.workspace_id == workspace_id,
        )
        .order_by(
            ExecutionBinding.updated_at.desc(),
            ExecutionBinding.id.desc(),
        )
        .limit(1)
    )


def load_binding_evidence(
    session: Session,
    account_id: str,
    binding_id: str,
) -> ExecutionBindingResources | None:
    row = session.execute(
        binding_evidence_query(account_id, binding_id)
    ).one_or_none()
    if row is None:
        return None
    binding, workspace, browser = row
    return ExecutionBindingResources(
        execution_binding=binding,
        device_workspace=workspace,
        browser_instance=browser,
    )


def execute_connection_update(
    session: Session,
    account_id: str,
    connection_id: str,
    *,
    expected_revision: int,
    values: dict[str, object],
) -> AccountConnection | None:
    return session.scalars(
        update(AccountConnection)
        .where(
            AccountConnection.account_id == account_id,
            AccountConnection.id == connection_id,
            AccountConnection.revision == expected_revision,
        )
        .values(
            **values,
            revision=AccountConnection.revision + 1,
        )
        .returning(AccountConnection)
        .execution_options(
            synchronize_session=False,
            populate_existing=True,
        )
    ).one_or_none()
