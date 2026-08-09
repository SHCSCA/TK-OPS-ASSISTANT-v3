from __future__ import annotations

import hashlib
import json
import logging
import secrets
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Protocol

import psutil

from services.browser_runtime import BrowserLaunchResult

log = logging.getLogger(__name__)


class BrowserProcessOwnershipError(RuntimeError):
    """浏览器进程所有权证据不足。"""

    error_code = "BROWSER_PROCESS_OWNERSHIP_UNPROVEN"


class ProcessLike(Protocol):
    pid: int

    def cmdline(self) -> list[str]: ...

    def create_time(self) -> float: ...

    def exe(self) -> str: ...

    def net_connections(self, kind: str) -> list[Any]: ...


@dataclass(frozen=True, slots=True)
class BrowserOwnerMarker:
    schemaVersion: int
    accountId: str
    browserInstanceId: str
    createdAt: str
    launchNonceHash: str
    runtimeGeneration: str


@dataclass(frozen=True, slots=True)
class BrowserOwnershipEvidence:
    schemaVersion: int
    runtimeGeneration: str
    executableCanonicalPathHash: str
    profileCanonicalPathHash: str
    processId: int
    processCreatedAt: str
    launchNonceHash: str
    debugHost: str
    debugPort: int
    ownerMarkerVersion: int

    def to_json(self) -> str:
        return json.dumps(
            asdict(self),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


class BrowserProcessOwnershipService:
    def __init__(
        self,
        *,
        runtime_generation: str,
        process_factory: Callable[[int], ProcessLike] = psutil.Process,
    ) -> None:
        self._runtime_generation = runtime_generation
        self._process_factory = process_factory

    def create_marker(
        self,
        *,
        account_id: str,
        browser_instance_id: str,
        profile_path: Path,
    ) -> str:
        nonce = secrets.token_hex(32)
        marker = BrowserOwnerMarker(
            schemaVersion=1,
            accountId=account_id,
            browserInstanceId=browser_instance_id,
            createdAt=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            launchNonceHash=_hash_text(nonce),
            runtimeGeneration=self._runtime_generation,
        )
        marker_path = _marker_path(profile_path)
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = marker_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(asdict(marker), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(marker_path)
        return nonce

    def verify_launch(
        self,
        *,
        account_id: str,
        browser_instance_id: str,
        profile_path: Path,
        nonce: str,
        launch: BrowserLaunchResult,
    ) -> BrowserOwnershipEvidence:
        try:
            process = self._process_factory(launch.process_id)
            executable = Path(process.exe()).resolve(strict=True)
            launched_executable = Path(launch.executable_path).resolve(strict=True)
            canonical_profile = profile_path.resolve(strict=True)
            command_profile = _profile_from_command(process.cmdline())
            marker = _read_marker(profile_path)
            owns_port = _process_owns_port(process, launch.debug_port)
            valid = (
                process.pid == launch.process_id
                and executable == launched_executable
                and command_profile is not None
                and command_profile.resolve(strict=True) == canonical_profile
                and launch.debug_host == "127.0.0.1"
                and owns_port
                and marker.accountId == account_id
                and marker.browserInstanceId == browser_instance_id
                and marker.launchNonceHash == _hash_text(nonce)
                and marker.runtimeGeneration == self._runtime_generation
            )
            if not valid:
                raise BrowserProcessOwnershipError(
                    "浏览器进程所有权证据不完整，已停止自动控制。"
                )
            created_at = datetime.fromtimestamp(
                process.create_time(),
                tz=UTC,
            ).isoformat().replace("+00:00", "Z")
            return BrowserOwnershipEvidence(
                schemaVersion=1,
                runtimeGeneration=self._runtime_generation,
                executableCanonicalPathHash=_hash_path(executable),
                profileCanonicalPathHash=_hash_path(canonical_profile),
                processId=process.pid,
                processCreatedAt=created_at,
                launchNonceHash=marker.launchNonceHash,
                debugHost=launch.debug_host,
                debugPort=launch.debug_port,
                ownerMarkerVersion=marker.schemaVersion,
            )
        except BrowserProcessOwnershipError:
            raise
        except (OSError, ValueError, psutil.Error, json.JSONDecodeError) as exc:
            log.exception(
                "浏览器进程所有权校验失败",
                extra={"browser_instance_id": browser_instance_id},
            )
            raise BrowserProcessOwnershipError(
                "无法证明浏览器进程属于当前账号，请查看日志。"
            ) from exc

    def verify_existing(
        self,
        *,
        account_id: str,
        browser_instance_id: str,
        profile_path: Path,
        process_id: int,
        executable_path: str,
        debug_host: str,
        debug_port: int,
        runtime_evidence_json: str,
    ) -> None:
        try:
            evidence = BrowserOwnershipEvidence(**json.loads(runtime_evidence_json))
            process = self._process_factory(process_id)
            executable = Path(process.exe()).resolve(strict=True)
            canonical_profile = profile_path.resolve(strict=True)
            command_profile = _profile_from_command(process.cmdline())
            marker = _read_marker(profile_path)
            created_at = datetime.fromtimestamp(
                process.create_time(),
                tz=UTC,
            ).isoformat().replace("+00:00", "Z")
            valid = (
                process.pid == process_id
                and executable == Path(executable_path).resolve(strict=True)
                and _hash_path(executable) == evidence.executableCanonicalPathHash
                and command_profile is not None
                and command_profile.resolve(strict=True) == canonical_profile
                and _hash_path(canonical_profile) == evidence.profileCanonicalPathHash
                and created_at == evidence.processCreatedAt
                and evidence.processId == process_id
                and evidence.debugHost == debug_host == "127.0.0.1"
                and evidence.debugPort == debug_port
                and _process_owns_port(process, debug_port)
                and marker.accountId == account_id
                and marker.browserInstanceId == browser_instance_id
                and marker.launchNonceHash == evidence.launchNonceHash
                and marker.runtimeGeneration == evidence.runtimeGeneration
            )
            if not valid:
                raise BrowserProcessOwnershipError(
                    "浏览器既有进程所有权证据不完整，已停止自动控制。"
                )
        except BrowserProcessOwnershipError:
            raise
        except (OSError, TypeError, ValueError, psutil.Error, json.JSONDecodeError) as exc:
            log.exception(
                "浏览器既有进程所有权校验失败",
                extra={"browser_instance_id": browser_instance_id},
            )
            raise BrowserProcessOwnershipError(
                "无法证明既有浏览器进程属于当前账号，请人工检查。"
            ) from exc


def _marker_path(profile_path: Path) -> Path:
    return profile_path / ".tk-ops" / "runtime-owner.v1.json"


def _read_marker(profile_path: Path) -> BrowserOwnerMarker:
    payload = json.loads(_marker_path(profile_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {
        "schemaVersion",
        "accountId",
        "browserInstanceId",
        "createdAt",
        "launchNonceHash",
        "runtimeGeneration",
    }:
        raise ValueError("浏览器 owner marker 结构无效")
    return BrowserOwnerMarker(**payload)


def _profile_from_command(command: list[str]) -> Path | None:
    prefix = "--user-data-dir="
    for argument in command:
        if argument.startswith(prefix):
            value = argument[len(prefix) :].strip().strip('"')
            return Path(value) if value else None
    return None


def _process_owns_port(process: ProcessLike, debug_port: int) -> bool:
    for connection in process.net_connections(kind="tcp"):
        address = getattr(connection, "laddr", None)
        port = getattr(address, "port", None)
        host = getattr(address, "ip", None)
        if port == debug_port and host in {"127.0.0.1", "::1"}:
            return True
    return False


def _hash_path(path: Path) -> str:
    return _hash_text(str(path).casefold())


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
