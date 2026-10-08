from __future__ import annotations

from collections.abc import Mapping

from common.pagination import CursorPosition
from services.accounts.idempotency import MutationCommand

from .mutation import AIConfigurationMutationExecutor, AIResourceMutation
from .query_helpers import require_route
from .route_revision_lifecycle import (
    activate_route_revision,
    create_route_revision,
    put_compatibility_route,
    validate_compatibility_route,
    validate_route_revision,
)
from .route_revision_queries import (
    load_revision_replay,
    load_route_replay,
    load_snapshot_replay,
    revision_start,
)
from .route_revision_support import (
    normalize_route_revision_payload,
    route_revision_to_dto,
)
from .unit_of_work import AIConfigurationTransaction, AIConfigurationUnitOfWork
from .validation import require_capability_key


class CapabilityRouteRevisionService:
    """提供能力路由草稿、校验快照和激活的唯一写路径。"""

    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        mutations: AIConfigurationMutationExecutor,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._mutations = mutations

    def list_revisions(
        self,
        capability_key: str,
        *,
        cursor: CursorPosition | None,
        limit: int,
    ) -> tuple[dict[str, object], CursorPosition | None]:
        capability_key = require_capability_key(capability_key)
        with self._unit_of_work.read() as transaction:
            route = require_route(transaction, capability_key)
            rows = transaction.ai.route_revisions.list(
                transaction.session,
                route.id,
            )
            start = revision_start(rows, cursor)
            page = rows[start : start + limit]
            next_cursor = (
                CursorPosition(
                    sort_value=str(page[-1].revision),
                    resource_id=page[-1].id,
                )
                if page and start + limit < len(rows)
                else None
            )
            return (
                {
                    "items": [route_revision_to_dto(row) for row in page],
                    "totalKnown": len(rows),
                },
                next_cursor,
            )

    def create_revision(
        self,
        capability_key: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> AIResourceMutation:
        capability_key = require_capability_key(capability_key)
        normalized = normalize_route_revision_payload(payload)
        command = MutationCommand(
            account_id=None,
            operation_name="ai.capability_route_revision.create",
            idempotency_key=idempotency_key,
            request_payload={
                "capabilityKey": capability_key,
                "payload": normalized,
                "expectedRevision": expected_revision,
            },
        )
        return self._mutations.execute(
            command,
            work=lambda transaction: create_route_revision(
                transaction,
                capability_key=capability_key,
                payload=normalized,
                expected_revision=expected_revision,
            ),
            replay_loader=load_revision_replay,
        )

    def validate_revision(
        self,
        capability_key: str,
        revision: int,
        *,
        idempotency_key: str,
    ) -> AIResourceMutation:
        capability_key = require_capability_key(capability_key)
        command = MutationCommand(
            account_id=None,
            operation_name="ai.capability_route_revision.validate",
            idempotency_key=idempotency_key,
            request_payload={
                "capabilityKey": capability_key,
                "revision": revision,
            },
        )
        return self._mutations.execute(
            command,
            work=lambda transaction: validate_route_revision(
                transaction,
                capability_key=capability_key,
                revision=revision,
            ),
            replay_loader=load_snapshot_replay,
        )

    def activate_revision(
        self,
        capability_key: str,
        revision: int,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> AIResourceMutation:
        capability_key = require_capability_key(capability_key)
        command = MutationCommand(
            account_id=None,
            operation_name="ai.capability_route_revision.activate",
            idempotency_key=idempotency_key,
            request_payload={
                "capabilityKey": capability_key,
                "revision": revision,
                "expectedRevision": expected_revision,
            },
        )
        return self._mutations.execute(
            command,
            work=lambda transaction: activate_route_revision(
                transaction,
                capability_key=capability_key,
                revision=revision,
                expected_revision=expected_revision,
            ),
            replay_loader=load_route_replay,
        )

    def compatibility_put(
        self,
        capability_key: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> AIResourceMutation:
        capability_key = require_capability_key(capability_key)
        command = MutationCommand(
            account_id=None,
            operation_name="ai.capability_route.put",
            idempotency_key=idempotency_key,
            request_payload={
                "capabilityKey": capability_key,
                "payload": dict(payload),
                "expectedRevision": expected_revision,
            },
        )
        return self._mutations.execute(
            command,
            work=lambda transaction: put_compatibility_route(
                transaction,
                capability_key=capability_key,
                payload=payload,
                expected_revision=expected_revision,
            ),
            replay_loader=load_route_replay,
        )

    def compatibility_validate(
        self,
        capability_key: str,
        *,
        idempotency_key: str,
    ) -> AIResourceMutation:
        capability_key = require_capability_key(capability_key)
        command = MutationCommand(
            account_id=None,
            operation_name="ai.capability_route.validate",
            idempotency_key=idempotency_key,
            request_payload={"capabilityKey": capability_key},
        )
        return self._mutations.execute(
            command,
            work=lambda transaction: validate_compatibility_route(
                transaction,
                capability_key=capability_key,
            ),
            replay_loader=load_snapshot_replay,
        )

__all__ = ["CapabilityRouteRevisionService"]
