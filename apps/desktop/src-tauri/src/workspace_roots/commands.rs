use std::path::PathBuf;

use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

use super::{
    types::{WorkspaceRootCommandError, WorkspaceRootDto, WorkspaceRootError},
    WorkspaceRootRegistry,
};

#[tauri::command(rename_all = "camelCase")]
pub fn pick_account_workspace_root(
    app: AppHandle,
    registry: State<'_, WorkspaceRootRegistry>,
    account_id: String,
    suggested_name: Option<String>,
) -> Result<Option<WorkspaceRootDto>, WorkspaceRootCommandError> {
    let title = suggested_name
        .filter(|value| !value.trim().is_empty())
        .map(|value| format!("为 {value} 选择工作目录"))
        .unwrap_or_else(|| "选择账号工作目录".to_owned());
    let selected = app.dialog().file().set_title(title).blocking_pick_folder();
    let Some(path) = selected else {
        return Ok(None);
    };
    let path = path.into_path().map_err(|_| {
        registry.public_error(
            "pick",
            WorkspaceRootError::new(
                "WORKSPACE_ROOT_PATH_UNAVAILABLE",
                "所选目录不是可用的本地路径，请重新选择。",
            ),
        )
    })?;
    registry
        .register(&account_id, &path)
        .map(Some)
        .map_err(|error| registry.public_error("pick", error))
}

#[tauri::command(rename_all = "camelCase")]
pub fn describe_account_workspace_root(
    registry: State<'_, WorkspaceRootRegistry>,
    account_id: String,
    root_ref: String,
) -> Result<WorkspaceRootDto, WorkspaceRootCommandError> {
    registry
        .describe(&account_id, &root_ref)
        .map_err(|error| registry.public_error("describe", error))
}

#[tauri::command(rename_all = "camelCase")]
pub fn reauthorize_account_workspace_root(
    app: AppHandle,
    registry: State<'_, WorkspaceRootRegistry>,
    account_id: String,
    root_ref: String,
) -> Result<Option<WorkspaceRootDto>, WorkspaceRootCommandError> {
    let selected = app
        .dialog()
        .file()
        .set_title("重新授权账号工作目录")
        .blocking_pick_folder();
    let Some(path) = selected else {
        return Ok(None);
    };
    let path: PathBuf = path.into_path().map_err(|_| {
        registry.public_error(
            "reauthorize",
            WorkspaceRootError::new(
                "WORKSPACE_ROOT_PATH_UNAVAILABLE",
                "所选目录不是可用的本地路径，请重新选择。",
            ),
        )
    })?;
    registry
        .reauthorize(&account_id, &root_ref, &path)
        .map(Some)
        .map_err(|error| registry.public_error("reauthorize", error))
}

#[tauri::command(rename_all = "camelCase")]
pub fn revoke_account_workspace_root(
    registry: State<'_, WorkspaceRootRegistry>,
    account_id: String,
    root_ref: String,
) -> Result<WorkspaceRootDto, WorkspaceRootCommandError> {
    registry
        .revoke(&account_id, &root_ref)
        .map_err(|error| registry.public_error("revoke", error))
}
