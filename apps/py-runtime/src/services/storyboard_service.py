from __future__ import annotations

import json
from uuid import uuid4

from fastapi import HTTPException

from repositories.ai_job_repository import AIJobRepository, StoredAIJobRecord
from repositories.storyboard_repository import StoryboardRepository, StoredStoryboardVersion
from schemas.scripts import AIJobRecordDto
from schemas.storyboards import StoryboardDocumentDto, StoryboardSceneDto, StoryboardVersionDto
from services.ai_text_generation_service import AITextGenerationService
from services.dashboard_service import DashboardService
from services.script_service import ScriptService


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
        based_on_script_revision = versions[0].based_on_script_revision if versions else project.currentScriptVersion
        return StoryboardDocumentDto(
            projectId=project.id,
            basedOnScriptRevision=based_on_script_revision,
            currentVersion=self._to_version_dto(versions[0]) if versions else None,
            versions=[self._to_version_dto(item) for item in versions],
            recentJobs=[
                self._to_job_dto(item)
                for item in self._ai_job_repository.list_recent(
                    project_id=project_id,
                    capability_ids=('storyboard_generation',),
                )
            ],
        )

    def save_document(
        self,
        project_id: str,
        *,
        based_on_script_revision: int,
        scenes: list[dict[str, str]],
    ) -> StoryboardDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        stored = self._repository.save_version(
            project.id,
            based_on_script_revision=based_on_script_revision,
            source='manual',
            scenes=scenes,
        )
        self._dashboard_service.update_project_versions(
            project.id,
            current_storyboard_version=stored.revision,
        )
        return self.get_document(project.id)

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
            raise HTTPException(status_code=400, detail='Cannot generate a storyboard without a script.')

        result = ai_text_generation_service.generate_text(
            'storyboard_generation',
            {'script': script_document.currentVersion.content},
            project_id=project.id,
            request_id=request_id,
        )
        scenes = _parse_scenes(result.text)
        stored = self._repository.save_version(
            project.id,
            based_on_script_revision=script_document.currentVersion.revision,
            source='ai_generate',
            scenes=scenes,
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


def _parse_scenes(raw_text: str) -> list[dict[str, str]]:
    normalized = raw_text.strip()
    if normalized.startswith('```'):
        normalized = normalized.strip('`')
        if normalized.startswith('json'):
            normalized = normalized[4:].strip()
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail='Storyboard provider returned invalid JSON.') from exc

    if not isinstance(payload, list) or not payload:
        raise HTTPException(status_code=502, detail='Storyboard provider returned no scenes.')

    scenes: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        scenes.append(
            {
                'sceneId': str(item.get('sceneId') or uuid4().hex),
                'title': str(item.get('title') or 'Untitled Scene'),
                'summary': str(item.get('summary') or ''),
                'visualPrompt': str(item.get('visualPrompt') or ''),
            }
        )

    if not scenes:
        raise HTTPException(status_code=502, detail='Storyboard provider returned empty scenes.')
    return scenes
