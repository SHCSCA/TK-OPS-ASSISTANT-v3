from __future__ import annotations

from dataclasses import dataclass, field

from repositories.ai_execution_v1.evidence import AIExecutionEvidenceRepository
from repositories.ai_execution_v1.executions import AIExecutionRepository
from repositories.ai_execution_v1.snapshots import AIExecutionSnapshotRepository


@dataclass(frozen=True, slots=True)
class AIExecutionV1Repository:
    executions: AIExecutionRepository = field(
        default_factory=AIExecutionRepository
    )
    snapshots: AIExecutionSnapshotRepository = field(
        default_factory=AIExecutionSnapshotRepository
    )
    evidence: AIExecutionEvidenceRepository = field(
        default_factory=AIExecutionEvidenceRepository
    )


__all__ = ["AIExecutionV1Repository"]
