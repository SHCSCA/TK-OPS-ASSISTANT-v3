use std::{
    env, fs,
    path::{Path, PathBuf},
};

use rand::{rngs::OsRng, RngCore};

use super::types::{ValidatedWorkspaceRoot, WorkspaceRootError};

pub(super) fn validate_account_id(account_id: &str) -> Result<(), WorkspaceRootError> {
    let valid = !account_id.trim().is_empty()
        && account_id.len() <= 128
        && account_id
            .chars()
            .all(|value| value.is_ascii_alphanumeric() || matches!(value, '-' | '_'));
    if valid {
        Ok(())
    } else {
        Err(WorkspaceRootError::new(
            "WORKSPACE_ROOT_ACCOUNT_INVALID",
            "账号标识无效，请刷新账号后重试。",
        ))
    }
}

pub(super) fn validate_selected_root(
    selected: &Path,
    restricted_roots: &[PathBuf],
    occupied_roots: &[PathBuf],
) -> Result<ValidatedWorkspaceRoot, WorkspaceRootError> {
    if !selected.is_absolute() || !selected.is_dir() {
        return Err(WorkspaceRootError::new(
            "WORKSPACE_ROOT_NOT_DIRECTORY",
            "请选择真实存在的本地文件夹。",
        ));
    }
    let canonical = fs::canonicalize(selected).map_err(|_| {
        WorkspaceRootError::new(
            "WORKSPACE_ROOT_RESOLVE_FAILED",
            "无法解析所选目录，请检查权限或重新选择。",
        )
    })?;
    if canonical.parent().is_none() || is_restricted(&canonical, restricted_roots) {
        return Err(WorkspaceRootError::new(
            "WORKSPACE_ROOT_DANGEROUS",
            "不能把磁盘根目录或系统关键目录作为账号工作目录。",
        ));
    }
    if occupied_roots
        .iter()
        .any(|root| same_path(root, &canonical))
    {
        return Err(WorkspaceRootError::new(
            "WORKSPACE_ROOT_ALREADY_ASSIGNED",
            "该目录已分配给其他账号，请选择独立目录。",
        ));
    }
    verify_writable(&canonical)?;
    let display_name = canonical
        .file_name()
        .and_then(|value| value.to_str())
        .filter(|value| !value.trim().is_empty())
        .unwrap_or("账号工作目录")
        .to_owned();
    Ok(ValidatedWorkspaceRoot {
        canonical_path: canonical,
        display_name,
    })
}

pub(super) fn system_restricted_roots(
    app_data_root: &Path,
    runtime_data_root: &Path,
) -> Vec<PathBuf> {
    let mut roots = vec![app_data_root.to_path_buf(), runtime_data_root.to_path_buf()];
    for variable in [
        "USERPROFILE",
        "WINDIR",
        "ProgramFiles",
        "ProgramFiles(x86)",
        "APPDATA",
        "LOCALAPPDATA",
    ] {
        if let Some(path) = env::var_os(variable).map(PathBuf::from) {
            roots.push(path);
        }
    }
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    if let Some(repository_root) = manifest_dir.ancestors().nth(3) {
        roots.push(repository_root.to_path_buf());
    }
    roots
}

fn is_restricted(candidate: &Path, roots: &[PathBuf]) -> bool {
    roots.iter().any(|root| {
        fs::canonicalize(root)
            .map(|canonical| same_path(&canonical, candidate))
            .unwrap_or_else(|_| same_path(root, candidate))
    })
}

fn same_path(left: &Path, right: &Path) -> bool {
    left.to_string_lossy()
        .eq_ignore_ascii_case(&right.to_string_lossy())
}

fn verify_writable(path: &Path) -> Result<(), WorkspaceRootError> {
    let mut random = [0_u8; 8];
    OsRng.try_fill_bytes(&mut random).map_err(|_| {
        WorkspaceRootError::new(
            "WORKSPACE_ROOT_PROBE_FAILED",
            "无法验证目录写入权限，请重新选择。",
        )
    })?;
    let probe = path.join(format!(".tk-ops-write-probe-{}", hex::encode(random)));
    fs::write(&probe, b"tk-ops").map_err(|_| {
        WorkspaceRootError::new(
            "WORKSPACE_ROOT_NOT_WRITABLE",
            "所选目录不可写，请检查权限或重新选择。",
        )
    })?;
    fs::remove_file(&probe).map_err(|_| {
        WorkspaceRootError::new(
            "WORKSPACE_ROOT_PROBE_CLEANUP_FAILED",
            "目录权限验证文件无法清理，请更换目录。",
        )
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn 拒绝系统受控目录并接受普通可写目录() {
        let sandbox = test_directory();
        let restricted = sandbox.join("app-data");
        let selected = sandbox.join("account-root");
        fs::create_dir_all(&restricted).expect("应创建受控目录");
        fs::create_dir_all(&selected).expect("应创建普通目录");

        let blocked = validate_selected_root(&restricted, &[restricted.clone()], &[])
            .expect_err("应拒绝受控根目录");
        assert_eq!(blocked.code, "WORKSPACE_ROOT_DANGEROUS");

        let accepted =
            validate_selected_root(&selected, &[restricted], &[]).expect("应接受普通可写目录");
        assert_eq!(
            accepted.canonical_path,
            fs::canonicalize(&selected).unwrap()
        );
        fs::remove_dir_all(sandbox).expect("应清理测试目录");
    }

    fn test_directory() -> PathBuf {
        let mut random = [0_u8; 8];
        OsRng
            .try_fill_bytes(&mut random)
            .expect("应创建测试随机标识");
        std::env::temp_dir().join(format!(
            "tk-ops-workspace-validation-test-{}",
            hex::encode(random)
        ))
    }
}
