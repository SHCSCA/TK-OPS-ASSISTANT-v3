from __future__ import annotations

from typing import Protocol


class SecretStore(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...


class NoopSecretStore:
    def get(self, key: str) -> str | None:
        return None

    def set(self, key: str, value: str) -> None:
        raise NotImplementedError("Secret storage is not wired in this milestone.")
