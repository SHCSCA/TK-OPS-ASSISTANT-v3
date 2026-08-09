from __future__ import annotations

import json
import logging
import multiprocessing
import os
import sys
import threading
from uuid import uuid4

import uvicorn

from app.config import (
    RuntimeConfigurationError,
    load_runtime_bootstrap_config,
)
from app.factory import create_app
from app.logging import configure_logging, log_event, shutdown_logging
from app.version import RUNTIME_VERSION
from persistence.migration import RuntimeMigrationError

log = logging.getLogger(__name__)

LIFECYCLE_PREFIX = "TK_OPS_LIFECYCLE "
RUNTIME_PORT_ENV = "TK_OPS_RUNTIME_PORT"


def main() -> int:
    multiprocessing.freeze_support()
    if sys.argv[1:] == ["--version"]:
        print(_package_version(), flush=True)
        return 0

    logging_ready = _prepare_startup_logging()
    _emit_lifecycle(status="starting", stage="bootstrap")
    try:
        port = _load_port()
        application = create_app()
        _emit_lifecycle(status="starting", stage="http")
        server = uvicorn.Server(
            uvicorn.Config(
                application,
                access_log=False,
                host="127.0.0.1",
                log_config=None,
                port=port,
                server_header=False,
                workers=1,
            )
        )
        _start_shutdown_listener(server)
        server.run()
        _emit_lifecycle(status="stopped", stage="shutdown")
        return 0
    except KeyboardInterrupt:
        _emit_lifecycle(status="stopped", stage="shutdown")
        return 0
    except SystemExit as exc:
        return _handle_startup_failure(
            RuntimeError(f"HTTP 服务异常退出：{exc.code}"),
            logging_ready=logging_ready,
        )
    except Exception as exc:
        return _handle_startup_failure(exc, logging_ready=logging_ready)
    finally:
        shutdown_logging()


def _prepare_startup_logging() -> bool:
    try:
        bootstrap = load_runtime_bootstrap_config()
        configure_logging(bootstrap.data_dir / "logs")
        return True
    except Exception:
        return False


def _load_port() -> int:
    raw_port = os.getenv(RUNTIME_PORT_ENV, "").strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise RuntimeConfigurationError(
            "Runtime 动态端口配置无效"
        ) from exc
    if not 1 <= port <= 65_535:
        raise RuntimeConfigurationError("Runtime 动态端口超出允许范围")
    return port


def _handle_startup_failure(
    exc: BaseException,
    *,
    logging_ready: bool,
) -> int:
    error_code, message, inherited_log_id = _safe_error(exc)
    log_id = inherited_log_id or (
        f"log_{uuid4().hex}" if logging_ready else None
    )
    if logging_ready:
        log.exception(
            "Runtime sidecar 启动失败",
            extra={
                "error_code": error_code,
                "log_id": log_id,
                "stage": "startup",
            },
        )
        log_event(
            "system",
            "runtime.startup.failed",
            error_code=error_code,
            log_id=log_id,
            stage="startup",
        )
    _emit_lifecycle(
        status="failed",
        stage="startup",
        error_code=error_code,
        log_id=log_id,
        message=message,
    )
    return 1


def _safe_error(
    exc: BaseException,
) -> tuple[str, str, str | None]:
    if isinstance(exc, RuntimeMigrationError):
        return exc.error_code, str(exc), exc.log_id
    if isinstance(exc, RuntimeConfigurationError):
        return (
            "RUNTIME_CONFIGURATION_INVALID",
            "Runtime 启动配置无效，请重新启动桌面应用。",
            None,
        )
    return (
        "RUNTIME_STARTUP_FAILED",
        "Runtime 启动失败，请通过关联日志诊断。",
        None,
    )


def _emit_lifecycle(
    *,
    status: str,
    stage: str,
    error_code: str | None = None,
    log_id: str | None = None,
    message: str | None = None,
) -> None:
    payload = {
        "kind": "runtime_lifecycle",
        "status": status,
        "stage": stage,
        "errorCode": error_code,
        "logId": log_id,
        "message": message,
    }
    print(
        f"{LIFECYCLE_PREFIX}{json.dumps(payload, ensure_ascii=True)}",
        flush=True,
    )


def _start_shutdown_listener(server: uvicorn.Server) -> None:
    if os.getenv("TK_OPS_RUNTIME_MANAGED_SIDECAR", "").strip() != "1":
        return

    def listen() -> None:
        try:
            command = sys.stdin.readline()
            if command == "" or command.strip().lower() == "shutdown":
                _emit_lifecycle(status="stopping", stage="shutdown")
                server.should_exit = True
        except Exception:
            log.exception("Runtime sidecar 停机通道异常")
            server.should_exit = True

    threading.Thread(
        target=listen,
        name="runtime-sidecar-shutdown",
        daemon=True,
    ).start()


def _package_version() -> str:
    return os.getenv("TK_OPS_RUNTIME_VERSION", "").strip() or RUNTIME_VERSION


if __name__ == "__main__":
    raise SystemExit(main())
