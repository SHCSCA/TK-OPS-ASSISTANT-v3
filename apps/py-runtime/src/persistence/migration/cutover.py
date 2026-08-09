from __future__ import annotations

import hashlib
import json
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

log = logging.getLogger(__name__)

CUTOVER_JOURNAL_FORMAT_VERSION = 1
CUTOVER_JOURNAL_MAX_BYTES = 2_097_152
WRITE_GATE_OPENED_STAGE = "write_gate_opened"
_ALLOWED_STAGES = frozenset(
    {
        "migration_started",
        "pre_migration_validated",
        "backup_created",
        "migration_applied",
        "post_migration_validated",
        "migration_completed",
        "migration_failed",
        "pre_write_startup_failed",
        "pre_write_startup_restore_started",
        "pre_write_startup_restore_validated",
        "pre_write_startup_restore_failed",
        "restore_started",
        "restore_validated",
        "restore_failed",
        WRITE_GATE_OPENED_STAGE,
        "write_gate_closed",
        "write_gate_failed",
        "compatibility_evidence_written",
    }
)


class CutoverJournalError(RuntimeError):
    """迁移切换证据无法安全读取或持久化。"""


@dataclass(frozen=True, slots=True)
class CutoverEvidence:
    cutover_event_id: str
    sequence: int
    stage: str
    record_hash: str


class DurableCutoverJournal:
    """以哈希链和原子替换保存迁移、恢复与写门证据。"""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._lock = RLock()

    def begin(
        self,
        *,
        log_id: str,
        evidence: Mapping[str, object],
    ) -> CutoverEvidence:
        cutover_event_id = f"cut_{uuid4().hex}"
        return self.append(
            cutover_event_id=cutover_event_id,
            log_id=log_id,
            stage="migration_started",
            evidence=evidence,
            require_existing=False,
        )

    def append(
        self,
        *,
        cutover_event_id: str,
        log_id: str,
        stage: str,
        evidence: Mapping[str, object],
        require_existing: bool = True,
    ) -> CutoverEvidence:
        if stage not in _ALLOWED_STAGES:
            raise CutoverJournalError("迁移切换证据阶段无效")
        if not cutover_event_id.startswith("cut_") or len(cutover_event_id) > 96:
            raise CutoverJournalError("迁移切换事件标识无效")
        if not log_id.startswith("log_") or len(log_id) > 96:
            raise CutoverJournalError("迁移切换日志标识无效")
        safe_evidence = _normalize_evidence(evidence)

        with self._lock:
            events = self._load_events()
            existing = any(
                item["cutoverEventId"] == cutover_event_id for item in events
            )
            if require_existing and not existing:
                raise CutoverJournalError("迁移切换事件不存在")
            if not require_existing and existing:
                raise CutoverJournalError("迁移切换事件重复")
            sequence = len(events) + 1
            previous_hash = (
                None if not events else str(events[-1]["recordHash"])
            )
            body: dict[str, object] = {
                "sequence": sequence,
                "cutoverEventId": cutover_event_id,
                "logId": log_id,
                "stage": stage,
                "timestamp": datetime.now(UTC).isoformat(),
                "previousHash": previous_hash,
                "evidence": safe_evidence,
            }
            record_hash = _sha256(body)
            events.append({**body, "recordHash": record_hash})
            self._write_events(events)
            return CutoverEvidence(
                cutover_event_id=cutover_event_id,
                sequence=sequence,
                stage=stage,
                record_hash=record_hash,
            )

    def automatic_restore_allowed(self, cutover_event_id: str) -> bool:
        """写门一旦开放，该 cutover 只能走显式强恢复。"""

        with self._lock:
            return not any(
                item["cutoverEventId"] == cutover_event_id
                and item["stage"] == WRITE_GATE_OPENED_STAGE
                for item in self._load_events()
            )

    def _load_events(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        if self.path.is_symlink() or not self.path.is_file():
            raise CutoverJournalError("迁移切换证据必须是受控普通文件")
        try:
            if self.path.stat().st_size > CUTOVER_JOURNAL_MAX_BYTES:
                raise CutoverJournalError("迁移切换证据超过大小上限")
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except CutoverJournalError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CutoverJournalError("迁移切换证据无法读取") from exc
        if not isinstance(document, Mapping):
            raise CutoverJournalError("迁移切换证据结构无效")
        if set(document) != {"formatVersion", "events"}:
            raise CutoverJournalError("迁移切换证据字段无效")
        if document.get("formatVersion") != CUTOVER_JOURNAL_FORMAT_VERSION:
            raise CutoverJournalError("迁移切换证据版本不受支持")
        raw_events = document.get("events")
        if not isinstance(raw_events, list):
            raise CutoverJournalError("迁移切换事件列表无效")
        events = [_validate_event(item, index) for index, item in enumerate(raw_events)]
        _validate_hash_chain(events)
        return events

    def _write_events(self, events: list[dict[str, object]]) -> None:
        if self.path.is_symlink():
            raise CutoverJournalError("迁移切换证据不能写入符号链接")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "formatVersion": CUTOVER_JOURNAL_FORMAT_VERSION,
            "events": events,
        }
        payload = (
            json.dumps(
                document,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        temporary_path = self.path.with_name(
            f".{self.path.name}.{uuid4().hex}.tmp"
        )
        try:
            with temporary_path.open("x", encoding="utf-8", newline="\n") as file:
                file.write(payload)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
        except (OSError, UnicodeError) as exc:
            temporary_path.unlink(missing_ok=True)
            log.exception("迁移切换证据原子写入失败")
            raise CutoverJournalError("迁移切换证据无法保存") from exc


def _validate_event(value: object, index: int) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise CutoverJournalError("迁移切换事件结构无效")
    expected_keys = {
        "sequence",
        "cutoverEventId",
        "logId",
        "stage",
        "timestamp",
        "previousHash",
        "evidence",
        "recordHash",
    }
    if set(value) != expected_keys:
        raise CutoverJournalError("迁移切换事件字段无效")
    event = dict(value)
    if event.get("sequence") != index + 1:
        raise CutoverJournalError("迁移切换事件序号不连续")
    if not isinstance(event.get("cutoverEventId"), str):
        raise CutoverJournalError("迁移切换事件标识无效")
    if not isinstance(event.get("logId"), str):
        raise CutoverJournalError("迁移切换日志标识无效")
    if event.get("stage") not in _ALLOWED_STAGES:
        raise CutoverJournalError("迁移切换证据阶段无效")
    if not isinstance(event.get("timestamp"), str):
        raise CutoverJournalError("迁移切换证据时间无效")
    if not isinstance(event.get("evidence"), Mapping):
        raise CutoverJournalError("迁移切换证据内容无效")
    if not isinstance(event.get("recordHash"), str):
        raise CutoverJournalError("迁移切换证据摘要无效")
    return event


def _validate_hash_chain(events: list[dict[str, object]]) -> None:
    previous_hash: str | None = None
    for event in events:
        if event.get("previousHash") != previous_hash:
            raise CutoverJournalError("迁移切换证据哈希链断裂")
        body = {key: value for key, value in event.items() if key != "recordHash"}
        record_hash = str(event["recordHash"])
        if record_hash != _sha256(body):
            raise CutoverJournalError("迁移切换证据摘要校验失败")
        previous_hash = record_hash


def _normalize_evidence(value: Mapping[str, object]) -> dict[str, object]:
    try:
        normalized = json.loads(
            json.dumps(
                dict(value),
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    except (TypeError, ValueError) as exc:
        raise CutoverJournalError("迁移切换证据包含不可序列化内容") from exc
    if not isinstance(normalized, dict):
        raise CutoverJournalError("迁移切换证据内容无效")
    return normalized


def _sha256(value: Mapping[str, object]) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
