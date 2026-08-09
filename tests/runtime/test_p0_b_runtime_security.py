from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from starlette.requests import Request

from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import RequestContext
from api.dependencies.request_origin_guard import validate_connection_origin
from api.dependencies.runtime_session_guard import require_runtime_session
from app.config import RuntimeConfigurationError, load_runtime_config
from errors import DomainError, ErrorCode
from schemas.v1.bootstrap import LicenseStatusDto

STRONG_RUNTIME_SESSION_TOKEN = "A" * 43


def test_production_config_requires_runtime_session_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("TK_OPS_RUNTIME_MODE", "production")
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TK_OPS_RUNTIME_EXPECTED_HOST", "127.0.0.1:43119")
    monkeypatch.delenv("TK_OPS_RUNTIME_SESSION_TOKEN", raising=False)

    with pytest.raises(RuntimeConfigurationError):
        load_runtime_config()


def test_production_config_requires_exact_loopback_host(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("TK_OPS_RUNTIME_MODE", "production")
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", str(tmp_path))
    monkeypatch.setenv(
        "TK_OPS_RUNTIME_SESSION_TOKEN",
        STRONG_RUNTIME_SESSION_TOKEN,
    )
    monkeypatch.setenv("TK_OPS_RUNTIME_EXPECTED_HOST", "localhost:43119")

    with pytest.raises(RuntimeConfigurationError):
        load_runtime_config()


def test_production_origin_list_does_not_accept_development_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("TK_OPS_RUNTIME_MODE", "production")
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", str(tmp_path))
    monkeypatch.setenv(
        "TK_OPS_RUNTIME_SESSION_TOKEN",
        STRONG_RUNTIME_SESSION_TOKEN,
    )
    monkeypatch.setenv("TK_OPS_RUNTIME_EXPECTED_HOST", "127.0.0.1:43119")
    monkeypatch.setenv(
        "TK_OPS_RUNTIME_ALLOWED_ORIGINS",
        "http://127.0.0.1:5174",
    )

    config = load_runtime_config()

    assert config.allowed_origins == (
        "tauri://localhost",
        "http://tauri.localhost",
    )


def test_runtime_config_rejects_unknown_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("TK_OPS_RUNTIME_MODE", "release")
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", str(tmp_path))

    with pytest.raises(RuntimeConfigurationError):
        load_runtime_config()


def test_production_config_rejects_weak_runtime_session_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("TK_OPS_RUNTIME_MODE", "production")
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TK_OPS_RUNTIME_SESSION_TOKEN", "runtime-session-token")
    monkeypatch.setenv(
        "TK_OPS_RUNTIME_EXPECTED_HOST",
        "127.0.0.1:43119",
    )

    with pytest.raises(RuntimeConfigurationError):
        load_runtime_config()


def test_runtime_session_requires_exact_bearer_token() -> None:
    valid_request = _request(
        headers={
            "host": "127.0.0.1:43119",
            "authorization": "Bearer expected-session",
        }
    )
    require_runtime_session(valid_request)

    invalid_request = _request(
        headers={
            "host": "127.0.0.1:43119",
            "authorization": "Bearer wrong-session",
        }
    )
    with pytest.raises(DomainError) as captured:
        require_runtime_session(invalid_request)

    assert captured.value.error_code == ErrorCode.RUNTIME_SESSION_INVALID
    assert "wrong-session" not in captured.value.log_context.values()


def test_request_origin_rejects_wrong_host_and_untrusted_origin() -> None:
    wrong_host = _request(
        headers={
            "host": "localhost:43119",
            "origin": "tauri://localhost",
        }
    )
    with pytest.raises(DomainError) as captured_host:
        validate_connection_origin(wrong_host)
    assert captured_host.value.error_code == ErrorCode.RUNTIME_HOST_INVALID

    wrong_origin = _request(
        headers={
            "host": "127.0.0.1:43119",
            "origin": "https://evil.example",
        }
    )
    with pytest.raises(DomainError) as captured_origin:
        validate_connection_origin(wrong_origin)
    assert captured_origin.value.error_code == ErrorCode.RUNTIME_ORIGIN_FORBIDDEN


def test_request_without_origin_still_requires_exact_host() -> None:
    request = _request(headers={"host": "127.0.0.1:43119"})

    validate_connection_origin(request)


@pytest.mark.parametrize(
    ("license_status", "expected_error"),
    [
        ("missing", ErrorCode.LICENSE_INVALID),
        ("expired", ErrorCode.LICENSE_INVALID),
        ("invalid", ErrorCode.LICENSE_INVALID),
        ("machine_mismatch", ErrorCode.LICENSE_MACHINE_MISMATCH),
    ],
)
def test_license_guard_only_accepts_active_status(
    license_status: str,
    expected_error: ErrorCode,
) -> None:
    request = _request(headers={"host": "127.0.0.1:43119"})
    request.app.state.bootstrap_v1_service = _LicenseProvider(license_status)
    context = RequestContext(
        request_id="req-security-test",
        operation_id="op-security-test",
        idempotency_key=None,
    )

    with pytest.raises(DomainError) as captured:
        require_active_license(request, context)

    assert captured.value.error_code == expected_error


def test_license_guard_accepts_active_status() -> None:
    request = _request(headers={"host": "127.0.0.1:43119"})
    request.app.state.bootstrap_v1_service = _LicenseProvider("active")
    context = RequestContext(
        request_id="req-security-test",
        operation_id="op-security-test",
        idempotency_key=None,
    )

    status = require_active_license(request, context)

    assert status.status == "active"


class _LicenseProvider:
    def __init__(self, status: str) -> None:
        self._status = status

    def get_license_status(
        self,
        *,
        request_id: str,
        operation_id: str,
    ) -> LicenseStatusDto:
        return LicenseStatusDto(
            status=self._status,
            machineCode="TKOPS-ABCDE-FGHIJ-KLMNO-PQRST-ABCDE",
            machineCodeMasked="TKOPS-**********ABCDE",
            expiresAt=None,
            activatedAt=None,
            blockingIssue=None,
            revision=1,
        )


def _request(*, headers: dict[str, str]) -> Request:
    app = FastAPI()
    app.state.runtime_config = SimpleNamespace(
        expected_host="127.0.0.1:43119",
        allowed_origins=("tauri://localhost",),
        runtime_session_token="expected-session",
    )
    return Request(
        {
            "type": "http",
            "app": app,
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/bootstrap/status",
            "raw_path": b"/api/v1/bootstrap/status",
            "query_string": b"",
            "headers": [
                (name.lower().encode("ascii"), value.encode("latin-1"))
                for name, value in headers.items()
            ],
            "client": ("127.0.0.1", 43120),
            "server": ("127.0.0.1", 43119),
        }
    )
