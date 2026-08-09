from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

runtime_root = Path(SPECPATH).resolve().parent
source_root = runtime_root / "src"

hidden_imports = [
    *collect_submodules("alembic"),
    *collect_submodules("persistence.migration"),
    *collect_submodules("sqlalchemy.dialects.sqlite"),
    *collect_submodules("uvicorn"),
    *collect_submodules("websockets"),
]

analysis = Analysis(
    [str(source_root / "sidecar_main.py")],
    pathex=[str(source_root)],
    binaries=[],
    datas=[
        *copy_metadata("tk-ops-runtime"),
        (
            str(runtime_root / "alembic.ini"),
            "apps/py-runtime",
        ),
        (
            str(runtime_root / "alembic"),
            "apps/py-runtime/alembic",
        ),
        (
            str(runtime_root / "pyproject.toml"),
            "apps/py-runtime",
        ),
        (
            str(runtime_root / "resources"),
            "apps/py-runtime/resources",
        ),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "httpx", "greenlet"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="tk-ops-runtime",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=True,
)
