use std::{
    fs::{self, File, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
    sync::{Mutex, MutexGuard},
};

use chrono::Utc;
use rand::{rngs::OsRng, RngCore};
use tauri::AppHandle;

use super::{
    logging::record_failure,
    types::{
        ResolvedWorkspaceRoot, WorkspaceRootCommandError, WorkspaceRootDto, WorkspaceRootError,
        WorkspaceRootRecord, WorkspaceRootRegistryFile,
    },
    validation::{system_restricted_roots, validate_account_id, validate_selected_root},
};
use crate::app_paths::resolve_app_data_dir;

const MAX_REGISTRY_BYTES: u64 = 1024 * 1024;

pub struct WorkspaceRootRegistry {
    lock: Mutex<()>,
    log_path: PathBuf,
    path: PathBuf,
    restricted_roots: Vec<PathBuf>,
}

impl WorkspaceRootRegistry {
    pub fn initialize(app: &AppHandle) -> Result<Self, WorkspaceRootCommandError> {
        let app_data_root = resolve_app_data_dir(app).map_err(|_| {
            command_error(
                "WORKSPACE_ROOT_REGISTRY_PATH_UNAVAILABLE",
                "无法解析工作目录注册表，请重新启动应用。",
            )
        })?;
        let runtime_data_root = app_data_root.join("runtime");
        let log_root = app_data_root.join("logs");
        fs::create_dir_all(&app_data_root).map_err(|_| {
            command_error(
                "WORKSPACE_ROOT_REGISTRY_DIRECTORY_FAILED",
                "无法创建工作目录注册表，请检查系统权限。",
            )
        })?;
        fs::create_dir_all(&log_root).map_err(|_| {
            command_error(
                "WORKSPACE_ROOT_LOG_DIRECTORY_FAILED",
                "无法创建工作目录日志，请检查系统权限。",
            )
        })?;
        let registry = Self {
            lock: Mutex::new(()),
            log_path: log_root.join("workspace-roots.jsonl"),
            path: app_data_root.join("workspace-roots.v1.json"),
            restricted_roots: system_restricted_roots(&app_data_root, &runtime_data_root),
        };
        if !registry.path.exists() {
            registry
                .write_registry(&WorkspaceRootRegistryFile::default())
                .map_err(|error| registry.public_error("initialize", error))?;
        } else {
            registry
                .load_registry()
                .map_err(|error| registry.public_error("initialize", error))?;
        }
        Ok(registry)
    }

    pub fn register(
        &self,
        account_id: &str,
        selected: &Path,
    ) -> Result<WorkspaceRootDto, WorkspaceRootError> {
        validate_account_id(account_id)?;
        let _guard = self.guard()?;
        let mut registry = self.load_registry()?;
        let occupied = registry
            .roots
            .iter()
            .filter(|root| root.account_id != account_id && root.status == "active")
            .map(|root| PathBuf::from(&root.canonical_path))
            .collect::<Vec<_>>();
        let validated = validate_selected_root(selected, &self.restricted_roots, &occupied)?;
        if let Some(existing) = registry.roots.iter().find(|root| {
            root.account_id == account_id
                && root.status == "active"
                && paths_match(&root.canonical_path, &validated.canonical_path)
        }) {
            return Ok(existing.to_dto());
        }
        let now = Utc::now().to_rfc3339();
        let record = WorkspaceRootRecord {
            account_id: account_id.to_owned(),
            canonical_path: validated.canonical_path.to_string_lossy().into_owned(),
            created_at: now.clone(),
            display_name: validated.display_name,
            revision: 1,
            root_ref: create_root_ref(&registry),
            status: "active".to_owned(),
            updated_at: now,
        };
        let result = record.to_dto();
        registry.roots.push(record);
        registry.revision = registry.revision.saturating_add(1);
        self.write_registry(&registry)?;
        Ok(result)
    }

    pub fn describe(
        &self,
        account_id: &str,
        root_ref: &str,
    ) -> Result<WorkspaceRootDto, WorkspaceRootError> {
        validate_account_id(account_id)?;
        let _guard = self.guard()?;
        let registry = self.load_registry()?;
        let record = find_owned_root(&registry, account_id, root_ref)?;
        if record.status != "active" {
            return Err(WorkspaceRootError::new(
                "WORKSPACE_ROOT_REVOKED",
                "工作目录授权已撤销，请重新选择目录。",
            ));
        }
        if !Path::new(&record.canonical_path).is_dir() {
            return Err(WorkspaceRootError::new(
                "WORKSPACE_ROOT_EXPIRED",
                "工作目录已失效，请重新授权。",
            ));
        }
        Ok(record.to_dto())
    }

    pub(crate) fn resolve_owned_active(
        &self,
        account_id: &str,
        root_ref: &str,
    ) -> Result<ResolvedWorkspaceRoot, WorkspaceRootError> {
        validate_account_id(account_id)?;
        let _guard = self.guard()?;
        let registry = self.load_registry()?;
        let record = find_owned_root(&registry, account_id, root_ref)?;
        if record.status != "active" {
            return Err(WorkspaceRootError::new(
                "WORKSPACE_ROOT_REVOKED",
                "工作目录授权已撤销，请重新授权。",
            ));
        }
        let canonical_path = fs::canonicalize(&record.canonical_path).map_err(|_| {
            WorkspaceRootError::new("WORKSPACE_ROOT_EXPIRED", "工作目录已失效，请重新授权。")
        })?;
        if !canonical_path.is_dir() {
            return Err(WorkspaceRootError::new(
                "WORKSPACE_ROOT_EXPIRED",
                "工作目录已失效，请重新授权。",
            ));
        }
        Ok(ResolvedWorkspaceRoot {
            canonical_path,
            revision: record.revision,
        })
    }

    pub fn reauthorize(
        &self,
        account_id: &str,
        root_ref: &str,
        selected: &Path,
    ) -> Result<WorkspaceRootDto, WorkspaceRootError> {
        validate_account_id(account_id)?;
        let _guard = self.guard()?;
        let mut registry = self.load_registry()?;
        let index = owned_root_index(&registry, account_id, root_ref)?;
        let occupied = registry
            .roots
            .iter()
            .enumerate()
            .filter(|(record_index, root)| *record_index != index && root.status == "active")
            .map(|(_, root)| PathBuf::from(&root.canonical_path))
            .collect::<Vec<_>>();
        let validated = validate_selected_root(selected, &self.restricted_roots, &occupied)?;
        let record = &mut registry.roots[index];
        record.canonical_path = validated.canonical_path.to_string_lossy().into_owned();
        record.display_name = validated.display_name;
        record.revision = record.revision.saturating_add(1);
        record.status = "active".to_owned();
        record.updated_at = Utc::now().to_rfc3339();
        let result = record.to_dto();
        registry.revision = registry.revision.saturating_add(1);
        self.write_registry(&registry)?;
        Ok(result)
    }

    pub fn revoke(
        &self,
        account_id: &str,
        root_ref: &str,
    ) -> Result<WorkspaceRootDto, WorkspaceRootError> {
        validate_account_id(account_id)?;
        let _guard = self.guard()?;
        let mut registry = self.load_registry()?;
        let index = owned_root_index(&registry, account_id, root_ref)?;
        let record = &mut registry.roots[index];
        record.revision = record.revision.saturating_add(1);
        record.status = "revoked".to_owned();
        record.updated_at = Utc::now().to_rfc3339();
        let result = record.to_dto();
        registry.revision = registry.revision.saturating_add(1);
        self.write_registry(&registry)?;
        Ok(result)
    }

    pub fn public_error(
        &self,
        operation: &str,
        error: WorkspaceRootError,
    ) -> WorkspaceRootCommandError {
        let log_id = record_failure(&self.log_path, operation, error.code);
        WorkspaceRootCommandError {
            error_code: error.code.to_owned(),
            log_id: Some(log_id),
            message: error.message.to_owned(),
        }
    }

    fn guard(&self) -> Result<MutexGuard<'_, ()>, WorkspaceRootError> {
        self.lock.lock().map_err(|_| {
            WorkspaceRootError::new(
                "WORKSPACE_ROOT_REGISTRY_LOCK_FAILED",
                "工作目录注册表状态异常，请重新启动应用。",
            )
        })
    }

    fn load_registry(&self) -> Result<WorkspaceRootRegistryFile, WorkspaceRootError> {
        read_registry(&self.path).or_else(|_| read_registry(&backup_path(&self.path)))
    }

    fn write_registry(
        &self,
        registry: &WorkspaceRootRegistryFile,
    ) -> Result<(), WorkspaceRootError> {
        let bytes = serde_json::to_vec_pretty(registry).map_err(|_| registry_write_error())?;
        if bytes.len() as u64 > MAX_REGISTRY_BYTES {
            return Err(registry_write_error());
        }
        let temporary = self.path.with_extension("json.tmp");
        let backup = backup_path(&self.path);
        let mut file = OpenOptions::new()
            .create(true)
            .truncate(true)
            .write(true)
            .open(&temporary)
            .map_err(|_| registry_write_error())?;
        file.write_all(&bytes).map_err(|_| registry_write_error())?;
        file.sync_all().map_err(|_| registry_write_error())?;
        if self.path.exists() {
            fs::copy(&self.path, &backup).map_err(|_| registry_write_error())?;
        }
        if fs::rename(&temporary, &self.path).is_err() {
            if self.path.exists() {
                fs::remove_file(&self.path).map_err(|_| registry_write_error())?;
            }
            fs::rename(&temporary, &self.path).map_err(|_| registry_write_error())?;
        }
        Ok(())
    }
}

fn read_registry(path: &Path) -> Result<WorkspaceRootRegistryFile, WorkspaceRootError> {
    let metadata = fs::metadata(path).map_err(|_| registry_read_error())?;
    if !metadata.is_file() || metadata.len() > MAX_REGISTRY_BYTES {
        return Err(registry_read_error());
    }
    let file = File::open(path).map_err(|_| registry_read_error())?;
    let registry: WorkspaceRootRegistryFile =
        serde_json::from_reader(file).map_err(|_| registry_read_error())?;
    if registry.schema_version != 1 {
        return Err(registry_read_error());
    }
    Ok(registry)
}

fn find_owned_root<'a>(
    registry: &'a WorkspaceRootRegistryFile,
    account_id: &str,
    root_ref: &str,
) -> Result<&'a WorkspaceRootRecord, WorkspaceRootError> {
    registry
        .roots
        .iter()
        .find(|root| root.root_ref == root_ref && root.account_id == account_id)
        .ok_or_else(root_not_found_error)
}

fn owned_root_index(
    registry: &WorkspaceRootRegistryFile,
    account_id: &str,
    root_ref: &str,
) -> Result<usize, WorkspaceRootError> {
    registry
        .roots
        .iter()
        .position(|root| root.root_ref == root_ref && root.account_id == account_id)
        .ok_or_else(root_not_found_error)
}

fn create_root_ref(registry: &WorkspaceRootRegistryFile) -> String {
    loop {
        let mut random = [0_u8; 16];
        if OsRng.try_fill_bytes(&mut random).is_err() {
            continue;
        }
        let candidate = format!("wr_{}", hex::encode(random));
        if registry.roots.iter().all(|root| root.root_ref != candidate) {
            return candidate;
        }
    }
}

fn paths_match(stored: &str, candidate: &Path) -> bool {
    Path::new(stored)
        .to_string_lossy()
        .eq_ignore_ascii_case(&candidate.to_string_lossy())
}

fn backup_path(path: &Path) -> PathBuf {
    path.with_extension("json.bak")
}

fn registry_read_error() -> WorkspaceRootError {
    WorkspaceRootError::new(
        "WORKSPACE_ROOT_REGISTRY_INVALID",
        "工作目录注册表损坏，请重新启动应用或恢复授权。",
    )
}

fn registry_write_error() -> WorkspaceRootError {
    WorkspaceRootError::new(
        "WORKSPACE_ROOT_REGISTRY_WRITE_FAILED",
        "无法保存工作目录授权，请检查系统权限。",
    )
}

fn root_not_found_error() -> WorkspaceRootError {
    WorkspaceRootError::new(
        "WORKSPACE_ROOT_NOT_FOUND",
        "工作目录授权不存在或不属于当前账号。",
    )
}

fn command_error(code: &str, message: &str) -> WorkspaceRootCommandError {
    WorkspaceRootCommandError {
        error_code: code.to_owned(),
        log_id: None,
        message: message.to_owned(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn 注册表按账号隔离并支持撤销与重新授权() {
        let sandbox = test_directory();
        let app_data = sandbox.join("app-data");
        let first_root = sandbox.join("account-a");
        let second_root = sandbox.join("account-a-new");
        fs::create_dir_all(&app_data).expect("应创建测试应用目录");
        fs::create_dir_all(&first_root).expect("应创建首个测试目录");
        fs::create_dir_all(&second_root).expect("应创建第二个测试目录");
        let registry = WorkspaceRootRegistry {
            lock: Mutex::new(()),
            log_path: app_data.join("workspace-roots.jsonl"),
            path: app_data.join("workspace-roots.v1.json"),
            restricted_roots: vec![app_data.clone()],
        };
        registry
            .write_registry(&WorkspaceRootRegistryFile::default())
            .expect("应初始化注册表");

        let created = registry
            .register("account-a", &first_root)
            .expect("应注册账号目录");
        let duplicate = registry
            .register("account-a", &first_root)
            .expect("同账号重复选择应幂等");
        assert_eq!(created.root_ref, duplicate.root_ref);

        let cross_account = registry
            .register("account-b", &first_root)
            .expect_err("其他账号不得复用目录");
        assert_eq!(cross_account.code, "WORKSPACE_ROOT_ALREADY_ASSIGNED");

        let wrong_owner = registry
            .describe("account-b", &created.root_ref)
            .expect_err("引用必须与账号共同校验");
        assert_eq!(wrong_owner.code, "WORKSPACE_ROOT_NOT_FOUND");

        registry
            .revoke("account-a", &created.root_ref)
            .expect("应撤销授权");
        let revoked = registry
            .describe("account-a", &created.root_ref)
            .expect_err("撤销后不可解析");
        assert_eq!(revoked.code, "WORKSPACE_ROOT_REVOKED");

        let restored = registry
            .reauthorize("account-a", &created.root_ref, &second_root)
            .expect("应重新授权");
        assert_eq!(restored.root_ref, created.root_ref);
        assert_eq!(restored.revision, 3);
        assert!(restored.display_path.ends_with("account-a-new"));

        fs::remove_dir_all(sandbox).expect("应清理测试目录");
    }

    #[test]
    fn 损坏主注册表时读取最后备份快照() {
        let sandbox = test_directory();
        fs::create_dir_all(&sandbox).expect("应创建测试目录");
        let registry = WorkspaceRootRegistry {
            lock: Mutex::new(()),
            log_path: sandbox.join("workspace-roots.jsonl"),
            path: sandbox.join("workspace-roots.v1.json"),
            restricted_roots: Vec::new(),
        };
        registry
            .write_registry(&WorkspaceRootRegistryFile::default())
            .expect("应写入初始注册表");
        registry
            .write_registry(&WorkspaceRootRegistryFile::default())
            .expect("应产生备份");
        fs::write(&registry.path, b"invalid-json").expect("应写入损坏内容");

        let recovered = registry.load_registry().expect("应回退备份");
        assert_eq!(recovered.schema_version, 1);
        fs::remove_dir_all(sandbox).expect("应清理测试目录");
    }

    fn test_directory() -> PathBuf {
        let mut random = [0_u8; 8];
        OsRng
            .try_fill_bytes(&mut random)
            .expect("应创建测试随机标识");
        std::env::temp_dir().join(format!(
            "tk-ops-workspace-root-test-{}",
            hex::encode(random)
        ))
    }
}
