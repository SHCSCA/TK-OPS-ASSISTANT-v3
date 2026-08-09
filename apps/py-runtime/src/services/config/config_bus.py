from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, replace

from sqlalchemy.orm import Session

from app.logging import log_event
from errors import DomainError, ErrorCode, FieldError
from repositories.system_config_repository import (
    StoredSystemConfig,
    SystemConfigRepository,
    SystemConfigRevisionConflict,
)
from services.config.projection import MigrationBootstrapProjectionWriter
from services.config.schema import (
    DEFAULT_VALUES,
    LEGACY_READ_PATHS,
    RESTART_REQUIRED_KEYS,
    WRITABLE_RULES,
    validate_config_relationships,
)

log = logging.getLogger(__name__)

ConfigUpdatedCallback = Callable[["ConfigBusSnapshot", tuple[str, ...]], None]
ConfigEventWriter = Callable[
    [Session, "ConfigBusSnapshot", tuple[str, ...]],
    None,
]


@dataclass(frozen=True, slots=True)
class ConfigBusSnapshot:
    values: dict[str, object]
    writable_keys: tuple[str, ...]
    restart_required_keys: tuple[str, ...]
    revision: int
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "values": self.values,
            "writableKeys": list(self.writable_keys),
            "restartRequiredKeys": list(self.restart_required_keys),
            "revision": self.revision,
        }

class ConfigBusService:
    def __init__(
        self,
        repository: SystemConfigRepository,
        *,
        event_writer: ConfigEventWriter | None = None,
        on_updated: ConfigUpdatedCallback | None = None,
        bootstrap_projection_writer: (
            MigrationBootstrapProjectionWriter | None
        ) = None,
    ) -> None:
        self._repository = repository
        self._event_writer = event_writer
        self._on_updated = on_updated
        self._bootstrap_projection_writer = bootstrap_projection_writer

    def sync_bootstrap_projection(self) -> None:
        if self._bootstrap_projection_writer is None:
            return
        snapshot = self.get()
        self._bootstrap_projection_writer.write(
            revision=snapshot.revision,
            values=snapshot.values,
        )

    def get(self, *, prefix: str | None = None) -> ConfigBusSnapshot:
        stored = self._repository.load()
        document = {} if stored is None else stored.document
        values = self._read_values(document)
        normalized_prefix = (prefix or "").strip()
        if normalized_prefix:
            values = {
                key: value
                for key, value in values.items()
                if key.startswith(normalized_prefix)
            }
        return ConfigBusSnapshot(
            values=values,
            writable_keys=tuple(sorted(WRITABLE_RULES)),
            restart_required_keys=RESTART_REQUIRED_KEYS,
            revision=0 if stored is None else stored.revision,
        )

    def update(
        self,
        values: Mapping[str, object],
        *,
        expected_revision: int,
        request_id: str,
        operation_id: str,
    ) -> ConfigBusSnapshot:
        field_errors = self._validate(values)
        if field_errors:
            error_code = (
                ErrorCode.CONFIG_KEY_NOT_WRITABLE
                if any(item.code == "not_writable" for item in field_errors)
                else ErrorCode.REQUEST_VALIDATION_FAILED
            )
            raise DomainError(
                error_code,
                "系统配置包含不可写或无效字段",
                status_code=422,
                field_errors=field_errors,
            )

        stored = self._repository.load()
        document = deepcopy({} if stored is None else stored.document)
        effective_values = self._read_values(document)
        effective_values.update(deepcopy(dict(values)))
        relationship_errors = self._validate_relationships(effective_values)
        if relationship_errors:
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "系统配置包含相互冲突的字段",
                status_code=422,
                field_errors=relationship_errors,
            )

        current_revision = 0 if stored is None else stored.revision
        if current_revision != expected_revision:
            raise self._revision_conflict(current_revision)

        config_bus = self._read_bus_document(document)
        for key, value in values.items():
            if key in LEGACY_READ_PATHS:
                _set_nested_value(document, key, value)
            else:
                config_bus[key] = deepcopy(value)
        document["configBus"] = config_bus

        changed_keys = tuple(sorted(values))

        def write_event(
            session: Session,
            stored_config: StoredSystemConfig,
        ) -> None:
            if self._event_writer is None:
                return
            self._event_writer(
                session,
                self._snapshot_from_stored(stored_config),
                changed_keys,
            )

        try:
            saved = self._repository.save_if_revision(
                document,
                expected_revision=expected_revision,
                before_commit=write_event,
            )
        except SystemConfigRevisionConflict as exc:
            latest = self._repository.load()
            latest_revision = 0 if latest is None else latest.revision
            raise self._revision_conflict(latest_revision) from exc
        except DomainError:
            raise
        except Exception as exc:
            log.exception("系统配置与事件事务保存失败")
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "系统配置保存失败，请稍后重试",
                status_code=500,
                loggable=True,
            ) from exc

        snapshot = self._snapshot_from_stored(saved)
        warnings: list[str] = []
        if self._bootstrap_projection_writer is not None:
            try:
                self._bootstrap_projection_writer.write(
                    revision=snapshot.revision,
                    values=snapshot.values,
                )
            except Exception:
                log.exception("系统配置已保存，但迁移启动投影刷新失败")
                warnings.append(
                    "配置已保存，但迁移启动配置未同步；"
                    "请勿重启 Runtime，并查看诊断日志"
                )
        log_event(
            "audit",
            "config.updated",
            request_id=request_id,
            operation_id=operation_id,
            context={
                "revision": snapshot.revision,
                "changedKeys": list(changed_keys),
            },
        )
        if self._on_updated is not None:
            try:
                self._on_updated(snapshot, changed_keys)
            except Exception:
                log.exception("系统配置更新后的刷新回调失败")
                warnings.append(
                    "配置已保存，运行时刷新失败；请重启 Runtime 后生效"
                )
        if warnings:
            snapshot = replace(snapshot, warnings=tuple(warnings))
        return snapshot

    def _snapshot_from_stored(
        self,
        stored: StoredSystemConfig,
    ) -> ConfigBusSnapshot:
        return ConfigBusSnapshot(
            values=self._read_values(stored.document),
            writable_keys=tuple(sorted(WRITABLE_RULES)),
            restart_required_keys=RESTART_REQUIRED_KEYS,
            revision=stored.revision,
        )

    def _read_values(self, document: Mapping[str, object]) -> dict[str, object]:
        values = deepcopy(DEFAULT_VALUES)
        for path in LEGACY_READ_PATHS:
            found, value = _get_nested_value(document, path)
            if found:
                values[path] = deepcopy(value)
        values.update(self._read_bus_document(document))
        resolved = {
            key: value
            for key, value in values.items()
            if key in WRITABLE_RULES or key in LEGACY_READ_PATHS
        }
        writable_values = {
            key: value
            for key, value in resolved.items()
            if key in WRITABLE_RULES
        }
        field_errors = self._validate(writable_values)
        field_errors.extend(self._validate_relationships(writable_values))
        if field_errors:
            log.error(
                "持久化配置不符合统一配置 Schema",
                extra={
                    "invalid_config_keys": [
                        item.field.removeprefix("values.")
                        for item in field_errors
                    ]
                },
            )
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "系统配置结构异常，请查看诊断日志",
                status_code=500,
                loggable=True,
            )
        return resolved

    def _read_bus_document(
        self,
        document: Mapping[str, object],
    ) -> dict[str, object]:
        raw_bus = document.get("configBus", {})
        if raw_bus is None:
            return {}
        if not isinstance(raw_bus, Mapping):
            log.error("系统配置总线文档结构损坏")
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "系统配置结构异常，请查看诊断日志",
                status_code=500,
                loggable=True,
            )
        return {
            str(key): deepcopy(value)
            for key, value in raw_bus.items()
            if str(key) in WRITABLE_RULES
        }

    def _validate(
        self,
        values: Mapping[str, object],
    ) -> list[FieldError]:
        errors: list[FieldError] = []
        for key, value in values.items():
            rule = WRITABLE_RULES.get(key)
            if rule is None:
                errors.append(
                    FieldError(
                        field=f"values.{key}",
                        code="not_writable",
                        message="该配置项不可由用户修改",
                    )
                )
                continue
            if not rule.validator(value):
                errors.append(
                    FieldError(
                        field=f"values.{key}",
                        code="invalid_value",
                        message=rule.message,
                    )
                )
        return errors

    @staticmethod
    def _validate_relationships(
        values: Mapping[str, object],
    ) -> list[FieldError]:
        return validate_config_relationships(values)

    def _revision_conflict(self, current_revision: int) -> DomainError:
        return DomainError(
            ErrorCode.CONFIG_REVISION_CONFLICT,
            "配置已被其他操作更新，请重新加载后再试",
            status_code=412,
            meta={
                "currentRevision": current_revision,
                "invalidations": ["system-config"],
            },
        )


def _get_nested_value(
    document: Mapping[str, object],
    path: str,
) -> tuple[bool, object]:
    current: object = document
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _set_nested_value(
    document: dict[str, object],
    path: str,
    value: object,
) -> None:
    parts = path.split(".")
    current = document
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = deepcopy(value)
