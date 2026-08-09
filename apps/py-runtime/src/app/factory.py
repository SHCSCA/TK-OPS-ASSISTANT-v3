from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from api.dependencies.request_context import install_request_context_middleware
from app.config import (
    RuntimeConfig,
    is_production_mode,
    load_runtime_bootstrap_config,
    load_runtime_config,
)
from app.container import (
    RuntimeContainer,
    RuntimeDependencyOverrides,
    build_runtime_container,
)
from app.container_state import attach_container_state
from app.exception_handlers import install_exception_handlers
from app.lifecycle import prepare_runtime_database
from app.logging import configure_logging, log_event
from app.pre_write_startup_recovery import (
    PreWriteStartupRecoveryCoordinator,
    PreWriteStartupRecoveryError,
)
from app.route_registry import register_routes
from app.runtime_background import RuntimeBackgroundServices
from app.security_middleware import install_v1_security_middleware
from app.secret_store import SecretStore, build_secret_store
from app.shutdown_deadline import ShutdownDeadline, wait_task_until
from app.write_gate import (
    RuntimeWriteGate,
    RuntimeWriteGateState,
    install_runtime_write_gate_middleware,
)
from persistence.engine import create_runtime_engine
from persistence.migration import MigrationReport
from persistence.migration.compatibility import (
    write_runtime_compatibility_evidence,
)
from persistence.migration.cutover import DurableCutoverJournal

log = logging.getLogger(__name__)


def create_app(
    *,
    dependency_overrides: RuntimeDependencyOverrides | None = None,
) -> FastAPI:
    bootstrap_config = load_runtime_bootstrap_config()
    configure_logging(bootstrap_config.data_dir / "logs")
    runtime_config = load_runtime_config(bootstrap_config)
    migration_report = prepare_runtime_database(runtime_config)
    startup_recovery = PreWriteStartupRecoveryCoordinator(
        database_path=runtime_config.database_path,
        migration_report=migration_report,
    )
    engine: Engine | None = None
    failure_stage = "secret_store"

    try:
        secret_store = build_secret_store(runtime_config)
        failure_stage = "database_engine"
        engine = create_runtime_engine(runtime_config.database_path)
        failure_stage = "runtime_container"
        return _build_runtime_app(
            runtime_config=runtime_config,
            migration_report=migration_report,
            secret_store=secret_store,
            engine=engine,
            startup_recovery=startup_recovery,
            dependency_overrides=dependency_overrides,
        )
    except PreWriteStartupRecoveryError:
        raise
    except Exception as exc:
        startup_recovery.recover_sync(
            exc,
            engine=engine,
            failure_stage=failure_stage,
        )
        raise


def _build_runtime_app(
    *,
    runtime_config: RuntimeConfig,
    migration_report: MigrationReport,
    secret_store: SecretStore,
    engine: Engine,
    startup_recovery: PreWriteStartupRecoveryCoordinator,
    dependency_overrides: RuntimeDependencyOverrides | None = None,
) -> FastAPI:
    container = build_runtime_container(
        runtime_config=runtime_config,
        migration_report=migration_report,
        secret_store=secret_store,
        engine=engine,
        dependency_overrides=dependency_overrides,
    )
    background_services = RuntimeBackgroundServices(container.kernel)
    write_gate = _build_runtime_write_gate(
        runtime_config=runtime_config,
        migration_report=migration_report,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        provider_health_handle: asyncio.Task[None] | None = None
        write_gate_opened = False
        startup_failure_handled = False
        try:
            await background_services.start()
            write_gate.open()
            write_gate_opened = True
            log_event(
                "system",
                "runtime.started",
                context={
                    "mode": container.current_settings.runtime.mode,
                    "schemaRevision": migration_report.target_revision,
                    "databaseReady": runtime_config.database_path.is_file(),
                },
            )
            if runtime_config.mode != "test":
                provider_health_handle = asyncio.create_task(
                    _refresh_provider_health(
                        container,
                        blocking_cancel_grace_seconds=min(
                            1.0,
                            container.kernel.policy.shutdown_grace_seconds,
                        ),
                    ),
                    name="runtime-provider-health-refresh",
                )
            yield
        except BaseException as exc:
            write_gate.fail_closed("Runtime 启动未完成，写入保持关闭")
            if not write_gate_opened:
                startup_failure_handled = True
                await startup_recovery.recover_async(
                    exc,
                    background_services=background_services,
                    engine=engine,
                    failure_stage="background_start",
                )
            raise
        finally:
            if not startup_failure_handled:
                await _shutdown_runtime_services(
                    container=container,
                    background_services=background_services,
                    write_gate=write_gate,
                    engine=engine,
                    provider_health_handle=provider_health_handle,
                )

    app = FastAPI(
        title="TK-OPS Runtime",
        summary="TK-OPS 账号级 AI 内容生产 Runtime",
        version=runtime_config.version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(runtime_config.allowed_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "If-Match",
            "X-Operation-ID",
        ],
        expose_headers=["X-Request-ID", "X-Operation-ID"],
    )
    attach_container_state(app, container)
    app.state.runtime_write_gate = write_gate
    install_runtime_write_gate_middleware(app, write_gate)
    install_v1_security_middleware(app)
    install_request_context_middleware(app)
    install_exception_handlers(app)
    register_routes(app, container)

    return app


async def _shutdown_runtime_services(
    *,
    container: RuntimeContainer,
    background_services: RuntimeBackgroundServices,
    write_gate: RuntimeWriteGate,
    engine: Engine,
    provider_health_handle: asyncio.Task[None] | None,
) -> None:
    if (
        write_gate.snapshot().state
        is not RuntimeWriteGateState.FAILED_CLOSED
    ):
        write_gate.close_for_shutdown()
    shutdown_deadline = ShutdownDeadline.start(
        container.kernel.policy.shutdown_grace_seconds
    )
    cancelled_error: asyncio.CancelledError | None = None
    try:
        if provider_health_handle is not None:
            provider_budget = min(
                1.0,
                shutdown_deadline.remaining_seconds() * 0.15,
            )
            try:
                await _stop_provider_health(
                    provider_health_handle,
                    deadline=shutdown_deadline.capped(provider_budget),
                )
            except asyncio.CancelledError as exc:
                cancelled_error = exc
                log.warning(
                    "Runtime 停机等待 Provider 健康刷新时收到取消请求"
                )
        try:
            await background_services.shutdown(deadline=shutdown_deadline)
        except asyncio.CancelledError as exc:
            cancelled_error = cancelled_error or exc
            log.warning(
                "Runtime 后台服务停机时收到取消请求，持久状态将在下次恢复"
            )
            try:
                await background_services.shutdown(deadline=shutdown_deadline)
            except asyncio.CancelledError:
                log.warning(
                    "Runtime 后台服务停机再次被取消，不再阻塞进程退出"
                )
            except Exception:
                log.exception("Runtime 后台服务取消后再次停机失败")
    finally:
        _dispose_runtime_engine(engine)
    if cancelled_error is not None:
        raise cancelled_error


def _build_runtime_write_gate(
    *,
    runtime_config: RuntimeConfig,
    migration_report: MigrationReport,
) -> RuntimeWriteGate:
    cutover_event_id = migration_report.cutover_event_id
    journal_path = migration_report.cutover_journal_path
    if not cutover_event_id or not journal_path:
        raise RuntimeError("Runtime 迁移报告缺少 cutover 写门证据")
    journal = DurableCutoverJournal(Path(journal_path))

    compatibility_path = (
        Path(migration_report.compatibility_evidence_path)
        if migration_report.compatibility_evidence_path
        else runtime_config.migration.compatibility_evidence_path
    )
    if compatibility_path is None:
        raise RuntimeError("Runtime 迁移配置缺少 Schema 兼容证据路径")
    compatibility = write_runtime_compatibility_evidence(
        compatibility_path,
        runtime_version=runtime_config.version,
        migration_log_id=migration_report.log_id,
        cutover_event_id=cutover_event_id,
        database_fingerprint=migration_report.post_migration_fingerprint,
        target_revision=migration_report.target_revision,
        minimum_revision=migration_report.schema_read_min_revision,
        require_artifact_build_id=(
            runtime_config.managed_sidecar
            and is_production_mode(runtime_config.mode)
        ),
    )
    journal.append(
        cutover_event_id=cutover_event_id,
        log_id=migration_report.log_id,
        stage="compatibility_evidence_written",
        evidence={
            "sha256": compatibility.sha256,
            "artifactBuildId": compatibility.artifact_build_id,
            "rollbackEligible": compatibility.rollback_eligible,
            **compatibility.schema_range.to_dict(),
        },
    )

    def write_transition(
        stage: str,
        evidence: Mapping[str, object],
    ) -> None:
        journal.append(
            cutover_event_id=cutover_event_id,
            log_id=migration_report.log_id,
            stage=stage,
            evidence=dict(evidence),
        )

    return RuntimeWriteGate(
        cutover_event_id=cutover_event_id,
        transition_writer=write_transition,
    )


async def _refresh_provider_health(
    container: RuntimeContainer,
    *,
    blocking_cancel_grace_seconds: float,
) -> None:
    handle = asyncio.create_task(
        asyncio.to_thread(
            container.services.ai_capability.refresh_provider_health,
        ),
        name="runtime-provider-health-worker",
    )
    try:
        await asyncio.shield(handle)
    except asyncio.CancelledError:
        try:
            completed, _ = await asyncio.wait(
                {handle},
                timeout=blocking_cancel_grace_seconds,
            )
        except asyncio.CancelledError:
            handle.add_done_callback(_consume_provider_health_result)
            raise
        if completed:
            _consume_provider_health_result(handle)
        else:
            log.warning(
                "AI Provider 健康刷新未在停机宽限期内收尾，将由后台线程完成",
                extra={
                    "grace_seconds": blocking_cancel_grace_seconds,
                },
            )
            handle.add_done_callback(_consume_provider_health_result)
        raise
    except Exception:
        log.exception("启动后刷新 AI Provider 健康快照失败")


async def _stop_provider_health(
    handle: asyncio.Task[None],
    *,
    deadline: ShutdownDeadline,
) -> None:
    if not handle.done():
        handle.cancel()
    completed = await wait_task_until(handle, deadline)
    if not completed:
        log.warning("Runtime 停机不再等待 AI Provider 健康刷新")
        handle.add_done_callback(_consume_provider_health_result)
        return
    _consume_provider_health_result(handle)


def _consume_provider_health_result(handle: asyncio.Task[object]) -> None:
    if handle.cancelled():
        return
    try:
        error = handle.exception()
    except Exception:
        log.exception("读取 AI Provider 健康刷新后台结果失败")
        return
    if error is not None:
        log.error(
            "AI Provider 健康刷新后台任务失败",
            exc_info=(type(error), error, error.__traceback__),
        )


def _dispose_runtime_engine(engine: Engine) -> None:
    try:
        engine.dispose()
    except Exception:
        log.exception("Runtime 停机释放数据库引擎失败")
