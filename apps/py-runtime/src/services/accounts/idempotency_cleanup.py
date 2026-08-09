from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from services.accounts.unit_of_work import AccountUnitOfWork

log = logging.getLogger(__name__)
_DEFAULT_BATCH_SIZE = 500


@dataclass(frozen=True, slots=True)
class MutationIdempotencyCleanupReport:
    removed_record_count: int
    batch_count: int


class MutationIdempotencyReconciler:
    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        *,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError("幂等记录清理批次必须大于零")
        self._unit_of_work = unit_of_work
        self._batch_size = batch_size
        self._clock = clock or (lambda: datetime.now(UTC))

    def reconcile(self) -> MutationIdempotencyCleanupReport:
        now = _to_utc_text(self._clock())
        removed_total = 0
        batch_count = 0
        while True:
            with self._unit_of_work.write() as transaction:
                expired_ids = transaction.idempotency.list_expired_ids(
                    transaction.session,
                    now=now,
                    limit=self._batch_size,
                )
                if not expired_ids:
                    break
                removed = transaction.idempotency.delete_expired(
                    transaction.session,
                    now=now,
                    limit_ids=expired_ids,
                )
                if removed != len(expired_ids):
                    raise RuntimeError("普通写幂等过期记录清理结果不一致")
            removed_total += removed
            batch_count += 1

        report = MutationIdempotencyCleanupReport(
            removed_record_count=removed_total,
            batch_count=batch_count,
        )
        log.info(
            "普通写幂等过期记录清理完成",
            extra={
                "removed_record_count": report.removed_record_count,
                "batch_count": report.batch_count,
            },
        )
        return report


def _to_utc_text(value: datetime) -> str:
    normalized = (
        value.replace(tzinfo=UTC)
        if value.tzinfo is None
        else value.astimezone(UTC)
    )
    return normalized.isoformat(timespec="microseconds").replace(
        "+00:00",
        "Z",
    )
