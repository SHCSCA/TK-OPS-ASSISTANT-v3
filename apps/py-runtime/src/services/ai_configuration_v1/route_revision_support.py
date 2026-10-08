from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import uuid4

from domain.models.ai_configuration_v1 import CapabilityRouteRevision
from errors import DomainError, ErrorCode

from .json_codec import content_hash, dump_json, load_object
from .mutation_helpers import utc_now
from .validation import require_object


def normalize_route_revision_payload(
    payload: Mapping[str, object],
) -> dict[str, object]:
    raw_candidates = payload.get("candidates")
    if (
        not isinstance(raw_candidates, Sequence)
        or isinstance(raw_candidates, (str, bytes))
        or len(raw_candidates) > 8
    ):
        raise _invalid("能力路由候选数量无效")
    enabled = payload.get("enabled", True)
    if not isinstance(enabled, bool):
        raise _invalid("能力路由启用状态无效")
    if enabled and not raw_candidates:
        raise _invalid("启用能力路由至少需要一个候选模型")
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw_candidates:
        if not isinstance(item, Mapping):
            raise _invalid("能力路由候选格式无效")
        model_id = item.get("modelProfileId")
        if (
            not isinstance(model_id, str)
            or not model_id.strip()
            or model_id != model_id.strip()
            or model_id in seen
        ):
            raise _invalid("能力路由候选模型重复或无效")
        seen.add(model_id)
        candidates.append({"modelProfileId": model_id})
    prompt_id = payload.get("promptProfileId")
    if prompt_id is not None and (
        not isinstance(prompt_id, str) or not prompt_id.strip()
    ):
        raise _invalid("能力路由 Prompt 标识无效")
    timeout_ms = _bounded_int(payload.get("timeoutMs", 120_000), 1, 86_400_000)
    max_retries = _bounded_int(payload.get("maxRetries", 1), 0, 3)
    max_concurrency = _bounded_int(payload.get("maxConcurrency", 1), 1, 32)
    max_cost = _bounded_int(payload.get("maxCostMicros", 0), 0, 10**12)
    currency = payload.get("currency", "USD")
    if (
        not isinstance(currency, str)
        or len(currency) != 3
        or not currency.isalpha()
        or currency != currency.upper()
    ):
        raise _invalid("能力路由币种或启用状态无效")
    return {
        "promptProfileId": prompt_id,
        "candidates": candidates,
        "timeoutMs": timeout_ms,
        "maxRetries": max_retries,
        "retryPolicy": require_object(
            payload.get("retryPolicy", {}),
            field="retryPolicy",
        ),
        "maxConcurrency": max_concurrency,
        "maxCostMicros": max_cost,
        "currency": currency,
        "enabled": enabled,
    }


def legacy_route_payload(
    payload: Mapping[str, object],
) -> dict[str, object]:
    primary = payload.get("primaryModelProfileId")
    fallback = payload.get("fallbackModelProfileId")
    candidates = [
        {"modelProfileId": item}
        for item in (primary, fallback)
        if isinstance(item, str)
    ]
    return normalize_route_revision_payload(
        {
            "promptProfileId": payload.get("promptProfileId"),
            "candidates": candidates,
            "timeoutMs": 120_000,
            "maxRetries": 1,
            "retryPolicy": {},
            "maxConcurrency": 1,
            "maxCostMicros": 0,
            "currency": "USD",
            "enabled": bool(payload.get("enabled")),
        }
    )


def build_route_revision(
    *,
    route_id: str,
    capability_key: str,
    revision: int,
    payload: Mapping[str, object],
) -> CapabilityRouteRevision:
    digest = route_revision_content_hash(
        capability_key=capability_key,
        payload=payload,
    )
    return CapabilityRouteRevision(
        id=f"rrev_{uuid4().hex}",
        capability_route_id=route_id,
        capability_key=capability_key,
        revision=revision,
        status="draft",
        prompt_profile_id=(
            str(payload["promptProfileId"])
            if payload.get("promptProfileId") is not None
            else None
        ),
        candidate_policy_json=dump_json(
            {"candidates": payload["candidates"]}
        ),
        timeout_ms=int(payload["timeoutMs"]),
        max_retries=int(payload["maxRetries"]),
        retry_policy_json=dump_json(payload["retryPolicy"]),
        max_concurrency=int(payload["maxConcurrency"]),
        max_cost_micros=int(payload["maxCostMicros"]),
        currency=str(payload["currency"]),
        enabled=bool(payload["enabled"]),
        dependency_snapshot_id=None,
        content_hash=digest,
        created_at=utc_now(),
    )


def route_revision_to_dto(
    row: CapabilityRouteRevision,
) -> dict[str, object]:
    candidate_policy = load_object(
        row.candidate_policy_json,
        label="能力路由候选策略",
    )
    return {
        "id": row.id,
        "capabilityRouteId": row.capability_route_id,
        "capabilityKey": row.capability_key,
        "revision": int(row.revision),
        "status": row.status,
        "promptProfileId": row.prompt_profile_id,
        "candidates": candidate_policy.get("candidates", []),
        "timeoutMs": int(row.timeout_ms),
        "maxRetries": int(row.max_retries),
        "retryPolicy": load_object(
            row.retry_policy_json,
            label="能力路由重试策略",
        ),
        "maxConcurrency": int(row.max_concurrency),
        "maxCostMicros": int(row.max_cost_micros),
        "currency": row.currency,
        "enabled": bool(row.enabled),
        "dependencySnapshotId": row.dependency_snapshot_id,
        "contentHash": row.content_hash,
        "createdAt": row.created_at,
    }


def route_revision_mirror(
    row: CapabilityRouteRevision,
    *,
    issues: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    candidate_policy = load_object(
        row.candidate_policy_json,
        label="能力路由候选策略",
    )
    raw_candidates = candidate_policy.get("candidates", [])
    model_ids = [
        item["modelProfileId"]
        for item in raw_candidates
        if isinstance(item, dict) and isinstance(item.get("modelProfileId"), str)
    ]
    return {
        "primary_model_profile_id": model_ids[0] if model_ids else None,
        "fallback_model_profile_id": model_ids[1] if len(model_ids) > 1 else None,
        "prompt_profile_id": row.prompt_profile_id,
        "enabled": bool(row.enabled),
        "validation_status": "valid" if not issues and row.enabled else "incomplete",
        "validation_issues_json": dump_json(list(issues)),
    }


def route_revision_content_hash(
    *,
    capability_key: str,
    payload: Mapping[str, object],
) -> str:
    return content_hash(
        {
            "capabilityKey": capability_key,
            "promptProfileId": payload.get("promptProfileId"),
            "candidates": payload["candidates"],
            "timeoutMs": payload["timeoutMs"],
            "maxRetries": payload["maxRetries"],
            "retryPolicy": payload["retryPolicy"],
            "maxConcurrency": payload["maxConcurrency"],
            "maxCostMicros": payload["maxCostMicros"],
            "currency": payload["currency"],
            "enabled": payload["enabled"],
        }
    )


def _bounded_int(value: object, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise _invalid("能力路由数值策略无效")
    return value


def _invalid(message: str) -> DomainError:
    return DomainError(
        ErrorCode.CAPABILITY_ROUTE_INVALID,
        message,
        status_code=422,
    )


__all__ = [
    "build_route_revision",
    "legacy_route_payload",
    "normalize_route_revision_payload",
    "route_revision_mirror",
    "route_revision_to_dto",
]
