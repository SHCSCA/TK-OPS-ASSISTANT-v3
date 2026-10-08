from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from errors import DomainError, ErrorCode
from schemas.v1.bootstrap import TaskAcceptedDto
from schemas.v1.knowledge import KnowledgeIndexInput
from services.accounts.unit_of_work import AccountUnitOfWork
from services.knowledge.index_policy import (
    KnowledgeIndexPolicy,
    knowledge_policy_snapshot,
)
from services.knowledge.index_state import KnowledgeIndexStateStore
from services.knowledge.task_handlers import KNOWLEDGE_INDEX_TASK_TYPE
from services.knowledge.file_extractors import EXTRACTOR_VERSION
from services.tasks.coordinator import TaskCoordinator

log = logging.getLogger(__name__)


class KnowledgeIndexSubmissionService:
    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        *,
        coordinator: TaskCoordinator,
        policy_provider: Callable[[], KnowledgeIndexPolicy],
    ) -> None:
        self._state = KnowledgeIndexStateStore(unit_of_work)
        self._coordinator = coordinator
        self._policy_provider = policy_provider

    async def submit(
        self,
        account_id: str,
        payload: KnowledgeIndexInput,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        plan = await asyncio.to_thread(
            self._state.plan,
            account_id,
            (
                None
                if payload.sourceIds is None
                else tuple(payload.sourceIds)
            ),
        )
        policy = self._load_policy()
        record = await self._coordinator.submit_account_task(
            account_id,
            task_type=KNOWLEDGE_INDEX_TASK_TYPE,
            payload={
                "sourceIds": list(plan.source_ids),
                "sourceManifests": [
                    item.to_snapshot()
                    for item in plan.source_manifests
                ],
                "policy": knowledge_policy_snapshot(policy),
                "extractorVersion": EXTRACTOR_VERSION,
            },
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )
        return TaskAcceptedDto(
            taskId=record.id,
            scope="account",
            accountId=account_id,
            taskType=record.task_type,
            status="queued",
            cancellable=record.cancellable,
            createdAt=record.created_at,
        )

    def _load_policy(self) -> KnowledgeIndexPolicy:
        try:
            return self._policy_provider()
        except DomainError:
            raise
        except Exception as exc:
            log.exception("创建知识索引任务时读取配置策略失败")
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "知识索引策略读取失败，请查看诊断日志",
                status_code=500,
                loggable=True,
            ) from exc
