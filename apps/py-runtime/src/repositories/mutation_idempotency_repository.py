from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from domain.models.mutation_idempotency import RuntimeMutationIdempotency


@dataclass(frozen=True, slots=True)
class MutationIdempotencyRecord:
    id: str
    scope: str
    account_id: str | None
    operation_name: str
    idempotency_key_hash: str
    request_hash: str
    response_json: str
    resource_type: str | None
    resource_id: str | None
    created_at: str
    expires_at: str


class MutationIdempotencyRepository:
    def get_system(
        self,
        session: Session,
        *,
        operation_name: str,
        idempotency_key_hash: str,
    ) -> MutationIdempotencyRecord | None:
        row = session.scalars(
            select(RuntimeMutationIdempotency).where(
                RuntimeMutationIdempotency.scope == "system",
                RuntimeMutationIdempotency.account_id.is_(None),
                RuntimeMutationIdempotency.operation_name == operation_name,
                RuntimeMutationIdempotency.idempotency_key_hash
                == idempotency_key_hash,
            )
        ).one_or_none()
        return None if row is None else self.to_record(row)

    def get_account(
        self,
        session: Session,
        *,
        account_id: str,
        operation_name: str,
        idempotency_key_hash: str,
    ) -> MutationIdempotencyRecord | None:
        row = session.scalars(
            select(RuntimeMutationIdempotency).where(
                RuntimeMutationIdempotency.scope == "account",
                RuntimeMutationIdempotency.account_id == account_id,
                RuntimeMutationIdempotency.operation_name == operation_name,
                RuntimeMutationIdempotency.idempotency_key_hash
                == idempotency_key_hash,
            )
        ).one_or_none()
        return None if row is None else self.to_record(row)

    def add(
        self,
        session: Session,
        row: RuntimeMutationIdempotency,
    ) -> MutationIdempotencyRecord:
        session.add(row)
        session.flush()
        return self.to_record(row)

    def delete_expired_record(
        self,
        session: Session,
        *,
        record_id: str,
        now: str,
    ) -> bool:
        result = session.execute(
            delete(RuntimeMutationIdempotency).where(
                RuntimeMutationIdempotency.id == record_id,
                RuntimeMutationIdempotency.expires_at <= now,
            )
        )
        session.flush()
        return int(result.rowcount or 0) == 1

    def delete_expired(
        self,
        session: Session,
        *,
        now: str,
        limit_ids: tuple[str, ...],
    ) -> int:
        if not limit_ids:
            return 0
        result = session.execute(
            delete(RuntimeMutationIdempotency).where(
                RuntimeMutationIdempotency.id.in_(limit_ids),
                RuntimeMutationIdempotency.expires_at <= now,
            )
        )
        return int(result.rowcount or 0)

    def list_expired_ids(
        self,
        session: Session,
        *,
        now: str,
        limit: int,
    ) -> tuple[str, ...]:
        return tuple(
            session.scalars(
                select(RuntimeMutationIdempotency.id)
                .where(RuntimeMutationIdempotency.expires_at <= now)
                .order_by(RuntimeMutationIdempotency.expires_at.asc())
                .limit(limit)
            ).all()
        )

    @staticmethod
    def to_record(
        row: RuntimeMutationIdempotency,
    ) -> MutationIdempotencyRecord:
        return MutationIdempotencyRecord(
            id=row.id,
            scope=row.scope,
            account_id=row.account_id,
            operation_name=row.operation_name,
            idempotency_key_hash=row.idempotency_key_hash,
            request_hash=row.request_hash,
            response_json=row.response_json,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            created_at=row.created_at,
            expires_at=row.expires_at,
        )
