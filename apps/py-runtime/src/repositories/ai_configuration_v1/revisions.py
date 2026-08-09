from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from domain.models.system_config import SystemConfig
from repositories.ai_configuration_v1._support import log_repository_errors


class AIConfigRevisionRepository:
    """在调用方事务内读取和原子递增系统 AI 配置修订。"""

    @log_repository_errors("读取 AI 配置修订")
    def get(self, session: Session) -> int:
        row = session.get(SystemConfig, 1)
        return 0 if row is None else int(row.ai_config_revision)

    @log_repository_errors("递增 AI 配置修订")
    def increment(self, session: Session) -> int:
        statement = (
            sqlite_insert(SystemConfig)
            .values(
                id=1,
                document="{}",
                revision=1,
                ai_config_revision=1,
                updated_at=_utc_now(),
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "ai_config_revision": SystemConfig.ai_config_revision + 1,
                },
            )
            .returning(SystemConfig.ai_config_revision)
        )
        revision = session.scalar(statement)
        if revision is None:
            raise RuntimeError("AI 配置修订递增未返回结果")
        cached = session.identity_map.get(
            session.identity_key(SystemConfig, 1)
        )
        if cached is not None:
            session.expire(cached, ["ai_config_revision"])
        return int(revision)

    def get_ai_config_revision(self, session: Session) -> int:
        return self.get(session)

    def increment_ai_config_revision(self, session: Session) -> int:
        return self.increment(session)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
