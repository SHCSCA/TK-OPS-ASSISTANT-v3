from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from services.license_crypto import (
    LicensePayloadError,
    load_public_key,
    mask_activation_code,
    verify_activation_code,
)
from services.license_activation_base import (
    ActivationResult,
    LicenseActivationAdapter,
    LicenseActivationError,
)


class OfflineLicenseActivationAdapter:
    def __init__(self, public_key_path: Path) -> None:
        self._public_key_path = public_key_path

    def activate(self, activation_code: str, *, machine_code: str) -> ActivationResult:
        try:
            payload, signed_payload = verify_activation_code(
                activation_code,
                load_public_key(self._public_key_path),
            )
        except LicensePayloadError as exc:
            raise LicenseActivationError(str(exc)) from exc

        if normalize_machine_code(payload.machine_code) != normalize_machine_code(machine_code):
            raise LicenseActivationError("机器码不匹配")

        if payload.license_type != "perpetual":
            raise LicenseActivationError("当前授权类型不受支持")

        return ActivationResult(
            license_type=payload.license_type,
            activated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            masked_code=mask_activation_code(activation_code),
            signed_payload=signed_payload,
        )


def normalize_machine_code(machine_code: str) -> str:
    return "".join(machine_code.strip().upper().split())
