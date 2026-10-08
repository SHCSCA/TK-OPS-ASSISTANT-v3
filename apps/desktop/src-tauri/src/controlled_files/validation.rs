use std::{collections::HashSet, fs, path::Path, time::UNIX_EPOCH};

use sha2::{Digest, Sha256};

use super::types::ControlledFileRegistryFile;
use super::types::{ControlledFileError, ControlledFileFilters, ValidatedControlledFile};

pub(super) const MAX_CONTROLLED_FILE_BYTES: u64 = 20 * 1024 * 1024;
pub(super) const DEFAULT_EXTENSIONS: &[&str] = &[
    "txt", "md", "markdown", "json", "pdf", "png", "jpg", "jpeg", "webp", "mp4", "mov", "webm",
    "mp3", "wav", "m4a",
];

pub(super) fn validate_controlled_file(
    selected: &Path,
    root: &Path,
    root_ref: &str,
    filters: Option<&ControlledFileFilters>,
) -> Result<ValidatedControlledFile, ControlledFileError> {
    if !selected.is_absolute() {
        return Err(file_error(
            "CONTROLLED_FILE_PATH_INVALID",
            "请选择真实存在的本地文件。",
        ));
    }
    let selected_metadata = fs::symlink_metadata(selected).map_err(|_| {
        file_error(
            "CONTROLLED_FILE_UNAVAILABLE",
            "所选文件不可用，请检查文件是否仍存在。",
        )
    })?;
    if selected_metadata.file_type().is_symlink() || !selected_metadata.is_file() {
        return Err(file_error(
            "CONTROLLED_FILE_TYPE_INVALID",
            "只能选择工作目录内的普通文件。",
        ));
    }
    let canonical_root = fs::canonicalize(root)
        .map_err(|_| file_error("WORKSPACE_ROOT_EXPIRED", "工作目录已失效，请重新授权。"))?;
    let canonical_path = fs::canonicalize(selected).map_err(|_| {
        file_error(
            "CONTROLLED_FILE_UNAVAILABLE",
            "无法解析所选文件，请检查权限后重试。",
        )
    })?;
    if canonical_path == canonical_root || !canonical_path.starts_with(&canonical_root) {
        return Err(file_error(
            "CONTROLLED_FILE_OUTSIDE_ROOT",
            "文件不在当前账号工作目录内，请先授权其所在目录。",
        ));
    }
    let relative = canonical_path.strip_prefix(&canonical_root).map_err(|_| {
        file_error(
            "CONTROLLED_FILE_OUTSIDE_ROOT",
            "文件不在当前账号工作目录内，请先授权其所在目录。",
        )
    })?;
    let relative_path = normalized_relative_path(relative)?;
    let metadata = fs::metadata(&canonical_path).map_err(|_| {
        file_error(
            "CONTROLLED_FILE_UNAVAILABLE",
            "所选文件不可读，请检查权限后重试。",
        )
    })?;
    let max_bytes = filters
        .and_then(|value| value.max_bytes)
        .unwrap_or(MAX_CONTROLLED_FILE_BYTES)
        .min(MAX_CONTROLLED_FILE_BYTES);
    if metadata.len() == 0 || metadata.len() > max_bytes {
        return Err(file_error(
            "CONTROLLED_FILE_SIZE_INVALID",
            "文件为空或超过允许大小，请选择较小文件。",
        ));
    }
    let extension = normalized_extension(&canonical_path)?;
    let allowed = allowed_extensions(filters)?;
    if !allowed.contains(&extension) {
        return Err(file_error(
            "CONTROLLED_FILE_EXTENSION_UNSUPPORTED",
            "当前文件类型不受支持，请选择允许的知识文件。",
        ));
    }
    let (kind, media_type) = classify_extension(&extension);
    let mtime = metadata
        .modified()
        .ok()
        .and_then(|value| value.duration_since(UNIX_EPOCH).ok())
        .map(|value| value.as_millis() as u64)
        .ok_or_else(|| {
            file_error(
                "CONTROLLED_FILE_IDENTITY_UNAVAILABLE",
                "无法读取文件身份，请重新选择文件。",
            )
        })?;
    Ok(ValidatedControlledFile {
        canonical_path,
        file_identity: file_identity(root_ref, &relative_path),
        kind: kind.to_owned(),
        media_type: media_type.to_owned(),
        mtime,
        relative_path,
        size: metadata.len(),
    })
}

pub(super) fn validate_registry_file(
    registry: &ControlledFileRegistryFile,
) -> Result<(), ControlledFileError> {
    let mut file_refs = HashSet::new();
    for record in &registry.files {
        let canonical = Path::new(&record.canonical_path);
        let relative = Path::new(&record.relative_path);
        if record.revision < 1
            || record.root_revision < 1
            || record.size < 1
            || record.status != "active" && record.status != "revoked"
            || !canonical.is_absolute()
            || relative.is_absolute()
            || relative
                .components()
                .any(|value| matches!(value, std::path::Component::ParentDir))
            || !valid_hex_reference(&record.file_ref, "file_ref_", 41)
            || !valid_hex_reference(&record.root_ref, "wr_", 35)
            || record.file_identity.len() != 64
            || !record
                .file_identity
                .chars()
                .all(|value| value.is_ascii_hexdigit())
            || !file_refs.insert(record.file_ref.clone())
        {
            return Err(file_error(
                "CONTROLLED_FILE_REGISTRY_INVALID",
                "受控文件注册表损坏，请重新启动应用。",
            ));
        }
    }
    Ok(())
}

fn allowed_extensions(
    filters: Option<&ControlledFileFilters>,
) -> Result<HashSet<String>, ControlledFileError> {
    let requested = filters
        .and_then(|value| value.extensions.as_ref())
        .filter(|value| !value.is_empty());
    let defaults = DEFAULT_EXTENSIONS
        .iter()
        .map(|value| (*value).to_owned())
        .collect::<HashSet<_>>();
    let Some(requested) = requested else {
        return Ok(defaults);
    };
    let normalized = requested
        .iter()
        .map(|value| value.trim().trim_start_matches('.').to_ascii_lowercase())
        .collect::<HashSet<_>>();
    if normalized.is_empty() || normalized.iter().any(|value| !defaults.contains(value)) {
        return Err(file_error(
            "CONTROLLED_FILE_FILTER_INVALID",
            "文件选择范围无效，请刷新页面后重试。",
        ));
    }
    Ok(normalized)
}

fn normalized_relative_path(path: &Path) -> Result<String, ControlledFileError> {
    let value = path.to_string_lossy().replace('\\', "/");
    if value.is_empty() || value.starts_with('/') || value.contains("../") {
        return Err(file_error(
            "CONTROLLED_FILE_RELATIVE_PATH_INVALID",
            "文件相对路径无效，请重新选择。",
        ));
    }
    Ok(value)
}

fn normalized_extension(path: &Path) -> Result<String, ControlledFileError> {
    path.extension()
        .and_then(|value| value.to_str())
        .map(str::to_ascii_lowercase)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| {
            file_error(
                "CONTROLLED_FILE_EXTENSION_UNSUPPORTED",
                "文件缺少受支持的扩展名。",
            )
        })
}

fn classify_extension(extension: &str) -> (&'static str, &'static str) {
    match extension {
        "txt" => ("text", "text/plain; charset=utf-8"),
        "md" | "markdown" => ("document", "text/markdown; charset=utf-8"),
        "json" => ("document", "application/json"),
        "pdf" => ("document", "application/pdf"),
        "png" => ("image", "image/png"),
        "jpg" | "jpeg" => ("image", "image/jpeg"),
        "webp" => ("image", "image/webp"),
        "mp4" => ("video", "video/mp4"),
        "mov" => ("video", "video/quicktime"),
        "webm" => ("video", "video/webm"),
        "mp3" => ("audio", "audio/mpeg"),
        "wav" => ("audio", "audio/wav"),
        "m4a" => ("audio", "audio/mp4"),
        _ => ("document", "application/octet-stream"),
    }
}

fn file_identity(root_ref: &str, relative_path: &str) -> String {
    let mut digest = Sha256::new();
    digest.update(root_ref.as_bytes());
    digest.update(b"\0");
    digest.update(relative_path.as_bytes());
    hex::encode(digest.finalize())
}

fn valid_hex_reference(value: &str, prefix: &str, length: usize) -> bool {
    value.len() == length
        && value.starts_with(prefix)
        && value[prefix.len()..]
            .chars()
            .all(|character| character.is_ascii_hexdigit())
}

fn file_error(code: &'static str, message: &'static str) -> ControlledFileError {
    ControlledFileError::new(code, message)
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::{rngs::OsRng, RngCore};
    use std::path::PathBuf;

    #[test]
    fn controlled_files_只接受工作目录内受支持的普通文件() {
        let sandbox = test_directory();
        let root = sandbox.join("account-root");
        let outside = sandbox.join("outside.txt");
        fs::create_dir_all(&root).expect("应创建账号目录");
        fs::write(root.join("knowledge.md"), "真实知识").expect("应写入知识文件");
        fs::write(&outside, "越界内容").expect("应写入越界文件");

        let accepted = validate_controlled_file(
            &root.join("knowledge.md"),
            &root,
            "wr_0123456789abcdef0123456789abcdef",
            None,
        )
        .expect("应接受目录内文件");
        assert_eq!(accepted.relative_path, "knowledge.md");
        assert_eq!(accepted.media_type, "text/markdown; charset=utf-8");
        assert_eq!(accepted.file_identity.len(), 64);

        let escaped =
            validate_controlled_file(&outside, &root, "wr_0123456789abcdef0123456789abcdef", None)
                .expect_err("应拒绝目录外文件");
        assert_eq!(escaped.code, "CONTROLLED_FILE_OUTSIDE_ROOT");
        fs::remove_dir_all(sandbox).expect("应清理测试目录");
    }

    #[test]
    fn controlled_files_拒绝超限和未授权扩展名() {
        let sandbox = test_directory();
        fs::create_dir_all(&sandbox).expect("应创建测试目录");
        let file = sandbox.join("knowledge.txt");
        fs::write(&file, "12345").expect("应写入测试文件");
        let filters = ControlledFileFilters {
            extensions: Some(vec!["md".to_owned()]),
            max_bytes: Some(4),
        };
        let error = validate_controlled_file(
            &file,
            &sandbox,
            "wr_0123456789abcdef0123456789abcdef",
            Some(&filters),
        )
        .expect_err("应先拒绝大小越界");
        assert_eq!(error.code, "CONTROLLED_FILE_SIZE_INVALID");
        fs::remove_dir_all(sandbox).expect("应清理测试目录");
    }

    fn test_directory() -> PathBuf {
        let mut random = [0_u8; 8];
        OsRng.try_fill_bytes(&mut random).expect("应创建随机标识");
        std::env::temp_dir().join(format!(
            "tk-ops-controlled-file-test-{}",
            hex::encode(random)
        ))
    }
}
