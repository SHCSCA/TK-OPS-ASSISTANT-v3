from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from domain.models import SystemConfig

log = logging.getLogger(__name__)


class SystemConfigRevisionConflict(Exception):
    pass


@dataclass(frozen=True, slots=True)
class StoredSystemConfig:
    revision: int
    document: dict[str, Any]
    updated_at: str
    ai_config_revision: int = 0


BeforeConfigCommit = Callable[[Session, StoredSystemConfig], None]


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
            ai_config_revision=row.ai_config_revision,
            document=json.loads(row.document),
            updated_at=row.updated_at,
        )

    def save(self, document: dict[str, Any]) -> StoredSystemConfig:
        current = self.load()
        revision = 1 if current is None else current.revision + 1
        ai_config_revision = (
            0 if current is None else current.ai_config_revision
        )
        updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        with self._session_factory() as session:
            session.merge(
                SystemConfig(
                    id=1,
                    document=json.dumps(document),
                    revision=revision,
                    ai_config_revision=ai_config_revision,
                    updated_at=updated_at,
                )
            )
            session.commit()

        return StoredSystemConfig(
            revision=revision,
            ai_config_revision=ai_config_revision,
            document=document,
            updated_at=updated_at,
        )

    def save_if_revision(
        self,
        document: dict[str, Any],
        *,
        expected_revision: int,
        before_commit: BeforeConfigCommit | None = None,
    ) -> StoredSystemConfig:
        current = self.load()
        updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        next_revision = expected_revision + 1
        serialized = json.dumps(document, ensure_ascii=False)
        saved = StoredSystemConfig(
            revision=next_revision,
            ai_config_revision=(
                0 if current is None else current.ai_config_revision
            ),
            document=document,
            updated_at=updated_at,
        )

        with self._session_factory() as session:
            try:
                if expected_revision == 0:
                    if session.get(SystemConfig, 1) is not None:
                        raise SystemConfigRevisionConflict
                    session.add(
                        SystemConfig(
                            id=1,
                            document=serialized,
                            revision=next_revision,
                            ai_config_revision=0,
                            updated_at=updated_at,
                        )
                    )
                else:
                    result = session.execute(
                        update(SystemConfig)
                        .where(
                            SystemConfig.id == 1,
                            SystemConfig.revision == expected_revision,
                        )
                        .values(
                            document=serialized,
                            revision=next_revision,
                            updated_at=updated_at,
                        )
                    )
                    if result.rowcount != 1:
                        raise SystemConfigRevisionConflict
                session.flush()
                if before_commit is not None:
                    before_commit(session, saved)
                session.commit()
            except SystemConfigRevisionConflict:
                session.rollback()
                raise
            except IntegrityError as exc:
                session.rollback()
                raise SystemConfigRevisionConflict from exc
            except Exception:
                session.rollback()
                log.exception("系统配置事务保存失败")
                raise

        return saved
