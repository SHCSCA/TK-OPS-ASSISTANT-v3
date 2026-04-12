from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class LicenseStatusDto(BaseModel):
    active: bool
    restrictedMode: bool
    machineCode: str
    machineBound: bool
    licenseType: str
    maskedCode: str
    activatedAt: str | None


class LicenseActivateInput(BaseModel):
    activationCode: Annotated[str, Field(min_length=1)]


class LicenseActivateResultDto(LicenseStatusDto):
    pass
