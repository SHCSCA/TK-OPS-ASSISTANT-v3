from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from domain.models import Base
from persistence.legacy_schema_accounts import repair_legacy_account_schemas
from persistence.legacy_schema_media import repair_legacy_media_schemas
from persistence.migration.legacy_baseline import KNOWN_FRESH_RUNTIME_TABLE_NAMES

log = logging.getLogger(__name__)


def create_runtime_engine(database_path: Path) -> Engine:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def initialize_domain_schema(engine: Engine) -> None:
    # 该入口只复现冻结 legacy cohort；正式 Runtime 表必须由 Alembic 接管。
    missing_tables = sorted(
        set(KNOWN_FRESH_RUNTIME_TABLE_NAMES) - set(Base.metadata.tables)
    )
    if missing_tables:
        log.error("冻结 legacy 元数据缺少表：%s", ", ".join(missing_tables))
        raise RuntimeError("冻结 legacy 元数据不完整，无法初始化兼容结构")
    Base.metadata.create_all(
        engine,
        tables=[
            Base.metadata.tables[table_name]
            for table_name in KNOWN_FRESH_RUNTIME_TABLE_NAMES
        ],
    )
    repair_legacy_media_schemas(engine)
    repair_legacy_account_schemas(engine)
