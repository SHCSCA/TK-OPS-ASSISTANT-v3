from __future__ import annotations

import json
import logging

from fastapi import HTTPException

from common.time import utc_now
from domain.models.publishing import PublishPlan, PublishReceipt
from repositories.publishing_repository import PublishingRepository
from schemas.publishing import (
    PrecheckConflictDto,
    PrecheckItemResult,
    PrecheckResultDto,
    PublishCalendarDto,
    PublishCalendarItemDto,
    PublishPlanCreateInput,
    PublishPlanDto,
    PublishPlanUpdateInput,
    PublishReceiptDto,
    SubmitPlanResultDto,
)

log = logging.getLogger(__name__)


class PublishingService:
    def __init__(self, repository: PublishingRepository) -> None:
        self._repository = repository

    def list_plans(self, *, status: str | None = None) -> list[PublishPlanDto]:
        try:
            plans = self._repository.list_plans(status=status)
        except Exception as exc:
            log.exception("查询发布计划列表失败")
            raise HTTPException(status_code=500, detail="查询发布计划列表失败") from exc
        return [self._to_dto(plan) for plan in plans]

    def create_plan(self, payload: PublishPlanCreateInput) -> PublishPlanDto:
        plan = PublishPlan(
            title=payload.title.strip(),
            account_id=payload.account_id,
            account_name=payload.account_name,
            project_id=payload.project_id,
            video_asset_id=payload.video_asset_id,
            scheduled_at=payload.scheduled_at,
        )
        try:
            saved = self._repository.create_plan(plan)
        except Exception as exc:
            log.exception("创建发布计划失败")
            raise HTTPException(status_code=500, detail="创建发布计划失败") from exc
        return self._to_dto(saved)

    def get_plan(self, plan_id: str) -> PublishPlanDto:
        return self._to_dto(self._get_plan_model(plan_id))

    def update_plan(self, plan_id: str, payload: PublishPlanUpdateInput) -> PublishPlanDto:
        changes = payload.model_dump(exclude_unset=True)
        if "title" in changes and isinstance(changes["title"], str):
            changes["title"] = changes["title"].strip()
        try:
            plan = self._repository.update_plan(plan_id, **changes)
        except Exception as exc:
            log.exception("更新发布计划失败")
            raise HTTPException(status_code=500, detail="更新发布计划失败") from exc
        if plan is None:
            raise HTTPException(status_code=404, detail="发布计划不存在")
        return self._to_dto(plan)

    def delete_plan(self, plan_id: str) -> None:
        try:
            deleted = self._repository.delete_plan(plan_id)
        except Exception as exc:
            log.exception("删除发布计划失败")
            raise HTTPException(status_code=500, detail="删除发布计划失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="发布计划不存在")

    def precheck(self, plan_id: str) -> PrecheckResultDto:
        plan = self._get_plan_model(plan_id)
        checked_at = utc_now()
        conflicts = self._find_conflicts(plan)
        items = [
            PrecheckItemResult(
                code="account_binding",
                label="账号绑定",
                result="passed" if plan.account_id else "pending",
                message="已关联账号" if plan.account_id else "请先补充账号绑定",
            ),
            PrecheckItemResult(
                code="video_asset",
                label="视频资产",
                result="passed" if plan.video_asset_id else "pending",
                message="已选择视频资产" if plan.video_asset_id else "请先补充视频资产",
            ),
            PrecheckItemResult(
                code="schedule",
                label="发布时间",
                result="failed" if conflicts else "passed",
                message="检测到排期冲突" if conflicts else "排期可用",
            ),
        ]
        payload = {
            "items": [item.model_dump(mode="json") for item in items],
            "conflicts": [item.model_dump(mode="json") for item in conflicts],
            "checkedAt": checked_at.isoformat(),
            "hasErrors": bool(conflicts),
        }
        try:
            self._repository.save_precheck(plan_id, json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            log.exception("保存发布预检结果失败")
            raise HTTPException(status_code=500, detail="保存发布预检结果失败") from exc
        return PrecheckResultDto(
            plan_id=plan_id,
            items=items,
            conflicts=conflicts,
            has_errors=bool(conflicts),
            checked_at=checked_at,
        )

    def submit(self, plan_id: str) -> SubmitPlanResultDto:
        plan = self._get_plan_model(plan_id)
        if self._precheck_has_failed(plan.precheck_result_json):
            raise HTTPException(status_code=409, detail="发布预检存在冲突，无法提交")
        try:
            submitted = self._repository.submit_plan(plan_id)
            submitted_at = submitted.submitted_at if submitted is not None else utc_now()
            self._repository.create_receipt(
                plan_id=plan_id,
                status="submitted",
                platform_response_json=json.dumps(
                    {
                        "planId": plan_id,
                        "submittedAt": submitted_at,
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            )
        except Exception as exc:
            log.exception("提交发布计划失败")
            raise HTTPException(status_code=500, detail="提交发布计划失败") from exc
        if submitted is None:
            raise HTTPException(status_code=404, detail="发布计划不存在")
        return SubmitPlanResultDto(
            plan_id=plan_id,
            status=submitted.status,
            submitted_at=submitted.submitted_at or utc_now(),
            message="发布计划已提交",
        )

    def cancel(self, plan_id: str) -> PublishPlanDto:
        try:
            plan = self._repository.update_plan(plan_id, status="cancelled")
        except Exception as exc:
            log.exception("取消发布计划失败")
            raise HTTPException(status_code=500, detail="取消发布计划失败") from exc
        if plan is None:
            raise HTTPException(status_code=404, detail="发布计划不存在")
        return self._to_dto(plan)

    def get_calendar(self) -> PublishCalendarDto:
        plans = self.list_plans()
        items = [
            PublishCalendarItemDto(
                plan_id=plan.id,
                title=plan.title,
                status=plan.status,
                scheduled_at=plan.scheduled_at,
                account_name=plan.account_name,
                conflict_count=self._calendar_conflict_count(plan.id),
            )
            for plan in plans
            if plan.scheduled_at is not None
        ]
        return PublishCalendarDto(items=items, generated_at=utc_now())

    def list_receipts(self, plan_id: str) -> list[PublishReceiptDto]:
        self._get_plan_model(plan_id)
        try:
            receipts = self._repository.list_receipts(plan_id)
        except Exception as exc:
            log.exception("查询发布回执历史失败")
            raise HTTPException(status_code=500, detail="查询发布回执历史失败") from exc
        return [self._to_receipt_dto(receipt) for receipt in receipts]

    def get_latest_receipt(self, plan_id: str) -> PublishReceiptDto:
        self._get_plan_model(plan_id)
        try:
            receipt = self._repository.get_latest_receipt(plan_id)
        except Exception as exc:
            log.exception("查询最新发布回执失败")
            raise HTTPException(status_code=500, detail="查询最新发布回执失败") from exc
        if receipt is None:
            raise HTTPException(status_code=404, detail="发布回执不存在")
        return self._to_receipt_dto(receipt)

    def _get_plan_model(self, plan_id: str) -> PublishPlan:
        try:
            plan = self._repository.get_plan(plan_id)
        except Exception as exc:
            log.exception("查询发布计划详情失败")
            raise HTTPException(status_code=500, detail="查询发布计划详情失败") from exc
        if plan is None:
            raise HTTPException(status_code=404, detail="发布计划不存在")
        return plan

    def _find_conflicts(self, plan: PublishPlan) -> list[PrecheckConflictDto]:
        if plan.scheduled_at is None:
            return []
        try:
            plans = self._repository.list_plans()
        except Exception as exc:
            log.exception("查询发布排期冲突失败")
            raise HTTPException(status_code=500, detail="查询发布排期冲突失败") from exc
        conflicts: list[PrecheckConflictDto] = []
        for other in plans:
            if other.id == plan.id:
                continue
            if other.scheduled_at != plan.scheduled_at:
                continue
            if plan.account_id is not None and other.account_id != plan.account_id:
                continue
            conflicts.append(
                PrecheckConflictDto(
                    conflicting_plan_id=other.id,
                    conflicting_title=other.title,
                    conflicting_scheduled_at=other.scheduled_at,
                    reason="同账号同一时间点存在排期冲突",
                )
            )
        return conflicts

    def _precheck_has_failed(self, precheck_json: str | None) -> bool:
        if not precheck_json:
            return False
        try:
            payload = json.loads(precheck_json)
        except json.JSONDecodeError:
            return True
        conflicts = payload.get("conflicts")
        if isinstance(conflicts, list) and conflicts:
            return True
        items = payload.get("items")
        if isinstance(items, list):
            return any(
                isinstance(item, dict) and item.get("result") == "failed" for item in items
            )
        return False

    def _calendar_conflict_count(self, plan_id: str) -> int:
        plan = self._get_plan_model(plan_id)
        if plan.scheduled_at is None:
            return 0
        return len(self._find_conflicts(plan))

    def _to_dto(self, plan: PublishPlan) -> PublishPlanDto:
        return PublishPlanDto(
            id=plan.id,
            title=plan.title,
            account_id=plan.account_id,
            account_name=plan.account_name,
            project_id=plan.project_id,
            video_asset_id=plan.video_asset_id,
            status=plan.status,
            scheduled_at=plan.scheduled_at,
            submitted_at=plan.submitted_at,
            published_at=plan.published_at,
            error_message=plan.error_message,
            precheck_result_json=plan.precheck_result_json,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )

    def _to_receipt_dto(self, receipt: PublishReceipt) -> PublishReceiptDto:
        return PublishReceiptDto(
            id=receipt.id,
            plan_id=receipt.plan_id,
            status=receipt.status,
            platform_response_json=receipt.platform_response_json,
            received_at=receipt.received_at,
            created_at=receipt.created_at,
        )
