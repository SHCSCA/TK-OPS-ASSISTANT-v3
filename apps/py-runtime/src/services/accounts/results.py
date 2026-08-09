from __future__ import annotations

from dataclasses import dataclass

from errors import DomainError, ErrorCode
from services.accounts.unit_of_work import MutationExecution


@dataclass(frozen=True, slots=True)
class AccountServiceResponse:
    data: dict[str, object]
    meta: dict[str, object]

    def to_storage(self) -> dict[str, object]:
        return {
            "data": self.data,
            "meta": self.meta,
        }

    @classmethod
    def from_mutation(
        cls,
        execution: MutationExecution,
    ) -> AccountServiceResponse:
        data = execution.response.get("data")
        meta = execution.response.get("meta")
        if not isinstance(data, dict) or not isinstance(meta, dict):
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "幂等业务响应结构异常，请查看诊断日志",
                status_code=500,
                loggable=True,
            )
        normalized_meta = dict(meta)
        normalized_meta["idempotentReplay"] = execution.replayed
        return cls(data=dict(data), meta=normalized_meta)
