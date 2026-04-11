from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from persistence import connect_sqlite, initialize_schema


@dataclass(frozen=True, slots=True)
class StoredSystemConfig:
    revision: int
    document: dict[str, Any]
    updated_at: str


class SystemConfigRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        initialize_schema(database_path)

    def load(self) -> StoredSystemConfig | None:
        with connect_sqlite(self._database_path) as connection:
            row = connection.execute(
                "SELECT revision, document, updated_at FROM system_config WHERE id = 1"
            ).fetchone()

        if row is None:
            return None

        return StoredSystemConfig(
            revision=int(row["revision"]),
            document=json.loads(str(row["document"])),
            updated_at=str(row["updated_at"]),
        )

    def save(self, document: dict[str, Any]) -> StoredSystemConfig:
        current = self.load()
        revision = 1 if current is None else current.revision + 1
        updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        with connect_sqlite(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO system_config (id, document, revision, updated_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    document = excluded.document,
                    revision = excluded.revision,
                    updated_at = excluded.updated_at
                """,
                (json.dumps(document), revision, updated_at),
            )
            connection.commit()

        return StoredSystemConfig(
            revision=revision,
            document=document,
            updated_at=updated_at,
        )
