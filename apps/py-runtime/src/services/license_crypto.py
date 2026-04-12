from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


@dataclass(frozen=True, slots=True)
class LicensePayload:
    machine_code: str
    license_type: str
    issued_at: str
    version: int

    def to_json_bytes(self) -> bytes:
        return json.dumps(
            {
                "machineCode": self.machine_code,
                "licenseType": self.license_type,
                "issuedAt": self.issued_at,
                "version": self.version,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")


class LicensePayloadError(ValueError):
    pass


def load_public_key(path: Path) -> Ed25519PublicKey:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise LicensePayloadError("公钥未配置") from exc

    try:
        key = serialization.load_pem_public_key(payload)
    except ValueError as exc:
        raise LicensePayloadError("公钥未配置") from exc

    if not isinstance(key, Ed25519PublicKey):
        raise LicensePayloadError("公钥未配置")

    return key


def load_private_key(path: Path) -> Ed25519PrivateKey:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise LicensePayloadError("未找到授权私钥") from exc

    try:
        key = serialization.load_pem_private_key(payload, password=None)
    except ValueError as exc:
        raise LicensePayloadError("未找到授权私钥") from exc

    if not isinstance(key, Ed25519PrivateKey):
        raise LicensePayloadError("未找到授权私钥")

    return key


def sign_license_payload(payload: LicensePayload, private_key: Ed25519PrivateKey) -> str:
    payload_bytes = payload.to_json_bytes()
    signature = private_key.sign(payload_bytes)
    return f"{_base64url_encode(payload_bytes)}.{_base64url_encode(signature)}"


def verify_activation_code(
    activation_code: str,
    public_key: Ed25519PublicKey,
) -> tuple[LicensePayload, str]:
    normalized_code = activation_code.strip()
    if "." not in normalized_code:
        raise LicensePayloadError("授权码格式非法")

    payload_part, signature_part = normalized_code.split(".", maxsplit=1)
    try:
        payload_bytes = _base64url_decode(payload_part)
        signature = _base64url_decode(signature_part)
    except ValueError as exc:
        raise LicensePayloadError("授权码格式非法") from exc

    try:
        public_key.verify(signature, payload_bytes)
    except InvalidSignature as exc:
        raise LicensePayloadError("签名校验失败") from exc

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LicensePayloadError("授权码格式非法") from exc

    try:
        parsed = LicensePayload(
            machine_code=str(payload["machineCode"]),
            license_type=str(payload["licenseType"]),
            issued_at=str(payload["issuedAt"]),
            version=int(payload["version"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LicensePayloadError("授权码格式非法") from exc

    return parsed, payload_part


def mask_activation_code(activation_code: str) -> str:
    normalized_code = activation_code.strip()
    if len(normalized_code) <= 12:
        return "*" * len(normalized_code)

    return f"{normalized_code[:4]}{'*' * 16}{normalized_code[-4:]}"


def export_public_key_pem(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def export_private_key_pem(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))
