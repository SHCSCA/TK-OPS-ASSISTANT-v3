from __future__ import annotations

from app.config import RuntimeConfig
from persistence.migration import MigrationReport, run_startup_migrations


def prepare_runtime_database(runtime_config: RuntimeConfig) -> MigrationReport:
    """在任何仓储和服务创建前完成数据库启动迁移。"""

    return run_startup_migrations(
        runtime_config.database_path,
        runtime_config.migration,
        runtime_root=runtime_config.repo_root / "apps" / "py-runtime",
    )
