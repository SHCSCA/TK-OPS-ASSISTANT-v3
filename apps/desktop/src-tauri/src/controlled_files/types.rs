use std::{fmt, path::PathBuf};

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct ControlledFileFilters {
    pub extensions: Option<Vec<String>>,
    pub max_bytes: Option<u64>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ControlledFileDto {
    pub display_name: String,
    pub file_ref: String,
    pub kind: String,
    pub revision: u64,
    pub root_ref: String,
    pub size: u64,
    pub status: String,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub(super) struct ControlledFileRecord {
    pub account_id: String,
    pub canonical_path: String,
    pub file_identity: String,
    pub file_ref: String,
    pub kind: String,
    pub media_type: String,
    pub mtime: u64,
    pub relative_path: String,
    pub revision: u64,
    pub root_ref: String,
    pub root_revision: u64,
    pub size: u64,
    pub status: String,
}

impl ControlledFileRecord {
    pub fn to_dto(&self) -> ControlledFileDto {
        let display_name = PathBuf::from(&self.relative_path)
            .file_name()
            .and_then(|value| value.to_str())
            .unwrap_or("受控文件")
            .to_owned();
        ControlledFileDto {
            display_name,
            file_ref: self.file_ref.clone(),
            kind: self.kind.clone(),
            revision: self.revision,
            root_ref: self.root_ref.clone(),
            size: self.size,
            status: self.status.clone(),
        }
    }
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub(super) struct ControlledFileRegistryFile {
    pub files: Vec<ControlledFileRecord>,
    pub revision: u64,
    pub schema_version: u32,
}

impl Default for ControlledFileRegistryFile {
    fn default() -> Self {
        Self {
            files: Vec::new(),
            revision: 0,
            schema_version: 1,
        }
    }
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ControlledFileCommandError {
    pub error_code: String,
    pub log_id: Option<String>,
    pub message: String,
}

impl fmt::Display for ControlledFileCommandError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl fmt::Debug for ControlledFileCommandError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("ControlledFileCommandError")
            .field("error_code", &self.error_code)
            .field("log_id", &self.log_id)
            .finish()
    }
}

impl std::error::Error for ControlledFileCommandError {}

#[derive(Debug)]
pub(super) struct ControlledFileError {
    pub code: &'static str,
    pub message: &'static str,
}

impl ControlledFileError {
    pub fn new(code: &'static str, message: &'static str) -> Self {
        Self { code, message }
    }
}

#[derive(Debug)]
pub(super) struct ValidatedControlledFile {
    pub canonical_path: PathBuf,
    pub file_identity: String,
    pub kind: String,
    pub media_type: String,
    pub mtime: u64,
    pub relative_path: String,
    pub size: u64,
}

pub(super) struct ControlledFileOwnership {
    pub dto: ControlledFileDto,
    pub root_revision: u64,
}
