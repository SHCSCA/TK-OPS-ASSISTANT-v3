from __future__ import annotations

import json
import logging

from fastapi import HTTPException

from common.time import utc_now
from domain.models.publishing import PublishPlan
from repositories.publishing_repository import PublishingRepository
from schemas.publishing import (
    PrecheckItemResult,
    PrecheckResultDto,
    PublishPlanCreateInput,
    PublishPlanDto,
    PublishPlanUpdateInput,
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
        self._get_plan_model(plan_id)
        checked_at = utc_now()
        items = [
            PrecheckItemResult(
                code="account_binding",
                label="账号绑定",
                result="pending",
                message="V1 暂未接入真实账号检查",
            ),
            PrecheckItemResult(
                code="video_asset",
                label="视频资产",
                result="pending",
                message="V1 暂未接入真实资产检查",
            ),
            PrecheckItemResult(
                code="schedule",
                label="发布时间",
                result="pending",
                message="V1 暂未接入排期冲突检查",
            ),
        ]
        items_json = json.dumps(
            [item.model_dump(mode="json") for item in items], ensure_ascii=False
        )
        try:
            self._repository.save_precheck(plan_id, items_json)
        except Exception as exc:
            log.exception("保存发布预检结果失败")
            raise HTTPException(status_code=500, detail="保存发布预检结果失败") from exc
        return PrecheckResultDto(
            plan_id=plan_id,
            items=items,
            has_errors=False,
            checked_at=checked_at,
        )

    def submit(self, plan_id: str) -> SubmitPlanResultDto:
        plan = self._get_plan_model(plan_id)
        if self._precheck_has_failed(plan.precheck_result_json):
            raise HTTPException(status_code=409, detail="发布预检存在失败项，无法提交")
        try:
            submitted = self._repository.submit_plan(plan_id)
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

    def _get_plan_model(self, plan_id: str) -> PublishPlan:
        try:
            plan = self._repository.get_plan(plan_id)
        except Exception as exc:
            log.exception("查询发布计划详情失败")
            raise HTTPException(status_code=500, detail="查询发布计划详情失败") from exc
        if plan is None:
            raise HTTPException(status_code=404, detail="发布计划不存在")
        return plan

    def _precheck_has_failed(self, precheck_json: str | None) -> bool:
        if not precheck_json:
            return False
        try:
            items = json.loads(precheck_json)
        except json.JSONDecodeError:
            return True
        return any(item.get("result") == "failed" for item in items if isinstance(item, dict))

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
