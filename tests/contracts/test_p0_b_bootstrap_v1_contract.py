from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies.request_context import install_request_context_middleware
from api.routes.v1.bootstrap import router
from app.config import load_runtime_config
from app.exception_handlers import install_exception_handlers
from errors import DomainError
from repositories.license_repository import StoredLicenseGrant
from services.bootstrap_v1 import (
    BootstrapV1Service,
    DirectoryV1Service,
    LicenseV1Service,
)
from services.license_activation_base import ActivationResult
from services.machine_code import MachineIdentityResolution
from services.tasks.types import RuntimeTaskRecord, TaskScope, TaskStatus

EXPECTED_HOST = "127.0.0.1:43119"
SESSION_TOKEN = "p0-b-runtime-session"
MACHINE_CODE = "TKOPS-ABCDE-FGHIJ-KLMNO-PQRST-UVWXY"


def test_bootstrap_v1_routes_and_license_exemptions(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    app, repository = _build_app(runtime_data_dir, monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)
    headers = _headers()

    status_response = client.get("/api/v1/bootstrap/status", headers=headers)
    license_response = client.get("/api/v1/bootstrap/license", headers=headers)
    blocked_directories = client.post(
        "/api/v1/bootstrap/directories/initialize",
        headers={**headers, "Idempotency-Key": "idem-directories-before-license"},
        json={"workspaceRootRef": None},
    )

    assert status_response.status_code == 200
    assert license_response.status_code == 200
    assert repository.save_calls == 0
    assert status_response.json()["data"]["license"]["status"] == "missing"
    assert status_response.json()["data"]["license"]["machineCode"] == MACHINE_CODE
    assert license_response.json()["data"]["machineCode"] == MACHINE_CODE
    assert blocked_directories.status_code == 403
    assert blocked_directories.json()["error_code"] == "LICENSE_INVALID"


def test_bootstrap_v1_activation_directory_and_self_check_contracts(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    app, repository = _build_app(runtime_data_dir, monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)
    headers = _headers()

    activation_response = client.post(
        "/api/v1/bootstrap/license/activate",
        headers={**headers, "Idempotency-Key": "idem-license-activate"},
        json={
            "licenseKey": "signed.license",
        },
    )
    directory_response = client.post(
        "/api/v1/bootstrap/directories/initialize",
        headers={**headers, "Idempotency-Key": "idem-directories"},
        json={"workspaceRootRef": None},
    )
    self_check_response = client.post(
        "/api/v1/bootstrap/self-checks",
        headers={**headers, "Idempotency-Key": "idem-self-check"},
        json={"checks": ["database", "directories", "runtime"]},
    )

    assert activation_response.status_code == 200
    assert activation_response.json()["data"]["status"] == "active"
    assert activation_response.json()["data"]["machineCode"] == MACHINE_CODE
    assert repository.save_calls == 1
    assert directory_response.status_code == 200
    assert directory_response.json()["data"]["status"] == "ready"
    assert self_check_response.status_code == 202
    assert self_check_response.json()["data"] == {
        "taskId": "task-bootstrap-self-check",
        "scope": "system",
        "accountId": None,
        "taskType": "bootstrap.self_check",
        "status": "queued",
        "cancellable": True,
        "createdAt": "2026-07-26T10:00:00Z",
    }


def test_bootstrap_v1_rejects_missing_session_and_wrong_origin(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    app, _ = _build_app(runtime_data_dir, monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    missing_session = client.get(
        "/api/v1/bootstrap/status",
        headers={"Host": EXPECTED_HOST, "Origin": "tauri://localhost"},
    )
    wrong_origin = client.get(
        "/api/v1/bootstrap/status",
        headers={
            "Host": EXPECTED_HOST,
            "Origin": "https://evil.example",
            "Authorization": f"Bearer {SESSION_TOKEN}",
        },
    )

    assert missing_session.status_code == 401
    assert missing_session.json()["error_code"] == "RUNTIME_SESSION_REQUIRED"
    assert wrong_origin.status_code == 403
    assert wrong_origin.json()["error_code"] == "RUNTIME_ORIGIN_FORBIDDEN"


def test_bootstrap_v1_write_routes_require_idempotency_key(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    app, _ = _build_app(runtime_data_dir, monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/bootstrap/license/activate",
        headers=_headers(),
        json={
            "licenseKey": "signed.license",
        },
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "REQUEST_VALIDATION_FAILED"
    assert response.json()["fieldErrors"] == [
        {
            "field": "Idempotency-Key",
            "code": "required",
            "message": "必须提供幂等键",
        }
    ]


def test_license_activation_rolls_back_grant_and_secret_when_event_fails(
) -> None:
    repository = _LicenseRepository()
    secret_store = _SecretStore()
    service = LicenseV1Service(
        repository=repository,
        activation_adapter=_ActivationAdapter(),
        machine_code_service=_MachineCodeService(),
        secret_store=secret_store,
        event_service=_FailingEventService(),
    )

    with pytest.raises(DomainError):
        service.activate(
            license_key="signed.license",
            machine_code=MACHINE_CODE,
            idempotency_key="idem-event-failure",
            request_id="req-event-failure",
            operation_id="op-event-failure",
        )

    assert repository.value is None
    assert secret_store.values == {}


def _build_app(
    runtime_data_dir: Path,
    monkeypatch,
) -> tuple[FastAPI, "_LicenseRepository"]:
    monkeypatch.setenv("TK_OPS_RUNTIME_MODE", "test")
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", str(runtime_data_dir))
    monkeypatch.setenv("TK_OPS_RUNTIME_SESSION_TOKEN", SESSION_TOKEN)
    monkeypatch.setenv("TK_OPS_RUNTIME_EXPECTED_HOST", EXPECTED_HOST)
    monkeypatch.setattr(
        "services.bootstrap_v1.service.resolve_ffprobe",
        lambda: SimpleNamespace(status="ready", error_code=None),
    )
    monkeypatch.setattr(
        "services.bootstrap_v1.service.resolve_ffmpeg",
        lambda: SimpleNamespace(status="ready", error_code=None),
    )
    runtime_config = load_runtime_config()
    repository = _LicenseRepository()
    service = BootstrapV1Service(
        runtime_config=runtime_config,
        license_service=LicenseV1Service(
            repository=repository,
            activation_adapter=_ActivationAdapter(),
            machine_code_service=_MachineCodeService(),
            secret_store=_SecretStore(),
        ),
        directory_service=DirectoryV1Service(runtime_config=runtime_config),
        task_submitter=_TaskSubmitter(),
    )
    app = FastAPI()
    app.state.runtime_config = runtime_config
    app.state.bootstrap_v1_service = service
    install_request_context_middleware(app)
    install_exception_handlers(app)
    app.include_router(router)
    return app, repository


def _headers() -> dict[str, str]:
    return {
        "Host": EXPECTED_HOST,
        "Origin": "tauri://localhost",
        "Authorization": f"Bearer {SESSION_TOKEN}",
        "X-Operation-ID": "op-bootstrap-contract",
    }


class _LicenseRepository:
    def __init__(self) -> None:
        self.value: StoredLicenseGrant | None = None
        self.save_calls = 0

    def load(self) -> StoredLicenseGrant | None:
        return self.value

    def save(
        self,
        grant: StoredLicenseGrant,
        *,
        before_commit=None,
    ) -> StoredLicenseGrant:
        previous = self.value
        self.value = grant
        self.save_calls += 1
        try:
            if before_commit is not None:
                before_commit(None, grant)
        except Exception:
            self.value = previous
            raise
        return grant


class _ActivationAdapter:
    def activate(self, activation_code: str, *, machine_code: str) -> ActivationResult:
        assert activation_code == "signed.license"
        assert machine_code == MACHINE_CODE
        return ActivationResult(
            license_type="perpetual",
            activated_at="2026-07-26T09:00:00Z",
            masked_code="sign****************ense",
            signed_payload="signed",
        )


class _MachineCodeService:
    def get_machine_code(self) -> str:
        return MACHINE_CODE

    def resolve(
        self,
        *,
        legacy_machine_code: str | None = None,
    ) -> MachineIdentityResolution:
        del legacy_machine_code
        return MachineIdentityResolution(
            machine_code=MACHINE_CODE,
            status="verified",
            matched_factor_count=3,
            mismatched_factor_count=0,
            unavailable_factor_count=0,
        )


class _SecretStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def delete(self, key: str) -> None:
        self.values.pop(key, None)


class _TaskSubmitter:
    async def submit_system_task(self, **kwargs) -> RuntimeTaskRecord:
        assert kwargs["task_type"] == "bootstrap.self_check"
        assert kwargs["payload"] == {
            "checks": ["database", "directories", "runtime"]
        }
        return RuntimeTaskRecord(
            id="task-bootstrap-self-check",
            scope=TaskScope.SYSTEM,
            account_id=None,
            task_type="bootstrap.self_check",
            status=TaskStatus.QUEUED,
            completion_kind=None,
            failure_kind=None,
            progress=0,
            cancellable=True,
            timeout_at=None,
            attempt=1,
            retry_of_task_id=None,
            config_snapshot_json="{}",
            result_ref=None,
            error_code=None,
            error_log_id=None,
            revision=1,
            created_at="2026-07-26T10:00:00Z",
            started_at=None,
            completed_at=None,
            updated_at="2026-07-26T10:00:00Z",
            idempotency_key_hash="a" * 64,
            request_hash="b" * 64,
            handler_version=1,
        )


class _FailingEventService:
    def append(self, *_args, **_kwargs) -> None:
        raise RuntimeError("event write failed")
