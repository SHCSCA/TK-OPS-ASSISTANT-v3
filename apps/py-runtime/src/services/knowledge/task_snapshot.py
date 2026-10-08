from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from services.knowledge.index_types import KnowledgeIndexSourceManifest
from services.tasks.errors import task_snapshot_invalid
from services.tasks.types import JsonValue

_FILE_REF = re.compile(r"^file_ref_[A-Za-z0-9_-]{8,128}$")
_ROOT_REF = re.compile(r"^wr_[0-9a-f]{32}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")


def parse_source_manifests(
    raw: JsonValue | None,
) -> tuple[KnowledgeIndexSourceManifest, ...]:
    if not isinstance(raw, list) or not raw or len(raw) > 10_000:
        raise task_snapshot_invalid("知识索引任务来源快照无效")
    manifests = tuple(_parse_manifest(item) for item in raw)
    source_ids = [item.source_id for item in manifests]
    if len(source_ids) != len(set(source_ids)):
        raise task_snapshot_invalid("知识索引任务来源快照包含重复项")
    return manifests


def _parse_manifest(value: JsonValue) -> KnowledgeIndexSourceManifest:
    if not isinstance(value, Mapping):
        raise task_snapshot_invalid("知识索引任务来源快照结构无效")
    source_mode = value.get("sourceMode")
    expected_keys = (
        {
            "sourceId",
            "sourceRevision",
            "sourceMode",
            "fileRef",
            "rootRef",
            "rootRevision",
            "fileRevision",
            "fingerprint",
        }
        if source_mode == "file"
        else {"sourceId", "sourceRevision", "sourceMode"}
    )
    if set(value) != expected_keys:
        raise task_snapshot_invalid("知识索引任务来源快照字段无效")
    source_id = value.get("sourceId")
    source_revision = value.get("sourceRevision")
    if (
        not isinstance(source_id, str)
        or not source_id.strip()
        or isinstance(source_revision, bool)
        or not isinstance(source_revision, int)
        or source_revision < 1
        or source_mode not in {"file", "url", "text"}
    ):
        raise task_snapshot_invalid("知识索引任务来源快照值无效")
    if source_mode != "file":
        return KnowledgeIndexSourceManifest(
            source_id=source_id,
            source_revision=source_revision,
            source_mode=source_mode,
        )
    file_ref = value.get("fileRef")
    root_ref = value.get("rootRef")
    root_revision = value.get("rootRevision")
    file_revision = value.get("fileRevision")
    fingerprint = value.get("fingerprint")
    if (
        not isinstance(file_ref, str)
        or not _FILE_REF.fullmatch(file_ref)
        or not isinstance(root_ref, str)
        or not _ROOT_REF.fullmatch(root_ref)
        or isinstance(root_revision, bool)
        or not isinstance(root_revision, int)
        or root_revision < 1
        or isinstance(file_revision, bool)
        or not isinstance(file_revision, int)
        or file_revision < 1
        or not isinstance(fingerprint, str)
        or not _HASH.fullmatch(fingerprint)
    ):
        raise task_snapshot_invalid("受控文件任务快照值无效")
    return KnowledgeIndexSourceManifest(
        source_id=source_id,
        source_revision=source_revision,
        source_mode="file",
        file_ref=file_ref,
        root_ref=root_ref,
        root_revision=root_revision,
        file_revision=file_revision,
        fingerprint=fingerprint,
    )
