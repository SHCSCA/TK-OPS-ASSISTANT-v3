from __future__ import annotations

import importlib.util


def test_runtime_has_websocket_server_dependency() -> None:
    has_websocket_transport = (
        importlib.util.find_spec("websockets") is not None
        or importlib.util.find_spec("wsproto") is not None
    )

    assert has_websocket_transport
