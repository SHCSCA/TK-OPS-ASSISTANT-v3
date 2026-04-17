from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = REPO_ROOT / "apps" / "py-runtime" / "src"

if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))


@pytest.fixture
def runtime_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TK_OPS_RUNTIME_MODE", "test")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        monkeypatch.setenv("TK_OPS_RUNTIME_PORT", str(sock.getsockname()[1]))
    return tmp_path


@pytest.fixture
def runtime_app(runtime_data_dir: Path):
    from app.factory import create_app

    return create_app()


@pytest.fixture
def runtime_client(runtime_app) -> TestClient:
    return TestClient(runtime_app)
