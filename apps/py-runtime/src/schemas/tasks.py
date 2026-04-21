from __future__ import annotations

from enum import StrEnum


class TaskStatus(StrEnum):
    DRAFT = 'draft'
    QUEUED = 'queued'
    RUNNING = 'running'
    BLOCKED = 'blocked'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
