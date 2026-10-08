from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from domain.models.knowledge import KnowledgeSnapshot
from errors import DomainError, ErrorCode
from services.knowledge.chunk_store import KnowledgeChunkStore

from .unit_of_work import AIExecutionTransaction


@dataclass(frozen=True, slots=True)
class FrozenKnowledgeContext:
    text: str
    manifest: tuple[dict[str, object], ...]
    manifest_hash: str
    input_units: int


class KnowledgeContextResolver:
    """按知识快照 v2 严格读取并校验账号派生文本块。"""

    def __init__(self, chunk_store: KnowledgeChunkStore) -> None:
        self._chunk_store = chunk_store

    def resolve(
        self,
        transaction: AIExecutionTransaction,
        *,
        account_id: str,
        snapshot: KnowledgeSnapshot,
        max_input_units: int,
    ) -> FrozenKnowledgeContext:
        if snapshot.account_id != account_id or max_input_units < 1:
            raise _context_unavailable()
        manifest = _load_manifest(snapshot.source_manifest_json)
        selected: list[dict[str, object]] = []
        sections: list[str] = []
        used_units = 0
        for entry in sorted(manifest, key=lambda item: str(item["sourceId"])):
            if used_units >= max_input_units:
                break
            if entry["accountId"] != account_id:
                raise _snapshot_not_ready()
            source_id = str(entry["sourceId"])
            source_revision = int(entry["sourceRevision"])
            source = transaction.knowledge.get_source(
                account_id,
                transaction.session,
                source_id=source_id,
            )
            if source is None:
                raise _snapshot_not_ready()
            chunks = transaction.knowledge_assets.list_chunks(
                account_id,
                transaction.session,
                source_id=source_id,
                source_revision=source_revision,
            )
            expected_chunks = entry["chunks"]
            if not isinstance(expected_chunks, list) or len(chunks) != len(
                expected_chunks
            ):
                raise _snapshot_not_ready()
            for row, expected in zip(chunks, expected_chunks, strict=True):
                if used_units >= max_input_units:
                    break
                _validate_chunk_evidence(row, expected)
                text = self._chunk_store.read_text(account_id, row.content_ref)
                if hashlib.sha256(text.encode("utf-8")).hexdigest() != row.content_hash:
                    raise _snapshot_not_ready()
                remaining = max_input_units - used_units
                included_units = min(max(1, int(row.token_count)), remaining)
                truncated = int(row.token_count) > remaining
                selected_text = (
                    text[: max(1, remaining * 4)] if truncated else text
                ).strip()
                if not selected_text:
                    continue
                sections.append(
                    f"[来源 {source_id} / 块 {int(row.ordinal)}]\n{selected_text}"
                )
                selected.append(
                    {
                        "sourceId": source_id,
                        "sourceRevision": source_revision,
                        "ordinal": int(row.ordinal),
                        "contentHash": row.content_hash,
                        "extractorVersion": int(row.extractor_version),
                        "includedUnits": included_units,
                        "truncated": truncated,
                    }
                )
                used_units += included_units
        if not sections:
            raise _context_unavailable()
        frozen = tuple(selected)
        return FrozenKnowledgeContext(
            text="\n\n".join(sections),
            manifest=frozen,
            manifest_hash=_sha256_json(list(frozen)),
            input_units=used_units,
        )


def _load_manifest(raw: str) -> list[dict[str, object]]:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise _snapshot_not_ready() from exc
    if not isinstance(value, list) or not value:
        raise _context_unavailable()
    normalized: list[dict[str, object]] = []
    source_ids: set[str] = set()
    for item in value:
        if (
            not isinstance(item, dict)
            or item.get("manifestVersion") != 2
            or not isinstance(item.get("accountId"), str)
            or not isinstance(item.get("sourceId"), str)
            or isinstance(item.get("sourceRevision"), bool)
            or not isinstance(item.get("sourceRevision"), int)
            or int(item["sourceRevision"]) < 1
            or not isinstance(item.get("chunks"), list)
        ):
            raise _context_unavailable()
        source_id = str(item["sourceId"])
        if source_id in source_ids:
            raise _snapshot_not_ready()
        source_ids.add(source_id)
        normalized.append(dict(item))
    return normalized


def _validate_chunk_evidence(row: object, expected: object) -> None:
    if not isinstance(expected, dict):
        raise _snapshot_not_ready()
    evidence = {
        "ordinal": int(getattr(row, "ordinal")),
        "contentHash": str(getattr(row, "content_hash")),
        "tokenCount": int(getattr(row, "token_count")),
        "extractorVersion": int(getattr(row, "extractor_version")),
    }
    if evidence != expected:
        raise _snapshot_not_ready()


def _sha256_json(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _context_unavailable() -> DomainError:
    return DomainError(
        ErrorCode.AI_KNOWLEDGE_TEXT_CONTEXT_UNAVAILABLE,
        "当前知识快照没有可用于文本生成的索引内容",
        status_code=409,
    )


def _snapshot_not_ready() -> DomainError:
    return DomainError(
        ErrorCode.AI_KNOWLEDGE_SNAPSHOT_NOT_READY,
        "知识快照与派生索引不一致，请重新建立快照",
        status_code=409,
        loggable=True,
    )


__all__ = ["FrozenKnowledgeContext", "KnowledgeContextResolver"]
