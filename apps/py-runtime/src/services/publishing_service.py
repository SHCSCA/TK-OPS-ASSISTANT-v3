from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from common.http_errors import RuntimeHTTPException
from common.time import utc_now
from domain.models.account import Account
from domain.models.device_workspace import DeviceWorkspace, ExecutionBinding
from domain.models.publishing import PublishPlan, PublishReceipt
from repositories.account_repository import AccountRepository
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from repositories.publishing_repository import PublishingRepository
from schemas.publishing import (
    PrecheckConflictDto,
    PrecheckItemResult,
    PrecheckResultDto,
    PublishBindingSummaryDto,
    PublishCalendarDto,
    PublishCalendarItemDto,
    PublishPlanCreateInput,
    PublishPlanDto,
    PublishPlanLatestReceiptDto,
    PublishPlanPrecheckSummaryDto,
    PublishPlanReadinessDto,
    PublishPlanRecoveryDto,
    PublishPlanUpdateInput,
    PublishReceiptDto,
    PublishSuggestedActionDto,
    SubmitPlanResultDto,
)
from services.ws_manager import ws_manager

log = logging.getLogger(__name__)


class PublishingService:
    def __init__(
        self,
        repository: PublishingRepository,
        *,
        account_repository: AccountRepository | None = None,
        device_workspace_repository: DeviceWorkspaceRepository | None = None,
    ) -> None:
        self._repository = repository
        self._account_repository = account_repository
        self._device_workspace_repository = device_workspace_repository

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
        account = self._get_account_model(plan.account_id)
        binding = self._get_binding_for_account(plan.account_id)
        workspace = self._get_binding_workspace(binding)
        checked_at = utc_now()
        conflicts = self._find_conflicts(plan)
        items = self._build_precheck_items(
            plan=plan,
            account=account,
            binding=binding,
            workspace=workspace,
            conflicts=conflicts,
        )
        blocking_count = sum(1 for item in items if item.result == "failed")
        readiness = self._build_publish_readiness(
            items=items,
            binding=binding,
            workspace=workspace,
        )

        payload = {
            "items": [item.model_dump(mode="json") for item in items],
            "conflicts": [item.model_dump(mode="json") for item in conflicts],
            "checkedAt": checked_at.isoformat(),
            "hasErrors": blocking_count > 0,
            "blockingCount": blocking_count,
            "readiness": readiness.model_dump(mode="json"),
        }
        try:
            self._repository.save_precheck(plan_id, json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            log.exception("保存发布预检结果失败")
            raise HTTPException(status_code=500, detail="保存发布预检结果失败") from exc

        result = PrecheckResultDto(
            plan_id=plan_id,
            items=items,
            conflicts=conflicts,
            has_errors=blocking_count > 0,
            checked_at=checked_at,
            blocking_count=blocking_count,
            readiness=readiness,
        )
        self._broadcast_event(
            {
                "type": "publishing.precheck.completed",
                "planId": plan_id,
                "status": result.readiness.status,
                "blockingCount": result.blocking_count,
                "checkedAt": checked_at.isoformat(),
            }
        )
        return result

    def submit(self, plan_id: str) -> SubmitPlanResultDto:
        precheck = self.precheck(plan_id)
        if precheck.has_errors:
            raise RuntimeHTTPException(
                status_code=409,
                detail="发布预检未通过，请先处理阻断项。",
                error_code="publishing.precheck_failed",
                details={
                    "planId": plan_id,
                    "blockingCount": precheck.blocking_count,
                    "items": [item.model_dump(mode="json") for item in precheck.items],
                },
            )

        try:
            submitted = self._repository.submit_plan(plan_id)
            if submitted is None:
                raise HTTPException(status_code=404, detail="发布计划不存在")
            submitted = self._repository.update_plan(plan_id, status="submitted", error_message=None)
            if submitted is None:
                raise HTTPException(status_code=404, detail="发布计划不存在")
            receipt = self._repository.create_receipt(
                plan_id=plan_id,
                status="receipt_pending",
                platform_response_json=json.dumps(
                    {
                        "stage": "receipt",
                        "summary": "已提交平台，等待平台回执。",
                        "errorCode": None,
                        "errorMessage": None,
                        "nextAction": {
                            "key": "refresh-receipt",
                            "label": "刷新回执",
                        },
                        "isFinal": False,
                    },
                    ensure_ascii=False,
                ),
            )
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("提交发布计划失败")
            raise HTTPException(status_code=500, detail="提交发布计划失败") from exc

        receipt_dto = self._to_latest_receipt_dto(receipt)
        result = SubmitPlanResultDto(
            plan_id=plan_id,
            status=submitted.status,
            submitted_at=submitted.submitted_at or utc_now(),
            message="发布计划已提交，正在等待平台回执。",
            receipt_status=receipt.status,
            error_code=None,
            error_message=None,
            next_action=PublishSuggestedActionDto(
                key="refresh-receipt",
                label="刷新回执",
            ),
            receipt=receipt_dto,
        )
        self._broadcast_event(
            {
                "type": "publishing.submit.completed",
                "planId": plan_id,
                "status": submitted.status,
                "submittedAt": result.submitted_at.isoformat(),
            }
        )
        self._broadcast_event(
            {
                "type": "publishing.receipt.updated",
                "planId": plan_id,
                "receiptStatus": receipt.status,
                "summary": receipt_dto.summary,
                "receivedAt": receipt.received_at.isoformat(),
            }
        )
        return result

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
            raise RuntimeHTTPException(
                status_code=404,
                detail="发布回执不存在",
                error_code="publishing.receipt_not_found",
            )
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

    def _get_account_model(self, account_id: str | None) -> Account | None:
        if self._account_repository is None or not account_id:
            return None
        try:
            return self._account_repository.get_account(account_id)
        except Exception:
            log.exception("查询发布账号详情失败")
            return None

    def _get_binding_for_account(self, account_id: str | None) -> ExecutionBinding | None:
        if self._device_workspace_repository is None or not account_id:
            return None
        try:
            return self._device_workspace_repository.get_binding_for_account(account_id)
        except Exception:
            log.exception("查询发布执行绑定失败")
            return None

    def _get_binding_workspace(self, binding: ExecutionBinding | None) -> DeviceWorkspace | None:
        if self._device_workspace_repository is None or binding is None:
            return None
        try:
            return self._device_workspace_repository.get_workspace(binding.device_workspace_id)
        except Exception:
            log.exception("查询发布工作区失败")
            return None

    def _build_precheck_items(
        self,
        *,
        plan: PublishPlan,
        account: Account | None,
        binding: ExecutionBinding | None,
        workspace: DeviceWorkspace | None,
        conflicts: list[PrecheckConflictDto],
    ) -> list[PrecheckItemResult]:
        items: list[PrecheckItemResult] = []

        if not plan.account_id:
            items.append(
                PrecheckItemResult(
                    code="account_readiness",
                    label="账号就绪",
                    result="failed",
                    message="发布计划尚未绑定发布账号。",
                    error_code="publishing.account_required",
                    affected_target="账号",
                    next_action=PublishSuggestedActionDto(
                        key="bind-account",
                        label="绑定账号",
                    ),
                )
            )
        elif account is None:
            items.append(
                PrecheckItemResult(
                    code="account_readiness",
                    label="账号就绪",
                    result="failed",
                    message="绑定账号不存在或不可用，请重新选择发布账号。",
                    error_code="publishing.account_not_ready",
                    affected_target="账号",
                    next_action=PublishSuggestedActionDto(
                        key="reselect-account",
                        label="重新选择账号",
                    ),
                )
            )
        elif account.status not in {"active", "ready"}:
            items.append(
                PrecheckItemResult(
                    code="account_readiness",
                    label="账号就绪",
                    result="failed",
                    message="发布账号当前未启用，暂不可提交发布。",
                    error_code="publishing.account_not_ready",
                    affected_target="账号",
                    next_action=PublishSuggestedActionDto(
                        key="enable-account",
                        label="启用账号",
                    ),
                )
            )
        elif not (account.username or "").strip():
            items.append(
                PrecheckItemResult(
                    code="account_readiness",
                    label="账号就绪",
                    result="failed",
                    message="发布账号缺少用户名，无法继续发布。",
                    error_code="publishing.account_not_ready",
                    affected_target="账号",
                    next_action=PublishSuggestedActionDto(
                        key="complete-account-profile",
                        label="补全账号信息",
                    ),
                )
            )
        elif _is_auth_expired(account.auth_expires_at):
            items.append(
                PrecheckItemResult(
                    code="account_readiness",
                    label="账号就绪",
                    result="failed",
                    message="发布账号授权已过期，请重新校验授权。",
                    error_code="publishing.account_not_ready",
                    affected_target="账号",
                    next_action=PublishSuggestedActionDto(
                        key="refresh-account-auth",
                        label="重新校验授权",
                    ),
                )
            )
        else:
            items.append(
                PrecheckItemResult(
                    code="account_readiness",
                    label="账号就绪",
                    result="passed",
                    message="发布账号已就绪。",
                    affected_target="账号",
                )
            )

        if binding is None or binding.status != "active":
            items.append(
                PrecheckItemResult(
                    code="device_binding",
                    label="设备绑定",
                    result="failed",
                    message="发布账号尚未绑定可用工作区，无法执行发布。",
                    error_code="publishing.device_binding_required",
                    affected_target="设备与工作区",
                    next_action=PublishSuggestedActionDto(
                        key="bind-workspace",
                        label="绑定工作区",
                    ),
                )
            )
        elif workspace is None:
            items.append(
                PrecheckItemResult(
                    code="device_binding",
                    label="设备绑定",
                    result="failed",
                    message="绑定工作区不存在，请重新绑定后再试。",
                    error_code="publishing.device_binding_required",
                    affected_target="设备与工作区",
                    next_action=PublishSuggestedActionDto(
                        key="rebind-workspace",
                        label="重新绑定工作区",
                    ),
                )
            )
        elif not (workspace.root_path or "").strip():
            items.append(
                PrecheckItemResult(
                    code="device_binding",
                    label="设备绑定",
                    result="failed",
                    message="绑定工作区缺少根目录，无法执行发布。",
                    error_code="publishing.device_binding_required",
                    affected_target="设备与工作区",
                    next_action=PublishSuggestedActionDto(
                        key="repair-workspace",
                        label="修复工作区",
                    ),
                )
            )
        elif not Path(workspace.root_path).exists():
            items.append(
                PrecheckItemResult(
                    code="device_binding",
                    label="设备绑定",
                    result="failed",
                    message="绑定工作区目录不存在，请先修复目录后再发布。",
                    error_code="publishing.device_binding_required",
                    affected_target="设备与工作区",
                    next_action=PublishSuggestedActionDto(
                        key="repair-workspace-path",
                        label="修复工作区目录",
                    ),
                )
            )
        else:
            items.append(
                PrecheckItemResult(
                    code="device_binding",
                    label="设备绑定",
                    result="passed",
                    message="工作区绑定可用。",
                    affected_target="设备与工作区",
                )
            )

        if plan.scheduled_at is None:
            items.append(
                PrecheckItemResult(
                    code="publish_config",
                    label="发布配置",
                    result="failed",
                    message="发布计划尚未设置发布时间。",
                    error_code="publishing.config_missing",
                    affected_target="发布配置",
                    next_action=PublishSuggestedActionDto(
                        key="set-schedule",
                        label="设置发布时间",
                    ),
                )
            )
        else:
            items.append(
                PrecheckItemResult(
                    code="publish_config",
                    label="发布配置",
                    result="passed",
                    message="发布时间已配置。",
                    affected_target="发布配置",
                )
            )

        if not plan.video_asset_id:
            items.append(
                PrecheckItemResult(
                    code="video_asset",
                    label="视频资产",
                    result="failed",
                    message="发布计划缺少视频资产，无法提交发布。",
                    error_code="publishing.video_asset_required",
                    affected_target="视频资产",
                    next_action=PublishSuggestedActionDto(
                        key="select-video-asset",
                        label="选择视频资产",
                    ),
                )
            )
        else:
            items.append(
                PrecheckItemResult(
                    code="video_asset",
                    label="视频资产",
                    result="passed",
                    message="视频资产已关联。",
                    affected_target="视频资产",
                )
            )

        if conflicts:
            items.append(
                PrecheckItemResult(
                    code="schedule",
                    label="发布排期",
                    result="failed",
                    message="检测到同账号同时间的排期冲突。",
                    error_code="publishing.schedule_conflict",
                    affected_target="发布时间",
                    next_action=PublishSuggestedActionDto(
                        key="reschedule-plan",
                        label="调整发布时间",
                    ),
                )
            )
        else:
            items.append(
                PrecheckItemResult(
                    code="schedule",
                    label="发布排期",
                    result="passed",
                    message="当前排期可用。",
                    affected_target="发布时间",
                )
            )

        return items

    def _build_publish_readiness(
        self,
        *,
        items: list[PrecheckItemResult],
        binding: ExecutionBinding | None,
        workspace: DeviceWorkspace | None,
    ) -> PublishPlanReadinessDto:
        binding_summary = self._build_binding_summary(binding, workspace)
        first_blocking = next((item for item in items if item.result == "failed"), None)
        if first_blocking is None:
            return PublishPlanReadinessDto(
                can_submit=True,
                status="ready",
                binding=binding_summary,
            )
        return PublishPlanReadinessDto(
            can_submit=False,
            status="blocked",
            error_code=first_blocking.error_code,
            error_message=first_blocking.message,
            next_action=first_blocking.next_action,
            binding=binding_summary,
        )

    def _build_binding_summary(
        self,
        binding: ExecutionBinding | None,
        workspace: DeviceWorkspace | None,
    ) -> PublishBindingSummaryDto | None:
        if binding is None:
            return None
        return PublishBindingSummaryDto(
            binding_id=binding.id,
            workspace_id=binding.device_workspace_id,
            workspace_name=workspace.name if workspace is not None else None,
            workspace_status=workspace.status if workspace is not None else None,
            root_path=workspace.root_path if workspace is not None else None,
            updated_at=binding.updated_at,
        )

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
                    reason="同账号同一时间点存在排期冲突。",
                )
            )
        return conflicts

    def _calendar_conflict_count(self, plan_id: str) -> int:
        plan = self._get_plan_model(plan_id)
        if plan.scheduled_at is None:
            return 0
        return len(self._find_conflicts(plan))

    def _to_dto(self, plan: PublishPlan) -> PublishPlanDto:
        latest_receipt = self._get_latest_receipt_model(plan.id)
        precheck_summary = self._build_precheck_summary(plan.precheck_result_json)
        precheck_items = self._load_precheck_items(plan.precheck_result_json)
        binding = self._get_binding_for_account(plan.account_id)
        workspace = self._get_binding_workspace(binding)
        readiness = self._build_publish_readiness(
            items=precheck_items or self._build_precheck_items(
                plan=plan,
                account=self._get_account_model(plan.account_id),
                binding=binding,
                workspace=workspace,
                conflicts=self._find_conflicts(plan),
            ),
            binding=binding,
            workspace=workspace,
        )
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
            precheck_summary=precheck_summary,
            latest_receipt=self._to_latest_receipt_dto(latest_receipt) if latest_receipt else None,
            publish_readiness=readiness,
            recovery=self._build_recovery(plan, readiness, latest_receipt),
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )

    def _to_receipt_dto(self, receipt: PublishReceipt) -> PublishReceiptDto:
        payload = self._parse_receipt_payload(receipt.platform_response_json)
        return PublishReceiptDto(
            id=receipt.id,
            plan_id=receipt.plan_id,
            status=receipt.status,
            stage=str(payload.get("stage") or _receipt_stage_for_status(receipt.status)),
            summary=str(payload.get("summary") or _receipt_summary_for_status(receipt.status)),
            error_code=_optional_str(payload.get("errorCode")),
            error_message=_optional_str(payload.get("errorMessage")),
            next_action=_to_action(payload.get("nextAction")),
            is_final=bool(payload.get("isFinal", receipt.status in {"submitted", "published", "failed", "cancelled"})),
            platform_response_json=receipt.platform_response_json,
            received_at=receipt.received_at,
            created_at=receipt.created_at,
        )

    def _to_latest_receipt_dto(self, receipt: PublishReceipt) -> PublishPlanLatestReceiptDto:
        payload = self._parse_receipt_payload(receipt.platform_response_json)
        return PublishPlanLatestReceiptDto(
            id=receipt.id,
            status=receipt.status,
            stage=str(payload.get("stage") or _receipt_stage_for_status(receipt.status)),
            summary=str(payload.get("summary") or _receipt_summary_for_status(receipt.status)),
            error_code=_optional_str(payload.get("errorCode")),
            error_message=_optional_str(payload.get("errorMessage")),
            next_action=_to_action(payload.get("nextAction")),
            received_at=receipt.received_at,
            is_final=bool(payload.get("isFinal", receipt.status in {"submitted", "published", "failed", "cancelled"})),
        )

    def _build_precheck_summary(self, precheck_json: str | None) -> PublishPlanPrecheckSummaryDto:
        payload = self._parse_precheck_payload(precheck_json)
        if payload is None:
            return PublishPlanPrecheckSummaryDto(status="pending", checked_at=None, blocking_count=0)
        checked_at = _parse_datetime(payload.get("checkedAt"))
        blocking_count = _coerce_int(payload.get("blockingCount"))
        if blocking_count == 0 and bool(payload.get("hasErrors")):
            blocking_count = 1
        status = "blocked" if blocking_count > 0 else "ready"
        return PublishPlanPrecheckSummaryDto(
            status=status,
            checked_at=checked_at,
            blocking_count=blocking_count,
        )

    def _build_recovery(
        self,
        plan: PublishPlan,
        readiness: PublishPlanReadinessDto,
        latest_receipt: PublishReceipt | None,
    ) -> PublishPlanRecoveryDto:
        latest_receipt_dto = (
            self._to_latest_receipt_dto(latest_receipt) if latest_receipt is not None else None
        )
        can_retry = bool(
            latest_receipt_dto and latest_receipt_dto.status in {"failed", "receipt_failed"}
        ) or plan.status in {"failed", "cancelled"}
        can_cancel = plan.status in {"draft", "submitting", "submitted", "receipt_pending"}

        if not readiness.can_submit:
            next_action = readiness.next_action
        elif can_retry:
            next_action = PublishSuggestedActionDto(
                key="retry-submit",
                label="重新提交",
            )
        elif can_cancel:
            next_action = PublishSuggestedActionDto(
                key="cancel-publish",
                label="取消发布",
            )
        elif latest_receipt_dto and not latest_receipt_dto.is_final:
            next_action = PublishSuggestedActionDto(
                key="refresh-receipt",
                label="刷新回执",
            )
        else:
            next_action = None

        return PublishPlanRecoveryDto(
            can_retry=can_retry,
            can_cancel=can_cancel,
            next_action=next_action,
        )

    def _load_precheck_items(self, precheck_json: str | None) -> list[PrecheckItemResult]:
        payload = self._parse_precheck_payload(precheck_json)
        if payload is None:
            return []
        items = payload.get("items")
        if not isinstance(items, list):
            return []
        parsed: list[PrecheckItemResult] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                parsed.append(PrecheckItemResult.model_validate(item))
            except Exception:
                continue
        return parsed

    def _parse_precheck_payload(self, precheck_json: str | None) -> dict[str, Any] | None:
        if not precheck_json:
            return None
        try:
            payload = json.loads(precheck_json)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _parse_receipt_payload(self, platform_response_json: str | None) -> dict[str, Any]:
        if not platform_response_json:
            return {}
        try:
            payload = json.loads(platform_response_json)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _get_latest_receipt_model(self, plan_id: str) -> PublishReceipt | None:
        try:
            return self._repository.get_latest_receipt(plan_id)
        except Exception:
            log.exception("查询最新发布回执失败")
            return None

    def _broadcast_event(self, event: dict[str, object]) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(ws_manager.broadcast(event))
        else:
            asyncio.create_task(ws_manager.broadcast(event))


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _to_action(value: object) -> PublishSuggestedActionDto | None:
    if not isinstance(value, dict):
        return None
    key = _optional_str(value.get("key"))
    label = _optional_str(value.get("label"))
    if key is None or label is None:
        return None
    return PublishSuggestedActionDto(key=key, label=label)


def _is_auth_expired(auth_expires_at: str | None) -> bool:
    if auth_expires_at is None:
        return False
    raw_value = auth_expires_at.strip()
    if raw_value == "":
        return False
    normalized = raw_value.replace("Z", "+00:00")
    try:
        expires_at = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)


def _receipt_stage_for_status(status: str) -> str:
    if status in {"submitted", "receipt_pending"}:
        return "receipt"
    if status in {"failed", "receipt_failed"}:
        return "receipt"
    if status == "published":
        return "published"
    if status == "cancelled":
        return "cancelled"
    return "submit"


def _receipt_summary_for_status(status: str) -> str:
    if status == "receipt_pending":
        return "已提交平台，等待平台回执。"
    if status == "submitted":
        return "平台已接收发布请求。"
    if status in {"failed", "receipt_failed"}:
        return "平台回执失败，请处理后重试。"
    if status == "published":
        return "平台已确认发布完成。"
    if status == "cancelled":
        return "发布计划已取消。"
    return "发布链路状态已更新。"
