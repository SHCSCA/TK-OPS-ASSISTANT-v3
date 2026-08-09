from __future__ import annotations

from pathlib import Path

from app.config import RuntimeBootstrapConfig, load_runtime_config


def test_runtime_workspace_registry_path_comes_from_host_environment(
    monkeypatch,
    tmp_path: Path,
) -> None:
    registry = tmp_path / "workspace-roots.v1.json"
    monkeypatch.setenv("TK_OPS_WORKSPACE_ROOT_REGISTRY_PATH", str(registry))
    monkeypatch.setenv("TK_OPS_RUNTIME_MODE", "test")

    config = load_runtime_config(
        RuntimeBootstrapConfig(repo_root=tmp_path, data_dir=tmp_path / "runtime")
    )

    assert config.workspace_root_registry_path == registry.resolve()


def test_tauri_contract_registers_all_workspace_root_commands() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    main_source = (
        repository_root / "apps" / "desktop" / "src-tauri" / "src" / "main.rs"
    ).read_text(encoding="utf-8")
    process_source = (
        repository_root
        / "apps"
        / "desktop"
        / "src-tauri"
        / "src"
        / "runtime_supervisor"
        / "process.rs"
    ).read_text(encoding="utf-8")
    commands_source = (
        repository_root
        / "apps"
        / "desktop"
        / "src-tauri"
        / "src"
        / "workspace_roots"
        / "commands.rs"
    ).read_text(encoding="utf-8")

    for command in (
        "pick_account_workspace_root",
        "describe_account_workspace_root",
        "reauthorize_account_workspace_root",
        "revoke_account_workspace_root",
    ):
        assert command in main_source
        assert command in commands_source
    assert "TK_OPS_WORKSPACE_ROOT_REGISTRY_PATH" in process_source
    assert "return Ok(None)" in commands_source
