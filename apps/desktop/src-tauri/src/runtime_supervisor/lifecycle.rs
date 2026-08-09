use std::sync::Arc;

use serde::Deserialize;

use super::{RuntimeSupervisor, SupervisorError, LIFECYCLE_PREFIX};

const MAX_LIFECYCLE_EVENT_BYTES: usize = 16 * 1024;
const MAX_LIFECYCLE_BUFFER_BYTES: usize = 64 * 1024;

impl RuntimeSupervisor {
    pub(super) fn handle_stdout(self: &Arc<Self>, generation: u64, bytes: &[u8]) {
        let lines = match self.buffer_lifecycle_output(generation, bytes) {
            BufferedOutput::Lines(lines) => lines,
            BufferedOutput::Oversized => {
                self.logger.record(
                    "warning",
                    "runtime.lifecycle.oversized",
                    Some("RUNTIME_LIFECYCLE_OVERSIZED"),
                    None,
                );
                return;
            }
            BufferedOutput::Stale => return,
        };
        for bytes in lines {
            let Ok(line) = std::str::from_utf8(&bytes) else {
                self.logger.record(
                    "warning",
                    "runtime.lifecycle.encoding.invalid",
                    Some("RUNTIME_LIFECYCLE_ENCODING_INVALID"),
                    None,
                );
                continue;
            };
            let Some(event) = parse_lifecycle_line(line) else {
                if line.starts_with(LIFECYCLE_PREFIX) {
                    self.logger.record(
                        "warning",
                        "runtime.lifecycle.invalid",
                        Some("RUNTIME_LIFECYCLE_INVALID"),
                        None,
                    );
                }
                continue;
            };
            if !self.is_current(generation) {
                return;
            }
            if event.status == "failed" {
                let error_code = event
                    .error_code
                    .as_deref()
                    .unwrap_or("RUNTIME_STARTUP_FAILED");
                let mut error = if error_code == "RUNTIME_STARTUP_FAILED" {
                    SupervisorError::retryable(error_code, "Runtime 启动失败，请通过关联日志诊断。")
                } else {
                    SupervisorError::permanent(error_code, "Runtime 启动失败，请通过关联日志诊断。")
                };
                error.log_id = event.log_id;
                self.handle_failure(generation, error);
                return;
            }
            if event.status == "starting" {
                self.update_if_current(generation, |inner| {
                    inner.phase = format!("sidecar_{}", event.stage);
                });
            }
        }
    }

    fn buffer_lifecycle_output(&self, generation: u64, bytes: &[u8]) -> BufferedOutput {
        if bytes.len() > MAX_LIFECYCLE_BUFFER_BYTES {
            return BufferedOutput::Oversized;
        }
        let mut inner = self.lock_inner();
        if inner.generation != generation {
            return BufferedOutput::Stale;
        }
        if inner.lifecycle_buffer_generation != generation {
            inner.lifecycle_buffer.clear();
            inner.lifecycle_buffer_generation = generation;
        }
        match append_lifecycle_chunks(&mut inner.lifecycle_buffer, bytes) {
            Ok(lines) => BufferedOutput::Lines(lines),
            Err(()) => {
                inner.lifecycle_buffer.clear();
                BufferedOutput::Oversized
            }
        }
    }
}

enum BufferedOutput {
    Lines(Vec<Vec<u8>>),
    Oversized,
    Stale,
}

fn append_lifecycle_chunks(buffer: &mut Vec<u8>, bytes: &[u8]) -> Result<Vec<Vec<u8>>, ()> {
    if bytes.len() > MAX_LIFECYCLE_BUFFER_BYTES
        || buffer.len().saturating_add(bytes.len()) > MAX_LIFECYCLE_BUFFER_BYTES
    {
        return Err(());
    }
    buffer.extend_from_slice(bytes);

    let mut lines = Vec::new();
    while let Some(index) = buffer.iter().position(|value| *value == b'\n') {
        let mut line = buffer.drain(..=index).collect::<Vec<_>>();
        while line
            .last()
            .is_some_and(|value| matches!(*value, b'\n' | b'\r'))
        {
            line.pop();
        }
        if line.len() > MAX_LIFECYCLE_EVENT_BYTES {
            return Err(());
        }
        if !line.is_empty() {
            lines.push(line);
        }
    }
    if buffer.len() > MAX_LIFECYCLE_EVENT_BYTES {
        return Err(());
    }
    Ok(lines)
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct LifecycleEvent {
    error_code: Option<String>,
    kind: String,
    log_id: Option<String>,
    stage: String,
    status: String,
}

fn parse_lifecycle_line(line: &str) -> Option<LifecycleEvent> {
    let payload = line.strip_prefix(LIFECYCLE_PREFIX)?;
    let event = serde_json::from_str::<LifecycleEvent>(payload).ok()?;
    (event.kind == "runtime_lifecycle").then_some(event)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn 只接受完整的生命周期行信封() {
        let valid = concat!(
            "TK_OPS_LIFECYCLE ",
            "{\"kind\":\"runtime_lifecycle\",\"status\":\"starting\",",
            "\"stage\":\"http\",\"errorCode\":null,\"logId\":null}"
        );
        let event = parse_lifecycle_line(valid).expect("应解析完整信封");
        assert_eq!(event.status, "starting");
        assert_eq!(event.stage, "http");
        assert!(parse_lifecycle_line("普通输出").is_none());
        assert!(parse_lifecycle_line("TK_OPS_LIFECYCLE {\"kind\":\"runtime_lifecycle\"").is_none());
    }

    #[test]
    fn 跨分块缓冲直到收到换行符() {
        let mut buffer = Vec::new();
        assert!(
            append_lifecycle_chunks(&mut buffer, b"TK_OPS_LIFECYCLE {\"kind\":\"runtime_")
                .expect("首段应进入缓冲")
                .is_empty()
        );
        assert!(append_lifecycle_chunks(
            &mut buffer,
            b"lifecycle\",\"status\":\"starting\",\"stage\":\"http\","
        )
        .expect("中间段应进入缓冲")
        .is_empty());
        let lines = append_lifecycle_chunks(&mut buffer, b"\"errorCode\":null,\"logId\":null}\r\n")
            .expect("末段应形成完整行");
        assert_eq!(lines.len(), 1);
        assert!(buffer.is_empty());
        let line = std::str::from_utf8(&lines[0]).expect("完整行应为 UTF-8");
        let event = parse_lifecycle_line(line).expect("完整行应可解析");
        assert_eq!(event.stage, "http");
    }

    #[test]
    fn 拒绝超出单事件上限的未完成行() {
        let mut buffer = Vec::new();
        let oversized = vec![b'x'; MAX_LIFECYCLE_EVENT_BYTES + 1];
        assert!(append_lifecycle_chunks(&mut buffer, &oversized).is_err());
    }
}
