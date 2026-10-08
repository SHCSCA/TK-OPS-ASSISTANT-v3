from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from api.dependencies.revision import get_expected_revision_allow_zero
from tests.contracts.p0e_ai_contract_support import (
    AI_ROUTE_CONTRACTS,
    AI_ROUTE_MODULES,
    AIRouteContract,
)

RUNTIME_ROOT = Path(__file__).resolve().parents[2] / "apps" / "py-runtime"
ROUTES_ROOT = RUNTIME_ROOT / "src" / "api" / "routes" / "v1"


def _route_index(runtime_app: object) -> dict[tuple[str, str], APIRoute]:
    routes: dict[tuple[str, str], APIRoute] = {}
    for route in runtime_app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods:
            routes[(method, route.path)] = route
    return routes


def _response_model_name(route: APIRoute) -> str:
    field = route.response_field
    assert field is not None
    return str(field.field_info.annotation)


def _function_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for filename in AI_ROUTE_MODULES:
        path = ROUTES_ROOT / filename
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sources[node.name] = ast.get_source_segment(source, node) or ""
    return sources


def test_p0_e_ai_route_inventory_is_frozen_to_40_operations(
    runtime_app: object,
) -> None:
    assert len(AI_ROUTE_CONTRACTS) == 40
    expected = {(item.method, item.path) for item in AI_ROUTE_CONTRACTS}
    assert len(expected) == 40
    module_names = {
        f"api.routes.v1.{filename.removesuffix('.py')}"
        for filename in AI_ROUTE_MODULES
    }
    actual = {
        key
        for key, route in _route_index(runtime_app).items()
        if route.endpoint.__module__ in module_names
    }
    assert actual == expected


@pytest.mark.parametrize(
    "contract",
    AI_ROUTE_CONTRACTS,
    ids=lambda item: f"{item.method} {item.path}",
)
def test_p0_e_ai_route_status_and_response_dto(
    runtime_app: object,
    contract: AIRouteContract,
) -> None:
    route = _route_index(runtime_app)[(contract.method, contract.path)]

    assert (route.status_code or 200) == contract.status_code
    assert contract.response_model in _response_model_name(route)


def test_p0_e_mutation_routes_declare_revision_and_idempotency_guards(
    runtime_app: object,
) -> None:
    functions = _function_sources()
    route_index = _route_index(runtime_app)

    for contract in AI_ROUTE_CONTRACTS:
        if not (contract.requires_revision or contract.requires_idempotency):
            continue
        endpoint = route_index[(contract.method, contract.path)].endpoint
        source = functions[endpoint.__name__]
        if contract.requires_revision:
            assert "get_expected_revision" in source, contract.path
        if contract.requires_idempotency:
            assert "require_idempotency_key" in source, contract.path


def test_initial_capability_route_revision_accepts_zero() -> None:
    revision = get_expected_revision_allow_zero("0")

    assert revision.value == 0
    assert "get_expected_revision_allow_zero" in _function_sources()[
        "put_capability_route"
    ]


def test_ai_input_dtos_forbid_unknown_fields() -> None:
    from schemas.v1.account_ai_recipe import AccountAIRecipeVersionInput
    from schemas.v1.capability_routes import CapabilityRouteInput
    from schemas.v1.composition_templates import CompositionTemplateInput
    from schemas.v1.model_profiles import ModelCreateInput
    from schemas.v1.prompt_profiles import PromptProfileInput
    from schemas.v1.provider_profiles import ProviderCreateInput

    dto_types = (
        AccountAIRecipeVersionInput,
        CapabilityRouteInput,
        CompositionTemplateInput,
        ModelCreateInput,
        PromptProfileInput,
        ProviderCreateInput,
    )
    assert all(dto.model_config.get("extra") == "forbid" for dto in dto_types)


def test_ai_summary_dtos_do_not_expose_plaintext_or_prompt_bodies() -> None:
    from schemas.v1.prompt_profiles import PromptProfileDto
    from schemas.v1.provider_profiles import (
        CredentialSummaryDto,
        ProviderDto,
    )
    from schemas.v1.tasks import TaskAcceptedDto

    assert "credential" not in ProviderDto.model_fields
    assert "credentialSummary" in ProviderDto.model_fields
    assert "credential" not in CredentialSummaryDto.model_fields
    assert {
        "systemPrompt",
        "taskTemplate",
        "visualStylePrefix",
        "safetyConstraints",
    }.isdisjoint(PromptProfileDto.model_fields)
    assert {
        "configSnapshot",
        "configSnapshotJson",
        "payload",
        "credential",
        "systemPrompt",
        "taskTemplate",
    }.isdisjoint(TaskAcceptedDto.model_fields)
