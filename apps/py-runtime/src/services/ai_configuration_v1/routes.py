from __future__ import annotations

from collections.abc import Mapping

from common.pagination import CursorPosition
from domain.models.ai_configuration_v1 import CapabilityRoute

from .dto import route_to_dto
from .mutation import AIResourceMutation
from .pagination_helpers import (
    route_cursor_start as _route_cursor_start,
)
from .profile_normalization import (
    normalize_route_payload as _normalize_route_payload,
)
from .route_revisions import CapabilityRouteRevisionService
from .route_validation import (
    route_issues as _route_issues,
    validation_status as _validation_status,
)
from .unit_of_work import AIConfigurationTransaction, AIConfigurationUnitOfWork
from .validation import require_capability_key


class CapabilityRouteService:
    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        revisions: CapabilityRouteRevisionService,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._revisions = revisions

    def list_capability_routes(
        self,
        *,
        capability_key: str | None = None,
        validation_status: str | None = None,
        cursor: CursorPosition | None = None,
        limit: int = 50,
    ) -> tuple[dict[str, object], CursorPosition | None]:
        if capability_key is not None:
            require_capability_key(capability_key)
        with self._unit_of_work.read() as transaction:
            rows = transaction.ai.routes.list(
                transaction.session,
                capability_key=capability_key,
            )
            resolved = tuple(
                (row, _current_route_dto(transaction, row))
                for row in rows
            )
            if validation_status is not None:
                resolved = tuple(
                    item
                    for item in resolved
                    if item[1]["validationStatus"] == validation_status
                )
            resolved_rows = tuple(item[0] for item in resolved)
            start = _route_cursor_start(resolved_rows, cursor)
            page = resolved[start : start + limit]
            next_position = (
                CursorPosition(
                    sort_value=page[-1][0].capability_key,
                    resource_id=page[-1][0].id,
                )
                if start + limit < len(resolved) and page
                else None
            )
            return (
                {
                    "items": [item[1] for item in page],
                    "totalKnown": len(resolved),
                },
                next_position,
            )

    def put_capability_route(
        self,
        capability_key: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        capability_key = require_capability_key(capability_key)
        normalized = _normalize_route_payload(payload)
        return self._revisions.compatibility_put(
            capability_key,
            normalized,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
        )

    def validate_capability_route(
        self,
        capability_key: str,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        capability_key = require_capability_key(capability_key)
        return self._revisions.compatibility_validate(
            capability_key,
            idempotency_key=idempotency_key,
        )


def _current_route_dto(
    transaction: AIConfigurationTransaction,
    row: CapabilityRoute,
) -> dict[str, object]:
    payload = {
        "primaryModelProfileId": row.primary_model_profile_id,
        "fallbackModelProfileId": row.fallback_model_profile_id,
        "promptProfileId": row.prompt_profile_id,
        "enabled": bool(row.enabled),
    }
    issues = _route_issues(
        transaction,
        capability_key=row.capability_key,
        payload=payload,
    )
    data = route_to_dto(row)
    data["validationStatus"] = _validation_status(payload, issues)
    data["validationIssues"] = issues
    return data
