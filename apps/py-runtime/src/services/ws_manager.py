from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

log = logging.getLogger(__name__)


class ConnectionManager:
    """管理全局 WebSocket 连接。"""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info(f"WebSocket 客户端已连接。当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            log.info(f"WebSocket 客户端已断开。当前连接数: {len(self.active_connections)}")

    async def broadcast(self, message: dict[str, Any]) -> None:
        """向所有连接的客户端广播 JSON 消息。"""
        if not self.active_connections:
            return

        log.debug(f"正在广播 WebSocket 消息: {message}")
        
        # 批量发送，忽略失败的连接
        tasks = []
        for connection in self.active_connections:
            tasks.append(self._send_safe(connection, message))
        
        await asyncio.gather(*tasks)

    async def _send_safe(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        try:
            await websocket.send_json(message)
        except Exception as e:
            log.warning(f"向 WebSocket 发送消息失败: {e}")
            self.disconnect(websocket)


# 全局单例
ws_manager = ConnectionManager()
