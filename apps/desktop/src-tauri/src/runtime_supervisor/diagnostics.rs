use std::{fs, io::Write};

use serde::Serialize;
use serde_json::Value;

use super::{
    config::{hash_file, SupervisorConfig},
    logging::{epoch_millis, SupervisorLogger},
    state::SupervisorInner,
    SupervisorError,
};
use crate::app_paths::AppPaths;

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SupervisorLogEntryDto {
    pub error_code: Option<String>,
    pub level: String,
    pub log_id: String,
    pub operation: String,
    pub timestamp_epoch_ms: u64,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SupervisorDiagnosticsDto {
    pub artifact_build_id: Option<String>,
    pub artifact_sha256: Option<String>,
    pub desktop_version: String,
    pub generated_at_epoch_ms: u64,
    pub generation: u64,
    pub last_exit_code: Option<i32>,
    pub max_restart_attempts: u32,
    pub phase: String,
    pub recent_logs: Vec<SupervisorLogEntryDto>,
    pub restart_attempt: u32,
    pub status: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SupervisorDiagnosticExportDto {
    pub file_name: String,
    pub path: String,
}

impl SupervisorLogEntryDto {
    pub fn from_redacted_value(value: &Value) -> Option<Self> {
        Some(Self {
            error_code: value
                .get("errorCode")
                .and_then(Value::as_str)
                .map(str::to_owned),
            level: controlled_text(value.get("level")?.as_str()?, 16)?,
            log_id: controlled_text(value.get("logId")?.as_str()?, 96)?,
            operation: controlled_text(value.get("operation")?.as_str()?, 96)?,
            timestamp_epoch_ms: value.get("timestampEpochMs")?.as_u64()?,
        })
    }
}

pub(super) fn build_diagnostics(
    inner: &SupervisorInner,
    paths: Option<&AppPaths>,
    logger: &SupervisorLogger,
    config: &SupervisorConfig,
) -> SupervisorDiagnosticsDto {
    let (artifact_build_id, artifact_sha256) = paths
        .and_then(read_artifact_evidence)
        .unwrap_or((None, None));
    SupervisorDiagnosticsDto {
        artifact_build_id,
        artifact_sha256,
        desktop_version: env!("CARGO_PKG_VERSION").to_owned(),
        generated_at_epoch_ms: epoch_millis(),
        generation: inner.generation,
        last_exit_code: inner.last_exit_code,
        max_restart_attempts: config.restart.max_attempts,
        phase: inner.phase.clone(),
        recent_logs: logger.tail(config.diagnostics.tail_lines),
        restart_attempt: inner.restart_attempt,
        status: format!("{:?}", inner.status).to_ascii_lowercase(),
    }
}

pub(super) fn export_diagnostics(
    paths: &AppPaths,
    diagnostics: &SupervisorDiagnosticsDto,
) -> Result<SupervisorDiagnosticExportDto, SupervisorError> {
    let export_dir = paths.runtime_data_dir.join("diagnostics");
    fs::create_dir_all(&export_dir).map_err(|_| export_error())?;
    let file_name = format!("tk-ops-diagnostics-{}.json", epoch_millis());
    let destination = export_dir.join(&file_name);
    let temporary = export_dir.join(format!(".{file_name}.tmp"));
    let payload = serde_json::to_vec_pretty(diagnostics).map_err(|_| export_error())?;
    {
        let mut file = fs::File::create(&temporary).map_err(|_| export_error())?;
        file.write_all(&payload).map_err(|_| export_error())?;
        file.sync_all().map_err(|_| export_error())?;
    }
    fs::rename(&temporary, &destination).map_err(|_| export_error())?;
    Ok(SupervisorDiagnosticExportDto {
        file_name,
        path: destination.to_string_lossy().into_owned(),
    })
}

fn read_artifact_evidence(paths: &AppPaths) -> Option<(Option<String>, Option<String>)> {
    let content = fs::read_to_string(&paths.sidecar_manifest).ok()?;
    let manifest: Value = serde_json::from_str(&content).ok()?;
    let build_id = manifest
        .get("buildId")
        .and_then(Value::as_str)
        .and_then(|value| controlled_text(value, 128));
    let artifact_hash = hash_file(&paths.sidecar_binary)
        .ok()
        .filter(|value| value.len() == 64);
    Some((build_id, artifact_hash))
}

fn controlled_text(value: &str, max_len: usize) -> Option<String> {
    if value.is_empty()
        || value.len() > max_len
        || !value
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || "._:-".contains(character))
    {
        return None;
    }
    Some(value.to_owned())
}

fn export_error() -> SupervisorError {
    SupervisorError::retryable(
        "RUNTIME_DIAGNOSTICS_EXPORT_FAILED",
        "无法导出 Runtime 诊断，请检查目录权限后重试。",
    )
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use super::SupervisorLogEntryDto;

    #[test]
    fn 日志摘要只接受受控字段并拒绝路径文本() {
        let safe = json!({
            "timestampEpochMs": 42,
            "level": "error",
            "operation": "runtime.failure",
            "errorCode": "RUNTIME_EXITED",
            "logId": "desktop_log_42",
            "path": "C:\\Users\\secret"
        });
        let entry = SupervisorLogEntryDto::from_redacted_value(&safe).unwrap();
        assert_eq!(entry.operation, "runtime.failure");

        let unsafe_value = json!({
            "timestampEpochMs": 42,
            "level": "error",
            "operation": "C:\\Users\\secret",
            "logId": "desktop_log_42"
        });
        assert!(SupervisorLogEntryDto::from_redacted_value(&unsafe_value).is_none());
    }
}
