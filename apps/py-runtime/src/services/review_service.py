from __future__ import annotations

import json
import logging

from fastapi import HTTPException

from common.time import utc_now
from domain.models.review import ReviewSummary
from repositories.dashboard_repository import DashboardRepository, StoredProject
from repositories.review_repository import ReviewRepository
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from schemas.dashboard import ProjectSummaryDto
from schemas.review import (
    AnalyzeProjectResultDto,
    ReviewSuggestion,
    ReviewSummaryDto,
    ReviewSummaryUpdateInput,
)

log = logging.getLogger(__name__)


class ReviewService:
    def __init__(
        self,
        repository: ReviewRepository,
        *,
        dashboard_repository: DashboardRepository | None = None,
        script_repository: ScriptRepository | None = None,
        storyboard_repository: StoryboardRepository | None = None,
    ) -> None:
        self._repository = repository
        self._dashboard_repository = dashboard_repository
        self._script_repository = script_repository
        self._storyboard_repository = storyboard_repository

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
        existing = self._get_existing_suggestion_state(project_id)
        suggestions = [
            ReviewSuggestion(
                id=f"{project_id}:hook_first_3s",
                code="hook_first_3s",
                category="内容结构",
                title="提高前 3 秒钩子",
                description="开头需要更快呈现冲突、结果或强利益点，降低用户划走概率。",
                priority="high",
            ),
            ReviewSuggestion(
                id=f"{project_id}:add_subtitle",
                code="add_subtitle",
                category="可读性",
                title="增加字幕",
                description="为关键信息和口播补齐字幕，提升静音播放场景下的理解效率。",
                priority="medium",
            ),
            ReviewSuggestion(
                id=f"{project_id}:cover_optimization",
                code="cover_optimization",
                category="点击率",
                title="优化封面",
                description="封面应突出主体、结果和关键词，避免信息层级分散。",
                priority="low",
            ),
        ]
        suggestions = [self._merge_suggestion_state(item, existing) for item in suggestions]
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
        return AnalyzeProjectResultDto(
            project_id=project_id,
            status="done",
            message="复盘分析已完成",
            analyzed_at=summary.last_analyzed_at or utc_now(),
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
            raise HTTPException(status_code=500, detail="复盘采纳缺少项目存储依赖")
        if script_repository is None or storyboard_repository is None:
            raise HTTPException(status_code=500, detail="复盘采纳缺少上下文复制依赖")

        summary = self._get_summary_model(source_project_id)
        suggestions = self._parse_suggestions(summary.suggestions_json)
        suggestion = next((item for item in suggestions if item.id == suggestion_id), None)
        if suggestion is None:
            raise HTTPException(status_code=404, detail="复盘建议不存在")

        child_name = f"{summary.project_name or source_project_id} - {suggestion.title}"
        child_description = f"由复盘建议 {suggestion.code} 采纳生成的子项目"
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

    def _get_summary_model(self, project_id: str) -> ReviewSummary:
        try:
            summary = self._repository.get_summary(project_id)
            if summary is None:
                summary = self._repository.upsert_summary(project_id)
        except Exception as exc:
            log.exception("查询复盘摘要失败")
            raise HTTPException(status_code=500, detail="查询复盘摘要失败") from exc
        return summary

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
            raise HTTPException(status_code=400, detail="复盘建议标识缺少项目上下文")
        project_id, _ = suggestion_id.split(":", 1)
        if not project_id:
            raise HTTPException(status_code=400, detail="复盘建议标识缺少项目上下文")
        return project_id

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
        suggestions: list[ReviewSuggestion] = []
        for item in items:
            if isinstance(item, dict):
                suggestions.append(ReviewSuggestion(**item))
        return suggestions

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
