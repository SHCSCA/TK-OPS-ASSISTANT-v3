from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from api.websocket.manager import RuntimeWebSocketManager
from api.websocket.models import SubscribeFrame
from api.websocket.session import WebSocketAccessContext
from errors import DomainError

log = logging.getLogger(__name__)

ConnectionAuthorizer = Callable[
    [WebSocket],
    Awaitable[WebSocketAccessContext],
]


def build_v1_websocket_router(
    manager: RuntimeWebSocketManager,
    *,
    authorize_connection: ConnectionAuthorizer,
    subscribe_timeout_seconds: float = 10.0,
    max_message_bytes: int = 64 * 1024,
) -> APIRouter:
    if subscribe_timeout_seconds <= 0:
        raise ValueError("WebSocket 首帧超时必须大于 0")
    if max_message_bytes < 1:
        raise ValueError("WebSocket 消息上限必须大于 0")

    router = APIRouter(tags=["websocket-v1"])

    @router.websocket("/api/v1/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        access = await _authorize_or_close(websocket, authorize_connection)
        if access is None:
            return

        await websocket.accept(subprotocol=access.accepted_subprotocol)
        await manager.register_v1(websocket, access)
        subscribed = False
        subscription_deadline = (
            asyncio.get_running_loop().time() + subscribe_timeout_seconds
        )
        try:
            while True:
                if subscribed:
                    raw = await websocket.receive_text()
                else:
                    remaining_seconds = (
                        subscription_deadline - asyncio.get_running_loop().time()
                    )
                    if remaining_seconds <= 0:
                        raise TimeoutError
                    raw = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=remaining_seconds,
                    )
                if len(raw.encode("utf-8")) > max_message_bytes:
                    await manager.send_protocol_error(
                        websocket,
                        error_code="REQUEST_VALIDATION_FAILED",
                        message="WebSocket 消息超过允许大小。",
                    )
                    await websocket.close(code=4400)
                    return

                try:
                    payload = _read_json_object(raw)
                    if payload.get("type") == "ping":
                        await manager.send_pong(websocket)
                        continue

                    frame = SubscribeFrame.model_validate(payload)
                    await manager.subscribe(websocket, frame)
                    subscribed = True
                except (ValueError, ValidationError):
                    log.warning(
                        "WebSocket 订阅帧校验失败",
                        extra={"session_id": access.session_id},
                    )
                    await manager.send_protocol_error(
                        websocket,
                        error_code="REQUEST_VALIDATION_FAILED",
                        message="WebSocket 订阅参数无效。",
                    )
                except DomainError as exc:
                    log.warning(
                        "WebSocket 订阅被拒绝",
                        extra={
                            "session_id": access.session_id,
                            "error_code": exc.error_code,
                        },
                    )
                    await manager.send_protocol_error(
                        websocket,
                        error_code=exc.error_code,
                        message=exc.message,
                        subscription_revision=frame.subscription_revision,
                    )
        except TimeoutError:
            log.warning(
                "WebSocket 首个订阅帧超时",
                extra={"session_id": access.session_id},
            )
            try:
                await manager.send_protocol_error(
                    websocket,
                    error_code="REQUEST_TIMEOUT",
                    message="等待 WebSocket 订阅超时。",
                )
            except Exception:
                log.exception(
                    "发送 WebSocket 订阅超时反馈失败",
                    extra={"session_id": access.session_id},
                )
            await _close_safely(websocket, code=4408)
        except WebSocketDisconnect:
            pass
        except Exception:
            log.exception(
                "v1 WebSocket 会话异常",
                extra={"session_id": access.session_id},
            )
            await _close_safely(websocket, code=1011)
        finally:
            await manager.unregister(websocket)

    return router


def _read_json_object(raw: str) -> dict[str, object]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("WebSocket 消息不是有效 JSON 对象") from exc
    if not isinstance(payload, dict):
        raise ValueError("WebSocket 消息必须是 JSON 对象")
    return payload


async def _authorize_or_close(
    websocket: WebSocket,
    authorize_connection: ConnectionAuthorizer,
) -> WebSocketAccessContext | None:
    try:
        return await authorize_connection(websocket)
    except Exception as exc:
        error_code = _exception_error_code(exc, "RUNTIME_SESSION_INVALID")
        log.warning(
            "WebSocket 连接门禁拒绝请求",
            extra={"error_code": error_code, "error_type": type(exc).__name__},
        )
        close_code = (
            4403
            if error_code
            in {
                "RUNTIME_HOST_INVALID",
                "RUNTIME_ORIGIN_FORBIDDEN",
                "LICENSE_INVALID",
            }
            else 4401
        )
        await _close_safely(websocket, code=close_code)
        return None


async def _close_safely(websocket: WebSocket, *, code: int) -> None:
    try:
        await websocket.close(code=code)
    except Exception:
        log.exception("关闭 WebSocket 连接失败", extra={"close_code": code})


def _exception_error_code(exc: Exception, fallback: str) -> str:
    value = getattr(exc, "error_code", fallback)
    return str(getattr(value, "value", value))
