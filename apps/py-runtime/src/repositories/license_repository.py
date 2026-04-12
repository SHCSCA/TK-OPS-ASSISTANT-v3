from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from persistence import connect_sqlite, initialize_schema


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
    def __init__(self, database_path) -> None:
        self._database_path = database_path
        initialize_schema(database_path)

    def load(self) -> StoredLicenseGrant | None:
        with connect_sqlite(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT
                    active,
                    restricted_mode,
                    machine_code,
                    machine_bound,
                    license_type,
                    signed_payload,
                    masked_code,
                    activated_at
                FROM license_grant
                WHERE id = ?
                """,
                (LICENSE_ROW_ID,),
            ).fetchone()

        if row is None:
            return None

        return StoredLicenseGrant(
            active=bool(row["active"]),
            restricted_mode=bool(row["restricted_mode"]),
            machine_code=str(row["machine_code"] or row["machine_id"]),
            machine_bound=bool(row["machine_bound"]),
            license_type=str(row["license_type"] or "perpetual"),
            signed_payload=str(row["signed_payload"]),
            masked_code=str(row["masked_code"]),
            activated_at=str(row["activated_at"]) if row["activated_at"] else None,
        )

    def save(self, grant: StoredLicenseGrant) -> StoredLicenseGrant:
        with connect_sqlite(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO license_grant (
                    id,
                    active,
                    restricted_mode,
                    machine_id,
                    machine_code,
                    machine_bound,
                    activation_mode,
                    license_type,
                    signed_payload,
                    masked_code,
                    activated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    active = excluded.active,
                    restricted_mode = excluded.restricted_mode,
                    machine_id = excluded.machine_id,
                    machine_code = excluded.machine_code,
                    machine_bound = excluded.machine_bound,
                    activation_mode = excluded.activation_mode,
                    license_type = excluded.license_type,
                    signed_payload = excluded.signed_payload,
                    masked_code = excluded.masked_code,
                    activated_at = excluded.activated_at
                """,
                (
                    LICENSE_ROW_ID,
                    int(grant.active),
                    int(grant.restricted_mode),
                    grant.machine_code,
                    grant.machine_code,
                    int(grant.machine_bound),
                    "offline_signed",
                    grant.license_type,
                    grant.signed_payload,
                    grant.masked_code,
                    grant.activated_at,
                ),
            )
            connection.commit()

        return grant
