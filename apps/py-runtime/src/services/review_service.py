from __future__ import annotations

import json
import logging

from fastapi import HTTPException

from common.time import utc_now
from domain.models.review import ReviewSummary
from repositories.review_repository import ReviewRepository
from schemas.review import (
    AnalyzeProjectResultDto,
    ReviewSuggestion,
    ReviewSummaryDto,
    ReviewSummaryUpdateInput,
)

log = logging.getLogger(__name__)


class ReviewService:
    def __init__(self, repository: ReviewRepository) -> None:
        self._repository = repository

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
        suggestions = [
            ReviewSuggestion(
                code="hook_first_3s",
                category="内容结构",
                title="提高前3秒钩子",
                description="开头需要更快呈现冲突、结果或强利益点，降低用户划走概率。",
                priority="high",
            ),
            ReviewSuggestion(
                code="add_subtitle",
                category="可读性",
                title="增加字幕",
                description="为关键口播与信息点补齐字幕，提升静音播放场景下的理解效率。",
                priority="medium",
            ),
            ReviewSuggestion(
                code="cover_optimization",
                category="点击率",
                title="优化封面",
                description="封面应突出主体、结果和关键词，避免信息层级分散。",
                priority="low",
            ),
        ]
        suggestions_json = json.dumps(
            [item.model_dump(mode="json") for item in suggestions],
            ensure_ascii=False,
        )
        try:
            self._repository.save_suggestions(project_id, suggestions_json)
            summary = self._repository.mark_analyzed(project_id)
        except Exception as exc:
            log.exception("触发复盘分析失败")
            raise HTTPException(status_code=500, detail="触发复盘分析失败") from exc
        return AnalyzeProjectResultDto(
            project_id=project_id,
            status="done",
            message="复盘分析已完成",
            analyzed_at=summary.last_analyzed_at or utc_now(),
        )

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
