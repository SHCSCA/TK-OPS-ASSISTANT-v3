from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from domain.models import Base
from domain.models.runtime_event import RuntimeEvent
from domain.models.runtime_task import RuntimeTask
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.runtime_event_repository import RuntimeEventRepository
from services.events import RuntimeEventService


@dataclass(frozen=True, slots=True)
class RuntimeEventTestStack:
    engine: Engine
    session_factory: sessionmaker[Session]
    repository: RuntimeEventRepository
    service: RuntimeEventService


def make_runtime_event_stack(
    database_path: Path,
    *,
    replay_limit: int = 100,
) -> RuntimeEventTestStack:
    for model in (RuntimeEvent, RuntimeTask):
        if model.metadata is not Base.metadata:
            raise AssertionError("Runtime 事件模型必须注册到统一元数据")

    engine = create_runtime_engine(database_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repository = RuntimeEventRepository(session_factory=session_factory)
    return RuntimeEventTestStack(
        engine=engine,
        session_factory=session_factory,
        repository=repository,
        service=RuntimeEventService(repository, replay_limit=replay_limit),
    )
