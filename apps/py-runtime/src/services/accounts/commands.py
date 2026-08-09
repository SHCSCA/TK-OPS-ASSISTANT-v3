from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import urlsplit
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.accounts import (
    AccountCreateInput,
    AccountPatchInput,
    ArchiveInput,
    CompleteWizardInput,
)
from services.accounts.events import append_account_event
from services.accounts.account_creation import create_account_draft
from services.accounts.guards import (
    require_account,
    require_revision,
    revision_conflict,
)
from services.accounts.idempotency import MutationCommand
from services.accounts.lifecycle import ensure_account_transition
from services.accounts.read_model import AccountReadModel
from services.accounts.results import AccountServiceResponse
from services.accounts.runtime_policy import AccountRuntimePolicy
from services.accounts.types import AccountStatus
from services.accounts.unit_of_work import (
    AccountMutationExecutor,
    AccountTransaction,
    AccountUnitOfWork,
    MutationWorkResult,
)

_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._]{2,64}$")
_STABLE_ASSET_REF_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
)
_WIZARD_STEPS = frozenset(
    {
        "identity",
        "connection",
        "positioning",
        "knowledge",
        "ai_recipe",
        "health",
    }
)


class AccountCommandService:
    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        mutation_executor: AccountMutationExecutor,
        *,
        read_model: AccountReadModel,
        policy_provider: Callable[[], AccountRuntimePolicy],
    ) -> None:
        self._unit_of_work = unit_of_work
        self._mutations = mutation_executor
        self._read_model = read_model
        self._policy_provider = policy_provider

    def create(
        self,
        payload: AccountCreateInput,
        *,
        idempotency_key: str,
    ) -> AccountServiceResponse:
        name = _normalize_name(payload.name)
        username = _normalize_username(payload.username)
        platform = payload.platform.strip().lower()
        if platform != "tiktok":
            raise DomainError(
                ErrorCode.ACCOUNT_PLATFORM_UNSUPPORTED,
                "P0 仅支持创建 TikTok 账号",
                status_code=422,
                field_errors=[
                    FieldError(
                        field="platform",
                        code="unsupported_platform",
                        message="当前必须为 tiktok",
                    )
                ],
            )
        policy = self._policy_provider()
        execution = self._mutations.execute(
            MutationCommand(
                account_id=None,
                operation_name="account.create",
                idempotency_key=idempotency_key,
                request_payload={
                    "name": name,
                    "username": username,
                    "platform": platform,
                },
            ),
            lambda transaction: create_account_draft(
                transaction,
                name=name,
                username=username,
                policy=policy,
                read_model=self._read_model,
            ),
        )
        return AccountServiceResponse.from_mutation(execution)

    def patch(
        self,
        account_id: str,
        payload: AccountPatchInput,
        *,
        expected_revision: int,
    ) -> AccountServiceResponse:
        values: dict[str, object] = {}
        if "name" in payload.model_fields_set:
            assert payload.name is not None
            values["name"] = _normalize_name(payload.name)
        if "username" in payload.model_fields_set:
            values["username"] = _normalize_username(payload.username)
        if "avatarAssetRef" in payload.model_fields_set:
            values["avatar_url"] = _normalize_asset_ref(
                payload.avatarAssetRef
            )
        policy = self._policy_provider()
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
            updated = transaction.accounts.update_identity(
                transaction.session,
                account_id=account_id,
                expected_revision=expected_revision,
                values=values,
                updated_at=_utc_now_text(),
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
                f"account:{account_id}:detail",
                f"account:{account_id}:workspace",
            ]
            append_account_event(
                transaction,
                account_id=account_id,
                event_type="account.updated",
                aggregate_type="account",
                aggregate_id=account_id,
                revision=int(updated.revision),
                invalidations=invalidations,
                values={"changedFields": sorted(values)},
            )
            return AccountServiceResponse(
                data=dto.model_dump(mode="json"),
                meta={
                    "revision": int(updated.revision),
                    "invalidations": invalidations,
                },
            )

    def complete_wizard(
        self,
        account_id: str,
        payload: CompleteWizardInput,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> AccountServiceResponse:
        completed = frozenset(payload.completedSteps)
        missing = sorted(_WIZARD_STEPS - completed)
        unexpected = sorted(completed - _WIZARD_STEPS)
        if missing or unexpected:
            raise DomainError(
                ErrorCode.ACCOUNT_WIZARD_INCOMPLETE,
                "账号添加向导尚未完成",
                status_code=409,
                meta={
                    "missingSteps": missing,
                    "unexpectedSteps": unexpected,
                },
            )
        policy = self._policy_provider()
        execution = self._mutations.execute(
            MutationCommand(
                account_id=account_id,
                operation_name="account.wizard.complete",
                idempotency_key=idempotency_key,
                request_payload={
                    "completedSteps": sorted(completed),
                    "expectedRevision": expected_revision,
                },
            ),
            lambda transaction: self._complete_wizard(
                transaction,
                account_id=account_id,
                expected_revision=expected_revision,
                policy=policy,
            ),
        )
        return AccountServiceResponse.from_mutation(execution)

    def archive(
        self,
        account_id: str,
        payload: ArchiveInput,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> AccountServiceResponse:
        policy = self._policy_provider()
        execution = self._mutations.execute(
            MutationCommand(
                account_id=account_id,
                operation_name="account.archive",
                idempotency_key=idempotency_key,
                request_payload={
                    "reason": payload.reason,
                    "expectedRevision": expected_revision,
                },
            ),
            lambda transaction: self._archive(
                transaction,
                account_id=account_id,
                expected_revision=expected_revision,
                reason_provided=payload.reason is not None,
                policy=policy,
            ),
        )
        return AccountServiceResponse.from_mutation(execution)

    def _complete_wizard(
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
        if account.status != AccountStatus.DRAFT.value:
            raise DomainError(
                ErrorCode.ACCOUNT_STATE_TRANSITION_INVALID,
                "只有草稿账号可以完成添加向导",
                status_code=409,
            )
        decision = self._read_model.lifecycle_decision(
            transaction,
            account,
            required_capabilities=policy.required_capabilities,
            wizard_completed_override=True,
        )
        ensure_account_transition(
            AccountStatus.DRAFT,
            AccountStatus.UNBOUND,
        )
        if decision.status is not AccountStatus.UNBOUND:
            ensure_account_transition(
                AccountStatus.UNBOUND,
                decision.status,
            )
        now = _utc_now_text()
        updated = transaction.accounts.set_lifecycle(
            transaction.session,
            account_id=account_id,
            expected_revision=expected_revision,
            status=decision.status.value,
            status_reason_code=_status_reason(decision.status),
            wizard_completed_at=now,
            archived_at=None,
            health_checked_at=account.last_health_checked_at,
            updated_at=now,
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
            f"account:{account_id}:detail",
            f"account:{account_id}:workspace",
            f"account:{account_id}:readiness",
        ]
        append_account_event(
            transaction,
            account_id=account_id,
            event_type="account.updated",
            aggregate_type="account",
            aggregate_id=account_id,
            revision=int(updated.revision),
            invalidations=invalidations,
            values={"status": updated.status, "wizardCompleted": True},
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

    def _archive(
        self,
        transaction: AccountTransaction,
        *,
        account_id: str,
        expected_revision: int,
        reason_provided: bool,
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
        ensure_account_transition(
            AccountStatus(account.status),
            AccountStatus.ARCHIVED,
        )
        now = _utc_now_text()
        updated = transaction.accounts.set_lifecycle(
            transaction.session,
            account_id=account_id,
            expected_revision=expected_revision,
            status=AccountStatus.ARCHIVED.value,
            status_reason_code="USER_ARCHIVED",
            wizard_completed_at=account.wizard_completed_at,
            archived_at=now,
            health_checked_at=account.last_health_checked_at,
            updated_at=now,
        )
        if updated is None:
            latest = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
                allow_archived=True,
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
            f"account:{account_id}:workspace",
        ]
        append_account_event(
            transaction,
            account_id=account_id,
            event_type="account.archived",
            aggregate_type="account",
            aggregate_id=account_id,
            revision=int(updated.revision),
            invalidations=invalidations,
            values={
                "status": updated.status,
                "reasonProvided": reason_provided,
            },
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


def _normalize_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "账号名称不能为空",
            status_code=422,
            field_errors=[
                FieldError(
                    field="name",
                    code="empty_name",
                    message="账号名称不能只包含空白",
                )
            ],
        )
    return normalized


def _normalize_username(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().removeprefix("@")
    if not _USERNAME_PATTERN.fullmatch(normalized):
        raise DomainError(
            ErrorCode.ACCOUNT_USERNAME_INVALID,
            "TikTok 账号标识格式无效",
            status_code=422,
            field_errors=[
                FieldError(
                    field="username",
                    code="invalid_username",
                    message="仅允许 2 至 64 位字母、数字、点和下划线",
                )
            ],
        )
    return normalized


def _normalize_asset_ref(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if _STABLE_ASSET_REF_PATTERN.fullmatch(normalized):
        return normalized
    if (
        normalized.startswith("asset://")
        and len(normalized) > len("asset://")
        and ".." not in normalized
        and "\\" not in normalized
    ):
        return normalized
    parsed = urlsplit(normalized)
    if (
        parsed.scheme == "https"
        and parsed.hostname
        and parsed.username is None
        and parsed.password is None
    ):
        return normalized
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "头像资源引用格式无效",
        status_code=422,
        field_errors=[
            FieldError(
                field="avatarAssetRef",
                code="invalid_asset_ref",
                message="必须使用受控资产引用或安全 HTTPS 地址",
            )
        ],
    )


def _status_reason(status: AccountStatus) -> str | None:
    if status is AccountStatus.UNBOUND:
        return "ACCOUNT_CONNECTION_REQUIRED"
    if status is AccountStatus.ATTENTION:
        return "ACCOUNT_DEPENDENCY_ATTENTION"
    return None


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
