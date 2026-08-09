from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from common.pagination import CursorPosition
from domain.models.ai_configuration_v1 import CapabilityRoute
from services.accounts.idempotency import MutationCommand

from .dto import route_to_dto
from .json_codec import dump_json
from .mutation import (
    AIConfigurationMutationExecutor,
    AIResourceMutation,
)
from .mutation_helpers import (
    append_route_events as _append_route_events,
    route_revision_conflict as _revision_conflict,
    utc_now as _utc_now,
)
from .pagination_helpers import (
    route_cursor_start as _route_cursor_start,
)
from .profile_normalization import (
    normalize_route_payload as _normalize_route_payload,
)
from .query_helpers import require_route as _require_route
from .replay_helpers import load_route_replay as _load_route_replay
from .route_validation import (
    route_invalid as _route_invalid,
    route_issues as _route_issues,
    validation_status as _validation_status,
)
from .unit_of_work import (
    AIConfigurationTransaction,
    AIConfigurationUnitOfWork,
)
from .validation import require_capability_key


class CapabilityRouteService:
    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        mutations: AIConfigurationMutationExecutor,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._mutations = mutations

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
        command = MutationCommand(
            account_id=None,
            operation_name="ai.capability_route.put",
            idempotency_key=idempotency_key,
            request_payload={
                "capabilityKey": capability_key,
                **normalized,
                "expectedRevision": expected_revision,
            },
        )
        return self._mutations.execute(
            command,
            work=lambda transaction: self._put(
                transaction,
                capability_key=capability_key,
                payload=normalized,
                expected_revision=expected_revision,
            ),
            replay_loader=_load_route_replay,
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
        command = MutationCommand(
            account_id=None,
            operation_name="ai.capability_route.validate",
            idempotency_key=idempotency_key,
            request_payload={"capabilityKey": capability_key},
        )
        return self._mutations.execute(
            command,
            work=lambda transaction: self._validate_existing(
                transaction,
                capability_key,
            ),
            replay_loader=_load_route_replay,
        )

    def _put(
        self,
        transaction: AIConfigurationTransaction,
        *,
        capability_key: str,
        payload: Mapping[str, object],
        expected_revision: int,
    ) -> AIResourceMutation:
        current = transaction.ai.routes.get(
            transaction.session,
            capability_key,
        )
        issues = _route_issues(
            transaction,
            capability_key=capability_key,
            payload=payload,
        )
        validation_status = _validation_status(payload, issues)
        if payload["enabled"] and issues:
            raise _route_invalid(issues)
        now = _utc_now()
        changes = {
            "primary_model_profile_id": payload[
                "primaryModelProfileId"
            ],
            "fallback_model_profile_id": payload[
                "fallbackModelProfileId"
            ],
            "prompt_profile_id": payload["promptProfileId"],
            "enabled": payload["enabled"],
            "validation_status": validation_status,
            "validation_issues_json": dump_json(issues),
        }
        if current is None:
            if expected_revision != 0:
                raise _revision_conflict(0)
            row = transaction.ai.routes.add(
                transaction.session,
                CapabilityRoute(
                    id=f"route_{uuid4().hex}",
                    capability_key=capability_key,
                    primary_model_profile_id=changes[
                        "primary_model_profile_id"
                    ],
                    fallback_model_profile_id=changes[
                        "fallback_model_profile_id"
                    ],
                    prompt_profile_id=changes["prompt_profile_id"],
                    enabled=bool(changes["enabled"]),
                    validation_status=validation_status,
                    validation_issues_json=str(
                        changes["validation_issues_json"]
                    ),
                    revision=1,
                    created_at=now,
                    updated_at=now,
                ),
            )
        else:
            row = transaction.ai.routes.update(
                transaction.session,
                capability_key,
                expected_revision=expected_revision,
                changes=changes,
                updated_at=now,
            )
            if row is None:
                raise _revision_conflict(int(current.revision))
        ai_revision = transaction.ai.revisions.increment(
            transaction.session
        )
        invalidations = ("routes", "ai-summary", "recipes")
        _append_route_events(
            transaction,
            row=row,
            ai_revision=ai_revision,
            invalidations=invalidations,
        )
        return AIResourceMutation(
            data=route_to_dto(row),
            resource_type="capability_route",
            resource_id=row.id,
            revision=int(row.revision),
            invalidations=invalidations,
            replay_snapshot_safe=True,
        )

    def _validate_existing(
        self,
        transaction: AIConfigurationTransaction,
        capability_key: str,
    ) -> AIResourceMutation:
        current = _require_route(transaction, capability_key)
        payload = {
            "primaryModelProfileId": current.primary_model_profile_id,
            "fallbackModelProfileId": current.fallback_model_profile_id,
            "promptProfileId": current.prompt_profile_id,
            "enabled": bool(current.enabled),
        }
        issues = _route_issues(
            transaction,
            capability_key=capability_key,
            payload=payload,
        )
        status = _validation_status(payload, issues)
        issues_json = dump_json(issues)
        if (
            current.validation_status == status
            and current.validation_issues_json == issues_json
        ):
            return AIResourceMutation(
                data=route_to_dto(current),
                resource_type="capability_route",
                resource_id=current.id,
                revision=int(current.revision),
                invalidations=("routes", "recipes"),
                replay_snapshot_safe=True,
            )
        updated = transaction.ai.routes.update(
            transaction.session,
            capability_key,
            expected_revision=int(current.revision),
            changes={
                "validation_status": status,
                "validation_issues_json": issues_json,
            },
            updated_at=_utc_now(),
        )
        if updated is None:
            raise _revision_conflict(int(current.revision))
        ai_revision = transaction.ai.revisions.increment(
            transaction.session
        )
        invalidations = ("routes", "recipes")
        _append_route_events(
            transaction,
            row=updated,
            ai_revision=ai_revision,
            invalidations=invalidations,
        )
        return AIResourceMutation(
            data=route_to_dto(updated),
            resource_type="capability_route",
            resource_id=updated.id,
            revision=int(updated.revision),
            invalidations=invalidations,
            replay_snapshot_safe=True,
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
