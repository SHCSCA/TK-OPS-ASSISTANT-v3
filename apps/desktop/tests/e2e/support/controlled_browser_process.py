from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _DevtoolsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/json/version":
            self.send_error(404)
            return
        host, port = self.server.server_address
        payload = json.dumps(
            {
                "Browser": "TK-OPS E2E Controlled Browser/1.0",
                "webSocketDebuggerUrl": (
                    f"ws://{host}:{port}/devtools/browser/e2e"
                ),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *_args: object) -> None:
        # E2E 受控进程只提供所有权与健康探测，不输出请求噪音。
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-data-dir", required=True)
    parser.add_argument("--remote-debugging-port", required=True, type=int)
    args = parser.parse_args()
    del args.user_data_dir
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.remote_debugging_port),
        _DevtoolsHandler,
    )
    server.serve_forever(poll_interval=0.1)


if __name__ == "__main__":
    main()
