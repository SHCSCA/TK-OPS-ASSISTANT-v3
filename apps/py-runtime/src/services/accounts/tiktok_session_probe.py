from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol
from urllib.error import URLError
from urllib.request import urlopen

log = logging.getLogger(__name__)


class TikTokSessionProbeError(RuntimeError):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True, slots=True)
class TikTokSessionProbeResult:
    authenticated: bool
    identity: str | None


class TikTokSessionProbePort(Protocol):
    def probe(
        self,
        *,
        debug_port: int,
        timeout_seconds: int,
    ) -> TikTokSessionProbeResult: ...

    def clear_session(
        self,
        *,
        debug_port: int,
        timeout_seconds: int,
    ) -> None: ...


class TikTokSessionProbe:
    """仅从受控浏览器公开页面状态读取登录结果，不读取密码或 Cookie。"""

    def probe(
        self,
        *,
        debug_port: int,
        timeout_seconds: int,
    ) -> TikTokSessionProbeResult:
        target = self._target(debug_port, timeout_seconds)
        websocket_url = target.get("webSocketDebuggerUrl")
        if not isinstance(websocket_url, str) or not websocket_url:
            raise TikTokSessionProbeError(
                "ACCOUNT_PLATFORM_IDENTITY_UNAVAILABLE",
                "无法连接 TikTok 页面，请在浏览器打开账号主页后重试。",
            )
        try:
            from websockets.sync.client import connect

            with connect(
                websocket_url,
                open_timeout=timeout_seconds,
                close_timeout=2,
                origin="http://127.0.0.1",
            ) as websocket:
                websocket.send(
                    json.dumps(
                        {
                            "id": 1,
                            "method": "Runtime.evaluate",
                            "params": {
                                "expression": _PUBLIC_IDENTITY_EXPRESSION,
                                "returnByValue": True,
                            },
                        }
                    )
                )
                response = json.loads(websocket.recv(timeout=timeout_seconds))
        except Exception as exc:
            log.exception("TikTok 登录状态探测失败")
            raise TikTokSessionProbeError(
                "ACCOUNT_PLATFORM_SESSION_INVALID",
                "TikTok 登录状态探测失败，请返回浏览器确认后重试。",
            ) from exc
        value = (
            response.get("result", {})
            .get("result", {})
            .get("value")
        )
        try:
            payload = json.loads(value) if isinstance(value, str) else {}
        except json.JSONDecodeError as exc:
            raise TikTokSessionProbeError(
                "ACCOUNT_PLATFORM_IDENTITY_UNAVAILABLE",
                "未能识别 TikTok 公开账号身份，请打开个人主页后重试。",
            ) from exc
        identity = payload.get("identity")
        return TikTokSessionProbeResult(
            authenticated=payload.get("authenticated") is True,
            identity=(
                str(identity).strip().removeprefix("@").lower()
                if isinstance(identity, str) and identity.strip()
                else None
            ),
        )

    def clear_session(
        self,
        *,
        debug_port: int,
        timeout_seconds: int,
    ) -> None:
        target = self._target(debug_port, timeout_seconds)
        websocket_url = target.get("webSocketDebuggerUrl")
        if not isinstance(websocket_url, str) or not websocket_url:
            raise TikTokSessionProbeError(
                "ACCOUNT_PLATFORM_SESSION_INVALID",
                "无法连接受控浏览器，未能安全清理 TikTok 会话。",
            )
        try:
            from websockets.sync.client import connect

            with connect(
                websocket_url,
                open_timeout=timeout_seconds,
                close_timeout=2,
                origin="http://127.0.0.1",
            ) as websocket:
                websocket.send(
                    json.dumps(
                        {
                            "id": 2,
                            "method": "Storage.clearDataForOrigin",
                            "params": {
                                "origin": "https://www.tiktok.com",
                                "storageTypes": "all",
                            },
                        }
                    )
                )
                response = json.loads(websocket.recv(timeout=timeout_seconds))
                if "error" in response:
                    raise RuntimeError("CDP 拒绝清理平台存储")
        except Exception as exc:
            log.exception("清理 TikTok 浏览器会话失败")
            raise TikTokSessionProbeError(
                "ACCOUNT_PLATFORM_SESSION_INVALID",
                "未能证明 TikTok 会话已清理，请查看日志后重试。",
            ) from exc

    @staticmethod
    def _target(debug_port: int, timeout_seconds: int) -> dict[str, object]:
        try:
            with urlopen(  # noqa: S310
                f"http://127.0.0.1:{debug_port}/json/list",
                timeout=timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise TikTokSessionProbeError(
                "ACCOUNT_PLATFORM_SESSION_INVALID",
                "受控浏览器不可达，请重新启动执行环境。",
            ) from exc
        if not isinstance(payload, list):
            payload = []
        for item in payload:
            if (
                isinstance(item, dict)
                and isinstance(item.get("url"), str)
                and "tiktok.com" in str(item["url"]).lower()
            ):
                return item
        raise TikTokSessionProbeError(
            "ACCOUNT_PLATFORM_IDENTITY_UNAVAILABLE",
            "未找到 TikTok 页面，请在浏览器打开账号主页后重试。",
        )


_PUBLIC_IDENTITY_EXPRESSION = r"""
JSON.stringify((() => {
  const href = String(location.href || "");
  const profile = document.querySelector(
    '[data-e2e="profile-icon"], [data-e2e="nav-profile"], a[href*="/@"]'
  );
  const links = Array.from(document.querySelectorAll('a[href*="/@"]'))
    .map((item) => item.getAttribute("href") || "");
  const candidates = [href, ...links];
  let identity = null;
  for (const value of candidates) {
    const match = value.match(/\/@([A-Za-z0-9._-]+)/);
    if (match) {
      identity = match[1];
      break;
    }
  }
  return { authenticated: Boolean(profile), identity };
})())
""".strip()
