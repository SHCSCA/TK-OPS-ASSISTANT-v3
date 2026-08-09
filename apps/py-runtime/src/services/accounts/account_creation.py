from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from domain.models.account import Account
from domain.models.knowledge import AccountKnowledgeBase
from services.accounts.events import append_account_event
from services.accounts.json_codec import dump_json
from services.accounts.read_model import AccountReadModel
from services.accounts.runtime_policy import AccountRuntimePolicy
from services.accounts.unit_of_work import (
    AccountTransaction,
    MutationWorkResult,
)


def create_account_draft(
    transaction: AccountTransaction,
    *,
    name: str,
    username: str | None,
    policy: AccountRuntimePolicy,
    read_model: AccountReadModel,
) -> MutationWorkResult:
    now = _utc_now_text()
    account_id = f"acc_{uuid4().hex}"
    account = transaction.accounts.add(
        transaction.session,
        Account(
            id=account_id,
            name=name,
            platform="tiktok",
            username=username,
            platform_account_id=None,
            avatar_url=None,
            status="draft",
            wizard_completed_at=None,
            status_reason_code=None,
            last_used_at=None,
            last_health_checked_at=None,
            archived_at=None,
            revision=1,
            auth_expires_at=None,
            follower_count=None,
            following_count=None,
            video_count=None,
            tags=None,
            notes=None,
            last_validated_at=None,
            created_at=now,
            updated_at=now,
        ),
    )
    knowledge_base = transaction.knowledge.add_base(
        account_id,
        transaction.session,
        AccountKnowledgeBase(
            id=f"kb_{uuid4().hex}",
            account_id=account_id,
            status="empty",
            rules_json=dump_json(
                {
                    "inclusionRules": {},
                    "exclusionRules": {},
                    "citationPolicy": {},
                }
            ),
            rules_version=0,
            index_revision=0,
            last_indexed_at=None,
            error_code=None,
            error_log_id=None,
            revision=1,
            created_at=now,
            updated_at=now,
        ),
    )
    transaction.configuration.save_publish_defaults(
        account_id,
        transaction.session,
        values={
            "timezone": "UTC",
            "privacy_level": "private",
            "allow_comments": False,
            "allow_duet": False,
            "allow_stitch": False,
            "caption_rules_json": dump_json({}),
        },
        created_at=now,
        updated_at=now,
    )
    dto = read_model.to_dto(
        transaction,
        account,
        required_capabilities=policy.required_capabilities,
    )
    invalidations = ["accounts:list"]
    append_account_event(
        transaction,
        account_id=account_id,
        event_type="account.created",
        aggregate_type="account",
        aggregate_id=account_id,
        revision=1,
        invalidations=invalidations,
        values={
            "status": account.status,
            "knowledgeBaseId": knowledge_base.id,
        },
    )
    return MutationWorkResult(
        response={
            "data": dto.model_dump(mode="json"),
            "meta": {
                "revision": 1,
                "invalidations": invalidations,
            },
        },
        resource_type="account",
        resource_id=account_id,
    )


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
