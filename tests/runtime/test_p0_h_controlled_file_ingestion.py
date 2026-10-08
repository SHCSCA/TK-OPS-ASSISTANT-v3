from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import (
    RuntimeConfigurationError,
    _load_controlled_file_registry_path,
)
from domain.models.account_asset import (
    AccountAsset,
    KnowledgeIndexChunk,
    KnowledgeSourceAsset,
)
from domain.models.knowledge import KnowledgeSource
from domain.models.runtime_task import RuntimeTask
from errors import ErrorCode
from tests.runtime.p0c_account_integration_support import (
    create_account,
    mutation_headers,
    session,
    wait_account_task,
)


def test_controlled_registry_startup_path_is_fixed_under_app_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "runtime"
    data_dir.mkdir()
    expected = tmp_path / "controlled-files.v1.json"
    monkeypatch.setenv(
        "TK_OPS_CONTROLLED_FILE_REGISTRY_PATH",
        str(expected),
    )
    assert _load_controlled_file_registry_path(data_dir) == expected.resolve()

    monkeypatch.setenv(
        "TK_OPS_CONTROLLED_FILE_REGISTRY_PATH",
        str(tmp_path.parent / "outside-controlled-files.v1.json"),
    )
    with pytest.raises(RuntimeConfigurationError):
        _load_controlled_file_registry_path(data_dir)


def test_controlled_text_file_creates_asset_source_chunks_without_copy(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    client = licensed_runtime_client
    account_id, _ = create_account(
        client,
        name="受控知识账号",
        idempotency_key="idem_h3_controlled_account",
    )
    root = runtime_data_dir / "account-root"
    root.mkdir()
    source_file = root / "knowledge.md"
    source_file.write_text("# 账号定位\n真实受控知识内容。", encoding="utf-8")
    file_ref = "file_ref_0123456789abcdef0123456789abcdef"
    root_ref = "wr_0123456789abcdef0123456789abcdef"
    _write_registries(
        runtime_data_dir,
        account_id=account_id,
        root=root,
        source_file=source_file,
        file_ref=file_ref,
        root_ref=root_ref,
        kind="document",
        media_type="text/markdown; charset=utf-8",
    )

    created = _create_file_source(
        client,
        account_id=account_id,
        file_ref=file_ref,
        kind="document",
        title="账号定位知识",
        idempotency_key="idem_h3_create_text_file",
    )
    source_id = str(created["data"]["id"])

    with session(client) as database:
        asset = database.scalar(
            select(AccountAsset).where(
                AccountAsset.account_id == account_id,
                AccountAsset.controlled_file_ref == file_ref,
            )
        )
        link = database.get(
            KnowledgeSourceAsset,
            {"account_id": account_id, "knowledge_source_id": source_id},
        )
        assert asset is not None
        assert link is not None
        assert link.account_asset_id == asset.id
        assert asset.status == "pending"
        persisted_evidence = "|".join(
            (
                asset.authorization_basis,
                asset.controlled_file_ref,
                asset.display_name,
                asset.root_ref,
            )
        )
        assert str(root) not in persisted_evidence
        assert str(source_file) not in persisted_evidence

    submitted = client.post(
        f"/api/v1/accounts/{account_id}/knowledge/index-jobs",
        headers=mutation_headers(idempotency_key="idem_h3_index_text_file"),
        json={"sourceIds": [source_id]},
    )
    assert submitted.status_code == 202, submitted.text
    task_id = str(submitted.json()["data"]["taskId"])
    completed = wait_account_task(
        client,
        account_id=account_id,
        task_id=task_id,
    )
    assert completed["status"] == "completed"

    with session(client) as database:
        source = database.get(KnowledgeSource, source_id)
        task = database.get(RuntimeTask, task_id)
        asset = database.scalar(
            select(AccountAsset).where(
                AccountAsset.account_id == account_id,
                AccountAsset.controlled_file_ref == file_ref,
            )
        )
        chunks = database.scalars(
            select(KnowledgeIndexChunk).where(
                KnowledgeIndexChunk.account_id == account_id,
                KnowledgeIndexChunk.knowledge_source_id == source_id,
            )
        ).all()
        assert source is not None and source.status == "ready"
        assert asset is not None and asset.status == "ready"
        assert source.content_hash == hashlib.sha256(
            source_file.read_bytes()
        ).hexdigest()
        assert asset.content_hash == source.content_hash
        assert len(chunks) == 1
        assert chunks[0].extractor_version == 1
        assert chunks[0].content_ref.startswith(
            f"knowledge-chunk://{account_id}/{source_id}/"
        )
        assert task is not None
        snapshot = json.loads(task.config_snapshot_json)
        frozen = snapshot["payload"]["sourceManifests"][0]
        assert frozen["fileRef"] == file_ref
        assert frozen["rootRef"] == root_ref
        assert frozen["rootRevision"] == 1
        assert len(frozen["fingerprint"]) == 64
        serialized = task.config_snapshot_json
        assert str(root) not in serialized
        assert str(source_file) not in serialized
        assert "controlledFileRef" not in serialized

    derived_root = runtime_data_dir / "accounts" / account_id
    assert source_file.is_file()
    assert not tuple(derived_root.rglob(source_file.name))
    assert tuple(derived_root.rglob("*.txt"))


def test_changed_controlled_file_fails_task_and_marks_only_source_stale(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    client = licensed_runtime_client
    account_id, _ = create_account(
        client,
        name="文件变化账号",
        idempotency_key="idem_h3_changed_account",
    )
    root = runtime_data_dir / "changed-root"
    root.mkdir()
    source_file = root / "facts.txt"
    source_file.write_text("初始内容", encoding="utf-8")
    file_ref = "file_ref_11111111111111111111111111111111"
    root_ref = "wr_11111111111111111111111111111111"
    _write_registries(
        runtime_data_dir,
        account_id=account_id,
        root=root,
        source_file=source_file,
        file_ref=file_ref,
        root_ref=root_ref,
        kind="text",
        media_type="text/plain; charset=utf-8",
    )
    created = _create_file_source(
        client,
        account_id=account_id,
        file_ref=file_ref,
        kind="text",
        title="会变化的知识",
        idempotency_key="idem_h3_changed_source",
    )
    source_id = str(created["data"]["id"])
    source_file.write_text("授权后发生变化的内容", encoding="utf-8")
    stat = source_file.stat()
    os.utime(
        source_file,
        ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000),
    )

    submitted = client.post(
        f"/api/v1/accounts/{account_id}/knowledge/index-jobs",
        headers=mutation_headers(idempotency_key="idem_h3_changed_index"),
        json={"sourceIds": [source_id]},
    )
    assert submitted.status_code == 202, submitted.text
    task = wait_account_task(
        client,
        account_id=account_id,
        task_id=str(submitted.json()["data"]["taskId"]),
    )
    assert task["status"] == "failed"
    assert task["errorCode"] == ErrorCode.CONTROLLED_FILE_CHANGED

    with session(client) as database:
        source = database.get(KnowledgeSource, source_id)
        asset = database.scalar(
            select(AccountAsset).where(
                AccountAsset.account_id == account_id,
                AccountAsset.controlled_file_ref == file_ref,
            )
        )
        chunks = database.scalars(
            select(KnowledgeIndexChunk).where(
                KnowledgeIndexChunk.account_id == account_id,
                KnowledgeIndexChunk.knowledge_source_id == source_id,
            )
        ).all()
        assert source is not None and source.status == "stale"
        assert source.error_code == ErrorCode.CONTROLLED_FILE_CHANGED
        assert asset is not None and asset.status == "stale"
        assert asset.error_code == ErrorCode.CONTROLLED_FILE_CHANGED
        assert chunks == []
    assert source_file.read_text(encoding="utf-8") == "授权后发生变化的内容"


def test_binary_controlled_file_is_metadata_only_and_cross_account_hidden(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    client = licensed_runtime_client
    account_a, _ = create_account(
        client,
        name="媒体知识 A",
        idempotency_key="idem_h3_media_a",
    )
    account_b, _ = create_account(
        client,
        name="媒体知识 B",
        idempotency_key="idem_h3_media_b",
    )
    root = runtime_data_dir / "media-root"
    root.mkdir()
    source_file = root / "cover.png"
    source_file.write_bytes(b"\x89PNG\r\n\x1a\ncontrolled-media")
    file_ref = "file_ref_22222222222222222222222222222222"
    root_ref = "wr_22222222222222222222222222222222"
    _write_registries(
        runtime_data_dir,
        account_id=account_a,
        root=root,
        source_file=source_file,
        file_ref=file_ref,
        root_ref=root_ref,
        kind="image",
        media_type="image/png",
    )
    cross = client.post(
        f"/api/v1/accounts/{account_b}/knowledge/sources",
        headers=mutation_headers(idempotency_key="idem_h3_cross_account"),
        json={
            "kind": "image",
            "sourceMode": "file",
            "controlledFileRef": file_ref,
            "title": "不得越权",
        },
    )
    assert cross.status_code == 404
    assert cross.json()["error_code"] == ErrorCode.CONTROLLED_FILE_REF_INVALID

    created = _create_file_source(
        client,
        account_id=account_a,
        file_ref=file_ref,
        kind="image",
        title="封面图片",
        idempotency_key="idem_h3_media_source",
    )
    source_id = str(created["data"]["id"])
    submitted = client.post(
        f"/api/v1/accounts/{account_a}/knowledge/index-jobs",
        headers=mutation_headers(idempotency_key="idem_h3_media_index"),
        json={"sourceIds": [source_id]},
    )
    completed = wait_account_task(
        client,
        account_id=account_a,
        task_id=str(submitted.json()["data"]["taskId"]),
    )
    assert completed["status"] == "completed"
    with session(client) as database:
        asset = database.scalar(
            select(AccountAsset).where(
                AccountAsset.account_id == account_a,
                AccountAsset.controlled_file_ref == file_ref,
            )
        )
        chunks = database.scalars(
            select(KnowledgeIndexChunk).where(
                KnowledgeIndexChunk.account_id == account_a,
                KnowledgeIndexChunk.knowledge_source_id == source_id,
            )
        ).all()
        assert asset is not None and asset.status == "metadata_only"
        assert chunks == []


def _create_file_source(
    client: TestClient,
    *,
    account_id: str,
    file_ref: str,
    kind: str,
    title: str,
    idempotency_key: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/accounts/{account_id}/knowledge/sources",
        headers=mutation_headers(idempotency_key=idempotency_key),
        json={
            "kind": kind,
            "sourceMode": "file",
            "controlledFileRef": file_ref,
            "title": title,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _write_registries(
    runtime_data_dir: Path,
    *,
    account_id: str,
    root: Path,
    source_file: Path,
    file_ref: str,
    root_ref: str,
    kind: str,
    media_type: str,
) -> None:
    root = root.resolve()
    source_file = source_file.resolve()
    relative_path = source_file.relative_to(root).as_posix()
    stat = source_file.stat()
    mtime = stat.st_mtime_ns // 1_000_000
    identity = hashlib.sha256(
        f"{root_ref}\0{relative_path}".encode("utf-8")
    ).hexdigest()
    workspace_registry = {
        "schemaVersion": 1,
        "revision": 1,
        "roots": [
            {
                "accountId": account_id,
                "canonicalPath": str(root),
                "createdAt": "2026-08-09T00:00:00Z",
                "displayName": root.name,
                "revision": 1,
                "rootRef": root_ref,
                "status": "active",
                "updatedAt": "2026-08-09T00:00:00Z",
            }
        ],
    }
    controlled_registry = {
        "schemaVersion": 1,
        "revision": 1,
        "files": [
            {
                "accountId": account_id,
                "canonicalPath": str(source_file),
                "fileIdentity": identity,
                "fileRef": file_ref,
                "kind": kind,
                "mediaType": media_type,
                "mtime": mtime,
                "relativePath": relative_path,
                "revision": 1,
                "rootRef": root_ref,
                "rootRevision": 1,
                "size": stat.st_size,
                "status": "active",
            }
        ],
    }
    (runtime_data_dir / "workspace-roots.v1.json").write_text(
        json.dumps(workspace_registry, ensure_ascii=False),
        encoding="utf-8",
    )
    (runtime_data_dir / "controlled-files.v1.json").write_text(
        json.dumps(controlled_registry, ensure_ascii=False),
        encoding="utf-8",
    )
