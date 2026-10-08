use std::{
    fs::{self, File, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
    sync::{Mutex, MutexGuard},
};

use rand::{rngs::OsRng, RngCore};
use tauri::AppHandle;

use super::{
    logging::record_failure,
    types::{
        ControlledFileCommandError, ControlledFileDto, ControlledFileError, ControlledFileFilters,
        ControlledFileOwnership, ControlledFileRecord, ControlledFileRegistryFile,
    },
    validation::{validate_controlled_file, validate_registry_file},
};
use crate::{app_paths::resolve_app_data_dir, workspace_roots::ResolvedWorkspaceRoot};

const MAX_REGISTRY_BYTES: u64 = 2 * 1024 * 1024;

pub struct ControlledFileRegistry {
    lock: Mutex<()>,
    log_path: PathBuf,
    path: PathBuf,
}

impl ControlledFileRegistry {
    pub fn initialize(app: &AppHandle) -> Result<Self, ControlledFileCommandError> {
        let app_data_root = resolve_app_data_dir(app).map_err(|_| {
            command_error(
                "CONTROLLED_FILE_REGISTRY_PATH_UNAVAILABLE",
                "无法解析受控文件注册表，请重新启动应用。",
            )
        })?;
        let log_root = app_data_root.join("logs");
        fs::create_dir_all(&app_data_root).map_err(|_| {
            command_error(
                "CONTROLLED_FILE_REGISTRY_DIRECTORY_FAILED",
                "无法创建受控文件注册表，请检查系统权限。",
            )
        })?;
        fs::create_dir_all(&log_root).map_err(|_| {
            command_error(
                "CONTROLLED_FILE_LOG_DIRECTORY_FAILED",
                "无法创建受控文件日志，请检查系统权限。",
            )
        })?;
        let registry = Self {
            lock: Mutex::new(()),
            log_path: log_root.join("controlled-files.jsonl"),
            path: app_data_root.join("controlled-files.v1.json"),
        };
        if registry.path.exists() {
            registry
                .load_registry()
                .map_err(|error| registry.public_error("initialize", error))?;
        } else {
            registry
                .write_registry(&ControlledFileRegistryFile::default())
                .map_err(|error| registry.public_error("initialize", error))?;
        }
        Ok(registry)
    }

    pub(super) fn register(
        &self,
        account_id: &str,
        root_ref: &str,
        root: &ResolvedWorkspaceRoot,
        selected: &Path,
        filters: Option<&ControlledFileFilters>,
    ) -> Result<ControlledFileDto, ControlledFileError> {
        validate_account_id(account_id)?;
        validate_root_ref(root_ref)?;
        let validated =
            validate_controlled_file(selected, &root.canonical_path, root_ref, filters)?;
        let _guard = self.guard()?;
        let mut registry = self.load_registry()?;
        let record = ControlledFileRecord {
            account_id: account_id.to_owned(),
            canonical_path: validated.canonical_path.to_string_lossy().into_owned(),
            file_identity: validated.file_identity,
            file_ref: create_file_ref(&registry),
            kind: validated.kind,
            media_type: validated.media_type,
            mtime: validated.mtime,
            relative_path: validated.relative_path,
            revision: 1,
            root_ref: root_ref.to_owned(),
            root_revision: root.revision,
            size: validated.size,
            status: "active".to_owned(),
        };
        let result = record.to_dto();
        registry.files.push(record);
        registry.revision = registry.revision.saturating_add(1);
        self.write_registry(&registry)?;
        Ok(result)
    }

    pub(super) fn describe_owned(
        &self,
        account_id: &str,
        file_ref: &str,
    ) -> Result<ControlledFileOwnership, ControlledFileError> {
        validate_account_id(account_id)?;
        validate_file_ref(file_ref)?;
        let _guard = self.guard()?;
        let registry = self.load_registry()?;
        let record = find_owned_file(&registry, account_id, file_ref)?;
        if record.status != "active" {
            return Err(ControlledFileError::new(
                "CONTROLLED_FILE_REVOKED",
                "文件授权已撤销，请重新选择文件。",
            ));
        }
        Ok(ControlledFileOwnership {
            dto: record.to_dto(),
            root_revision: record.root_revision,
        })
    }

    pub(super) fn revoke(
        &self,
        account_id: &str,
        file_ref: &str,
    ) -> Result<ControlledFileDto, ControlledFileError> {
        validate_account_id(account_id)?;
        validate_file_ref(file_ref)?;
        let _guard = self.guard()?;
        let mut registry = self.load_registry()?;
        let index = owned_file_index(&registry, account_id, file_ref)?;
        let record = &mut registry.files[index];
        if record.status != "revoked" {
            record.status = "revoked".to_owned();
            record.revision = record.revision.saturating_add(1);
            registry.revision = registry.revision.saturating_add(1);
            self.write_registry(&registry)?;
        }
        Ok(registry.files[index].to_dto())
    }

    pub(super) fn public_error(
        &self,
        operation: &str,
        error: ControlledFileError,
    ) -> ControlledFileCommandError {
        ControlledFileCommandError {
            error_code: error.code.to_owned(),
            log_id: Some(record_failure(&self.log_path, operation, error.code)),
            message: error.message.to_owned(),
        }
    }

    fn guard(&self) -> Result<MutexGuard<'_, ()>, ControlledFileError> {
        self.lock.lock().map_err(|_| {
            ControlledFileError::new(
                "CONTROLLED_FILE_REGISTRY_LOCK_FAILED",
                "受控文件注册表状态异常，请重新启动应用。",
            )
        })
    }

    fn load_registry(&self) -> Result<ControlledFileRegistryFile, ControlledFileError> {
        read_registry(&self.path).or_else(|_| read_registry(&backup_path(&self.path)))
    }

    fn write_registry(
        &self,
        registry: &ControlledFileRegistryFile,
    ) -> Result<(), ControlledFileError> {
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

fn read_registry(path: &Path) -> Result<ControlledFileRegistryFile, ControlledFileError> {
    let metadata = fs::metadata(path).map_err(|_| registry_read_error())?;
    if !metadata.is_file() || metadata.len() > MAX_REGISTRY_BYTES {
        return Err(registry_read_error());
    }
    let registry: ControlledFileRegistryFile =
        serde_json::from_reader(File::open(path).map_err(|_| registry_read_error())?)
            .map_err(|_| registry_read_error())?;
    if registry.schema_version != 1 {
        return Err(registry_read_error());
    }
    validate_registry_file(&registry)?;
    Ok(registry)
}

fn find_owned_file<'a>(
    registry: &'a ControlledFileRegistryFile,
    account_id: &str,
    file_ref: &str,
) -> Result<&'a ControlledFileRecord, ControlledFileError> {
    registry
        .files
        .iter()
        .find(|record| record.account_id == account_id && record.file_ref == file_ref)
        .ok_or_else(file_not_found_error)
}

fn owned_file_index(
    registry: &ControlledFileRegistryFile,
    account_id: &str,
    file_ref: &str,
) -> Result<usize, ControlledFileError> {
    registry
        .files
        .iter()
        .position(|record| record.account_id == account_id && record.file_ref == file_ref)
        .ok_or_else(file_not_found_error)
}

fn create_file_ref(registry: &ControlledFileRegistryFile) -> String {
    loop {
        let mut random = [0_u8; 16];
        if OsRng.try_fill_bytes(&mut random).is_err() {
            continue;
        }
        let candidate = format!("file_ref_{}", hex::encode(random));
        if registry
            .files
            .iter()
            .all(|record| record.file_ref != candidate)
        {
            return candidate;
        }
    }
}

fn validate_account_id(account_id: &str) -> Result<(), ControlledFileError> {
    let valid = !account_id.trim().is_empty()
        && account_id.len() <= 128
        && account_id
            .chars()
            .all(|value| value.is_ascii_alphanumeric() || matches!(value, '-' | '_'));
    if valid {
        Ok(())
    } else {
        Err(ControlledFileError::new(
            "CONTROLLED_FILE_ACCOUNT_INVALID",
            "账号标识无效，请刷新账号后重试。",
        ))
    }
}

fn validate_root_ref(root_ref: &str) -> Result<(), ControlledFileError> {
    validate_reference(root_ref, "wr_", 35, "CONTROLLED_FILE_ROOT_REF_INVALID")
}

fn validate_file_ref(file_ref: &str) -> Result<(), ControlledFileError> {
    validate_reference(file_ref, "file_ref_", 41, "CONTROLLED_FILE_REF_INVALID")
}

fn validate_reference(
    value: &str,
    prefix: &str,
    length: usize,
    code: &'static str,
) -> Result<(), ControlledFileError> {
    if value.len() == length
        && value.starts_with(prefix)
        && value[prefix.len()..]
            .chars()
            .all(|character| character.is_ascii_hexdigit())
    {
        Ok(())
    } else {
        Err(ControlledFileError::new(
            code,
            "受控文件引用无效，请重新选择文件。",
        ))
    }
}

fn backup_path(path: &Path) -> PathBuf {
    path.with_extension("json.bak")
}

fn registry_read_error() -> ControlledFileError {
    ControlledFileError::new(
        "CONTROLLED_FILE_REGISTRY_INVALID",
        "受控文件注册表损坏，请重新启动应用。",
    )
}

fn registry_write_error() -> ControlledFileError {
    ControlledFileError::new(
        "CONTROLLED_FILE_REGISTRY_WRITE_FAILED",
        "无法保存文件授权，请检查系统权限。",
    )
}

fn file_not_found_error() -> ControlledFileError {
    ControlledFileError::new(
        "CONTROLLED_FILE_NOT_FOUND",
        "文件授权不存在或不属于当前账号。",
    )
}

fn command_error(code: &str, message: &str) -> ControlledFileCommandError {
    ControlledFileCommandError {
        error_code: code.to_owned(),
        log_id: None,
        message: message.to_owned(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn controlled_files_注册表按账号隔离并支持撤销() {
        let sandbox = std::env::temp_dir().join(format!(
            "tk-ops-controlled-registry-{}",
            hex::encode(rand::random::<[u8; 8]>())
        ));
        let root_path = sandbox.join("account-root");
        fs::create_dir_all(&root_path).expect("应创建账号目录");
        let file = root_path.join("knowledge.txt");
        fs::write(&file, "知识内容").expect("应写入知识文件");
        let registry = ControlledFileRegistry {
            lock: Mutex::new(()),
            log_path: sandbox.join("controlled-files.jsonl"),
            path: sandbox.join("controlled-files.v1.json"),
        };
        registry
            .write_registry(&ControlledFileRegistryFile::default())
            .expect("应初始化注册表");
        let root = ResolvedWorkspaceRoot {
            canonical_path: root_path,
            revision: 2,
        };
        let created = registry
            .register(
                "acc_a",
                "wr_0123456789abcdef0123456789abcdef",
                &root,
                &file,
                None,
            )
            .expect("应创建授权");
        assert_eq!(created.status, "active");
        assert!(registry.describe_owned("acc_a", &created.file_ref).is_ok());
        assert!(registry.describe_owned("acc_b", &created.file_ref).is_err());
        let revoked = registry
            .revoke("acc_a", &created.file_ref)
            .expect("应撤销授权");
        assert_eq!(revoked.status, "revoked");
        fs::remove_dir_all(sandbox).expect("应清理测试目录");
    }
}
