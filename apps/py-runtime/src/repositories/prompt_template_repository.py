from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import PromptTemplate
from domain.models.base import generate_uuid


@dataclass(frozen=True, slots=True)
class StoredPromptTemplate:
    id: str
    kind: str
    name: str
    description: str
    content: str
    created_at: str
    updated_at: str


class PromptTemplateRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_templates(self, kind: str | None = None) -> list[StoredPromptTemplate]:
        with self._session_factory() as session:
            stmt = select(PromptTemplate).order_by(PromptTemplate.updated_at.desc())
            if kind is not None:
                stmt = stmt.where(PromptTemplate.kind == kind)
            rows = session.scalars(stmt).all()
        return [self._to_stored(item) for item in rows]

    def get_template(self, template_id: str) -> StoredPromptTemplate | None:
        with self._session_factory() as session:
            template = session.get(PromptTemplate, template_id)
            if template is None:
                return None
            session.expunge(template)
        return self._to_stored(template)

    def create_template(
        self,
        *,
        kind: str,
        name: str,
        description: str,
        content: str,
    ) -> StoredPromptTemplate:
        template = PromptTemplate(
            id=generate_uuid(),
            kind=kind,
            name=name,
            description=description,
            content=content,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        with self._session_factory() as session:
            session.add(template)
            session.commit()
            session.refresh(template)
            session.expunge(template)
        return self._to_stored(template)

    def update_template(
        self,
        template_id: str,
        *,
        kind: str,
        name: str,
        description: str,
        content: str,
    ) -> StoredPromptTemplate | None:
        with self._session_factory() as session:
            template = session.get(PromptTemplate, template_id)
            if template is None:
                return None
            template.kind = kind
            template.name = name
            template.description = description
            template.content = content
            template.updated_at = _utc_now()
            session.commit()
            session.refresh(template)
            session.expunge(template)
        return self._to_stored(template)

    def delete_template(self, template_id: str) -> bool:
        with self._session_factory() as session:
            template = session.get(PromptTemplate, template_id)
            if template is None:
                return False
            session.delete(template)
            session.commit()
        return True

    def _to_stored(self, template: PromptTemplate) -> StoredPromptTemplate:
        return StoredPromptTemplate(
            id=template.id,
            kind=template.kind,
            name=template.name,
            description=template.description,
            content=template.content,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
