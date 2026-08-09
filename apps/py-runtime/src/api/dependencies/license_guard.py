from __future__ import annotations

import logging
from typing import Protocol

from fastapi import Depends, Request

from api.dependencies.request_context import RequestContext, get_request_context
from app.logging import log_event
from errors import DomainError, ErrorCode
from schemas.v1.bootstrap import LicenseStatusDto

log = logging.getLogger(__name__)


class LicenseStatusProvider(Protocol):
    def get_license_status(
        self,
        *,
        request_id: str,
        operation_id: str,
    ) -> LicenseStatusDto: ...


def require_active_license(
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> LicenseStatusDto:
    """仅允许实时许可证状态为 active 的请求继续执行。"""

    provider = _resolve_license_status_provider(request)
    try:
        status = provider.get_license_status(
            request_id=context.request_id,
            operation_id=context.operation_id,
        )
    except DomainError:
        raise
    except Exception as exc:
        log.exception("读取 v1 许可证状态失败")
        raise DomainError(
            ErrorCode.LICENSE_STORE_UNAVAILABLE,
            "许可证安全存储不可用",
            status_code=503,
            loggable=True,
            log_context={"operation": "license.guard"},
        ) from exc

    if status.status == "active":
        return status

    error_code = (
        ErrorCode.LICENSE_MACHINE_MISMATCH
        if status.status == "machine_mismatch"
        else ErrorCode.LICENSE_INVALID
    )
    log_event(
        "security",
        "runtime.license_rejected",
        level=logging.WARNING,
        request_id=context.request_id,
        operation_id=context.operation_id,
        error_code=str(error_code),
        context={"licenseStatus": status.status},
    )
    raise DomainError(
        error_code,
        "许可证与本机不匹配"
        if status.status == "machine_mismatch"
        else "许可证无效，请先完成激活",
        status_code=403,
        log_context={"licenseStatus": status.status},
    )


def _resolve_license_status_provider(request: Request) -> LicenseStatusProvider:
    direct_provider = getattr(request.app.state, "bootstrap_v1_service", None)
    if direct_provider is not None:
        return direct_provider  # type: ignore[no-any-return]

    container = getattr(request.app.state, "runtime_container", None)
    services = getattr(container, "services", None)
    container_provider = getattr(services, "bootstrap_v1", None)
    if container_provider is not None:
        return container_provider  # type: ignore[no-any-return]

    log.error("v1 Bootstrap 服务未装配，许可证门已关闭")
    raise DomainError(
        ErrorCode.LICENSE_STORE_UNAVAILABLE,
        "许可证安全存储不可用",
        status_code=503,
        loggable=True,
        log_context={"operation": "license.guard", "serviceMissing": True},
    )
