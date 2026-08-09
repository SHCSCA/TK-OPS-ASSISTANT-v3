from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
import pytest
from sqlalchemy import create_engine

from persistence.migration.p0c_account_data_migration import (
    backfill_account_defaults,
)
from tests.runtime.p0c_migration_test_support import (
    insert_account,
    migration_config,
    rows,
)

REVISION_0018 = "0018_p0_runtime_kernel"
REVISION_0019 = "0019_p0_account_vertical_chain"


def test_0019_backfills_missing_account_defaults_without_overwrite(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0c-account-defaults.db"
    config = migration_config(database_path)
    command.upgrade(config, REVISION_0018)

    with sqlite3.connect(database_path) as connection:
        insert_account(
            connection,
            "account-missing",
            status="active",
        )
        connection.execute(
            """
            UPDATE accounts
            SET status_reason_code = 'STALE_LEGACY_REASON'
            WHERE id = 'account-missing'
            """
        )
        insert_account(
            connection,
            "account-existing",
            status="draft",
        )
        connection.execute(
            """
            INSERT INTO account_knowledge_bases (
                id, account_id, status, rules_json, rules_version,
                index_revision, last_indexed_at, error_code, error_log_id,
                revision, created_at, updated_at
            ) VALUES (
                'base-existing', 'account-existing', 'stale',
                '{"legacy":true}', 7, 9, '2026-01-02',
                'LEGACY_INDEX_STALE', 'log-existing', 4,
                '2026-01-01', '2026-01-02'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO account_publish_defaults (
                account_id, timezone, privacy_level, allow_comments,
                allow_duet, allow_stitch, caption_rules_json, revision,
                created_at, updated_at
            ) VALUES (
                'account-existing', 'Asia/Shanghai', 'public', 1, 1, 1,
                '{"suffix":"legacy"}', 5, '2026-01-01', '2026-01-02'
            )
            """
        )
        connection.commit()

    command.upgrade(config, REVISION_0019)

    account_rows = rows(
        database_path,
        """
        SELECT id, status, status_reason_code
        FROM accounts
        ORDER BY id
        """,
    )
    base_rows = rows(
        database_path,
        """
        SELECT account_id, status, rules_json, rules_version,
               index_revision, revision
        FROM account_knowledge_bases
        ORDER BY account_id
        """,
    )
    defaults_rows = rows(
        database_path,
        """
        SELECT account_id, timezone, privacy_level, allow_comments,
               allow_duet, allow_stitch, caption_rules_json, revision
        FROM account_publish_defaults
        ORDER BY account_id
        """,
    )

    assert account_rows == [
        ("account-existing", "draft", None),
        (
            "account-missing",
            "draft",
            "P0C_LEGACY_ACTIVE_DRAFT_REVIEW",
        ),
    ]
    assert base_rows == [
        (
            "account-existing",
            "stale",
            '{"legacy":true}',
            7,
            9,
            4,
        ),
        (
            "account-missing",
            "empty",
            '{"inclusionRules":{},"exclusionRules":{},'
            '"citationPolicy":{}}',
            0,
            0,
            1,
        ),
    ]
    assert defaults_rows == [
        (
            "account-existing",
            "Asia/Shanghai",
            "public",
            1,
            1,
            1,
            '{"suffix":"legacy"}',
            5,
        ),
        (
            "account-missing",
            "UTC",
            "private",
            0,
            0,
            0,
            "{}",
            1,
        ),
    ]
    assert rows(
        database_path,
        "SELECT COUNT(*) FROM knowledge_sources",
    ) == [(0,)]
    assert rows(
        database_path,
        "SELECT COUNT(*) FROM knowledge_snapshots",
    ) == [(0,)]

    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    try:
        with engine.begin() as connection:
            backfill_account_defaults(connection)
            backfill_account_defaults(connection)
    finally:
        engine.dispose()

    assert rows(
        database_path,
        "SELECT COUNT(*) FROM account_knowledge_bases",
    ) == [(2,)]
    assert rows(
        database_path,
        "SELECT COUNT(*) FROM account_publish_defaults",
    ) == [(2,)]
    assert rows(
        database_path,
        """
        SELECT timezone, privacy_level, caption_rules_json, revision
        FROM account_publish_defaults
        WHERE account_id = 'account-existing'
        """,
    ) == [("Asia/Shanghai", "public", '{"suffix":"legacy"}', 5)]


def test_0019_rejects_deterministic_knowledge_base_id_collision(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0c-account-default-collision.db"
    config = migration_config(database_path)
    command.upgrade(config, REVISION_0018)
    candidate_id = f"kb_p0c_{'account-collision'.encode('utf-8').hex()}"

    with sqlite3.connect(database_path) as connection:
        insert_account(
            connection,
            "account-collision",
            status="active",
        )
        insert_account(
            connection,
            "account-owner",
            status="draft",
        )
        connection.execute(
            """
            INSERT INTO account_knowledge_bases (
                id, account_id, status, rules_json, rules_version,
                index_revision, revision, created_at, updated_at
            ) VALUES (?, 'account-owner', 'empty', '{}', 0, 0, 1,
                      '2026-01-01', '2026-01-01')
            """,
            (candidate_id,),
        )
        connection.commit()

    with pytest.raises(
        RuntimeError,
        match="账号知识库确定性回填 ID 与既有对象冲突",
    ):
        command.upgrade(config, REVISION_0019)

    assert rows(
        database_path,
        "SELECT version_num FROM alembic_version",
    ) == [(REVISION_0018,)]
    assert rows(
        database_path,
        """
        SELECT status, status_reason_code
        FROM accounts
        WHERE id = 'account-collision'
        """,
    ) == [("active", None)]
    assert rows(
        database_path,
        "SELECT COUNT(*) FROM account_publish_defaults",
    ) == [(0,)]
