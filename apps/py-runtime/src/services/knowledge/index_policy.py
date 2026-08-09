from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from services.tasks.errors import task_snapshot_invalid


@dataclass(frozen=True, slots=True)
class KnowledgeIndexPolicy:
    max_source_bytes: int
    url_timeout_seconds: int
    max_redirects: int
    config_revision: int

    def __post_init__(self) -> None:
        if isinstance(self.max_source_bytes, bool) or not (
            1 * 1024 * 1024
            <= self.max_source_bytes
            <= 100 * 1024 * 1024
        ):
            raise ValueError("知识来源大小上限必须位于 1 MiB 到 100 MiB")
        if isinstance(self.url_timeout_seconds, bool) or not (
            1 <= self.url_timeout_seconds <= 120
        ):
            raise ValueError("知识 URL 超时必须位于 1 到 120 秒")
        if isinstance(self.max_redirects, bool) or not (
            0 <= self.max_redirects <= 10
        ):
            raise ValueError("知识 URL 重定向上限必须位于 0 到 10")
        if isinstance(self.config_revision, bool) or self.config_revision < 0:
            raise ValueError("知识索引策略配置修订号不能小于零")


def knowledge_policy_snapshot(
    policy: KnowledgeIndexPolicy,
) -> dict[str, int]:
    return {
        "maxSourceBytes": policy.max_source_bytes,
        "urlTimeoutSeconds": policy.url_timeout_seconds,
        "maxRedirects": policy.max_redirects,
        "configRevision": policy.config_revision,
    }


def knowledge_policy_from_snapshot(
    value: object,
) -> KnowledgeIndexPolicy:
    if not isinstance(value, Mapping) or set(value) != {
        "maxSourceBytes",
        "urlTimeoutSeconds",
        "maxRedirects",
        "configRevision",
    }:
        raise task_snapshot_invalid(
            "知识索引任务缺少完整的创建时策略快照"
        )
    fields = tuple(value[key] for key in (
        "maxSourceBytes",
        "urlTimeoutSeconds",
        "maxRedirects",
        "configRevision",
    ))
    if any(isinstance(item, bool) or not isinstance(item, int) for item in fields):
        raise task_snapshot_invalid("知识索引策略快照字段格式无效")
    try:
        return KnowledgeIndexPolicy(
            max_source_bytes=fields[0],
            url_timeout_seconds=fields[1],
            max_redirects=fields[2],
            config_revision=fields[3],
        )
    except ValueError as exc:
        raise task_snapshot_invalid("知识索引策略快照超出允许范围") from exc
