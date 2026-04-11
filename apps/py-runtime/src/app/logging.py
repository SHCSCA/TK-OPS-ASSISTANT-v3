from __future__ import annotations

import json
import logging
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LOGGER_NAME = "tk_ops.runtime"
REQUEST_ID_CONTEXT: ContextVar[str] = ContextVar("tk_ops_request_id", default="")


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "category": getattr(record, "category", "system"),
            "requestId": getattr(record, "request_id", "") or REQUEST_ID_CONTEXT.get(),
            "message": record.getMessage(),
            "context": getattr(record, "context", {}) or {},
        }
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_dir: Path, level: str = "INFO") -> None:
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(_resolve_level(level))
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    handler = logging.FileHandler(log_dir / "runtime.jsonl", encoding="utf-8")
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)


def push_request_id(request_id: str) -> Token[str]:
    return REQUEST_ID_CONTEXT.set(request_id)


def pop_request_id(token: Token[str]) -> None:
    REQUEST_ID_CONTEXT.reset(token)


def log_event(
    category: str,
    message: str,
    *,
    level: int = logging.INFO,
    context: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.log(
        level,
        message,
        extra={
            "category": category,
            "context": context or {},
            "request_id": request_id or REQUEST_ID_CONTEXT.get(),
        },
    )

    for handler in logger.handlers:
        handler.flush()


def _resolve_level(level: str) -> int:
    normalized = level.strip().upper() or "INFO"
    return getattr(logging, normalized, logging.INFO)
