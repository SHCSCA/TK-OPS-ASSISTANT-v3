from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config.database import (  # noqa: E402
    DatabasePathConfigurationError,
    database_path_to_url,
    resolve_database_path,
    resolve_runtime_data_dir,
)
from domain.models import Base  # noqa: E402

config = context.config
log = logging.getLogger(__name__)

target_metadata = Base.metadata

_DEFAULT_INI_DATABASE_URL = "sqlite:///runtime.db"


def _database_url() -> str:
    attribute_url = config.attributes.get("database_url")
    if attribute_url:
        return str(attribute_url)

    option_url = str(config.get_main_option("sqlalchemy.url") or "").strip()
    if option_url and option_url != _DEFAULT_INI_DATABASE_URL:
        return option_url

    repo_root = Path(__file__).resolve().parents[3]
    data_dir = resolve_runtime_data_dir(repo_root / ".runtime-data")
    database_path = resolve_database_path(data_dir)
    try:
        database_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.exception("无法准备 Alembic 数据库目录")
        raise DatabasePathConfigurationError(
            "无法创建数据库目录，请检查 Runtime 数据目录权限"
        ) from exc
    return database_path_to_url(database_path)


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
