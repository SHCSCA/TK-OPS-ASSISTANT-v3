from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from schemas.v1.account_common import (
    AccountV1Model,
    PositiveRevision,
    StableId,
)


class PositioningVersionInput(AccountV1Model):
    audience: dict[str, object]
    contentPillars: Annotated[list[str], Field(min_length=1, max_length=100)]
    tone: dict[str, object]
    prohibitedTopics: Annotated[list[str], Field(max_length=200)]
    publishingConstraints: dict[str, object]


class PositioningVersionSummaryDto(AccountV1Model):
    version: PositiveRevision
    status: Literal["draft", "active", "archived"]
    summary: str
    createdAt: str


class PositioningVersionDto(PositioningVersionSummaryDto):
    id: StableId
    accountId: StableId
    audience: dict[str, object]
    contentPillars: list[str]
    tone: dict[str, object]
    prohibitedTopics: list[str]
    publishingConstraints: dict[str, object]
    contentHash: Annotated[str, Field(min_length=64, max_length=64)]
    activatedAt: str | None
    revision: PositiveRevision


class PositioningDto(AccountV1Model):
    accountId: StableId
    activeVersion: PositiveRevision | None
    versions: list[PositioningVersionSummaryDto]
    revision: PositiveRevision


class BrandKitVersionInput(AccountV1Model):
    colors: Annotated[list[str], Field(max_length=100)]
    fonts: Annotated[list[str], Field(max_length=100)]
    logoAssetRefs: Annotated[list[str], Field(max_length=100)]
    visualRules: dict[str, object]
    voiceRules: dict[str, object]


class BrandKitVersionSummaryDto(AccountV1Model):
    version: PositiveRevision
    status: Literal["draft", "active", "archived"]
    contentHash: Annotated[str, Field(min_length=64, max_length=64)]
    createdAt: str


class ActiveBrandKitDto(AccountV1Model):
    colors: list[str]
    fonts: list[str]
    logoAssetRefs: list[str]
    visualRules: dict[str, object]
    voiceRules: dict[str, object]


class BrandKitDto(AccountV1Model):
    accountId: StableId
    activeVersion: PositiveRevision | None
    versions: list[BrandKitVersionSummaryDto]
    active: ActiveBrandKitDto | None
    revision: PositiveRevision


class PublishDefaultsInput(AccountV1Model):
    timezone: Annotated[str, Field(min_length=1, max_length=128)]
    privacyLevel: Annotated[str, Field(min_length=1, max_length=64)]
    allowComments: bool
    allowDuet: bool
    allowStitch: bool
    captionRules: dict[str, object]


class PublishDefaultsDto(PublishDefaultsInput):
    accountId: StableId
    revision: PositiveRevision
