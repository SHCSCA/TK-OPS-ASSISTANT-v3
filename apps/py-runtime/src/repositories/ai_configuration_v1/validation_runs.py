from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.models.ai_execution_evidence import AIProviderValidationRun
from repositories.ai_configuration_v1._support import (
    limited,
    log_repository_errors,
)


class AIProviderValidationRunRepository:
    """持久化 Provider 分阶段真实验证的脱敏证据。"""

    @log_repository_errors("读取 Provider 验证证据")
    def get(
        self,
        session: Session,
        validation_run_id: str,
    ) -> AIProviderValidationRun | None:
        return session.get(AIProviderValidationRun, validation_run_id)

    @log_repository_errors("新增 Provider 验证证据")
    def add(
        self,
        session: Session,
        row: AIProviderValidationRun,
    ) -> AIProviderValidationRun:
        session.add(row)
        session.flush([row])
        return row

    @log_repository_errors("列出 Provider 验证证据")
    def list(
        self,
        session: Session,
        *,
        provider_profile_id: str | None = None,
        provider_revision: int | None = None,
        model_profile_id: str | None = None,
        model_revision: int | None = None,
        capability_key: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> tuple[AIProviderValidationRun, ...]:
        statement = select(AIProviderValidationRun)
        filters = {
            "provider_profile_id": provider_profile_id,
            "provider_revision": provider_revision,
            "model_profile_id": model_profile_id,
            "model_revision": model_revision,
            "capability_key": capability_key,
            "status": status,
        }
        for field_name, value in filters.items():
            if value is not None:
                statement = statement.where(
                    getattr(AIProviderValidationRun, field_name) == value
                )
        statement = statement.order_by(
            AIProviderValidationRun.created_at.desc(),
            AIProviderValidationRun.id.asc(),
        )
        return tuple(session.scalars(limited(statement, limit)).all())

    @log_repository_errors("读取最新真实能力验证")
    def latest_verified_capability(
        self,
        session: Session,
        *,
        provider_profile_id: str,
        provider_revision: int,
        model_profile_id: str,
        model_revision: int,
        capability_key: str,
    ) -> AIProviderValidationRun | None:
        return session.scalars(
            select(AIProviderValidationRun)
            .where(
                AIProviderValidationRun.provider_profile_id
                == provider_profile_id,
                AIProviderValidationRun.provider_revision
                == provider_revision,
                AIProviderValidationRun.model_profile_id == model_profile_id,
                AIProviderValidationRun.model_revision == model_revision,
                AIProviderValidationRun.capability_key == capability_key,
                AIProviderValidationRun.stage == "real_small_call",
                AIProviderValidationRun.status == "verified",
            )
            .order_by(AIProviderValidationRun.created_at.desc())
            .limit(1)
        ).one_or_none()
