from __future__ import annotations

import json
import socket
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass(slots=True)
class ControlledProviderScenario:
    token: str = "p0h-test-token"
    model_id: str = "p0h-text-model"
    omit_usage: bool = False
    invalid_generation: bool = False
    error_status: int | None = None
    error_marker: str = ""
    response_statuses: list[int] = field(default_factory=list)
    retry_after_seconds: float | None = None
    response_delay_seconds: float = 0.0
    disconnect_after_request: bool = False
    output_text: str = '{"script":"OK"}'
    input_units: int = 6
    output_units: int = 1
    request_started: threading.Event = field(default_factory=threading.Event)
    received: list[dict[str, object]] = field(default_factory=list)


class ControlledProviderServer:
    """仅用于自动化契约验证，不能作为真实 Provider 验收证据。"""

    def __init__(self, scenario: ControlledProviderScenario) -> None:
        self.scenario = scenario
        handler = _handler_type(scenario)
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="p0h-controlled-provider",
            daemon=True,
        )

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/v1"

    def __enter__(self) -> ControlledProviderServer:
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


def _handler_type(
    scenario: ControlledProviderScenario,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            scenario.received.append(
                {"method": "GET", "path": self.path}
            )
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            if self.path != "/v1/models":
                self._send_json(404, {"error": "not_found"})
                return
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": scenario.model_id,
                            "display_name": "P0-H 文本模型",
                        }
                    ],
                },
            )

        def do_POST(self) -> None:
            raw = self.rfile.read(
                min(int(self.headers.get("Content-Length", "0")), 65_536)
            )
            scenario.received.append(
                {
                    "method": "POST",
                    "path": self.path,
                    "body": json.loads(raw.decode("utf-8")),
                }
            )
            scenario.request_started.set()
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            if scenario.response_delay_seconds > 0:
                time.sleep(scenario.response_delay_seconds)
            if scenario.disconnect_after_request:
                try:
                    self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                self.connection.close()
                return
            scripted_status = (
                scenario.response_statuses.pop(0)
                if scenario.response_statuses
                else scenario.error_status
            )
            if scripted_status is not None:
                self._send_json(
                    scripted_status,
                    {"error": scenario.error_marker},
                    headers=(
                        {
                            "Retry-After": str(
                                scenario.retry_after_seconds
                            )
                        }
                        if scenario.retry_after_seconds is not None
                        else None
                    ),
                )
                return
            if self.path != "/v1/chat/completions":
                self._send_json(404, {"error": "not_found"})
                return
            if scenario.invalid_generation:
                self._send_json(200, {"id": "invalid"})
                return
            payload: dict[str, object] = {
                "id": "response-p0h-controlled",
                "model": scenario.model_id,
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "OK"},
                        "finish_reason": "stop",
                    }
                ],
            }
            payload["choices"][0]["message"]["content"] = (
                scenario.output_text
            )
            if not scenario.omit_usage:
                payload["usage"] = {
                    "prompt_tokens": scenario.input_units,
                    "completion_tokens": scenario.output_units,
                    "total_tokens": (
                        scenario.input_units + scenario.output_units
                    ),
                }
            self._send_json(200, payload)

        def _authorized(self) -> bool:
            return self.headers.get("Authorization") == (
                f"Bearer {scenario.token}"
            )

        def _send_json(
            self,
            status: int,
            payload: object,
            *,
            headers: dict[str, str] | None = None,
        ) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                return

        def log_message(self, _format: str, *_args: object) -> None:
            return

    return Handler


__all__ = ["ControlledProviderScenario", "ControlledProviderServer"]
