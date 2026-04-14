from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.ws_manager import ws_manager

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ws", tags=["websocket"])


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """全局 WebSocket 入口。"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # 等待客户端消息（如果有），目前仅用于心跳或连接维持
            data = await websocket.receive_text()
            log.debug(f"收到客户端消息: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        log.error(f"WebSocket 意外断开: {e}")
        ws_manager.disconnect(websocket)
