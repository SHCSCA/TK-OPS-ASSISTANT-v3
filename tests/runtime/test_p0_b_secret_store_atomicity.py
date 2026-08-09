from __future__ import annotations

import os
from pathlib import Path
from threading import Barrier, Thread

import pytest

import app.secret_store as secret_store_module
from app.secret_store import FileSecretStore
from errors import DomainError
from repositories.license_repository import StoredLicenseGrant
from services.bootstrap_v1.license import LicenseV1Service
from services.bootstrap_v1.license_support import (
    build_secret_reference,
    secret_key,
)
from services.license_activation_base import ActivationResult
from services.machine_code import MachineIdentityResolution


def test_file_secret_store_instances_share_path_lock_and_preserve_keys(
    tmp_path: Path,
) -> None:
    path = tmp_path / "secrets" / "providers.json"
    first = FileSecretStore(path)
    second = FileSecretStore(path)
    barrier = Barrier(3)

    def write(store: FileSecretStore, key: str, value: str) -> None:
        barrier.wait()
        store.set(key, value)

    workers = [
        Thread(target=write, args=(first, "provider:a", "value-a")),
        Thread(target=write, args=(second, "provider:b", "value-b")),
    ]
    for worker in workers:
        worker.start()
    barrier.wait()
    for worker in workers:
        worker.join(timeout=2)

    assert first._lock is second._lock
    assert not any(worker.is_alive() for worker in workers)
    assert first.get("provider:a") == "value-a"
    assert first.get("provider:b") == "value-b"


def test_file_secret_store_concurrent_set_and_delete_preserve_other_keys(
    tmp_path: Path,
) -> None:
    path = tmp_path / "secrets" / "providers.json"
    first = FileSecretStore(path)
    second = FileSecretStore(path)
    first.set("provider:keep", "keep-value")
    first.set("provider:remove", "remove-value")
    barrier = Barrier(3)

    def add_value() -> None:
        barrier.wait()
        first.set("provider:add", "add-value")

    def delete_value() -> None:
        barrier.wait()
        second.delete("provider:remove")

    workers = [Thread(target=add_value), Thread(target=delete_value)]
    for worker in workers:
        worker.start()
    barrier.wait()
    for worker in workers:
        worker.join(timeout=2)

    assert not any(worker.is_alive() for worker in workers)
    assert first.get("provider:keep") == "keep-value"
    assert first.get("provider:add") == "add-value"
    assert first.get("provider:remove") is None


def test_file_secret_store_uses_fsync_and_same_directory_replace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "secrets" / "providers.json"
    store = FileSecretStore(path)
    fsync_calls: list[int] = []
    replacements: list[tuple[Path, Path]] = []
    real_fsync = os.fsync
    real_replace = os.replace

    def record_fsync(descriptor: int) -> None:
        fsync_calls.append(descriptor)
        real_fsync(descriptor)

    def record_replace(
        source: os.PathLike[str],
        target: os.PathLike[str],
    ) -> None:
        replacements.append((Path(source), Path(target)))
        real_replace(source, target)

    monkeypatch.setattr(secret_store_module.os, "fsync", record_fsync)
    monkeypatch.setattr(secret_store_module.os, "replace", record_replace)

    store.set("provider:a", "value-a")

    assert fsync_calls
    assert len(replacements) == 1
    temporary_path, destination_path = replacements[0]
    assert temporary_path.parent == destination_path.parent == path.parent
    assert destination_path == path
    assert not temporary_path.exists()


def test_file_secret_store_keeps_previous_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "secrets" / "providers.json"
    store = FileSecretStore(path)
    store.set("provider:a", "old-value")

    def fail_replace(*_args: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(secret_store_module.os, "replace", fail_replace)

    with pytest.raises(OSError):
        store.set("provider:a", "new-value")

    assert store.get("provider:a") == "old-value"
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_license_activation_restores_overwritten_secret_when_commit_fails(
) -> None:
    license_key = "signed.license"
    reference = build_secret_reference(license_key)
    storage_key = secret_key(reference)
    secret_store = _MemorySecretStore(
        {storage_key: "previous-license-value"}
    )
    service = LicenseV1Service(
        repository=_FailingLicenseRepository(),
        activation_adapter=_ActivationAdapter(),
        machine_code_service=_MachineCodeService(),
        secret_store=secret_store,
        event_service=_FailingEventService(),
    )

    with pytest.raises(DomainError):
        service.activate(
            license_key=license_key,
            machine_code="machine-code",
            idempotency_key="idem-restore-secret",
            request_id="req-restore-secret",
            operation_id="op-restore-secret",
        )

    assert secret_store.values[storage_key] == "previous-license-value"


class _MemorySecretStore:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def delete(self, key: str) -> None:
        self.values.pop(key, None)


class _FailingLicenseRepository:
    def load(self) -> StoredLicenseGrant | None:
        return None

    def save(
        self,
        grant: StoredLicenseGrant,
        *,
        before_commit=None,
    ) -> StoredLicenseGrant:
        if before_commit is not None:
            before_commit(None, grant)
        return grant


class _ActivationAdapter:
    def activate(
        self,
        activation_code: str,
        *,
        machine_code: str,
    ) -> ActivationResult:
        assert activation_code == "signed.license"
        assert machine_code == "machine-code"
        return ActivationResult(
            license_type="perpetual",
            activated_at="2026-07-26T09:00:00Z",
            masked_code="sign****************ense",
            signed_payload="signed",
        )


class _MachineCodeService:
    def get_machine_code(self) -> str:
        return "machine-code"

    def resolve(
        self,
        *,
        legacy_machine_code: str | None = None,
    ) -> MachineIdentityResolution:
        del legacy_machine_code
        return MachineIdentityResolution(
            machine_code="machine-code",
            status="verified",
            matched_factor_count=3,
            mismatched_factor_count=0,
            unavailable_factor_count=0,
        )


class _FailingEventService:
    def append(self, *_args: object, **_kwargs: object) -> None:
        raise RuntimeError("event write failed")
