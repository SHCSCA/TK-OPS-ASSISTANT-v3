from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class LicenseGrant(Base):
    __tablename__ = "license_grant"
    __table_args__ = (CheckConstraint("id = 1"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active: Mapped[int] = mapped_column(Integer, nullable=False)
    restricted_mode: Mapped[int] = mapped_column(Integer, nullable=False)
    machine_id: Mapped[str] = mapped_column(Text, nullable=False)
    machine_bound: Mapped[int] = mapped_column(Integer, nullable=False)
    activation_mode: Mapped[str] = mapped_column(Text, nullable=False)
    masked_code: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    machine_code: Mapped[str] = mapped_column(Text, nullable=False, default="")
    license_type: Mapped[str] = mapped_column(Text, nullable=False, default="perpetual")
    signed_payload: Mapped[str] = mapped_column(Text, nullable=False, default="")
