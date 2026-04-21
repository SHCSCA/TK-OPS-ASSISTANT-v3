from __future__ import annotations

from fastapi import HTTPException


class RuntimeHTTPException(HTTPException):
    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        error_code: str,
        details: object | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.details = details
