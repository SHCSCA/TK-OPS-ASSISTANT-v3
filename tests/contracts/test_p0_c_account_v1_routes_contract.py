from __future__ import annotations

import inspect

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from api.dependencies.account_scope import (
    get_account_scope,
    get_account_scope_allow_archived,
)
from api.dependencies.license_guard import require_active_license
from api.dependencies.pagination import get_pagination
from api.dependencies.request_context import get_request_context
from api.dependencies.revision import get_expected_revision
from api.routes.v1.account_configuration import (
    router as account_configuration_router,
)
from api.routes.v1.account_connection import (
    router as account_connection_router,
)
from api.routes.v1.account_knowledge import router as account_knowledge_router
from api.routes.v1.accounts import router as accounts_router

_ROUTERS = (
    accounts_router,
    account_connection_router,
    account_configuration_router,
    account_knowledge_router,
)

_EXPECTED_INVENTORY = {
    ("GET", "/api/v1/accounts", 200),
    ("POST", "/api/v1/accounts", 201),
    ("GET", "/api/v1/accounts/{account_id}", 200),
    ("PATCH", "/api/v1/accounts/{account_id}", 200),
    (
        "GET",
        "/api/v1/accounts/{account_id}/workspace-context",
        200,
    ),
    (
        "POST",
        "/api/v1/accounts/{account_id}/workspace-activation",
        200,
    ),
    ("POST", "/api/v1/accounts/{account_id}/complete-wizard", 200),
    ("POST", "/api/v1/accounts/{account_id}/copy-config", 200),
    ("POST", "/api/v1/accounts/{account_id}/archive", 202),
    ("POST", "/api/v1/accounts/{account_id}/restore", 202),
    ("GET", "/api/v1/accounts/{account_id}/health", 200),
    ("POST", "/api/v1/accounts/{account_id}/health-checks", 202),
    ("GET", "/api/v1/accounts/{account_id}/connection", 200),
    (
        "GET",
        "/api/v1/accounts/{account_id}/connection/candidates",
        200,
    ),
    (
        "PUT",
        "/api/v1/accounts/{account_id}/connection/binding",
        200,
    ),
    (
        "DELETE",
        "/api/v1/accounts/{account_id}/connection/binding",
        200,
    ),
    (
        "POST",
        "/api/v1/accounts/{account_id}/connection/checks",
        202,
    ),
    ("GET", "/api/v1/accounts/{account_id}/positioning", 200),
    (
        "GET",
        "/api/v1/accounts/{account_id}/positioning/versions/{version}",
        200,
    ),
    (
        "POST",
        "/api/v1/accounts/{account_id}/positioning/versions",
        201,
    ),
    (
        "POST",
        (
            "/api/v1/accounts/{account_id}/positioning/"
            "versions/{version}/activate"
        ),
        200,
    ),
    ("GET", "/api/v1/accounts/{account_id}/knowledge", 200),
    ("PATCH", "/api/v1/accounts/{account_id}/knowledge", 200),
    (
        "GET",
        "/api/v1/accounts/{account_id}/knowledge/sources",
        200,
    ),
    (
        "POST",
        "/api/v1/accounts/{account_id}/knowledge/sources",
        201,
    ),
    (
        "DELETE",
        "/api/v1/accounts/{account_id}/knowledge/sources/{source_id}",
        200,
    ),
    (
        "POST",
        "/api/v1/accounts/{account_id}/knowledge/index-jobs",
        202,
    ),
    (
        "GET",
        "/api/v1/accounts/{account_id}/knowledge/snapshots",
        200,
    ),
    (
        "POST",
        "/api/v1/accounts/{account_id}/knowledge/snapshots",
        201,
    ),
    (
        "GET",
        (
            "/api/v1/accounts/{account_id}/knowledge/"
            "snapshots/{snapshot_id}"
        ),
        200,
    ),
    ("GET", "/api/v1/accounts/{account_id}/brand-kit", 200),
    ("PUT", "/api/v1/accounts/{account_id}/brand-kit", 200),
    ("GET", "/api/v1/accounts/{account_id}/publish-defaults", 200),
    ("PUT", "/api/v1/accounts/{account_id}/publish-defaults", 200),
}

_REVISION_ROUTES = {
    ("PATCH", "/api/v1/accounts/{account_id}"),
    ("POST", "/api/v1/accounts/{account_id}/workspace-activation"),
    ("POST", "/api/v1/accounts/{account_id}/complete-wizard"),
    ("POST", "/api/v1/accounts/{account_id}/copy-config"),
    ("POST", "/api/v1/accounts/{account_id}/archive"),
    ("POST", "/api/v1/accounts/{account_id}/restore"),
    ("PUT", "/api/v1/accounts/{account_id}/connection/binding"),
    ("DELETE", "/api/v1/accounts/{account_id}/connection/binding"),
    (
        "POST",
        "/api/v1/accounts/{account_id}/positioning/versions",
    ),
    (
        "POST",
        (
            "/api/v1/accounts/{account_id}/positioning/"
            "versions/{version}/activate"
        ),
    ),
    ("PATCH", "/api/v1/accounts/{account_id}/knowledge"),
    (
        "DELETE",
        "/api/v1/accounts/{account_id}/knowledge/sources/{source_id}",
    ),
    ("PUT", "/api/v1/accounts/{account_id}/brand-kit"),
    ("PUT", "/api/v1/accounts/{account_id}/publish-defaults"),
}

_IDEMPOTENT_ROUTES = {
    ("POST", "/api/v1/accounts"),
    ("POST", "/api/v1/accounts/{account_id}/workspace-activation"),
    ("POST", "/api/v1/accounts/{account_id}/complete-wizard"),
    ("POST", "/api/v1/accounts/{account_id}/copy-config"),
    ("POST", "/api/v1/accounts/{account_id}/archive"),
    ("POST", "/api/v1/accounts/{account_id}/restore"),
    ("POST", "/api/v1/accounts/{account_id}/health-checks"),
    ("PUT", "/api/v1/accounts/{account_id}/connection/binding"),
    ("DELETE", "/api/v1/accounts/{account_id}/connection/binding"),
    (
        "POST",
        "/api/v1/accounts/{account_id}/connection/checks",
    ),
    (
        "POST",
        "/api/v1/accounts/{account_id}/positioning/versions",
    ),
    (
        "POST",
        (
            "/api/v1/accounts/{account_id}/positioning/"
            "versions/{version}/activate"
        ),
    ),
    (
        "POST",
        "/api/v1/accounts/{account_id}/knowledge/sources",
    ),
    (
        "DELETE",
        "/api/v1/accounts/{account_id}/knowledge/sources/{source_id}",
    ),
    (
        "POST",
        "/api/v1/accounts/{account_id}/knowledge/index-jobs",
    ),
    (
        "POST",
        "/api/v1/accounts/{account_id}/knowledge/snapshots",
    ),
    ("PUT", "/api/v1/accounts/{account_id}/brand-kit"),
}

_ARCHIVED_ALLOWED_ROUTES = {
    ("GET", "/api/v1/accounts/{account_id}"),
    ("POST", "/api/v1/accounts/{account_id}/archive"),
    ("POST", "/api/v1/accounts/{account_id}/restore"),
    ("GET", "/api/v1/accounts/{account_id}/health"),
}


def test_account_http_inventory_includes_p0_d_additions() -> None:
    assert _inventory() == _EXPECTED_INVENTORY
    assert len(_EXPECTED_INVENTORY) == 34


def test_all_account_v1_routes_use_license_and_request_context() -> None:
    for route in _routes():
        dependencies = _dependency_calls(route)
        assert require_active_license in dependencies, route.path
        assert get_request_context in dependencies, route.path


def test_account_scope_dependencies_keep_contextvar_lifecycle_async() -> None:
    assert inspect.isasyncgenfunction(get_account_scope)
    assert inspect.isasyncgenfunction(get_account_scope_allow_archived)


def test_scoped_routes_enforce_account_and_archive_boundaries() -> None:
    for route in _routes():
        method = _method(route)
        key = (method, route.path)
        dependencies = _dependency_calls(route)
        if route.path == "/api/v1/accounts":
            assert get_account_scope not in dependencies
            assert get_account_scope_allow_archived not in dependencies
            continue
        if key in _ARCHIVED_ALLOWED_ROUTES:
            assert get_account_scope_allow_archived in dependencies, key
            assert get_account_scope not in dependencies, key
        else:
            assert get_account_scope in dependencies, key
            assert get_account_scope_allow_archived not in dependencies, key


def test_revision_pagination_and_idempotency_dependencies_are_exact() -> None:
    for route in _routes():
        method = _method(route)
        key = (method, route.path)
        dependencies = _dependency_calls(route)
        assert (
            get_expected_revision in dependencies
        ) is (key in _REVISION_ROUTES), key
        assert (
            get_pagination in dependencies
        ) is (
            route.path
            in {
                "/api/v1/accounts",
                "/api/v1/accounts/{account_id}/knowledge/sources",
                "/api/v1/accounts/{account_id}/knowledge/snapshots",
            }
            and method == "GET"
        ), key
        source = inspect.getsource(route.endpoint)
        assert (
            "_require_idempotency_key" in source
        ) is (key in _IDEMPOTENT_ROUTES), key


def test_account_target_is_never_accepted_from_mutation_body() -> None:
    for route in _routes():
        if _method(route) not in {"POST", "PUT", "PATCH", "DELETE"}:
            continue
        body_field = route.body_field
        if body_field is None:
            continue
        body_type = body_field.field_info.annotation
        model_fields = getattr(body_type, "model_fields", {})
        model_config = getattr(body_type, "model_config", {})
        assert model_config.get("extra") == "forbid", route.path
        assert "accountId" not in model_fields, route.path
        assert "targetAccountId" not in model_fields, route.path
        assert "account_id" not in model_fields, route.path


def test_scoped_endpoints_only_forward_resolved_account_scope() -> None:
    for route in _routes():
        if route.path == "/api/v1/accounts":
            continue
        parameters = inspect.signature(route.endpoint).parameters
        assert "account_id" not in parameters, route.path
        assert "scope.account_id" in inspect.getsource(route.endpoint), route.path


def test_nested_knowledge_resource_ids_are_bounded_stable_ids() -> None:
    app = FastAPI()
    for router in _ROUTERS:
        app.include_router(router)
    schema = app.openapi()
    expected = {
        "type": "string",
        "minLength": 1,
        "maxLength": 128,
        "pattern": r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
    }
    targets = (
        (
            "/api/v1/accounts/{account_id}/knowledge/sources/{source_id}",
            "delete",
            "source_id",
        ),
        (
            (
                "/api/v1/accounts/{account_id}/knowledge/"
                "snapshots/{snapshot_id}"
            ),
            "get",
            "snapshot_id",
        ),
    )
    for path, method, parameter_name in targets:
        parameters = schema["paths"][path][method]["parameters"]
        parameter = next(
            item for item in parameters if item["name"] == parameter_name
        )
        assert parameter["in"] == "path"
        assert parameter["required"] is True
        assert {
            key: parameter["schema"][key]
            for key in expected
        } == expected


def _routes() -> tuple[APIRoute, ...]:
    return tuple(
        route
        for router in _ROUTERS
        for route in router.routes
        if isinstance(route, APIRoute)
    )


def _inventory() -> set[tuple[str, str, int]]:
    return {
        (_method(route), route.path, route.status_code or 200)
        for route in _routes()
    }


def _method(route: APIRoute) -> str:
    methods = route.methods or set()
    selected = methods.intersection({"GET", "POST", "PUT", "PATCH", "DELETE"})
    assert len(selected) == 1
    return next(iter(selected))


def _dependency_calls(route: APIRoute) -> set[object]:
    calls: set[object] = set()

    def visit(dependency: Dependant) -> None:
        calls.add(dependency.call)
        for child in dependency.dependencies:
            visit(child)

    visit(route.dependant)
    return calls
