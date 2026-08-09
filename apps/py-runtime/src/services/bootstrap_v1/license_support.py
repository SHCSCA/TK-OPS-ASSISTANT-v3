from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime

from app.secret_store import SecretStore
from errors import DomainError, ErrorCode
from repositories.license_repository import StoredLicenseGrant
from schemas.v1.bootstrap import (
    LicenseBlockingIssueDto,
    LicenseState,
    LicenseStatusDto,
)
from services.license_activation_base import LicenseActivationError
from services.machine_code import MachineIdentityResolution

log = logging.getLogger(__name__)

LICENSE_SECRET_PREFIX = "secret://license-grants/"


@dataclass(frozen=True, slots=True)
class SecretValueSnapshot:
    existed: bool
    value: str | None = field(default=None, repr=False)


def license_status(
    *,
    status: LicenseState,
    machine_code: str,
    machine_code_masked: str,
    activated_at: str | None,
    revision: int,
    issue_code: ErrorCode | str | None = None,
    issue_message: str | None = None,
    machine_identity: MachineIdentityResolution | None = None,
) -> LicenseStatusDto:
    issue = (
        LicenseBlockingIssueDto(
            code=str(issue_code),
            message=issue_message or "许可证不可用",
        )
        if issue_code is not None
        else None
    )
    identity = machine_identity or MachineIdentityResolution(
        machine_code=machine_code,
        status="verified",
        matched_factor_count=0,
        mismatched_factor_count=0,
        unavailable_factor_count=0,
    )
    return LicenseStatusDto(
        status=status,
        machineCode=machine_code,
        machineCodeMasked=machine_code_masked,
        expiresAt=None,
        activatedAt=activated_at,
        blockingIssue=issue,
        revision=revision,
        machineIdentityStatus=identity.status,
        machineIdentityAlgorithm=identity.algorithm_version,
        matchedFactorCount=identity.matched_factor_count,
        mismatchedFactorCount=identity.mismatched_factor_count,
        unavailableFactorCount=identity.unavailable_factor_count,
    )


def build_secret_reference(license_key: str) -> str:
    digest = hashlib.sha256(license_key.encode("utf-8")).hexdigest()
    return f"{LICENSE_SECRET_PREFIX}{digest}"


def bootstrap_event_id(kind: str, idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"evt_bootstrap_{kind}_{digest}"


def secret_key(secret_reference: str) -> str:
    return secret_reference.removeprefix("secret://")


def capture_secret_snapshot(
    secret_store: SecretStore,
    secret_reference: str,
) -> SecretValueSnapshot:
    try:
        value = secret_store.get(secret_key(secret_reference))
    except Exception as exc:
        log.exception("读取许可证安全存储补偿快照失败")
        raise DomainError(
            ErrorCode.LICENSE_STORE_UNAVAILABLE,
            "许可证安全存储不可用",
            status_code=503,
            loggable=True,
            log_context={"operation": "license.secret_read"},
        ) from exc
    return SecretValueSnapshot(existed=value is not None, value=value)


def restore_secret_snapshot(
    secret_store: SecretStore,
    secret_reference: str,
    snapshot: SecretValueSnapshot,
) -> None:
    try:
        if snapshot.existed:
            secret_store.set(
                secret_key(secret_reference),
                snapshot.value or "",
            )
        else:
            secret_store.delete(secret_key(secret_reference))
    except Exception as exc:
        log.exception("回滚许可证安全存储失败")
        raise DomainError(
            ErrorCode.LICENSE_STORE_UNAVAILABLE,
            "许可证安全存储回滚失败，请查看诊断日志",
            status_code=503,
            loggable=True,
            log_context={"operation": "license.secret_rollback"},
        ) from exc


def mask_machine_code(machine_code: str) -> str:
    normalized = normalize_machine_code(machine_code)
    if len(normalized) <= 10:
        return "*" * len(normalized)
    return (
        f"{normalized[:6]}"
        f"{'*' * max(5, len(normalized) - 11)}"
        f"{normalized[-5:]}"
    )


def license_revision(stored: StoredLicenseGrant) -> int:
    if stored.activated_at:
        try:
            timestamp = datetime.fromisoformat(
                stored.activated_at.replace("Z", "+00:00")
            ).timestamp()
            return max(1, int(timestamp * 1_000_000))
        except (TypeError, ValueError, OSError):
            log.warning("许可证激活时间格式无效，已回退到基础修订")
    return 1


def normalize_machine_code(machine_code: str) -> str:
    return "".join(machine_code.strip().upper().split())


def activation_domain_error(
    exc: LicenseActivationError,
    *,
    operation: str,
) -> DomainError:
    if is_machine_mismatch(exc):
        return DomainError(
            ErrorCode.LICENSE_MACHINE_MISMATCH,
            "许可证与本机不匹配",
            status_code=403,
            log_context={"operation": operation},
        )
    if is_store_unavailable(exc):
        return DomainError(
            ErrorCode.LICENSE_STORE_UNAVAILABLE,
            "许可证安全存储不可用",
            status_code=503,
            loggable=True,
            log_context={"operation": operation},
        )
    return DomainError(
        ErrorCode.LICENSE_INVALID,
        "许可证无效",
        status_code=403,
        log_context={"operation": operation},
    )


def is_machine_mismatch(exc: LicenseActivationError) -> bool:
    return str(exc) == "机器码不匹配"


def is_store_unavailable(exc: LicenseActivationError) -> bool:
    return str(exc) in {
        "公钥未配置",
        "许可证激活依赖未就绪，请检查运行时依赖与授权配置",
    }
