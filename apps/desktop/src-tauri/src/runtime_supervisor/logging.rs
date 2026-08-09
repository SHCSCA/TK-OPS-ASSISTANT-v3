use std::{
    collections::VecDeque,
    fs,
    fs::OpenOptions,
    io::Write,
    path::PathBuf,
    time::{SystemTime, UNIX_EPOCH},
};

use rand::{rngs::OsRng, RngCore};
use serde_json::json;

use super::diagnostics::SupervisorLogEntryDto;

pub struct SupervisorLogger {
    path: PathBuf,
}

impl SupervisorLogger {
    pub fn new(path: PathBuf) -> Self {
        Self { path }
    }

    pub fn record(
        &self,
        level: &str,
        operation: &str,
        error_code: Option<&str>,
        inherited_log_id: Option<&str>,
    ) -> String {
        let log_id = inherited_log_id
            .map(str::to_owned)
            .unwrap_or_else(generate_log_id);
        let event = json!({
            "timestampEpochMs": epoch_millis(),
            "level": level,
            "module": "tauri.runtime_supervisor",
            "operation": operation,
            "errorCode": error_code,
            "logId": log_id
        });
        match OpenOptions::new()
            .append(true)
            .create(true)
            .open(&self.path)
        {
            Ok(mut file) => {
                let _ = writeln!(file, "{event}");
            }
            Err(_) => {
                eprintln!("TK-OPS Supervisor 日志写入失败：{operation}");
            }
        }
        log_id
    }

    pub fn tail(&self, limit: usize) -> Vec<SupervisorLogEntryDto> {
        let Ok(content) = fs::read_to_string(&self.path) else {
            return Vec::new();
        };
        let mut entries = VecDeque::with_capacity(limit.min(1_000));
        for line in content.lines() {
            let Ok(value) = serde_json::from_str::<serde_json::Value>(line) else {
                continue;
            };
            let Some(entry) = SupervisorLogEntryDto::from_redacted_value(&value) else {
                continue;
            };
            if entries.len() == limit {
                entries.pop_front();
            }
            entries.push_back(entry);
        }
        entries.into_iter().collect()
    }
}

pub fn epoch_millis() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis() as u64)
        .unwrap_or(0)
}

fn generate_log_id() -> String {
    let mut bytes = [0_u8; 12];
    if OsRng.try_fill_bytes(&mut bytes).is_err() {
        return format!("desktop_log_{}", epoch_millis());
    }
    format!("desktop_log_{}", hex::encode(bytes))
}
