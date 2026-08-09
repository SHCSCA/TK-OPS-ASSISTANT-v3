from __future__ import annotations

from services.knowledge.index_executor import KnowledgeIndexExecutor
from services.knowledge.task_handlers import (
    KNOWLEDGE_INDEX_TASK_TYPE,
    build_knowledge_index_handler,
)
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.types import (
    TaskHandlerDefinition,
    TaskResumePolicy,
)


def register_knowledge_index_handler(
    registry: TaskHandlerRegistry,
    *,
    executor: KnowledgeIndexExecutor,
    timeout_seconds: int | None = None,
) -> None:
    registry.register(
        TaskHandlerDefinition(
            task_type=KNOWLEDGE_INDEX_TASK_TYPE,
            handler=build_knowledge_index_handler(executor),
            allowed_snapshot_fields=frozenset({"sourceIds", "policy"}),
            resume_policy=TaskResumePolicy.RESUME,
            cancellable=True,
            handler_version=1,
            timeout_seconds=timeout_seconds,
            single_active_per_scope=True,
        )
    )
