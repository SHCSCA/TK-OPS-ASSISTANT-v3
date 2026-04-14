from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base shared by all persistent domain models."""


def generate_uuid() -> str:
    return uuid4().hex
