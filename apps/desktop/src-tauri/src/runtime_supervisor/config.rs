use std::{
    fs::{self, File},
    io::Read,
    net::TcpListener,
    path::Path,
    time::Duration,
};

use rand::{rngs::OsRng, RngCore};
use serde::Deserialize;
use sha2::{Digest, Sha256};

use super::SupervisorError;
use crate::app_paths::AppPaths;

const TARGET_TRIPLE: &str = "x86_64-pc-windows-msvc";
const SCHEMA_READ_MIN: &str = "0017_p0_enforce_and_cutover";
const SCHEMA_READ_MAX: &str = "0022_p0g_production_hardening";
const MAX_BOOTSTRAP_CONFIG_BYTES: u64 = 32 * 1024;
const MAX_MANIFEST_BYTES: u64 = 64 * 1024;

#[derive(Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct SupervisorConfig {
    format_version: u32,
    pub diagnostics: DiagnosticsConfig,
    pub health_poll_interval_ms: u64,
    pub health_request_timeout_ms: u64,
    pub port_selection_attempts: u32,
    pub restart: RestartConfig,
    pub shutdown_grace_ms: u64,
    pub startup_timeout_ms: u64,
}

#[derive(Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct RestartConfig {
    pub initial_delay_ms: u64,
    pub max_attempts: u32,
    pub max_delay_ms: u64,
}

#[derive(Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct DiagnosticsConfig {
    pub tail_lines: usize,
}

impl SupervisorConfig {
    pub fn load(path: &Path) -> Result<Self, SupervisorError> {
        let content = read_bounded_text(
            path,
            MAX_BOOTSTRAP_CONFIG_BYTES,
            "RUNTIME_BOOTSTRAP_CONFIG_MISSING",
            "Runtime 启动配置缺失或过大，请重新安装应用。",
        )?;
        let config: Self = serde_json::from_str(&content).map_err(|_| {
            SupervisorError::permanent(
                "RUNTIME_BOOTSTRAP_CONFIG_INVALID",
                "Runtime 启动配置无效，请重新安装应用。",
            )
        })?;
        config.validate()?;
        Ok(config)
    }

    pub fn startup_timeout(&self) -> Duration {
        Duration::from_millis(self.startup_timeout_ms)
    }

    pub fn poll_interval(&self) -> Duration {
        Duration::from_millis(self.health_poll_interval_ms)
    }

    pub fn request_timeout(&self) -> Duration {
        Duration::from_millis(self.health_request_timeout_ms)
    }

    pub fn shutdown_grace(&self) -> Duration {
        Duration::from_millis(self.shutdown_grace_ms)
    }

    pub fn fallback() -> Self {
        serde_json::from_str(include_str!(
            "../../resources/runtime/runtime-supervisor.bootstrap.json"
        ))
        .unwrap_or(Self {
            format_version: 1,
            diagnostics: DiagnosticsConfig { tail_lines: 200 },
            health_poll_interval_ms: 250,
            health_request_timeout_ms: 900,
            port_selection_attempts: 1,
            restart: RestartConfig {
                initial_delay_ms: 500,
                max_attempts: 3,
                max_delay_ms: 5000,
            },
            shutdown_grace_ms: 1000,
            startup_timeout_ms: 5000,
        })
    }

    pub fn backoff(&self, attempt: u32) -> Duration {
        let exponent = attempt.saturating_sub(1).min(16);
        let factor = 1_u64.checked_shl(exponent).unwrap_or(u64::MAX);
        Duration::from_millis(
            self.restart
                .initial_delay_ms
                .saturating_mul(factor)
                .min(self.restart.max_delay_ms),
        )
    }

    pub fn restart_delay(&self, attempt: u32) -> Duration {
        self.shutdown_grace() + self.backoff(attempt)
    }

    fn validate(&self) -> Result<(), SupervisorError> {
        let valid = self.format_version == 1
            && (5_000..=120_000).contains(&self.startup_timeout_ms)
            && (100..=5_000).contains(&self.health_poll_interval_ms)
            && (100..=5_000).contains(&self.health_request_timeout_ms)
            && self.restart.max_attempts <= 5
            && (100..=10_000).contains(&self.restart.initial_delay_ms)
            && self.restart.max_delay_ms >= self.restart.initial_delay_ms
            && self.restart.max_delay_ms <= 30_000
            && (20..=1_000).contains(&self.diagnostics.tail_lines)
            && self.port_selection_attempts > 0
            && self.port_selection_attempts <= 16
            && (500..=10_000).contains(&self.shutdown_grace_ms);
        if valid {
            Ok(())
        } else {
            Err(SupervisorError::permanent(
                "RUNTIME_BOOTSTRAP_CONFIG_UNSAFE",
                "Runtime 启动配置超出安全范围，请重新安装应用。",
            ))
        }
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct SidecarManifest {
    api_version: String,
    binary: String,
    build_id: String,
    format_version: u32,
    generated_at: String,
    lifecycle_protocol: u32,
    schema_read_max: String,
    schema_read_min: String,
    sha256: String,
    source_sha256: String,
    target: String,
    version: String,
}

pub fn verify_sidecar(paths: &AppPaths) -> Result<VerifiedSidecar, SupervisorError> {
    if !paths.sidecar_binary.is_file()
        || !paths.ffprobe_binary.is_file()
        || !paths.sidecar_manifest.is_file()
    {
        return Err(SupervisorError::permanent(
            "RUNTIME_SIDECAR_RESOURCE_MISSING",
            "Runtime 或媒体工具制品缺失，请重新安装应用。",
        ));
    }
    let content = read_bounded_text(
        &paths.sidecar_manifest,
        MAX_MANIFEST_BYTES,
        "RUNTIME_MANIFEST_READ_FAILED",
        "Runtime 制品清单缺失或过大，请重新安装应用。",
    )?;
    let manifest: SidecarManifest = serde_json::from_str(&content).map_err(|_| {
        SupervisorError::permanent(
            "RUNTIME_MANIFEST_INVALID",
            "Runtime 制品清单无效，请重新安装应用。",
        )
    })?;
    let actual_hash = hash_file(&paths.sidecar_binary)?;
    validate_manifest(&manifest, &actual_hash)?;
    Ok(VerifiedSidecar {
        build_id: manifest.build_id,
    })
}

pub fn prepare_attempt(
    config: &SupervisorConfig,
    verified: VerifiedSidecar,
) -> Result<AttemptConfig, SupervisorError> {
    let port = select_loopback_port(config.port_selection_attempts)?;
    let mut token_bytes = [0_u8; 32];
    OsRng.try_fill_bytes(&mut token_bytes).map_err(|_| {
        SupervisorError::permanent(
            "RUNTIME_TOKEN_GENERATION_FAILED",
            "无法创建安全 Runtime 会话，请重新启动应用。",
        )
    })?;
    let session_token = hex::encode(token_bytes);
    Ok(AttemptConfig {
        artifact_build_id: verified.build_id,
        base_url: format!("http://127.0.0.1:{port}"),
        expected_host: format!("127.0.0.1:{port}"),
        port,
        session_token,
    })
}

pub struct AttemptConfig {
    pub artifact_build_id: String,
    pub base_url: String,
    pub expected_host: String,
    pub port: u16,
    pub session_token: String,
}

pub struct VerifiedSidecar {
    build_id: String,
}

fn select_loopback_port(attempts: u32) -> Result<u16, SupervisorError> {
    for _ in 0..attempts {
        if let Ok(listener) = TcpListener::bind(("127.0.0.1", 0)) {
            if let Ok(address) = listener.local_addr() {
                let port = address.port();
                drop(listener);
                return Ok(port);
            }
        }
    }
    Err(SupervisorError::retryable(
        "RUNTIME_LOOPBACK_PORT_UNAVAILABLE",
        "无法分配本机 Runtime 端口，请稍后重试。",
    ))
}

pub(super) fn hash_file(path: &Path) -> Result<String, SupervisorError> {
    let mut file = File::open(path).map_err(|_| {
        SupervisorError::permanent(
            "RUNTIME_SIDECAR_READ_FAILED",
            "无法读取 Runtime 制品，请重新安装应用。",
        )
    })?;
    let mut digest = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let size = file.read(&mut buffer).map_err(|_| {
            SupervisorError::permanent(
                "RUNTIME_SIDECAR_HASH_FAILED",
                "无法校验 Runtime 制品，请重新安装应用。",
            )
        })?;
        if size == 0 {
            break;
        }
        digest.update(&buffer[..size]);
    }
    Ok(hex::encode_upper(digest.finalize()))
}

fn validate_manifest(manifest: &SidecarManifest, actual_hash: &str) -> Result<(), SupervisorError> {
    let expected_version = env!("CARGO_PKG_VERSION");
    let valid_hash = manifest.sha256.len() == 64
        && manifest
            .sha256
            .chars()
            .all(|value| value.is_ascii_hexdigit())
        && manifest.sha256.eq_ignore_ascii_case(actual_hash);
    let valid_source_hash = manifest.source_sha256.len() == 64
        && manifest
            .source_sha256
            .chars()
            .all(|value| value.is_ascii_hexdigit());
    let expected_build_id = format!(
        "{expected_version}-{TARGET_TRIPLE}-{}",
        actual_hash[..12].to_ascii_lowercase()
    );
    let valid_contract = manifest.api_version == "v1"
        && manifest.binary == "tk-ops-runtime.exe"
        && manifest.format_version == 1
        && is_iso_timestamp(&manifest.generated_at)
        && manifest.lifecycle_protocol == 1
        && manifest.target == TARGET_TRIPLE
        && manifest.version == expected_version
        && manifest.build_id == expected_build_id
        && manifest.schema_read_min == SCHEMA_READ_MIN
        && manifest.schema_read_max == SCHEMA_READ_MAX;
    if valid_hash && valid_source_hash && valid_contract {
        Ok(())
    } else {
        Err(SupervisorError::permanent(
            "RUNTIME_SIDECAR_INTEGRITY_FAILED",
            "Runtime 制品版本或完整性校验失败，请重新安装应用。",
        ))
    }
}

fn is_iso_timestamp(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.len() == 24
        && bytes[4] == b'-'
        && bytes[7] == b'-'
        && bytes[10] == b'T'
        && bytes[13] == b':'
        && bytes[16] == b':'
        && bytes[19] == b'.'
        && bytes[23] == b'Z'
        && bytes.iter().enumerate().all(|(index, byte)| {
            matches!(index, 4 | 7 | 10 | 13 | 16 | 19 | 23) || byte.is_ascii_digit()
        })
}

fn read_bounded_text(
    path: &Path,
    max_bytes: u64,
    error_code: &str,
    message: &str,
) -> Result<String, SupervisorError> {
    let metadata =
        fs::metadata(path).map_err(|_| SupervisorError::permanent(error_code, message))?;
    if !metadata.is_file() || metadata.len() > max_bytes {
        return Err(SupervisorError::permanent(error_code, message));
    }
    fs::read_to_string(path).map_err(|_| SupervisorError::permanent(error_code, message))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn 制品清单必须匹配版本哈希和数据库兼容边界() {
        let hash = "A".repeat(64);
        let build_id = format!(
            "{}-{TARGET_TRIPLE}-{}",
            env!("CARGO_PKG_VERSION"),
            hash[..12].to_ascii_lowercase()
        );
        let mut manifest = SidecarManifest {
            api_version: "v1".to_owned(),
            binary: "tk-ops-runtime.exe".to_owned(),
            build_id,
            format_version: 1,
            generated_at: "2026-07-26T00:00:00.000Z".to_owned(),
            lifecycle_protocol: 1,
            schema_read_max: SCHEMA_READ_MAX.to_owned(),
            schema_read_min: SCHEMA_READ_MIN.to_owned(),
            sha256: hash.clone(),
            source_sha256: "B".repeat(64),
            target: TARGET_TRIPLE.to_owned(),
            version: env!("CARGO_PKG_VERSION").to_owned(),
        };
        assert!(validate_manifest(&manifest, &hash).is_ok());

        manifest.schema_read_max = "9999_unknown".to_owned();
        assert!(validate_manifest(&manifest, &hash).is_err());
    }

    #[test]
    fn 自动重启必须等待旧进程终止后再进入退避() {
        let config = SupervisorConfig {
            format_version: 1,
            diagnostics: DiagnosticsConfig { tail_lines: 200 },
            health_poll_interval_ms: 250,
            health_request_timeout_ms: 900,
            port_selection_attempts: 4,
            restart: RestartConfig {
                initial_delay_ms: 800,
                max_attempts: 2,
                max_delay_ms: 1800,
            },
            shutdown_grace_ms: 1800,
            startup_timeout_ms: 90000,
        };

        assert_eq!(config.restart_delay(1), Duration::from_millis(2600));
        assert_eq!(config.restart_delay(2), Duration::from_millis(3400));
    }
}
