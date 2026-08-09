from __future__ import annotations

from app.config import RuntimeConfig
from app.secret_store import SecretStore
from repositories.license_repository import LicenseRepository
from services.bootstrap_v1.directories import DirectoryV1Service, WorkspaceRootResolver
from services.bootstrap_v1.license import LicenseV1Service
from services.bootstrap_v1.service import BootstrapV1Service, SystemTaskSubmitter
from services.events import RuntimeEventService
from services.license_activation_base import LicenseActivationAdapter
from services.machine_code import MachineCodeService


def build_bootstrap_v1_service(
    *,
    runtime_config: RuntimeConfig,
    license_repository: LicenseRepository,
    activation_adapter: LicenseActivationAdapter,
    secret_store: SecretStore,
    task_submitter: SystemTaskSubmitter | None = None,
    workspace_root_resolver: WorkspaceRootResolver | None = None,
    event_service: RuntimeEventService | None = None,
    machine_factor_timeout_seconds: int = 10,
    machine_factor_retry_attempts: int = 1,
) -> BootstrapV1Service:
    return BootstrapV1Service(
        runtime_config=runtime_config,
        license_service=LicenseV1Service(
            repository=license_repository,
            activation_adapter=activation_adapter,
            machine_code_service=MachineCodeService(
                secret_store=secret_store,
                runtime_mode=runtime_config.mode,
                factor_timeout_seconds=machine_factor_timeout_seconds,
                factor_retry_attempts=machine_factor_retry_attempts,
                allow_test_override=True,
            ),
            secret_store=secret_store,
            event_service=event_service,
        ),
        directory_service=DirectoryV1Service(
            runtime_config=runtime_config,
            workspace_root_resolver=workspace_root_resolver,
            event_service=event_service,
        ),
        task_submitter=task_submitter,
    )
