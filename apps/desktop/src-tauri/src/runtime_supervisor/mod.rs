pub mod commands;
mod config;
mod diagnostics;
mod health;
mod lifecycle;
mod logging;
mod policy;
mod process;
mod state;

use std::{
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex, MutexGuard,
    },
    thread,
};

use config::{prepare_attempt, verify_sidecar, SupervisorConfig};
use diagnostics::export_diagnostics;
pub use diagnostics::{SupervisorDiagnosticExportDto, SupervisorDiagnosticsDto};
use health::{wait_until_ready, HealthOutcome};
use logging::{epoch_millis, SupervisorLogger};
use policy::{
    decide_automatic_restart, decide_process_stop, decide_shutdown, is_generation_active,
    termination_error_code, AutomaticRestartDecision, ProcessStopDecision, ShutdownDecision,
};
use process::ManagedProcess;
use state::SupervisorInner;
pub use state::{
    RuntimeConnectionInfo, SupervisorCommandError, SupervisorError, SupervisorState,
    SupervisorStatusDto,
};
use tauri::{AppHandle, Emitter};
use tauri_plugin_shell::process::CommandEvent;

use crate::app_paths::AppPaths;

const STATUS_EVENT: &str = "runtime-supervisor://status";
const LIFECYCLE_PREFIX: &str = "TK_OPS_LIFECYCLE ";

pub struct RuntimeSupervisor {
    app: AppHandle,
    bootstrap_error: Option<SupervisorError>,
    config: SupervisorConfig,
    inner: Mutex<SupervisorInner>,
    logger: SupervisorLogger,
    paths: Option<AppPaths>,
    shutting_down: AtomicBool,
}

impl RuntimeSupervisor {
    pub fn from_app(app: &AppHandle) -> Self {
        let paths_result = AppPaths::resolve(app);
        let fallback_log = std::env::temp_dir().join("tk-ops-runtime-supervisor-fallback.jsonl");
        let logger = SupervisorLogger::new(
            paths_result
                .as_ref()
                .map(|paths| paths.supervisor_log.clone())
                .unwrap_or(fallback_log),
        );
        let (paths, config, bootstrap_error) = match paths_result {
            Ok(paths) => match SupervisorConfig::load(&paths.bootstrap_config) {
                Ok(config) => (Some(paths), config, None),
                Err(error) => (Some(paths), SupervisorConfig::fallback(), Some(error)),
            },
            Err(error) => (None, SupervisorConfig::fallback(), Some(error)),
        };
        let mut supervisor = Self {
            app: app.clone(),
            bootstrap_error,
            config,
            inner: Mutex::new(SupervisorInner::offline()),
            logger,
            paths,
            shutting_down: AtomicBool::new(false),
        };
        if let Some(error) = supervisor.bootstrap_error.clone() {
            let error = supervisor.record_error(error, "bootstrap");
            supervisor.bootstrap_error = Some(error.clone());
            let inner = supervisor
                .inner
                .get_mut()
                .unwrap_or_else(|poisoned| poisoned.into_inner());
            inner.apply_error(&error);
        }
        supervisor
    }

    pub fn start_initial(self: &Arc<Self>) {
        if self.bootstrap_error.is_some() {
            self.logger.record(
                "error",
                "runtime.initial_start_blocked",
                Some("RUNTIME_BOOTSTRAP_FAILED"),
                None,
            );
            self.emit_status();
            return;
        }
        self.logger
            .record("info", "runtime.initial_start_requested", None, None);
        self.begin_attempt(0, "initializing");
    }

    pub fn record_startup_event(&self, level: &str, operation: &str, error_code: Option<&str>) {
        self.logger.record(level, operation, error_code, None);
    }

    pub fn connection(&self) -> Result<RuntimeConnectionInfo, SupervisorCommandError> {
        let inner = self.lock_inner();
        if inner.status != SupervisorState::Ready {
            return Err(SupervisorCommandError {
                error_code: inner
                    .error_code
                    .clone()
                    .unwrap_or_else(|| "RUNTIME_NOT_READY".to_owned()),
                log_id: inner.log_id.clone(),
                message: "Runtime 尚未就绪，请稍后重试。".to_owned(),
            });
        }
        match (&inner.base_url, &inner.session_token) {
            (Some(base_url), Some(session_token)) => Ok(RuntimeConnectionInfo {
                base_url: base_url.clone(),
                generation: inner.generation,
                session_token: session_token.clone(),
            }),
            _ => Err(SupervisorCommandError {
                error_code: "RUNTIME_CONNECTION_UNAVAILABLE".to_owned(),
                log_id: inner.log_id.clone(),
                message: "Runtime 连接信息不可用，请重新启动 Runtime。".to_owned(),
            }),
        }
    }

    pub fn status(&self) -> SupervisorStatusDto {
        self.snapshot(&self.lock_inner())
    }

    pub fn diagnostics(&self) -> SupervisorDiagnosticsDto {
        diagnostics::build_diagnostics(
            &self.lock_inner(),
            self.paths.as_ref(),
            &self.logger,
            &self.config,
        )
    }

    pub fn export_diagnostics(
        &self,
    ) -> Result<SupervisorDiagnosticExportDto, SupervisorCommandError> {
        let paths = self.paths.as_ref().ok_or_else(|| SupervisorCommandError {
            error_code: "RUNTIME_PATHS_UNAVAILABLE".to_owned(),
            log_id: self.lock_inner().log_id.clone(),
            message: "诊断目录不可用，请检查系统权限。".to_owned(),
        })?;
        export_diagnostics(paths, &self.diagnostics())
            .map_err(|error| self.record_error(error, "diagnostics.export").into())
    }

    pub fn restart(self: &Arc<Self>) -> Result<SupervisorStatusDto, SupervisorCommandError> {
        if let Some(error) = self.bootstrap_error.clone() {
            return Err(error.into());
        }
        {
            let mut inner = self.lock_inner();
            if matches!(
                inner.status,
                SupervisorState::Starting | SupervisorState::Stopping
            ) {
                return Err(SupervisorCommandError {
                    error_code: "RUNTIME_RESTART_IN_PROGRESS".to_owned(),
                    log_id: inner.log_id.clone(),
                    message: "Runtime 正在启动或停止，请稍后重试。".to_owned(),
                });
            }
            inner.begin_stopping("manual_restart");
        }
        self.emit_status();
        self.stop_current("manual_restart");
        self.begin_attempt(0, "restarting");
        Ok(self.status())
    }

    pub fn shutdown(&self) {
        let decision = decide_shutdown(self.shutting_down.swap(true, Ordering::SeqCst));
        if decision == ShutdownDecision::AlreadyStopping {
            return;
        }
        self.update(|inner| {
            inner.begin_stopping("stopping");
        });
        self.stop_current("desktop_exit");
    }

    fn begin_attempt(self: &Arc<Self>, restart_attempt: u32, phase: &str) {
        let generation = {
            let mut inner = self.lock_inner();
            inner.begin_attempt(restart_attempt, phase)
        };
        self.logger
            .record("info", "runtime.attempt_scheduled", None, None);
        self.emit_status();
        let supervisor = self.clone();
        thread::spawn(move || {
            supervisor
                .logger
                .record("info", "runtime.attempt_thread_started", None, None);
            supervisor.launch_attempt(generation);
        });
    }

    fn launch_attempt(self: Arc<Self>, generation: u64) {
        let result = self.launch_attempt_inner(generation);
        if let Err(error) = result {
            self.handle_failure(generation, error);
        }
    }

    fn launch_attempt_inner(self: &Arc<Self>, generation: u64) -> Result<(), SupervisorError> {
        let paths = self.paths.as_ref().ok_or_else(|| {
            SupervisorError::permanent(
                "RUNTIME_PATHS_UNAVAILABLE",
                "Runtime 路径不可用，请重新启动应用。",
            )
        })?;
        let verified_sidecar = verify_sidecar(paths)?;
        self.logger
            .record("info", "runtime.sidecar_verified", None, None);
        let attempt = prepare_attempt(&self.config, verified_sidecar)?;
        self.update_if_current(generation, |inner| {
            inner.phase = "spawning".to_owned();
            inner.base_url = Some(attempt.base_url.clone());
            inner.session_token = Some(attempt.session_token.clone());
        });
        let (mut receiver, process) = ManagedProcess::spawn(&self.app, paths, &attempt)?;
        self.logger
            .record("info", "runtime.process_spawned", None, None);
        self.update_if_current(generation, |inner| {
            inner.phase = "health_check".to_owned();
            inner.process = Some(process);
        });
        let event_supervisor = self.clone();
        tauri::async_runtime::spawn(async move {
            while let Some(event) = receiver.recv().await {
                event_supervisor.handle_process_event(generation, event);
            }
        });
        let outcome = wait_until_ready(
            &attempt,
            self.config.startup_timeout(),
            self.config.poll_interval(),
            self.config.request_timeout(),
            || self.is_current(generation),
        )?;
        if matches!(outcome, HealthOutcome::Ready) {
            self.update_if_current(generation, |inner| {
                inner.mark_ready();
            });
            self.logger.record("info", "runtime.ready", None, None);
        }
        Ok(())
    }

    fn handle_process_event(self: &Arc<Self>, generation: u64, event: CommandEvent) {
        match event {
            CommandEvent::Stdout(bytes) => {
                self.handle_stdout(generation, &bytes);
            }
            CommandEvent::Stderr(_) => {
                self.logger.record(
                    "warning",
                    "runtime.stderr",
                    Some("RUNTIME_STDERR_REDACTED"),
                    None,
                );
            }
            CommandEvent::Error(_) => self.handle_failure(
                generation,
                SupervisorError::retryable(
                    "RUNTIME_PROCESS_EVENT_FAILED",
                    "Runtime 进程监控异常，请重新启动 Runtime。",
                ),
            ),
            CommandEvent::Terminated(payload) => {
                self.update_if_current(generation, |inner| {
                    inner.last_exit_code = payload.code;
                });
                if self.is_current(generation) && !self.shutting_down.load(Ordering::SeqCst) {
                    let error = SupervisorError::retryable(
                        termination_error_code(payload.code),
                        "Runtime 已离线，请查看日志后重试。",
                    );
                    self.handle_failure(generation, error);
                }
            }
            _ => {}
        }
    }

    fn handle_failure(self: &Arc<Self>, generation: u64, error: SupervisorError) {
        if !self.is_current(generation) || self.shutting_down.load(Ordering::SeqCst) {
            return;
        }
        let error = self.record_error(error, "runtime.failure");
        let restart_plan = {
            let mut inner = self.lock_inner();
            if inner.generation != generation {
                return;
            }
            let restart_guard_generation = inner.advance_generation();
            let process = inner.process.take();
            if let Some(mut process) = process {
                process.graceful_shutdown();
                let grace = self.config.shutdown_grace();
                thread::spawn(move || process.force_terminate(grace));
            }
            inner.apply_error(&error);
            match decide_automatic_restart(
                error.retryable,
                inner.restart_attempt,
                self.config.restart.max_attempts,
                self.shutting_down.load(Ordering::SeqCst),
            ) {
                AutomaticRestartDecision::Restart { attempt } => {
                    inner.status = SupervisorState::Starting;
                    inner.phase = "restart_backoff".to_owned();
                    inner.restart_attempt = attempt;
                    Some((attempt, restart_guard_generation))
                }
                AutomaticRestartDecision::StayFailed => None,
            }
        };
        self.emit_status();
        if let Some((attempt, guard_generation)) = restart_plan {
            let delay = self.config.restart_delay(attempt);
            let supervisor = self.clone();
            thread::spawn(move || {
                thread::sleep(delay);
                let may_restart = {
                    let inner = supervisor.lock_inner();
                    inner.generation == guard_generation
                        && inner.status == SupervisorState::Starting
                        && inner.phase == "restart_backoff"
                };
                if may_restart && !supervisor.shutting_down.load(Ordering::SeqCst) {
                    supervisor.begin_attempt(attempt, "restarting");
                }
            });
        }
    }

    fn stop_current(&self, operation: &str) {
        let process = self.lock_inner().process.take();
        let decision = decide_process_stop(process.is_some());
        if let (ProcessStopDecision::GracefulThenForce, Some(mut process)) = (decision, process) {
            process.graceful_shutdown();
            process.force_terminate(self.config.shutdown_grace());
        }
        self.logger.record("info", operation, None, None);
    }

    fn is_current(&self, generation: u64) -> bool {
        is_generation_active(
            generation,
            self.lock_inner().generation,
            self.shutting_down.load(Ordering::SeqCst),
        )
    }

    fn update(&self, update: impl FnOnce(&mut SupervisorInner)) {
        {
            let mut inner = self.lock_inner();
            update(&mut inner);
            inner.updated_at_epoch_ms = epoch_millis();
        }
        self.emit_status();
    }

    fn update_if_current(&self, generation: u64, update: impl FnOnce(&mut SupervisorInner)) {
        {
            let mut inner = self.lock_inner();
            if inner.generation != generation {
                return;
            }
            update(&mut inner);
            inner.updated_at_epoch_ms = epoch_millis();
        }
        self.emit_status();
    }

    fn emit_status(&self) {
        let status = self.status();
        if self.app.emit(STATUS_EVENT, status).is_err() {
            self.logger.record(
                "warning",
                "status.emit.failed",
                Some("RUNTIME_STATUS_EVENT_FAILED"),
                None,
            );
        }
    }

    fn snapshot(&self, inner: &SupervisorInner) -> SupervisorStatusDto {
        SupervisorStatusDto {
            base_url: inner.base_url.clone(),
            can_restart: matches!(
                inner.status,
                SupervisorState::Failed | SupervisorState::Offline | SupervisorState::Ready
            ),
            error_code: inner.error_code.clone(),
            generation: inner.generation,
            log_id: inner.log_id.clone(),
            max_restart_attempts: self.config.restart.max_attempts,
            phase: inner.phase.clone(),
            restart_attempt: inner.restart_attempt,
            status: inner.status,
            updated_at_epoch_ms: inner.updated_at_epoch_ms,
        }
    }

    fn record_error(&self, mut error: SupervisorError, operation: &str) -> SupervisorError {
        let log_id = self.logger.record(
            "error",
            operation,
            Some(&error.code),
            error.log_id.as_deref(),
        );
        error.log_id = Some(log_id);
        error
    }

    fn lock_inner(&self) -> MutexGuard<'_, SupervisorInner> {
        self.inner.lock().unwrap_or_else(|poisoned| {
            self.logger.record(
                "error",
                "state.lock.recovered",
                Some("RUNTIME_SUPERVISOR_STATE_POISONED"),
                None,
            );
            poisoned.into_inner()
        })
    }
}
