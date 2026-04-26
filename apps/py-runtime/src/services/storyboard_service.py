from __future__ import annotations

import logging
from copy import deepcopy
from uuid import uuid4

from fastapi import HTTPException

from repositories.ai_job_repository import AIJobRepository, StoredAIJobRecord
from repositories.storyboard_repository import StoryboardRepository, StoredStoryboardVersion
from schemas.scripts import AIJobRecordDto
from schemas.storyboards import (
    StoryboardConflictSummaryDto,
    StoryboardDocumentDto,
    StoryboardLastOperationDto,
    StoryboardSceneDto,
    StoryboardShotDto,
    StoryboardShotInput,
    StoryboardShotUpdateInput,
    StoryboardTemplateDto,
    StoryboardVersionDto,
)
from services.ai_text_generation_service import AITextGenerationService
from services.dashboard_service import DashboardService
from services.script_document_json import (
    build_storyboard_scenes_from_json,
    parse_storyboard_document_json,
)
from services.script_service import ScriptService
from services.storyboard_scene_parser import parse_storyboard_scenes

log = logging.getLogger(__name__)


class StoryboardService:
    def __init__(
        self,
        dashboard_service: DashboardService,
        repository: StoryboardRepository,
        ai_job_repository: AIJobRepository,
        ai_text_generation_service: AITextGenerationService,
        script_service: ScriptService,
    ) -> None:
        self._dashboard_service = dashboard_service
        self._repository = repository
        self._ai_job_repository = ai_job_repository
        self._ai_text_generation_service = ai_text_generation_service
        self._script_service = script_service

    def get_document(self, project_id: str) -> StoryboardDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        versions = self._repository.list_versions(project_id)
        version_dtos = [self._to_version_dto(item) for item in versions]
        recent_jobs = [
            self._to_job_dto(item)
            for item in self._ai_job_repository.list_recent(
                project_id=project_id,
                capability_ids=('storyboard_generation',),
            )
        ]
        current_version = version_dtos[0] if version_dtos else None
        current_script_revision = project.currentScriptVersion
        based_on_script_revision = (
            current_version.basedOnScriptRevision if current_version else current_script_revision
        )
        latest_ai_job = recent_jobs[0] if recent_jobs else None
        job_by_id = {item.id: item for item in recent_jobs}
        sync_status, conflict_summary = self._build_sync_state(
            current_version=current_version,
            current_script_revision=current_script_revision,
        )
        return StoryboardDocumentDto(
            projectId=project.id,
            basedOnScriptRevision=based_on_script_revision,
            currentScriptRevision=current_script_revision,
            currentVersion=current_version,
            versions=version_dtos,
            recentJobs=recent_jobs,
            syncStatus=sync_status,
            conflictSummary=conflict_summary,
            latestAiJob=latest_ai_job,
            lastOperation=self._to_last_operation_dto(current_version, job_by_id),
        )

    def save_document(
        self,
        project_id: str,
        *,
        based_on_script_revision: int,
        scenes: list[dict[str, str]],
        markdown: str | None = None,
        storyboard_json: dict[str, object] | None = None,
    ) -> StoryboardDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        normalized_markdown = markdown.strip() if markdown else None
        scenes_to_save = (
            build_storyboard_scenes_from_json(storyboard_json)
            if storyboard_json is not None
            else _manual_markdown_to_scenes(normalized_markdown, scenes)
        )
        stored = self._repository.save_version(
            project.id,
            based_on_script_revision=based_on_script_revision,
            source='manual',
            scenes=scenes_to_save,
            markdown=normalized_markdown,
            format='json_v1' if storyboard_json is not None else 'legacy_markdown',
            storyboard_json=storyboard_json,
        )
        self._dashboard_service.update_project_versions(
            project.id,
            current_storyboard_version=stored.revision,
        )
        return self.get_document(project.id)

    def list_templates(self) -> list[StoryboardTemplateDto]:
        return [
            StoryboardTemplateDto(
                id='hook-problem-solution',
                name='钩子-问题-解决',
                description='适合短视频创作的基础三段式分镜模板。',
                shots=[
                    StoryboardShotDto(
                        sceneId='shot-1',
                        title='开场钩子',
                        summary='快速抛出冲突或吸引点。',
                        visualPrompt='强节奏开场，镜头推进。',
                    ),
                    StoryboardShotDto(
                        sceneId='shot-2',
                        title='问题展开',
                        summary='明确展示用户痛点。',
                        visualPrompt='生活化场景，突出问题细节。',
                    ),
                    StoryboardShotDto(
                        sceneId='shot-3',
                        title='方案收束',
                        summary='给出解决方式和行动引导。',
                        visualPrompt='产品或结果画面清晰收束。',
                    ),
                ],
            ),
            StoryboardTemplateDto(
                id='before-after-proof',
                name='前后对比-证明',
                description='适合演示改造效果、增长结果或效率提升。',
                shots=[
                    StoryboardShotDto(
                        sceneId='shot-1',
                        title='前态',
                        summary='先展示旧状态。',
                        visualPrompt='对比感强的静态场景。',
                    ),
                    StoryboardShotDto(
                        sceneId='shot-2',
                        title='变化过程',
                        summary='展示变化的关键步骤。',
                        visualPrompt='中景推进，强调转变。',
                    ),
                    StoryboardShotDto(
                        sceneId='shot-3',
                        title='后态',
                        summary='给出结果与收益。',
                        visualPrompt='明亮收束画面，突出结果。',
                    ),
                ],
            ),
        ]

    def sync_from_script(self, project_id: str) -> StoryboardDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        script_document = self._script_service.get_document(project.id)
        if script_document.currentVersion is None:
            raise HTTPException(status_code=400, detail='请先创建脚本版本，再同步分镜。')

        scenes = _script_to_shots(
            script_document.currentVersion.content,
            script_document.currentVersion.documentJson,
        )
        stored = self._repository.save_version(
            project.id,
            based_on_script_revision=script_document.currentVersion.revision,
            source='sync_from_script',
            scenes=scenes,
        )
        self._dashboard_service.update_project_versions(
            project.id,
            current_storyboard_version=stored.revision,
        )
        return self.get_document(project.id)

    def create_shot(self, project_id: str, payload: StoryboardShotInput) -> StoryboardDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        current_version = self._get_current_version(project.id)
        shots = self._current_shots(current_version)
        shots.append(
            {
                'sceneId': uuid4().hex,
                'title': payload.title.strip(),
                'summary': payload.summary.strip(),
                'visualPrompt': payload.visualPrompt.strip(),
            }
        )
        return self._save_shots(project.id, current_version, shots, source='shot_create')

    def update_shot(
        self,
        project_id: str,
        shot_id: str,
        payload: StoryboardShotUpdateInput,
    ) -> StoryboardDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        current_version = self._get_current_version(project.id)
        shots = self._current_shots(current_version)
        shot = self._find_shot(shots, shot_id)
        if shot is None:
            raise HTTPException(status_code=404, detail='镜头不存在。')
        if payload.title is not None:
            shot['title'] = payload.title.strip()
        if payload.summary is not None:
            shot['summary'] = payload.summary.strip()
        if payload.visualPrompt is not None:
            shot['visualPrompt'] = payload.visualPrompt.strip()
        return self._save_shots(project.id, current_version, shots, source='shot_update')

    def delete_shot(self, project_id: str, shot_id: str) -> StoryboardDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        current_version = self._get_current_version(project.id)
        shots = self._current_shots(current_version)
        filtered = [item for item in shots if item.get('sceneId') != shot_id]
        if len(filtered) == len(shots):
            raise HTTPException(status_code=404, detail='镜头不存在。')
        return self._save_shots(project.id, current_version, filtered, source='shot_delete')

    def generate(self, project_id: str, *, request_id: str | None = None) -> StoryboardDocumentDto:
        return self.generate_with_service(
            project_id,
            ai_text_generation_service=self._ai_text_generation_service,
            request_id=request_id,
        )

    def generate_with_service(
        self,
        project_id: str,
        *,
        ai_text_generation_service,
        request_id: str | None = None,
    ) -> StoryboardDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        script_document = self._script_service.get_document(project.id)
        if script_document.currentVersion is None:
            raise HTTPException(status_code=400, detail='请先创建脚本版本，再生成分镜。')

        result = ai_text_generation_service.generate_text(
            'storyboard_generation',
            {'script': _script_source_for_storyboard(script_document.currentVersion)},
            project_id=project.id,
            request_id=request_id,
        )
        storyboard_json = parse_storyboard_document_json(result.text)
        scenes = build_storyboard_scenes_from_json(storyboard_json)
        stored = self._repository.save_version(
            project.id,
            based_on_script_revision=script_document.currentVersion.revision,
            source='ai_generate',
            scenes=scenes,
            markdown=None,
            format='json_v1',
            storyboard_json=storyboard_json,
            provider=result.provider,
            model=result.model,
            ai_job_id=result.ai_job_id,
        )
        self._dashboard_service.update_project_versions(
            project.id,
            current_storyboard_version=stored.revision,
        )
        return self.get_document(project.id)

    def _to_version_dto(self, stored: StoredStoryboardVersion) -> StoryboardVersionDto:
        return StoryboardVersionDto(
            revision=stored.revision,
            basedOnScriptRevision=stored.based_on_script_revision,
            source=stored.source,
            scenes=[StoryboardSceneDto.model_validate(item) for item in stored.scenes],
            markdown=stored.markdown,
            format=stored.format if stored.format in {'json_v1', 'legacy_markdown'} else 'legacy_markdown',
            storyboardJson=stored.storyboard_json,
            provider=stored.provider,
            model=stored.model,
            aiJobId=stored.ai_job_id,
            createdAt=stored.created_at,
        )

    def _to_job_dto(self, stored: StoredAIJobRecord) -> AIJobRecordDto:
        return AIJobRecordDto(
            id=stored.id,
            capabilityId=stored.capability_id,
            provider=stored.provider,
            model=stored.model,
            status=stored.status,
            error=stored.error,
            durationMs=stored.duration_ms,
            createdAt=stored.created_at,
            completedAt=stored.completed_at,
        )

    def _to_last_operation_dto(
        self,
        current_version: StoryboardVersionDto | None,
        job_by_id: dict[str, AIJobRecordDto],
    ) -> StoryboardLastOperationDto | None:
        if current_version is None:
            return None

        ai_job = (
            job_by_id.get(current_version.aiJobId)
            if current_version.aiJobId is not None
            else None
        )
        return StoryboardLastOperationDto(
            revision=current_version.revision,
            source=current_version.source,
            createdAt=current_version.createdAt,
            aiJobId=current_version.aiJobId,
            aiJobStatus=ai_job.status if ai_job is not None else None,
        )

    def _build_sync_state(
        self,
        *,
        current_version: StoryboardVersionDto | None,
        current_script_revision: int,
    ) -> tuple[str, StoryboardConflictSummaryDto]:
        if current_script_revision <= 0:
            return (
                'missing_script',
                StoryboardConflictSummaryDto(
                    hasConflict=False,
                    reason='当前项目还没有脚本版本，暂时无法同步分镜。',
                    currentScriptRevision=current_script_revision,
                    basedOnScriptRevision=current_version.basedOnScriptRevision if current_version else None,
                    storyboardRevision=current_version.revision if current_version else None,
                ),
            )

        if current_version is None:
            return (
                'missing_storyboard',
                StoryboardConflictSummaryDto(
                    hasConflict=False,
                    reason='当前项目还没有分镜版本，可以从脚本同步生成。',
                    currentScriptRevision=current_script_revision,
                    basedOnScriptRevision=None,
                    storyboardRevision=None,
                ),
            )

        if current_version.basedOnScriptRevision == current_script_revision:
            return (
                'synced',
                StoryboardConflictSummaryDto(
                    hasConflict=False,
                    reason=None,
                    currentScriptRevision=current_script_revision,
                    basedOnScriptRevision=current_version.basedOnScriptRevision,
                    storyboardRevision=current_version.revision,
                ),
            )

        if current_version.basedOnScriptRevision < current_script_revision:
            return (
                'outdated',
                StoryboardConflictSummaryDto(
                    hasConflict=True,
                    reason='当前分镜基于旧脚本版本，建议先重新同步再继续编辑。',
                    currentScriptRevision=current_script_revision,
                    basedOnScriptRevision=current_version.basedOnScriptRevision,
                    storyboardRevision=current_version.revision,
                ),
            )

        return (
            'conflict',
            StoryboardConflictSummaryDto(
                hasConflict=True,
                reason='当前分镜引用的脚本版本高于项目当前脚本版本，请检查版本恢复链路。',
                currentScriptRevision=current_script_revision,
                basedOnScriptRevision=current_version.basedOnScriptRevision,
                storyboardRevision=current_version.revision,
            ),
        )

    def _get_current_version(self, project_id: str) -> StoredStoryboardVersion | None:
        versions = self._repository.list_versions(project_id)
        return versions[0] if versions else None

    def _current_shots(self, version: StoredStoryboardVersion | None) -> list[dict[str, str]]:
        if version is None:
            return []
        return deepcopy(version.scenes)

    def _find_shot(self, shots: list[dict[str, str]], shot_id: str) -> dict[str, str] | None:
        for shot in shots:
            if str(shot.get('sceneId')) == shot_id:
                return shot
        return None

    def _save_shots(
        self,
        project_id: str,
        current_version: StoredStoryboardVersion | None,
        shots: list[dict[str, str]],
        *,
        source: str,
    ) -> StoryboardDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        based_on_script_revision = (
            current_version.based_on_script_revision
            if current_version is not None
            else project.current_script_version
        )
        stored = self._repository.save_version(
            project_id,
            based_on_script_revision=based_on_script_revision,
            source=source,
            scenes=shots,
        )
        self._dashboard_service.update_project_versions(
            project_id,
            current_storyboard_version=stored.revision,
        )
        return self.get_document(project_id)


def _script_to_shots(
    script_content: str,
    document_json: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    if document_json is not None:
        scenes = _script_json_to_shots(document_json)
        if scenes:
            return scenes

    paragraphs = [
        line.strip()
        for line in script_content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        if line.strip()
    ]
    return [
        {
            'sceneId': f'shot-{index}',
            'title': paragraph[:24] or f'镜头 {index}',
            'summary': paragraph,
            'visualPrompt': paragraph,
        }
        for index, paragraph in enumerate(paragraphs, start=1)
    ]


def _script_json_to_shots(document_json: dict[str, object]) -> list[dict[str, str]]:
    segments = document_json.get('segments')
    if not isinstance(segments, list):
        return []

    scenes: list[dict[str, str]] = []
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            continue
        segment_id = str(segment.get('segmentId') or f'S{index:02d}').strip()
        voiceover = str(segment.get('voiceover') or '').strip()
        subtitle = str(segment.get('subtitle') or '').strip()
        visual = str(segment.get('visualSuggestion') or '').strip()
        title = f'{segment_id} · {str(segment.get("goal") or "脚本段落").strip()}'
        summary = visual or voiceover or subtitle or title
        scenes.append(
            {
                'sceneId': f'SH{index:02d}',
                'title': title,
                'summary': summary,
                'visualPrompt': str(segment.get('storyboardHint') or summary).strip(),
                'shotLabel': segment_id,
                'time': str(segment.get('time') or '').strip(),
                'subtitle': subtitle,
                'voiceover': voiceover,
                'visualContent': visual,
            }
        )
    return scenes


def _script_source_for_storyboard(version: object) -> str:
    document_json = getattr(version, 'documentJson', None)
    if document_json is not None:
        import json

        return json.dumps(document_json, ensure_ascii=False)
    return str(getattr(version, 'content', ''))


def _manual_markdown_to_scenes(
    markdown: str | None,
    fallback_scenes: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not markdown:
        return fallback_scenes

    try:
        parsed = parse_storyboard_scenes(markdown)
    except HTTPException:
        log.exception('手动保存分镜 Markdown 解析失败，已使用兜底分镜结构。')
        return fallback_scenes or [_fallback_scene_from_markdown(markdown)]
    return parsed or fallback_scenes or [_fallback_scene_from_markdown(markdown)]


def _provider_markdown_to_scenes(markdown: str) -> list[dict[str, str]]:
    normalized_markdown = markdown.strip()
    if not normalized_markdown:
        raise HTTPException(status_code=502, detail='分镜 Provider 未返回有效 Markdown。')

    try:
        parsed = parse_storyboard_scenes(normalized_markdown)
    except HTTPException:
        log.exception('分镜 Provider 返回 Markdown 但无法解析镜头，已保留原文并使用兜底分镜。')
        return [_fallback_scene_from_markdown(normalized_markdown)]
    return parsed or [_fallback_scene_from_markdown(normalized_markdown)]


def _fallback_scene_from_markdown(markdown: str) -> dict[str, str]:
    first_line = next((line.strip() for line in markdown.splitlines() if line.strip()), '手动分镜')
    return {
        'sceneId': uuid4().hex,
        'title': first_line[:32],
        'summary': markdown[:500],
        'visualPrompt': markdown[:500],
    }
