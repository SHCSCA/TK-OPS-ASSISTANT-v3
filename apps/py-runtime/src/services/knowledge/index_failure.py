from __future__ import annotations

import logging
from uuid import uuid4

from errors import ErrorCode
from services.knowledge.index_state import KnowledgeIndexStateStore

log = logging.getLogger(__name__)


class KnowledgeIndexFailureRecorder:
    def __init__(self, state: KnowledgeIndexStateStore) -> None:
        self._state = state

    def record_failure(
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
            log.error(
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
            if error_code == ErrorCode.CONTROLLED_FILE_CHANGED.value:
                self._state.mark_stale(
                    account_id,
                    source_id,
                    error_code=error_code,
                    error_log_id=evidence_log_id,
                    task_id=task_id,
                    config_revision=config_revision,
                )
            else:
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

    def record_cancelled(
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
