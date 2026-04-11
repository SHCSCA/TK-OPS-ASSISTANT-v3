from __future__ import annotations

from datetime import UTC, datetime

from app.config import RuntimeConfig


def build_health_payload(runtime_config: RuntimeConfig) -> dict[str, str]:
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return {
        "service": "online",
        "version": runtime_config.version,
        "now": now,
        "mode": runtime_config.mode,
    }
