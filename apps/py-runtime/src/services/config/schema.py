from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from config.migration import (
    MIGRATION_BACKUP_RETENTION_DEFAULT,
    is_valid_migration_backup_retention,
)
from errors import FieldError
from services.config.schema_ai_execution import (
    AI_EXECUTION_DEFAULTS,
    AI_EXECUTION_RESTART_KEYS,
    AI_EXECUTION_RULE_SPECS,
    validate_ai_execution_relationships,
)


API_PAGINATION_LIMIT_MINIMUM = 1
API_PAGINATION_LIMIT_MAXIMUM = 1_000
MUTATION_IDEMPOTENCY_TTL_MINIMUM = 3_600
MUTATION_IDEMPOTENCY_TTL_MAXIMUM = 2_592_000
KNOWLEDGE_INDEX_SOURCE_BYTES_MINIMUM = 1_048_576
KNOWLEDGE_INDEX_SOURCE_BYTES_MAXIMUM = 104_857_600
KNOWLEDGE_INDEX_URL_TIMEOUT_MINIMUM = 1
KNOWLEDGE_INDEX_URL_TIMEOUT_MAXIMUM = 120
KNOWLEDGE_INDEX_REDIRECTS_MINIMUM = 0
KNOWLEDGE_INDEX_REDIRECTS_MAXIMUM = 10


@dataclass(frozen=True, slots=True)
class ConfigRule:
    validator: Callable[[object], bool]
    message: str


def _is_string(value: object) -> bool:
    return isinstance(value, str) and len(value) <= 1024


def _is_positive_int(
    value: object,
    *,
    minimum: int,
    maximum: int,
) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    )


WRITABLE_RULES: dict[str, ConfigRule] = {
    "logging.level": ConfigRule(
        lambda value: value in {"DEBUG", "INFO", "WARNING", "ERROR"},
        "日志级别必须为 DEBUG、INFO、WARNING 或 ERROR",
    ),
    "media.ffprobePath": ConfigRule(_is_string, "FFprobe 路径格式无效"),
    "media.ffmpegPath": ConfigRule(_is_string, "FFmpeg 路径格式无效"),
    "browser.executablePath": ConfigRule(_is_string, "浏览器路径格式无效"),
    "browser.startTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=1, maximum=120),
        "浏览器启动超时必须为 1 至 120 秒",
    ),
    "browser.stopTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=1, maximum=60),
        "浏览器停止超时必须为 1 至 60 秒",
    ),
    "browser.healthTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=1, maximum=60),
        "浏览器检查超时必须为 1 至 60 秒",
    ),
    "execution.provisionTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=10, maximum=600),
        "执行环境创建超时必须为 10 至 600 秒",
    ),
    "execution.cleanupTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=5, maximum=300),
        "执行环境清理超时必须为 5 至 300 秒",
    ),
    "execution.recoveryTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=10, maximum=600),
        "执行环境恢复超时必须为 10 至 600 秒",
    ),
    "connection.loginSessionTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=60, maximum=3_600),
        "登录会话超时必须为 60 至 3600 秒",
    ),
    "connection.probeTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=5, maximum=120),
        "登录探测超时必须为 5 至 120 秒",
    ),
    "connection.cancelTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=5, maximum=120),
        "登录取消超时必须为 5 至 120 秒",
    ),
    "machineIdentity.factorTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=1, maximum=60),
        "机器身份因子采集超时必须为 1 至 60 秒",
    ),
    "machineIdentity.factorRetryAttempts": ConfigRule(
        lambda value: _is_positive_int(value, minimum=0, maximum=5),
        "机器身份因子重试次数必须为 0 至 5",
    ),
    "machineIdentity.degradedRecheckSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=30, maximum=86_400),
        "机器身份降级复检间隔必须为 30 至 86400 秒",
    ),
    "runtime.taskTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=1,
            maximum=86_400,
        ),
        "任务超时必须为 1 至 86400 秒",
    ),
    "runtime.taskMaxTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=1,
            maximum=604_800,
        ),
        "任务最大超时必须为 1 至 604800 秒",
    ),
    "runtime.taskSnapshotMaxBytes": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=1_024,
            maximum=1_048_576,
        ),
        "任务快照上限必须为 1024 至 1048576 字节",
    ),
    "runtime.taskMaxConcurrency": ConfigRule(
        lambda value: _is_positive_int(value, minimum=1, maximum=32),
        "任务并发上限必须为 1 至 32",
    ),
    "http.retry.maxAttempts": ConfigRule(
        lambda value: _is_positive_int(value, minimum=0, maximum=10),
        "HTTP 重试次数必须为 0 至 10",
    ),
    "http.retry.baseDelayMs": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=50,
            maximum=60_000,
        ),
        "HTTP 重试基础等待必须为 50 至 60000 毫秒",
    ),
    "websocket.reconnect.maxDelayMs": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=100,
            maximum=60_000,
        ),
        "WebSocket 重连等待必须为 100 至 60000 毫秒",
    ),
    "websocket.replayLimit": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=10,
            maximum=10_000,
        ),
        "WebSocket 事件重放上限必须为 10 至 10000 条",
    ),
    "websocket.publishBatchSize": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=1,
            maximum=1_000,
        ),
        "WebSocket 事件发布批次必须为 1 至 1000 条",
    ),
    "websocket.publishIntervalMs": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=50,
            maximum=10_000,
        ),
        "WebSocket 事件发布间隔必须为 50 至 10000 毫秒",
    ),
    "websocket.subscribeTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=1, maximum=60),
        "WebSocket 首帧超时必须为 1 至 60 秒",
    ),
    "websocket.sendTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=1, maximum=60),
        "WebSocket 发送超时必须为 1 至 60 秒",
    ),
    "websocket.closeTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(value, minimum=1, maximum=30),
        "WebSocket 关闭超时必须为 1 至 30 秒",
    ),
    "websocket.maxMessageBytes": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=1_024,
            maximum=1_048_576,
        ),
        "WebSocket 消息上限必须为 1024 至 1048576 字节",
    ),
    "websocket.legacyMaxMessageBytes": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=256,
            maximum=65_536,
        ),
        "legacy WebSocket 消息上限必须为 256 至 65536 字节",
    ),
    "migration.backupRetention": ConfigRule(
        is_valid_migration_backup_retention,
        "迁移备份保留数量必须为 1 至 50",
    ),
    "provider.defaultTimeoutMs": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=1_000,
            maximum=600_000,
        ),
        "Provider 超时必须为 1000 至 600000 毫秒",
    ),
    "provider.maxConcurrency": ConfigRule(
        lambda value: _is_positive_int(value, minimum=1, maximum=32),
        "Provider 并发数必须为 1 至 32",
    ),
    "accounts.requiredCapabilities": ConfigRule(
        lambda value: (
            isinstance(value, list)
            and len(value) <= 32
            and all(
                isinstance(item, str) and 0 < len(item) <= 128
                for item in value
            )
        ),
        "账号必需能力必须为不超过 32 项的能力标识列表",
    ),
    "api.paginationDefaultLimit": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=API_PAGINATION_LIMIT_MINIMUM,
            maximum=API_PAGINATION_LIMIT_MAXIMUM,
        ),
        "API 默认分页条数必须为 1 至 1000",
    ),
    "api.paginationMaxLimit": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=API_PAGINATION_LIMIT_MINIMUM,
            maximum=API_PAGINATION_LIMIT_MAXIMUM,
        ),
        "API 最大分页条数必须为 1 至 1000",
    ),
    "api.mutationIdempotencyTtlSeconds": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=MUTATION_IDEMPOTENCY_TTL_MINIMUM,
            maximum=MUTATION_IDEMPOTENCY_TTL_MAXIMUM,
        ),
        "普通写操作幂等保留时间必须为 3600 至 2592000 秒",
    ),
    "knowledge.index.maxSourceBytes": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=KNOWLEDGE_INDEX_SOURCE_BYTES_MINIMUM,
            maximum=KNOWLEDGE_INDEX_SOURCE_BYTES_MAXIMUM,
        ),
        "知识索引单来源上限必须为 1048576 至 104857600 字节",
    ),
    "knowledge.index.urlTimeoutSeconds": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=KNOWLEDGE_INDEX_URL_TIMEOUT_MINIMUM,
            maximum=KNOWLEDGE_INDEX_URL_TIMEOUT_MAXIMUM,
        ),
        "知识索引 URL 超时必须为 1 至 120 秒",
    ),
    "knowledge.index.maxRedirects": ConfigRule(
        lambda value: _is_positive_int(
            value,
            minimum=KNOWLEDGE_INDEX_REDIRECTS_MINIMUM,
            maximum=KNOWLEDGE_INDEX_REDIRECTS_MAXIMUM,
        ),
        "知识索引 URL 重定向次数必须为 0 至 10",
    ),
    "ui.theme": ConfigRule(
        lambda value: value in {"light", "dark", "system"},
        "主题必须为 light、dark 或 system",
    ),
    "ui.lastAccountId": ConfigRule(
        lambda value: value is None
        or (isinstance(value, str) and 0 < len(value) <= 128),
        "最近账号标识格式无效",
    ),
    "ui.recentPages": ConfigRule(
        lambda value: (
            isinstance(value, Mapping)
            and len(value) <= 200
            and all(
                isinstance(key, str)
                and 0 < len(key) <= 128
                and isinstance(item, str)
                and 0 < len(item) <= 256
                for key, item in value.items()
            )
        ),
        "账号最近页面配置格式无效",
    ),
    "ui.compactWindow": ConfigRule(
        lambda value: isinstance(value, bool),
        "紧凑窗口配置必须为布尔值",
    ),
}
WRITABLE_RULES.update(
    {
        key: ConfigRule(validator, message)
        for key, (validator, message) in AI_EXECUTION_RULE_SPECS.items()
    }
)

DEFAULT_VALUES: dict[str, object] = {
    "logging.level": "INFO",
    "media.ffprobePath": "",
    "media.ffmpegPath": "",
    "browser.executablePath": "",
    "browser.startTimeoutSeconds": 30,
    "browser.stopTimeoutSeconds": 15,
    "browser.healthTimeoutSeconds": 10,
    "execution.provisionTimeoutSeconds": 120,
    "execution.cleanupTimeoutSeconds": 30,
    "execution.recoveryTimeoutSeconds": 120,
    "connection.loginSessionTimeoutSeconds": 600,
    "connection.probeTimeoutSeconds": 20,
    "connection.cancelTimeoutSeconds": 30,
    "machineIdentity.factorTimeoutSeconds": 10,
    "machineIdentity.factorRetryAttempts": 1,
    "machineIdentity.degradedRecheckSeconds": 300,
    "runtime.taskTimeoutSeconds": 900,
    "runtime.taskMaxTimeoutSeconds": 86_400,
    "runtime.taskSnapshotMaxBytes": 262_144,
    "runtime.taskMaxConcurrency": 4,
    "http.retry.maxAttempts": 3,
    "http.retry.baseDelayMs": 500,
    "websocket.reconnect.maxDelayMs": 30_000,
    "websocket.replayLimit": 500,
    "websocket.publishBatchSize": 100,
    "websocket.publishIntervalMs": 250,
    "websocket.subscribeTimeoutSeconds": 10,
    "websocket.sendTimeoutSeconds": 5,
    "websocket.closeTimeoutSeconds": 3,
    "websocket.maxMessageBytes": 65_536,
    "websocket.legacyMaxMessageBytes": 4_096,
    "migration.backupRetention": MIGRATION_BACKUP_RETENTION_DEFAULT,
    "provider.defaultTimeoutMs": 120_000,
    "provider.maxConcurrency": 4,
    "accounts.requiredCapabilities": [
        "script_generation",
        "storyboard_generation",
        "text_to_video",
    ],
    "api.paginationDefaultLimit": 50,
    "api.paginationMaxLimit": 200,
    "api.mutationIdempotencyTtlSeconds": 604_800,
    "knowledge.index.maxSourceBytes": 20_971_520,
    "knowledge.index.urlTimeoutSeconds": 15,
    "knowledge.index.maxRedirects": 3,
    "ui.theme": "system",
    "ui.lastAccountId": None,
    "ui.recentPages": {},
    "ui.compactWindow": False,
}
DEFAULT_VALUES.update(AI_EXECUTION_DEFAULTS)

RESTART_REQUIRED_KEYS: tuple[str, ...] = (
    "browser.executablePath",
    "machineIdentity.factorTimeoutSeconds",
    "machineIdentity.factorRetryAttempts",
    "machineIdentity.degradedRecheckSeconds",
    "migration.backupRetention",
    "provider.defaultTimeoutMs",
    "provider.maxConcurrency",
    "runtime.taskMaxConcurrency",
    "runtime.taskMaxTimeoutSeconds",
    "runtime.taskSnapshotMaxBytes",
    "runtime.taskTimeoutSeconds",
    "websocket.legacyMaxMessageBytes",
    "websocket.closeTimeoutSeconds",
    "websocket.maxMessageBytes",
    "websocket.publishBatchSize",
    "websocket.publishIntervalMs",
    "websocket.replayLimit",
    "websocket.sendTimeoutSeconds",
    "websocket.subscribeTimeoutSeconds",
)
RESTART_REQUIRED_KEYS += AI_EXECUTION_RESTART_KEYS

LEGACY_READ_PATHS: tuple[str, ...] = (
    "runtime.mode",
    "runtime.workspaceRoot",
    "paths.cacheDir",
    "paths.exportDir",
    "paths.logDir",
    "logging.level",
    "media.ffprobePath",
    "media.ffmpegPath",
    "browser.executablePath",
)


def validate_config_relationships(
    values: Mapping[str, object],
) -> list[FieldError]:
    errors: list[FieldError] = []
    default_timeout = values.get("runtime.taskTimeoutSeconds")
    maximum_timeout = values.get("runtime.taskMaxTimeoutSeconds")
    if (
        isinstance(default_timeout, int)
        and isinstance(maximum_timeout, int)
        and default_timeout > maximum_timeout
    ):
        errors.append(
            FieldError(
                field="values.runtime.taskMaxTimeoutSeconds",
                code="invalid_relationship",
                message="任务最大超时不得小于默认任务超时",
            )
        )

    default_limit = values.get("api.paginationDefaultLimit")
    maximum_limit = values.get("api.paginationMaxLimit")
    if (
        isinstance(default_limit, int)
        and isinstance(maximum_limit, int)
        and default_limit > maximum_limit
    ):
        errors.append(
            FieldError(
                field="values.api.paginationMaxLimit",
                code="invalid_relationship",
                message="API 最大分页条数不得小于默认分页条数",
            )
        )

    errors.extend(
        validate_ai_execution_relationships(
            values,
            task_maximum_timeout=maximum_timeout,
        )
    )
    return errors


def validate_config_schema() -> None:
    missing_defaults = sorted(set(WRITABLE_RULES) - set(DEFAULT_VALUES))
    unexpected_defaults = sorted(set(DEFAULT_VALUES) - set(WRITABLE_RULES))
    invalid_defaults = sorted(
        key
        for key, rule in WRITABLE_RULES.items()
        if key in DEFAULT_VALUES and not rule.validator(DEFAULT_VALUES[key])
    )
    invalid_restart_keys = sorted(
        set(RESTART_REQUIRED_KEYS) - set(WRITABLE_RULES)
    )
    invalid_default_relationships = [
        item.field for item in validate_config_relationships(DEFAULT_VALUES)
    ]
    if (
        missing_defaults
        or unexpected_defaults
        or invalid_defaults
        or invalid_restart_keys
        or invalid_default_relationships
    ):
        raise RuntimeError(
            "配置总线 Schema 无效："
            f"缺少默认值={missing_defaults}，"
            f"多余默认值={unexpected_defaults}，"
            f"非法默认值={invalid_defaults}，"
            f"非法重启项={invalid_restart_keys}，"
            f"非法默认关系={invalid_default_relationships}"
        )


validate_config_schema()
