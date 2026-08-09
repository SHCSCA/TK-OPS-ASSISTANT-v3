from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from domain.models.ai_configuration_v1 import CompositionTemplateProfile
from repositories.ai_configuration_v1._support import (
    acquire_sqlite_write_lock,
    limited,
    log_repository_errors,
)


class CompositionTemplateProfileRepository:
    """持久化受控 Composition Template 版本。"""

    @log_repository_errors("列出合成模板版本")
    def list(
        self,
        session: Session,
        *,
        template_key: str | None = None,
        template_type: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> tuple[CompositionTemplateProfile, ...]:
        statement = select(CompositionTemplateProfile)
        if template_key is not None:
            statement = statement.where(
                CompositionTemplateProfile.template_key == template_key
            )
        if template_type is not None:
            statement = statement.where(
                CompositionTemplateProfile.template_type == template_type
            )
        if status is not None:
            statement = statement.where(
                CompositionTemplateProfile.status == status
            )
        statement = statement.order_by(
            CompositionTemplateProfile.template_key.asc(),
            CompositionTemplateProfile.version.desc(),
        )
        return tuple(session.scalars(limited(statement, limit)).all())

    def list_versions(
        self,
        session: Session,
        template_key: str,
        *,
        limit: int | None = None,
    ) -> tuple[CompositionTemplateProfile, ...]:
        return self.list(
            session,
            template_key=template_key,
            limit=limit,
        )

    @log_repository_errors("读取合成模板版本")
    def get(
        self,
        session: Session,
        *,
        template_key: str,
        version: int,
    ) -> CompositionTemplateProfile | None:
        return session.scalars(
            select(CompositionTemplateProfile).where(
                CompositionTemplateProfile.template_key == template_key,
                CompositionTemplateProfile.version == version,
            )
        ).one_or_none()

    @log_repository_errors("按标识读取合成模板版本")
    def get_by_id(
        self,
        session: Session,
        template_id: str,
    ) -> CompositionTemplateProfile | None:
        return session.get(CompositionTemplateProfile, template_id)

    @log_repository_errors("读取活动合成模板版本")
    def get_active(
        self,
        session: Session,
        template_key: str,
    ) -> CompositionTemplateProfile | None:
        return session.scalars(
            select(CompositionTemplateProfile).where(
                CompositionTemplateProfile.template_key == template_key,
                CompositionTemplateProfile.status == "active",
            )
        ).one_or_none()

    @log_repository_errors("读取最新合成模板版本")
    def get_latest(
        self,
        session: Session,
        template_key: str,
    ) -> CompositionTemplateProfile | None:
        return session.scalars(
            select(CompositionTemplateProfile)
            .where(CompositionTemplateProfile.template_key == template_key)
            .order_by(CompositionTemplateProfile.version.desc())
            .limit(1)
        ).one_or_none()

    @log_repository_errors("计算下一合成模板版本")
    def next_version(
        self,
        session: Session,
        template_key: str,
    ) -> int:
        maximum = session.scalar(
            select(func.max(CompositionTemplateProfile.version)).where(
                CompositionTemplateProfile.template_key == template_key
            )
        )
        return int(maximum or 0) + 1

    @log_repository_errors("新增合成模板版本")
    def add(
        self,
        session: Session,
        template: CompositionTemplateProfile,
    ) -> CompositionTemplateProfile:
        session.add(template)
        session.flush([template])
        return template

    @log_repository_errors("激活合成模板版本")
    def activate(
        self,
        session: Session,
        *,
        template_key: str,
        version: int,
        expected_revision: int,
        next_revision: int,
        activated_at: str,
    ) -> CompositionTemplateProfile | None:
        acquire_sqlite_write_lock(session, "composition_template_profiles")
        target = self.get(
            session,
            template_key=template_key,
            version=version,
        )
        if (
            target is None
            or target.status == "archived"
            or target.revision != expected_revision
        ):
            return None
        if target.status == "active":
            return target
        session.execute(
            update(CompositionTemplateProfile)
            .where(
                CompositionTemplateProfile.template_key == template_key,
                CompositionTemplateProfile.status == "active",
                CompositionTemplateProfile.id != target.id,
            )
            .values(
                status="archived",
                revision=CompositionTemplateProfile.revision + 1,
            )
        )
        target.status = "active"
        target.activated_at = activated_at
        target.revision = next_revision
        session.flush([target])
        return target

    @log_repository_errors("归档合成模板版本")
    def archive(
        self,
        session: Session,
        *,
        template_key: str,
        version: int,
        expected_revision: int,
    ) -> CompositionTemplateProfile | None:
        acquire_sqlite_write_lock(session, "composition_template_profiles")
        target = self.get(
            session,
            template_key=template_key,
            version=version,
        )
        if target is None or target.revision != expected_revision:
            return None
        if target.status != "archived":
            target.status = "archived"
            target.revision += 1
            session.flush([target])
        return target
