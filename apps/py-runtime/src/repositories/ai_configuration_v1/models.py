from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from domain.models.ai_configuration_v1 import (
    ModelCapability,
    ModelProfile,
    ProviderProfile,
)
from repositories.ai_configuration_v1._support import (
    limited,
    log_repository_errors,
    validated_changes,
)

_MODEL_UPDATE_FIELDS = frozenset(
    {
        "display_name",
        "enabled",
        "context_window",
        "base_limits_json",
    }
)
_CAPABILITY_UPDATE_FIELDS = frozenset(
    {
        "declared_supported",
        "adapter_supported",
        "contract_verified",
        "input_modalities_json",
        "output_modalities_json",
        "parameter_schema_json",
        "source_urls_json",
        "known_limits_json",
        "verified_at",
        "contract_revision",
    }
)


class ModelProfileRepository:
    """持久化 Provider 下的模型档案。"""

    @log_repository_errors("列出模型")
    def list(
        self,
        session: Session,
        *,
        provider_id: str | None = None,
        enabled: bool | None = None,
        capability_key: str | None = None,
        limit: int | None = None,
    ) -> tuple[ModelProfile, ...]:
        statement = select(ModelProfile)
        if capability_key is not None:
            statement = (
                statement.join(
                    ModelCapability,
                    ModelCapability.model_profile_id == ModelProfile.id,
                )
                .where(ModelCapability.capability_key == capability_key)
                .distinct()
            )
        if provider_id is not None:
            statement = statement.where(
                ModelProfile.provider_profile_id == provider_id
            )
        if enabled is not None:
            statement = statement.where(ModelProfile.enabled == enabled)
        statement = statement.order_by(
            ModelProfile.updated_at.desc(),
            ModelProfile.id.asc(),
        )
        return tuple(session.scalars(limited(statement, limit)).all())

    @log_repository_errors("读取模型")
    def get(
        self,
        session: Session,
        model_profile_id: str,
    ) -> ModelProfile | None:
        return session.get(ModelProfile, model_profile_id)

    @log_repository_errors("按 Provider 与模型标识读取模型")
    def get_by_provider_model(
        self,
        session: Session,
        *,
        provider_id: str,
        model_id: str,
    ) -> ModelProfile | None:
        return session.scalars(
            select(ModelProfile).where(
                ModelProfile.provider_profile_id == provider_id,
                ModelProfile.model_id == model_id,
            )
        ).one_or_none()

    @log_repository_errors("新增模型")
    def add(
        self,
        session: Session,
        model: ModelProfile,
    ) -> ModelProfile:
        session.add(model)
        session.flush([model])
        return model

    @log_repository_errors("更新模型")
    def update(
        self,
        session: Session,
        model_profile_id: str,
        *,
        expected_revision: int,
        changes: Mapping[str, object],
        updated_at: str,
    ) -> ModelProfile | None:
        values = validated_changes(changes, _MODEL_UPDATE_FIELDS)
        if not values:
            current = self.get(session, model_profile_id)
            if current is None or current.revision != expected_revision:
                return None
            return current
        statement = (
            update(ModelProfile)
            .where(
                ModelProfile.id == model_profile_id,
                ModelProfile.revision == expected_revision,
            )
            .values(
                **values,
                updated_at=updated_at,
                revision=ModelProfile.revision + 1,
            )
            .returning(ModelProfile)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        )
        return session.scalars(statement).one_or_none()


class ModelCapabilityRepository:
    """持久化模型能力三项交集与验证证据。"""

    @log_repository_errors("列出模型能力")
    def list(
        self,
        session: Session,
        *,
        provider_id: str | None = None,
        model_profile_id: str | None = None,
        capability_key: str | None = None,
        contract_verified: bool | None = None,
        limit: int | None = None,
    ) -> tuple[ModelCapability, ...]:
        statement = select(ModelCapability)
        if provider_id is not None:
            statement = statement.join(
                ModelProfile,
                ModelProfile.id == ModelCapability.model_profile_id,
            ).where(ModelProfile.provider_profile_id == provider_id)
        if model_profile_id is not None:
            statement = statement.where(
                ModelCapability.model_profile_id == model_profile_id
            )
        if capability_key is not None:
            statement = statement.where(
                ModelCapability.capability_key == capability_key
            )
        if contract_verified is not None:
            statement = statement.where(
                ModelCapability.contract_verified == contract_verified
            )
        statement = statement.order_by(
            ModelCapability.model_profile_id.asc(),
            ModelCapability.capability_key.asc(),
        )
        return tuple(session.scalars(limited(statement, limit)).all())

    @log_repository_errors("读取模型能力")
    def get(
        self,
        session: Session,
        *,
        model_profile_id: str,
        capability_key: str,
    ) -> ModelCapability | None:
        return session.scalars(
            select(ModelCapability).where(
                ModelCapability.model_profile_id == model_profile_id,
                ModelCapability.capability_key == capability_key,
            )
        ).one_or_none()

    @log_repository_errors("新增模型能力")
    def add(
        self,
        session: Session,
        capability: ModelCapability,
    ) -> ModelCapability:
        session.add(capability)
        session.flush([capability])
        return capability

    @log_repository_errors("保存模型能力")
    def save(
        self,
        session: Session,
        capability: ModelCapability,
    ) -> ModelCapability:
        current = self.get(
            session,
            model_profile_id=capability.model_profile_id,
            capability_key=capability.capability_key,
        )
        if current is None:
            return self.add(session, capability)
        if current.id != capability.id:
            raise ValueError("同一模型能力键不得更换持久化标识")
        for field in _CAPABILITY_UPDATE_FIELDS:
            setattr(current, field, getattr(capability, field))
        session.flush([current])
        return current

    @log_repository_errors("更新模型能力")
    def update(
        self,
        session: Session,
        *,
        model_profile_id: str,
        capability_key: str,
        changes: Mapping[str, object],
    ) -> ModelCapability | None:
        current = self.get(
            session,
            model_profile_id=model_profile_id,
            capability_key=capability_key,
        )
        if current is None:
            return None
        for field, value in validated_changes(
            changes,
            _CAPABILITY_UPDATE_FIELDS,
        ).items():
            setattr(current, field, value)
        session.flush([current])
        return current

    @log_repository_errors("读取模型及 Provider")
    def get_model_provider(
        self,
        session: Session,
        model_profile_id: str,
    ) -> tuple[ModelProfile, ProviderProfile] | None:
        row = session.execute(
            select(ModelProfile, ProviderProfile)
            .join(
                ProviderProfile,
                ProviderProfile.id == ModelProfile.provider_profile_id,
            )
            .where(ModelProfile.id == model_profile_id)
        ).one_or_none()
        if row is None:
            return None
        return row[0], row[1]
