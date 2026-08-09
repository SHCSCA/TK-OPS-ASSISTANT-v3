from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from errors import DomainError, ErrorCode
from services.accounts.idempotency import (
    MutationCommand,
    MutationIdempotencyService,
)

from .unit_of_work import (
    AIConfigurationTransaction,
    AIConfigurationUnitOfWork,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AIResourceMutation:
    data: Mapping[str, object]
    resource_type: str
    resource_id: str
    revision: int | None
    invalidations: tuple[str, ...]
    replay_snapshot_safe: bool = False


class AIConfigurationMutationExecutor:
    """仅把安全资源引用写入幂等表，重放时重新读取完整资源。"""

    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        idempotency_service: MutationIdempotencyService,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._idempotency = idempotency_service

    def execute(
        self,
        command: MutationCommand,
        *,
        work: Callable[
            [AIConfigurationTransaction],
            AIResourceMutation,
        ],
        replay_loader: Callable[
            [AIConfigurationTransaction, str, str],
            Mapping[str, object],
        ],
    ) -> AIResourceMutation:
        try:
            with self._unit_of_work.write() as transaction:
                replay = self._idempotency.find_replay(
                    transaction.session,
                    command,
                )
                if replay is not None:
                    resource_type, resource_id, replay_revision = (
                        _replay_reference(replay.response)
                    )
                    data = _load_replay_data(
                        replay.response,
                        fallback=lambda: replay_loader(
                            transaction,
                            resource_type,
                            resource_id,
                        ),
                    )
                    return AIResourceMutation(
                        data=data,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        revision=(
                            replay_revision
                            if replay_revision is not None
                            else _optional_int(data.get("revision"))
                        ),
                        invalidations=(),
                        replay_snapshot_safe=(
                            isinstance(
                                replay.response.get("replayData"),
                                Mapping,
                            )
                        ),
                    )
                result = work(transaction)
                stored_response: dict[str, object] = {
                    "resourceType": result.resource_type,
                    "resourceId": result.resource_id,
                    "revision": result.revision,
                }
                if result.replay_snapshot_safe:
                    stored_response["replayData"] = dict(result.data)
                self._idempotency.store(
                    transaction.session,
                    command,
                    response=stored_response,
                    resource_type=result.resource_type,
                    resource_id=result.resource_id,
                )
                return result
        except IntegrityError as exc:
            replayed = self._resolve_race(
                command,
                replay_loader=replay_loader,
            )
            if replayed is not None:
                return replayed
            log.exception("AI 配置写入发生无法归因的完整性冲突")
            raise DomainError(
                ErrorCode.REQUEST_CONFLICT,
                "AI 配置写入冲突，请刷新后重试",
                status_code=409,
                loggable=True,
            ) from exc

    def _resolve_race(
        self,
        command: MutationCommand,
        *,
        replay_loader: Callable[
            [AIConfigurationTransaction, str, str],
            Mapping[str, object],
        ],
    ) -> AIResourceMutation | None:
        with self._unit_of_work.read() as transaction:
            replay = self._idempotency.find_replay(
                transaction.session,
                command,
            )
            if replay is None:
                return None
            resource_type, resource_id, replay_revision = _replay_reference(
                replay.response
            )
            data = _load_replay_data(
                replay.response,
                fallback=lambda: replay_loader(
                    transaction,
                    resource_type,
                    resource_id,
                ),
            )
            return AIResourceMutation(
                data=data,
                resource_type=resource_type,
                resource_id=resource_id,
                revision=(
                    replay_revision
                    if replay_revision is not None
                    else _optional_int(data.get("revision"))
                ),
                invalidations=(),
                replay_snapshot_safe=(
                    isinstance(
                        replay.response.get("replayData"),
                        Mapping,
                    )
                ),
            )


def _replay_reference(
    response: Mapping[str, object],
) -> tuple[str, str, int | None]:
    resource_type = response.get("resourceType")
    resource_id = response.get("resourceId")
    if (
        not isinstance(resource_type, str)
        or not resource_type
        or not isinstance(resource_id, str)
        or not resource_id
    ):
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "AI 配置幂等记录异常，请查看诊断日志",
            status_code=500,
            loggable=True,
        )
    return resource_type, resource_id, _optional_int(
        response.get("revision")
    )


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _load_replay_data(
    response: Mapping[str, object],
    *,
    fallback: Callable[[], Mapping[str, object]],
) -> Mapping[str, object]:
    replay_data = response.get("replayData")
    if isinstance(replay_data, Mapping):
        return dict(replay_data)
    return fallback()
