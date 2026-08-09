from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from domain.models.ai_configuration_v1 import PromptProfile
from repositories.ai_configuration_v1._support import (
    acquire_sqlite_write_lock,
    limited,
    log_repository_errors,
)


class PromptProfileRepository:
    """持久化 Prompt 版本并保证单一活动版本。"""

    @log_repository_errors("列出 Prompt 版本")
    def list(
        self,
        session: Session,
        *,
        profile_key: str | None = None,
        capability_key: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> tuple[PromptProfile, ...]:
        statement = select(PromptProfile)
        if profile_key is not None:
            statement = statement.where(PromptProfile.profile_key == profile_key)
        if capability_key is not None:
            statement = statement.where(
                PromptProfile.capability_key == capability_key
            )
        if status is not None:
            statement = statement.where(PromptProfile.status == status)
        statement = statement.order_by(
            PromptProfile.profile_key.asc(),
            PromptProfile.version.desc(),
        )
        return tuple(session.scalars(limited(statement, limit)).all())

    def list_versions(
        self,
        session: Session,
        profile_key: str,
        *,
        limit: int | None = None,
    ) -> tuple[PromptProfile, ...]:
        return self.list(
            session,
            profile_key=profile_key,
            limit=limit,
        )

    @log_repository_errors("读取 Prompt 版本")
    def get(
        self,
        session: Session,
        *,
        profile_key: str,
        version: int,
    ) -> PromptProfile | None:
        return session.scalars(
            select(PromptProfile).where(
                PromptProfile.profile_key == profile_key,
                PromptProfile.version == version,
            )
        ).one_or_none()

    @log_repository_errors("按标识读取 Prompt 版本")
    def get_by_id(
        self,
        session: Session,
        prompt_profile_id: str,
    ) -> PromptProfile | None:
        return session.get(PromptProfile, prompt_profile_id)

    @log_repository_errors("读取活动 Prompt 版本")
    def get_active(
        self,
        session: Session,
        profile_key: str,
    ) -> PromptProfile | None:
        return session.scalars(
            select(PromptProfile).where(
                PromptProfile.profile_key == profile_key,
                PromptProfile.status == "active",
            )
        ).one_or_none()

    @log_repository_errors("读取最新 Prompt 版本")
    def get_latest(
        self,
        session: Session,
        profile_key: str,
    ) -> PromptProfile | None:
        return session.scalars(
            select(PromptProfile)
            .where(PromptProfile.profile_key == profile_key)
            .order_by(PromptProfile.version.desc())
            .limit(1)
        ).one_or_none()

    @log_repository_errors("计算下一 Prompt 版本")
    def next_version(
        self,
        session: Session,
        profile_key: str,
    ) -> int:
        maximum = session.scalar(
            select(func.max(PromptProfile.version)).where(
                PromptProfile.profile_key == profile_key
            )
        )
        return int(maximum or 0) + 1

    @log_repository_errors("新增 Prompt 版本")
    def add(
        self,
        session: Session,
        prompt: PromptProfile,
    ) -> PromptProfile:
        session.add(prompt)
        session.flush([prompt])
        return prompt

    @log_repository_errors("激活 Prompt 版本")
    def activate(
        self,
        session: Session,
        *,
        profile_key: str,
        version: int,
        expected_revision: int,
        next_revision: int,
        activated_at: str,
    ) -> PromptProfile | None:
        acquire_sqlite_write_lock(session, "prompt_profiles")
        target = self.get(
            session,
            profile_key=profile_key,
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
            update(PromptProfile)
            .where(
                PromptProfile.profile_key == profile_key,
                PromptProfile.status == "active",
                PromptProfile.id != target.id,
            )
            .values(
                status="archived",
                revision=PromptProfile.revision + 1,
            )
        )
        target.status = "active"
        target.activated_at = activated_at
        target.revision = next_revision
        session.flush([target])
        return target

    @log_repository_errors("归档 Prompt 版本")
    def archive(
        self,
        session: Session,
        *,
        profile_key: str,
        version: int,
        expected_revision: int,
    ) -> PromptProfile | None:
        acquire_sqlite_write_lock(session, "prompt_profiles")
        target = self.get(
            session,
            profile_key=profile_key,
            version=version,
        )
        if target is None or target.revision != expected_revision:
            return None
        if target.status != "archived":
            target.status = "archived"
            target.revision += 1
            session.flush([target])
        return target
