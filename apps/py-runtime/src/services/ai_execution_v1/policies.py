from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from domain.models.ai_configuration_v1 import CapabilityRouteRevision
from errors import DomainError, ErrorCode
from services.ai_configuration_v1.json_codec import load_object


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    timeout_ms: int
    allow_fallback: bool
    max_retries: int
    max_cost_micros: int
    currency: str
    max_output_units: int
    temperature: float
    knowledge_max_input_units: int
    require_reported_usage: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "timeoutMs": self.timeout_ms,
            "allowFallback": self.allow_fallback,
            "maxRetries": self.max_retries,
            "maxCostMicros": self.max_cost_micros,
            "currency": self.currency,
            "maxOutputUnits": self.max_output_units,
            "temperature": self.temperature,
            "knowledgeMaxInputUnits": self.knowledge_max_input_units,
            "requireReportedUsage": self.require_reported_usage,
        }


@dataclass(frozen=True, slots=True)
class CostEstimate:
    minimum_micros: int | None
    maximum_micros: int | None
    pricing_revision: int | None


def resolve_execution_policy(
    route: CapabilityRouteRevision,
    requested: dict[str, object],
    *,
    default_timeout_seconds: int,
    config_max_retries: int,
    default_max_cost_micros: int,
) -> ExecutionPolicy:
    retry = load_object(route.retry_policy_json, label="能力路由重试策略")
    timeout_ms = _bounded_int(
        requested.get("timeoutMs", min(route.timeout_ms, default_timeout_seconds * 1_000)),
        "timeoutMs",
        minimum=1_000,
        maximum=int(route.timeout_ms),
    )
    max_retries = _bounded_int(
        requested.get("maxRetries", route.max_retries),
        "maxRetries",
        minimum=0,
        maximum=min(3, int(route.max_retries), config_max_retries),
    )
    requested_cost = _bounded_int(
        requested.get(
            "maxCostMicros",
            route.max_cost_micros or default_max_cost_micros,
        ),
        "maxCostMicros",
        minimum=0,
        maximum=10**12,
    )
    route_cost = int(route.max_cost_micros)
    max_cost = (
        min(value for value in (requested_cost, route_cost) if value > 0)
        if requested_cost > 0 and route_cost > 0
        else requested_cost or route_cost
    )
    currency = requested.get("currency", route.currency)
    if not isinstance(currency, str) or not currency.strip() or len(currency) > 16:
        raise _invalid_policy("currency")
    allow_fallback = requested.get("allowFallback", True)
    if not isinstance(allow_fallback, bool):
        raise _invalid_policy("allowFallback")
    max_output_units = _bounded_int(
        retry.get("maxOutputUnits", 1_024),
        "maxOutputUnits",
        minimum=1,
        maximum=1_000_000,
    )
    knowledge_units = _bounded_int(
        retry.get("knowledgeMaxInputUnits", 4_096),
        "knowledgeMaxInputUnits",
        minimum=1,
        maximum=1_000_000,
    )
    temperature = retry.get("temperature", 0.2)
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not math.isfinite(float(temperature))
        or not 0 <= float(temperature) <= 2
    ):
        raise _invalid_policy("temperature")
    require_usage = retry.get("requireReportedUsage", True)
    if not isinstance(require_usage, bool):
        raise _invalid_policy("requireReportedUsage")
    return ExecutionPolicy(
        timeout_ms=timeout_ms,
        allow_fallback=allow_fallback,
        max_retries=max_retries,
        max_cost_micros=max_cost,
        currency=currency.strip().upper(),
        max_output_units=max_output_units,
        temperature=float(temperature),
        knowledge_max_input_units=knowledge_units,
        require_reported_usage=require_usage,
    )


def execution_policy_from_snapshot(raw: str) -> ExecutionPolicy:
    value = load_object(raw, label="AI 执行策略快照")
    try:
        policy = ExecutionPolicy(
            timeout_ms=int(value["timeoutMs"]),
            allow_fallback=value["allowFallback"],
            max_retries=int(value["maxRetries"]),
            max_cost_micros=int(value["maxCostMicros"]),
            currency=str(value["currency"]),
            max_output_units=int(value["maxOutputUnits"]),
            temperature=float(value["temperature"]),
            knowledge_max_input_units=int(value["knowledgeMaxInputUnits"]),
            require_reported_usage=value["requireReportedUsage"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _invalid_policy("snapshot") from exc
    if (
        not isinstance(policy.allow_fallback, bool)
        or not isinstance(policy.require_reported_usage, bool)
        or policy.timeout_ms < 1
        or not 0 <= policy.max_retries <= 3
        or policy.max_cost_micros < 0
        or policy.max_output_units < 1
        or policy.knowledge_max_input_units < 1
        or not math.isfinite(policy.temperature)
        or not 0 <= policy.temperature <= 2
    ):
        raise _invalid_policy("snapshot")
    return policy


def estimate_cost(
    cost_policy: dict[str, Any],
    *,
    input_units: int,
    output_units: int,
) -> CostEstimate:
    input_rate = _optional_rate(
        cost_policy,
        "inputMicrosPerMillionUnits",
        "inputMicrosPerMillion",
    )
    output_rate = _optional_rate(
        cost_policy,
        "outputMicrosPerMillionUnits",
        "outputMicrosPerMillion",
    )
    revision = cost_policy.get("pricingRevision")
    pricing_revision = (
        revision
        if isinstance(revision, int)
        and not isinstance(revision, bool)
        and revision >= 1
        else None
    )
    if input_rate is None or output_rate is None or pricing_revision is None:
        return CostEstimate(None, None, pricing_revision)
    maximum = math.ceil(
        (input_units * input_rate + output_units * output_rate) / 1_000_000
    )
    minimum = math.ceil(input_units * input_rate / 1_000_000)
    return CostEstimate(minimum, maximum, pricing_revision)


def require_cost_within_budget(
    estimate: CostEstimate,
    *,
    budget_micros: int,
) -> None:
    if budget_micros <= 0:
        return
    if estimate.maximum_micros is None:
        raise DomainError(
            ErrorCode.AI_COST_UNAVAILABLE,
            "当前 Provider 缺少可验证定价，无法执行硬预算",
            status_code=409,
        )
    if estimate.maximum_micros > budget_micros:
        raise DomainError(
            ErrorCode.AI_COST_LIMIT_EXCEEDED,
            "本次 AI 执行的最坏成本超过预算上限",
            status_code=409,
            meta={
                "estimatedMaximumMicros": estimate.maximum_micros,
                "budgetLimitMicros": budget_micros,
            },
        )


def actual_cost_micros(
    cost_policy: dict[str, Any],
    *,
    input_units: int,
    output_units: int,
) -> CostEstimate:
    return estimate_cost(
        cost_policy,
        input_units=input_units,
        output_units=output_units,
    )


def _optional_rate(
    policy: dict[str, Any],
    primary: str,
    fallback: str,
) -> int | None:
    value = policy.get(primary, policy.get(fallback))
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    ):
        return value
    return None


def _bounded_int(
    value: object,
    field: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise _invalid_policy(field)
    return value


def _invalid_policy(field: str) -> DomainError:
    return DomainError(
        ErrorCode.AI_COST_POLICY_INVALID,
        f"AI 执行策略字段 {field} 超出允许范围",
        status_code=422,
    )


__all__ = [
    "CostEstimate",
    "ExecutionPolicy",
    "actual_cost_micros",
    "execution_policy_from_snapshot",
    "estimate_cost",
    "require_cost_within_budget",
    "resolve_execution_policy",
]
