from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from common.http_errors import RuntimeHTTPException
from common.time import utc_now
from domain.models.publishing import PublishPlan, PublishReceipt
from domain.models.review import ReviewSummary
from repositories.ai_job_repository import AIJobRepository
from repositories.dashboard_repository import DashboardRepository, StoredProject
from repositories.publishing_repository import PublishingRepository
from repositories.review_repository import ReviewRepository
from repositories.script_repository import ScriptRepository, StoredScriptVersion
from repositories.storyboard_repository import StoryboardRepository
from schemas.dashboard import ProjectSummaryDto
from schemas.review import (
    AnalyzeProjectResultDto,
    ApplySuggestionToScriptResultDto,
    ReviewFeedbackTargetDto,
    ReviewIssueCategoryDto,
    ReviewLatestExecutionResultDto,
    ReviewSuggestion,
    ReviewSummaryDto,
    ReviewSummaryUpdateInput,
)
from schemas.scripts import ScriptVersionDto

log = logging.getLogger(__name__)

_PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}


class ReviewService:
    def __init__(
        self,
        repository: ReviewRepository,
        *,
        dashboard_repository: DashboardRepository | None = None,
        script_repository: ScriptRepository | None = None,
        storyboard_repository: StoryboardRepository | None = None,
        publishing_repository: PublishingRepository | None = None,
        ai_job_repository: AIJobRepository | None = None,
    ) -> None:
        self._repository = repository
        self._dashboard_repository = dashboard_repository
        self._script_repository = script_repository
        self._storyboard_repository = storyboard_repository
        self._publishing_repository = publishing_repository
        self._ai_job_repository = ai_job_repository

    def get_summary(
        self,
        project_id: str,
        *,
        dashboard_repository: DashboardRepository | None = None,
        script_repository: ScriptRepository | None = None,
        publishing_repository: PublishingRepository | None = None,
    ) -> ReviewSummaryDto:
        project = self._get_project_or_raise(project_id, dashboard_repository=dashboard_repository)
        summary = self._get_or_create_summary(project_id, project_name=project.name)
        scripts = self._list_script_versions(project_id, script_repository=script_repository)
        latest_plan = self._get_latest_publish_plan(
            project_id,
            publishing_repository=publishing_repository,
        )
        latest_receipt = self._get_latest_publish_receipt(
            latest_plan,
            publishing_repository=publishing_repository,
        )
        return self._to_dto(
            summary,
            project=project,
            scripts=scripts,
            latest_plan=latest_plan,
            latest_receipt=latest_receipt,
        )

    def update_summary(
        self,
        project_id: str,
        payload: ReviewSummaryUpdateInput,
        *,
        dashboard_repository: DashboardRepository | None = None,
        script_repository: ScriptRepository | None = None,
        publishing_repository: PublishingRepository | None = None,
    ) -> ReviewSummaryDto:
        project = self._get_project_or_raise(project_id, dashboard_repository=dashboard_repository)
        values = payload.model_dump(exclude_unset=True)
        project_name = values.pop("project_name", None) or project.name
        try:
            summary = self._repository.upsert_summary(
                project_id,
                project_name=project_name,
                **values,
            )
        except Exception as exc:
            log.exception("更新复盘摘要失败")
            raise HTTPException(status_code=500, detail="更新复盘摘要失败") from exc

        scripts = self._list_script_versions(project_id, script_repository=script_repository)
        latest_plan = self._get_latest_publish_plan(
            project_id,
            publishing_repository=publishing_repository,
        )
        latest_receipt = self._get_latest_publish_receipt(
            latest_plan,
            publishing_repository=publishing_repository,
        )
        return self._to_dto(
            summary,
            project=project,
            scripts=scripts,
            latest_plan=latest_plan,
            latest_receipt=latest_receipt,
        )

    def analyze(
        self,
        project_id: str,
        *,
        dashboard_repository: DashboardRepository | None = None,
        script_repository: ScriptRepository | None = None,
        publishing_repository: PublishingRepository | None = None,
    ) -> AnalyzeProjectResultDto:
        project = self._get_project_or_raise(project_id, dashboard_repository=dashboard_repository)
        summary = self._get_or_create_summary(project_id, project_name=project.name)
        scripts = self._list_script_versions(project_id, script_repository=script_repository)
        latest_plan = self._get_latest_publish_plan(
            project_id,
            publishing_repository=publishing_repository,
        )
        latest_receipt = self._get_latest_publish_receipt(
            latest_plan,
            publishing_repository=publishing_repository,
        )
        existing = self._get_existing_suggestion_state(project_id)
        suggestions = self._build_contextual_suggestions(
            summary=summary,
            project=project,
            scripts=scripts,
            latest_plan=latest_plan,
            latest_receipt=latest_receipt,
        )
        suggestions = [self._merge_suggestion_state(item, existing) for item in suggestions]
        suggestions_json = json.dumps(
            [item.model_dump(mode="json") for item in suggestions],
            ensure_ascii=False,
        )
        try:
            self._repository.save_suggestions(project_id, suggestions_json)
            analyzed_summary = self._repository.mark_analyzed(project_id)
        except Exception as exc:
            log.exception("生成复盘建议失败")
            raise HTTPException(status_code=500, detail="生成复盘建议失败") from exc

        latest_script = scripts[0] if scripts else None
        message_parts = [f"已基于项目「{project.name}」"]
        if latest_script is not None:
            message_parts.append(f"脚本第 {latest_script.revision} 版")
        else:
            message_parts.append("当前无脚本版本")
        if latest_plan is not None:
            message_parts.append(f"发布计划「{latest_plan.title}」")
        message = "、".join(message_parts) + f"生成 {len(suggestions)} 条复盘建议。"
        return AnalyzeProjectResultDto(
            project_id=project_id,
            status="done",
            message=message,
            analyzed_at=analyzed_summary.last_analyzed_at or utc_now(),
        )

    def adopt_suggestion(
        self,
        suggestion_id: str,
        *,
        project_id: str | None = None,
        dashboard_repository: DashboardRepository | None = None,
        script_repository: ScriptRepository | None = None,
        storyboard_repository: StoryboardRepository | None = None,
    ) -> ProjectSummaryDto:
        source_project_id = project_id or self._project_id_from_suggestion_id(suggestion_id)
        dashboard_repository = dashboard_repository or self._dashboard_repository
        script_repository = script_repository or self._script_repository
        storyboard_repository = storyboard_repository or self._storyboard_repository
        if dashboard_repository is None:
            raise HTTPException(status_code=500, detail="复盘采纳缺少项目仓储依赖")
        if script_repository is None or storyboard_repository is None:
            raise HTTPException(status_code=500, detail="复盘采纳缺少上下文复制依赖")

        summary = self._get_summary_model(source_project_id)
        suggestions = self._parse_suggestions(summary.suggestions_json)
        suggestion = next((item for item in suggestions if item.id == suggestion_id), None)
        if suggestion is None:
            raise RuntimeHTTPException(
                status_code=404,
                detail="复盘建议不存在，无法采纳。",
                error_code="review.suggestion_not_found",
            )

        child_name = f"{summary.project_name or source_project_id} - {suggestion.title}"
        child_description = f"由复盘建议 {suggestion.code} 采纳后生成的子项目。"
        try:
            child_project = dashboard_repository.create_project(
                name=child_name,
                description=child_description,
            )
            script_revision = self._copy_latest_script_context(
                source_project_id=source_project_id,
                target_project_id=child_project.id,
                script_repository=script_repository,
            )
            storyboard_revision = self._copy_latest_storyboard_context(
                source_project_id=source_project_id,
                target_project_id=child_project.id,
                storyboard_repository=storyboard_repository,
            )
            dashboard_repository.update_project_versions(
                child_project.id,
                current_script_version=script_revision,
                current_storyboard_version=storyboard_revision,
            )
            suggestion.adopted = True
            suggestion.adopted_as_project_id = child_project.id
            suggestion.adopted_at = utc_now()
            self._repository.save_suggestions(
                source_project_id,
                json.dumps([item.model_dump(mode="json") for item in suggestions], ensure_ascii=False),
            )
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("复盘建议采纳失败")
            raise HTTPException(status_code=500, detail="复盘建议采纳失败") from exc
        return self._to_project_dto(child_project)

    def apply_suggestion_to_script(
        self,
        suggestion_id: str,
        *,
        project_id: str | None = None,
        dashboard_repository: DashboardRepository | None = None,
        script_repository: ScriptRepository | None = None,
    ) -> ApplySuggestionToScriptResultDto:
        source_project_id = project_id or self._project_id_from_suggestion_id(suggestion_id)
        dashboard_repository = dashboard_repository or self._dashboard_repository
        script_repository = script_repository or self._script_repository
        if dashboard_repository is None:
            raise HTTPException(status_code=500, detail="复盘服务缺少项目仓储依赖")
        if script_repository is None:
            raise HTTPException(status_code=500, detail="复盘服务缺少脚本仓储依赖")

        summary = self._get_summary_model(source_project_id)
        suggestions = self._parse_suggestions(summary.suggestions_json)
        suggestion = next((item for item in suggestions if item.id == suggestion_id), None)
        if suggestion is None:
            raise RuntimeHTTPException(
                status_code=404,
                detail="复盘建议不存在，无法应用到脚本。",
                error_code="review.suggestion_not_found",
            )

        try:
            script_versions = script_repository.list_versions(source_project_id)
            latest_content = script_versions[0].content if script_versions else ""
            applied_content = self._build_applied_script_content(
                latest_content=latest_content,
                suggestion=suggestion,
            )
            stored_script = script_repository.save_version(
                source_project_id,
                source="review_apply",
                content=applied_content,
            )
            dashboard_repository.update_project_versions(
                source_project_id,
                current_script_version=stored_script.revision,
            )
            suggestion.adopted = True
            suggestion.adopted_at = utc_now()
            suggestion.adopted_as_project_id = None
            self._repository.save_suggestions(
                source_project_id,
                json.dumps([item.model_dump(mode="json") for item in suggestions], ensure_ascii=False),
            )
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("复盘建议应用到脚本失败")
            raise HTTPException(status_code=500, detail="复盘建议应用到脚本失败") from exc

        return ApplySuggestionToScriptResultDto(
            projectId=source_project_id,
            suggestionId=suggestion_id,
            status="已应用",
            message="已将复盘建议应用到原项目脚本，并生成新的脚本版本。",
            currentScriptVersion=stored_script.revision,
            scriptVersion=self._to_script_version_dto(stored_script),
        )

    def _get_or_create_summary(self, project_id: str, *, project_name: str | None) -> ReviewSummary:
        try:
            summary = self._repository.get_summary(project_id)
            if summary is None:
                summary = self._repository.upsert_summary(project_id, project_name=project_name)
            elif project_name is not None and summary.project_name != project_name:
                summary = self._repository.upsert_summary(project_id, project_name=project_name)
        except Exception as exc:
            log.exception("查询复盘摘要失败")
            raise HTTPException(status_code=500, detail="查询复盘摘要失败") from exc
        return summary

    def _get_summary_model(self, project_id: str) -> ReviewSummary:
        try:
            summary = self._repository.get_summary(project_id)
            if summary is None:
                summary = self._repository.upsert_summary(project_id)
        except Exception as exc:
            log.exception("查询复盘摘要失败")
            raise HTTPException(status_code=500, detail="查询复盘摘要失败") from exc
        return summary

    def _get_project_or_raise(
        self,
        project_id: str,
        *,
        dashboard_repository: DashboardRepository | None = None,
    ) -> StoredProject:
        repository = dashboard_repository or self._dashboard_repository
        if repository is None:
            raise HTTPException(status_code=500, detail="复盘服务缺少项目仓储依赖")
        try:
            project = repository.get_project(project_id)
        except Exception as exc:
            log.exception("查询复盘项目失败")
            raise HTTPException(status_code=500, detail="查询复盘项目失败") from exc
        if project is None:
            raise RuntimeHTTPException(
                status_code=404,
                detail="复盘项目不存在，请先创建或切换到有效项目。",
                error_code="review.project_not_found",
            )
        return project

    def _list_script_versions(
        self,
        project_id: str,
        *,
        script_repository: ScriptRepository | None = None,
    ) -> list[StoredScriptVersion]:
        repository = script_repository or self._script_repository
        if repository is None:
            return []
        try:
            return repository.list_versions(project_id)
        except Exception:
            log.exception("查询复盘脚本版本失败")
            return []

    def _get_latest_publish_plan(
        self,
        project_id: str,
        *,
        publishing_repository: PublishingRepository | None = None,
    ) -> PublishPlan | None:
        repository = publishing_repository or self._publishing_repository
        if repository is None:
            return None
        try:
            plans = repository.list_plans()
        except Exception:
            log.exception("查询复盘发布计划失败")
            return None
        project_plans = [plan for plan in plans if plan.project_id == project_id]
        if not project_plans:
            return None
        project_plans.sort(
            key=lambda item: (
                _sortable_datetime(item.updated_at),
                _sortable_datetime(item.submitted_at),
                _sortable_datetime(item.created_at),
            ),
            reverse=True,
        )
        return project_plans[0]

    def _get_latest_publish_receipt(
        self,
        latest_plan: PublishPlan | None,
        *,
        publishing_repository: PublishingRepository | None = None,
    ) -> PublishReceipt | None:
        if latest_plan is None:
            return None
        repository = publishing_repository or self._publishing_repository
        if repository is None:
            return None
        try:
            return repository.get_latest_receipt(latest_plan.id)
        except Exception:
            log.exception("查询复盘最近一次发布执行结果失败")
            return None

    def _build_contextual_suggestions(
        self,
        *,
        summary: ReviewSummary,
        project: StoredProject,
        scripts: list[StoredScriptVersion],
        latest_plan: PublishPlan | None,
        latest_receipt: PublishReceipt | None,
    ) -> list[ReviewSuggestion]:
        suggestions: list[ReviewSuggestion] = []
        latest_script = scripts[0] if scripts else None
        current_script_revision = self._current_script_revision(project, latest_script)
        engagement_rate = self._engagement_rate(summary)

        if latest_script is None:
            suggestions.append(
                ReviewSuggestion(
                    id=f"{project.id}:script_baseline",
                    code="script_baseline",
                    category="脚本留存",
                    title="先补齐可复盘脚本基线",
                    description=(
                        f"项目「{project.name}」当前还没有脚本版本，建议先产出可执行脚本，再进入复盘与优化闭环。"
                    ),
                    priority="high",
                )
            )
        else:
            lines = [line.strip() for line in latest_script.content.splitlines() if line.strip()]
            first_line = lines[0] if lines else ""
            if summary.completion_rate < 0.35 or summary.avg_watch_time_sec < 8:
                suggestions.append(
                    ReviewSuggestion(
                        id=f"{project.id}:hook_first_3s",
                        code="hook_first_3s",
                        category="脚本留存",
                        title="强化前三秒钩子",
                        description=(
                            f"当前脚本第 {latest_script.revision} 版的平均观看时长为 {summary.avg_watch_time_sec:.1f} 秒，"
                            f"完播率为 {_format_percent(summary.completion_rate)}，建议重写开场，用结果、冲突或收益点更早抓住用户。"
                        ),
                        priority="high",
                    )
                )
            elif len(first_line) < 12 or len(lines) < 4:
                suggestions.append(
                    ReviewSuggestion(
                        id=f"{project.id}:hook_first_3s",
                        code="hook_first_3s",
                        category="脚本留存",
                        title="补强开场钩子",
                        description=(
                            f"当前脚本第 {latest_script.revision} 版开场信息量偏弱，建议把第一句改成更明确的结果预告或反差提问，"
                            f"避免前 3 秒流失。"
                        ),
                        priority="medium",
                    )
                )

        if summary.total_views > 0 and engagement_rate < 0.05:
            suggestions.append(
                ReviewSuggestion(
                    id=f"{project.id}:interaction_cta",
                    code="interaction_cta",
                    category="互动转化",
                    title="补强互动指令",
                    description=(
                        f"当前累计播放 {summary.total_views}，点赞 {summary.total_likes}，评论 {summary.total_comments}，"
                        f"互动率约为 {_format_percent(engagement_rate)}。建议在脚本结尾补一条更明确的评论或收藏指令。"
                    ),
                    priority="medium",
                )
            )
        elif summary.total_views <= 0:
            suggestions.append(
                ReviewSuggestion(
                    id=f"{project.id}:data_collection",
                    code="data_collection",
                    category="数据回收",
                    title="先补齐首轮数据样本",
                    description=(
                        f"项目「{project.name}」当前还没有可用播放指标，建议先完成一次真实发布或导入真实表现数据，再进行复盘决策。"
                    ),
                    priority="medium",
                )
            )

        if current_script_revision > (project.current_storyboard_version or 0):
            suggestions.append(
                ReviewSuggestion(
                    id=f"{project.id}:storyboard_sync",
                    code="storyboard_sync",
                    category="分镜同步",
                    title="让分镜追上当前脚本版本",
                    description=(
                        f"项目当前脚本已到第 {current_script_revision} 版，但分镜版本仍为 {project.current_storyboard_version}。"
                        f"建议先同步分镜，再继续剪辑和发布。"
                    ),
                    priority="high" if (project.current_storyboard_version or 0) == 0 else "medium",
                )
            )

        if latest_plan is None:
            suggestions.append(
                ReviewSuggestion(
                    id=f"{project.id}:publishing_plan",
                    code="publishing_plan",
                    category="发布闭环",
                    title="建立真实发布闭环",
                    description=(
                        f"项目「{project.name}」尚未创建发布计划。建议先绑定发布计划，再让复盘建议回流到真实执行链路。"
                    ),
                    priority="medium",
                )
            )
        else:
            latest_execution = self._build_latest_execution_result(latest_plan, latest_receipt)
            if latest_execution is not None:
                if latest_execution.status in {"failed", "receipt_failed"}:
                    suggestions.append(
                        ReviewSuggestion(
                            id=f"{project.id}:publishing_repair",
                            code="publishing_repair",
                            category="发布闭环",
                            title="优先处理最近一次执行失败",
                            description=(
                                f"最近执行结果来自发布计划「{latest_plan.title}」，当前状态为 {latest_execution.status}。"
                                f"建议先处理错误后再进入下一轮脚本优化。"
                            ),
                            priority="high",
                        )
                    )
                elif latest_execution.status in {"receipt_pending", "submitted", "submitting"}:
                    suggestions.append(
                        ReviewSuggestion(
                            id=f"{project.id}:publishing_followup",
                            code="publishing_followup",
                            category="发布闭环",
                            title="跟进最近一次发布回执",
                            description=(
                                f"最近执行结果来自发布计划「{latest_plan.title}」，当前仍处于 {latest_execution.status}。"
                                f"建议在回执稳定后再决定是否继续扩大发布或回滚脚本。"
                            ),
                            priority="low",
                        )
                    )
                elif latest_execution.status == "precheck_blocked":
                    suggestions.append(
                        ReviewSuggestion(
                            id=f"{project.id}:publishing_repair",
                            code="publishing_repair",
                            category="发布闭环",
                            title="先清理发布阻断项",
                            description=(
                                f"最近执行结果显示发布计划「{latest_plan.title}」仍有阻断项：{latest_execution.summary}"
                            ),
                            priority="high",
                        )
                    )

        if not suggestions:
            suggestions.append(
                ReviewSuggestion(
                    id=f"{project.id}:next_iteration",
                    code="next_iteration",
                    category="下一轮实验",
                    title="进入下一轮脚本实验",
                    description=(
                        f"项目「{project.name}」当前已具备脚本与发布上下文，建议围绕脚本第 {current_script_revision or 0} 版继续做小步实验。"
                    ),
                    priority="low",
                )
            )

        return suggestions[:4]

    def _get_existing_suggestion_state(self, project_id: str) -> dict[str, ReviewSuggestion]:
        summary = self._repository.get_summary(project_id)
        if summary is None:
            return {}
        suggestions = self._parse_suggestions(summary.suggestions_json)
        return {item.id: item for item in suggestions}

    def _merge_suggestion_state(
        self,
        suggestion: ReviewSuggestion,
        existing: dict[str, ReviewSuggestion],
    ) -> ReviewSuggestion:
        current = existing.get(suggestion.id)
        if current is None:
            return suggestion
        suggestion.adopted = current.adopted
        suggestion.adopted_as_project_id = current.adopted_as_project_id
        suggestion.adopted_at = current.adopted_at
        return suggestion

    def _copy_latest_script_context(
        self,
        *,
        source_project_id: str,
        target_project_id: str,
        script_repository: ScriptRepository,
    ) -> int | None:
        versions = script_repository.list_versions(source_project_id)
        if not versions:
            return None
        latest = versions[0]
        copied = script_repository.save_version(
            target_project_id,
            source=latest.source,
            content=latest.content,
            provider=latest.provider,
            model=latest.model,
            ai_job_id=latest.ai_job_id,
        )
        return copied.revision

    def _copy_latest_storyboard_context(
        self,
        *,
        source_project_id: str,
        target_project_id: str,
        storyboard_repository: StoryboardRepository,
    ) -> int | None:
        versions = storyboard_repository.list_versions(source_project_id)
        if not versions:
            return None
        latest = versions[0]
        copied = storyboard_repository.save_version(
            target_project_id,
            based_on_script_revision=latest.based_on_script_revision,
            source=latest.source,
            scenes=latest.scenes,
            provider=latest.provider,
            model=latest.model,
            ai_job_id=latest.ai_job_id,
        )
        return copied.revision

    def _project_id_from_suggestion_id(self, suggestion_id: str) -> str:
        if ":" not in suggestion_id:
            raise RuntimeHTTPException(
                status_code=400,
                detail="复盘建议标识缺少项目上下文。",
                error_code="review.invalid_suggestion_id",
            )
        project_id, _ = suggestion_id.split(":", 1)
        if not project_id:
            raise RuntimeHTTPException(
                status_code=400,
                detail="复盘建议标识缺少项目上下文。",
                error_code="review.invalid_suggestion_id",
            )
        return project_id

    def _to_dto(
        self,
        summary: ReviewSummary,
        *,
        project: StoredProject,
        scripts: list[StoredScriptVersion],
        latest_plan: PublishPlan | None,
        latest_receipt: PublishReceipt | None,
    ) -> ReviewSummaryDto:
        suggestions = self._parse_suggestions(summary.suggestions_json)
        latest_execution_result = self._build_latest_execution_result(latest_plan, latest_receipt)
        return ReviewSummaryDto(
            id=summary.id,
            project_id=summary.project_id,
            project_name=summary.project_name,
            total_views=summary.total_views,
            total_likes=summary.total_likes,
            total_comments=summary.total_comments,
            avg_watch_time_sec=summary.avg_watch_time_sec,
            completion_rate=summary.completion_rate,
            review_summary=self._build_review_summary(
                summary=summary,
                project=project,
                scripts=scripts,
                latest_execution_result=latest_execution_result,
            ),
            issue_categories=self._build_issue_categories(suggestions),
            feedback_targets=self._build_feedback_targets(
                project=project,
                scripts=scripts,
                latest_plan=latest_plan,
            ),
            latest_execution_result=latest_execution_result,
            suggestions=suggestions,
            last_analyzed_at=summary.last_analyzed_at,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
        )

    def _build_review_summary(
        self,
        *,
        summary: ReviewSummary,
        project: StoredProject,
        scripts: list[StoredScriptVersion],
        latest_execution_result: ReviewLatestExecutionResultDto | None,
    ) -> str:
        latest_script = scripts[0] if scripts else None
        current_script_revision = self._current_script_revision(project, latest_script)
        parts = [f"项目「{project.name}」当前脚本版本为第 {current_script_revision} 版"]
        if project.current_storyboard_version > 0:
            parts.append(f"分镜版本为第 {project.current_storyboard_version} 版")
        else:
            parts.append("尚未形成有效分镜版本")

        if summary.total_views > 0:
            parts.append(
                f"累计播放 {summary.total_views}，平均观看 {summary.avg_watch_time_sec:.1f} 秒，"
                f"完播率 {_format_percent(summary.completion_rate)}"
            )
        else:
            parts.append("当前还没有沉淀可用于复盘的真实播放数据")

        if latest_execution_result is not None:
            parts.append(
                f"最近执行结果来自「{latest_execution_result.title}」，状态为 {latest_execution_result.status}"
            )
        return "；".join(parts) + "。"

    def _build_issue_categories(
        self,
        suggestions: list[ReviewSuggestion],
    ) -> list[ReviewIssueCategoryDto]:
        grouped: dict[str, dict[str, Any]] = {}
        for suggestion in suggestions:
            bucket = grouped.setdefault(
                suggestion.category,
                {
                    "count": 0,
                    "pending_count": 0,
                    "adopted_count": 0,
                    "highest_priority": "low",
                },
            )
            bucket["count"] += 1
            if suggestion.adopted:
                bucket["adopted_count"] += 1
            else:
                bucket["pending_count"] += 1
            if _PRIORITY_RANK.get(suggestion.priority, 0) > _PRIORITY_RANK.get(
                bucket["highest_priority"],
                0,
            ):
                bucket["highest_priority"] = suggestion.priority

        items = [
            ReviewIssueCategoryDto(category=category, **payload)
            for category, payload in grouped.items()
        ]
        items.sort(key=lambda item: (-_PRIORITY_RANK.get(item.highest_priority, 0), -item.count, item.category))
        return items

    def _build_feedback_targets(
        self,
        *,
        project: StoredProject,
        scripts: list[StoredScriptVersion],
        latest_plan: PublishPlan | None,
    ) -> list[ReviewFeedbackTargetDto]:
        targets: list[ReviewFeedbackTargetDto] = []
        latest_script = scripts[0] if scripts else None
        current_script_revision = self._current_script_revision(project, latest_script)
        if current_script_revision > 0:
            targets.append(
                ReviewFeedbackTargetDto(
                    target_type="script_version",
                    target_id=f"{project.id}:{current_script_revision}",
                    title=f"脚本第 {current_script_revision} 版",
                    reason="复盘建议优先回流到当前脚本版本，再决定是否生成新版本。",
                    current_version=current_script_revision,
                    status=latest_script.source if latest_script is not None else None,
                )
            )

        storyboard_version = project.current_storyboard_version or 0
        targets.append(
            ReviewFeedbackTargetDto(
                target_type="storyboard_version",
                target_id=f"{project.id}:storyboard:{storyboard_version or 'missing'}",
                title=(
                    f"分镜第 {storyboard_version} 版" if storyboard_version > 0 else "待创建分镜"
                ),
                reason="脚本改动后需要同步确认分镜和后续剪辑上下文。",
                current_version=storyboard_version or None,
                status="ready" if storyboard_version > 0 else "missing",
            )
        )

        if latest_plan is not None:
            targets.append(
                ReviewFeedbackTargetDto(
                    target_type="publishing_plan",
                    target_id=latest_plan.id,
                    title=latest_plan.title,
                    reason="复盘结果需要与最近一次发布计划和执行结果形成闭环。",
                    status=latest_plan.status,
                )
            )
        else:
            targets.append(
                ReviewFeedbackTargetDto(
                    target_type="publishing_plan",
                    target_id=f"{project.id}:publishing:missing",
                    title="待创建发布计划",
                    reason="当前还没有真实发布计划，无法验证复盘建议的执行结果。",
                    status="missing",
                )
            )

        return targets

    def _build_latest_execution_result(
        self,
        latest_plan: PublishPlan | None,
        latest_receipt: PublishReceipt | None,
    ) -> ReviewLatestExecutionResultDto | None:
        if latest_plan is None:
            return None

        if latest_receipt is not None:
            payload = self._parse_json_object(latest_receipt.platform_response_json)
            return ReviewLatestExecutionResultDto(
                source="publishing",
                plan_id=latest_plan.id,
                title=latest_plan.title,
                status=latest_receipt.status,
                summary=str(payload.get("summary") or _publish_status_summary(latest_receipt.status)),
                scheduled_at=latest_plan.scheduled_at,
                received_at=latest_receipt.received_at,
                error_code=_optional_str(payload.get("errorCode")),
                error_message=_optional_str(payload.get("errorMessage")),
            )

        precheck_payload = self._parse_json_object(latest_plan.precheck_result_json)
        blocking_count = _coerce_int(precheck_payload.get("blockingCount"))
        if blocking_count > 0:
            readiness = precheck_payload.get("readiness")
            error_code = None
            error_message = None
            if isinstance(readiness, dict):
                error_code = _optional_str(readiness.get("error_code") or readiness.get("errorCode"))
                error_message = _optional_str(
                    readiness.get("error_message") or readiness.get("errorMessage")
                )
            summary = f"发布预检未通过，当前存在 {blocking_count} 个阻断项。"
            return ReviewLatestExecutionResultDto(
                source="publishing",
                plan_id=latest_plan.id,
                title=latest_plan.title,
                status="precheck_blocked",
                summary=summary,
                scheduled_at=latest_plan.scheduled_at,
                received_at=None,
                error_code=error_code,
                error_message=error_message,
            )

        return ReviewLatestExecutionResultDto(
            source="publishing",
            plan_id=latest_plan.id,
            title=latest_plan.title,
            status=latest_plan.status,
            summary=_publish_status_summary(latest_plan.status),
            scheduled_at=latest_plan.scheduled_at,
            received_at=None,
            error_code=None,
            error_message=latest_plan.error_message,
        )

    def _parse_suggestions(self, suggestions_json: str | None) -> list[ReviewSuggestion]:
        if not suggestions_json:
            return []
        try:
            items = json.loads(suggestions_json)
        except json.JSONDecodeError:
            log.exception("复盘建议 JSON 解析失败")
            return []
        suggestions: list[ReviewSuggestion] = []
        for item in items:
            if isinstance(item, dict):
                suggestions.append(ReviewSuggestion(**item))
        return suggestions

    def _parse_json_object(self, raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _to_project_dto(self, project: StoredProject) -> ProjectSummaryDto:
        return ProjectSummaryDto(
            id=project.id,
            name=project.name,
            description=project.description,
            status=project.status,
            currentScriptVersion=project.current_script_version,
            currentStoryboardVersion=project.current_storyboard_version,
            createdAt=project.created_at,
            updatedAt=project.updated_at,
            lastAccessedAt=project.last_accessed_at,
        )

    def _to_script_version_dto(self, stored: StoredScriptVersion) -> ScriptVersionDto:
        return ScriptVersionDto(
            revision=stored.revision,
            source=stored.source,
            content=stored.content,
            provider=stored.provider,
            model=stored.model,
            aiJobId=stored.ai_job_id,
            createdAt=stored.created_at,
        )

    def _build_applied_script_content(
        self,
        *,
        latest_content: str,
        suggestion: ReviewSuggestion,
    ) -> str:
        latest_text = latest_content.rstrip()
        review_note = "\n".join(
            [
                "【复盘建议】",
                suggestion.title.strip(),
                suggestion.description.strip(),
            ]
        ).strip()
        if latest_text:
            return f"{latest_text}\n\n{review_note}"
        return review_note

    def _current_script_revision(
        self,
        project: StoredProject,
        latest_script: StoredScriptVersion | None,
    ) -> int:
        return int(latest_script.revision if latest_script is not None else project.current_script_version or 0)

    def _engagement_rate(self, summary: ReviewSummary) -> float:
        if summary.total_views <= 0:
            return 0.0
        return (summary.total_likes + summary.total_comments) / summary.total_views


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def _sortable_datetime(value: datetime | str | None) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if isinstance(value, str) and value.strip():
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.min.replace(tzinfo=UTC)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    return datetime.min.replace(tzinfo=UTC)


def _format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _publish_status_summary(status: str) -> str:
    mapping = {
        "draft": "发布计划仍是草稿，尚未进入执行。",
        "submitting": "发布计划正在提交到平台。",
        "submitted": "发布计划已提交，等待平台处理。",
        "receipt_pending": "平台已接收，等待平台回执确认。",
        "published": "平台已确认发布完成。",
        "failed": "发布执行失败，请处理后重试。",
        "receipt_failed": "平台回执失败，请处理后重试。",
        "cancelled": "发布计划已取消。",
        "precheck_blocked": "发布预检未通过，存在阻断项。",
    }
    return mapping.get(status, "发布链路状态已更新。")
