use std::{
    io::{Read, Write},
    net::{IpAddr, Ipv4Addr, SocketAddr, TcpStream},
    time::{Duration, Instant},
};

use serde_json::Value;

use super::{config::AttemptConfig, SupervisorError};

pub enum HealthOutcome {
    Cancelled,
    Ready,
}

pub fn wait_until_ready(
    attempt: &AttemptConfig,
    startup_timeout: Duration,
    poll_interval: Duration,
    request_timeout: Duration,
    is_current: impl Fn() -> bool,
) -> Result<HealthOutcome, SupervisorError> {
    let deadline = Instant::now() + startup_timeout;
    while Instant::now() < deadline {
        if !is_current() {
            return Ok(HealthOutcome::Cancelled);
        }
        match probe(attempt, request_timeout) {
            Ok(()) => return Ok(HealthOutcome::Ready),
            Err(ProbeError::Fatal(error)) => return Err(error),
            Err(ProbeError::Transient) => {
                std::thread::sleep(poll_interval);
            }
        }
    }
    Err(SupervisorError::retryable(
        "RUNTIME_STARTUP_TIMEOUT",
        "Runtime 启动超时，请查看日志后重试。",
    ))
}

enum ProbeError {
    Fatal(SupervisorError),
    Transient,
}

fn probe(attempt: &AttemptConfig, timeout: Duration) -> Result<(), ProbeError> {
    let address = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), attempt.port);
    let mut stream =
        TcpStream::connect_timeout(&address, timeout).map_err(|_| ProbeError::Transient)?;
    stream
        .set_read_timeout(Some(timeout))
        .map_err(|_| ProbeError::Transient)?;
    stream
        .set_write_timeout(Some(timeout))
        .map_err(|_| ProbeError::Transient)?;
    let request = format!(
        "GET /api/v1/bootstrap/status HTTP/1.1\r\nHost: {}\r\nAuthorization: Bearer {}\r\nAccept: application/json\r\nConnection: close\r\n\r\n",
        attempt.expected_host, attempt.session_token
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|_| ProbeError::Transient)?;
    let mut response = Vec::new();
    stream
        .take(1024 * 1024)
        .read_to_end(&mut response)
        .map_err(|_| ProbeError::Transient)?;
    parse_response(&response)
}

fn parse_response(response: &[u8]) -> Result<(), ProbeError> {
    let split_at = response
        .windows(4)
        .position(|window| window == b"\r\n\r\n")
        .ok_or(ProbeError::Transient)?;
    let headers = String::from_utf8_lossy(&response[..split_at]);
    let status = headers
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|value| value.parse::<u16>().ok())
        .ok_or(ProbeError::Transient)?;
    if matches!(status, 401 | 403) {
        return Err(ProbeError::Fatal(SupervisorError::permanent(
            "RUNTIME_HEALTH_AUTHENTICATION_FAILED",
            "Runtime 会话认证失败，请重新启动桌面应用。",
        )));
    }
    if status != 200 {
        return Err(ProbeError::Transient);
    }
    let body = &response[split_at + 4..];
    let payload: Value = serde_json::from_slice(body).map_err(|_| ProbeError::Transient)?;
    if payload.get("ok").and_then(Value::as_bool) == Some(true) {
        Ok(())
    } else {
        Err(ProbeError::Transient)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn 接受通过认证的就绪信封() {
        let response =
            b"HTTP/1.1 200 OK\r\nContent-Length: 31\r\n\r\n{\"ok\":true,\"data\":{\"status\":\"ready\"}}";
        assert!(parse_response(response).is_ok());
    }

    #[test]
    fn 将认证失败识别为不可重试错误() {
        let response = b"HTTP/1.1 401 Unauthorized\r\nContent-Length: 2\r\n\r\n{}";
        assert!(matches!(
            parse_response(response),
            Err(ProbeError::Fatal(_))
        ));
    }

    #[test]
    fn 启动时限耗尽后返回可重试超时错误() {
        let attempt = AttemptConfig {
            artifact_build_id: "test-build".to_owned(),
            base_url: "http://127.0.0.1:1".to_owned(),
            expected_host: "127.0.0.1:1".to_owned(),
            port: 1,
            session_token: "test-token".to_owned(),
        };
        let result = wait_until_ready(
            &attempt,
            Duration::ZERO,
            Duration::ZERO,
            Duration::ZERO,
            || panic!("零时限不应进入健康探测循环"),
        );

        match result {
            Err(error) => {
                assert_eq!(error.code, "RUNTIME_STARTUP_TIMEOUT");
                assert!(error.retryable);
            }
            _ => panic!("零时限必须直接返回启动超时"),
        }
    }
}
