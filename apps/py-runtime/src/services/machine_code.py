from __future__ import annotations

import ctypes
import hashlib
import json
import logging
import os
import subprocess
import winreg
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Callable, Literal

from app.config import is_development_mode
from app.secret_store import SecretStore


log = logging.getLogger(__name__)
MACHINE_CODE_ALGORITHM_VERSION = "v2"
LEGACY_MACHINE_CODE_ALGORITHM_VERSION = "v1"
MACHINE_IDENTITY_SECRET_KEY = "machine-identity/v2"
MINIMUM_STABLE_FACTORS = 2
_FACTOR_KEYS = ("registry", "cim", "system_volume")

FactorStatus = Literal["available", "unavailable", "invalid"]
IdentityStatus = Literal["verified", "degraded", "unavailable", "mismatch"]


class MachineCodeError(RuntimeError):
    def __init__(self, message: str, *, code: str = "MACHINE_IDENTITY_RETRY_REQUIRED") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class MachineFactorObservation:
    key: str
    status: FactorStatus
    value_hash: str | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class MachineIdentityResolution:
    machine_code: str
    status: IdentityStatus
    matched_factor_count: int
    mismatched_factor_count: int
    unavailable_factor_count: int
    algorithm_version: str = MACHINE_CODE_ALGORITHM_VERSION


@dataclass(frozen=True, slots=True)
class _MachineIdentityBaseline:
    formatVersion: int
    algorithmVersion: str
    canonicalMachineCode: str
    factorHashes: dict[str, str]
    createdAt: str
    lastVerifiedAt: str


class MachineCodeService:
    def __init__(
        self,
        *,
        secret_store: SecretStore | None = None,
        runtime_mode: str = "test",
        factor_timeout_seconds: int = 10,
        factor_retry_attempts: int = 1,
        allow_test_override: bool = False,
    ) -> None:
        self._secret_store = secret_store
        self._runtime_mode = runtime_mode
        self._factor_timeout_seconds = factor_timeout_seconds
        self._factor_retry_attempts = factor_retry_attempts
        self._allow_test_override = allow_test_override

    def get_machine_code(self, *, legacy_machine_code: str | None = None) -> str:
        override = self._read_override()
        if override is not None:
            return override

        if self._secret_store is None:
            return self._legacy_machine_code(self._available_raw_values())

        resolution = self.resolve(legacy_machine_code=legacy_machine_code)
        if resolution.status in {"verified", "degraded"}:
            return resolution.machine_code
        if resolution.status == "mismatch":
            raise MachineCodeError(
                "设备身份与本机安全基线不匹配",
                code="LICENSE_MACHINE_MISMATCH",
            )
        raise MachineCodeError(
            "设备信息采集不完整，请稍后重试",
            code="MACHINE_IDENTITY_RETRY_REQUIRED",
        )

    def resolve(
        self,
        *,
        legacy_machine_code: str | None = None,
    ) -> MachineIdentityResolution:
        override = self._read_override()
        if override is not None:
            return MachineIdentityResolution(
                machine_code=override,
                status="verified",
                matched_factor_count=3,
                mismatched_factor_count=0,
                unavailable_factor_count=0,
            )

        observations, raw_values = self._collect_factor_observations()
        baseline = self._load_baseline()
        if baseline is None:
            return self._initialize_baseline(
                observations,
                raw_values=raw_values,
                legacy_machine_code=legacy_machine_code,
            )
        return self._compare_with_baseline(baseline, observations)

    def _read_override(self) -> str | None:
        override = os.getenv("TK_OPS_MACHINE_CODE_OVERRIDE", "").strip()
        if not override:
            return None
        if not (
            self._allow_test_override
            and is_development_mode(self._runtime_mode)
        ):
            log.warning(
                "已拒绝未授权的机器码覆盖",
                extra={"operation": "license.machine_identity.override"},
            )
            return None
        return override.upper()

    def _initialize_baseline(
        self,
        observations: tuple[MachineFactorObservation, ...],
        *,
        raw_values: dict[str, str],
        legacy_machine_code: str | None,
    ) -> MachineIdentityResolution:
        factor_hashes = {
            item.key: item.value_hash
            for item in observations
            if item.status == "available" and item.value_hash is not None
        }
        unavailable_count = len(_FACTOR_KEYS) - len(factor_hashes)
        canonical = ""

        if legacy_machine_code:
            if len(raw_values) < len(_FACTOR_KEYS):
                return MachineIdentityResolution(
                    machine_code=legacy_machine_code,
                    status="unavailable",
                    matched_factor_count=0,
                    mismatched_factor_count=0,
                    unavailable_factor_count=unavailable_count,
                )
            legacy_current = self._legacy_machine_code(raw_values)
            if _normalize_machine_code(legacy_current) != _normalize_machine_code(
                legacy_machine_code
            ):
                return MachineIdentityResolution(
                    machine_code=legacy_machine_code,
                    status="mismatch",
                    matched_factor_count=0,
                    mismatched_factor_count=len(_FACTOR_KEYS),
                    unavailable_factor_count=0,
                )
            canonical = legacy_machine_code.strip().upper()
        else:
            if len(factor_hashes) < MINIMUM_STABLE_FACTORS:
                return MachineIdentityResolution(
                    machine_code="",
                    status="unavailable",
                    matched_factor_count=0,
                    mismatched_factor_count=0,
                    unavailable_factor_count=unavailable_count,
                )
            canonical = _machine_code_from_hashes(factor_hashes)

        now = _utc_now()
        baseline = _MachineIdentityBaseline(
            formatVersion=2,
            algorithmVersion=MACHINE_CODE_ALGORITHM_VERSION,
            canonicalMachineCode=canonical,
            factorHashes=factor_hashes,
            createdAt=now,
            lastVerifiedAt=now,
        )
        self._save_baseline(baseline)
        return MachineIdentityResolution(
            machine_code=canonical,
            status="verified",
            matched_factor_count=len(factor_hashes),
            mismatched_factor_count=0,
            unavailable_factor_count=unavailable_count,
        )

    def _compare_with_baseline(
        self,
        baseline: _MachineIdentityBaseline,
        observations: tuple[MachineFactorObservation, ...],
    ) -> MachineIdentityResolution:
        by_key = {item.key: item for item in observations}
        matched = 0
        mismatched = 0
        unavailable = 0
        for key, expected_hash in baseline.factorHashes.items():
            observation = by_key.get(key)
            if observation is None or observation.status != "available":
                unavailable += 1
            elif observation.value_hash == expected_hash:
                matched += 1
            else:
                mismatched += 1

        if matched >= MINIMUM_STABLE_FACTORS:
            status: IdentityStatus = "verified"
        elif matched >= 1 and mismatched == 0:
            status = "degraded"
        elif mismatched >= MINIMUM_STABLE_FACTORS:
            status = "mismatch"
        else:
            status = "unavailable"

        if status in {"verified", "degraded"}:
            self._save_baseline(
                _MachineIdentityBaseline(
                    **{
                        **asdict(baseline),
                        "lastVerifiedAt": _utc_now(),
                    }
                )
            )
        return MachineIdentityResolution(
            machine_code=baseline.canonicalMachineCode,
            status=status,
            matched_factor_count=matched,
            mismatched_factor_count=mismatched,
            unavailable_factor_count=unavailable,
        )

    def _load_baseline(self) -> _MachineIdentityBaseline | None:
        if self._secret_store is None:
            return None
        try:
            raw = self._secret_store.get(MACHINE_IDENTITY_SECRET_KEY)
            if raw is None:
                return None
            payload = json.loads(raw)
            baseline = _MachineIdentityBaseline(**payload)
            if not _is_valid_baseline(baseline):
                raise ValueError("机器身份基线结构无效")
            return baseline
        except Exception as exc:
            log.exception(
                "读取机器身份安全基线失败",
                extra={"operation": "license.machine_identity.read"},
            )
            raise MachineCodeError(
                "机器身份安全存储不可用",
                code="MACHINE_IDENTITY_STORE_UNAVAILABLE",
            ) from exc

    def _save_baseline(self, baseline: _MachineIdentityBaseline) -> None:
        if self._secret_store is None:
            raise MachineCodeError(
                "机器身份安全存储不可用",
                code="MACHINE_IDENTITY_STORE_UNAVAILABLE",
            )
        try:
            self._secret_store.set(
                MACHINE_IDENTITY_SECRET_KEY,
                json.dumps(asdict(baseline), ensure_ascii=False, sort_keys=True),
            )
        except Exception as exc:
            log.exception(
                "写入机器身份安全基线失败",
                extra={"operation": "license.machine_identity.write"},
            )
            raise MachineCodeError(
                "机器身份安全存储不可用",
                code="MACHINE_IDENTITY_STORE_UNAVAILABLE",
            ) from exc

    def _collect_factor_observations(
        self,
    ) -> tuple[tuple[MachineFactorObservation, ...], dict[str, str]]:
        readers: tuple[tuple[str, Callable[[], str]], ...] = (
            ("registry", self._read_machine_guid),
            ("cim", self._read_device_uuid),
            ("system_volume", self._read_system_drive_serial),
        )
        observations: list[MachineFactorObservation] = []
        raw_values: dict[str, str] = {}
        for key, reader in readers:
            observation, raw_value = self._observe_factor(key, reader)
            observations.append(observation)
            if raw_value is not None:
                raw_values[key] = raw_value
        return tuple(observations), raw_values

    def _observe_factor(
        self,
        key: str,
        reader: Callable[[], str],
    ) -> tuple[MachineFactorObservation, str | None]:
        last_error: Exception | None = None
        for attempt in range(self._factor_retry_attempts + 1):
            try:
                value = reader().strip().upper()
                if not value:
                    return (
                        MachineFactorObservation(
                            key=key,
                            status="invalid",
                            value_hash=None,
                            error_code="MACHINE_FACTOR_EMPTY",
                        ),
                        None,
                    )
                return (
                    MachineFactorObservation(
                        key=key,
                        status="available",
                        value_hash=_factor_hash(key, value),
                        error_code=None,
                    ),
                    value,
                )
            except Exception as exc:
                last_error = exc
                if attempt < self._factor_retry_attempts:
                    sleep(0.05)
        log.warning(
            "采集机器身份因子失败",
            extra={
                "operation": "license.machine_identity.factor",
                "factor": key,
                "error_code": "MACHINE_FACTOR_UNAVAILABLE",
                "error_type": type(last_error).__name__ if last_error else "unknown",
            },
        )
        return (
            MachineFactorObservation(
                key=key,
                status="unavailable",
                value_hash=None,
                error_code="MACHINE_FACTOR_UNAVAILABLE",
            ),
            None,
        )

    def _available_raw_values(self) -> dict[str, str]:
        _, raw_values = self._collect_factor_observations()
        if len(raw_values) < MINIMUM_STABLE_FACTORS:
            raise MachineCodeError("稳定设备因子不足，无法生成机器码")
        return raw_values

    @staticmethod
    def _legacy_machine_code(raw_values: dict[str, str]) -> str:
        values = [raw_values[key] for key in _FACTOR_KEYS if key in raw_values]
        normalized = "|".join(value.strip().upper() for value in values)
        return _format_machine_code(hashlib.sha256(normalized.encode("utf-8")).hexdigest())

    def _read_machine_guid(self) -> str:
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
        except OSError as exc:
            raise MachineCodeError("无法读取本机注册信息") from exc
        return str(value)

    def _read_device_uuid(self) -> str:
        powershell = (
            Path(os.getenv("SystemRoot", r"C:\Windows"))
            / "System32"
            / "WindowsPowerShell"
            / "v1.0"
            / "powershell.exe"
        )
        command = [
            str(powershell),
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_ComputerSystemProduct).UUID",
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=True,
                text=True,
                encoding="utf-8",
                timeout=self._factor_timeout_seconds,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise MachineCodeError("无法读取设备标识") from exc
        value = result.stdout.strip()
        if not value:
            raise MachineCodeError("设备标识为空")
        return value

    def _read_system_drive_serial(self) -> str:
        drive = os.getenv("SystemDrive", "C:").strip() or "C:"
        serial_number = ctypes.c_uint32()
        maximum_component_length = ctypes.c_uint32()
        file_system_flags = ctypes.c_uint32()
        success = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(f"{drive}\\"),
            None,
            0,
            ctypes.byref(serial_number),
            ctypes.byref(maximum_component_length),
            ctypes.byref(file_system_flags),
            None,
            0,
        )
        if not success:
            raise MachineCodeError("无法读取系统盘序列号")
        return f"{serial_number.value:08X}"


def _factor_hash(key: str, value: str) -> str:
    return hashlib.sha256(f"{key}\0{value}".encode("utf-8")).hexdigest()


def _machine_code_from_hashes(factor_hashes: dict[str, str]) -> str:
    canonical = "|".join(
        f"{key}:{factor_hashes[key]}" for key in sorted(factor_hashes)
    )
    return _format_machine_code(hashlib.sha256(canonical.encode("utf-8")).hexdigest())


def _format_machine_code(digest: str) -> str:
    normalized = digest.upper()
    groups = [normalized[index : index + 5] for index in range(0, 25, 5)]
    return f"TKOPS-{'-'.join(groups)}"


def _normalize_machine_code(value: str) -> str:
    return "".join(value.strip().upper().split())


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _is_valid_baseline(baseline: _MachineIdentityBaseline) -> bool:
    return (
        baseline.formatVersion == 2
        and baseline.algorithmVersion == MACHINE_CODE_ALGORITHM_VERSION
        and baseline.canonicalMachineCode.startswith("TKOPS-")
        and MINIMUM_STABLE_FACTORS <= len(baseline.factorHashes) <= len(_FACTOR_KEYS)
        and set(baseline.factorHashes).issubset(_FACTOR_KEYS)
        and all(
            isinstance(value, str) and len(value) == 64
            for value in baseline.factorHashes.values()
        )
        and bool(baseline.createdAt)
        and bool(baseline.lastVerifiedAt)
    )
