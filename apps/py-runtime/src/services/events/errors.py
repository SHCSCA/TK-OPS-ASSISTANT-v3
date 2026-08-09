from __future__ import annotations

from errors import DomainError, ErrorCode


class RuntimeEventError(DomainError):
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        *,
        status_code: int,
    ) -> None:
        super().__init__(
            error_code,
            message,
            status_code=status_code,
        )


class EventValidationError(RuntimeEventError):
    def __init__(self, message: str) -> None:
        super().__init__(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            message,
            status_code=422,
        )


class AccountScopeMismatchError(RuntimeEventError):
    def __init__(self, message: str = "事件订阅与账号范围不匹配。") -> None:
        super().__init__(
            ErrorCode.ACCOUNT_SCOPE_MISMATCH,
            message,
            status_code=403,
        )


class CursorMismatchError(RuntimeEventError):
    def __init__(self, message: str = "事件游标与 Topic 不一致。") -> None:
        super().__init__(
            ErrorCode.WS_CURSOR_MISMATCH,
            message,
            status_code=409,
        )
