from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from schemas.v1.account_common import AccountV1Model, PositiveRevision, StableId

LoginSessionState = Literal[
    "preparing",
    "waiting_user",
    "probing",
    "completed",
    "cancelled",
    "failed",
    "timed_out",
]


class LoginSessionCreateInput(AccountV1Model):
    environmentId: StableId


class LoginSessionDto(AccountV1Model):
    id: StableId
    accountId: StableId
    environmentId: StableId
    state: LoginSessionState
    expectedIdentity: str
    detectedIdentity: str | None
    expiresAt: str
    prepareTaskId: StableId | None
    probeTaskId: StableId | None
    errorCode: str | None
    errorLogId: StableId | None
    revision: PositiveRevision


class LoginSessionAcceptedDto(AccountV1Model):
    sessionId: StableId
    taskId: StableId
    state: LoginSessionState


class LoginSessionProbeInput(AccountV1Model):
    revision: Annotated[int, Field(ge=1)]


class LogoutAcceptedDto(AccountV1Model):
    taskId: StableId
