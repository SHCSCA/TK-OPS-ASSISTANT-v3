use std::{
    env, fs,
    path::{Component, Path, PathBuf},
};

use tauri::{path::BaseDirectory, AppHandle, Manager};

use crate::runtime_supervisor::SupervisorError;

pub struct AppPaths {
    pub bootstrap_config: PathBuf,
    pub controlled_file_registry: PathBuf,
    pub ffprobe_binary: PathBuf,
    pub resource_dir: PathBuf,
    pub runtime_data_dir: PathBuf,
    pub sidecar_binary: PathBuf,
    pub sidecar_manifest: PathBuf,
    pub supervisor_log: PathBuf,
    pub workspace_root_registry: PathBuf,
}

impl AppPaths {
    pub fn resolve(app: &AppHandle) -> Result<Self, SupervisorError> {
        let data_dir = resolve_app_data_dir(app)?;
        let runtime_data_dir = data_dir.join("runtime");
        let log_dir = data_dir.join("logs");
        create_directory(&runtime_data_dir)?;
        create_directory(&log_dir)?;

        let resource_dir = app.path().resource_dir().map_err(|_| {
            SupervisorError::permanent(
                "RESOURCE_DIRECTORY_UNAVAILABLE",
                "无法解析应用资源目录，请重新安装应用。",
            )
        })?;
        let bootstrap_config = app
            .path()
            .resolve(
                "resources/runtime/runtime-supervisor.bootstrap.json",
                BaseDirectory::Resource,
            )
            .map_err(|_| {
                SupervisorError::permanent(
                    "RUNTIME_BOOTSTRAP_PATH_UNAVAILABLE",
                    "无法解析 Runtime 启动配置，请重新安装应用。",
                )
            })?;
        let sidecar_manifest = app
            .path()
            .resolve(
                "resources/runtime/tk-ops-runtime.manifest.json",
                BaseDirectory::Resource,
            )
            .map_err(|_| {
                SupervisorError::permanent(
                    "RUNTIME_MANIFEST_PATH_UNAVAILABLE",
                    "无法解析 Runtime 制品清单，请重新安装应用。",
                )
            })?;
        let sidecar_binary = app
            .path()
            .resolve(
                "resources/runtime/tk-ops-runtime.exe",
                BaseDirectory::Resource,
            )
            .map_err(|_| {
                SupervisorError::permanent(
                    "RUNTIME_SIDECAR_PATH_UNAVAILABLE",
                    "无法解析 Runtime 程序路径，请重新安装应用。",
                )
            })?;
        let ffprobe_binary = app
            .path()
            .resolve(
                "resources/bin/ffprobe/windows-x64/ffprobe.exe",
                BaseDirectory::Resource,
            )
            .map_err(|_| {
                SupervisorError::permanent(
                    "MEDIA_TOOL_PATH_UNAVAILABLE",
                    "无法解析媒体工具，请重新安装应用。",
                )
            })?;
        Ok(Self {
            bootstrap_config,
            controlled_file_registry: data_dir.join("controlled-files.v1.json"),
            ffprobe_binary,
            resource_dir,
            runtime_data_dir,
            sidecar_binary,
            sidecar_manifest,
            supervisor_log: log_dir.join("runtime-supervisor.jsonl"),
            workspace_root_registry: data_dir.join("workspace-roots.v1.json"),
        })
    }
}

pub(crate) fn resolve_app_data_dir(app: &AppHandle) -> Result<PathBuf, SupervisorError> {
    if env::var("TK_OPS_INSTALLER_SMOKE").ok().as_deref() == Some("1") {
        return resolve_smoke_data_dir();
    }
    app.path().app_local_data_dir().map_err(|_| {
        SupervisorError::permanent(
            "APP_DATA_PATH_UNAVAILABLE",
            "无法解析应用数据目录，请检查系统权限。",
        )
    })
}

fn resolve_smoke_data_dir() -> Result<PathBuf, SupervisorError> {
    let raw_path = env::var("TK_OPS_INSTALLER_SMOKE_DATA_DIR").unwrap_or_default();
    let candidate = PathBuf::from(raw_path.trim());
    let temporary_root = env::temp_dir();
    if !candidate.is_absolute()
        || candidate == temporary_root
        || candidate
            .components()
            .any(|component| matches!(component, Component::ParentDir | Component::CurDir))
        || !candidate.starts_with(&temporary_root)
    {
        return Err(SupervisorError::permanent(
            "INSTALLER_SMOKE_DATA_DIR_INVALID",
            "安装包验收数据目录无效。",
        ));
    }
    create_directory(&candidate)?;
    let canonical_root = fs::canonicalize(&temporary_root).map_err(|_| {
        SupervisorError::permanent(
            "INSTALLER_SMOKE_TEMP_UNAVAILABLE",
            "安装包验收临时目录不可用。",
        )
    })?;
    let canonical_candidate = fs::canonicalize(&candidate).map_err(|_| {
        SupervisorError::permanent(
            "INSTALLER_SMOKE_DATA_DIR_UNAVAILABLE",
            "安装包验收数据目录不可用。",
        )
    })?;
    if canonical_candidate == canonical_root || !canonical_candidate.starts_with(canonical_root) {
        return Err(SupervisorError::permanent(
            "INSTALLER_SMOKE_DATA_DIR_OUT_OF_SCOPE",
            "安装包验收数据目录超出临时目录。",
        ));
    }
    // 范围校验使用规范路径，传给 Python 时保留普通 Windows 绝对路径。
    Ok(candidate)
}

fn create_directory(path: &Path) -> Result<(), SupervisorError> {
    fs::create_dir_all(path).map_err(|_| {
        SupervisorError::permanent(
            "APP_DATA_DIRECTORY_CREATE_FAILED",
            "无法创建应用数据目录，请检查系统权限。",
        )
    })
}
