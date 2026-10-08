from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import ClassVar
from urllib.parse import urlsplit

HOST = "127.0.0.1"
PORT = 18121
EXPECTED_CREDENTIAL = os.environ.get("TK_OPS_E2E_PROVIDER_CREDENTIAL", "").strip()


class Evidence:
    def __init__(self) -> None:
        self._lock = Lock()
        self._values = {
            "authorizedRequests": 0,
            "chatCompletionRequests": 0,
            "modelsRequests": 0,
            "reportedUsageResponses": 0,
        }

    def increment(self, key: str) -> None:
        with self._lock:
            self._values[key] += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "evidenceKind": "p0h_controlled_contract",
                "providerEvidenceKind": "controlled_contract",
                **self._values,
            }


EVIDENCE = Evidence()


class ControlledProviderHandler(BaseHTTPRequestHandler):
    server_version: ClassVar[str] = "TKOPSP0HControlledProvider/1"

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/__e2e__/health":
            self._send_json(200, {"ok": True})
            return
        if path == "/__e2e__/evidence":
            self._send_json(200, EVIDENCE.snapshot())
            return
        if not self._authorized():
            self._send_json(401, {"error": "invalid_credential"})
            return
        EVIDENCE.increment("authorizedRequests")
        if path == "/v1/models":
            EVIDENCE.increment("modelsRequests")
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [{"id": "tk-e2e-text-1", "object": "model"}],
                },
            )
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if not self._authorized():
            self._send_json(401, {"error": "invalid_credential"})
            return
        EVIDENCE.increment("authorizedRequests")
        if path != "/v1/chat/completions":
            self._send_json(404, {"error": "not_found"})
            return
        payload = self._read_json()
        if payload is None or payload.get("model") != "tk-e2e-text-1":
            self._send_json(400, {"error": "invalid_request"})
            return
        EVIDENCE.increment("chatCompletionRequests")
        EVIDENCE.increment("reportedUsageResponses")
        self._send_json(
            200,
            {
                "id": "p0h-controlled-response",
                "object": "chat.completion",
                "model": "tk-e2e-text-1",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "script": "先给结论，再用三个步骤说明稳定选题流程。"
                                },
                                ensure_ascii=False,
                            ),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 18,
                    "completion_tokens": 12,
                    "total_tokens": 30,
                },
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _authorized(self) -> bool:
        return self.headers.get("Authorization") == f"Bearer {EXPECTED_CREDENTIAL}"

    def _read_json(self) -> dict[str, object] | None:
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 1_048_576:
                return None
            value = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> None:
    if not EXPECTED_CREDENTIAL:
        raise SystemExit("缺少受控测试 Provider 凭据")
    server = ThreadingHTTPServer((HOST, PORT), ControlledProviderHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
