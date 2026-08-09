from __future__ import annotations

from services.tasks.errors import task_handler_not_found
from services.tasks.types import TaskHandlerDefinition


class TaskHandlerRegistry:
    """保存稳定任务类型到版本化处理器的唯一映射。"""

    def __init__(self) -> None:
        self._definitions: dict[str, TaskHandlerDefinition] = {}

    def register(self, definition: TaskHandlerDefinition) -> None:
        task_type = definition.task_type.strip()
        if task_type in self._definitions:
            raise ValueError(f"任务处理器已注册：{task_type}")
        self._definitions[task_type] = definition

    def require(self, task_type: str) -> TaskHandlerDefinition:
        definition = self._definitions.get(task_type.strip())
        if definition is None:
            raise task_handler_not_found(task_type)
        return definition

    def get(self, task_type: str) -> TaskHandlerDefinition | None:
        return self._definitions.get(task_type.strip())

    def task_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._definitions))
