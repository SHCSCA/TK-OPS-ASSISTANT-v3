use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

use super::{
    types::{
        ControlledFileCommandError, ControlledFileDto, ControlledFileError, ControlledFileFilters,
    },
    validation::DEFAULT_EXTENSIONS,
    ControlledFileRegistry,
};
use crate::workspace_roots::WorkspaceRootRegistry;

#[tauri::command(rename_all = "camelCase")]
pub fn pick_account_controlled_file(
    app: AppHandle,
    registry: State<'_, ControlledFileRegistry>,
    workspace_roots: State<'_, WorkspaceRootRegistry>,
    account_id: String,
    root_ref: String,
    filters: Option<ControlledFileFilters>,
) -> Result<Option<ControlledFileDto>, ControlledFileCommandError> {
    let selected = app
        .dialog()
        .file()
        .set_title("选择账号知识文件")
        .add_filter("支持的知识文件", DEFAULT_EXTENSIONS)
        .blocking_pick_file();
    let Some(selected) = selected else {
        return Ok(None);
    };
    let selected = selected.into_path().map_err(|_| {
        registry.public_error(
            "pick",
            ControlledFileError::new(
                "CONTROLLED_FILE_PATH_INVALID",
                "所选文件不是可用的本地路径，请重新选择。",
            ),
        )
    })?;
    let root = workspace_roots
        .resolve_owned_active(&account_id, &root_ref)
        .map_err(|error| {
            registry.public_error("pick", ControlledFileError::new(error.code, error.message))
        })?;
    registry
        .register(&account_id, &root_ref, &root, &selected, filters.as_ref())
        .map(Some)
        .map_err(|error| registry.public_error("pick", error))
}

#[tauri::command(rename_all = "camelCase")]
pub fn describe_account_controlled_file(
    registry: State<'_, ControlledFileRegistry>,
    workspace_roots: State<'_, WorkspaceRootRegistry>,
    account_id: String,
    file_ref: String,
) -> Result<ControlledFileDto, ControlledFileCommandError> {
    let owned = registry
        .describe_owned(&account_id, &file_ref)
        .map_err(|error| registry.public_error("describe", error))?;
    let root = workspace_roots
        .resolve_owned_active(&account_id, &owned.dto.root_ref)
        .map_err(|error| {
            registry.public_error(
                "describe",
                ControlledFileError::new(error.code, error.message),
            )
        })?;
    if root.revision != owned.root_revision {
        return Err(registry.public_error(
            "describe",
            ControlledFileError::new(
                "CONTROLLED_FILE_ROOT_CHANGED",
                "工作目录授权已变化，请重新选择文件。",
            ),
        ));
    }
    Ok(owned.dto)
}

#[tauri::command(rename_all = "camelCase")]
pub fn revoke_account_controlled_file(
    registry: State<'_, ControlledFileRegistry>,
    account_id: String,
    file_ref: String,
) -> Result<ControlledFileDto, ControlledFileCommandError> {
    registry
        .revoke(&account_id, &file_ref)
        .map_err(|error| registry.public_error("revoke", error))
}
