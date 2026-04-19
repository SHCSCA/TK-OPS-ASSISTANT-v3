from __future__ import annotations

from fastapi import HTTPException


class ProviderHTTPException(HTTPException):
    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        error_code: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
