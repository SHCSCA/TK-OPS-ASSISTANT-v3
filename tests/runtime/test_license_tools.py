from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

from services.license_crypto import load_public_key, verify_activation_code


TOOLS_DIR = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "py-runtime"
    / "tools"
    / "license-issuer"
)
REPO_ROOT = TOOLS_DIR.parents[3]


def test_generate_keypair_script_creates_public_and_private_key(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS_DIR / "generate_keypair.py"),
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    private_key_path = tmp_path / "license-private.pem"
    public_key_path = tmp_path / "license-public.pem"
    assert private_key_path.exists()
    assert public_key_path.exists()
    assert "license-public.pem" in result.stdout


def test_generate_keypair_script_refuses_to_overwrite_existing_pair(
    tmp_path: Path,
) -> None:
    _generate_keypair(tmp_path)
    private_key_path = tmp_path / "license-private.pem"
    public_key_path = tmp_path / "license-public.pem"
    private_before = private_key_path.read_bytes()
    public_before = public_key_path.read_bytes()

    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS_DIR / "generate_keypair.py"),
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "已拒绝覆盖" in result.stderr
    assert private_key_path.read_bytes() == private_before
    assert public_key_path.read_bytes() == public_before


def test_issue_license_script_signs_activation_code(tmp_path: Path) -> None:
    _generate_keypair(tmp_path)

    env = _issuer_env(tmp_path)
    machine_code = "TKOPS-TEST1-TEST2-TEST3-TEST4-TEST5"
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS_DIR / "issue_license.py"),
            "--machine-code",
            machine_code,
        ],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    activation_code = str(payload["activationCode"])
    verified_payload, _ = verify_activation_code(
        activation_code,
        load_public_key(tmp_path / "license-public.pem"),
    )
    assert verified_payload.machine_code == machine_code
    assert verified_payload.license_type == "perpetual"
    assert str(payload["publicKeyFingerprint"]).startswith("ED25519-")


def test_issue_license_script_interactive_mode_accepts_stdin(tmp_path: Path) -> None:
    _generate_keypair(tmp_path)

    env = _issuer_env(tmp_path)
    machine_code = "TKOPS-TEST1-TEST2-TEST3-TEST4-TEST5"
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS_DIR / "issue_license.py"),
            "--interactive",
        ],
        input=f"{machine_code}\n",
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )

    activation_code = result.stdout.split("授权码如下：", maxsplit=1)[1].strip().splitlines()[0]
    verified_payload, _ = verify_activation_code(
        activation_code,
        load_public_key(tmp_path / "license-public.pem"),
    )
    assert verified_payload.machine_code == machine_code


def test_issue_license_script_rejects_mismatched_runtime_public_key(
    tmp_path: Path,
) -> None:
    issuer_dir = tmp_path / "issuer"
    runtime_dir = tmp_path / "runtime"
    _generate_keypair(issuer_dir)
    _generate_keypair(runtime_dir)
    env = os.environ.copy()
    env["TK_OPS_LICENSE_PRIVATE_KEY_PATH"] = str(
        issuer_dir / "license-private.pem"
    )
    env["TK_OPS_LICENSE_PUBLIC_KEY_PATH"] = str(
        runtime_dir / "license-public.pem"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS_DIR / "issue_license.py"),
            "--machine-code",
            "TKOPS-TEST1-TEST2-TEST3-TEST4-TEST5",
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "签发私钥与 Runtime 验签公钥不匹配" in result.stderr


def test_issue_license_bat_is_ascii_wrapper() -> None:
    bat_content = (TOOLS_DIR / "issue-license.bat").read_text(encoding="utf-8")

    bat_content.encode("ascii")
    assert "--interactive" in bat_content


def test_issue_license_script_rejects_missing_private_key(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["TK_OPS_LICENSE_PRIVATE_KEY_PATH"] = str(tmp_path / "missing.pem")
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS_DIR / "issue_license.py"),
            "--machine-code",
            "TKOPS-TEST1-TEST2-TEST3-TEST4-TEST5",
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "未找到授权私钥" in result.stderr


def test_issue_license_script_uses_default_private_key_path(
    monkeypatch,
) -> None:
    monkeypatch.delenv("TK_OPS_LICENSE_PRIVATE_KEY_PATH", raising=False)
    script = runpy.run_path(str(TOOLS_DIR / "issue_license.py"))

    resolved = script["resolve_private_key_path"](None)

    assert resolved == (
        REPO_ROOT / ".runtime-data" / "licenses" / "license-private.pem"
    ).resolve()


def _generate_keypair(output_dir: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(TOOLS_DIR / "generate_keypair.py"),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def _issuer_env(key_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["TK_OPS_LICENSE_PRIVATE_KEY_PATH"] = str(
        key_dir / "license-private.pem"
    )
    env["TK_OPS_LICENSE_PUBLIC_KEY_PATH"] = str(
        key_dir / "license-public.pem"
    )
    return env
