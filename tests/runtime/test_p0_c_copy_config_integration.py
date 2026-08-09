from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domain.models.account import Account
from domain.models.account_configuration import (
    AccountConfigCopyRun,
    AccountPublishDefaults,
    BrandKit,
    PositioningProfile,
)
from domain.models.knowledge import AccountKnowledgeBase, KnowledgeSource
from domain.models.mutation_idempotency import RuntimeMutationIdempotency
from domain.models.runtime_event import RuntimeEvent
from errors import ErrorCode
from services.accounts.types import RecipeCopyDecision
from tests.runtime.p0c_account_integration_support import (
    create_account,
    error_code,
    mutation_headers,
    session,
)

_COPY_SECTIONS = [
    "positioning",
    "knowledgeRules",
    "brandKit",
    "aiRecipe",
    "publishDefaults",
]


def test_copy_config_uses_whitelist_and_skips_unavailable_ai_recipe(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client
    source_id, source_revision = create_account(
        client,
        name="复制来源账号",
        idempotency_key="idem_copy_source",
    )
    source_revision = _configure_source_account(
        client,
        account_id=source_id,
        revision=source_revision,
    )
    target_id, target_revision = create_account(
        client,
        name="复制目标账号",
        idempotency_key="idem_copy_target",
    )

    copied = client.post(
        f"/api/v1/accounts/{target_id}/copy-config",
        headers=mutation_headers(
            revision=target_revision,
            idempotency_key="idem_copy_all_sections",
            operation_id="op_copy_all_sections",
        ),
        json={
            "sourceAccountId": source_id,
            "sections": _COPY_SECTIONS,
        },
    )

    assert copied.status_code == 200, copied.text
    result = copied.json()["data"]
    assert result["requestedSections"] == _COPY_SECTIONS
    assert result["copiedSections"] == [
        "positioning",
        "knowledgeRules",
        "brandKit",
        "publishDefaults",
    ]
    assert result["skippedSections"] == [
        {
            "section": "aiRecipe",
            "reasonCode": "AI_RECIPE_NOT_CONFIGURED",
        }
    ]
    assert result["targetRevision"] == target_revision + 1

    with session(client) as database:
        source_positioning = database.scalar(
            select(PositioningProfile).where(
                PositioningProfile.account_id == source_id,
                PositioningProfile.status == "active",
            )
        )
        target_positioning = database.scalar(
            select(PositioningProfile).where(
                PositioningProfile.account_id == target_id,
                PositioningProfile.status == "active",
            )
        )
        source_knowledge = database.scalar(
            select(AccountKnowledgeBase).where(
                AccountKnowledgeBase.account_id == source_id
            )
        )
        target_knowledge = database.scalar(
            select(AccountKnowledgeBase).where(
                AccountKnowledgeBase.account_id == target_id
            )
        )
        source_brand = database.scalar(
            select(BrandKit).where(
                BrandKit.account_id == source_id,
                BrandKit.status == "active",
            )
        )
        target_brand = database.scalar(
            select(BrandKit).where(
                BrandKit.account_id == target_id,
                BrandKit.status == "active",
            )
        )
        source_defaults = database.get(AccountPublishDefaults, source_id)
        target_defaults = database.get(AccountPublishDefaults, target_id)
        target_sources = database.scalar(
            select(func.count())
            .select_from(KnowledgeSource)
            .where(KnowledgeSource.account_id == target_id)
        )
        target = database.get(Account, target_id)

        assert source_positioning is not None
        assert target_positioning is not None
        assert source_knowledge is not None
        assert target_knowledge is not None
        assert source_brand is not None
        assert target_brand is not None
        assert source_defaults is not None
        assert target_defaults is not None
        assert target is not None
        assert target.status == "draft"
        assert int(target.revision) == target_revision + 1
        assert target_sources == 0
        assert (
            target_positioning.audience_json,
            target_positioning.content_pillars_json,
            target_positioning.voice_style_json,
            target_positioning.prohibited_terms_json,
            target_positioning.publishing_constraints_json,
        ) == (
            source_positioning.audience_json,
            source_positioning.content_pillars_json,
            source_positioning.voice_style_json,
            source_positioning.prohibited_terms_json,
            source_positioning.publishing_constraints_json,
        )
        assert target_knowledge.rules_json == source_knowledge.rules_json
        assert (
            target_brand.visual_style_json,
            target_brand.colors_json,
            target_brand.fonts_json,
            target_brand.logo_asset_refs_json,
            target_brand.voice_rules_json,
        ) == (
            source_brand.visual_style_json,
            source_brand.colors_json,
            source_brand.fonts_json,
            source_brand.logo_asset_refs_json,
            source_brand.voice_rules_json,
        )
        assert (
            target_defaults.timezone,
            target_defaults.privacy_level,
            target_defaults.allow_comments,
            target_defaults.allow_duet,
            target_defaults.allow_stitch,
            target_defaults.caption_rules_json,
        ) == (
            source_defaults.timezone,
            source_defaults.privacy_level,
            source_defaults.allow_comments,
            source_defaults.allow_duet,
            source_defaults.allow_stitch,
            source_defaults.caption_rules_json,
        )

    non_draft_id, non_draft_revision = create_account(
        client,
        name="非草稿复制目标",
        idempotency_key="idem_non_draft_copy_target",
    )
    wizard = client.post(
        f"/api/v1/accounts/{non_draft_id}/complete-wizard",
        headers=mutation_headers(
            revision=non_draft_revision,
            idempotency_key="idem_complete_non_draft_target",
        ),
        json={
            "completedSteps": [
                "identity",
                "connection",
                "positioning",
                "knowledge",
                "ai_recipe",
                "health",
            ]
        },
    )
    assert wizard.status_code == 200
    rejected = client.post(
        f"/api/v1/accounts/{non_draft_id}/copy-config",
        headers=mutation_headers(
            revision=int(wizard.json()["meta"]["revision"]),
            idempotency_key="idem_copy_into_non_draft",
        ),
        json={
            "sourceAccountId": source_id,
            "sections": ["positioning"],
        },
    )
    assert rejected.status_code == 409
    assert error_code(
        rejected
    ) == ErrorCode.ACCOUNT_STATE_TRANSITION_INVALID
    assert source_revision > 1


def test_copy_config_rolls_back_every_section_when_ai_port_fails(
    licensed_runtime_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = licensed_runtime_client
    source_id, source_revision = create_account(
        client,
        name="原子复制来源",
        idempotency_key="idem_atomic_copy_source",
    )
    _configure_source_account(
        client,
        account_id=source_id,
        revision=source_revision,
    )
    target_id, target_revision = create_account(
        client,
        name="原子复制目标",
        idempotency_key="idem_atomic_copy_target",
    )
    copy_service = client.app.state.account_copy_service
    monkeypatch.setattr(
        copy_service,
        "_ai_recipe_copy_port",
        _FailingAIRecipeCopyPort(),
    )

    failed = client.post(
        f"/api/v1/accounts/{target_id}/copy-config",
        headers=mutation_headers(
            revision=target_revision,
            idempotency_key="idem_atomic_copy_failure",
            operation_id="op_atomic_copy_failure",
        ),
        json={
            "sourceAccountId": source_id,
            "sections": ["positioning", "aiRecipe"],
        },
    )

    assert failed.status_code == 500
    assert error_code(failed) == ErrorCode.INTERNAL_ERROR
    with session(client) as database:
        target = database.get(Account, target_id)
        positioning_count = database.scalar(
            select(func.count())
            .select_from(PositioningProfile)
            .where(PositioningProfile.account_id == target_id)
        )
        copy_run_count = database.scalar(
            select(func.count())
            .select_from(AccountConfigCopyRun)
            .where(AccountConfigCopyRun.target_account_id == target_id)
        )
        event_count = database.scalar(
            select(func.count())
            .select_from(RuntimeEvent)
            .where(
                RuntimeEvent.account_id == target_id,
                RuntimeEvent.event_type == "account.config.copied",
            )
        )
        idempotency_count = database.scalar(
            select(func.count())
            .select_from(RuntimeMutationIdempotency)
            .where(
                RuntimeMutationIdempotency.account_id == target_id,
                RuntimeMutationIdempotency.operation_name
                == "account.config.copy",
            )
        )
        assert target is not None
        assert int(target.revision) == target_revision
        assert positioning_count == 0
        assert copy_run_count == 0
        assert event_count == 0
        assert idempotency_count == 0


def _configure_source_account(
    client: TestClient,
    *,
    account_id: str,
    revision: int,
) -> int:
    created_positioning = client.post(
        f"/api/v1/accounts/{account_id}/positioning/versions",
        headers=mutation_headers(
            revision=revision,
            idempotency_key=f"idem_positioning_{account_id}",
        ),
        json={
            "audience": {"segment": "独立创作者"},
            "contentPillars": ["AI 工具", "内容方法"],
            "tone": {"style": "清晰克制"},
            "prohibitedTopics": ["虚假承诺"],
            "publishingConstraints": {"maxDurationSeconds": 90},
        },
    )
    assert created_positioning.status_code == 201
    revision = int(created_positioning.json()["meta"]["revision"])
    version = int(created_positioning.json()["data"]["version"])
    activated = client.post(
        (
            f"/api/v1/accounts/{account_id}/positioning/"
            f"versions/{version}/activate"
        ),
        headers=mutation_headers(
            revision=revision,
            idempotency_key=f"idem_activate_positioning_{account_id}",
        ),
    )
    assert activated.status_code == 200
    revision = int(activated.json()["meta"]["revision"])

    knowledge = client.patch(
        f"/api/v1/accounts/{account_id}/knowledge",
        headers=mutation_headers(revision=revision),
        json={
            "inclusionRules": {"languages": ["zh-CN"]},
            "exclusionRules": {"staleAfterDays": 30},
            "citationPolicy": {"required": True},
        },
    )
    assert knowledge.status_code == 200
    revision = int(knowledge.json()["meta"]["revision"])

    brand = client.put(
        f"/api/v1/accounts/{account_id}/brand-kit",
        headers=mutation_headers(
            revision=revision,
            idempotency_key=f"idem_brand_{account_id}",
        ),
        json={
            "colors": ["#7057FF", "#101828"],
            "fonts": ["Inter", "Noto Sans SC"],
            "logoAssetRefs": ["asset://brand-logo"],
            "visualRules": {"density": "calm"},
            "voiceRules": {"opening": "直接给结论"},
        },
    )
    assert brand.status_code == 200
    revision = int(brand.json()["meta"]["revision"])

    defaults = client.put(
        f"/api/v1/accounts/{account_id}/publish-defaults",
        headers=mutation_headers(revision=revision),
        json={
            "timezone": "Asia/Shanghai",
            "privacyLevel": "public",
            "allowComments": True,
            "allowDuet": False,
            "allowStitch": False,
            "captionRules": {"suffix": "#AI内容"},
        },
    )
    assert defaults.status_code == 200
    return int(defaults.json()["meta"]["revision"])


class _FailingAIRecipeCopyPort:
    def copy_active_recipe(
        self,
        session: Session,
        *,
        source_account_id: str,
        target_account_id: str,
    ) -> RecipeCopyDecision:
        del session, source_account_id, target_account_id
        raise RuntimeError("模拟 AI 配方复制失败")
