from __future__ import annotations

import logging
from collections.abc import Callable, Collection, Mapping
from functools import wraps
from typing import ParamSpec, TypeVar

from sqlalchemy import Select, text
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

_P = ParamSpec("_P")
_R = TypeVar("_R")


def log_repository_errors(
    operation: str,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """记录仓储异常后原样抛出，事务回滚由调用方负责。"""

    def decorator(function: Callable[_P, _R]) -> Callable[_P, _R]:
        @wraps(function)
        def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            try:
                return function(*args, **kwargs)
            except Exception:
                log.exception(
                    "AI 配置仓储操作失败",
                    extra={"operation": operation},
                )
                raise

        return wrapped

    return decorator


def validated_changes(
    changes: Mapping[str, object],
    allowed_fields: Collection[str],
) -> dict[str, object]:
    unexpected = sorted(set(changes) - set(allowed_fields))
    if unexpected:
        raise ValueError(f"包含不允许持久化的字段：{', '.join(unexpected)}")
    return dict(changes)


def limited(statement: Select[tuple[_R]], limit: int | None) -> Select[tuple[_R]]:
    if limit is None:
        return statement
    if limit < 1:
        raise ValueError("查询上限必须大于零")
    return statement.limit(limit)


_SQLITE_WRITE_LOCKS = {
    "prompt_profiles": text(
        "UPDATE prompt_profiles SET revision = revision WHERE 0"
    ),
    "composition_template_profiles": text(
        "UPDATE composition_template_profiles SET revision = revision WHERE 0"
    ),
    "account_ai_recipes": text(
        "UPDATE account_ai_recipes SET revision = revision WHERE 0"
    ),
    "capability_routes": text(
        "UPDATE capability_routes SET revision = revision WHERE 0"
    ),
}


def acquire_sqlite_write_lock(session: Session, table_name: str) -> None:
    """在版本激活前串行化 SQLite 的检查与写入。"""

    if session.get_bind().dialect.name != "sqlite":
        return
    statement = _SQLITE_WRITE_LOCKS.get(table_name)
    if statement is None:
        raise ValueError(f"未登记写锁目标表：{table_name}")
    session.execute(statement)
