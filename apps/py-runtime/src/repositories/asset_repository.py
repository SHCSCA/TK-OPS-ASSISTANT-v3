from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from domain.models.asset import Asset, AssetReference

log = logging.getLogger(__name__)


class AssetRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_assets(
        self,
        *,
        asset_type: str | None = None,
        source: str | None = None,
        project_id: str | None = None,
        q: str | None = None,
    ) -> list[Asset]:
        with self._session_factory() as session:
            stmt = select(Asset).order_by(Asset.created_at.desc())
            if asset_type is not None:
                stmt = stmt.where(Asset.type == asset_type)
            if source is not None:
                stmt = stmt.where(Asset.source == source)
            if project_id is not None:
                stmt = stmt.where(Asset.project_id == project_id)
            if q is not None:
                pattern = f"%{q}%"
                stmt = stmt.where(
                    or_(Asset.name.ilike(pattern), Asset.tags.ilike(pattern))
                )
            assets = session.scalars(stmt).all()
            # detach from session
            session.expunge_all()
            return list(assets)

    def create_asset(self, asset: Asset) -> Asset:
        with self._session_factory() as session:
            session.add(asset)
            session.commit()
            session.refresh(asset)
            session.expunge(asset)
            return asset

    def get_asset(self, asset_id: str) -> Asset | None:
        with self._session_factory() as session:
            asset = session.get(Asset, asset_id)
            if asset is not None:
                session.expunge(asset)
            return asset

    def get_reference(self, reference_id: str) -> AssetReference | None:
        with self._session_factory() as session:
            reference = session.get(AssetReference, reference_id)
            if reference is not None:
                session.expunge(reference)
            return reference

    def count_references(self, asset_id: str) -> int:
        with self._session_factory() as session:
            return session.scalar(
                select(func.count(AssetReference.id)).where(
                    AssetReference.asset_id == asset_id
                )
            ) or 0

    def update_asset(self, asset_id: str, *, changes: dict[str, object]) -> Asset | None:
        with self._session_factory() as session:
            asset = session.get(Asset, asset_id)
            if asset is None:
                return None
            for key, value in changes.items():
                setattr(asset, key, value)
            asset.updated_at = _utc_now()
            session.commit()
            session.refresh(asset)
            session.expunge(asset)
            return asset

    def delete_asset(self, asset_id: str) -> bool:
        with self._session_factory() as session:
            asset = session.get(Asset, asset_id)
            if asset is None:
                return False
            session.delete(asset)
            session.commit()
            return True

    def list_references(self, asset_id: str) -> list[AssetReference]:
        with self._session_factory() as session:
            refs = session.scalars(
                select(AssetReference)
                .where(AssetReference.asset_id == asset_id)
                .order_by(AssetReference.created_at.asc())
            ).all()
            session.expunge_all()
            return list(refs)

    def create_reference(self, reference: AssetReference) -> AssetReference:
        with self._session_factory() as session:
            session.add(reference)
            session.commit()
            session.refresh(reference)
            session.expunge(reference)
            return reference

    def delete_reference(self, reference_id: str) -> bool:
        with self._session_factory() as session:
            ref = session.get(AssetReference, reference_id)
            if ref is None:
                return False
            session.delete(ref)
            session.commit()
            return True


def _utc_now() -> str:
    return datetime.utcnow().isoformat()
