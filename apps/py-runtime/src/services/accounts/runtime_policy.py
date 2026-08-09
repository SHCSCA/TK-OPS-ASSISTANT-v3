from __future__ import annotations

from dataclasses import dataclass

from errors import DomainError, ErrorCode
from services.config import ConfigBusService, ConfigBusSnapshot
from services.config.schema import (
    MUTATION_IDEMPOTENCY_TTL_MAXIMUM,
    MUTATION_IDEMPOTENCY_TTL_MINIMUM,
)

_REQUIRED_CAPABILITIES_KEY = "accounts.requiredCapabilities"
_MUTATION_TTL_KEY = "api.mutationIdempotencyTtlSeconds"
_LEGACY_CAPABILITY_ALIASES = {
    "video_generation": "text_to_video",
}


@dataclass(frozen=True, slots=True)
class AccountRuntimePolicy:
    required_capabilities: tuple[str, ...]
    mutation_idempotency_ttl_seconds: int
    config_revision: int


def load_account_runtime_policy(
    config_bus: ConfigBusService,
) -> AccountRuntimePolicy:
    snapshot = config_bus.get()
    return account_runtime_policy_from_snapshot(snapshot)


def account_runtime_policy_from_snapshot(
    snapshot: ConfigBusSnapshot,
) -> AccountRuntimePolicy:
    capabilities = snapshot.values.get(_REQUIRED_CAPABILITIES_KEY)
    retention = snapshot.values.get(_MUTATION_TTL_KEY)
    if (
        not isinstance(capabilities, list)
        or len(capabilities) > 32
        or any(
            not isinstance(item, str)
            or not item
            or len(item) > 128
            for item in capabilities
        )
        or len(set(capabilities)) != len(capabilities)
        or not isinstance(retention, int)
        or isinstance(retention, bool)
        or not (
            MUTATION_IDEMPOTENCY_TTL_MINIMUM
            <= retention
            <= MUTATION_IDEMPOTENCY_TTL_MAXIMUM
        )
    ):
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "账号运行策略配置异常，请查看诊断日志",
            status_code=500,
            loggable=True,
            log_context={
                "operation": "accounts.resolve_runtime_policy",
                "configRevision": snapshot.revision,
            },
        )
    normalized_capabilities = tuple(
        _LEGACY_CAPABILITY_ALIASES.get(item, item)
        for item in capabilities
    )
    return AccountRuntimePolicy(
        required_capabilities=tuple(dict.fromkeys(normalized_capabilities)),
        mutation_idempotency_ttl_seconds=retention,
        config_revision=snapshot.revision,
    )
