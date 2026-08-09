from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from services.execution_environments.workspace_root_resolver import (
    WorkspaceRootResolutionError,
    WorkspaceRootResolver,
)

ROOT_REF = "wr_0123456789abcdef0123456789abcdef"


def test_resolver_enforces_account_scope_and_recovers_after_restart(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "account-workspace"
    workspace.mkdir()
    registry = tmp_path / "workspace-roots.v1.json"
    _write_registry(registry, workspace=workspace)

    resolved = WorkspaceRootResolver(registry).resolve(
        account_id="account-a",
        root_ref=ROOT_REF,
    )

    assert resolved.path == workspace.resolve()
    assert resolved.registry_revision == 1
    assert resolved.revision == 1
    restarted = WorkspaceRootResolver(registry).resolve(
        account_id="account-a",
        root_ref=ROOT_REF,
    )
    assert restarted == resolved

    with pytest.raises(WorkspaceRootResolutionError) as captured:
        WorkspaceRootResolver(registry).resolve(
            account_id="account-b",
            root_ref=ROOT_REF,
        )
    assert captured.value.error_code == "WORKSPACE_ROOT_NOT_FOUND"


def test_resolver_reloads_revision_and_rejects_revoked_or_expired_root(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "account-workspace"
    workspace.mkdir()
    registry = tmp_path / "workspace-roots.v1.json"
    _write_registry(registry, workspace=workspace)
    resolver = WorkspaceRootResolver(registry)
    assert resolver.resolve(account_id="account-a", root_ref=ROOT_REF).revision == 1

    _write_registry(
        registry,
        workspace=workspace,
        registry_revision=2,
        root_revision=2,
        status="revoked",
    )
    resolver.invalidate()
    with pytest.raises(WorkspaceRootResolutionError) as revoked:
        resolver.resolve(account_id="account-a", root_ref=ROOT_REF)
    assert revoked.value.error_code == "WORKSPACE_ROOT_REVOKED"

    _write_registry(
        registry,
        workspace=workspace,
        registry_revision=3,
        root_revision=3,
    )
    workspace.rmdir()
    resolver.invalidate()
    with pytest.raises(WorkspaceRootResolutionError) as expired:
        resolver.resolve(account_id="account-a", root_ref=ROOT_REF)
    assert expired.value.error_code == "WORKSPACE_ROOT_EXPIRED"


def test_resolver_uses_last_verified_snapshot_when_registry_is_corrupted(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "account-workspace"
    workspace.mkdir()
    registry = tmp_path / "workspace-roots.v1.json"
    _write_registry(registry, workspace=workspace)
    resolver = WorkspaceRootResolver(registry)
    first = resolver.resolve(account_id="account-a", root_ref=ROOT_REF)

    registry.write_text("invalid-json", encoding="utf-8")
    os.utime(registry, None)
    recovered = resolver.resolve(account_id="account-a", root_ref=ROOT_REF)

    assert recovered == first


def test_resolver_reads_backup_when_primary_is_unavailable(tmp_path: Path) -> None:
    workspace = tmp_path / "account-workspace"
    workspace.mkdir()
    registry = tmp_path / "workspace-roots.v1.json"
    backup = tmp_path / "workspace-roots.v1.json.bak"
    _write_registry(backup, workspace=workspace)

    recovered = WorkspaceRootResolver(registry).resolve(
        account_id="account-a",
        root_ref=ROOT_REF,
    )

    assert recovered.path == workspace.resolve()


def _write_registry(
    path: Path,
    *,
    workspace: Path,
    registry_revision: int = 1,
    root_revision: int = 1,
    status: str = "active",
) -> None:
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "revision": registry_revision,
                "roots": [
                    {
                        "accountId": "account-a",
                        "canonicalPath": str(workspace.resolve()),
                        "createdAt": "2026-08-02T00:00:00Z",
                        "displayName": "account-workspace",
                        "revision": root_revision,
                        "rootRef": ROOT_REF,
                        "status": status,
                        "updatedAt": "2026-08-02T00:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
