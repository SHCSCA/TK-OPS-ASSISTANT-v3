from __future__ import annotations

import json
import logging
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.log_redaction import (
    LOCAL_PATH_MARKER as LOCAL_PATH_MARKER,
    REDACTION_MARKER as REDACTION_MARKER,
    SAFE_ROUTE_CONTEXT_KEYS as SAFE_ROUTE_CONTEXT_KEYS,
    SAFE_TRACE_METADATA_KEYS as SAFE_TRACE_METADATA_KEYS,
    SENSITIVE_KEY_PARTS as SENSITIVE_KEY_PARTS,
    redact_log_text,
    redact_log_value,
    safe_exception_summary as _safe_exception_summary,
)

LOGGER_NAME = "tk_ops.runtime"
REQUEST_ID_CONTEXT: ContextVar[str] = ContextVar("tk_ops_request_id", default="")
LOG_CONTEXT: ContextVar[dict[str, object] | None] = ContextVar(
    "tk_ops_log_context",
    default=None,
)
HANDLER_MARKER = "_tk_ops_runtime_handler"
STRUCTURED_CONTEXT_KEYS: tuple[str, ...] = (
    "operation_id",
    "log_id",
    "account_id",
    "resource_type",
    "resource_id",
    "task_id",
    "stage",
    "duration_ms",
    "provider_profile_id",
    "model_profile_id",
    "capability_key",
    "prompt_profile_id",
    "prompt_version",
    "config_revision",
    "error_code",
    "retry_of",
)
class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        inherited_context = LOG_CONTEXT.get() or {}
        request_id = (
            getattr(record, "request_id", "")
            or REQUEST_ID_CONTEXT.get()
            or inherited_context.get("request_id", "")
        )
        structured_context = {
            key: getattr(record, key, inherited_context.get(key))
            for key in STRUCTURED_CONTEXT_KEYS
        }
        event_context = redact_log_value(getattr(record, "context", {}) or {})
        payload = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "module": record.name,
            "operation": getattr(record, "operation", None),
            "request_id": request_id,
            **structured_context,
            "logger": record.name,
            "category": getattr(record, "category", "system"),
            "requestId": request_id,
            "message": redact_log_text(record.getMessage()),
            "context": event_context,
        }
        if record.exc_info is not None:
            payload["exception"] = _safe_exception_summary(record.exc_info)
        safe_payload = redact_log_value(payload)
        return json.dumps(safe_payload, ensure_ascii=False)


def configure_logging(log_dir: Path, level: str = "INFO") -> None:
    log_dir.mkdir(parents=True, exist_ok=True)

    resolved_level = _resolve_level(level)
    root_logger = logging.getLogger()
    handler = logging.FileHandler(log_dir / "runtime.jsonl", encoding="utf-8")
    handler.setLevel(resolved_level)
    handler.setFormatter(JsonLogFormatter())
    setattr(handler, HANDLER_MARKER, True)

    # 新输出成功打开后再替换旧处理器，避免重配置失败时丢失启动日志。
    shutdown_logging()
    root_logger.setLevel(resolved_level)
    root_logger.addHandler(handler)

    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    logger.setLevel(resolved_level)
    logger.propagate = True


def shutdown_logging() -> None:
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if not getattr(handler, HANDLER_MARKER, False):
            continue
        root_logger.removeHandler(handler)
        handler.close()


def push_request_id(request_id: str) -> Token[str]:
    return REQUEST_ID_CONTEXT.set(request_id)


def pop_request_id(token: Token[str]) -> None:
    REQUEST_ID_CONTEXT.reset(token)


def push_log_context(**values: object) -> Token[dict[str, object] | None]:
    current = LOG_CONTEXT.get() or {}
    merged = dict(current)
    merged.update(
        {
            key: value
            for key, value in values.items()
            if value is not None
        }
    )
    return LOG_CONTEXT.set(merged)


def pop_log_context(token: Token[dict[str, object] | None]) -> None:
    try:
        LOG_CONTEXT.reset(token)
    except ValueError:
        # FastAPI 可能在独立异步上下文中关闭依赖生成器，需在该上下文恢复旧值。
        previous = token.old_value
        LOG_CONTEXT.set(
            None if previous is Token.MISSING else previous
        )
        logging.getLogger(__name__).warning(
            "日志上下文已在独立异步上下文中安全恢复"
        )


def log_event(
    category: str,
    message: str,
    *,
    level: int = logging.INFO,
    context: dict[str, Any] | None = None,
    request_id: str | None = None,
    operation_id: str | None = None,
    log_id: str | None = None,
    error_code: str | None = None,
    account_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    task_id: str | None = None,
    stage: str | None = None,
) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.log(
        level,
        message,
        extra={
            "category": category,
            "operation": message,
            "context": redact_log_value(context or {}),
            "request_id": request_id or REQUEST_ID_CONTEXT.get(),
            "operation_id": operation_id,
            "log_id": log_id,
            "error_code": error_code,
            "account_id": account_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "task_id": task_id,
            "stage": stage,
        },
    )

    for handler in logging.getLogger().handlers:
        if getattr(handler, HANDLER_MARKER, False):
            handler.flush()


def _resolve_level(level: str) -> int:
    normalized = level.strip().upper() or "INFO"
    return getattr(logging, normalized, logging.INFO)
