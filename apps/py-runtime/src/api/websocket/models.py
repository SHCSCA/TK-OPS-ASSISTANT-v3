from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TopicCursorFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    topic: str = Field(min_length=1, max_length=512)
    last_event_id: str | None = Field(
        default=None,
        alias="lastEventId",
        min_length=1,
        max_length=128,
    )
    after_sequence: int | None = Field(
        default=None,
        alias="afterSequence",
        ge=0,
    )


class SubscribeFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["subscribe"]
    subscription_revision: int = Field(alias="subscriptionRevision", ge=1)
    account_id: str | None = Field(
        default=None,
        alias="accountId",
        min_length=1,
        max_length=128,
    )
    topics: list[TopicCursorFrame] = Field(min_length=1, max_length=64)


class SubscribedTopicFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    topic: str
    current_sequence: int = Field(alias="currentSequence", ge=0)
    replayed_count: int = Field(alias="replayedCount", ge=0)


class SubscribedFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["subscribed"] = "subscribed"
    subscription_revision: int = Field(alias="subscriptionRevision", ge=1)
    topics: list[SubscribedTopicFrame]


class SyncRequiredFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["sync.required"] = "sync.required"
    subscription_revision: int = Field(alias="subscriptionRevision", ge=1)
    topic: str
    current_sequence: int = Field(alias="currentSequence", ge=0)
    reason: Literal["WS_EVENT_GAP"] = "WS_EVENT_GAP"


class ProtocolErrorFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["error"] = "error"
    error_code: str = Field(alias="errorCode")
    message: str
    subscription_revision: int | None = Field(
        default=None,
        alias="subscriptionRevision",
    )


class PongFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["pong"] = "pong"


def frame_payload(frame: BaseModel) -> dict[str, Any]:
    return frame.model_dump(by_alias=True, exclude_none=True, mode="json")
