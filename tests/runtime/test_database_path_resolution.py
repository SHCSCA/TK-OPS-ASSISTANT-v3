from __future__ import annotations

import logging
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.config import load_runtime_config
from config.database import (
    DatabasePathConfigurationError,
    database_path_to_url,
    resolve_database_path,
    resolve_runtime_data_dir,
)


def test_database_path_defaults_to_runtime_data_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_path_environment(monkeypatch)

    database_path = resolve_database_path(tmp_path)

    assert database_path == (tmp_path / "runtime.db").resolve()


@pytest.mark.parametrize(
    "variable_name",
    ["TK_OPS_RUNTIME_DB_PATH", "TK_OPS_DATABASE_PATH"],
)
def test_database_path_accepts_each_compatible_environment_variable(
    variable_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_path_environment(monkeypatch)
    configured_path = tmp_path / "configured.db"
    monkeypatch.setenv(variable_name, str(configured_path))

    assert resolve_database_path(tmp_path) == configured_path.resolve()


def test_database_path_accepts_matching_compatible_environment_variables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured_path = tmp_path / "configured.db"
    monkeypatch.setenv("TK_OPS_RUNTIME_DB_PATH", str(configured_path))
    monkeypatch.setenv(
        "TK_OPS_DATABASE_PATH",
        str(configured_path.parent / "." / configured_path.name),
    )

    assert resolve_database_path(tmp_path) == configured_path.resolve()


def test_relative_database_path_is_anchored_to_runtime_data_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = (tmp_path / "runtime-data").resolve()
    first_working_directory = tmp_path / "first-working-directory"
    second_working_directory = tmp_path / "second-working-directory"
    first_working_directory.mkdir()
    second_working_directory.mkdir()
    monkeypatch.setenv("TK_OPS_RUNTIME_DB_PATH", "nested/runtime.db")

    monkeypatch.chdir(first_working_directory)
    first = resolve_database_path(data_dir)
    monkeypatch.chdir(second_working_directory)
    second = resolve_database_path(data_dir)

    assert first == second == (data_dir / "nested" / "runtime.db").resolve()


def test_relative_runtime_data_dir_is_anchored_to_default_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default_data_dir = (tmp_path / "repo" / ".runtime-data").resolve()
    working_directory = tmp_path / "working-directory"
    working_directory.mkdir()
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", "custom-data")
    monkeypatch.chdir(working_directory)

    assert resolve_runtime_data_dir(default_data_dir) == (
        default_data_dir.parent / "custom-data"
    ).resolve()


def test_database_path_rejects_conflicting_compatible_environment_variables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("TK_OPS_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    monkeypatch.setenv("TK_OPS_DATABASE_PATH", str(tmp_path / "legacy.db"))

    with caplog.at_level(logging.ERROR), pytest.raises(
        DatabasePathConfigurationError,
        match="数据库路径配置冲突",
    ):
        resolve_database_path(tmp_path)

    assert "数据库路径配置解析失败" in caplog.text


def test_runtime_config_uses_shared_database_path_resolver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_path_environment(monkeypatch)
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", str(tmp_path))

    runtime_config = load_runtime_config()

    assert runtime_config.database_path == (tmp_path / "runtime.db").resolve()


def test_runtime_config_rejects_conflicting_database_environment_variables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TK_OPS_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    monkeypatch.setenv("TK_OPS_DATABASE_PATH", str(tmp_path / "legacy.db"))

    with pytest.raises(DatabasePathConfigurationError, match="数据库路径配置冲突"):
        load_runtime_config()


@pytest.mark.parametrize("override_kind", ["attribute", "option"])
def test_programmatic_alembic_database_url_override_is_respected(
    override_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_path_environment(monkeypatch)
    database_path = tmp_path / f"{override_kind}.db"
    config = _alembic_config()
    database_url = database_path_to_url(database_path.resolve())
    if override_kind == "attribute":
        config.attributes["database_url"] = database_url
    else:
        config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    assert database_path.exists()


def test_alembic_cli_default_uses_runtime_data_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_path_environment(monkeypatch)
    data_dir = tmp_path / "runtime-data"
    working_directory = tmp_path / "working-directory"
    working_directory.mkdir()
    monkeypatch.setenv("TK_OPS_RUNTIME_DATA_DIR", str(data_dir))
    monkeypatch.chdir(working_directory)

    command.upgrade(_alembic_config(), "head")

    assert (data_dir / "runtime.db").exists()
    assert not (working_directory / "runtime.db").exists()


def test_alembic_cli_rejects_conflicting_database_environment_variables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_database_path = tmp_path / "runtime.db"
    legacy_database_path = tmp_path / "legacy.db"
    monkeypatch.setenv("TK_OPS_RUNTIME_DB_PATH", str(runtime_database_path))
    monkeypatch.setenv("TK_OPS_DATABASE_PATH", str(legacy_database_path))

    with pytest.raises(DatabasePathConfigurationError, match="数据库路径配置冲突"):
        command.upgrade(_alembic_config(), "head")

    assert not runtime_database_path.exists()
    assert not legacy_database_path.exists()


def test_alembic_does_not_reconfigure_root_logging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_path_environment(monkeypatch)
    config = _alembic_config()
    config.attributes["database_url"] = database_path_to_url(
        (tmp_path / "logging.db").resolve()
    )
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level
    sentinel_handler = logging.NullHandler()
    root_logger.handlers = [sentinel_handler]
    root_logger.setLevel(logging.DEBUG)

    try:
        command.upgrade(config, "head")

        assert root_logger.handlers == [sentinel_handler]
        assert root_logger.level == logging.DEBUG
    finally:
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)


def _alembic_config() -> Config:
    repo_root = Path(__file__).resolve().parents[2]
    runtime_root = repo_root / "apps" / "py-runtime"
    config = Config(str(runtime_root / "alembic.ini"))
    config.set_main_option("script_location", str(runtime_root / "alembic"))
    return config


def _clear_database_path_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TK_OPS_RUNTIME_DB_PATH", raising=False)
    monkeypatch.delenv("TK_OPS_DATABASE_PATH", raising=False)
