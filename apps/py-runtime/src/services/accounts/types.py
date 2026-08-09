from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AccountStatus(StrEnum):
    DRAFT = "draft"
    UNBOUND = "unbound"
    READY = "ready"
    ATTENTION = "attention"
    ARCHIVED = "archived"


class ReadinessStatus(StrEnum):
    READY = "ready"
    ATTENTION = "attention"
    BLOCKED = "blocked"
    MISSING = "missing"
    EMPTY = "empty"
    CHECKING = "checking"


class ReadinessOverall(StrEnum):
    READY = "ready"
    ATTENTION = "attention"
    BLOCKED = "blocked"


class SuggestedActionKey(StrEnum):
    OPEN_CONNECTION = "open_connection"
    OPEN_KNOWLEDGE = "open_knowledge"
    OPEN_AI_RECIPE = "open_ai_recipe"
    RUN_HEALTH_CHECK = "run_health_check"
    VIEW_LOG = "view_log"


@dataclass(frozen=True, slots=True)
class SuggestedAction:
    action_key: SuggestedActionKey
    label: str
    route_id: str
    section: str | None = None
    task_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadinessItem:
    status: ReadinessStatus
    label: str
    error_code: str | None = None
    log_id: str | None = None
    checked_at: str | None = None
    suggested_action: SuggestedAction | None = None


@dataclass(frozen=True, slots=True)
class AccountReadiness:
    connection: ReadinessItem
    knowledge: ReadinessItem
    ai: ReadinessItem
    overall: ReadinessOverall
    checked_at: str | None
    suggested_action: SuggestedAction | None


@dataclass(frozen=True, slots=True)
class AccountHealthFacts:
    current_status: AccountStatus
    archived: bool
    wizard_completed: bool
    has_real_binding: bool
    connection_ever_verified: bool
    connection: ReadinessItem
    knowledge: ReadinessItem
    ai: ReadinessItem


@dataclass(frozen=True, slots=True)
class AccountLifecycleDecision:
    status: AccountStatus
    readiness: AccountReadiness


@dataclass(frozen=True, slots=True)
class RecipeCopyDecision:
    copied: bool
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.copied == (self.reason_code is not None):
            raise ValueError("AI Recipe 复制结果与原因不一致")
