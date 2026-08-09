from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.websocket.endpoint import (
    ConnectionAuthorizer,
    _authorize_or_close,
    _close_safely,
)
from api.websocket.manager import RuntimeWebSocketManager

log = logging.getLogger(__name__)


def build_legacy_websocket_router(
    manager: RuntimeWebSocketManager,
    *,
    authorize_connection: ConnectionAuthorizer,
    max_message_bytes: int = 4 * 1024,
) -> APIRouter:
    if max_message_bytes < 1:
        raise ValueError("legacy WebSocket 消息上限必须大于 0")

    router = APIRouter(tags=["websocket-legacy"])

    @router.websocket("/api/ws")
    async def legacy_websocket_endpoint(websocket: WebSocket) -> None:
        access = await _authorize_or_close(websocket, authorize_connection)
        if access is None:
            return

        await websocket.accept(subprotocol=access.accepted_subprotocol)
        await manager.register_legacy(websocket, access)
        try:
            while True:
                raw = await websocket.receive_text()
                if len(raw.encode("utf-8")) > max_message_bytes:
                    log.warning(
                        "legacy WebSocket 消息超过允许大小",
                        extra={"session_id": access.session_id},
                    )
                    await websocket.close(code=4400)
                    return
                if raw != "ping":
                    log.debug(
                        "legacy WebSocket 忽略非心跳消息",
                        extra={
                            "session_id": access.session_id,
                            "message_size": len(raw),
                        },
                    )
        except WebSocketDisconnect:
            pass
        except Exception:
            log.exception(
                "legacy WebSocket 会话异常",
                extra={"session_id": access.session_id},
            )
            await _close_safely(websocket, code=1011)
        finally:
            await manager.unregister(websocket)

    return router
