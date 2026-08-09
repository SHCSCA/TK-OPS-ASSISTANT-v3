from __future__ import annotations

from sqlalchemy import text


def ensure_table_columns(
    connection,
    table_name: str,
    required_columns: dict[str, str],
) -> set[str] | None:  # type: ignore[no-untyped-def]
    columns = table_columns(connection, table_name)
    if not columns:
        return None

    for column_name, column_sql in required_columns.items():
        if column_name in columns:
            continue
        connection.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
        )

    return table_columns(connection, table_name)


def table_info(
    connection,
    table_name: str,
) -> dict[str, dict[str, object]]:  # type: ignore[no-untyped-def]
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
    return {
        str(row["name"]): {
            "notnull": int(row["notnull"]),
            "type": str(row["type"]),
        }
        for row in rows
    }


def table_columns(connection, table_name: str) -> set[str]:  # type: ignore[no-untyped-def]
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
    return {str(row["name"]) for row in rows}


def column_expr(columns: set[str], column_name: str) -> str:
    return column_name if column_name in columns else "NULL"


def nullif_text_column_expr(columns: set[str], column_name: str) -> str:
    return f"NULLIF({column_name}, '')" if column_name in columns else "NULL"


def has_blocking_legacy_asset_columns(connection) -> bool:  # type: ignore[no-untyped-def]
    rows = connection.execute(text("PRAGMA table_info(assets)")).mappings().all()
    legacy_columns = {"kind", "file_name", "mime_type"}
    return any(
        str(row["name"]) in legacy_columns and int(row["notnull"]) == 1
        for row in rows
    )


def has_blocking_legacy_account_columns(connection) -> bool:  # type: ignore[no-untyped-def]
    rows = connection.execute(text("PRAGMA table_info(accounts)")).mappings().all()
    legacy_columns = {"handle", "display_name", "group_name", "source", "metadata_json"}
    for row in rows:
        column_name = str(row["name"])
        if column_name in legacy_columns and int(row["notnull"]) == 1:
            if row["dflt_value"] in (None, ""):
                return True
    return False


def has_blocking_legacy_device_workspace_columns(
    connection,
) -> bool:  # type: ignore[no-untyped-def]
    rows = connection.execute(text("PRAGMA table_info(device_workspaces)")).mappings().all()
    legacy_columns = {"device_type", "browser_profile", "health_json", "source"}
    for row in rows:
        column_name = str(row["name"])
        if column_name in legacy_columns and int(row["notnull"]) == 1:
            return True
        if column_name in {"created_at", "updated_at"} and int(row["notnull"]) == 1:
            if row["dflt_value"] in (None, ""):
                return True
    return False


def has_blocking_legacy_execution_binding_columns(
    connection,
) -> bool:  # type: ignore[no-untyped-def]
    rows = connection.execute(text("PRAGMA table_info(execution_bindings)")).mappings().all()
    nullable_columns = {"source", "metadata_json"}
    for row in rows:
        column_name = str(row["name"])
        if column_name in nullable_columns and int(row["notnull"]) == 1:
            return True
        if column_name in {"created_at", "updated_at"} and int(row["notnull"]) == 1:
            if row["dflt_value"] in (None, ""):
                return True
    return False
