from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from domain.models.account_configuration import (
    AccountPublishDefaults,
    BrandKit,
)
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.account_configuration import (
    ActiveBrandKitDto,
    BrandKitDto,
    BrandKitVersionInput,
    BrandKitVersionSummaryDto,
    PublishDefaultsDto,
    PublishDefaultsInput,
)
from services.accounts.events import append_account_event
from services.accounts.guards import (
    require_account,
    require_revision,
    revision_conflict,
)
from services.accounts.idempotency import MutationCommand
from services.accounts.json_codec import (
    content_hash,
    dump_json,
    load_json_list,
    load_json_object,
)
from services.accounts.results import AccountServiceResponse
from services.accounts.unit_of_work import (
    AccountMutationExecutor,
    AccountTransaction,
    AccountUnitOfWork,
    MutationWorkResult,
)

_CONTROLLED_ASSET_REF_PATTERN = re.compile(
    r"^(?:asset://[A-Za-z0-9._:-]+|asset_[A-Za-z0-9._:-]+)$"
)


class AccountBrandingService:
    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        mutation_executor: AccountMutationExecutor,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._mutations = mutation_executor

    def get_brand_kit(self, account_id: str) -> BrandKitDto:
        with self._unit_of_work.read() as transaction:
            account = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            rows = transaction.configuration.list_brand_kits(
                account_id,
                transaction.session,
            )
            return _brand_kit_to_dto(
                account_id,
                rows,
                account_revision=int(account.revision),
            )

    def put_brand_kit(
        self,
        account_id: str,
        payload: BrandKitVersionInput,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> AccountServiceResponse:
        _validate_brand_kit(payload)
        request_payload = payload.model_dump(mode="json")
        request_payload["expectedRevision"] = expected_revision
        execution = self._mutations.execute(
            MutationCommand(
                account_id=account_id,
                operation_name="account.brand_kit.put",
                idempotency_key=idempotency_key,
                request_payload=request_payload,
            ),
            lambda transaction: self._put_brand_kit(
                transaction,
                account_id=account_id,
                payload=payload,
                expected_revision=expected_revision,
            ),
        )
        return AccountServiceResponse.from_mutation(execution)

    def get_publish_defaults(
        self,
        account_id: str,
    ) -> PublishDefaultsDto:
        with self._unit_of_work.read() as transaction:
            account = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            stored = transaction.configuration.get_publish_defaults(
                account_id,
                transaction.session,
            )
            if stored is None:
                raise DomainError(
                    ErrorCode.PUBLISH_DEFAULTS_INVALID,
                    "账号发布默认值尚未初始化",
                    status_code=409,
                )
            return _publish_defaults_to_dto(
                stored,
                account_revision=int(account.revision),
            )

    def put_publish_defaults(
        self,
        account_id: str,
        payload: PublishDefaultsInput,
        *,
        expected_revision: int,
    ) -> AccountServiceResponse:
        timezone, privacy_level = _validate_publish_defaults(payload)
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
            now = _utc_now_text()
            stored = transaction.configuration.save_publish_defaults(
                account_id,
                transaction.session,
                values={
                    "timezone": timezone,
                    "privacy_level": privacy_level,
                    "allow_comments": payload.allowComments,
                    "allow_duet": payload.allowDuet,
                    "allow_stitch": payload.allowStitch,
                    "caption_rules_json": dump_json(payload.captionRules),
                },
                created_at=now,
                updated_at=now,
            )
            updated_account = transaction.accounts.bump_revision(
                transaction.session,
                account_id=account_id,
                expected_revision=expected_revision,
                updated_at=now,
            )
            if updated_account is None:
                latest = require_account(
                    account_id,
                    transaction.session,
                    transaction.accounts,
                )
                raise revision_conflict(latest)
            dto = _publish_defaults_to_dto(
                stored,
                account_revision=int(updated_account.revision),
            )
            invalidations = [
                f"account:{account_id}:publish-defaults",
                f"account:{account_id}:workspace",
            ]
            append_account_event(
                transaction,
                account_id=account_id,
                event_type="publish.defaults.updated",
                aggregate_type="account_publish_defaults",
                aggregate_id=account_id,
                revision=int(updated_account.revision),
                invalidations=invalidations,
                values={"resourceRevision": int(stored.revision)},
            )
            return AccountServiceResponse(
                data=dto.model_dump(mode="json"),
                meta={
                    "revision": int(updated_account.revision),
                    "invalidations": invalidations,
                },
            )

    @staticmethod
    def _put_brand_kit(
        transaction: AccountTransaction,
        *,
        account_id: str,
        payload: BrandKitVersionInput,
        expected_revision: int,
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
        now = _utc_now_text()
        version = transaction.configuration.next_brand_kit_version(
            account_id,
            transaction.session,
        )
        brand_kit = BrandKit(
            id=f"brand_{uuid4().hex}",
            account_id=account_id,
            version=version,
            status="active",
            visual_style_json=dump_json(payload.visualRules),
            colors_json=dump_json(payload.colors),
            fonts_json=dump_json(payload.fonts),
            logo_asset_refs_json=dump_json(payload.logoAssetRefs),
            voice_rules_json=dump_json(payload.voiceRules),
            revision=1,
            created_at=now,
            activated_at=now,
        )
        transaction.configuration.add_and_activate_brand_kit(
            account_id,
            transaction.session,
            brand_kit,
        )
        updated_account = transaction.accounts.bump_revision(
            transaction.session,
            account_id=account_id,
            expected_revision=expected_revision,
            updated_at=now,
        )
        if updated_account is None:
            latest = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            raise revision_conflict(latest)
        rows = transaction.configuration.list_brand_kits(
            account_id,
            transaction.session,
        )
        dto = _brand_kit_to_dto(
            account_id,
            rows,
            account_revision=int(updated_account.revision),
        )
        invalidations = [
            f"account:{account_id}:brand-kit",
            f"account:{account_id}:workspace",
        ]
        append_account_event(
            transaction,
            account_id=account_id,
            event_type="brand-kit.updated",
            aggregate_type="brand_kit",
            aggregate_id=brand_kit.id,
            revision=int(updated_account.revision),
            invalidations=invalidations,
            values={
                "version": brand_kit.version,
                "resourceRevision": brand_kit.revision,
            },
        )
        return MutationWorkResult(
            response={
                "data": dto.model_dump(mode="json"),
                "meta": {
                    "revision": int(updated_account.revision),
                    "invalidations": invalidations,
                },
            },
            resource_type="brand_kit",
            resource_id=brand_kit.id,
        )


def _brand_kit_to_dto(
    account_id: str,
    rows: tuple[BrandKit, ...],
    *,
    account_revision: int,
) -> BrandKitDto:
    active = next((row for row in rows if row.status == "active"), None)
    return BrandKitDto(
        accountId=account_id,
        activeVersion=None if active is None else int(active.version),
        versions=[
            BrandKitVersionSummaryDto(
                version=int(row.version),
                status=row.status,
                contentHash=_brand_kit_hash(row),
                createdAt=row.created_at,
            )
            for row in rows
        ],
        active=None if active is None else _active_brand_kit_to_dto(active),
        revision=account_revision,
    )


def _active_brand_kit_to_dto(row: BrandKit) -> ActiveBrandKitDto:
    return ActiveBrandKitDto(
        colors=_string_list(row.colors_json, "品牌颜色"),
        fonts=_string_list(row.fonts_json, "品牌字体"),
        logoAssetRefs=_string_list(
            row.logo_asset_refs_json,
            "品牌 Logo 引用",
        ),
        visualRules=load_json_object(
            row.visual_style_json,
            resource_label="品牌视觉规则",
        ),
        voiceRules=load_json_object(
            row.voice_rules_json,
            resource_label="品牌表达规则",
        ),
    )


def _brand_kit_hash(row: BrandKit) -> str:
    dto = _active_brand_kit_to_dto(row)
    return content_hash(dto.model_dump(mode="json"))


def _string_list(value: str, resource_label: str) -> list[str]:
    loaded = load_json_list(value, resource_label=resource_label)
    if not all(isinstance(item, str) for item in loaded):
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            f"{resource_label}数据结构异常，请查看诊断日志",
            status_code=500,
            loggable=True,
        )
    return [item for item in loaded if isinstance(item, str)]


def _publish_defaults_to_dto(
    stored: AccountPublishDefaults,
    *,
    account_revision: int,
) -> PublishDefaultsDto:
    return PublishDefaultsDto(
        accountId=stored.account_id,
        timezone=stored.timezone,
        privacyLevel=stored.privacy_level,
        allowComments=bool(stored.allow_comments),
        allowDuet=bool(stored.allow_duet),
        allowStitch=bool(stored.allow_stitch),
        captionRules=load_json_object(
            stored.caption_rules_json,
            resource_label="发布文案规则",
        ),
        revision=account_revision,
    )


def _validate_publish_defaults(
    payload: PublishDefaultsInput,
) -> tuple[str, str]:
    timezone = payload.timezone.strip()
    privacy_level = payload.privacyLevel.strip().lower()
    field_errors: list[FieldError] = []
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        field_errors.append(
            FieldError(
                field="timezone",
                code="invalid_timezone",
                message="必须使用有效的 IANA 时区",
            )
        )
    if privacy_level not in {"public", "friends", "private"}:
        field_errors.append(
            FieldError(
                field="privacyLevel",
                code="invalid_privacy_level",
                message="仅支持 public、friends 或 private",
            )
        )
    if privacy_level != "public" and (
        payload.allowDuet or payload.allowStitch
    ):
        field_errors.append(
            FieldError(
                field="privacyLevel",
                code="interaction_requires_public",
                message="合拍与拼接仅能用于公开发布",
            )
        )
    if field_errors:
        raise DomainError(
            ErrorCode.PUBLISH_DEFAULTS_INVALID,
            "发布默认值不符合 TikTok 平台约束",
            status_code=422,
            field_errors=field_errors,
        )
    return timezone, privacy_level


def _validate_brand_kit(payload: BrandKitVersionInput) -> None:
    field_errors: list[FieldError] = []
    for field, values in (
        ("colors", payload.colors),
        ("fonts", payload.fonts),
        ("logoAssetRefs", payload.logoAssetRefs),
    ):
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized) or len(
            set(normalized)
        ) != len(normalized):
            field_errors.append(
                FieldError(
                    field=field,
                    code="invalid_or_duplicate_value",
                    message="列表值不能为空或重复",
                )
            )
    if any(
        not re.fullmatch(r"#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?", value)
        for value in payload.colors
    ):
        field_errors.append(
            FieldError(
                field="colors",
                code="invalid_color",
                message="颜色必须使用 6 位或 8 位十六进制格式",
            )
        )
    if any(
        _CONTROLLED_ASSET_REF_PATTERN.fullmatch(value) is None
        for value in payload.logoAssetRefs
    ):
        field_errors.append(
            FieldError(
                field="logoAssetRefs",
                code="invalid_asset_ref",
                message="Logo 必须使用受控资产引用",
            )
        )
    if field_errors:
        raise DomainError(
            ErrorCode.BRAND_KIT_INVALID,
            "品牌规范配置无效",
            status_code=422,
            field_errors=field_errors,
        )


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
