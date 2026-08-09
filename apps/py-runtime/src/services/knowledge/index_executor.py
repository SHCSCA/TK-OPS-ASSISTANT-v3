from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from uuid import uuid4

from errors import DomainError, ErrorCode
from services.accounts.lifecycle_sync import AccountLifecycleSynchronizer
from services.accounts.unit_of_work import AccountUnitOfWork
from services.knowledge.content_store import KnowledgeContentStore
from services.knowledge.index_policy import KnowledgeIndexPolicy
from services.knowledge.index_state import KnowledgeIndexStateStore
from services.knowledge.index_types import (
    KnowledgeIndexPlan,
    KnowledgeIndexResult,
    KnowledgeIndexSource,
)
from services.knowledge.ports import (
    ControlledFileResolver,
    KnowledgeUrlFetcher,
    ResolvedKnowledgeContent,
)
from services.knowledge.source_validation import require_controlled_file_ref
from services.tasks.errors import TaskCancellationRequested

log = logging.getLogger(__name__)


class KnowledgeIndexExecutor:
    """读取真实来源并把哈希和状态证据写回账号聚合。"""

    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        *,
        content_store: KnowledgeContentStore,
        controlled_file_resolver: ControlledFileResolver,
        url_fetcher: KnowledgeUrlFetcher,
        lifecycle_synchronizer: AccountLifecycleSynchronizer,
        policy_provider: Callable[[], KnowledgeIndexPolicy] | None = None,
    ) -> None:
        self._state = KnowledgeIndexStateStore(
            unit_of_work,
            lifecycle_synchronizer=lifecycle_synchronizer,
        )
        self._content_store = content_store
        self._controlled_files = controlled_file_resolver
        self._url_fetcher = url_fetcher
        self._policy_provider = policy_provider

    def plan(
        self,
        account_id: str,
        source_ids: tuple[str, ...] | None,
    ) -> KnowledgeIndexPlan:
        return self._state.plan(account_id, source_ids)

    def index_source(
        self,
        account_id: str,
        source_id: str,
        *,
        task_id: str,
        cancel_check: Callable[[], None],
        policy: KnowledgeIndexPolicy | None = None,
    ) -> KnowledgeIndexResult:
        resolved_policy = self._resolve_policy(policy)
        started = False
        try:
            cancel_check()
            self._state.mark_indexing(
                account_id,
                source_id,
                task_id=task_id,
                config_revision=resolved_policy.config_revision,
            )
            started = True
            cancel_check()
            source = self._state.source(account_id, source_id)
            content = self._read_content(
                account_id,
                source,
                policy=resolved_policy,
            )
            cancel_check()
            _validate_content(content, policy=resolved_policy)
            digest = hashlib.sha256(content.data).hexdigest()
            cancel_check()
            revision = self._state.mark_ready(
                account_id,
                source_id,
                content_hash=digest,
                task_id=task_id,
                config_revision=resolved_policy.config_revision,
            )
            return KnowledgeIndexResult(
                source_id=source_id,
                content_hash=digest,
                byte_size=len(content.data),
                account_revision=revision,
            )
        except TaskCancellationRequested:
            if started:
                self._record_cancelled(
                    account_id,
                    source_id,
                    task_id=task_id,
                    config_revision=resolved_policy.config_revision,
                )
            raise
        except DomainError as exc:
            if started:
                self._record_failure(
                    account_id,
                    source_id,
                    error_code=exc.error_code,
                    task_id=task_id,
                    config_revision=resolved_policy.config_revision,
                )
            raise
        except Exception as exc:
            log_id = f"log_{uuid4().hex}"
            log.exception(
                "知识来源索引发生未预期异常",
                extra={
                    "account_id": account_id,
                    "resource_type": "knowledge_source",
                    "resource_id": source_id,
                    "task_id": task_id,
                    "log_id": log_id,
                    "error_code": ErrorCode.KNOWLEDGE_INDEX_FAILED.value,
                    "config_revision": resolved_policy.config_revision,
                },
            )
            if started:
                self._record_failure(
                    account_id,
                    source_id,
                    error_code=ErrorCode.KNOWLEDGE_INDEX_FAILED.value,
                    task_id=task_id,
                    config_revision=resolved_policy.config_revision,
                    log_id=log_id,
                )
            raise DomainError(
                ErrorCode.KNOWLEDGE_INDEX_FAILED,
                "知识来源索引失败，请查看诊断日志后重试",
                status_code=500,
                loggable=True,
                log_context={
                    "account_id": account_id,
                    "resource_id": source_id,
                    "task_id": task_id,
                    "log_id": log_id,
                },
            ) from exc

    def _read_content(
        self,
        account_id: str,
        source: KnowledgeIndexSource,
        *,
        policy: KnowledgeIndexPolicy,
    ) -> ResolvedKnowledgeContent:
        if source.source_mode == "text":
            return ResolvedKnowledgeContent(
                data=self._content_store.read_bytes(
                    account_id,
                    source.source_ref,
                ),
                media_type="text/plain; charset=utf-8",
            )
        if source.source_mode == "file":
            return self._controlled_files.read_bytes(
                account_id,
                require_controlled_file_ref(source.source_ref),
                max_bytes=policy.max_source_bytes,
            )
        if source.source_mode == "url" and source.source_url is not None:
            return self._url_fetcher.fetch(
                source.source_url,
                policy=policy,
            )
        raise DomainError(
            ErrorCode.KNOWLEDGE_SOURCE_INVALID,
            "知识来源摄取方式与持久化证据不一致",
            status_code=422,
            loggable=True,
        )

    def _resolve_policy(
        self,
        policy: KnowledgeIndexPolicy | None,
    ) -> KnowledgeIndexPolicy:
        if policy is not None:
            return policy
        if self._policy_provider is None:
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "知识索引策略尚未装配",
                status_code=500,
                loggable=True,
            )
        try:
            return self._policy_provider()
        except DomainError:
            raise
        except Exception as exc:
            log.exception("读取知识索引策略失败")
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "知识索引策略读取失败，请查看诊断日志",
                status_code=500,
                loggable=True,
            ) from exc

    def _record_failure(
        self,
        account_id: str,
        source_id: str,
        *,
        error_code: str,
        task_id: str,
        config_revision: int,
        log_id: str | None = None,
    ) -> None:
        evidence_log_id = log_id or f"log_{uuid4().hex}"
        if log_id is None:
            log.exception(
                "知识来源索引失败",
                extra={
                    "account_id": account_id,
                    "resource_type": "knowledge_source",
                    "resource_id": source_id,
                    "task_id": task_id,
                    "log_id": evidence_log_id,
                    "error_code": error_code,
                    "config_revision": config_revision,
                },
            )
        try:
            self._state.mark_failed(
                account_id,
                source_id,
                error_code=error_code,
                error_log_id=evidence_log_id,
                task_id=task_id,
                config_revision=config_revision,
            )
        except Exception:
            log.exception(
                "写入知识索引失败证据时发生异常",
                extra={
                    "account_id": account_id,
                    "resource_type": "knowledge_source",
                    "resource_id": source_id,
                    "task_id": task_id,
                    "log_id": evidence_log_id,
                    "error_code": error_code,
                },
            )

    def _record_cancelled(
        self,
        account_id: str,
        source_id: str,
        *,
        task_id: str,
        config_revision: int,
    ) -> None:
        try:
            self._state.mark_cancelled(
                account_id,
                source_id,
                task_id=task_id,
                config_revision=config_revision,
            )
        except Exception:
            log.exception(
                "写入知识索引取消状态时发生异常",
                extra={
                    "account_id": account_id,
                    "resource_type": "knowledge_source",
                    "resource_id": source_id,
                    "task_id": task_id,
                },
            )


def _validate_content(
    content: ResolvedKnowledgeContent,
    *,
    policy: KnowledgeIndexPolicy,
) -> None:
    if not isinstance(content.data, bytes):
        raise DomainError(
            ErrorCode.KNOWLEDGE_INDEX_FAILED,
            "知识来源读取器返回了无效内容",
            status_code=500,
            loggable=True,
        )
    if not content.data:
        raise DomainError(
            ErrorCode.KNOWLEDGE_INDEX_FAILED,
            "知识来源内容为空，无法建立索引",
            status_code=422,
        )
    if len(content.data) > policy.max_source_bytes:
        raise DomainError(
            ErrorCode.KNOWLEDGE_INDEX_FAILED,
            "知识来源超过配置总线允许的大小",
            status_code=422,
        )
