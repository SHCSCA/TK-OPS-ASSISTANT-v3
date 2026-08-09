from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header

from errors import DomainError, ErrorCode, FieldError

_IF_MATCH_PATTERN = re.compile(r'^(?:"([1-9][0-9]*)"|([1-9][0-9]*))$')
_IF_MATCH_ALLOW_ZERO_PATTERN = re.compile(
    r'^(?:"(0|[1-9][0-9]*)"|(0|[1-9][0-9]*))$'
)


@dataclass(frozen=True, slots=True)
class ExpectedRevision:
    value: int


def get_expected_revision(
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> ExpectedRevision:
    if if_match is None:
        raise DomainError(
            ErrorCode.REVISION_CONFLICT,
            "缺少资源修订号，请重新加载后再试",
            status_code=412,
        )
    match = _IF_MATCH_PATTERN.fullmatch(if_match)
    if match is None:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "资源修订号格式无效",
            status_code=422,
            field_errors=[
                FieldError(
                    field="If-Match",
                    code="invalid_revision",
                    message='必须为正整数或带双引号的正整数，例如 "3"',
                )
            ],
        )
    return ExpectedRevision(value=int(match.group(1) or match.group(2)))


def get_expected_revision_allow_zero(
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> ExpectedRevision:
    if if_match is None:
        raise DomainError(
            ErrorCode.REVISION_CONFLICT,
            "缺少资源修订号，请重新加载后再试",
            status_code=412,
        )
    match = _IF_MATCH_ALLOW_ZERO_PATTERN.fullmatch(if_match)
    if match is None:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "资源修订号格式无效",
            status_code=422,
            field_errors=[
                FieldError(
                    field="If-Match",
                    code="invalid_revision",
                    message='必须为非负整数或带双引号的非负整数，例如 "0"',
                )
            ],
        )
    return ExpectedRevision(value=int(match.group(1) or match.group(2)))
