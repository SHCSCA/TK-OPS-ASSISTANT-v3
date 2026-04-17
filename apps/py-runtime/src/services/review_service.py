from __future__ import annotations

import json
import logging
from uuid import uuid4

from fastapi import HTTPException

from common.time import utc_now
from domain.models.review import ReviewSummary
from repositories.review_repository import ReviewRepository
from repositories.script_repository import ScriptRepository
from schemas.review import (
    AnalyzeProjectResultDto,
    ApplyReviewSuggestionResultDto,
    GenerateReviewSuggestionsResultDto,
    ReviewSuggestion,
    ReviewSuggestionUpdateInput,
    ReviewSummaryDto,
    ReviewSummaryUpdateInput,
)
from services.dashboard_service import DashboardService

log = logging.getLogger(__name__)


class ReviewService:
    def __init__(
        self,
        repository: ReviewRepository,
        dashboard_service: DashboardService,
        script_repository: ScriptRepository,
    ) -> None:
        self._repository = repository
        self._dashboard_service = dashboard_service
        self._script_repository = script_repository

    def get_summary(self, project_id: str) -> ReviewSummaryDto:
        try:
            summary = self._repository.get_summary(project_id)
            if summary is None:
                summary = self._repository.upsert_summary(project_id)
        except Exception as exc:
            log.exception("查询复盘摘要失败")
            raise HTTPException(status_code=500, detail="查询复盘摘要失败") from exc
        return self._to_dto(summary)

    def update_summary(
        self,
        project_id: str,
        payload: ReviewSummaryUpdateInput,
    ) -> ReviewSummaryDto:
        values = payload.model_dump(exclude_unset=True)
        project_name = values.pop("project_name", None)
        try:
            summary = self._repository.upsert_summary(
                project_id,
                project_name=project_name,
                **values,
            )
        except Exception as exc:
            log.exception("更新复盘摘要失败")
            raise HTTPException(status_code=500, detail="更新复盘摘要失败") from exc
        return self._to_dto(summary)

    def analyze(self, project_id: str) -> AnalyzeProjectResultDto:
        result = self.generate_suggestions(project_id)
        try:
            summary = self._repository.mark_analyzed(project_id)
        except Exception as exc:
            log.exception("触发复盘分析失败")
            raise HTTPException(status_code=500, detail="触发复盘分析失败") from exc
        return AnalyzeProjectResultDto(
            project_id=project_id,
            status=result.status,
            message="复盘分析已完成。",
            analyzed_at=summary.last_analyzed_at or utc_now(),
        )

    def get_suggestions(self, project_id: str) -> list[ReviewSuggestion]:
        try:
            summary = self._repository.get_summary(project_id)
        except Exception as exc:
            log.exception("查询复盘建议失败")
            raise HTTPException(status_code=500, detail="查询复盘建议失败") from exc
        if summary is None:
            return []
        return self._parse_suggestions(summary.suggestions_json)

    def generate_suggestions(
        self,
        project_id: str,
    ) -> GenerateReviewSuggestionsResultDto:
        suggestions = self._build_rule_based_suggestions(project_id)
        suggestions_json = json.dumps(
            [item.model_dump(mode="json") for item in suggestions],
            ensure_ascii=False,
        )
        try:
            self._repository.save_suggestions(project_id, suggestions_json)
            summary = self._repository.mark_analyzed(project_id)
        except Exception as exc:
            log.exception("生成复盘建议失败")
            raise HTTPException(status_code=500, detail="生成复盘建议失败") from exc
        generated_at = summary.last_analyzed_at or utc_now()
        return GenerateReviewSuggestionsResultDto(
            project_id=project_id,
            status="done",
            message="复盘建议已生成。",
            generated_count=len(suggestions),
            generated_at=generated_at,
        )

    def update_suggestion(
        self,
        suggestion_id: str,
        payload: ReviewSuggestionUpdateInput,
    ) -> ReviewSuggestion:
        if payload.status not in {"pending", "applied", "dismissed"}:
            raise HTTPException(status_code=409, detail="建议状态不合法")
        project_id, suggestions = self._find_suggestion_owner(suggestion_id)
        updated: ReviewSuggestion | None = None
        new_items: list[ReviewSuggestion] = []
        for item in suggestions:
            if item.id == suggestion_id:
                updated = item.model_copy(update={"status": payload.status})
                new_items.append(updated)
            else:
                new_items.append(item)
        if updated is None:
            raise HTTPException(status_code=404, detail="复盘建议不存在")
        self._persist_suggestions(project_id, new_items)
        return updated

    def apply_suggestion_to_script(self, suggestion_id: str) -> ApplyReviewSuggestionResultDto:
        project_id, suggestions = self._find_suggestion_owner(suggestion_id)
        target: ReviewSuggestion | None = None
        new_items: list[ReviewSuggestion] = []
        for item in suggestions:
            if item.id == suggestion_id:
                target = item.model_copy(update={"status": "applied"})
                new_items.append(target)
            else:
                new_items.append(item)
        if target is None:
            raise HTTPException(status_code=404, detail="复盘建议不存在")

        current_versions = self._script_repository.list_versions(project_id)
        base_content = current_versions[0].content if current_versions else ""
        addition = f"\n\n# 复盘优化建议\n- {target.title}\n- {target.description}"
        stored = self._script_repository.save_version(
            project_id,
            source="review_suggestion",
            content=(base_content + addition).strip(),
        )
        self._dashboard_service.update_project_versions(
            project_id,
            current_script_version=stored.revision,
        )
        self._persist_suggestions(project_id, new_items)
        return ApplyReviewSuggestionResultDto(
            project_id=project_id,
            suggestion_id=suggestion_id,
            script_revision=stored.revision,
            status="applied",
            message="建议已应用到脚本。",
        )

    def _find_suggestion_owner(self, suggestion_id: str) -> tuple[str, list[ReviewSuggestion]]:
        try:
            summaries = self._repository.list_summaries()
        except Exception as exc:
            log.exception("查询复盘建议失败")
            raise HTTPException(status_code=500, detail="查询复盘建议失败") from exc
        for summary in summaries:
            suggestions = self._parse_suggestions(summary.suggestions_json)
            if any(item.id == suggestion_id for item in suggestions):
                return summary.project_id, suggestions
        raise HTTPException(status_code=404, detail="复盘建议不存在")

    def _persist_suggestions(self, project_id: str, suggestions: list[ReviewSuggestion]) -> None:
        suggestions_json = json.dumps(
            [item.model_dump(mode="json") for item in suggestions],
            ensure_ascii=False,
        )
        try:
            self._repository.save_suggestions(project_id, suggestions_json)
        except Exception as exc:
            log.exception("保存复盘建议失败")
            raise HTTPException(status_code=500, detail="保存复盘建议失败") from exc

    def _build_rule_based_suggestions(self, project_id: str) -> list[ReviewSuggestion]:
        return [
            ReviewSuggestion(
                id=str(uuid4()),
                code="hook_first_3s",
                category="内容结构",
                title="强化前三秒钩子",
                description="开头需要更快呈现冲突、结果或强利益点，降低用户划走概率。",
                priority="high",
                status="pending",
                actionLabel="应用到脚本",
                sourceType="script",
                sourceId=project_id,
                createdAt=utc_now(),
            ),
            ReviewSuggestion(
                id=str(uuid4()),
                code="add_subtitle",
                category="可读性",
                title="补齐关键字幕",
                description="为重点句补齐字幕和停顿，提升静音播放时的信息传达。",
                priority="medium",
                status="pending",
                actionLabel="应用到脚本",
                sourceType="subtitle",
                sourceId=project_id,
                createdAt=utc_now(),
            ),
        ]

    def _to_dto(self, summary: ReviewSummary) -> ReviewSummaryDto:
        return ReviewSummaryDto(
            id=summary.id,
            project_id=summary.project_id,
            project_name=summary.project_name,
            total_views=summary.total_views,
            total_likes=summary.total_likes,
            total_comments=summary.total_comments,
            avg_watch_time_sec=summary.avg_watch_time_sec,
            completion_rate=summary.completion_rate,
            suggestions=self._parse_suggestions(summary.suggestions_json),
            last_analyzed_at=summary.last_analyzed_at,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
        )

    def _parse_suggestions(self, suggestions_json: str | None) -> list[ReviewSuggestion]:
        if not suggestions_json:
            return []
        try:
            items = json.loads(suggestions_json)
        except json.JSONDecodeError:
            log.exception("复盘建议 JSON 解析失败")
            return []
        return [ReviewSuggestion(**item) for item in items if isinstance(item, dict)]
