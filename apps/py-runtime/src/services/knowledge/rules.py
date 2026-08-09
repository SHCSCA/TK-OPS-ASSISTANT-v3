from __future__ import annotations

from schemas.v1.knowledge import KnowledgeRulesPatchInput
from services.accounts.events import append_account_event
from services.accounts.guards import require_account, require_revision
from services.accounts.json_codec import dump_json
from services.accounts.results import AccountServiceResponse
from services.accounts.unit_of_work import AccountUnitOfWork
from services.knowledge.presentation import knowledge_to_dto
from services.knowledge.support import (
    bump_account,
    knowledge_base_missing,
    knowledge_invalidations,
    latest_snapshot_id,
    utc_now_text,
)


class KnowledgeRulesService:
    def __init__(self, unit_of_work: AccountUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def patch(
        self,
        account_id: str,
        payload: KnowledgeRulesPatchInput,
        *,
        expected_revision: int,
    ) -> AccountServiceResponse:
        with self._unit_of_work.write() as transaction:
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
            now = utc_now_text()
            knowledge_base = transaction.knowledge.update_rules(
                account_id,
                transaction.session,
                rules_json=dump_json(payload.model_dump(mode="json")),
                updated_at=now,
            )
            if knowledge_base is None:
                raise knowledge_base_missing()
            updated = bump_account(
                transaction,
                account_id=account_id,
                expected_revision=expected_revision,
                updated_at=now,
            )
            dto = knowledge_to_dto(
                account_id,
                knowledge_base,
                source_counts=transaction.knowledge.source_counts(
                    account_id,
                    transaction.session,
                ),
                latest_snapshot_id=latest_snapshot_id(
                    transaction,
                    account_id,
                ),
                account_revision=int(updated.revision),
            )
            invalidations = knowledge_invalidations(account_id)
            append_account_event(
                transaction,
                account_id=account_id,
                event_type="knowledge.rules.updated",
                aggregate_type="account_knowledge_base",
                aggregate_id=knowledge_base.id,
                revision=int(updated.revision),
                invalidations=invalidations,
                values={"rulesVersion": knowledge_base.rules_version},
                topic_resource="knowledge",
            )
            return AccountServiceResponse(
                data=dto.model_dump(mode="json"),
                meta={
                    "revision": int(updated.revision),
                    "invalidations": invalidations,
                },
            )
