from __future__ import annotations

import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Connection

log = logging.getLogger(__name__)

SOURCE_MODE_CHECK = "source_mode IN ('file','url','text')"
SOURCE_URL_CHECK = (
    "(source_mode = 'url' AND source_url IS NOT NULL "
    "AND length(trim(source_url)) > 0 "
    "AND source_url = trim(source_url) "
    "AND (lower(source_url) LIKE 'http://%' "
    "OR lower(source_url) LIKE 'https://%')) "
    "OR (source_mode IN ('file','text') AND source_url IS NULL)"
)


def upgrade_knowledge_source_ingest_contract(connection: Connection) -> None:
    """补齐并收紧知识来源输入方式与独立 URL 字段。"""

    op.add_column(
        "knowledge_sources",
        sa.Column("source_mode", sa.String(), nullable=True),
    )
    op.add_column(
        "knowledge_sources",
        sa.Column("source_url", sa.Text(), nullable=True),
    )
    connection.execute(
        sa.text(
            """
            UPDATE knowledge_sources
            SET source_mode = CASE
                    WHEN lower(trim(source_ref)) LIKE 'http://%'
                      OR lower(trim(source_ref)) LIKE 'https://%'
                    THEN 'url'
                    WHEN kind = 'text'
                    THEN 'text'
                    ELSE 'file'
                END,
                source_url = CASE
                    WHEN lower(trim(source_ref)) LIKE 'http://%'
                      OR lower(trim(source_ref)) LIKE 'https://%'
                    THEN trim(source_ref)
                    ELSE NULL
                END
            """
        )
    )
    missing = int(
        connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM knowledge_sources "
                "WHERE source_mode IS NULL"
            )
        ).scalar_one()
    )
    if missing:
        log.error(
            "知识来源输入方式回填不完整",
            extra={"missing_source_mode_count": missing},
        )
        raise RuntimeError(
            "P0C_MIGRATION_VALIDATION_FAILED: "
            f"有 {missing} 条知识来源未完成输入方式回填"
        )
    with op.batch_alter_table("knowledge_sources", recreate="always") as batch:
        batch.alter_column(
            "source_mode",
            existing_type=sa.String(),
            nullable=False,
        )
        batch.create_check_constraint(
            "ck_knowledge_sources_source_mode",
            SOURCE_MODE_CHECK,
        )
        batch.create_check_constraint(
            "ck_knowledge_sources_source_url",
            SOURCE_URL_CHECK,
        )
    op.create_index(
        "ix_knowledge_sources_account_mode_updated",
        "knowledge_sources",
        ["account_id", "source_mode", "updated_at"],
    )


def downgrade_knowledge_source_ingest_contract() -> None:
    """在外层完成数据保护后移除 0019 新增的摄取字段。"""

    op.drop_index(
        "ix_knowledge_sources_account_mode_updated",
        table_name="knowledge_sources",
    )
    with op.batch_alter_table("knowledge_sources", recreate="always") as batch:
        batch.drop_constraint(
            "ck_knowledge_sources_source_url",
            type_="check",
        )
        batch.drop_constraint(
            "ck_knowledge_sources_source_mode",
            type_="check",
        )
        batch.drop_column("source_url")
        batch.drop_column("source_mode")
