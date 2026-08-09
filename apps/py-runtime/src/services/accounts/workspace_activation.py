from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from services.accounts.events import append_account_event
from services.accounts.guards import (
    require_account,
    require_revision,
    revision_conflict,
)
from services.accounts.idempotency import MutationCommand
from services.accounts.read_model import AccountReadModel
from services.accounts.results import AccountServiceResponse
from services.accounts.runtime_policy import AccountRuntimePolicy
from services.accounts.unit_of_work import (
    AccountMutationExecutor,
    AccountTransaction,
    MutationWorkResult,
)

log = logging.getLogger(__name__)


class AccountWorkspaceActivationService:
    def __init__(
        self,
        mutation_executor: AccountMutationExecutor,
        *,
        read_model: AccountReadModel,
        policy_provider: Callable[[], AccountRuntimePolicy],
    ) -> None:
        self._mutations = mutation_executor
        self._read_model = read_model
        self._policy_provider = policy_provider

    def activate(
        self,
        account_id: str,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> AccountServiceResponse:
        policy = self._policy_provider()
        execution = self._mutations.execute(
            MutationCommand(
                account_id=account_id,
                operation_name="account.workspace.activate",
                idempotency_key=idempotency_key,
                request_payload={"expectedRevision": expected_revision},
            ),
            lambda transaction: self._activate(
                transaction,
                account_id=account_id,
                expected_revision=expected_revision,
                policy=policy,
            ),
        )
        return AccountServiceResponse.from_mutation(execution)

    def _activate(
        self,
        transaction: AccountTransaction,
        *,
        account_id: str,
        expected_revision: int,
        policy: AccountRuntimePolicy,
    ) -> MutationWorkResult:
        transaction.accounts.acquire_write_lock(
            transaction.session,
            account_id=account_id,
        )
        account = require_account(
            account_id,
            transaction.session,
            transaction.accounts,
        )
        require_revision(account, expected_revision)
        activated_at = _utc_now_text()
        updated = transaction.accounts.activate_workspace(
            transaction.session,
            account_id=account_id,
            expected_revision=expected_revision,
            activated_at=activated_at,
        )
        if updated is None:
            latest = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            raise revision_conflict(latest)
        dto = self._read_model.to_dto(
            transaction,
            updated,
            required_capabilities=policy.required_capabilities,
        )
        invalidations = [
            "accounts:list",
            "current-context",
            f"account:{account_id}:detail",
            f"account:{account_id}:workspace",
        ]
        append_account_event(
            transaction,
            account_id=account_id,
            event_type="account.workspace.activated",
            aggregate_type="account",
            aggregate_id=account_id,
            revision=int(updated.revision),
            invalidations=invalidations,
            values={"lastUsedAt": activated_at},
        )
        return MutationWorkResult(
            response={
                "data": dto.model_dump(mode="json"),
                "meta": {
                    "revision": int(updated.revision),
                    "invalidations": invalidations,
                },
            },
            resource_type="account",
            resource_id=account_id,
        )


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
