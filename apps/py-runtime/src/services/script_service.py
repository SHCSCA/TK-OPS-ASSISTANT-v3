from __future__ import annotations

import asyncio
from fastapi import HTTPException

from repositories.ai_job_repository import AIJobRepository, StoredAIJobRecord
from repositories.prompt_template_repository import PromptTemplateRepository
from repositories.script_repository import ScriptRepository, StoredScriptVersion
from schemas.scripts import (
    AIJobRecordDto,
    ScriptDocumentDto,
    ScriptSegmentRewriteInput,
    ScriptTitleVariantDto,
    ScriptVersionDto,
)
from services.ai_text_generation_service import AITextGenerationService
from services.dashboard_service import DashboardService
from services.ws_manager import ws_manager


class ScriptService:
    def __init__(
        self,
        dashboard_service: DashboardService,
        repository: ScriptRepository,
        ai_job_repository: AIJobRepository,
        ai_text_generation_service: AITextGenerationService,
        prompt_template_repository: PromptTemplateRepository,
    ) -> None:
        self._dashboard_service = dashboard_service
        self._repository = repository
        self._ai_job_repository = ai_job_repository
        self._ai_text_generation_service = ai_text_generation_service
        self._prompt_template_repository = prompt_template_repository

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

    def list_versions(self, project_id: str) -> list[ScriptVersionDto]:
        self._dashboard_service.require_project(project_id)
        return [
            self._to_version_dto(item)
            for item in self._repository.list_versions(project_id)
        ]

    def get_version(self, project_id: str, revision: int) -> StoredScriptVersion:
        self._dashboard_service.require_project(project_id)
        version = self._repository.get_version(project_id, revision)
        if version is None:
            raise HTTPException(status_code=404, detail='脚本版本不存在')
        return version

    def restore_version(self, project_id: str, revision: int) -> ScriptDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        source_version = self.get_version(project.id, revision)
        stored = self._repository.save_version(
            project.id,
            source='restore',
            content=source_version.content,
        )
        self._dashboard_service.update_project_versions(
            project.id,
            current_script_version=stored.revision,
        )
        return self.get_document(project.id)

    def generate_title_variants(
        self,
        project_id: str,
        topic: str,
        count: int,
        *,
        ai_text_generation_service=None,
        request_id: str | None = None,
    ) -> list[ScriptTitleVariantDto]:
        project = self._dashboard_service.require_project(project_id)
        service = ai_text_generation_service or self._ai_text_generation_service
        result = service.generate_text(
            'script_generation',
            {'topic': topic.strip(), 'count': str(count), 'mode': 'title_variants'},
            project_id=project.id,
            request_id=request_id,
        )
        titles = _parse_title_variants(result.text, count)
        return [ScriptTitleVariantDto(title=item) for item in titles]

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
        _emit_script_stream_event(
            'script.ai.stream.chunk',
            jobId=result.ai_job_id,
            sequence=1,
            deltaText=result.text,
            versionId=str(stored.revision),
        )
        _emit_script_stream_event(
            'script.ai.stream.completed',
            jobId=result.ai_job_id,
            fullText=stored.content,
            versionId=str(stored.revision),
        )
        return self.get_document(project.id)

    def rewrite_segment(
        self,
        project_id: str,
        segment_id: str,
        payload: ScriptSegmentRewriteInput,
        *,
        ai_text_generation_service=None,
        request_id: str | None = None,
    ) -> ScriptDocumentDto:
        project = self._dashboard_service.require_project(project_id)
        versions = self._repository.list_versions(project.id)
        if not versions:
            raise HTTPException(status_code=400, detail='请先创建脚本版本，再执行段落改写。')

        segment_index = _parse_segment_index(segment_id)
        latest_lines = _split_lines(versions[0].content)
        if segment_index < 1 or segment_index > len(latest_lines):
            raise HTTPException(status_code=404, detail='未找到对应的脚本段落。')

        prompt_template = None
        if payload.promptTemplateId:
            prompt_template = self._prompt_template_repository.get_template(payload.promptTemplateId)
            if prompt_template is None:
                raise HTTPException(status_code=404, detail='Prompt 模板不存在')

        prompt_variables = {
            'script': versions[0].content,
            'segment': latest_lines[segment_index - 1],
            'segmentIndex': str(segment_index),
            'instructions': payload.instructions.strip(),
        }
        if prompt_template is not None:
            prompt_variables['promptTemplate'] = prompt_template.content

        service = ai_text_generation_service or self._ai_text_generation_service
        result = service.generate_text(
            'script_rewrite',
            prompt_variables,
            project_id=project.id,
            request_id=request_id,
        )

        rewritten_lines = list(latest_lines)
        rewritten_lines[segment_index - 1] = _pick_segment_rewrite(result.text, segment_index)
        stored = self._repository.save_version(
            project.id,
            source='ai_segment_rewrite',
            content='\n'.join(rewritten_lines).strip(),
            provider=result.provider,
            model=result.model,
            ai_job_id=result.ai_job_id,
        )
        self._dashboard_service.update_project_versions(
            project.id,
            current_script_version=stored.revision,
        )
        _emit_script_stream_event(
            'script.ai.stream.chunk',
            jobId=result.ai_job_id,
            sequence=1,
            deltaText=result.text,
            versionId=str(stored.revision),
        )
        _emit_script_stream_event(
            'script.ai.stream.completed',
            jobId=result.ai_job_id,
            fullText=stored.content,
            versionId=str(stored.revision),
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


def _parse_segment_index(segment_id: str) -> int:
    normalized = segment_id.strip()
    if not normalized.isdigit():
        raise HTTPException(status_code=400, detail='脚本段落编号必须是正整数。')
    return int(normalized)


def _split_lines(content: str) -> list[str]:
    return [line for line in content.replace('\r\n', '\n').replace('\r', '\n').split('\n')]


def _pick_segment_rewrite(raw_text: str, segment_index: int) -> str:
    lines = [line.strip() for line in raw_text.replace('\r\n', '\n').replace('\r', '\n').split('\n') if line.strip()]
    if not lines:
        return raw_text.strip()
    if len(lines) >= segment_index:
        return lines[segment_index - 1]
    return lines[-1]


def _parse_title_variants(raw_text: str, expected_count: int) -> list[str]:
    normalized = raw_text.strip()
    if normalized.startswith('```'):
        normalized = normalized.strip('`')
        if normalized.startswith('json'):
            normalized = normalized[4:].strip()

    try:
        import json

        payload = json.loads(normalized)
    except Exception:
        payload = None

    titles: list[str] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, str) and item.strip():
                titles.append(item.strip())
            elif isinstance(item, dict):
                title = str(item.get('title') or '').strip()
                if title:
                    titles.append(title)
    else:
        titles = [line.strip() for line in normalized.splitlines() if line.strip()]

    if len(titles) < expected_count:
        raise HTTPException(status_code=502, detail='标题变体 Provider 返回结果不足。')
    return titles[:expected_count]


def _emit_script_stream_event(event_type: str, **payload: object) -> None:
    message = {
        'type': event_type,
        **payload,
    }
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(ws_manager.broadcast(message))
    else:
        loop.create_task(ws_manager.broadcast(message))
