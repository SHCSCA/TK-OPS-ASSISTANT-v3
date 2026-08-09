use std::sync::Arc;

use tauri::State;

use super::{
    RuntimeConnectionInfo, RuntimeSupervisor, SupervisorCommandError,
    SupervisorDiagnosticExportDto, SupervisorDiagnosticsDto, SupervisorStatusDto,
};

#[tauri::command]
pub fn get_runtime_connection(
    state: State<'_, Arc<RuntimeSupervisor>>,
) -> Result<RuntimeConnectionInfo, SupervisorCommandError> {
    state.connection()
}

#[tauri::command]
pub fn get_runtime_supervisor_status(
    state: State<'_, Arc<RuntimeSupervisor>>,
) -> SupervisorStatusDto {
    state.status()
}

#[tauri::command]
pub fn get_runtime_supervisor_diagnostics(
    state: State<'_, Arc<RuntimeSupervisor>>,
) -> SupervisorDiagnosticsDto {
    state.diagnostics()
}

#[tauri::command]
pub fn export_runtime_supervisor_diagnostics(
    state: State<'_, Arc<RuntimeSupervisor>>,
) -> Result<SupervisorDiagnosticExportDto, SupervisorCommandError> {
    state.export_diagnostics()
}

#[tauri::command]
pub fn restart_runtime(
    state: State<'_, Arc<RuntimeSupervisor>>,
) -> Result<SupervisorStatusDto, SupervisorCommandError> {
    state.restart()
}
