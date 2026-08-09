from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="为 E2E 临时库建立真实账号执行绑定",
    )
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--fixture-key", required=True)
    return parser.parse_args()


def _require_e2e_directory(raw_path: str) -> Path:
    data_dir = Path(raw_path).expanduser().resolve()
    if not data_dir.is_dir() or not data_dir.name.startswith("tk-ops-e2e-"):
        raise ValueError("绑定夹具只能写入受控 E2E 临时目录")
    return data_dir


def _seed(
    data_dir: Path,
    account_id: str,
    fixture_key: str,
) -> dict[str, str]:
    safe_key = fixture_key.strip().lower()
    if not safe_key or not safe_key.replace("-", "").isalnum():
        raise ValueError("fixture-key 格式无效")

    database_path = data_dir / "runtime.db"
    if not database_path.is_file():
        raise FileNotFoundError("E2E Runtime 数据库尚未创建")

    workspace_id = f"workspace_e2e_{safe_key}"
    browser_id = f"browser_e2e_{safe_key}"
    binding_id = f"binding_e2e_{safe_key}"
    workspace_root = data_dir / "workspaces" / safe_key
    profile_root = data_dir / "browser-profiles" / safe_key
    workspace_root.mkdir(parents=True, exist_ok=True)
    profile_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()

    connection = sqlite3.connect(database_path, timeout=10)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("BEGIN IMMEDIATE")
        account = connection.execute(
            "SELECT id FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        if account is None:
            raise ValueError("目标 E2E 账号不存在")
        connection.execute(
            """
            INSERT INTO device_workspaces (
                id, account_id, name, root_path, status, error_count,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                account_id = excluded.account_id,
                name = excluded.name,
                root_path = excluded.root_path,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (
                workspace_id,
                account_id,
                f"E2E {safe_key} 本地工作区",
                str(workspace_root),
                "ready",
                timestamp,
                timestamp,
            ),
        )
        connection.execute(
            """
            INSERT INTO browser_instances (
                id, account_id, workspace_id, name, profile_path, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                account_id = excluded.account_id,
                workspace_id = excluded.workspace_id,
                name = excluded.name,
                profile_path = excluded.profile_path,
                status = excluded.status,
                process_id = NULL,
                updated_at = excluded.updated_at
            """,
            (
                browser_id,
                account_id,
                workspace_id,
                f"E2E {safe_key} 浏览器实例",
                str(profile_root),
                "stopped",
                timestamp,
                timestamp,
            ),
        )
        connection.execute(
            """
            INSERT INTO execution_bindings (
                id, account_id, device_workspace_id, browser_instance_id,
                status, source, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                account_id = excluded.account_id,
                device_workspace_id = excluded.device_workspace_id,
                browser_instance_id = excluded.browser_instance_id,
                status = excluded.status,
                source = excluded.source,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
            """,
            (
                binding_id,
                account_id,
                workspace_id,
                browser_id,
                "active",
                "e2e_local_fixture",
                json.dumps(
                    {
                        "fixture": True,
                        "browserProcessClaimed": False,
                    },
                    ensure_ascii=False,
                ),
                timestamp,
                timestamp,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        log.exception("写入 E2E 执行绑定失败")
        raise
    finally:
        connection.close()

    return {
        "bindingId": binding_id,
        "browserInstanceId": browser_id,
        "deviceWorkspaceId": workspace_id,
    }


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )
    try:
        args = _arguments()
        result = _seed(
            _require_e2e_directory(args.data_dir),
            str(args.account_id),
            str(args.fixture_key),
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception:
        log.exception("E2E 执行绑定夹具准备失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
