from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from config.migration import (
    MIGRATION_BACKUP_RETENTION_KEY,
    MigrationBootstrapProjection,
    MigrationConfigurationError,
    write_migration_bootstrap_projection,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MigrationBootstrapProjectionWriter:
    """将配置总线键投影为迁移前可校验的最小启动配置。"""

    data_dir: Path

    def write(
        self,
        *,
        revision: int,
        values: Mapping[str, object],
    ) -> MigrationBootstrapProjection:
        retention = values.get(MIGRATION_BACKUP_RETENTION_KEY)
        if not isinstance(retention, int) or isinstance(retention, bool):
            raise MigrationConfigurationError("配置总线缺少迁移备份保留数量")
        try:
            return write_migration_bootstrap_projection(
                self.data_dir,
                config_revision=revision,
                backup_retention_count=retention,
            )
        except MigrationConfigurationError:
            log.exception(
                "配置总线迁移启动投影失败",
                extra={
                    "config_revision": revision,
                    "projection_key": MIGRATION_BACKUP_RETENTION_KEY,
                },
            )
            raise
