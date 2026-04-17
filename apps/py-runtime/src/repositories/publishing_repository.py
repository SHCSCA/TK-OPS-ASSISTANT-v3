from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now
from domain.models.publishing import PublishPlan, PublishReceipt


class PublishingRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_plans(self, *, status: str | None = None) -> list[PublishPlan]:
        with self._session_factory() as session:
            stmt = select(PublishPlan).order_by(PublishPlan.created_at.desc())
            if status is not None:
                stmt = stmt.where(PublishPlan.status == status)
            plans = session.scalars(stmt).all()
            session.expunge_all()
            return list(plans)

    def create_plan(self, plan: PublishPlan) -> PublishPlan:
        with self._session_factory() as session:
            session.add(plan)
            session.commit()
            session.refresh(plan)
            session.expunge(plan)
            return plan

    def get_plan(self, plan_id: str) -> PublishPlan | None:
        with self._session_factory() as session:
            plan = session.get(PublishPlan, plan_id)
            if plan is not None:
                session.expunge(plan)
            return plan

    def update_plan(self, plan_id: str, **kwargs: object) -> PublishPlan | None:
        with self._session_factory() as session:
            plan = session.get(PublishPlan, plan_id)
            if plan is None:
                return None
            for key, value in kwargs.items():
                setattr(plan, key, value)
            plan.updated_at = utc_now()
            session.commit()
            session.refresh(plan)
            session.expunge(plan)
            return plan

    def delete_plan(self, plan_id: str) -> bool:
        with self._session_factory() as session:
            plan = session.get(PublishPlan, plan_id)
            if plan is None:
                return False
            session.delete(plan)
            session.commit()
            return True

    def save_precheck(self, plan_id: str, items_json: str) -> PublishPlan | None:
        with self._session_factory() as session:
            plan = session.get(PublishPlan, plan_id)
            if plan is None:
                return None
            plan.precheck_result_json = items_json
            plan.updated_at = utc_now()
            session.commit()
            session.refresh(plan)
            session.expunge(plan)
            return plan

    def submit_plan(self, plan_id: str) -> PublishPlan | None:
        with self._session_factory() as session:
            plan = session.get(PublishPlan, plan_id)
            if plan is None:
                return None
            plan.status = "submitted"
            plan.submitted_at = utc_now()
            plan.updated_at = plan.submitted_at
            session.commit()
            session.refresh(plan)
            session.expunge(plan)
            return plan

    def get_receipt(self, plan_id: str) -> PublishReceipt | None:
        with self._session_factory() as session:
            receipt = session.scalar(
                select(PublishReceipt).where(PublishReceipt.plan_id == plan_id)
            )
            if receipt is not None:
                session.expunge(receipt)
            return receipt

    def create_receipt(
        self,
        *,
        plan_id: str,
        status: str,
        external_url: str | None = None,
        error_message: str | None = None,
    ) -> PublishReceipt:
        with self._session_factory() as session:
            receipt = session.scalar(
                select(PublishReceipt).where(PublishReceipt.plan_id == plan_id)
            )
            now = utc_now()
            if receipt is None:
                receipt = PublishReceipt(
                    plan_id=plan_id,
                    status=status,
                    external_url=external_url,
                    error_message=error_message,
                    completed_at=now,
                )
                session.add(receipt)
            else:
                receipt.status = status
                receipt.external_url = external_url
                receipt.error_message = error_message
                receipt.completed_at = now
            session.commit()
            session.refresh(receipt)
            session.expunge(receipt)
            return receipt
