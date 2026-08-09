from __future__ import annotations

import json
from pathlib import Path

import pytest

from config.migration import (
    MigrationConfigurationError,
    load_migration_bootstrap_projection,
    resolve_migration_bootstrap_projection_path,
    resolve_migration_config,
    write_migration_bootstrap_projection,
)
from domain.models import Base
from persistence.engine import (
    create_runtime_engine,
    create_session_factory,
)
from repositories.system_config_repository import SystemConfigRepository
from services.config import ConfigBusService
from services.config.projection import MigrationBootstrapProjectionWriter


def test_projection_round_trip_has_revision_hash_and_unified_range(
    tmp_path: Path,
) -> None:
    written = write_migration_bootstrap_projection(
        tmp_path,
        config_revision=7,
        backup_retention_count=12,
    )

    loaded = load_migration_bootstrap_projection(
        resolve_migration_bootstrap_projection_path(tmp_path)
    )

    assert loaded == written
    assert len(written.sha256) == 64
    config = resolve_migration_config(
        tmp_path,
        tmp_path / "runtime.db",
        environ={},
    )
    assert config.backup_retention_count == 12
    assert config.backup_retention_source == "projection"
    assert config.bootstrap_projection_revision == 7


def test_corrupted_projection_fails_closed_before_database_open(
    tmp_path: Path,
) -> None:
    projection_path = resolve_migration_bootstrap_projection_path(tmp_path)
    write_migration_bootstrap_projection(
        tmp_path,
        config_revision=1,
        backup_retention_count=5,
    )
    document = json.loads(projection_path.read_text(encoding="utf-8"))
    document["values"]["migration.backupRetention"] = 50
    projection_path.write_text(
        json.dumps(document),
        encoding="utf-8",
    )

    with pytest.raises(MigrationConfigurationError, match="校验失败"):
        resolve_migration_config(
            tmp_path,
            tmp_path / "runtime.db",
            environ={},
        )

    assert not (tmp_path / "runtime.db").exists()


def test_deployment_environment_override_is_explicit_and_high_priority(
    tmp_path: Path,
) -> None:
    write_migration_bootstrap_projection(
        tmp_path,
        config_revision=3,
        backup_retention_count=8,
    )

    config = resolve_migration_config(
        tmp_path,
        tmp_path / "runtime.db",
        environ={"TK_OPS_MIGRATION_BACKUP_RETENTION": "9"},
    )

    assert config.backup_retention_count == 9
    assert config.backup_retention_source == "deployment_env"
    with pytest.raises(MigrationConfigurationError, match="1 到 50"):
        resolve_migration_config(
            tmp_path,
            tmp_path / "runtime.db",
            environ={"TK_OPS_MIGRATION_BACKUP_RETENTION": "51"},
        )


def test_config_bus_update_atomically_refreshes_bootstrap_projection(
    tmp_path: Path,
) -> None:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    repository = SystemConfigRepository(
        session_factory=create_session_factory(engine),
    )
    stored = repository.save({"logging": {"level": "INFO"}})
    service = ConfigBusService(
        repository,
        bootstrap_projection_writer=MigrationBootstrapProjectionWriter(
            tmp_path
        ),
    )

    service.sync_bootstrap_projection()
    result = service.update(
        {"migration.backupRetention": 17},
        expected_revision=stored.revision,
        request_id="req_p0f_projection",
        operation_id="op_p0f_projection",
    )
    projection = load_migration_bootstrap_projection(
        resolve_migration_bootstrap_projection_path(tmp_path)
    )

    assert projection is not None
    assert projection.config_revision == result.revision
    assert projection.backup_retention_count == 17
    engine.dispose()
