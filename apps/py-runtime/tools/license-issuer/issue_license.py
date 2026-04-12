from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
RUNTIME_SRC = CURRENT_FILE.parents[2] / "src"
REPO_ROOT = CURRENT_FILE.parents[4]
DEFAULT_PRIVATE_KEY_PATH = REPO_ROOT / ".runtime-data" / "licenses" / "license-private.pem"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from services.license_crypto import (  # noqa: E402
    LicensePayload,
    LicensePayloadError,
    load_private_key,
    sign_license_payload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="签发离线授权码")
    parser.add_argument("--machine-code", required=False, help="客户机机器码")
    parser.add_argument(
        "--private-key",
        type=Path,
        default=None,
        help="授权私钥路径；未提供时读取 TK_OPS_LICENSE_PRIVATE_KEY_PATH 或默认私钥路径",
    )
    parser.add_argument(
        "--plain-output",
        action="store_true",
        help="只输出授权码，不输出 JSON",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="交互式输入机器码，并在 Windows 上尝试复制授权码",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    machine_code = resolve_machine_code(args.machine_code, args.interactive)
    if not machine_code:
        print("机器码不能为空。", file=sys.stderr)
        return 1

    private_key_path = resolve_private_key_path(args.private_key)
    if not private_key_path.exists():
        print("未找到授权私钥。", file=sys.stderr)
        print(f"默认查找位置：{private_key_path}", file=sys.stderr)
        print(
            "请先运行：venv\\Scripts\\python.exe "
            "apps\\py-runtime\\tools\\license-issuer\\generate_keypair.py "
            "--output-dir .runtime-data\\licenses",
            file=sys.stderr,
        )
        return 1

    try:
        private_key = load_private_key(private_key_path)
        activation_code = sign_license_payload(
            LicensePayload(
                machine_code=machine_code,
                license_type="perpetual",
                issued_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                version=1,
            ),
            private_key,
        )
    except LicensePayloadError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.plain_output:
        print(activation_code)
    elif args.interactive:
        print()
        print("授权码如下：")
        print(activation_code)
        if copy_to_clipboard(activation_code):
            print("授权码已复制到剪贴板。")
        else:
            print("未能自动复制到剪贴板，请手动复制上方授权码。")
    else:
        print(
            json.dumps(
                {
                    "machineCode": machine_code,
                    "licenseType": "perpetual",
                    "activationCode": activation_code,
                },
                ensure_ascii=False,
            )
        )
    return 0


def resolve_machine_code(machine_code: str | None, interactive: bool) -> str:
    if machine_code is not None:
        return machine_code.strip().upper()

    if not interactive:
        return ""

    try:
        return input("请输入客户机机器码：").strip().upper()
    except EOFError:
        return ""


def resolve_private_key_path(private_key_path: Path | None) -> Path:
    if private_key_path is not None:
        return private_key_path.expanduser().resolve()

    env_path = os.getenv("TK_OPS_LICENSE_PRIVATE_KEY_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser().resolve()

    return DEFAULT_PRIVATE_KEY_PATH.resolve()


def copy_to_clipboard(value: str) -> bool:
    if sys.platform != "win32":
        return False

    try:
        result = subprocess.run(
            ["clip"],
            input=value,
            text=True,
            check=False,
            capture_output=True,
        )
    except OSError:
        return False

    return result.returncode == 0


if __name__ == "__main__":
    raise SystemExit(main())
