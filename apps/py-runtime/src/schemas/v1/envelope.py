from __future__ import annotations

from collections.abc import Mapping, Sequence

from errors import FieldError


def ok_response(
    data: object,
    *,
    meta: Mapping[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"ok": True, "data": data}
    if meta is not None:
        payload["meta"] = dict(meta)
    return payload


def error_response(
    message: str,
    *,
    error_code: str,
    log_id: str | None = None,
    field_errors: Sequence[FieldError | Mapping[str, str]] | None = None,
    meta: Mapping[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "ok": False,
        "error": message,
        "error_code": error_code,
    }
    if log_id is not None:
        payload["log_id"] = log_id
    if field_errors:
        payload["fieldErrors"] = [
            item.to_dict() if isinstance(item, FieldError) else dict(item)
            for item in field_errors
        ]
    if meta is not None:
        payload["meta"] = dict(meta)
    return payload
