from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from errors.codes import ErrorCode


@dataclass(frozen=True, slots=True)
class FieldError:
    field: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "code": self.code,
            "message": self.message,
        }


class DomainError(Exception):
    def __init__(
        self,
        error_code: ErrorCode | str,
        message: str,
        *,
        status_code: int,
        field_errors: Sequence[FieldError] | None = None,
        meta: Mapping[str, object] | None = None,
        loggable: bool = False,
        headers: Mapping[str, str] | None = None,
        log_context: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = str(error_code)
        self.message = message
        self.status_code = status_code
        self.field_errors = tuple(field_errors or ())
        self.meta = dict(meta or {})
        self.loggable = loggable
        self.headers = dict(headers or {})
        self.log_context = dict(log_context or {})
