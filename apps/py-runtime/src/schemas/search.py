from __future__ import annotations

from pydantic import BaseModel


class SearchProjectResultDto(BaseModel):
    id: str
    name: str
    subtitle: str
    updatedAt: str


class SearchScriptResultDto(BaseModel):
    id: str
    projectId: str
    title: str
    snippet: str
    updatedAt: str


class SearchTaskResultDto(BaseModel):
    id: str
    kind: str
    label: str
    status: str
    updatedAt: str


class SearchAssetResultDto(BaseModel):
    id: str
    name: str
    type: str
    thumbnailUrl: str | None
    updatedAt: str


class SearchAccountResultDto(BaseModel):
    id: str
    name: str
    status: str


class SearchWorkspaceResultDto(BaseModel):
    id: str
    name: str
    status: str


class GlobalSearchResultDto(BaseModel):
    projects: list[SearchProjectResultDto]
    scripts: list[SearchScriptResultDto]
    tasks: list[SearchTaskResultDto]
    assets: list[SearchAssetResultDto]
    accounts: list[SearchAccountResultDto]
    workspaces: list[SearchWorkspaceResultDto]

