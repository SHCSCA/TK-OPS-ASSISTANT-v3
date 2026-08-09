"""补齐 P0-E AI 版本审计字段。

Revision ID: 0020_p0e_ai_vertical_chain
Revises: 0019_p0_account_vertical_chain
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import NoReturn

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy import Connection

revision = "0020_p0e_ai_vertical_chain"
down_revision = "0019_p0_account_vertical_chain"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)

_HASH_CHECK = (
    "length(content_hash) = 64 "
    "AND content_hash NOT GLOB '*[^0-9a-f]*'"
)


def upgrade() -> None:
    connection = op.get_bind()
    _validate_required_tables(connection)
    recipe_hashes = _prepare_recipe_hashes(connection)
    op.add_column(
        "prompt_profiles",
        sa.Column(
            "revision",
            sa.Integer(),
            nullable=True,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "account_ai_recipes",
        sa.Column("content_hash", sa.String(), nullable=True),
    )
    _backfill_prompt_revisions(connection)
    _backfill_recipe_hashes(connection, recipe_hashes)
    _tighten_contract()
    _validate_contract(connection)


def downgrade() -> None:
    _refuse_data_bearing_downgrade()
    _preflight_cross_revision_downgrade()
    with op.batch_alter_table(
        "account_ai_recipes",
        recreate="always",
    ) as batch:
        batch.drop_constraint(
            "ck_account_ai_recipes_content_hash",
            type_="check",
        )
        batch.drop_column("content_hash")
    with op.batch_alter_table(
        "prompt_profiles",
        recreate="always",
    ) as batch:
        batch.drop_constraint(
            "ck_prompt_profiles_version",
            type_="check",
        )
        batch.create_check_constraint(
            "ck_prompt_profiles_version",
            "version >= 1",
        )
        batch.drop_column("revision")


def _validate_required_tables(connection: Connection) -> None:
    table_names = {
        row[0]
        for row in connection.execute(
            sa.text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            )
        )
    }
    missing = {
        "prompt_profiles",
        "account_ai_recipes",
    }.difference(table_names)
    if missing:
        _fail(f"缺少 P0-E 依赖表：{', '.join(sorted(missing))}")


def _backfill_prompt_revisions(connection: Connection) -> None:
    connection.execute(
        sa.text(
            """
            UPDATE prompt_profiles
            SET revision = CASE
                WHEN version >= 1 THEN version
                ELSE 1
            END
            """
        )
    )


def _prepare_recipe_hashes(
    connection: Connection,
) -> list[tuple[object, str]]:
    rows = connection.execute(
        sa.text(
            """
            SELECT
                id,
                name,
                route_overrides_json,
                visual_style_json,
                voice_profile_ref,
                composition_template_ref,
                cost_policy_json,
                fallback_policy_json,
                source_ai_config_revision
            FROM account_ai_recipes
            """
        )
    ).mappings()
    prepared: list[tuple[object, str]] = []
    for row in rows:
        payload = {
            "name": row["name"],
            "routeOverrides": _load_json(row["route_overrides_json"]),
            "visualStyle": _load_json(row["visual_style_json"]),
            "voiceProfileRef": row["voice_profile_ref"],
            "compositionTemplateRef": row["composition_template_ref"],
            "costPolicy": _load_json(row["cost_policy_json"]),
            "fallbackPolicy": _load_json(row["fallback_policy_json"]),
            "sourceAiConfigRevision": row["source_ai_config_revision"],
        }
        digest = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        prepared.append((row["id"], digest))
    return prepared


def _backfill_recipe_hashes(
    connection: Connection,
    recipe_hashes: list[tuple[object, str]],
) -> None:
    for recipe_id, digest in recipe_hashes:
        connection.execute(
            sa.text(
                """
                UPDATE account_ai_recipes
                SET content_hash = :content_hash
                WHERE id = :recipe_id
                """
            ),
            {
                "content_hash": digest,
                "recipe_id": recipe_id,
            },
        )


def _load_json(raw_value: object) -> object:
    if not isinstance(raw_value, str):
        _fail("账号 AI Recipe JSON 字段不是文本")
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError as exc:
        _fail(f"账号 AI Recipe JSON 无法解析：{exc.msg}")


def _tighten_contract() -> None:
    with op.batch_alter_table(
        "prompt_profiles",
        recreate="always",
    ) as batch:
        batch.drop_constraint(
            "ck_prompt_profiles_version",
            type_="check",
        )
        batch.alter_column(
            "revision",
            existing_type=sa.Integer(),
            nullable=False,
            server_default=None,
        )
        batch.create_check_constraint(
            "ck_prompt_profiles_version",
            "version >= 1 AND revision >= 1",
        )
    with op.batch_alter_table(
        "account_ai_recipes",
        recreate="always",
    ) as batch:
        batch.alter_column(
            "content_hash",
            existing_type=sa.String(),
            nullable=False,
        )
        batch.create_check_constraint(
            "ck_account_ai_recipes_content_hash",
            _HASH_CHECK,
        )


def _validate_contract(connection: Connection) -> None:
    invalid_prompt = connection.execute(
        sa.text(
            """
            SELECT 1 FROM prompt_profiles
            WHERE revision IS NULL OR revision < 1
            LIMIT 1
            """
        )
    ).first()
    invalid_recipe = connection.execute(
        sa.text(
            """
            SELECT 1 FROM account_ai_recipes
            WHERE content_hash IS NULL
               OR length(content_hash) <> 64
               OR content_hash GLOB '*[^0-9a-f]*'
            LIMIT 1
            """
        )
    ).first()
    foreign_key_violations = connection.execute(
        sa.text("PRAGMA foreign_key_check")
    ).all()
    if invalid_prompt:
        _fail("Prompt Profile 修订回填失败")
    if invalid_recipe:
        _fail("账号 AI Recipe 内容摘要回填失败")
    if foreign_key_violations:
        _fail(
            f"迁移后检测到 {len(foreign_key_violations)} 条孤儿外键"
        )


def _refuse_data_bearing_downgrade() -> None:
    connection = op.get_bind()
    blockers: list[str] = []
    if connection.execute(
        sa.text("SELECT 1 FROM prompt_profiles LIMIT 1")
    ).first():
        blockers.append("prompt_profiles.revision")
    if connection.execute(
        sa.text("SELECT 1 FROM account_ai_recipes LIMIT 1")
    ).first():
        blockers.append("account_ai_recipes.content_hash")
    if not blockers:
        return
    names = ", ".join(blockers)
    log.error(
        "P0-E 迁移拒绝有数据降级",
        extra={"downgrade_blockers": names},
    )
    raise RuntimeError(
        "P0E_DOWNGRADE_REQUIRES_BACKUP: 已存在 P0-E AI 版本数据，"
        f"禁止自动降级；请恢复迁移前备份。涉及对象：{names}"
    )


def _preflight_cross_revision_downgrade() -> None:
    destination = context.get_revision_argument()
    if destination in {down_revision, (down_revision,)}:
        return
    predecessor = context.script.get_revision(down_revision)
    guard = (
        getattr(
            predecessor.module,
            "_preflight_cross_revision_downgrade",
            None,
        )
        if predecessor is not None
        else None
    )
    if not callable(guard):
        _fail("无法加载 0019 跨版本降级保护")
    guard()


def _fail(message: str) -> NoReturn:
    log.error(
        "P0-E AI 迁移数据验证失败",
        extra={"validation_issue": message},
    )
    raise RuntimeError(f"P0E_MIGRATION_VALIDATION_FAILED: {message}")
