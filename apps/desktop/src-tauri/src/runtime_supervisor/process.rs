use std::{process, time::Duration};

use tauri::AppHandle;
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};

use super::{config::AttemptConfig, SupervisorError};
use crate::app_paths::AppPaths;

pub type ProcessEventReceiver = tauri::async_runtime::Receiver<CommandEvent>;

pub struct ManagedProcess {
    child: Option<CommandChild>,
    job: JobGuard,
}

impl ManagedProcess {
    pub fn spawn(
        app: &AppHandle,
        paths: &AppPaths,
        attempt: &AttemptConfig,
    ) -> Result<(ProcessEventReceiver, Self), SupervisorError> {
        let command = app
            .shell()
            .command(&paths.sidecar_binary)
            .current_dir(&paths.runtime_data_dir)
            .env("TK_OPS_RUNTIME_MODE", "production")
            .env("TK_OPS_RUNTIME_PORT", attempt.port.to_string())
            .env("TK_OPS_RUNTIME_SESSION_TOKEN", &attempt.session_token)
            .env("TK_OPS_RUNTIME_EXPECTED_HOST", &attempt.expected_host)
            .env("TK_OPS_RUNTIME_DATA_DIR", &paths.runtime_data_dir)
            .env(
                "TK_OPS_WORKSPACE_ROOT_REGISTRY_PATH",
                &paths.workspace_root_registry,
            )
            .env("TK_OPS_RESOURCE_DIR", &paths.resource_dir)
            .env("TK_OPS_RUNTIME_MANAGED_SIDECAR", "1")
            .env("TK_OPS_RUNTIME_VERSION", env!("CARGO_PKG_VERSION"))
            .env(
                "TK_OPS_RUNTIME_ARTIFACT_BUILD_ID",
                &attempt.artifact_build_id,
            )
            .env("TK_OPS_FFPROBE_PATH", &paths.ffprobe_binary)
            .env("PYTHONUTF8", "1")
            .env("PYTHONIOENCODING", "utf-8")
            .env("TK_OPS_RUNTIME_PARENT_PID", process::id().to_string());
        let (receiver, child) = command.spawn().map_err(|_| {
            SupervisorError::retryable(
                "RUNTIME_SIDECAR_SPAWN_FAILED",
                "Runtime 进程启动失败，请查看日志后重试。",
            )
        })?;
        let job = match JobGuard::attach(child.pid()) {
            Ok(job) => job,
            Err(error) => {
                let _ = child.kill();
                return Err(error);
            }
        };
        Ok((
            receiver,
            Self {
                child: Some(child),
                job,
            },
        ))
    }

    pub fn graceful_shutdown(&mut self) {
        if let Some(child) = self.child.as_mut() {
            let _ = child.write(b"shutdown\n");
        }
    }

    pub fn force_terminate(mut self, grace: Duration) {
        std::thread::sleep(grace);
        self.job.terminate();
        if let Some(child) = self.child.take() {
            let _ = child.kill();
        }
    }
}

#[cfg(windows)]
struct JobGuard {
    handle: windows_sys::Win32::Foundation::HANDLE,
}

#[cfg(windows)]
unsafe impl Send for JobGuard {}

#[cfg(windows)]
impl JobGuard {
    fn attach(pid: u32) -> Result<Self, SupervisorError> {
        use std::{mem, ptr};
        use windows_sys::Win32::{
            Foundation::{CloseHandle, HANDLE},
            System::{
                JobObjects::{
                    AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
                    SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
                    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
                },
                Threading::{
                    OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION, PROCESS_SET_QUOTA,
                    PROCESS_TERMINATE,
                },
            },
        };

        unsafe {
            let handle = CreateJobObjectW(ptr::null(), ptr::null());
            if handle.is_null() {
                return Err(job_error());
            }
            let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = mem::zeroed();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            let configured = SetInformationJobObject(
                handle,
                JobObjectExtendedLimitInformation,
                &info as *const _ as *const _,
                mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            );
            if configured == 0 {
                CloseHandle(handle);
                return Err(job_error());
            }
            let process_handle: HANDLE = OpenProcess(
                PROCESS_SET_QUOTA | PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION,
                0,
                pid,
            );
            if process_handle.is_null() {
                CloseHandle(handle);
                return Err(job_error());
            }
            let assigned = AssignProcessToJobObject(handle, process_handle);
            CloseHandle(process_handle);
            if assigned == 0 {
                CloseHandle(handle);
                return Err(job_error());
            }
            Ok(Self { handle })
        }
    }

    fn terminate(&self) {
        use windows_sys::Win32::System::JobObjects::TerminateJobObject;
        unsafe {
            let _ = TerminateJobObject(self.handle, 1);
        }
    }
}

#[cfg(windows)]
impl Drop for JobGuard {
    fn drop(&mut self) {
        unsafe {
            let _ = windows_sys::Win32::Foundation::CloseHandle(self.handle);
        }
    }
}

#[cfg(windows)]
fn job_error() -> SupervisorError {
    SupervisorError::retryable(
        "RUNTIME_PROCESS_TREE_GUARD_FAILED",
        "无法建立 Runtime 进程树保护，请重新启动应用。",
    )
}

#[cfg(not(windows))]
struct JobGuard;

#[cfg(not(windows))]
impl JobGuard {
    fn attach(_pid: u32) -> Result<Self, SupervisorError> {
        Err(SupervisorError::permanent(
            "RUNTIME_PLATFORM_UNSUPPORTED",
            "当前 Runtime sidecar 仅支持 Windows。",
        ))
    }

    fn terminate(&self) {}
}
