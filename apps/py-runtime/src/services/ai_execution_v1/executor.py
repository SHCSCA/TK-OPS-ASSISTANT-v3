from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from uuid import uuid4

from domain.models.ai_execution_snapshot import AIExecutionCandidate
from errors import DomainError, ErrorCode
from services.ai_configuration_v1.json_codec import content_hash
from services.tasks.errors import TaskCancellationRequested
from services.tasks.types import TaskExecutionContext

from .concurrency import AIExecutionConcurrencyGate
from .content_store import AIExecutionContentStore
from .error_mapping import map_provider_failure
from .execution_material import (
    AIExecutionMaterialLoader,
    FrozenExecutionMaterial,
)
from .execution_state import AIExecutionStateService
from .output_validation import validate_provider_output
from .policies import actual_cost_micros
from .provider_runtime import (
    AIExecutionProviderRuntime,
    FrozenCandidateRuntime,
)
from .types import (
    AIProviderRequest,
    CancellationToken,
    ProviderCallError,
)
from .unit_of_work import AIExecutionUnitOfWork

log = logging.getLogger(__name__)


class AIExecutionExecutor:
    """串行执行 retry/fallback，并确保失败不会隐式重复收费调用。"""

    def __init__(
        self,
        unit_of_work: AIExecutionUnitOfWork,
        *,
        material_loader: AIExecutionMaterialLoader,
        provider_runtime: AIExecutionProviderRuntime,
        state: AIExecutionStateService,
        content_store: AIExecutionContentStore,
        concurrency_gate: AIExecutionConcurrencyGate,
        retry_base_delay_ms: int,
        retry_max_delay_ms: int,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._materials = material_loader
        self._providers = provider_runtime
        self._state = state
        self._content_store = content_store
        self._concurrency = concurrency_gate
        self._retry_base_delay_ms = retry_base_delay_ms
        self._retry_max_delay_ms = retry_max_delay_ms

    async def execute(
        self,
        context: TaskExecutionContext,
        *,
        account_id: str,
        execution_id: str,
        expected_snapshot_hash: str,
    ) -> None:
        active_job_id: str | None = None
        try:
            await asyncio.to_thread(
                self._state.start_execution,
                account_id,
                execution_id,
            )
            material = await asyncio.to_thread(
                self._load_material,
                account_id,
                execution_id,
            )
            if material.snapshot.snapshot_hash != expected_snapshot_hash:
                raise DomainError(
                    ErrorCode.TASK_SNAPSHOT_INVALID,
                    "AI 执行任务快照与业务快照不一致",
                    status_code=500,
                    loggable=True,
                )
            total_deadline = (
                time.monotonic() + material.policy.timeout_ms / 1_000
            )
            await context.report_progress(0.1)
            for fallback_index, candidate in enumerate(material.candidates):
                retries = min(
                    int(candidate.max_retries),
                    material.policy.max_retries,
                )
                for retry_index in range(retries + 1):
                    context.raise_if_cancelled()
                    runtime = await asyncio.to_thread(
                        self._load_candidate,
                        account_id,
                        candidate,
                    )
                    request = AIProviderRequest(
                        capability_key=material.execution.capability_key,
                        model=runtime.model,
                        messages=material.rendered_prompt.messages,
                        max_output_units=material.policy.max_output_units,
                        temperature=material.policy.temperature,
                        idempotency_key=(
                            f"{execution_id}:{fallback_index}:{retry_index}"
                        ),
                    )
                    planned_hash = content_hash(
                        {
                            "snapshotHash": material.snapshot.snapshot_hash,
                            "candidateHash": candidate.snapshot_hash,
                            "fallbackIndex": fallback_index,
                            "retryIndex": retry_index,
                        }
                    )
                    job = await asyncio.to_thread(
                        self._state.start_job,
                        account_id,
                        execution_id,
                        candidate,
                        fallback_index=fallback_index,
                        retry_index=retry_index,
                        planned_request_hash=planned_hash,
                    )
                    active_job_id = job.id
                    token = CancellationToken()
                    try:
                        queue_timeout = min(
                            int(candidate.timeout_ms) / 1_000,
                            max(0.0, total_deadline - time.monotonic()),
                        )
                        async with self._concurrency.lease(
                            account_id=account_id,
                            route_provider_key=(
                                f"{material.snapshot.route_revision_id}:"
                                f"{candidate.provider_revision_id}"
                            ),
                            limit=int(candidate.max_concurrency),
                            timeout_seconds=queue_timeout,
                            cancellation_probe=context.raise_if_cancelled,
                        ):
                            context.raise_if_cancelled()
                            call_deadline = min(
                                total_deadline,
                                time.monotonic()
                                + int(candidate.timeout_ms) / 1_000,
                            )
                            result = await asyncio.to_thread(
                                runtime.port.execute,
                                request,
                                deadline_monotonic=call_deadline,
                                cancel_token=token,
                            )
                    except asyncio.CancelledError:
                        token.cancel()
                        raise
                    except TaskCancellationRequested:
                        token.cancel()
                        raise
                    except ProviderCallError as exc:
                        decision = map_provider_failure(exc)
                        within_total = time.monotonic() < total_deadline
                        can_retry = (
                            decision.retryable
                            and retry_index < retries
                            and within_total
                        )
                        can_fallback = (
                            not can_retry
                            and decision.fallback_allowed
                            and material.policy.allow_fallback
                            and fallback_index + 1 < len(material.candidates)
                            and within_total
                        )
                        terminal = not can_retry and not can_fallback
                        terminal_code = (
                            decision.error_code
                            if decision.result_unknown
                            else (
                                ErrorCode.AI_ALL_CANDIDATES_FAILED.value
                                if len(material.candidates) > 1
                                else decision.error_code
                            )
                        )
                        await asyncio.to_thread(
                            self._state.record_job_failure,
                            account_id,
                            execution_id,
                            job.id,
                            error_code=decision.error_code,
                            safe_summary=decision.safe_summary,
                            failure_kind=decision.failure_kind,
                            retryable=decision.retryable,
                            provider_status_code=exc.status_code,
                            provider_request_id_hash=None,
                            response_hash=exc.response_hash,
                            duration_ms=None,
                            terminal=terminal,
                            terminal_error_code=(
                                terminal_code if terminal else None
                            ),
                        )
                        active_job_id = None
                        if terminal:
                            raise DomainError(
                                terminal_code,
                                decision.safe_summary,
                                status_code=502,
                                loggable=True,
                            ) from exc
                        if can_retry:
                            await self._retry_wait(
                                context,
                                retry_index,
                                total_deadline=total_deadline,
                                retry_after_seconds=exc.retry_after_seconds,
                                jitter_key=(
                                    f"{execution_id}:{fallback_index}:"
                                    f"{retry_index}"
                                ),
                            )
                            continue
                        if can_fallback:
                            await asyncio.to_thread(
                                self._state.record_fallback_started,
                                account_id,
                                execution_id,
                            )
                            break
                    else:
                        if (
                            material.policy.require_reported_usage
                            and not result.usage.reported
                        ):
                            await asyncio.to_thread(
                                self._state.record_job_failure,
                                account_id,
                                execution_id,
                                job.id,
                                error_code=ErrorCode.AI_USAGE_UNAVAILABLE.value,
                                safe_summary="Provider 未返回验收所需用量",
                                failure_kind="error",
                                retryable=False,
                                provider_status_code=None,
                                provider_request_id_hash=(
                                    result.response_id_hash
                                ),
                                response_hash=result.response_hash,
                                duration_ms=result.duration_ms,
                                terminal=True,
                                terminal_error_code=(
                                    ErrorCode.AI_USAGE_UNAVAILABLE.value
                                ),
                            )
                            active_job_id = None
                            raise DomainError(
                                ErrorCode.AI_USAGE_UNAVAILABLE,
                                "Provider 未返回验收所需用量",
                                status_code=409,
                            )
                        try:
                            validated = validate_provider_output(
                                result.output_text,
                                material.rendered_prompt.output_schema,
                            )
                            output_id = f"aiout_{uuid4().hex}"
                            stored = self._content_store.store_output(
                                account_id,
                                execution_id,
                                output_id,
                                validated.text,
                            )
                        except DomainError as exc:
                            await asyncio.to_thread(
                                self._state.record_job_failure,
                                account_id,
                                execution_id,
                                job.id,
                                error_code=exc.error_code,
                                safe_summary=exc.message,
                                failure_kind="error",
                                retryable=False,
                                provider_status_code=None,
                                provider_request_id_hash=(
                                    result.response_id_hash
                                ),
                                response_hash=result.response_hash,
                                duration_ms=result.duration_ms,
                                terminal=True,
                                terminal_error_code=exc.error_code,
                            )
                            active_job_id = None
                            raise
                        try:
                            usage = result.usage
                            cost = actual_cost_micros(
                                runtime.cost_policy,
                                input_units=int(usage.input_units or 0),
                                output_units=int(usage.output_units or 0),
                            )
                            over_budget = await asyncio.to_thread(
                                self._state.complete_success,
                                account_id,
                                execution_id,
                                job.id,
                                candidate=candidate,
                                provider_result=result,
                                validated_output=validated,
                                stored_output=stored,
                                cost=cost,
                                commit_coordinator=(
                                    context.enable_commit_coordination()
                                ),
                            )
                        except BaseException:
                            self._content_store.remove_output(
                                account_id,
                                stored.reference,
                            )
                            raise
                        active_job_id = None
                        await context.report_progress(1.0)
                        if over_budget:
                            raise DomainError(
                                ErrorCode.AI_COST_LIMIT_EXCEEDED,
                                "Provider 实际用量超过本次预算上限",
                                status_code=409,
                            )
                        return
            raise DomainError(
                ErrorCode.AI_ALL_CANDIDATES_FAILED,
                "所有候选模型均未成功完成执行",
                status_code=502,
                loggable=True,
            )
        except asyncio.CancelledError:
            await asyncio.to_thread(
                self._state.complete_cancelled,
                account_id,
                execution_id,
                job_id=active_job_id,
            )
            raise
        except TaskCancellationRequested:
            await asyncio.to_thread(
                self._state.complete_cancelled,
                account_id,
                execution_id,
                job_id=active_job_id,
            )
            raise
        except DomainError as exc:
            await asyncio.to_thread(
                self._state.fail_without_job,
                account_id,
                execution_id,
                error_code=exc.error_code,
                safe_summary=exc.message,
                failure_kind=(
                    "result_unknown"
                    if exc.error_code
                    == ErrorCode.AI_PROVIDER_RESULT_UNKNOWN.value
                    else "error"
                ),
            )
            raise
        except Exception:
            log.exception(
                "AI 执行任务出现未处理异常",
                extra={
                    "account_id": account_id,
                    "resource_type": "ai_execution",
                    "resource_id": execution_id,
                },
            )
            await asyncio.to_thread(
                self._state.fail_without_job,
                account_id,
                execution_id,
                error_code=ErrorCode.INTERNAL_ERROR.value,
                safe_summary="AI 执行发生内部错误，请查看诊断日志后重试",
            )
            raise

    def _load_material(
        self,
        account_id: str,
        execution_id: str,
    ) -> FrozenExecutionMaterial:
        with self._unit_of_work.read() as transaction:
            return self._materials.load(
                transaction,
                account_id=account_id,
                execution_id=execution_id,
            )

    def _load_candidate(
        self,
        account_id: str,
        candidate: AIExecutionCandidate,
    ) -> FrozenCandidateRuntime:
        with self._unit_of_work.read() as transaction:
            if candidate.account_id != account_id:
                raise DomainError(
                    ErrorCode.ACCOUNT_SCOPE_MISMATCH,
                    "AI 候选不属于当前账号",
                    status_code=403,
                )
            return self._providers.load(transaction, candidate)

    async def _retry_wait(
        self,
        context: TaskExecutionContext,
        retry_index: int,
        *,
        total_deadline: float,
        retry_after_seconds: float | None,
        jitter_key: str,
    ) -> None:
        exponential_ms = min(
            self._retry_max_delay_ms,
            self._retry_base_delay_ms * (2**retry_index),
        )
        jitter_ms = round(exponential_ms * _retry_jitter(jitter_key))
        retry_after_ms = (
            0
            if retry_after_seconds is None
            else min(
                self._retry_max_delay_ms,
                max(0, round(retry_after_seconds * 1_000)),
            )
        )
        delay_ms = min(
            self._retry_max_delay_ms,
            max(jitter_ms, retry_after_ms),
        )
        remaining = delay_ms / 1_000
        while remaining > 0:
            context.raise_if_cancelled()
            total_remaining = total_deadline - time.monotonic()
            if total_remaining <= 0:
                raise DomainError(
                    ErrorCode.AI_PROVIDER_TIMEOUT,
                    "AI 执行已超过总时限",
                    status_code=504,
                )
            step = min(0.1, remaining, total_remaining)
            await asyncio.sleep(step)
            remaining -= step


def _retry_jitter(key: str) -> float:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    ratio = int.from_bytes(digest[:2], "big") / 65_535
    return 0.85 + ratio * 0.3


__all__ = ["AIExecutionExecutor"]
