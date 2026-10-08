from __future__ import annotations

from collections.abc import Sequence

from domain.models.ai_configuration_v1 import CapabilityRouteRevision


def dependency_issue(
    code: str,
    *,
    node_type: str,
    node_id: str | None,
    path: str,
    message: str,
) -> dict[str, object]:
    return {
        "code": code,
        "severity": "error",
        "nodeType": node_type,
        "nodeId": node_id,
        "path": path,
        "message": message,
        "blocking": True,
        "evidenceRef": None,
    }


def repair_actions(
    issues: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    seen: set[str] = set()
    for issue in issues:
        code = str(issue["code"])
        if code in seen:
            continue
        seen.add(code)
        provider_issue = code.startswith("AI_PROVIDER") or code.startswith(
            "AI_MODEL"
        )
        actions.append(
            {
                "kind": "navigate",
                "label": "前往验证模型" if provider_issue else "修复能力路由",
                "targetPage": "ai-system-settings",
                "targetSection": "providers" if provider_issue else "routes",
                "targetResourceId": issue.get("nodeId"),
                "requiredAccountId": None,
            }
        )
    return actions


def validate_route_policies(
    route: CapabilityRouteRevision,
    issues: list[dict[str, object]],
) -> None:
    if route.timeout_ms <= 0 or route.max_retries < 0:
        issues.append(
            dependency_issue(
                "AI_ROUTE_INCOMPLETE",
                node_type="capability_route_revision",
                node_id=route.id,
                path="timeoutMs",
                message="能力路由超时或重试策略无效",
            )
        )
    if route.max_concurrency <= 0:
        issues.append(
            dependency_issue(
                "AI_CONCURRENCY_POLICY_INVALID",
                node_type="capability_route_revision",
                node_id=route.id,
                path="maxConcurrency",
                message="能力路由并发策略无效",
            )
        )
    if route.max_cost_micros < 0 or len(route.currency) != 3:
        issues.append(
            dependency_issue(
                "AI_COST_POLICY_INVALID",
                node_type="capability_route_revision",
                node_id=route.id,
                path="maxCostMicros",
                message="能力路由成本策略无效",
            )
        )


__all__ = ["dependency_issue", "repair_actions", "validate_route_policies"]
