from __future__ import annotations

import base64
import ctypes
import json
import logging
import os
import tempfile
from pathlib import Path
from threading import Lock, RLock
from typing import Protocol

from app.config import RuntimeConfig

log = logging.getLogger(__name__)

_PATH_LOCKS_GUARD = Lock()
_PATH_LOCKS: dict[str, RLock] = {}


class SecretStore(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...

    def delete(self, key: str) -> None: ...


class _JsonSecretStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = _lock_for_path(path)

    def get(self, key: str) -> str | None:
        try:
            with self._lock:
                stored_value = self._load_unlocked().get(key)
                if stored_value is None:
                    return None
                return self._decode_value(stored_value)
        except Exception:
            log.exception("读取安全存储失败")
            raise

    def set(self, key: str, value: str) -> None:
        try:
            with self._lock:
                payload = self._load_unlocked()
                payload[key] = self._encode_value(value)
                _atomic_write_json(self._path, payload)
        except Exception:
            log.exception("写入安全存储失败")
            raise

    def delete(self, key: str) -> None:
        try:
            with self._lock:
                payload = self._load_unlocked()
                if key not in payload:
                    return
                del payload[key]
                _atomic_write_json(self._path, payload)
        except Exception:
            log.exception("删除安全存储记录失败")
            raise

    def _load_unlocked(self) -> dict[str, str]:
        if not self._path.exists():
            return {}

        payload = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in payload.items()
        ):
            raise ValueError("安全存储文件格式无效")
        return payload

    def _encode_value(self, value: str) -> str:
        return value

    def _decode_value(self, value: str) -> str:
        return value


class FileSecretStore(_JsonSecretStore):
    pass


class WindowsProtectedSecretStore(_JsonSecretStore):
    def _encode_value(self, value: str) -> str:
        return _dpapi_protect(value)

    def _decode_value(self, value: str) -> str:
        return _dpapi_unprotect(value)


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ('cbData', ctypes.c_uint32),
        ('pbData', ctypes.POINTER(ctypes.c_ubyte)),
    ]


def build_secret_store(runtime_config: RuntimeConfig) -> SecretStore:
    path = runtime_config.data_dir / "secrets" / "providers.json"
    if os.name == "nt" and runtime_config.mode != "test":
        return WindowsProtectedSecretStore(path)

    return FileSecretStore(path)


def _lock_for_path(path: Path) -> RLock:
    normalized_path = os.path.normcase(
        str(path.expanduser().resolve(strict=False))
    )
    with _PATH_LOCKS_GUARD:
        lock = _PATH_LOCKS.get(normalized_path)
        if lock is None:
            lock = RLock()
            _PATH_LOCKS[normalized_path] = lock
        return lock


def _atomic_write_json(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        stream = os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        )
        descriptor = -1
        with stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except Exception:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                log.warning("关闭安全存储临时文件失败", exc_info=True)
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            log.warning("清理安全存储临时文件失败", exc_info=True)
        raise


def _dpapi_protect(value: str) -> str:
    input_bytes = value.encode("utf-8")
    input_buffer = ctypes.create_string_buffer(input_bytes)
    input_blob = _DataBlob(
        cbData=len(input_bytes),
        pbData=ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    output_blob = _DataBlob()

    crypt_protect = ctypes.windll.crypt32.CryptProtectData
    crypt_protect.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.c_wchar_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(_DataBlob),
    ]
    crypt_protect.restype = ctypes.c_int

    if not crypt_protect(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise OSError("使用 Windows DPAPI 加密安全存储失败")

    try:
        encrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return base64.b64encode(encrypted).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)


def _dpapi_unprotect(value: str) -> str:
    encrypted_bytes = base64.b64decode(value.encode("ascii"))
    input_buffer = ctypes.create_string_buffer(encrypted_bytes)
    input_blob = _DataBlob(
        cbData=len(encrypted_bytes),
        pbData=ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    output_blob = _DataBlob()

    crypt_unprotect = ctypes.windll.crypt32.CryptUnprotectData
    crypt_unprotect.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(ctypes.c_wchar_p),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(_DataBlob),
    ]
    crypt_unprotect.restype = ctypes.c_int

    if not crypt_unprotect(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise OSError("使用 Windows DPAPI 解密安全存储失败")

    try:
        decrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return decrypted.decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)
