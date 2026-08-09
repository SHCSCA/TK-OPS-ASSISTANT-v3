from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import cast

import pytest
from fastapi import WebSocket

from api.websocket import (
    RuntimeWebSocketManager,
    SubscribeFrame,
    WebSocketAccessContext,
    build_legacy_websocket_router,
    build_v1_websocket_router,
)
from services.events import (
    CursorMismatchError,
    ReplayResolution,
    RuntimeEventDto,
    RuntimeEventService,
    TopicCursor,
)


class _FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []
        self.close_codes: list[int] = []

    async def send_json(self, payload: dict[str, object]) -> None:
        self.sent.append(payload)

    async def close(self, code: int = 1000) -> None:
        self.close_codes.append(code)


class _ControllableWebSocket(_FakeWebSocket):
    def __init__(self) -> None:
        super().__init__()
        self.block_sends = False

    async def send_json(self, payload: dict[str, object]) -> None:
        if self.block_sends:
            await asyncio.Future()
        await super().send_json(payload)


class _ReplayService:
    def __init__(
        self,
        resolve: Callable[[TopicCursor], ReplayResolution] | None = None,
    ) -> None:
        self._resolve = resolve

    def resolve_replay(self, cursor: TopicCursor) -> ReplayResolution:
        if self._resolve is not None:
            return self._resolve(cursor)
        return ReplayResolution(
            topic=cursor.topic,
            current_sequence=0,
            events=(),
            sync_required=False,
        )


def _event(
    *,
    event_id: str,
    event_type: str,
    topic: str,
    sequence: int,
    account_id: str | None,
    payload: dict[str, object] | None = None,
) -> RuntimeEventDto:
    return RuntimeEventDto(
        event_id=event_id,
        event_type=event_type,
        topic=topic,
        sequence=sequence,
        occurred_at="2026-07-26T00:00:00Z",
        account_id=account_id,
        resource_type=None,
        resource_id=None,
        task_id=None,
        revision=sequence,
        payload=payload or {},
    )


def _frame(
    *,
    revision: int,
    account_id: str | None,
    topics: list[str],
) -> SubscribeFrame:
    return SubscribeFrame.model_validate(
        {
            "type": "subscribe",
            "subscriptionRevision": revision,
            "accountId": account_id,
            "topics": [
                {
                    "topic": topic,
                    "lastEventId": None,
                    "afterSequence": None,
                }
                for topic in topics
            ],
        }
    )


@pytest.mark.asyncio
async def test_v1_manager_filters_live_events_by_account_and_topic() -> None:
    authorized_accounts: list[str] = []

    async def authorize_account(
        access: WebSocketAccessContext,
        account_id: str,
    ) -> None:
        assert access.session_id == "session-a"
        authorized_accounts.append(account_id)

    manager = RuntimeWebSocketManager(
        cast(RuntimeEventService, _ReplayService()),
        authorize_account=authorize_account,
    )
    fake_socket = _FakeWebSocket()
    websocket = cast(WebSocket, fake_socket)
    await manager.register_v1(
        websocket,
        WebSocketAccessContext(
            session_id="session-a",
            allowed_system_topics=frozenset({"system:health"}),
        ),
    )
    await manager.subscribe(
        websocket,
        _frame(
            revision=1,
            account_id="acc_a",
            topics=["system:health", "account:acc_a:tasks"],
        ),
    )
    baseline_count = len(fake_socket.sent)

    await manager.publish(
        _event(
            event_id="evt_b",
            event_type="task.progress",
            topic="account:acc_b:tasks",
            sequence=1,
            account_id="acc_b",
        )
    )
    await manager.publish(
        _event(
            event_id="evt_config",
            event_type="config.changed",
            topic="system:config",
            sequence=1,
            account_id=None,
        )
    )
    assert len(fake_socket.sent) == baseline_count

    await manager.publish(
        _event(
            event_id="evt_a",
            event_type="task.progress",
            topic="account:acc_a:tasks",
            sequence=1,
            account_id="acc_a",
        )
    )
    await manager.publish(
        _event(
            event_id="evt_health",
            event_type="runtime.health.updated",
            topic="system:health",
            sequence=1,
            account_id=None,
        )
    )

    assert authorized_accounts == ["acc_a"]
    assert [
        item["eventId"]
        for item in fake_socket.sent
        if "eventId" in item
    ] == ["evt_a", "evt_health"]


@pytest.mark.asyncio
async def test_topic_gap_only_disables_the_expired_topic() -> None:
    replay_event = _event(
        event_id="evt_health_2",
        event_type="runtime.health.updated",
        topic="system:health",
        sequence=2,
        account_id=None,
    )

    def resolve(cursor: TopicCursor) -> ReplayResolution:
        if cursor.topic == "account:acc_a:tasks":
            return ReplayResolution(
                topic=cursor.topic,
                current_sequence=7,
                events=(),
                sync_required=True,
                sync_reason="WS_EVENT_GAP",
            )
        return ReplayResolution(
            topic=cursor.topic,
            current_sequence=2,
            events=(replay_event,),
            sync_required=False,
        )

    async def authorize_account(
        access: WebSocketAccessContext,
        account_id: str,
    ) -> None:
        assert access.session_id == "session-gap"
        assert account_id == "acc_a"

    manager = RuntimeWebSocketManager(
        cast(RuntimeEventService, _ReplayService(resolve)),
        authorize_account=authorize_account,
    )
    fake_socket = _FakeWebSocket()
    websocket = cast(WebSocket, fake_socket)
    await manager.register_v1(
        websocket,
        WebSocketAccessContext(
            session_id="session-gap",
            allowed_system_topics=frozenset({"system:health"}),
        ),
    )
    await manager.subscribe(
        websocket,
        _frame(
            revision=4,
            account_id="acc_a",
            topics=["system:health", "account:acc_a:tasks"],
        ),
    )

    snapshot = await manager.get_snapshot(websocket)
    assert snapshot is not None
    assert snapshot.topics == frozenset({"system:health"})
    assert fake_socket.sent[0]["type"] == "subscribed"
    assert any(item.get("type") == "sync.required" for item in fake_socket.sent)
    assert any(item.get("eventId") == "evt_health_2" for item in fake_socket.sent)

    baseline_count = len(fake_socket.sent)
    await manager.publish(
        _event(
            event_id="evt_task_8",
            event_type="task.progress",
            topic="account:acc_a:tasks",
            sequence=8,
            account_id="acc_a",
        )
    )
    assert len(fake_socket.sent) == baseline_count

    with pytest.raises(CursorMismatchError):
        await manager.subscribe(
            websocket,
            _frame(
                revision=4,
                account_id="acc_a",
                topics=["system:health"],
            ),
        )


@pytest.mark.asyncio
async def test_legacy_manager_only_emits_sanitized_system_allowlist() -> None:
    manager = RuntimeWebSocketManager(
        cast(RuntimeEventService, _ReplayService())
    )
    fake_socket = _FakeWebSocket()
    websocket = cast(WebSocket, fake_socket)
    await manager.register_legacy(
        websocket,
        WebSocketAccessContext(session_id="legacy-session"),
    )

    await manager.publish(
        _event(
            event_id="evt_health",
            event_type="runtime.health.updated",
            topic="system:health",
            sequence=3,
            account_id=None,
            payload={
                "status": "ready",
                "revision": 3,
                "accountId": "acc_private",
                "credential": "secret-value",
            },
        )
    )
    await manager.publish(
        _event(
            event_id="evt_account",
            event_type="task.progress",
            topic="account:acc_a:tasks",
            sequence=1,
            account_id="acc_a",
            payload={"taskId": "task_a", "progress": 0.5},
        )
    )
    await manager.publish(
        _event(
            event_id="evt_internal",
            event_type="runtime.internal.updated",
            topic="system:health",
            sequence=4,
            account_id=None,
            payload={"status": "ready"},
        )
    )

    assert fake_socket.sent == [
        {
            "schema_version": 1,
            "type": "runtime.health.updated",
            "status": "ready",
            "revision": 3,
        }
    ]


@pytest.mark.asyncio
async def test_slow_connection_is_closed_without_blocking_other_subscribers() -> None:
    manager = RuntimeWebSocketManager(
        cast(RuntimeEventService, _ReplayService()),
        send_timeout_seconds=0.01,
        close_timeout_seconds=0.01,
    )
    slow_socket = _ControllableWebSocket()
    healthy_socket = _FakeWebSocket()
    slow_websocket = cast(WebSocket, slow_socket)
    healthy_websocket = cast(WebSocket, healthy_socket)
    access = WebSocketAccessContext(
        session_id="session-slow",
        allowed_system_topics=frozenset({"system:health"}),
    )
    await manager.register_v1(slow_websocket, access)
    await manager.register_v1(
        healthy_websocket,
        WebSocketAccessContext(
            session_id="session-healthy",
            allowed_system_topics=frozenset({"system:health"}),
        ),
    )
    await manager.subscribe(
        slow_websocket,
        _frame(
            revision=1,
            account_id=None,
            topics=["system:health"],
        ),
    )
    await manager.subscribe(
        healthy_websocket,
        _frame(
            revision=1,
            account_id=None,
            topics=["system:health"],
        ),
    )
    slow_socket.block_sends = True

    await asyncio.wait_for(
        manager.publish(
            _event(
                event_id="evt_health_slow",
                event_type="runtime.health.updated",
                topic="system:health",
                sequence=1,
                account_id=None,
            )
        ),
        timeout=0.2,
    )

    assert await manager.get_snapshot(slow_websocket) is None
    assert await manager.get_snapshot(healthy_websocket) is not None
    assert slow_socket.close_codes == [1011]
    assert any(
        item.get("eventId") == "evt_health_slow"
        for item in healthy_socket.sent
    )


def test_router_builders_keep_v1_and_legacy_paths_separate() -> None:
    manager = RuntimeWebSocketManager(
        cast(RuntimeEventService, _ReplayService())
    )

    async def authorize_connection(
        websocket: WebSocket,
    ) -> WebSocketAccessContext:
        return WebSocketAccessContext(session_id=str(id(websocket)))

    authorizer: Callable[
        [WebSocket],
        Awaitable[WebSocketAccessContext],
    ] = authorize_connection
    v1_router = build_v1_websocket_router(
        manager,
        authorize_connection=authorizer,
    )
    legacy_router = build_legacy_websocket_router(
        manager,
        authorize_connection=authorizer,
    )

    assert {route.path for route in v1_router.routes} == {"/api/v1/ws"}
    assert {route.path for route in legacy_router.routes} == {"/api/ws"}
