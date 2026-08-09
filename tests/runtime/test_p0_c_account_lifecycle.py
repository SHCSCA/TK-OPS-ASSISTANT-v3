from __future__ import annotations

import pytest

from errors import DomainError
from services.accounts import (
    AccountHealthFacts,
    AccountStatus,
    ReadinessItem,
    ReadinessStatus,
    UnavailableAIRecipeCopyPort,
    UnavailableAccountAIReadinessPort,
    compute_account_lifecycle,
    ensure_account_transition,
)


def _item(status: ReadinessStatus, label: str = "状态") -> ReadinessItem:
    return ReadinessItem(status=status, label=label)


def _facts(
    *,
    current_status: AccountStatus = AccountStatus.DRAFT,
    archived: bool = False,
    wizard_completed: bool = True,
    has_real_binding: bool = True,
    connection_ever_verified: bool = True,
    connection_status: ReadinessStatus = ReadinessStatus.READY,
    knowledge_status: ReadinessStatus = ReadinessStatus.EMPTY,
    ai_status: ReadinessStatus = ReadinessStatus.READY,
) -> AccountHealthFacts:
    return AccountHealthFacts(
        current_status=current_status,
        archived=archived,
        wizard_completed=wizard_completed,
        has_real_binding=has_real_binding,
        connection_ever_verified=connection_ever_verified,
        connection=_item(connection_status),
        knowledge=_item(knowledge_status),
        ai=_item(ai_status),
    )


def test_lifecycle_applies_archived_and_wizard_priority() -> None:
    archived = compute_account_lifecycle(
        _facts(archived=True, wizard_completed=False)
    )
    draft = compute_account_lifecycle(_facts(wizard_completed=False))

    assert archived.status is AccountStatus.ARCHIVED
    assert draft.status is AccountStatus.DRAFT
    assert archived.readiness.overall.value == "blocked"


def test_first_missing_binding_is_unbound() -> None:
    decision = compute_account_lifecycle(
        _facts(
            has_real_binding=False,
            connection_ever_verified=False,
            connection_status=ReadinessStatus.MISSING,
        )
    )

    assert decision.status is AccountStatus.UNBOUND


@pytest.mark.parametrize(
    "previous_status",
    [AccountStatus.READY, AccountStatus.ATTENTION],
)
def test_previously_operational_account_losing_binding_needs_attention(
    previous_status: AccountStatus,
) -> None:
    decision = compute_account_lifecycle(
        _facts(
            current_status=previous_status,
            has_real_binding=False,
            connection_status=ReadinessStatus.MISSING,
        )
    )

    assert decision.status is AccountStatus.ATTENTION


def test_empty_knowledge_base_does_not_block_ready() -> None:
    decision = compute_account_lifecycle(
        _facts(knowledge_status=ReadinessStatus.EMPTY)
    )

    assert decision.status is AccountStatus.READY
    assert decision.readiness.knowledge.status is ReadinessStatus.EMPTY


@pytest.mark.parametrize(
    ("field", "status"),
    [
        ("connection_status", ReadinessStatus.CHECKING),
        ("knowledge_status", ReadinessStatus.ATTENTION),
        ("ai_status", ReadinessStatus.MISSING),
    ],
)
def test_blocking_dependency_requires_attention(
    field: str,
    status: ReadinessStatus,
) -> None:
    decision = compute_account_lifecycle(_facts(**{field: status}))

    assert decision.status is AccountStatus.ATTENTION


def test_transition_matrix_rejects_ready_to_unbound() -> None:
    with pytest.raises(DomainError) as exc_info:
        ensure_account_transition(AccountStatus.READY, AccountStatus.UNBOUND)

    assert exc_info.value.error_code == "ACCOUNT_STATE_TRANSITION_INVALID"
    assert exc_info.value.status_code == 409


def test_archived_incomplete_draft_can_return_to_draft() -> None:
    ensure_account_transition(AccountStatus.ARCHIVED, AccountStatus.DRAFT)


def test_p0_c_ai_ports_fail_closed_without_fake_readiness() -> None:
    readiness = UnavailableAccountAIReadinessPort().evaluate(
        object(),
        account_id="acc_01",
        required_capability_keys=("script_generation",),
    )
    copy_result = UnavailableAIRecipeCopyPort().copy_active_recipe(
        object(),
        source_account_id="acc_source",
        target_account_id="acc_target",
    )

    assert readiness.status is ReadinessStatus.MISSING
    assert copy_result.copied is False
    assert copy_result.reason_code == "P0E_AI_RECIPE_NOT_AVAILABLE"
