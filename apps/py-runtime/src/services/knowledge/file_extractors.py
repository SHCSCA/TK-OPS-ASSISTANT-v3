from __future__ import annotations

import json
from dataclasses import dataclass

from errors import DomainError, ErrorCode
from services.knowledge.ports import ResolvedKnowledgeContent

EXTRACTOR_VERSION = 1
_CHUNK_CHARACTERS = 2_000


@dataclass(frozen=True, slots=True)
class ExtractedTextChunk:
    ordinal: int
    text: str
    token_count: int


@dataclass(frozen=True, slots=True)
class KnowledgeExtraction:
    status: str
    chunks: tuple[ExtractedTextChunk, ...]


def extract_knowledge_content(
    content: ResolvedKnowledgeContent,
) -> KnowledgeExtraction:
    media_type = (content.media_type or "").split(";", 1)[0].lower()
    if media_type not in {
        "text/plain",
        "text/markdown",
        "application/json",
    }:
        return KnowledgeExtraction(status="metadata_only", chunks=())
    try:
        text = content.data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DomainError(
            ErrorCode.KNOWLEDGE_INDEX_FAILED,
            "文本知识文件必须使用 UTF-8 编码",
            status_code=422,
        ) from exc
    if media_type == "application/json":
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DomainError(
                ErrorCode.KNOWLEDGE_INDEX_FAILED,
                "JSON 知识文件格式无效",
                status_code=422,
            ) from exc
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise DomainError(
            ErrorCode.KNOWLEDGE_INDEX_FAILED,
            "文本知识文件没有可索引内容",
            status_code=422,
        )
    chunks = tuple(
        ExtractedTextChunk(
            ordinal=index,
            text=normalized[offset : offset + _CHUNK_CHARACTERS],
            token_count=max(
                1,
                (
                    len(normalized[offset : offset + _CHUNK_CHARACTERS])
                    + 3
                )
                // 4,
            ),
        )
        for index, offset in enumerate(
            range(0, len(normalized), _CHUNK_CHARACTERS)
        )
    )
    return KnowledgeExtraction(status="ready", chunks=chunks)
