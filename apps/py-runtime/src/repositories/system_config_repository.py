from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from domain.models import SystemConfig


@dataclass(frozen=True, slots=True)
class StoredSystemConfig:
    revision: int
    document: dict[str, Any]
    updated_at: str


class SystemConfigRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def load(self) -> StoredSystemConfig | None:
        with self._session_factory() as session:
            row = session.get(SystemConfig, 1)

        if row is None:
            return None

        return StoredSystemConfig(
            revision=row.revision,
            document=json.loads(row.document),
            updated_at=row.updated_at,
        )

    def save(self, document: dict[str, Any]) -> StoredSystemConfig:
        current = self.load()
        revision = 1 if current is None else current.revision + 1
        updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        with self._session_factory() as session:
            session.merge(
                SystemConfig(
                    id=1,
                    document=json.dumps(document),
                    revision=revision,
                    updated_at=updated_at,
                )
            )
            session.commit()

        return StoredSystemConfig(
            revision=revision,
            document=document,
            updated_at=updated_at,
        )
