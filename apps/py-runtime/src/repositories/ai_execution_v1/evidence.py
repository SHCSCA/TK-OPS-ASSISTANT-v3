from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from domain.models.ai_execution import AIExecutionJob
from domain.models.ai_execution_evidence import (
    AIErrorEvidence,
    AIExecutionOutput,
    AIUsageRecord,
)


class AIExecutionEvidenceRepository:
    """持久化任务尝试、用量、输出与安全错误证据。"""

    def add_job(
        self,
        session: Session,
        row: AIExecutionJob,
    ) -> AIExecutionJob:
        session.add(row)
        session.flush([row])
        return row

    def get_job(
        self,
        session: Session,
        account_id: str,
        job_id: str,
    ) -> AIExecutionJob | None:
        return session.scalars(
            select(AIExecutionJob).where(
                AIExecutionJob.account_id == account_id,
                AIExecutionJob.id == job_id,
            )
        ).one_or_none()

    def list_jobs(
        self,
        session: Session,
        account_id: str,
        execution_id: str,
    ) -> tuple[AIExecutionJob, ...]:
        return tuple(
            session.scalars(
                select(AIExecutionJob)
                .where(
                    AIExecutionJob.account_id == account_id,
                    AIExecutionJob.execution_id == execution_id,
                )
                .order_by(AIExecutionJob.attempt.asc())
            ).all()
        )

    def transition_job(
        self,
        session: Session,
        account_id: str,
        job_id: str,
        *,
        expected_statuses: Sequence[str],
        values: Mapping[str, object],
    ) -> AIExecutionJob | None:
        return session.scalars(
            update(AIExecutionJob)
            .where(
                AIExecutionJob.account_id == account_id,
                AIExecutionJob.id == job_id,
                AIExecutionJob.status.in_(tuple(expected_statuses)),
            )
            .values(**values, revision=AIExecutionJob.revision + 1)
            .returning(AIExecutionJob)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        ).one_or_none()

    def add_usage(
        self,
        session: Session,
        row: AIUsageRecord,
    ) -> AIUsageRecord:
        session.add(row)
        session.flush([row])
        return row

    def list_usage(
        self,
        session: Session,
        account_id: str,
        execution_id: str,
    ) -> tuple[AIUsageRecord, ...]:
        return tuple(
            session.scalars(
                select(AIUsageRecord).where(
                    AIUsageRecord.account_id == account_id,
                    AIUsageRecord.execution_id == execution_id,
                )
            ).all()
        )

    def add_output(
        self,
        session: Session,
        row: AIExecutionOutput,
    ) -> AIExecutionOutput:
        session.add(row)
        session.flush([row])
        return row

    def get_output(
        self,
        session: Session,
        account_id: str,
        execution_id: str,
        output_id: str,
    ) -> AIExecutionOutput | None:
        return session.scalars(
            select(AIExecutionOutput).where(
                AIExecutionOutput.account_id == account_id,
                AIExecutionOutput.execution_id == execution_id,
                AIExecutionOutput.id == output_id,
            )
        ).one_or_none()

    def list_outputs(
        self,
        session: Session,
        account_id: str,
        execution_id: str,
    ) -> tuple[AIExecutionOutput, ...]:
        return tuple(
            session.scalars(
                select(AIExecutionOutput)
                .where(
                    AIExecutionOutput.account_id == account_id,
                    AIExecutionOutput.execution_id == execution_id,
                )
                .order_by(AIExecutionOutput.created_at.asc())
            ).all()
        )

    def add_error(
        self,
        session: Session,
        row: AIErrorEvidence,
    ) -> AIErrorEvidence:
        session.add(row)
        session.flush([row])
        return row

    def list_errors(
        self,
        session: Session,
        account_id: str,
        execution_id: str,
    ) -> tuple[AIErrorEvidence, ...]:
        return tuple(
            session.scalars(
                select(AIErrorEvidence)
                .where(
                    AIErrorEvidence.account_id == account_id,
                    AIErrorEvidence.execution_id == execution_id,
                )
                .order_by(AIErrorEvidence.created_at.asc())
            ).all()
        )


__all__ = ["AIExecutionEvidenceRepository"]
