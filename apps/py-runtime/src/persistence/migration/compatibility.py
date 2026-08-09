from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

log = logging.getLogger(__name__)

RUNTIME_ARTIFACT_BUILD_ID_ENV = "TK_OPS_RUNTIME_ARTIFACT_BUILD_ID"
SCHEMA_COMPATIBILITY_FORMAT_VERSION = 1
P0_MINIMUM_SUPPORTED_SCHEMA_REVISION = "0017_p0_enforce_and_cutover"
_BUILD_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,160}$")


class SchemaCompatibilityEvidenceError(RuntimeError):
    """Schema 兼容证据无法安全生成。"""


@dataclass(frozen=True, slots=True)
class RuntimeSchemaReadRange:
    minimum_revision: str
    maximum_revision: str
    write_revision: str

    def to_dict(self) -> dict[str, str]:
        return {
            "schemaReadMin": self.minimum_revision,
            "schemaReadMax": self.maximum_revision,
            "schemaWrite": self.write_revision,
        }


@dataclass(frozen=True, slots=True)
class RuntimeCompatibilityEvidence:
    path: Path
    sha256: str
    artifact_build_id: str | None
    rollback_eligible: bool
    schema_range: RuntimeSchemaReadRange


def write_runtime_compatibility_evidence(
    path: Path,
    *,
    runtime_version: str,
    migration_log_id: str,
    cutover_event_id: str,
    database_fingerprint: str,
    target_revision: str,
    minimum_revision: str = P0_MINIMUM_SUPPORTED_SCHEMA_REVISION,
    artifact_build_id: str | None = None,
    require_artifact_build_id: bool = False,
) -> RuntimeCompatibilityEvidence:
    """生成供打包和回退验收消费的只读 Schema 范围证据。"""

    resolved_build_id = (
        artifact_build_id
        if artifact_build_id is not None
        else os.getenv(RUNTIME_ARTIFACT_BUILD_ID_ENV, "").strip()
    )
    if resolved_build_id and not _BUILD_ID_PATTERN.fullmatch(resolved_build_id):
        raise SchemaCompatibilityEvidenceError("Runtime 制品 build_id 格式无效")
    if require_artifact_build_id and not resolved_build_id:
        raise SchemaCompatibilityEvidenceError(
            "受管生产 Runtime 缺少 Tauri 注入的制品 build_id"
        )
    schema_range = RuntimeSchemaReadRange(
        minimum_revision=minimum_revision,
        maximum_revision=target_revision,
        write_revision=target_revision,
    )
    rollback_eligible = bool(resolved_build_id)
    body: dict[str, object] = {
        "formatVersion": SCHEMA_COMPATIBILITY_FORMAT_VERSION,
        "generatedAt": datetime.now(UTC).isoformat(),
        "runtimeVersion": runtime_version,
        "artifactBuildId": resolved_build_id or None,
        "artifactIdentityVerified": rollback_eligible,
        "rollbackEligible": rollback_eligible,
        **schema_range.to_dict(),
        "migrationLogId": migration_log_id,
        "cutoverEventId": cutover_event_id,
        "databaseFingerprint": database_fingerprint,
        "recoveryPolicy": "forward_compatible_runtime_only",
    }
    sha256 = _sha256(body)
    _atomic_write(path.resolve(), {**body, "sha256": sha256})
    return RuntimeCompatibilityEvidence(
        path=path.resolve(),
        sha256=sha256,
        artifact_build_id=resolved_build_id or None,
        rollback_eligible=rollback_eligible,
        schema_range=schema_range,
    )


def verify_runtime_compatibility_evidence(
    path: Path,
) -> RuntimeCompatibilityEvidence:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SchemaCompatibilityEvidenceError("Runtime Schema 兼容证据无法读取") from exc
    if not isinstance(document, Mapping):
        raise SchemaCompatibilityEvidenceError("Runtime Schema 兼容证据结构无效")
    sha256 = document.get("sha256")
    if not isinstance(sha256, str):
        raise SchemaCompatibilityEvidenceError("Runtime Schema 兼容证据摘要无效")
    body = {key: value for key, value in document.items() if key != "sha256"}
    if sha256 != _sha256(body):
        raise SchemaCompatibilityEvidenceError("Runtime Schema 兼容证据校验失败")
    if document.get("formatVersion") != SCHEMA_COMPATIBILITY_FORMAT_VERSION:
        raise SchemaCompatibilityEvidenceError("Runtime Schema 兼容证据版本不受支持")
    minimum = document.get("schemaReadMin")
    maximum = document.get("schemaReadMax")
    write_revision = document.get("schemaWrite")
    if not all(isinstance(item, str) and item for item in (minimum, maximum, write_revision)):
        raise SchemaCompatibilityEvidenceError("Runtime Schema 读写范围无效")
    build_id = document.get("artifactBuildId")
    identity_verified = document.get("artifactIdentityVerified")
    rollback_eligible = document.get("rollbackEligible")
    if build_id is not None and not isinstance(build_id, str):
        raise SchemaCompatibilityEvidenceError("Runtime 制品 build_id 无效")
    if not isinstance(rollback_eligible, bool):
        raise SchemaCompatibilityEvidenceError("Runtime 回退资格标识无效")
    if not isinstance(identity_verified, bool):
        raise SchemaCompatibilityEvidenceError("Runtime 制品身份校验标识无效")
    if rollback_eligible is not bool(build_id):
        raise SchemaCompatibilityEvidenceError("Runtime 回退资格与制品身份不一致")
    if identity_verified is not rollback_eligible:
        raise SchemaCompatibilityEvidenceError("Runtime 制品身份与回退资格不一致")
    return RuntimeCompatibilityEvidence(
        path=path.resolve(),
        sha256=sha256,
        artifact_build_id=build_id,
        rollback_eligible=rollback_eligible,
        schema_range=RuntimeSchemaReadRange(
            minimum_revision=minimum,
            maximum_revision=maximum,
            write_revision=write_revision,
        ),
    )


def _atomic_write(path: Path, document: Mapping[str, object]) -> None:
    if path.is_symlink():
        raise SchemaCompatibilityEvidenceError("Runtime Schema 兼容证据不能写入符号链接")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    payload = (
        json.dumps(
            document,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    try:
        with temporary_path.open("x", encoding="utf-8", newline="\n") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    except (OSError, UnicodeError) as exc:
        temporary_path.unlink(missing_ok=True)
        log.exception("Runtime Schema 兼容证据原子写入失败")
        raise SchemaCompatibilityEvidenceError("Runtime Schema 兼容证据无法保存") from exc


def _sha256(value: Mapping[str, object]) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
