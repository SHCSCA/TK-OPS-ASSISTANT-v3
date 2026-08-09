from __future__ import annotations

from typing import NoReturn

from fastapi import Request

from api.routes.legacy.access import (
    legacy_write_unsupported,
    record_legacy_api_use,
)


def reject_legacy_ai_write(
    request: Request,
    *,
    replacement: str,
) -> NoReturn:
    """拒绝会覆盖旧 AI 配置的危险写入。"""

    record_legacy_api_use(request, replacement=replacement)
    legacy_write_unsupported(replacement=replacement)


__all__ = ["reject_legacy_ai_write"]
