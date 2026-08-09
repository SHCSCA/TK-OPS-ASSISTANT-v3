from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from api.routes.v1.execution_environments import router
from schemas.v1.execution_environments import ExecutionEnvironmentDto


def test_execution_environment_dto_never_exposes_sensitive_runtime_fields() -> None:
    fields = set(ExecutionEnvironmentDto.model_fields)
    assert {
        "id",
        "accountId",
        "name",
        "status",
        "workspace",
        "browser",
        "eligibility",
        "revision",
        "errorCode",
        "errorLogId",
        "errorMessage",
        "lastTaskId",
        "lastRetryOfTaskId",
        "recoveryActions",
    } == fields
    assert not {
        "root_path",
        "profile_path",
        "executable_path",
        "process_id",
        "debug_port",
        "runtime_evidence_json",
    }.intersection(fields)


def test_execution_environment_routes_are_v1_account_scoped_and_async() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    route_source = (
        repository_root
        / "apps"
        / "py-runtime"
        / "src"
        / "api"
        / "routes"
        / "v1"
        / "execution_environments.py"
    ).read_text(encoding="utf-8")

    assert 'prefix="/api/v1/accounts/{account_id}/execution-environments"' in route_source
    assert "status.HTTP_202_ACCEPTED" in route_source
    assert "get_account_scope" in route_source
    assert "Idempotency-Key" in route_source
    assert "root_path" not in route_source


def test_execution_environment_action_routes_require_revision_and_preserve_files() -> None:
    app = FastAPI()
    app.include_router(router)
    schema = app.openapi()
    base = "/api/v1/accounts/{account_id}/execution-environments/{environment_id}"
    actions = {
        f"{base}/start": "post",
        f"{base}/stop": "post",
        f"{base}/checks": "post",
        f"{base}/retry": "post",
        base: "delete",
    }

    for path, method in actions.items():
        operation = schema["paths"][path][method]
        parameters = {item["name"]: item for item in operation["parameters"]}
        assert parameters["If-Match"]["in"] == "header"
        assert parameters["If-Match"]["required"] is False
        assert operation["responses"]["202"]

    delete_parameters = {
        item["name"]: item
        for item in schema["paths"][base]["delete"]["parameters"]
    }
    assert delete_parameters["preserveUserFiles"]["schema"]["default"] is True
