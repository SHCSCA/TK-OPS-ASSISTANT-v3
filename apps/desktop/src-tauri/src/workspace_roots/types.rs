use std::{fmt, path::PathBuf};

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkspaceRootDto {
    pub display_name: String,
    pub display_path: String,
    pub revision: u64,
    pub root_ref: String,
    pub status: String,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub(super) struct WorkspaceRootRecord {
    pub account_id: String,
    pub canonical_path: String,
    pub created_at: String,
    pub display_name: String,
    pub revision: u64,
    pub root_ref: String,
    pub status: String,
    pub updated_at: String,
}

impl WorkspaceRootRecord {
    pub fn to_dto(&self) -> WorkspaceRootDto {
        WorkspaceRootDto {
            display_name: self.display_name.clone(),
            display_path: self.canonical_path.clone(),
            revision: self.revision,
            root_ref: self.root_ref.clone(),
            status: self.status.clone(),
        }
    }
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub(super) struct WorkspaceRootRegistryFile {
    pub revision: u64,
    pub roots: Vec<WorkspaceRootRecord>,
    pub schema_version: u32,
}

impl Default for WorkspaceRootRegistryFile {
    fn default() -> Self {
        Self {
            revision: 0,
            roots: Vec::new(),
            schema_version: 1,
        }
    }
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkspaceRootCommandError {
    pub error_code: String,
    pub log_id: Option<String>,
    pub message: String,
}

impl fmt::Display for WorkspaceRootCommandError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl fmt::Debug for WorkspaceRootCommandError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("WorkspaceRootCommandError")
            .field("error_code", &self.error_code)
            .field("log_id", &self.log_id)
            .finish()
    }
}

impl std::error::Error for WorkspaceRootCommandError {}

#[derive(Debug)]
pub(crate) struct WorkspaceRootError {
    pub code: &'static str,
    pub message: &'static str,
}

impl WorkspaceRootError {
    pub fn new(code: &'static str, message: &'static str) -> Self {
        Self { code, message }
    }
}

#[derive(Debug)]
pub(super) struct ValidatedWorkspaceRoot {
    pub canonical_path: PathBuf,
    pub display_name: String,
}

#[derive(Debug)]
pub(crate) struct ResolvedWorkspaceRoot {
    pub canonical_path: PathBuf,
    pub revision: u64,
}
