from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

CURRENT_FILE = Path(__file__).resolve()
RUNTIME_SRC = CURRENT_FILE.parents[2] / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from services.license_crypto import export_private_key_pem, export_public_key_pem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成离线授权签名密钥对")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="密钥输出目录",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    private_key_path = output_dir / "license-private.pem"
    public_key_path = output_dir / "license-public.pem"
    existing_paths = [
        path
        for path in (private_key_path, public_key_path)
        if path.exists()
    ]
    if existing_paths:
        print("密钥文件已存在，已拒绝覆盖。", file=sys.stderr)
        for path in existing_paths:
            print(f"现有文件：{path}", file=sys.stderr)
        print("许可证密钥对只能初始化一次；轮换前必须先制定兼容与重新签发方案。", file=sys.stderr)
        return 1

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()
        private_key_path.write_bytes(export_private_key_pem(private_key))
        public_key_path.write_bytes(export_public_key_pem(private_key))
    except OSError as exc:
        print(f"写入许可证密钥对失败：{exc}", file=sys.stderr)
        return 1

    print(f"私钥已生成：{private_key_path}")
    print(f"公钥已生成：{public_key_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
