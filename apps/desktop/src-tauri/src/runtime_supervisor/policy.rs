#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum AutomaticRestartDecision {
    Restart { attempt: u32 },
    StayFailed,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum ShutdownDecision {
    AlreadyStopping,
    StopCurrent,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum ProcessStopDecision {
    GracefulThenForce,
    NothingToStop,
}

pub(super) fn decide_automatic_restart(
    retryable: bool,
    current_attempt: u32,
    max_attempts: u32,
    shutting_down: bool,
) -> AutomaticRestartDecision {
    if !retryable || shutting_down || current_attempt >= max_attempts {
        return AutomaticRestartDecision::StayFailed;
    }
    AutomaticRestartDecision::Restart {
        attempt: current_attempt.saturating_add(1),
    }
}

pub(super) fn decide_shutdown(already_stopping: bool) -> ShutdownDecision {
    if already_stopping {
        ShutdownDecision::AlreadyStopping
    } else {
        ShutdownDecision::StopCurrent
    }
}

pub(super) fn decide_process_stop(has_process: bool) -> ProcessStopDecision {
    if has_process {
        ProcessStopDecision::GracefulThenForce
    } else {
        ProcessStopDecision::NothingToStop
    }
}

pub(super) fn is_generation_active(
    expected_generation: u64,
    current_generation: u64,
    shutting_down: bool,
) -> bool {
    expected_generation == current_generation && !shutting_down
}

pub(super) fn termination_error_code(exit_code: Option<i32>) -> &'static str {
    if exit_code == Some(0) {
        "RUNTIME_PROCESS_STOPPED"
    } else {
        "RUNTIME_PROCESS_EXITED"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn 自动重启严格受最大次数限制() {
        let first = decide_automatic_restart(true, 0, 2, false);
        let second = decide_automatic_restart(true, 1, 2, false);
        let exhausted = decide_automatic_restart(true, 2, 2, false);

        assert_eq!(first, AutomaticRestartDecision::Restart { attempt: 1 });
        assert_eq!(second, AutomaticRestartDecision::Restart { attempt: 2 });
        assert_eq!(exhausted, AutomaticRestartDecision::StayFailed);
    }

    #[test]
    fn 永久错误和退出阶段都禁止自动重启() {
        assert_eq!(
            decide_automatic_restart(false, 0, 2, false),
            AutomaticRestartDecision::StayFailed
        );
        assert_eq!(
            decide_automatic_restart(true, 0, 2, true),
            AutomaticRestartDecision::StayFailed
        );
    }

    #[test]
    fn 桌面退出只触发一次停止决策() {
        assert_eq!(decide_shutdown(false), ShutdownDecision::StopCurrent);
        assert_eq!(decide_shutdown(true), ShutdownDecision::AlreadyStopping);
    }

    #[test]
    fn 有进程时先优雅退出再强制清理() {
        assert_eq!(
            decide_process_stop(true),
            ProcessStopDecision::GracefulThenForce
        );
        assert_eq!(
            decide_process_stop(false),
            ProcessStopDecision::NothingToStop
        );
    }

    #[test]
    fn 退出后旧世代事件不能重新激活进程() {
        assert!(is_generation_active(7, 7, false));
        assert!(!is_generation_active(7, 8, false));
        assert!(!is_generation_active(7, 7, true));
    }

    #[test]
    fn 正常和异常退出使用稳定错误码() {
        assert_eq!(termination_error_code(Some(0)), "RUNTIME_PROCESS_STOPPED");
        assert_eq!(termination_error_code(Some(1)), "RUNTIME_PROCESS_EXITED");
        assert_eq!(termination_error_code(None), "RUNTIME_PROCESS_EXITED");
    }
}
