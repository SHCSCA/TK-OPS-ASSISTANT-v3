from __future__ import annotations

import logging

from fastapi import FastAPI

from api.routes import (
    accounts_router,
    ai_capabilities_router,
    ai_provider_runtime_router,
    ai_providers_router,
    assets_router,
    automation_router,
    dashboard_router,
    device_workspaces_router,
    prompt_templates_router,
    publishing_router,
    renders_router,
    review_router,
    scripts_router,
    search_router,
    storyboards_router,
    subtitles_router,
    video_deconstruction_router,
    voice_router,
    workspace_router,
)
from api.routes.legacy import (
    bootstrap_legacy_router,
    system_legacy_router,
    tasks_legacy_router,
)
from api.routes.v1.account_configuration import (
    router as account_configuration_v1_router,
)
from api.routes.v1.account_connection import (
    router as account_connection_v1_router,
)
from api.routes.v1.account_knowledge import (
    router as account_knowledge_v1_router,
)
from api.routes.v1.account_ai_recipe import (
    router as account_ai_recipe_v1_router,
)
from api.routes.v1.account_ai_executions import (
    router as account_ai_executions_v1_router,
)
from api.routes.v1.accounts import router as accounts_v1_router
from api.routes.v1.execution_environments import (
    router as execution_environments_v1_router,
)
from api.routes.v1.account_login_sessions import (
    router as account_login_sessions_v1_router,
)
from api.routes.v1.bootstrap import router as bootstrap_v1_router
from api.routes.v1.system_config import router as system_config_v1_router
from api.routes.v1.system_capability_routes import (
    router as system_capability_routes_v1_router,
)
from api.routes.v1.system_ai_dependencies import (
    router as system_ai_dependencies_v1_router,
)
from api.routes.v1.system_composition_templates import (
    router as system_composition_templates_v1_router,
)
from api.routes.v1.system_diagnostics import (
    router as system_diagnostics_v1_router,
)
from api.routes.v1.system_model_capabilities import (
    router as system_model_capabilities_v1_router,
)
from api.routes.v1.system_models import router as system_models_v1_router
from api.routes.v1.system_prompt_profiles import (
    router as system_prompt_profiles_v1_router,
)
from api.routes.v1.system_providers import (
    router as system_providers_v1_router,
)
from api.routes.v1.tasks import router as tasks_v1_router
from api.websocket import (
    build_legacy_websocket_router,
    build_v1_websocket_router,
)
from app.config import is_production_mode
from app.container import RuntimeContainer
from app.websocket_security import (
    build_legacy_websocket_connection_authorizer,
    build_websocket_connection_authorizer,
)

log = logging.getLogger(__name__)

LEGACY_COMPATIBILITY_HTTP_ROUTERS = (
    bootstrap_legacy_router,
    system_legacy_router,
    tasks_legacy_router,
)

LEGACY_UNMIGRATED_HTTP_ROUTERS = (
    accounts_router,
    ai_capabilities_router,
    ai_provider_runtime_router,
    ai_providers_router,
    assets_router,
    automation_router,
    dashboard_router,
    device_workspaces_router,
    prompt_templates_router,
    publishing_router,
    renders_router,
    review_router,
    search_router,
    scripts_router,
    storyboards_router,
    subtitles_router,
    video_deconstruction_router,
    voice_router,
    workspace_router,
)

V1_HTTP_ROUTERS = (
    bootstrap_v1_router,
    accounts_v1_router,
    account_connection_v1_router,
    account_configuration_v1_router,
    account_knowledge_v1_router,
    account_ai_recipe_v1_router,
    account_ai_executions_v1_router,
    execution_environments_v1_router,
    account_login_sessions_v1_router,
    system_providers_v1_router,
    system_models_v1_router,
    system_model_capabilities_v1_router,
    system_capability_routes_v1_router,
    system_ai_dependencies_v1_router,
    system_prompt_profiles_v1_router,
    system_composition_templates_v1_router,
    system_config_v1_router,
    system_diagnostics_v1_router,
    tasks_v1_router,
)


def register_routes(
    app: FastAPI,
    container: RuntimeContainer,
) -> None:
    for router in V1_HTTP_ROUTERS:
        app.include_router(router)

    for router in LEGACY_COMPATIBILITY_HTTP_ROUTERS:
        app.include_router(router)

    if not is_production_mode(container.config.mode):
        for router in LEGACY_UNMIGRATED_HTTP_ROUTERS:
            app.include_router(router)
    else:
        log.info("生产模式仅注册受控 legacy 薄适配路由")

    v1_connection_authorizer = build_websocket_connection_authorizer(
        container.services.bootstrap_v1
    )
    legacy_connection_authorizer = (
        build_legacy_websocket_connection_authorizer(
            container.services.bootstrap_v1
        )
    )
    app.include_router(
        build_v1_websocket_router(
            container.kernel.websocket_manager,
            authorize_connection=v1_connection_authorizer,
            subscribe_timeout_seconds=(
                container.kernel.policy.websocket_subscribe_timeout_seconds
            ),
            max_message_bytes=(
                container.kernel.policy.websocket_max_message_bytes
            ),
        )
    )
    app.include_router(
        build_legacy_websocket_router(
            container.kernel.websocket_manager,
            authorize_connection=legacy_connection_authorizer,
            max_message_bytes=(
                container.kernel.policy.legacy_websocket_max_message_bytes
            ),
        )
    )
