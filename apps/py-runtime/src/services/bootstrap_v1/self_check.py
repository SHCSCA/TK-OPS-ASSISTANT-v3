from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from errors import DomainError, ErrorCode
from services.diagnostics import RuntimeDiagnosticsService
from services.tasks.types import (
    JsonValue,
    TaskExecutionContext,
    TaskExecutionResult,
    TaskHandler,
)

log = logging.getLogger(__name__)

_SUPPORTED_CHECKS = frozenset(
    {"database", "directories", "media_tools", "runtime"}
)


def build_bootstrap_self_check_handler(
    *,
    diagnostics_service: RuntimeDiagnosticsService,
    session_factory: sessionmaker[Session],
) -> TaskHandler:
    async def handle(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult | None:
        checks = _parse_checks(payload)
        diagnostics = await asyncio.to_thread(
            diagnostics_service.get_diagnostics
        )
        for index, check in enumerate(checks, start=1):
            context.raise_if_cancelled()
            await asyncio.to_thread(
                _run_check,
                check,
                diagnostics=diagnostics,
                session_factory=session_factory,
            )
            await context.report_progress(index / len(checks))
        return TaskExecutionResult()

    return handle


def _parse_checks(payload: Mapping[str, JsonValue]) -> tuple[str, ...]:
    raw_checks = payload.get("checks")
    if not isinstance(raw_checks, list):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "Runtime 自检项格式无效",
            status_code=422,
        )
    checks = tuple(
        str(item)
        for item in raw_checks
        if isinstance(item, str) and item in _SUPPORTED_CHECKS
    )
    if not checks or len(checks) != len(raw_checks):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "Runtime 自检项包含不受支持的检查",
            status_code=422,
        )
    return checks


def _run_check(
    check: str,
    *,
    diagnostics: Mapping[str, object],
    session_factory: sessionmaker[Session],
) -> None:
    if check == "database":
        _check_database(session_factory)
        return

    diagnostic_key = "mediaTools" if check == "media_tools" else check
    section = diagnostics.get(diagnostic_key)
    status = (
        str(section.get("status"))
        if isinstance(section, Mapping)
        else "failed"
    )
    if check == "media_tools" and status in {"ready", "attention"}:
        return
    if status == "ready":
        return
    log.warning(
        "Runtime 自检项未通过",
        extra={"stage": check, "status": status},
    )
    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        f"Runtime 自检未通过：{check}",
        status_code=503,
        log_context={"stage": check, "status": status},
    )


def _check_database(
    session_factory: sessionmaker[Session],
) -> None:
    try:
        with session_factory() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:
        log.exception("Runtime 数据库自检失败")
        raise DomainError(
            ErrorCode.RUNTIME_NOT_READY,
            "Runtime 数据库自检未通过",
            status_code=503,
            loggable=True,
            log_context={"stage": "database"},
        ) from exc
