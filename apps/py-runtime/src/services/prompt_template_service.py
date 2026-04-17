from __future__ import annotations

from fastapi import HTTPException

from repositories.prompt_template_repository import (
    PromptTemplateRepository,
    StoredPromptTemplate,
)
from schemas.prompt_templates import (
    PromptTemplateDto,
    PromptTemplateInput,
    PromptTemplateUpdateInput,
)


class PromptTemplateService:
    def __init__(self, repository: PromptTemplateRepository) -> None:
        self._repository = repository

    def list_templates(self, kind: str | None = None) -> list[PromptTemplateDto]:
        return [self._to_dto(item) for item in self._repository.list_templates(kind)]

    def create_template(self, payload: PromptTemplateInput) -> PromptTemplateDto:
        stored = self._repository.create_template(
            kind=payload.kind.strip(),
            name=payload.name.strip(),
            description=payload.description.strip(),
            content=payload.content.strip(),
        )
        return self._to_dto(stored)

    def update_template(
        self,
        template_id: str,
        payload: PromptTemplateUpdateInput,
    ) -> PromptTemplateDto:
        stored = self._repository.update_template(
            template_id,
            kind=payload.kind.strip(),
            name=payload.name.strip(),
            description=payload.description.strip(),
            content=payload.content.strip(),
        )
        if stored is None:
            raise HTTPException(status_code=404, detail="Prompt 模板不存在")
        return self._to_dto(stored)

    def delete_template(self, template_id: str) -> dict[str, bool]:
        if not self._repository.delete_template(template_id):
            raise HTTPException(status_code=404, detail="Prompt 模板不存在")
        return {"deleted": True}

    def get_template(self, template_id: str) -> PromptTemplateDto:
        stored = self._repository.get_template(template_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="Prompt 模板不存在")
        return self._to_dto(stored)

    def _to_dto(self, item: StoredPromptTemplate) -> PromptTemplateDto:
        return PromptTemplateDto(
            id=item.id,
            kind=item.kind,
            name=item.name,
            description=item.description,
            content=item.content,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )
