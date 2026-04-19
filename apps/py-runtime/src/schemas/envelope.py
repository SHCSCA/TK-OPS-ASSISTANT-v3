from __future__ import annotations


def ok_response(data: object) -> dict[str, object]:
    return {"ok": True, "data": data}


def error_response(
    message: str,
    *,
    request_id: str | None = None,
    details: object | None = None,
    error_code: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"ok": False, "error": message}
    if error_code is not None:
        payload["error_code"] = error_code
    if request_id:
        payload["requestId"] = request_id
    if details is not None:
        payload["details"] = details
    return payload
