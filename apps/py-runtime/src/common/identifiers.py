from __future__ import annotations

import re

STABLE_ID_PATTERN_TEXT = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
STABLE_ID_PATTERN = re.compile(STABLE_ID_PATTERN_TEXT)


def is_stable_id(value: object) -> bool:
    return isinstance(value, str) and STABLE_ID_PATTERN.fullmatch(value) is not None
