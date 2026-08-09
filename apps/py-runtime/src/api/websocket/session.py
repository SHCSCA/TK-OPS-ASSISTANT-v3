from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class WebSocketAccessContext:
    session_id: str
    accepted_subprotocol: str | None = None
    allowed_system_topics: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class WebSocketSessionSnapshot:
    session_id: str
    mode: str
    account_id: str | None
    subscription_revision: int
    topics: frozenset[str]
