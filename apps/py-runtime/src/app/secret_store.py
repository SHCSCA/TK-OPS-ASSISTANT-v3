from __future__ import annotations

import base64
import ctypes
import json
import os
from pathlib import Path
from typing import Protocol

from app.config import RuntimeConfig


class SecretStore(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...


class FileSecretStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def get(self, key: str) -> str | None:
        return self._load().get(key)

    def set(self, key: str, value: str) -> None:
        payload = self._load()
        payload[key] = value
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def _load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}

        return json.loads(self._path.read_text(encoding='utf-8'))


class WindowsProtectedSecretStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def get(self, key: str) -> str | None:
        value = self._load().get(key)
        if value is None:
            return None

        return _dpapi_unprotect(value)

    def set(self, key: str, value: str) -> None:
        payload = self._load()
        payload[key] = _dpapi_protect(value)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def _load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}

        return json.loads(self._path.read_text(encoding='utf-8'))


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ('cbData', ctypes.c_uint32),
        ('pbData', ctypes.POINTER(ctypes.c_ubyte)),
    ]


def build_secret_store(runtime_config: RuntimeConfig) -> SecretStore:
    path = runtime_config.data_dir / 'secrets' / 'providers.json'
    if os.name == 'nt' and runtime_config.mode != 'test':
        return WindowsProtectedSecretStore(path)

    return FileSecretStore(path)


def _dpapi_protect(value: str) -> str:
    input_bytes = value.encode('utf-8')
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

    if not crypt_protect(ctypes.byref(input_blob), None, None, None, None, 0, ctypes.byref(output_blob)):
        raise OSError('Failed to protect secret with Windows DPAPI.')

    try:
        encrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return base64.b64encode(encrypted).decode('ascii')
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)


def _dpapi_unprotect(value: str) -> str:
    encrypted_bytes = base64.b64decode(value.encode('ascii'))
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

    if not crypt_unprotect(ctypes.byref(input_blob), None, None, None, None, 0, ctypes.byref(output_blob)):
        raise OSError('Failed to unprotect secret with Windows DPAPI.')

    try:
        decrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return decrypted.decode('utf-8')
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)
