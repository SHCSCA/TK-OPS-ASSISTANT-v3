from __future__ import annotations

from datetime import UTC, datetime

from common.time import utc_now, utc_now_iso


def test_utc_now_returns_timezone_aware_utc_datetime() -> None:
    now = utc_now()

    assert isinstance(now, datetime)
    assert now.tzinfo is UTC


def test_utc_now_iso_uses_z_suffix() -> None:
    value = utc_now_iso()

    assert value.endswith("Z")
    assert "+00:00" not in value
    assert datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
