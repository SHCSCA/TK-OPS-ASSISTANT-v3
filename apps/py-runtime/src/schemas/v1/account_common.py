from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from common.identifiers import STABLE_ID_PATTERN_TEXT

StableId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=128,
        pattern=STABLE_ID_PATTERN_TEXT,
    ),
]
PositiveRevision = Annotated[int, Field(ge=1)]
AccountStatusValue = Literal[
    "draft",
    "unbound",
    "ready",
    "attention",
    "archived",
]
ReadinessStatusValue = Literal[
    "ready",
    "attention",
    "blocked",
    "missing",
    "empty",
    "checking",
]


class AccountV1Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SuggestedActionDto(AccountV1Model):
    actionKey: Literal[
        "open_connection",
        "open_knowledge",
        "open_ai_recipe",
        "run_health_check",
        "view_log",
    ]
    label: Annotated[str, Field(min_length=1, max_length=128)]
    routeId: StableId
    section: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    taskId: StableId | None = None


class ReadinessItemDto(AccountV1Model):
    status: ReadinessStatusValue
    label: Annotated[str, Field(min_length=1, max_length=128)]
    errorCode: Annotated[str, Field(min_length=1, max_length=128)] | None
    logId: StableId | None
    checkedAt: str | None
    suggestedAction: SuggestedActionDto | None


class AccountReadinessDto(AccountV1Model):
    connection: ReadinessItemDto
    knowledge: ReadinessItemDto
    ai: ReadinessItemDto
    overall: Literal["ready", "attention", "blocked"]
    checkedAt: str | None
    suggestedAction: SuggestedActionDto | None


class AccountDto(AccountV1Model):
    id: StableId
    name: Annotated[str, Field(min_length=1, max_length=128)]
    username: Annotated[str, Field(min_length=1, max_length=64)] | None
    platform: Literal["tiktok"]
    status: AccountStatusValue
    positioningSummary: str | None
    lastUsedAt: str | None
    readiness: AccountReadinessDto
    wizardCompletedAt: str | None
    revision: PositiveRevision


class AccountListDto(AccountV1Model):
    items: list[AccountDto]
    totalKnown: Annotated[int, Field(ge=0)] | None
