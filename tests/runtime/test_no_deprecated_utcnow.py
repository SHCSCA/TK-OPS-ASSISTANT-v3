from __future__ import annotations

from pathlib import Path


def test_runtime_source_does_not_use_deprecated_utcnow() -> None:
    runtime_src = Path(__file__).resolve().parents[2] / "apps" / "py-runtime" / "src"
    offenders: list[str] = []

    for file_path in runtime_src.rglob("*.py"):
        if "__pycache__" in file_path.parts:
            continue
        text = file_path.read_text(encoding="utf-8")
        if "datetime.utcnow(" in text:
            offenders.append(str(file_path.relative_to(runtime_src)))

    assert offenders == []
