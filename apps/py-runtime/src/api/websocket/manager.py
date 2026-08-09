from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Literal

from fastapi import WebSocket

from api.websocket.models import (
    ProtocolErrorFrame,
    SubscribeFrame,
    SubscribedFrame,
    SubscribedTopicFrame,
    SyncRequiredFrame,
    frame_payload,
)
from api.websocket.session import WebSocketAccessContext, WebSocketSessionSnapshot
from services.events import (
    AccountScopeMismatchError,
    CursorMismatchError,
    EventValidationError,
    RuntimeEventDto,
    RuntimeEventService,
    TopicCursor,
    is_legacy_system_event,
    parse_topic,
    to_legacy_payload,
    validate_stable_id,
)

log = logging.getLogger(__name__)

AccountSubscriptionAuthorizer = Callable[
    [WebSocketAccessContext, str],
    Awaitable[None],
]
ConnectionMode = Literal["v1", "legacy"]


@dataclass(slots=True)
class _ConnectionState:
    websocket: WebSocket
    access: WebSocketAccessContext
    mode: ConnectionMode
    account_id: str | None = None
    subscription_revision: int = 0
    topics: frozenset[str] = field(default_factory=frozenset)
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    close_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    disconnected: bool = False


class RuntimeWebSocketManager:
    """维护 v1 订阅世代，并严格按 Topic 隔离实时事件。"""

    def __init__(
        self,
        event_service: RuntimeEventService,
        *,
        authorize_account: AccountSubscriptionAuthorizer | None = None,
        send_timeout_seconds: float = 5.0,
        close_timeout_seconds: float = 3.0,
    ) -> None:
        if send_timeout_seconds <= 0:
            raise ValueError("WebSocket 发送超时必须大于 0")
        if close_timeout_seconds <= 0:
            raise ValueError("WebSocket 关闭超时必须大于 0")
        self._event_service = event_service
        self._authorize_account = authorize_account
        self._send_timeout_seconds = send_timeout_seconds
        self._close_timeout_seconds = close_timeout_seconds
        self._connections: dict[int, _ConnectionState] = {}
        self._connections_lock = asyncio.Lock()
        self._topic_locks: dict[str, asyncio.Lock] = {}

    async def register_v1(
        self,
        websocket: WebSocket,
        access: WebSocketAccessContext,
    ) -> None:
        await self._register(websocket, access, mode="v1")

    async def register_legacy(
        self,
        websocket: WebSocket,
        access: WebSocketAccessContext,
    ) -> None:
        await self._register(websocket, access, mode="legacy")

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._connections_lock:
            removed = self._connections.pop(id(websocket), None)
        if removed is not None:
            log.info(
                "WebSocket 会话已移除",
                extra={
                    "session_id": removed.access.session_id,
                    "mode": removed.mode,
                    "account_id": removed.account_id,
                },
            )

    async def subscribe(
        self,
        websocket: WebSocket,
        frame: SubscribeFrame,
    ) -> WebSocketSessionSnapshot:
        state = await self._require_state(websocket, mode="v1")
        if frame.subscription_revision <= state.subscription_revision:
            raise CursorMismatchError("订阅修订必须高于当前订阅世代。")

        cursors = self._validate_subscription_scope(state, frame)
        if frame.account_id is not None:
            validate_stable_id(frame.account_id, "账号 ID")
            if self._authorize_account is None:
                raise AccountScopeMismatchError("账号订阅门禁尚未接入。")
            await self._authorize_account(state.access, frame.account_id)

        topics = tuple(sorted(cursor.topic for cursor in cursors))
        locked_topics = tuple(sorted(set(topics) | set(state.topics)))
        async with self._lock_topics(locked_topics):
            resolutions = [
                self._event_service.resolve_replay(cursor) for cursor in cursors
            ]
            subscribed_topics = [
                SubscribedTopicFrame(
                    topic=item.topic,
                    currentSequence=item.current_sequence,
                    replayedCount=len(item.events),
                )
                for item in resolutions
            ]
            await self._send_state(
                state,
                frame_payload(
                    SubscribedFrame(
                        subscriptionRevision=frame.subscription_revision,
                        topics=subscribed_topics,
                    )
                ),
            )

            active_topics: set[str] = set()
            for item in resolutions:
                if item.sync_required:
                    await self._send_state(
                        state,
                        frame_payload(
                            SyncRequiredFrame(
                                subscriptionRevision=frame.subscription_revision,
                                topic=item.topic,
                                currentSequence=item.current_sequence,
                            )
                        ),
                    )
                    continue
                for event in item.events:
                    await self._send_state(state, event.to_payload())
                active_topics.add(item.topic)

            state.account_id = frame.account_id
            state.subscription_revision = frame.subscription_revision
            state.topics = frozenset(active_topics)

        return self._snapshot(state)

    async def publish(self, event: RuntimeEventDto) -> None:
        parsed = parse_topic(event.topic)
        if parsed.account_id != event.account_id:
            raise AccountScopeMismatchError()

        async with self._lock_topics((event.topic,)):
            async with self._connections_lock:
                states = tuple(self._connections.values())

            deliveries: list[tuple[_ConnectionState, dict[str, object]]] = []
            for state in states:
                if state.mode == "v1" and event.topic in state.topics:
                    deliveries.append((state, event.to_payload()))
                    continue
                if state.mode == "legacy" and is_legacy_system_event(event):
                    deliveries.append((state, to_legacy_payload(event)))

            results = await asyncio.gather(
                *(
                    self._send_state(state, payload)
                    for state, payload in deliveries
                ),
                return_exceptions=True,
            )
            for (state, _), result in zip(deliveries, results, strict=True):
                if isinstance(result, Exception):
                    log.error(
                        "WebSocket 事件投递失败",
                        extra={
                            "session_id": state.access.session_id,
                            "topic": event.topic,
                            "event_id": event.event_id,
                            "error_type": type(result).__name__,
                        },
                    )
                    await self.unregister(state.websocket)

    async def send_protocol_error(
        self,
        websocket: WebSocket,
        *,
        error_code: str,
        message: str,
        subscription_revision: int | None = None,
    ) -> None:
        state = await self._require_state(websocket)
        await self._send_state(
            state,
            frame_payload(
                ProtocolErrorFrame(
                    errorCode=error_code,
                    message=message,
                    subscriptionRevision=subscription_revision,
                )
            ),
        )

    async def send_pong(self, websocket: WebSocket) -> None:
        state = await self._require_state(websocket, mode="v1")
        await self._send_state(state, {"type": "pong"})

    async def get_snapshot(
        self,
        websocket: WebSocket,
    ) -> WebSocketSessionSnapshot | None:
        async with self._connections_lock:
            state = self._connections.get(id(websocket))
            return self._snapshot(state) if state is not None else None

    async def _register(
        self,
        websocket: WebSocket,
        access: WebSocketAccessContext,
        *,
        mode: ConnectionMode,
    ) -> None:
        state = _ConnectionState(
            websocket=websocket,
            access=access,
            mode=mode,
        )
        async with self._connections_lock:
            self._connections[id(websocket)] = state
        log.info(
            "WebSocket 会话已注册",
            extra={"session_id": access.session_id, "mode": mode},
        )

    async def _require_state(
        self,
        websocket: WebSocket,
        *,
        mode: ConnectionMode | None = None,
    ) -> _ConnectionState:
        async with self._connections_lock:
            state = self._connections.get(id(websocket))
        if state is None or (mode is not None and state.mode != mode):
            raise EventValidationError("WebSocket 会话状态无效。")
        return state

    def _validate_subscription_scope(
        self,
        state: _ConnectionState,
        frame: SubscribeFrame,
    ) -> tuple[TopicCursor, ...]:
        seen: set[str] = set()
        cursors: list[TopicCursor] = []
        for item in frame.topics:
            if item.topic in seen:
                raise EventValidationError("同一订阅帧不得包含重复 Topic。")
            seen.add(item.topic)
            parsed = parse_topic(item.topic)
            if parsed.value != item.topic:
                raise EventValidationError("Topic 不得包含首尾空白。")
            if parsed.scope == "system":
                if parsed.value not in state.access.allowed_system_topics:
                    raise AccountScopeMismatchError("当前会话无权订阅该系统 Topic。")
            elif frame.account_id is None or parsed.account_id != frame.account_id:
                raise AccountScopeMismatchError()
            cursors.append(
                TopicCursor(
                    topic=parsed.value,
                    last_event_id=item.last_event_id,
                    after_sequence=item.after_sequence,
                )
            )
        return tuple(cursors)

    async def _send_state(
        self,
        state: _ConnectionState,
        payload: dict[str, object],
    ) -> None:
        try:
            async with asyncio.timeout(self._send_timeout_seconds):
                async with state.send_lock:
                    await state.websocket.send_json(payload)
        except TimeoutError:
            log.warning(
                "发送 WebSocket 消息超时",
                extra={
                    "session_id": state.access.session_id,
                    "mode": state.mode,
                    "timeout_seconds": self._send_timeout_seconds,
                },
            )
            await self._disconnect_state(state)
            raise
        except Exception:
            log.exception(
                "发送 WebSocket 消息失败",
                extra={"session_id": state.access.session_id, "mode": state.mode},
            )
            await self._disconnect_state(state)
            raise

    async def _disconnect_state(self, state: _ConnectionState) -> None:
        async with state.close_lock:
            if state.disconnected:
                return
            state.disconnected = True
            await self.unregister(state.websocket)
            try:
                async with asyncio.timeout(self._close_timeout_seconds):
                    await state.websocket.close(code=1011)
            except TimeoutError:
                log.warning(
                    "关闭 WebSocket 慢连接超时",
                    extra={
                        "session_id": state.access.session_id,
                        "mode": state.mode,
                        "timeout_seconds": self._close_timeout_seconds,
                    },
                )
            except Exception:
                log.exception(
                    "关闭 WebSocket 失败",
                    extra={
                        "session_id": state.access.session_id,
                        "mode": state.mode,
                    },
                )

    @asynccontextmanager
    async def _lock_topics(self, topics: tuple[str, ...]) -> AsyncIterator[None]:
        locks = [
            self._topic_locks.setdefault(topic, asyncio.Lock())
            for topic in topics
        ]
        for lock in locks:
            await lock.acquire()
        try:
            yield
        finally:
            for lock in reversed(locks):
                lock.release()

    @staticmethod
    def _snapshot(state: _ConnectionState) -> WebSocketSessionSnapshot:
        return WebSocketSessionSnapshot(
            session_id=state.access.session_id,
            mode=state.mode,
            account_id=state.account_id,
            subscription_revision=state.subscription_revision,
            topics=state.topics,
        )
