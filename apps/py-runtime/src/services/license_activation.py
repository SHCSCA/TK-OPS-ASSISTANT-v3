from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ActivationResult:
    activation_mode: str
    activated_at: str
    masked_code: str


class LicenseActivationAdapter(Protocol):
    def activate(self, activation_code: str) -> ActivationResult: ...


class PlaceholderLicenseActivationAdapter:
    def activate(self, activation_code: str) -> ActivationResult:
        normalized_code = activation_code.strip()
        return ActivationResult(
            activation_mode="placeholder",
            activated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            masked_code=_mask_activation_code(normalized_code),
        )


def _mask_activation_code(activation_code: str) -> str:
    if len(activation_code) <= 8:
        return "*" * len(activation_code)

    return f"{activation_code[:4]}{'*' * 16}{activation_code[-4:]}"
