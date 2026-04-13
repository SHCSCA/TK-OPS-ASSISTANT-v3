from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from sqlalchemy.orm import Session, sessionmaker

from domain.models import LicenseGrant


LICENSE_ROW_ID: Final[int] = 1


@dataclass(frozen=True, slots=True)
class StoredLicenseGrant:
    active: bool
    restricted_mode: bool
    machine_code: str
    machine_bound: bool
    license_type: str
    signed_payload: str
    masked_code: str
    activated_at: str | None


class LicenseRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def load(self) -> StoredLicenseGrant | None:
        with self._session_factory() as session:
            row = session.get(LicenseGrant, LICENSE_ROW_ID)

        if row is None:
            return None

        return StoredLicenseGrant(
            active=bool(row.active),
            restricted_mode=bool(row.restricted_mode),
            machine_code=row.machine_code or row.machine_id,
            machine_bound=bool(row.machine_bound),
            license_type=row.license_type or "perpetual",
            signed_payload=row.signed_payload,
            masked_code=row.masked_code,
            activated_at=row.activated_at,
        )

    def save(self, grant: StoredLicenseGrant) -> StoredLicenseGrant:
        with self._session_factory() as session:
            session.merge(
                LicenseGrant(
                    id=LICENSE_ROW_ID,
                    active=int(grant.active),
                    restricted_mode=int(grant.restricted_mode),
                    machine_id=grant.machine_code,
                    machine_code=grant.machine_code,
                    machine_bound=int(grant.machine_bound),
                    activation_mode="offline_signed",
                    license_type=grant.license_type,
                    signed_payload=grant.signed_payload,
                    masked_code=grant.masked_code,
                    activated_at=grant.activated_at,
                )
            )
            session.commit()

        return grant
