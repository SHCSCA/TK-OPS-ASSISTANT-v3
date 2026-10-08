use std::{fs::OpenOptions, io::Write, path::Path};

use chrono::Utc;
use rand::{rngs::OsRng, RngCore};
use serde_json::json;

pub(super) fn record_failure(log_path: &Path, operation: &str, error_code: &str) -> String {
    let mut random = [0_u8; 8];
    let _ = OsRng.try_fill_bytes(&mut random);
    let log_id = format!("cfl_{}", hex::encode(random));
    let event = json!({
        "timestamp": Utc::now().to_rfc3339(),
        "level": "error",
        "component": "controlled_files",
        "operation": operation,
        "errorCode": error_code,
        "logId": log_id,
    });
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_path) {
        let _ = writeln!(file, "{event}");
    }
    log_id
}
