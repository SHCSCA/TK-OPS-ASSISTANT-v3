from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from domain.models.account_configuration import (
    AccountConfigCopyRun,
    AccountPublishDefaults,
    BrandKit,
    PositioningProfile,
)

_PUBLISH_DEFAULT_FIELDS = frozenset(
    {
        "timezone",
        "privacy_level",
        "allow_comments",
        "allow_duet",
        "allow_stitch",
        "caption_rules_json",
    }
)


class AccountConfigurationV1Repository:
    def list_positioning(
        self,
        account_id: str,
        session: Session,
    ) -> tuple[PositioningProfile, ...]:
        return tuple(
            session.scalars(
                select(PositioningProfile)
                .where(PositioningProfile.account_id == account_id)
                .order_by(PositioningProfile.version.desc())
            ).all()
        )

    def get_positioning_version(
        self,
        account_id: str,
        session: Session,
        *,
        version: int,
    ) -> PositioningProfile | None:
        return session.scalars(
            select(PositioningProfile).where(
                PositioningProfile.account_id == account_id,
                PositioningProfile.version == version,
            )
        ).one_or_none()

    def get_active_positioning(
        self,
        account_id: str,
        session: Session,
    ) -> PositioningProfile | None:
        return session.scalars(
            select(PositioningProfile).where(
                PositioningProfile.account_id == account_id,
                PositioningProfile.status == "active",
            )
        ).one_or_none()

    def next_positioning_version(
        self,
        account_id: str,
        session: Session,
    ) -> int:
        maximum = session.scalar(
            select(func.max(PositioningProfile.version)).where(
                PositioningProfile.account_id == account_id
            )
        )
        return int(maximum or 0) + 1

    def add_positioning(
        self,
        account_id: str,
        session: Session,
        profile: PositioningProfile,
    ) -> PositioningProfile:
        _require_account_id(account_id, profile.account_id)
        session.add(profile)
        session.flush()
        return profile

    def activate_positioning(
        self,
        account_id: str,
        session: Session,
        *,
        version: int,
        activated_at: str,
    ) -> PositioningProfile | None:
        target = self.get_positioning_version(
            account_id,
            session,
            version=version,
        )
        if target is None or target.status == "archived":
            return None
        session.execute(
            update(PositioningProfile)
            .where(
                PositioningProfile.account_id == account_id,
                PositioningProfile.status == "active",
                PositioningProfile.id != target.id,
            )
            .values(
                status="archived",
                revision=PositioningProfile.revision + 1,
            )
        )
        if target.status != "active":
            target.status = "active"
            target.activated_at = activated_at
            target.revision += 1
            session.flush()
        return target

    def list_brand_kits(
        self,
        account_id: str,
        session: Session,
    ) -> tuple[BrandKit, ...]:
        return tuple(
            session.scalars(
                select(BrandKit)
                .where(BrandKit.account_id == account_id)
                .order_by(BrandKit.version.desc())
            ).all()
        )

    def get_active_brand_kit(
        self,
        account_id: str,
        session: Session,
    ) -> BrandKit | None:
        return session.scalars(
            select(BrandKit).where(
                BrandKit.account_id == account_id,
                BrandKit.status == "active",
            )
        ).one_or_none()

    def next_brand_kit_version(
        self,
        account_id: str,
        session: Session,
    ) -> int:
        maximum = session.scalar(
            select(func.max(BrandKit.version)).where(
                BrandKit.account_id == account_id
            )
        )
        return int(maximum or 0) + 1

    def add_and_activate_brand_kit(
        self,
        account_id: str,
        session: Session,
        brand_kit: BrandKit,
    ) -> BrandKit:
        _require_account_id(account_id, brand_kit.account_id)
        session.execute(
            update(BrandKit)
            .where(
                BrandKit.account_id == account_id,
                BrandKit.status == "active",
            )
            .values(
                status="archived",
                revision=BrandKit.revision + 1,
            )
        )
        session.add(brand_kit)
        session.flush()
        return brand_kit

    def get_publish_defaults(
        self,
        account_id: str,
        session: Session,
    ) -> AccountPublishDefaults | None:
        return session.scalars(
            select(AccountPublishDefaults).where(
                AccountPublishDefaults.account_id == account_id
            )
        ).one_or_none()

    def save_publish_defaults(
        self,
        account_id: str,
        session: Session,
        *,
        values: dict[str, object],
        created_at: str,
        updated_at: str,
    ) -> AccountPublishDefaults:
        unexpected_fields = sorted(set(values) - _PUBLISH_DEFAULT_FIELDS)
        if unexpected_fields:
            raise ValueError(
                "发布默认值包含不允许持久化的字段："
                + ", ".join(unexpected_fields)
            )
        stored = self.get_publish_defaults(account_id, session)
        if stored is None:
            stored = AccountPublishDefaults(
                account_id=account_id,
                revision=1,
                created_at=created_at,
                updated_at=updated_at,
                **values,
            )
            session.add(stored)
        else:
            for key, value in values.items():
                setattr(stored, key, value)
            stored.revision += 1
            stored.updated_at = updated_at
        session.flush()
        return stored

    def add_copy_run(
        self,
        account_id: str,
        session: Session,
        copy_run: AccountConfigCopyRun,
    ) -> AccountConfigCopyRun:
        _require_account_id(account_id, copy_run.target_account_id)
        session.add(copy_run)
        session.flush()
        return copy_run


def _require_account_id(expected: str, actual: str) -> None:
    if expected != actual:
        raise ValueError("账号配置对象与请求账号不一致")
