from __future__ import annotations

from collections.abc import Callable, Mapping

from errors import FieldError

RuleSpec = tuple[Callable[[object], bool], str]


def _bounded_int(value: object, minimum: int, maximum: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    )


AI_EXECUTION_RULE_SPECS: dict[str, RuleSpec] = {
    "ai.execution.enabled": (
        lambda value: isinstance(value, bool),
        "AI 执行开关必须为布尔值",
    ),
    "ai.execution.defaultTimeoutSeconds": (
        lambda value: _bounded_int(value, 1, 86_400),
        "AI 执行默认超时必须为 1 至 86400 秒",
    ),
    "ai.execution.maxRetries": (
        lambda value: _bounded_int(value, 0, 3),
        "AI 执行重试次数必须为 0 至 3",
    ),
    "ai.execution.retryBaseDelayMs": (
        lambda value: _bounded_int(value, 100, 10_000),
        "AI 执行重试基础等待必须为 100 至 10000 毫秒",
    ),
    "ai.execution.retryMaxDelayMs": (
        lambda value: _bounded_int(value, 100, 60_000),
        "AI 执行重试最大等待必须为 100 至 60000 毫秒",
    ),
    "ai.execution.globalMaxConcurrency": (
        lambda value: _bounded_int(value, 1, 32),
        "AI 执行全局并发数必须为 1 至 32",
    ),
    "ai.execution.defaultMaxCostMicros": (
        lambda value: _bounded_int(value, 0, 10**12),
        "AI 执行默认成本上限必须为非负整数",
    ),
    "ai.execution.outputMaxBytes": (
        lambda value: _bounded_int(value, 1_024, 104_857_600),
        "AI 执行输出上限必须为 1024 至 104857600 字节",
    ),
    "ai.providerValidation.maxOutputUnits": (
        lambda value: _bounded_int(value, 1, 32),
        "Provider 验证输出上限必须为 1 至 32",
    ),
    "knowledge.controlledFiles.maxBytes": (
        lambda value: _bounded_int(value, 1_024, 1_073_741_824),
        "受控文件上限必须为 1024 至 1073741824 字节",
    ),
    "knowledge.controlledFiles.grantRetentionHours": (
        lambda value: _bounded_int(value, 1, 8_760),
        "受控文件授权保留时间必须为 1 至 8760 小时",
    ),
    "ai.evidence.retentionDays": (
        lambda value: _bounded_int(value, 1, 3_650),
        "AI 证据保留时间必须为 1 至 3650 天",
    ),
}

AI_EXECUTION_DEFAULTS: dict[str, object] = {
    "ai.execution.enabled": False,
    "ai.execution.defaultTimeoutSeconds": 120,
    "ai.execution.maxRetries": 1,
    "ai.execution.retryBaseDelayMs": 500,
    "ai.execution.retryMaxDelayMs": 5_000,
    "ai.execution.globalMaxConcurrency": 4,
    "ai.execution.defaultMaxCostMicros": 0,
    "ai.execution.outputMaxBytes": 1_048_576,
    "ai.providerValidation.maxOutputUnits": 8,
    "knowledge.controlledFiles.maxBytes": 20_971_520,
    "knowledge.controlledFiles.grantRetentionHours": 168,
    "ai.evidence.retentionDays": 30,
}

AI_EXECUTION_RESTART_KEYS = tuple(AI_EXECUTION_DEFAULTS)


def validate_ai_execution_relationships(
    values: Mapping[str, object],
    *,
    task_maximum_timeout: object,
) -> list[FieldError]:
    errors: list[FieldError] = []
    ai_timeout = values.get("ai.execution.defaultTimeoutSeconds")
    if (
        isinstance(ai_timeout, int)
        and isinstance(task_maximum_timeout, int)
        and ai_timeout > task_maximum_timeout
    ):
        errors.append(
            FieldError(
                field="values.ai.execution.defaultTimeoutSeconds",
                code="invalid_relationship",
                message="AI 执行默认超时不得超过任务最大超时",
            )
        )
    retry_base = values.get("ai.execution.retryBaseDelayMs")
    retry_max = values.get("ai.execution.retryMaxDelayMs")
    if (
        isinstance(retry_base, int)
        and isinstance(retry_max, int)
        and retry_max < retry_base
    ):
        errors.append(
            FieldError(
                field="values.ai.execution.retryMaxDelayMs",
                code="invalid_relationship",
                message="AI 执行最大重试等待不得小于基础等待",
            )
        )
    return errors
