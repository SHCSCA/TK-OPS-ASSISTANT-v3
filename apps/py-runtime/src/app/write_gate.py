from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from threading import RLock

from fastapi import FastAPI, Request

from app.exception_handlers import handle_domain_error
from errors import DomainError

log = logging.getLogger(__name__)

RUNTIME_WRITE_GATE_CLOSED = "RUNTIME_WRITE_GATE_CLOSED"
SAFE_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
WriteGateTransition = Callable[[str, Mapping[str, object]], None]


class RuntimeWriteGateState(StrEnum):
    STARTUP_CLOSED = "startup_closed"
    OPEN = "open"
    SHUTDOWN_CLOSED = "shutdown_closed"
    FAILED_CLOSED = "failed_closed"


@dataclass(frozen=True, slots=True)
class RuntimeWriteGateSnapshot:
    state: RuntimeWriteGateState
    cutover_event_id: str
    reason: str

    @property
    def accepts_writes(self) -> bool:
        return self.state is RuntimeWriteGateState.OPEN

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "acceptsWrites": self.accepts_writes,
            "cutoverEventId": self.cutover_event_id,
            "reason": self.reason,
        }


class RuntimeWriteGate:
    """控制 Runtime 外部写请求，默认关闭并在 lifespan 就绪后开放。"""

    def __init__(
        self,
        *,
        cutover_event_id: str,
        transition_writer: WriteGateTransition | None = None,
    ) -> None:
        if not cutover_event_id:
            raise ValueError("Runtime 写门缺少 cutover_event_id")
        self._cutover_event_id = cutover_event_id
        self._transition_writer = transition_writer
        self._state = RuntimeWriteGateState.STARTUP_CLOSED
        self._reason = "Runtime 正在完成启动恢复与一致性检查"
        self._lock = RLock()

    def snapshot(self) -> RuntimeWriteGateSnapshot:
        with self._lock:
            return RuntimeWriteGateSnapshot(
                state=self._state,
                cutover_event_id=self._cutover_event_id,
                reason=self._reason,
            )

    def open(self) -> RuntimeWriteGateSnapshot:
        with self._lock:
            if self._state is RuntimeWriteGateState.OPEN:
                return self.snapshot()
            if self._state is RuntimeWriteGateState.FAILED_CLOSED:
                raise RuntimeError("Runtime 写门已进入失败关闭状态")
            self._record_transition(
                "write_gate_opened",
                {
                    "previousState": self._state.value,
                    "automaticRestoreAllowed": False,
                },
            )
            self._state = RuntimeWriteGateState.OPEN
            self._reason = ""
            snapshot = self.snapshot()
        log.info(
            "Runtime 写门已开放",
            extra={
                "category": "runtime",
                "operation": "write_gate.opened",
                "context": snapshot.to_dict(),
            },
        )
        return snapshot

    def close_for_shutdown(self) -> RuntimeWriteGateSnapshot:
        with self._lock:
            previous_state = self._state
            self._state = RuntimeWriteGateState.SHUTDOWN_CLOSED
            self._reason = "Runtime 正在安全停止，请稍后重试"
            snapshot = self.snapshot()
        self._record_transition_safely(
            "write_gate_closed",
            {
                "previousState": previous_state.value,
                "automaticRestoreAllowed": False,
            },
        )
        log.info(
            "Runtime 写门已因停机关闭",
            extra={
                "category": "runtime",
                "operation": "write_gate.closed",
                "context": snapshot.to_dict(),
            },
        )
        return snapshot

    def fail_closed(self, reason: str) -> RuntimeWriteGateSnapshot:
        safe_reason = reason.strip() or "Runtime 启动失败，写入已关闭"
        with self._lock:
            previous_state = self._state
            self._state = RuntimeWriteGateState.FAILED_CLOSED
            self._reason = safe_reason
            snapshot = self.snapshot()
        self._record_transition_safely(
            "write_gate_failed",
            {
                "previousState": previous_state.value,
                "reason": safe_reason,
                "automaticRestoreAllowed": False,
            },
        )
        log.error(
            "Runtime 写门保持失败关闭",
            extra={
                "category": "runtime",
                "operation": "write_gate.failed_closed",
                "context": snapshot.to_dict(),
            },
        )
        return snapshot

    def require_write_allowed(self) -> None:
        snapshot = self.snapshot()
        if snapshot.accepts_writes:
            return
        raise DomainError(
            RUNTIME_WRITE_GATE_CLOSED,
            snapshot.reason or "Runtime 暂不接受写入，请稍后重试",
            status_code=503,
            meta={
                "state": snapshot.state.value,
                "cutoverEventId": snapshot.cutover_event_id,
                "retryable": snapshot.state
                is not RuntimeWriteGateState.FAILED_CLOSED,
            },
            loggable=True,
            headers={"Retry-After": "1"},
            log_context={
                "writeGateState": snapshot.state.value,
                "cutoverEventId": snapshot.cutover_event_id,
            },
        )

    def _record_transition(
        self,
        stage: str,
        evidence: Mapping[str, object],
    ) -> None:
        if self._transition_writer is not None:
            self._transition_writer(stage, evidence)

    def _record_transition_safely(
        self,
        stage: str,
        evidence: Mapping[str, object],
    ) -> None:
        try:
            self._record_transition(stage, evidence)
        except Exception:
            log.exception(
                "Runtime 写门切换证据写入失败",
                extra={
                    "stage": stage,
                    "cutover_event_id": self._cutover_event_id,
                },
            )


def install_runtime_write_gate_middleware(
    app: FastAPI,
    write_gate: RuntimeWriteGate,
) -> None:
    @app.middleware("http")
    async def runtime_write_gate_middleware(  # type: ignore[no-untyped-def]
        request: Request,
        call_next,
    ):
        if request.method.upper() in SAFE_HTTP_METHODS:
            return await call_next(request)
        try:
            write_gate.require_write_allowed()
        except DomainError as exc:
            return await handle_domain_error(request, exc)
        return await call_next(request)
