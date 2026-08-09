use serde::Serialize;

use super::{logging::epoch_millis, process::ManagedProcess};

pub(super) struct SupervisorInner {
    pub base_url: Option<String>,
    pub error_code: Option<String>,
    pub generation: u64,
    pub lifecycle_buffer: Vec<u8>,
    pub lifecycle_buffer_generation: u64,
    pub last_exit_code: Option<i32>,
    pub log_id: Option<String>,
    pub phase: String,
    pub process: Option<ManagedProcess>,
    pub restart_attempt: u32,
    pub session_token: Option<String>,
    pub status: SupervisorState,
    pub updated_at_epoch_ms: u64,
}

#[derive(Clone, Copy, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum SupervisorState {
    Failed,
    Offline,
    Ready,
    Starting,
    Stopping,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SupervisorStatusDto {
    pub base_url: Option<String>,
    pub can_restart: bool,
    pub error_code: Option<String>,
    pub generation: u64,
    pub log_id: Option<String>,
    pub max_restart_attempts: u32,
    pub phase: String,
    pub restart_attempt: u32,
    pub status: SupervisorState,
    pub updated_at_epoch_ms: u64,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RuntimeConnectionInfo {
    pub base_url: String,
    pub generation: u64,
    pub session_token: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SupervisorCommandError {
    pub error_code: String,
    pub log_id: Option<String>,
    pub message: String,
}

#[derive(Clone)]
pub struct SupervisorError {
    pub(super) code: String,
    pub(super) log_id: Option<String>,
    pub(super) message: String,
    pub(super) retryable: bool,
}

impl SupervisorError {
    pub fn permanent(code: &str, message: &str) -> Self {
        Self {
            code: code.to_owned(),
            log_id: None,
            message: message.to_owned(),
            retryable: false,
        }
    }

    pub fn retryable(code: &str, message: &str) -> Self {
        Self {
            code: code.to_owned(),
            log_id: None,
            message: message.to_owned(),
            retryable: true,
        }
    }
}

impl SupervisorInner {
    pub fn offline() -> Self {
        Self {
            base_url: None,
            error_code: None,
            generation: 0,
            lifecycle_buffer: Vec::new(),
            lifecycle_buffer_generation: 0,
            last_exit_code: None,
            log_id: None,
            phase: "idle".to_owned(),
            process: None,
            restart_attempt: 0,
            session_token: None,
            status: SupervisorState::Offline,
            updated_at_epoch_ms: epoch_millis(),
        }
    }

    pub fn apply_error(&mut self, error: &SupervisorError) {
        self.error_code = Some(error.code.clone());
        self.log_id = error.log_id.clone();
        self.phase = "failed".to_owned();
        self.status = SupervisorState::Failed;
        self.updated_at_epoch_ms = epoch_millis();
    }

    pub fn begin_attempt(&mut self, restart_attempt: u32, phase: &str) -> u64 {
        let generation = self.advance_generation();
        self.restart_attempt = restart_attempt;
        self.status = SupervisorState::Starting;
        self.phase = phase.to_owned();
        self.base_url = None;
        self.session_token = None;
        self.error_code = None;
        self.log_id = None;
        self.last_exit_code = None;
        self.updated_at_epoch_ms = epoch_millis();
        generation
    }

    pub fn begin_stopping(&mut self, phase: &str) -> u64 {
        let generation = self.advance_generation();
        self.status = SupervisorState::Stopping;
        self.phase = phase.to_owned();
        self.base_url = None;
        self.session_token = None;
        self.updated_at_epoch_ms = epoch_millis();
        generation
    }

    pub fn mark_ready(&mut self) {
        self.status = SupervisorState::Ready;
        self.phase = "ready".to_owned();
        self.updated_at_epoch_ms = epoch_millis();
    }

    pub fn advance_generation(&mut self) -> u64 {
        self.generation = self.generation.saturating_add(1);
        self.lifecycle_buffer.clear();
        self.lifecycle_buffer_generation = self.generation;
        self.generation
    }
}

impl From<SupervisorError> for SupervisorCommandError {
    fn from(value: SupervisorError) -> Self {
        Self {
            error_code: value.code,
            log_id: value.log_id,
            message: value.message,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn 状态按离线启动就绪停止顺序迁移() {
        let mut inner = SupervisorInner::offline();
        assert_eq!(inner.status, SupervisorState::Offline);

        let attempt_generation = inner.begin_attempt(0, "initializing");
        assert_eq!(attempt_generation, 1);
        assert_eq!(inner.status, SupervisorState::Starting);
        assert_eq!(inner.phase, "initializing");

        inner.mark_ready();
        inner.base_url = Some("http://127.0.0.1:43100".to_owned());
        inner.session_token = Some("session-token".to_owned());
        assert_eq!(inner.status, SupervisorState::Ready);

        let stopping_generation = inner.begin_stopping("stopping");
        assert_eq!(stopping_generation, 2);
        assert_eq!(inner.status, SupervisorState::Stopping);
        assert_eq!(inner.phase, "stopping");
        assert!(inner.base_url.is_none());
        assert!(inner.session_token.is_none());
    }

    #[test]
    fn 失败迁移保留稳定错误信息() {
        let mut inner = SupervisorInner::offline();
        let mut error = SupervisorError::retryable("RUNTIME_STARTUP_TIMEOUT", "Runtime 启动超时。");
        error.log_id = Some("log-test".to_owned());

        inner.apply_error(&error);

        assert_eq!(inner.status, SupervisorState::Failed);
        assert_eq!(inner.phase, "failed");
        assert_eq!(inner.error_code.as_deref(), Some("RUNTIME_STARTUP_TIMEOUT"));
        assert_eq!(inner.log_id.as_deref(), Some("log-test"));
    }

    #[test]
    fn 推进世代同时清理残留生命周期缓冲() {
        let mut inner = SupervisorInner::offline();
        inner.lifecycle_buffer.extend_from_slice(b"partial");

        let generation = inner.advance_generation();

        assert_eq!(generation, 1);
        assert_eq!(inner.lifecycle_buffer_generation, 1);
        assert!(inner.lifecycle_buffer.is_empty());
    }
}
