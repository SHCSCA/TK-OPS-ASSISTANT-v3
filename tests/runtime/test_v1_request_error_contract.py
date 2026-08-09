from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from api.dependencies.request_context import (
    RequestContext,
    get_request_context,
    install_request_context_middleware,
)
from app.exception_handlers import install_exception_handlers
from app.logging import configure_logging, shutdown_logging
from errors import DomainError, ErrorCode
from schemas.v1.envelope import ok_response


class SecretValidationInput(BaseModel):
    apiKey: int


class DynamicKeyValidationInput(BaseModel):
    values: dict[str, int]


def _build_app() -> FastAPI:
    app = FastAPI()
    install_request_context_middleware(app)
    install_exception_handlers(app)

    @app.get("/api/v1/context")
    def read_context(
        context: RequestContext = Depends(get_request_context),
    ) -> dict[str, object]:
        return ok_response(
            {
                "requestId": context.request_id,
                "operationId": context.operation_id,
                "idempotencyKey": context.idempotency_key,
            }
        )

    @app.post("/api/v1/validate")
    def validate_input(payload: SecretValidationInput) -> dict[str, object]:
        return ok_response(payload.model_dump(mode="json"))

    @app.post("/api/v1/validate-dynamic-key")
    def validate_dynamic_key(
        payload: DynamicKeyValidationInput,
    ) -> dict[str, object]:
        return ok_response(payload.model_dump(mode="json"))

    @app.get("/api/v1/domain-error")
    def domain_error() -> None:
        raise DomainError(
            ErrorCode.RUNTIME_NOT_READY,
            "Runtime 尚未就绪",
            status_code=503,
            loggable=True,
        )

    @app.get("/api/v1/domain-error-auto-log")
    def domain_error_auto_log() -> None:
        raise DomainError(
            ErrorCode.DIRECTORY_CREATE_FAILED,
            "目录初始化失败",
            status_code=500,
        )

    @app.get("/api/v1/unexpected")
    def unexpected_error() -> None:
        raise RuntimeError("仅允许写入本地日志的内部异常")

    return app


def test_request_context_returns_controlled_ids() -> None:
    with TestClient(_build_app()) as client:
        response = client.get(
            "/api/v1/context",
            headers={
                "X-Operation-ID": "op_user_action_01",
                "Idempotency-Key": "idem_create_01",
            },
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"].startswith("req_")
    assert response.headers["X-Operation-ID"] == "op_user_action_01"
    assert response.json()["data"]["idempotencyKey"] == "idem_create_01"


def test_invalid_context_header_uses_safe_field_error() -> None:
    with TestClient(_build_app()) as client:
        response = client.get(
            "/api/v1/context",
            headers={"X-Operation-ID": "invalid operation id"},
        )

    payload = response.json()
    assert response.status_code == 422
    assert payload["error_code"] == "REQUEST_VALIDATION_FAILED"
    assert payload["fieldErrors"] == [
        {
            "field": "X-Operation-ID",
            "code": "invalid_header_id",
            "message": "必须为 1 至 128 位受控标识",
        }
    ]
    assert "log_id" not in payload


def test_validation_error_never_echoes_sensitive_input(tmp_path: Path) -> None:
    configure_logging(tmp_path)
    try:
        with TestClient(_build_app()) as client:
            response = client.post(
                "/api/v1/validate",
                json={"apiKey": "super-secret-key"},
            )
    finally:
        shutdown_logging()

    serialized_response = json.dumps(response.json(), ensure_ascii=False)
    serialized_log = (tmp_path / "runtime.jsonl").read_text(encoding="utf-8")
    assert response.status_code == 422
    assert response.json()["error_code"] == "REQUEST_VALIDATION_FAILED"
    assert "super-secret-key" not in serialized_response
    assert "super-secret-key" not in serialized_log
    assert "input" not in response.json()["fieldErrors"][0]


def test_validation_error_never_echoes_dynamic_input_key(
    tmp_path: Path,
) -> None:
    configure_logging(tmp_path)
    try:
        with TestClient(_build_app()) as client:
            response = client.post(
                "/api/v1/validate-dynamic-key",
                json={"values": {"super-secret-key": "not-an-integer"}},
            )
    finally:
        shutdown_logging()

    serialized_response = json.dumps(response.json(), ensure_ascii=False)
    serialized_log = (tmp_path / "runtime.jsonl").read_text(encoding="utf-8")
    assert response.status_code == 422
    assert response.json()["fieldErrors"][0]["field"] == "body.values.field"
    assert "super-secret-key" not in serialized_response
    assert "super-secret-key" not in serialized_log


def test_visible_domain_error_returns_real_log_reference(tmp_path: Path) -> None:
    configure_logging(tmp_path)
    try:
        with TestClient(_build_app()) as client:
            response = client.get("/api/v1/domain-error")
    finally:
        shutdown_logging()

    payload = response.json()
    entries = [
        json.loads(line)
        for line in (tmp_path / "runtime.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert response.status_code == 503
    assert payload["log_id"].startswith("log_")
    matching_entry = next(
        entry
        for entry in entries
        if entry.get("log_id") == payload["log_id"]
    )
    assert matching_entry["error_code"] == "RUNTIME_NOT_READY"


def test_server_domain_error_always_returns_log_reference(
    tmp_path: Path,
) -> None:
    configure_logging(tmp_path)
    try:
        with TestClient(_build_app()) as client:
            response = client.get("/api/v1/domain-error-auto-log")
    finally:
        shutdown_logging()

    payload = response.json()
    assert response.status_code == 500
    assert payload["error_code"] == "DIRECTORY_CREATE_FAILED"
    assert payload["log_id"].startswith("log_")


def test_framework_route_errors_use_chinese_messages() -> None:
    with TestClient(_build_app()) as client:
        missing = client.get("/api/v1/not-found")
        wrong_method = client.post("/api/v1/context")

    assert missing.status_code == 404
    assert missing.json()["error_code"] == "ROUTE_NOT_FOUND"
    assert missing.json()["error"] == "请求的接口不存在"
    assert wrong_method.status_code == 405
    assert wrong_method.json()["error_code"] == "METHOD_NOT_ALLOWED"
    assert wrong_method.json()["error"] == "请求方法不受支持"


def test_unknown_exception_is_logged_and_returns_safe_v1_error(tmp_path: Path) -> None:
    configure_logging(tmp_path)
    try:
        with TestClient(
            _build_app(),
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/api/v1/unexpected")
    finally:
        shutdown_logging()

    payload = response.json()
    entries = [
        json.loads(line)
        for line in (tmp_path / "runtime.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert response.status_code == 500
    assert payload["error_code"] == "INTERNAL_ERROR"
    assert payload["log_id"].startswith("log_")
    assert "内部异常" not in json.dumps(payload, ensure_ascii=False)
    matching_entry = next(
        entry
        for entry in entries
        if entry.get("log_id") == payload["log_id"]
    )
    assert "RuntimeError" in matching_entry["exception"]
