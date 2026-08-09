from __future__ import annotations

from pydantic import BaseModel, Field


class SystemConfigPatchInput(BaseModel):
    values: dict[str, object] = Field(default_factory=dict)


class SystemConfigDto(BaseModel):
    values: dict[str, object]
    writableKeys: list[str]
    restartRequiredKeys: list[str]
    revision: int
