from __future__ import annotations

from sqlalchemy.orm import Session

from services.config.config_bus import ConfigBusSnapshot
from services.events import RuntimeEventDraft, RuntimeEventService


def write_config_updated_event(
    session: Session,
    snapshot: ConfigBusSnapshot,
    changed_keys: tuple[str, ...],
    event_service_ref: list[RuntimeEventService],
) -> None:
    if not event_service_ref:
        raise RuntimeError("Runtime 事件服务尚未完成装配")
    event_service_ref[0].append(
        session,
        RuntimeEventDraft(
            event_type="config.changed",
            topic="system:config",
            revision=snapshot.revision,
            payload={
                "changedKeys": list(changed_keys),
                "invalidations": ["system-config"],
            },
        ),
    )
