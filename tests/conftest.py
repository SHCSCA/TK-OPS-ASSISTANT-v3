from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = REPO_ROOT / "apps" / "py-runtime" / "src"
TEST_RUNTIME_HOST = "127.0.0.1:43119"
TEST_RUNTIME_SESSION_TOKEN = "test-runtime-session-token"

if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))


@pytest.fixture
def runtime_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("TK_OPS_RUNTIME_DB_PATH", raising=False)
    monkeypatch.delenv("TK_OPS_DATABASE_PATH", raising=False)
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TK_OPS_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    monkeypatch.setenv("TK_OPS_RUNTIME_MODE", "test")
    monkeypatch.setenv(
        "TK_OPS_RUNTIME_SESSION_TOKEN",
        TEST_RUNTIME_SESSION_TOKEN,
    )
    monkeypatch.setenv("TK_OPS_RUNTIME_EXPECTED_HOST", TEST_RUNTIME_HOST)
    monkeypatch.setenv(
        "TK_OPS_WORKSPACE_ROOT_REGISTRY_PATH",
        str(tmp_path / "workspace-roots.v1.json"),
    )
    monkeypatch.setenv(
        "TK_OPS_CONTROLLED_FILE_REGISTRY_PATH",
        str(tmp_path / "controlled-files.v1.json"),
    )
    monkeypatch.delenv("TK_OPS_RUNTIME_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("TK_OPS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("TK_OPS_MIGRATION_BACKUP_DIR", raising=False)
    monkeypatch.delenv("TK_OPS_MIGRATION_BACKUP_RETENTION", raising=False)
    monkeypatch.delenv("TK_OPS_MIGRATION_LOCK_PATH", raising=False)
    monkeypatch.delenv("TK_OPS_MIGRATION_LOCK_TIMEOUT_SECONDS", raising=False)
    return tmp_path


@pytest.fixture
def runtime_app(runtime_data_dir: Path):
    from app.factory import create_app
    from app.logging import shutdown_logging

    app = create_app()
    try:
        yield app
    finally:
        engine = getattr(app.state, "runtime_engine", None)
        if engine is not None:
            engine.dispose()
        shutdown_logging()


@pytest.fixture
def runtime_client(runtime_app) -> TestClient:
    with TestClient(
        runtime_app,
        base_url=f"http://{TEST_RUNTIME_HOST}",
    ) as client:
        yield client


@pytest.fixture
def licensed_runtime_client(
    runtime_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    from schemas.v1.bootstrap import LicenseStatusDto

    monkeypatch.setattr(
        runtime_client.app.state.bootstrap_v1_service,
        "get_license_status",
        lambda **_: LicenseStatusDto(
            status="active",
            machineCode="TKOPS-ABCDE-FGHIJ-KLMNO-PQRST-TEST5",
            machineCodeMasked="TKOPS-…-TEST5",
            expiresAt=None,
            activatedAt="2026-07-26T00:00:00Z",
            blockingIssue=None,
            revision=1,
        ),
    )
    runtime_client.headers["Authorization"] = (
        f"Bearer {TEST_RUNTIME_SESSION_TOKEN}"
    )
    return runtime_client
