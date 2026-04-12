from __future__ import annotations

from fastapi import HTTPException

from repositories.ai_job_repository import AIJobRepository, StoredAIJobRecord
from repositories.script_repository import ScriptRepository, StoredScriptVersion
from schemas.scripts import ScriptDocumentDto, ScriptVersionDto, AIJobRecordDto
from services.ai_text_generation_service import AITextGenerationService
from services.dashboard_service import DashboardService


class ScriptService:
    def __init__(
        self,
        dashboard_service: DashboardService,
        repository: ScriptRepository,
        ai_job_repository: AIJobRepository,
        ai_text_generation_service: AITextGenerationService,
    ) -> None:
        self._dashboard_service = dashboard_service
        self._repository = repository
        self._ai_job_repository = ai_job_repository
        self._ai_text_generation_service = ai_text_generation_service

    def get_document(self, project_id: str) -> ScriptDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        versions = self._repository.list_versions(project_id)
        return ScriptDocumentDto(
            projectId=project.id,
            currentVersion=self._to_version_dto(versions[0]) if versions else None,
            versions=[self._to_version_dto(item) for item in versions],
            recentJobs=[
                self._to_job_dto(item)
                for item in self._ai_job_repository.list_recent(
                    project_id=project_id,
                    capability_ids=('script_generation', 'script_rewrite'),
                )
            ],
        )

    def save_document(self, project_id: str, content: str) -> ScriptDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        stored = self._repository.save_version(
            project.id,
            source='manual',
            content=content.strip(),
        )
        self._dashboard_service.update_project_versions(
            project.id,
            current_script_version=stored.revision,
        )
        return self.get_document(project.id)

    def generate(self, project_id: str, topic: str, *, request_id: str | None = None) -> ScriptDocumentDto:
        return self.generate_with_service(
            project_id,
            topic,
            ai_text_generation_service=self._ai_text_generation_service,
            request_id=request_id,
        )

    def generate_with_service(
        self,
        project_id: str,
        topic: str,
        *,
        ai_text_generation_service,
        request_id: str | None = None,
    ) -> ScriptDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        result = ai_text_generation_service.generate_text(
            'script_generation',
            {'topic': topic.strip()},
            project_id=project.id,
            request_id=request_id,
        )
        stored = self._repository.save_version(
            project.id,
            source='ai_generate',
            content=result.text,
            provider=result.provider,
            model=result.model,
            ai_job_id=result.ai_job_id,
        )
        self._dashboard_service.update_project_versions(
            project.id,
            current_script_version=stored.revision,
        )
        return self.get_document(project.id)

    def rewrite(
        self,
        project_id: str,
        instructions: str,
        *,
        request_id: str | None = None,
    ) -> ScriptDocumentDto:
        return self.rewrite_with_service(
            project_id,
            instructions,
            ai_text_generation_service=self._ai_text_generation_service,
            request_id=request_id,
        )

    def rewrite_with_service(
        self,
        project_id: str,
        instructions: str,
        *,
        ai_text_generation_service,
        request_id: str | None = None,
    ) -> ScriptDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        versions = self._repository.list_versions(project.id)
        if not versions:
            raise HTTPException(status_code=400, detail='请先创建脚本版本，再执行改写。')

        result = ai_text_generation_service.generate_text(
            'script_rewrite',
            {
                'script': versions[0].content,
                'instructions': instructions.strip(),
            },
            project_id=project.id,
            request_id=request_id,
        )
        stored = self._repository.save_version(
            project.id,
            source='ai_rewrite',
            content=result.text,
            provider=result.provider,
            model=result.model,
            ai_job_id=result.ai_job_id,
        )
        self._dashboard_service.update_project_versions(
            project.id,
            current_script_version=stored.revision,
        )
        return self.get_document(project.id)

    def _to_version_dto(self, stored: StoredScriptVersion) -> ScriptVersionDto:
        return ScriptVersionDto(
            revision=stored.revision,
            source=stored.source,
            content=stored.content,
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
