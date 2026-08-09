from __future__ import annotations

from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from schemas.v1.account_common import PositiveRevision, StableId

DataT = TypeVar("DataT")
ProfileStatusValue = Literal["draft", "active", "archived"]
ValidationStatusValue = Literal["valid", "incomplete", "invalid"]
JsonObject = dict[str, object]
NonEmptyText = Annotated[str, Field(min_length=1)]
BoundedName = Annotated[str, Field(min_length=1, max_length=128)]
BoundedKey = Annotated[str, Field(min_length=1, max_length=128)]
ContentHash = Annotated[
    str,
    Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    ),
]
NonNegativeRevision = Annotated[int, Field(ge=0)]


class AIConfigurationInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


class AIConfigurationDto(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
    )


class ResponseMetaDto(AIConfigurationDto):
    revision: PositiveRevision | None = None
    invalidations: list[str] | None = None
    nextCursor: str | None = None


class AISuccessEnvelope(BaseModel, Generic[DataT]):
    model_config = ConfigDict(extra="forbid")

    ok: Literal[True]
    data: DataT


class AISuccessEnvelopeWithMeta(AISuccessEnvelope[DataT], Generic[DataT]):
    meta: ResponseMetaDto


class VersionSummaryDto(AIConfigurationDto):
    version: PositiveRevision
    status: ProfileStatusValue
    contentHash: ContentHash


class ValidationIssueDto(AIConfigurationDto):
    code: BoundedKey
    field: Annotated[str, Field(min_length=1, max_length=512)] | None
    message: NonEmptyText


__all__ = [
    "AIConfigurationDto",
    "AIConfigurationInput",
    "AISuccessEnvelope",
    "AISuccessEnvelopeWithMeta",
    "BoundedKey",
    "BoundedName",
    "ContentHash",
    "JsonObject",
    "NonEmptyText",
    "NonNegativeRevision",
    "PositiveRevision",
    "ProfileStatusValue",
    "ResponseMetaDto",
    "StableId",
    "ValidationIssueDto",
    "ValidationStatusValue",
    "VersionSummaryDto",
]
