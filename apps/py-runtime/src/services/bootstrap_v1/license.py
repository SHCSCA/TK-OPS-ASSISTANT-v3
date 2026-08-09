from __future__ import annotations

import logging
from threading import RLock
from typing import Callable

from sqlalchemy.orm import Session

from app.logging import log_event
from app.secret_store import SecretStore
from errors import DomainError, ErrorCode
from repositories.license_repository import LicenseRepository, StoredLicenseGrant
from schemas.v1.bootstrap import LicenseStatusDto
from services.bootstrap_v1.license_support import (
    LICENSE_SECRET_PREFIX as _LICENSE_SECRET_PREFIX,
    activation_domain_error as _activation_domain_error,
    bootstrap_event_id as _bootstrap_event_id,
    build_secret_reference as _build_secret_reference,
    capture_secret_snapshot as _capture_secret_snapshot,
    is_machine_mismatch as _is_machine_mismatch,
    is_store_unavailable as _is_store_unavailable,
    license_revision as _license_revision,
    license_status as _license_status,
    mask_machine_code as _mask_machine_code,
    normalize_machine_code as _normalize_machine_code,
    restore_secret_snapshot as _restore_secret_snapshot,
    secret_key as _secret_key,
)
from services.license_activation_base import (
    LicenseActivationAdapter,
    LicenseActivationError,
    LicenseActivationUnavailableError,
)
from services.events import RuntimeEventDraft, RuntimeEventService
from services.machine_code import (
    MachineCodeError,
    MachineCodeService,
    MachineIdentityResolution,
)

log = logging.getLogger(__name__)


class LicenseV1Service:
    def __init__(
        self,
        *,
        repository: LicenseRepository,
        activation_adapter: LicenseActivationAdapter,
        machine_code_service: MachineCodeService,
        secret_store: SecretStore,
        event_service: RuntimeEventService | None = None,
    ) -> None:
        self._repository = repository
        self._activation_adapter = activation_adapter
        self._machine_code_service = machine_code_service
        self._secret_store = secret_store
        self._event_service = event_service
        self._activation_lock = RLock()

    def get_status(
        self,
        *,
        request_id: str,
        operation_id: str,
    ) -> LicenseStatusDto:
        stored = self._load_grant()
        machine_identity = self._resolve_machine_identity(stored)
        status = self._build_status(stored, machine_identity=machine_identity)
        log_event(
            "audit",
            "bootstrap.license_status_read",
            request_id=request_id,
            operation_id=operation_id,
            context={
                "licenseStatus": status.status,
                "revision": status.revision,
            },
        )
        return status

    def activate(
        self,
        *,
        license_key: str,
        machine_code: str | None,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> LicenseStatusDto:
        normalized_key = license_key.strip()
        initial = self._load_grant()
        machine_identity = self._resolve_machine_identity(initial)
        if machine_identity.status == "mismatch":
            raise DomainError(
                ErrorCode.LICENSE_MACHINE_MISMATCH,
                "许可证与本机不匹配",
                status_code=403,
                log_context={"operation": "license.activate"},
            )
        current_machine_code = machine_identity.machine_code
        if (
            machine_code is not None
            and _normalize_machine_code(machine_code)
            != _normalize_machine_code(current_machine_code)
        ):
            raise DomainError(
                ErrorCode.LICENSE_MACHINE_MISMATCH,
                "许可证与本机不匹配",
                status_code=403,
                log_context={"operation": "license.activate"},
            )

        secret_reference = _build_secret_reference(normalized_key)
        event_id = _bootstrap_event_id("license", idempotency_key)
        with self._activation_lock:
            current = self._load_grant()
            if (
                current is not None
                and current.signed_payload == secret_reference
                and self._build_status(
                    current,
                    machine_identity=machine_identity,
                ).status
                == "active"
            ):
                current_status = self._build_status(
                    current,
                    machine_identity=machine_identity,
                )
                self._ensure_license_event(
                    current_status,
                    event_id=event_id,
                )
                return current_status

            try:
                activation_result = self._activation_adapter.activate(
                    normalized_key,
                    machine_code=current_machine_code,
                )
            except LicenseActivationUnavailableError as exc:
                log.exception("许可证激活依赖不可用")
                raise DomainError(
                    ErrorCode.LICENSE_STORE_UNAVAILABLE,
                    "许可证安全存储不可用",
                    status_code=503,
                    loggable=True,
                    log_context={"operation": "license.activate"},
                ) from exc
            except LicenseActivationError as exc:
                log.warning("许可证激活校验失败")
                raise _activation_domain_error(
                    exc,
                    operation="license.activate",
                ) from exc
            except Exception as exc:
                log.exception("许可证激活发生未知异常")
                raise DomainError(
                    ErrorCode.LICENSE_STORE_UNAVAILABLE,
                    "许可证服务暂不可用",
                    status_code=503,
                    loggable=True,
                    log_context={"operation": "license.activate"},
                ) from exc

            secret_snapshot = _capture_secret_snapshot(
                self._secret_store,
                secret_reference,
            )
            try:
                self._save_secret(secret_reference, normalized_key)
                grant = StoredLicenseGrant(
                    active=True,
                    restricted_mode=False,
                    machine_code=current_machine_code,
                    machine_bound=True,
                    license_type=activation_result.license_type,
                    signed_payload=secret_reference,
                    masked_code=activation_result.masked_code,
                    activated_at=activation_result.activated_at,
                )
                updated = self._save_grant(
                    grant,
                    before_commit=lambda session, saved: (
                        self._append_license_event_in_transaction(
                            session,
                            saved,
                            event_id=event_id,
                        )
                    ),
                )
            except Exception:
                _restore_secret_snapshot(
                    self._secret_store,
                    secret_reference,
                    secret_snapshot,
                )
                raise
            if (
                current is not None
                and current.signed_payload != secret_reference
            ):
                self._delete_secret_reference(
                    current.signed_payload,
                    best_effort=True,
                )

        status = self._build_status(updated, machine_identity=machine_identity)
        log_event(
            "audit",
            "bootstrap.license_activated",
            request_id=request_id,
            operation_id=operation_id,
            context={
                "licenseStatus": status.status,
                "machineCodeMasked": status.machineCodeMasked,
                "licenseType": updated.license_type,
                "revision": status.revision,
                "idempotencyKeyPresent": bool(idempotency_key),
            },
        )
        return status

    def _build_status(
        self,
        stored: StoredLicenseGrant | None,
        *,
        machine_identity: MachineIdentityResolution,
    ) -> LicenseStatusDto:
        machine_code = machine_identity.machine_code
        masked_machine_code = _mask_machine_code(machine_code)
        if stored is None:
            return _license_status(
                status="missing",
                machine_code=machine_code,
                machine_code_masked=masked_machine_code,
                activated_at=None,
                revision=0,
                issue_code="LICENSE_MISSING",
                issue_message="许可证尚未激活",
                machine_identity=machine_identity,
            )

        revision = _license_revision(stored)
        if machine_identity.status == "mismatch" or (
            _normalize_machine_code(stored.machine_code)
            != _normalize_machine_code(machine_code)
        ):
            return _license_status(
                status="machine_mismatch",
                machine_code=machine_code,
                machine_code_masked=masked_machine_code,
                activated_at=stored.activated_at,
                revision=revision,
                issue_code=ErrorCode.LICENSE_MACHINE_MISMATCH,
                issue_message="许可证与本机不匹配",
                machine_identity=machine_identity,
            )

        if not stored.active or stored.restricted_mode:
            return _license_status(
                status="missing" if stored.restricted_mode else "invalid",
                machine_code=machine_code,
                machine_code_masked=masked_machine_code,
                activated_at=stored.activated_at,
                revision=revision,
                issue_code="LICENSE_MISSING"
                if stored.restricted_mode
                else ErrorCode.LICENSE_INVALID,
                issue_message="许可证尚未激活"
                if stored.restricted_mode
                else "许可证无效",
                machine_identity=machine_identity,
            )

        if stored.license_type != "perpetual":
            return _license_status(
                status="invalid",
                machine_code=machine_code,
                machine_code_masked=masked_machine_code,
                activated_at=stored.activated_at,
                revision=revision,
                issue_code=ErrorCode.LICENSE_INVALID,
                issue_message="当前许可证类型不受支持",
                machine_identity=machine_identity,
            )

        license_key = self._read_license_key(stored.signed_payload)
        if license_key is None:
            return _license_status(
                status="invalid",
                machine_code=machine_code,
                machine_code_masked=masked_machine_code,
                activated_at=stored.activated_at,
                revision=revision,
                issue_code=ErrorCode.LICENSE_INVALID,
                issue_message="许可证需要重新激活",
                machine_identity=machine_identity,
            )

        try:
            self._activation_adapter.activate(
                license_key,
                machine_code=machine_code,
            )
        except LicenseActivationUnavailableError as exc:
            log.exception("读取许可证时激活依赖不可用")
            raise DomainError(
                ErrorCode.LICENSE_STORE_UNAVAILABLE,
                "许可证安全存储不可用",
                status_code=503,
                loggable=True,
                log_context={"operation": "license.read"},
            ) from exc
        except LicenseActivationError as exc:
            log.warning("已存许可证校验失败")
            if _is_machine_mismatch(exc):
                return _license_status(
                    status="machine_mismatch",
                    machine_code=machine_code,
                    machine_code_masked=masked_machine_code,
                    activated_at=stored.activated_at,
                    revision=revision,
                    issue_code=ErrorCode.LICENSE_MACHINE_MISMATCH,
                    issue_message="许可证与本机不匹配",
                    machine_identity=machine_identity,
                )
            if _is_store_unavailable(exc):
                raise _activation_domain_error(
                    exc,
                    operation="license.read",
                ) from exc
            return _license_status(
                status="invalid",
                machine_code=machine_code,
                machine_code_masked=masked_machine_code,
                activated_at=stored.activated_at,
                revision=revision,
                issue_code=ErrorCode.LICENSE_INVALID,
                issue_message="许可证签名无效",
                machine_identity=machine_identity,
            )
        except Exception as exc:
            log.exception("校验已存许可证时发生未知异常")
            raise DomainError(
                ErrorCode.LICENSE_STORE_UNAVAILABLE,
                "许可证服务暂不可用",
                status_code=503,
                loggable=True,
                log_context={"operation": "license.read"},
            ) from exc

        return _license_status(
            status="active",
            machine_code=machine_code,
            machine_code_masked=masked_machine_code,
            activated_at=stored.activated_at,
            revision=revision,
            machine_identity=machine_identity,
        )

    def _resolve_machine_identity(
        self,
        stored: StoredLicenseGrant | None,
    ) -> MachineIdentityResolution:
        try:
            resolution = self._machine_code_service.resolve(
                legacy_machine_code=(stored.machine_code if stored else None),
            )
        except MachineCodeError as exc:
            log.exception("生成许可证机器码失败")
            code = (
                ErrorCode.MACHINE_IDENTITY_STORE_UNAVAILABLE
                if exc.code == "MACHINE_IDENTITY_STORE_UNAVAILABLE"
                else ErrorCode.MACHINE_IDENTITY_RETRY_REQUIRED
            )
            raise DomainError(
                code,
                "机器身份安全存储不可用"
                if code == ErrorCode.MACHINE_IDENTITY_STORE_UNAVAILABLE
                else "设备信息采集不完整，请稍后重试",
                status_code=503,
                loggable=True,
                log_context={"operation": "license.machine_code"},
            ) from exc
        if resolution.status == "unavailable":
            raise DomainError(
                ErrorCode.MACHINE_IDENTITY_RETRY_REQUIRED,
                "设备信息采集不完整，请稍后重试",
                status_code=503,
                loggable=True,
                log_context={"operation": "license.machine_identity"},
            )
        return resolution

    def _load_grant(self) -> StoredLicenseGrant | None:
        try:
            return self._repository.load()
        except Exception as exc:
            log.exception("读取许可证记录失败")
            raise DomainError(
                ErrorCode.LICENSE_STORE_UNAVAILABLE,
                "许可证安全存储不可用",
                status_code=503,
                loggable=True,
                log_context={"operation": "license.read"},
            ) from exc

    def _save_grant(
        self,
        grant: StoredLicenseGrant,
        *,
        before_commit: Callable[
            [Session, StoredLicenseGrant],
            None,
        ]
        | None = None,
    ) -> StoredLicenseGrant:
        try:
            return self._repository.save(
                grant,
                before_commit=before_commit,
            )
        except Exception as exc:
            log.exception("保存许可证记录失败")
            raise DomainError(
                ErrorCode.LICENSE_STORE_UNAVAILABLE,
                "许可证安全存储不可用",
                status_code=503,
                loggable=True,
                log_context={"operation": "license.write"},
            ) from exc

    def _save_secret(self, secret_reference: str, license_key: str) -> None:
        try:
            self._secret_store.set(_secret_key(secret_reference), license_key)
        except Exception as exc:
            log.exception("写入许可证安全存储失败")
            raise DomainError(
                ErrorCode.LICENSE_STORE_UNAVAILABLE,
                "许可证安全存储不可用",
                status_code=503,
                loggable=True,
                log_context={"operation": "license.secret_write"},
            ) from exc

    def _delete_secret_reference(
        self,
        secret_reference: str,
        *,
        best_effort: bool = False,
    ) -> None:
        if not secret_reference.startswith(_LICENSE_SECRET_PREFIX):
            return
        try:
            self._secret_store.delete(_secret_key(secret_reference))
        except Exception as exc:
            log.exception("清理许可证安全存储引用失败")
            if best_effort:
                return
            raise DomainError(
                ErrorCode.LICENSE_STORE_UNAVAILABLE,
                "许可证安全存储清理失败，请查看诊断日志",
                status_code=503,
                loggable=True,
                log_context={"operation": "license.secret_delete"},
            ) from exc

    def _append_license_event_in_transaction(
        self,
        session: Session,
        grant: StoredLicenseGrant,
        *,
        event_id: str,
    ) -> None:
        if self._event_service is None:
            return
        self._event_service.append(
            session,
            RuntimeEventDraft(
                event_id=event_id,
                event_type="bootstrap.license.changed",
                topic="system:bootstrap",
                revision=_license_revision(grant),
                payload={
                    "status": "active",
                    "invalidations": ["bootstrap", "license"],
                },
            ),
        )

    def _ensure_license_event(
        self,
        status: LicenseStatusDto,
        *,
        event_id: str,
    ) -> None:
        if self._event_service is None:
            return
        self._event_service.append_standalone_idempotent(
            RuntimeEventDraft(
                event_id=event_id,
                event_type="bootstrap.license.changed",
                topic="system:bootstrap",
                revision=status.revision,
                payload={
                    "status": status.status,
                    "invalidations": ["bootstrap", "license"],
                },
            )
        )

    def _read_license_key(self, reference: str) -> str | None:
        if reference.startswith(_LICENSE_SECRET_PREFIX):
            try:
                license_key = self._secret_store.get(_secret_key(reference))
            except Exception as exc:
                log.exception("读取许可证安全存储失败")
                raise DomainError(
                    ErrorCode.LICENSE_STORE_UNAVAILABLE,
                    "许可证安全存储不可用",
                    status_code=503,
                    loggable=True,
                    log_context={"operation": "license.secret_read"},
                ) from exc
            if license_key is None:
                log.error("许可证安全存储引用不存在")
                raise DomainError(
                    ErrorCode.LICENSE_STORE_UNAVAILABLE,
                    "许可证安全存储不可用",
                    status_code=503,
                    loggable=True,
                    log_context={
                        "operation": "license.secret_read",
                        "secretMissing": True,
                    },
                )
            return license_key

        if "." in reference:
            return reference
        return None
