from __future__ import annotations

from typing import Annotated

from fastapi import Path

from common.identifiers import STABLE_ID_PATTERN_TEXT

StablePathId = Annotated[
    str,
    Path(
        min_length=1,
        max_length=128,
        pattern=STABLE_ID_PATTERN_TEXT,
    ),
]
