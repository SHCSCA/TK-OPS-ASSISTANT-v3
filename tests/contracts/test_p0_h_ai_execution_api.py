from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from fastapi.routing import APIRoute

from api.routes.v1.account_ai_executions import router as executions_router
from errors import ErrorCode
from schemas.v1.ai_executions import (
    AIExecutionCreateInput,
    AIExecutionDetailDto,
    AIExecutionEvidenceDto,
    AIExecutionPreflightInput,
    AIExecutionRetryInput,
)
from schemas.v1.model_profiles import CapabilityCheckInput
from schemas.v1.provider_profiles import (
    CredentialSummaryDto,
    ProviderCheckInput,
    ProviderDto,
)
from services.ai_configuration_v1.task_adapter_results import (
    NormalizedCapability,
)
from services.ai_configuration_v1.task_real_validation import (
    contract_only_capabilities,
)
from services.ai_execution_v1.provider_ports import AIProviderPort
from services.ai_execution_v1.task_registration import (
    register_ai_execution_handler,
)
from services.ai_execution_v1.types import ProviderCallError
from services.config.schema_ai_execution import AI_EXECUTION_DEFAULTS
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.types import TaskResumePolicy


def test_provider_validation_inputs_are_closed_and_explicit() -> None:
    provider = ProviderCheckInput()
    capability = CapabilityCheckInput()

    assert provider.stages == ["network", "authentication"]
    assert capability.mode == "contract_only"
    assert provider.model_config.get("extra") == "forbid"
    assert capability.model_config.get("extra") == "forbid"


def test_credential_references_are_not_exposed_by_public_dtos() -> None:
    forbidden = {"credential", "credentialRef", "credentialReference"}

    assert forbidden.isdisjoint(ProviderDto.model_fields)
    assert forbidden.isdisjoint(CredentialSummaryDto.model_fields)
    assert "credentialReferenceChanged" in CredentialSummaryDto.model_fields


def test_contract_only_probe_cannot_be_promoted_to_real_validation() -> None:
    source = NormalizedCapability(
        capability_key="script_generation",
        declared_supported=True,
        adapter_supported=True,
        contract_verified=True,
        input_modalities_json="[]",
        output_modalities_json="[]",
        parameter_schema_json="{}",
        known_limits_json="{}",
    )

    result = contract_only_capabilities((source,))

    assert result[0].contract_verified is False


def test_provider_validation_output_limit_comes_from_config_bus() -> None:
    assert AI_EXECUTION_DEFAULTS["ai.providerValidation.maxOutputUnits"] == 8
    assert AI_EXECUTION_DEFAULTS["ai.execution.enabled"] is False


def test_provider_port_and_safe_error_contract_are_narrow() -> None:
    assert {
        "health",
        "discover_models",
        "validate_capability",
        "execute",
        "cancel",
    }.issubset(AIProviderPort.__dict__)
    assert "response_body" not in ProviderCallError.__dict__
    assert "request_body" not in ProviderCallError.__dict__


def test_ai_execution_http_inventory_matches_unique_api_document() -> None:
    actual = {
        (method, route.path)
        for route in executions_router.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    expected = {
        ("POST", "/api/v1/accounts/{account_id}/ai-executions/preflight"),
        ("POST", "/api/v1/accounts/{account_id}/ai-executions"),
        ("GET", "/api/v1/accounts/{account_id}/ai-executions"),
        ("GET", "/api/v1/accounts/{account_id}/ai-executions/{execution_id}"),
        ("POST", "/api/v1/accounts/{account_id}/ai-executions/{execution_id}/cancel"),
        ("POST", "/api/v1/accounts/{account_id}/ai-executions/{execution_id}/retry"),
        (
            "GET",
            "/api/v1/accounts/{account_id}/ai-executions/{execution_id}/outputs/{output_id}",
        ),
        (
            "GET",
            "/api/v1/accounts/{account_id}/ai-executions/{execution_id}/evidence",
        ),
    }
    assert actual == expected

    documentation = Path("docs/api/v1/ai-executions.md").read_text(
        encoding="utf-8"
    )
    for method, path in expected:
        assert f"### {method} `{path}`" in documentation


def test_ai_execution_request_and_public_dto_contracts_are_closed() -> None:
    for model in (
        AIExecutionPreflightInput,
        AIExecutionCreateInput,
        AIExecutionRetryInput,
    ):
        assert model.model_config.get("extra") == "forbid"

    forbidden = {
        "credential",
        "credentialRef",
        "apiKey",
        "authorization",
        "headers",
        "prompt",
        "input",
        "rawRequest",
        "rawResponse",
        "absolutePath",
        "cookie",
        "token",
    }
    assert forbidden.isdisjoint(AIExecutionDetailDto.model_fields)
    assert forbidden.isdisjoint(AIExecutionEvidenceDto.model_fields)


def test_ai_execution_task_snapshot_and_recovery_policy_are_fixed() -> None:
    registry = TaskHandlerRegistry()
    register_ai_execution_handler(registry, executor=Mock())
    definition = registry.require("ai.execution")

    assert definition.allowed_snapshot_fields == frozenset(
        {"executionId", "snapshotHash"}
    )
    assert definition.resume_policy is TaskResumePolicy.INTERRUPT
    assert definition.cancellable is True
    assert definition.handler_version == 1


def test_ai_execution_error_codes_are_stable() -> None:
    required = {
        "AI_EXECUTION_NOT_FOUND",
        "AI_EXECUTION_DISABLED",
        "AI_EXECUTION_INVALID",
        "AI_EXECUTION_STATE_CONFLICT",
        "AI_PROVIDER_RESULT_UNKNOWN",
        "AI_COST_UNAVAILABLE",
        "AI_COST_LIMIT_EXCEEDED",
        "AI_USAGE_UNAVAILABLE",
        "AI_EVIDENCE_REDACTION_FAILED",
    }
    assert required.issubset({item.value for item in ErrorCode})
