from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from common.identifiers import is_stable_id
from services.events.errors import AccountScopeMismatchError, EventValidationError

TopicScope = Literal["system", "account"]

_RESOURCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9._-]*(?::[a-z][a-z0-9._-]*)*$"
)
_MAX_TOPIC_LENGTH = 512

SYSTEM_BOOTSTRAP_TOPIC = "system:bootstrap"
SYSTEM_CONFIG_TOPIC = "system:config"
SYSTEM_HEALTH_TOPIC = "system:health"
SYSTEM_AI_TOPIC = "system:ai"
SYSTEM_TASKS_TOPIC = "system:tasks"


@dataclass(frozen=True, slots=True)
class ParsedTopic:
    value: str
    scope: TopicScope
    resource: str
    account_id: str | None


def build_system_topic(resource: str) -> str:
    _validate_resource(resource)
    return f"system:{resource}"


def build_account_topic(account_id: str, resource: str) -> str:
    validate_stable_id(account_id, "账号 ID")
    _validate_resource(resource)
    return f"account:{account_id}:{resource}"


def parse_topic(topic: str) -> ParsedTopic:
    if len(topic) > _MAX_TOPIC_LENGTH:
        raise EventValidationError("Topic 超过允许长度。")
    normalized = topic.strip()
    if normalized.startswith("system:"):
        resource = normalized.removeprefix("system:")
        _validate_resource(resource)
        return ParsedTopic(
            value=normalized,
            scope="system",
            resource=resource,
            account_id=None,
        )

    if normalized.startswith("account:"):
        parts = normalized.split(":", 2)
        if len(parts) != 3:
            raise EventValidationError("账号 Topic 格式无效。")
        account_id, resource = parts[1], parts[2]
        validate_stable_id(account_id, "账号 ID")
        _validate_resource(resource)
        return ParsedTopic(
            value=normalized,
            scope="account",
            resource=resource,
            account_id=account_id,
        )

    raise EventValidationError("Topic 必须使用 system:* 或 account:{account_id}:*。")


def validate_topic_scope(topic: str, account_id: str | None) -> ParsedTopic:
    parsed = parse_topic(topic)
    if parsed.scope == "system":
        if account_id is not None:
            raise AccountScopeMismatchError("系统 Topic 不得携带账号 ID。")
        return parsed

    if account_id is None or parsed.account_id != account_id:
        raise AccountScopeMismatchError()
    return parsed


def validate_stable_id(value: str, label: str) -> None:
    if not is_stable_id(value):
        raise EventValidationError(f"{label} 格式无效。")


def _validate_resource(resource: str) -> None:
    if not _RESOURCE_PATTERN.fullmatch(resource):
        raise EventValidationError("Topic 资源段格式无效。")
