from __future__ import annotations

from pydantic import BaseModel, Field


class PromptTemplateDto(BaseModel):
    id: str
    kind: str
    name: str
    description: str
    content: str
    createdAt: str
    updatedAt: str


class PromptTemplateInput(BaseModel):
    kind: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    content: str = Field(min_length=1)


class PromptTemplateUpdateInput(BaseModel):
    kind: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    content: str = Field(min_length=1)
