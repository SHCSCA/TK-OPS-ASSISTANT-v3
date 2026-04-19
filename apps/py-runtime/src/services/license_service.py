from __future__ import annotations

from fastapi import HTTPException

from app.config import RuntimeConfig
from app.logging import log_event
from repositories.license_repository import LicenseRepository, StoredLicenseGrant
from schemas.license import (
    LicenseActivateInput,
    LicenseActivateResultDto,
    LicenseStatusDto,
)
from services.license_activation_base import (
    LicenseActivationAdapter,
    LicenseActivationError,
    LicenseActivationUnavailableError,
)
from services.machine_code import MachineCodeError, MachineCodeService


class LicenseService:
    def __init__(
        self,
        *,
        runtime_config: RuntimeConfig,
        repository: LicenseRepository,
        activation_adapter: LicenseActivationAdapter,
        machine_code_service: MachineCodeService,
    ) -> None:
        self._runtime_config = runtime_config
        self._repository = repository
        self._activation_adapter = activation_adapter
        self._machine_code_service = machine_code_service

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
        try:
            activation_result = self._activation_adapter.activate(
                payload.activationCode,
                machine_code=current.machine_code,
            )
        except LicenseActivationUnavailableError as exc:
            log_event(
                "audit",
                "license.activation_failed",
                request_id=request_id,
                context={
                    "machineCode": current.machine_code,
                    "reason": str(exc),
                },
            )
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LicenseActivationError as exc:
            log_event(
                "audit",
                "license.activation_failed",
                request_id=request_id,
                context={
                    "machineCode": current.machine_code,
                    "reason": str(exc),
                },
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        updated = self._repository.save(
            StoredLicenseGrant(
                active=True,
                restricted_mode=False,
                machine_code=current.machine_code,
                machine_bound=True,
                license_type=activation_result.license_type,
                signed_payload=activation_result.signed_payload,
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
                "machineCode": result.machineCode,
                "licenseType": result.licenseType,
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
                machine_code=self._resolve_machine_code(),
                machine_bound=False,
                license_type="perpetual",
                signed_payload="",
                masked_code="",
                activated_at=None,
            )
        )

    def _to_status_dto(self, stored: StoredLicenseGrant) -> LicenseStatusDto:
        return LicenseStatusDto(
            active=stored.active,
            restrictedMode=stored.restricted_mode,
            machineCode=stored.machine_code,
            machineBound=stored.machine_bound,
            licenseType=stored.license_type,
            maskedCode=stored.masked_code,
            activatedAt=stored.activated_at,
        )

    def _resolve_machine_code(self) -> str:
        try:
            return self._machine_code_service.get_machine_code()
        except MachineCodeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
