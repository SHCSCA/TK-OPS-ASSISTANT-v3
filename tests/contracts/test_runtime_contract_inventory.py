from __future__ import annotations

import re
import sys
from pathlib import Path

from fastapi.routing import APIRoute

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = PROJECT_ROOT / "apps" / "py-runtime" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from app.factory import create_app

DOC_PATH = PROJECT_ROOT / "docs" / "RUNTIME-API-CALLS.md"
CONTRACT_OWNERS: dict[str, tuple[str, ...]] = {
    "/api/accounts": ("test_runtime_page_modules_contract.py",),
    "/api/ai-providers": ("test_ai_capabilities_contract.py",),
    "/api/assets": ("test_runtime_page_modules_contract.py",),
    "/api/automation": ("test_automation_runtime_contract.py",),
    "/api/bootstrap": ("test_bootstrap_contract.py",),
    "/api/dashboard": ("test_dashboard_contract.py",),
    "/api/devices": ("test_browser_instances_contract.py", "test_runtime_page_modules_contract.py"),
    "/api/license": ("test_license_contract.py",),
    "/api/prompt-templates": ("test_prompt_templates_contract.py",),
    "/api/publishing": ("test_publishing_runtime_contract.py",),
    "/api/renders": ("test_renders_runtime_contract.py",),
    "/api/review": ("test_review_contract.py", "test_runtime_page_modules_contract.py"),
    "/api/scripts": ("test_scripts_contract.py",),
    "/api/search": ("test_search_contract.py",),
    "/api/settings": (
        "test_ai_capabilities_contract.py",
        "test_runtime_health_contract.py",
        "test_settings_config_contract.py",
    ),
    "/api/storyboards": ("test_storyboards_contract.py",),
    "/api/subtitles": ("test_subtitle_runtime_contract.py",),
    "/api/tasks": ("test_tasks_contract.py",),
    "/api/video-deconstruction": ("test_video_deconstruction_api.py",),
    "/api/voice": ("test_voice_runtime_contract.py",),
    "/api/workspace": ("test_workspace_runtime_contract.py",),
}


def _load_actual_http_routes() -> set[tuple[str, str]]:
    app = create_app()
    return {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods or set()
        if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }


def _load_documented_http_routes() -> set[tuple[str, str]]:
    text = DOC_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"\|\s*`(GET|POST|PUT|PATCH|DELETE) (/api/[^`]+)`\s*\|", text))


def test_runtime_api_doc_matches_registered_http_routes() -> None:
    actual = _load_actual_http_routes()
    documented = _load_documented_http_routes()

    assert documented == actual


def test_every_runtime_http_module_has_owned_contract_tests() -> None:
    contract_dir = PROJECT_ROOT / "tests" / "contracts"
    available = {path.name: path for path in contract_dir.glob("test_*.py")}

    actual_prefixes = {
        next(prefix for prefix in CONTRACT_OWNERS if path.startswith(prefix))
        for _, path in _load_actual_http_routes()
        if path.startswith("/api/") and not path.startswith("/api/ws")
    }

    assert actual_prefixes == set(CONTRACT_OWNERS)

    missing_files: list[str] = []
    missing_references: list[str] = []
    for prefix, owners in CONTRACT_OWNERS.items():
        for owner in owners:
            owner_path = available.get(owner)
            if owner_path is None:
                missing_files.append(f"{prefix} -> {owner}")
                continue
            text = owner_path.read_text(encoding="utf-8")
            if prefix not in text:
                missing_references.append(f"{prefix} -> {owner}")

    assert not missing_files, f"????????: {missing_files}"
    assert not missing_references, f"?????????????: {missing_references}"
