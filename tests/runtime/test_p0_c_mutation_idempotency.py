from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from domain import models as domain_models
from domain.models.mutation_idempotency import RuntimeMutationIdempotency
from errors import DomainError, ErrorCode
from repositories.mutation_idempotency_repository import (
    MutationIdempotencyRepository,
)
from services.accounts.idempotency import (
    MutationCommand,
    MutationIdempotencyService,
)
from services.accounts.idempotency_cleanup import (
    MutationIdempotencyReconciler,
)
from services.accounts.unit_of_work import AccountUnitOfWork


def test_expired_mutation_key_is_removed_and_can_be_reused() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    domain_models.Base.metadata.create_all(engine)
    repository = MutationIdempotencyRepository()
    command = _command(payload={"name": "旧请求"})
    old_service = MutationIdempotencyService(
        repository,
        retention_seconds=3_600,
        clock=lambda: datetime(2026, 7, 26, 8, tzinfo=UTC),
    )
    new_service = MutationIdempotencyService(
        repository,
        retention_seconds=3_600,
        clock=lambda: datetime(2026, 7, 26, 10, tzinfo=UTC),
    )

    try:
        with Session(engine) as session:
            old_service.store(
                session,
                command,
                response={"data": {"accountId": "account-old"}},
            )
            session.commit()

        replacement = _command(payload={"name": "新请求"})
        with Session(engine) as session:
            assert new_service.find_replay(session, replacement) is None
            new_service.store(
                session,
                replacement,
                response={"data": {"accountId": "account-new"}},
            )
            session.commit()

        with Session(engine) as session:
            rows = session.scalars(
                select(RuntimeMutationIdempotency)
            ).all()
            assert len(rows) == 1
            assert '"account-new"' in rows[0].response_json
            assert (
                rows[0].created_at
                == "2026-07-26T10:00:00.000000Z"
            )
    finally:
        engine.dispose()


def test_live_mutation_key_rejects_different_request() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    domain_models.Base.metadata.create_all(engine)
    repository = MutationIdempotencyRepository()
    service = MutationIdempotencyService(
        repository,
        retention_seconds=3_600,
        clock=lambda: datetime(2026, 7, 26, 8, tzinfo=UTC),
    )

    try:
        with Session(engine) as session:
            service.store(
                session,
                _command(payload={"name": "请求一"}),
                response={"data": {"accountId": "account-one"}},
            )
            session.commit()

        with Session(engine) as session:
            with pytest.raises(DomainError) as caught:
                service.find_replay(
                    session,
                    _command(payload={"name": "请求二"}),
                )
        assert caught.value.error_code == ErrorCode.REQUEST_CONFLICT.value
    finally:
        engine.dispose()


def test_startup_reconciler_removes_all_expired_batches_only() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    domain_models.Base.metadata.create_all(engine)
    repository = MutationIdempotencyRepository()
    expired_service = MutationIdempotencyService(
        repository,
        retention_seconds=3_600,
        clock=lambda: datetime(2026, 7, 26, 8, tzinfo=UTC),
    )
    live_service = MutationIdempotencyService(
        repository,
        retention_seconds=3_600,
        clock=lambda: datetime(2026, 7, 26, 9, 30, tzinfo=UTC),
    )

    try:
        with Session(engine) as database:
            for index in range(3):
                expired_service.store(
                    database,
                    _command(
                        payload={"index": index},
                        idempotency_key=f"idem-expired-{index}",
                    ),
                    response={"data": {"index": index}},
                )
            live_service.store(
                database,
                _command(
                    payload={"index": "live"},
                    idempotency_key="idem-live",
                ),
                response={"data": {"index": "live"}},
            )
            database.commit()

        unit_of_work = AccountUnitOfWork(
            sessionmaker(bind=engine),
            event_service=Mock(),
            idempotency_repository=repository,
        )
        report = MutationIdempotencyReconciler(
            unit_of_work,
            batch_size=2,
            clock=lambda: datetime(2026, 7, 26, 10, tzinfo=UTC),
        ).reconcile()

        assert report.removed_record_count == 3
        assert report.batch_count == 2
        with Session(engine) as database:
            rows = database.scalars(
                select(RuntimeMutationIdempotency)
            ).all()
            assert len(rows) == 1
            assert (
                rows[0].expires_at
                == "2026-07-26T10:30:00.000000Z"
            )
            assert '"live"' in rows[0].response_json
    finally:
        engine.dispose()


def _command(
    *,
    payload: dict[str, object],
    idempotency_key: str = "idem-account-create",
) -> MutationCommand:
    return MutationCommand(
        account_id=None,
        operation_name="account.create",
        idempotency_key=idempotency_key,
        request_payload=payload,
    )
