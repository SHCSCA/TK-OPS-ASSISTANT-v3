from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ActivationResult:
    license_type: str
    activated_at: str
    masked_code: str
    signed_payload: str


class LicenseActivationAdapter(Protocol):
    def activate(self, activation_code: str, *, machine_code: str) -> ActivationResult: ...


class LicenseActivationError(RuntimeError):
    pass


class LicenseActivationUnavailableError(LicenseActivationError):
    pass
