from __future__ import annotations


def ok_response(data: object) -> dict[str, object]:
    return {"ok": True, "data": data}


def error_response(message: str) -> dict[str, object]:
    return {"ok": False, "error": message}
