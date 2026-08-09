from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.machine_code import (
    MACHINE_IDENTITY_SECRET_KEY,
    MachineCodeError,
    MachineCodeService,
)


class _MemorySecretStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def delete(self, key: str) -> None:
        self.values.pop(key, None)


def test_device_uuid_uses_bounded_absolute_powershell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def run(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(stdout="device-uuid\n")

    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    monkeypatch.setattr(subprocess, "run", run)

    value = MachineCodeService()._read_device_uuid()

    expected = (
        Path(r"C:\Windows")
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    assert value == "device-uuid"
    assert captured["command"] == [
        str(expected),
        "-NoProfile",
        "-Command",
        "(Get-CimInstance Win32_ComputerSystemProduct).UUID",
    ]
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["timeout"] == 10
    assert kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW


def test_device_uuid_timeout_maps_to_stable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(command: list[str], **_: object) -> None:
        raise subprocess.TimeoutExpired(command, timeout=10)

    monkeypatch.setattr(subprocess, "run", timeout)

    with pytest.raises(MachineCodeError, match="无法读取设备标识"):
        MachineCodeService()._read_device_uuid()


def test_machine_code_v1_preserves_existing_three_factor_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = MachineCodeService()
    monkeypatch.setattr(service, "_read_machine_guid", lambda: "guid")
    monkeypatch.setattr(service, "_read_device_uuid", lambda: "uuid")
    monkeypatch.setattr(service, "_read_system_drive_serial", lambda: "serial")

    assert service.get_machine_code() == "TKOPS-A88E9-29BC5-FE65A-CF0A4-0D067"


@pytest.mark.parametrize(
    "failed_reader",
    ["_read_machine_guid", "_read_device_uuid", "_read_system_drive_serial"],
)
def test_machine_code_v1_tolerates_one_unavailable_factor(
    monkeypatch: pytest.MonkeyPatch,
    failed_reader: str,
) -> None:
    service = MachineCodeService()
    monkeypatch.setattr(service, "_read_machine_guid", lambda: "guid")
    monkeypatch.setattr(service, "_read_device_uuid", lambda: "uuid")
    monkeypatch.setattr(service, "_read_system_drive_serial", lambda: "serial")

    def unavailable() -> str:
        raise MachineCodeError("factor unavailable")

    monkeypatch.setattr(service, failed_reader, unavailable)

    first = service.get_machine_code()
    second = service.get_machine_code()

    assert first.startswith("TKOPS-")
    assert first == second


def test_machine_code_v1_rejects_less_than_two_stable_factors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = MachineCodeService()
    monkeypatch.setattr(service, "_read_machine_guid", lambda: "guid")

    def unavailable() -> str:
        raise MachineCodeError("factor unavailable")

    monkeypatch.setattr(service, "_read_device_uuid", unavailable)
    monkeypatch.setattr(service, "_read_system_drive_serial", unavailable)

    with pytest.raises(MachineCodeError, match="稳定设备因子不足"):
        service.get_machine_code()


def test_machine_identity_v2_keeps_canonical_code_when_cim_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _MemorySecretStore()
    service = MachineCodeService(secret_store=store, runtime_mode="production")
    monkeypatch.setattr(service, "_read_machine_guid", lambda: "guid")
    monkeypatch.setattr(service, "_read_device_uuid", lambda: "uuid")
    monkeypatch.setattr(service, "_read_system_drive_serial", lambda: "serial")
    first = service.resolve()

    def unavailable() -> str:
        raise MachineCodeError("cim unavailable")

    monkeypatch.setattr(service, "_read_device_uuid", unavailable)
    second = service.resolve()

    assert first.status == "verified"
    assert second.status == "verified"
    assert second.machine_code == first.machine_code
    assert second.matched_factor_count == 2
    assert second.unavailable_factor_count == 1


def test_machine_identity_v2_reports_degraded_with_one_matching_factor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _MemorySecretStore()
    service = MachineCodeService(secret_store=store, runtime_mode="production")
    monkeypatch.setattr(service, "_read_machine_guid", lambda: "guid")
    monkeypatch.setattr(service, "_read_device_uuid", lambda: "uuid")
    monkeypatch.setattr(service, "_read_system_drive_serial", lambda: "serial")
    first = service.resolve()

    def unavailable() -> str:
        raise MachineCodeError("factor unavailable")

    monkeypatch.setattr(service, "_read_device_uuid", unavailable)
    monkeypatch.setattr(service, "_read_system_drive_serial", unavailable)
    second = service.resolve()

    assert second.status == "degraded"
    assert second.machine_code == first.machine_code
    assert second.matched_factor_count == 1


def test_machine_identity_v2_requires_two_explicit_mismatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _MemorySecretStore()
    service = MachineCodeService(secret_store=store, runtime_mode="production")
    monkeypatch.setattr(service, "_read_machine_guid", lambda: "guid")
    monkeypatch.setattr(service, "_read_device_uuid", lambda: "uuid")
    monkeypatch.setattr(service, "_read_system_drive_serial", lambda: "serial")
    service.resolve()
    monkeypatch.setattr(service, "_read_machine_guid", lambda: "other-guid")
    monkeypatch.setattr(service, "_read_device_uuid", lambda: "other-uuid")

    resolution = service.resolve()

    assert resolution.status == "mismatch"
    assert resolution.mismatched_factor_count == 2


def test_machine_identity_v2_refuses_corrupted_secure_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _MemorySecretStore()
    store.values[MACHINE_IDENTITY_SECRET_KEY] = "not-json"
    service = MachineCodeService(secret_store=store, runtime_mode="production")
    monkeypatch.setattr(service, "_read_machine_guid", lambda: "guid")
    monkeypatch.setattr(service, "_read_device_uuid", lambda: "uuid")
    monkeypatch.setattr(service, "_read_system_drive_serial", lambda: "serial")

    with pytest.raises(MachineCodeError) as captured:
        service.resolve()

    assert captured.value.code == "MACHINE_IDENTITY_STORE_UNAVAILABLE"


def test_machine_identity_v2_migrates_complete_v1_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _MemorySecretStore()
    service = MachineCodeService(secret_store=store, runtime_mode="production")
    monkeypatch.setattr(service, "_read_machine_guid", lambda: "guid")
    monkeypatch.setattr(service, "_read_device_uuid", lambda: "uuid")
    monkeypatch.setattr(service, "_read_system_drive_serial", lambda: "serial")
    legacy = "TKOPS-A88E9-29BC5-FE65A-CF0A4-0D067"

    resolution = service.resolve(legacy_machine_code=legacy)

    assert resolution.status == "verified"
    assert resolution.machine_code == legacy
    assert MACHINE_IDENTITY_SECRET_KEY in store.values


def test_machine_identity_production_rejects_environment_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _MemorySecretStore()
    service = MachineCodeService(
        secret_store=store,
        runtime_mode="production",
        allow_test_override=True,
    )
    monkeypatch.setenv(
        "TK_OPS_MACHINE_CODE_OVERRIDE",
        "TKOPS-OVERR-IDE00-00000-00000-00000",
    )
    monkeypatch.setattr(service, "_read_machine_guid", lambda: "guid")
    monkeypatch.setattr(service, "_read_device_uuid", lambda: "uuid")
    monkeypatch.setattr(service, "_read_system_drive_serial", lambda: "serial")

    resolution = service.resolve()

    assert resolution.machine_code != "TKOPS-OVERR-IDE00-00000-00000-00000"
