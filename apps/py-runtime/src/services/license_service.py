from __future__ import annotations

from uuid import uuid4

from app.config import RuntimeConfig
from app.logging import log_event
from repositories.license_repository import LicenseRepository, StoredLicenseGrant
from schemas.license import (
    LicenseActivateInput,
    LicenseActivateResultDto,
    LicenseStatusDto,
)
from services.license_activation import LicenseActivationAdapter


class LicenseService:
    def __init__(
        self,
        *,
        runtime_config: RuntimeConfig,
        repository: LicenseRepository,
        activation_adapter: LicenseActivationAdapter,
    ) -> None:
        self._runtime_config = runtime_config
        self._repository = repository
        self._activation_adapter = activation_adapter

    def get_status(self, *, request_id: str | None = None) -> LicenseStatusDto:
        stored = self._load_or_create()
        status = self._to_status_dto(stored)
        log_event(
            "audit",
            "license.status_loaded",
            request_id=request_id,
            context={
                "active": status.active,
                "restrictedMode": status.restrictedMode,
                "machineBound": status.machineBound,
            },
        )
        return status

    def activate(
        self,
        payload: LicenseActivateInput,
        *,
        request_id: str | None = None,
    ) -> LicenseActivateResultDto:
        current = self._load_or_create()
        activation_result = self._activation_adapter.activate(payload.activationCode)
        updated = self._repository.save(
            StoredLicenseGrant(
                active=True,
                restricted_mode=False,
                machine_id=current.machine_id,
                machine_bound=True,
                activation_mode=activation_result.activation_mode,
                masked_code=activation_result.masked_code,
                activated_at=activation_result.activated_at,
            )
        )
        result = LicenseActivateResultDto.model_validate(
            self._to_status_dto(updated).model_dump(mode="json")
        )
        log_event(
            "audit",
            "license.activated",
            request_id=request_id,
            context={
                "machineId": result.machineId,
                "activationMode": result.activationMode,
            },
        )
        return result

    def _load_or_create(self) -> StoredLicenseGrant:
        stored = self._repository.load()
        if stored is not None:
            return stored

        return self._repository.save(
            StoredLicenseGrant(
                active=False,
                restricted_mode=True,
                machine_id=uuid4().hex,
                machine_bound=False,
                activation_mode="placeholder",
                masked_code="",
                activated_at=None,
            )
        )

    def _to_status_dto(self, stored: StoredLicenseGrant) -> LicenseStatusDto:
        return LicenseStatusDto(
            active=stored.active,
            restrictedMode=stored.restricted_mode,
            machineId=stored.machine_id,
            machineBound=stored.machine_bound,
            activationMode=stored.activation_mode,
            maskedCode=stored.masked_code,
            activatedAt=stored.activated_at,
        )
