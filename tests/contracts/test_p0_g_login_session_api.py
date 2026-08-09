from __future__ import annotations

from pathlib import Path

from schemas.v1.account_login_sessions import LoginSessionDto


def test_login_session_dto_contains_no_credentials_or_cookie_material() -> None:
    fields = set(LoginSessionDto.model_fields)
    assert {
        "id",
        "accountId",
        "environmentId",
        "state",
        "expectedIdentity",
        "detectedIdentity",
        "expiresAt",
        "prepareTaskId",
        "probeTaskId",
        "errorCode",
        "errorLogId",
        "revision",
    } == fields
    assert {"password", "cookie", "credential", "sessionRef"}.isdisjoint(fields)


def test_login_routes_are_account_scoped_and_user_supervised() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    source = (
        repository_root
        / "apps"
        / "py-runtime"
        / "src"
        / "api"
        / "routes"
        / "v1"
        / "account_login_sessions.py"
    ).read_text(encoding="utf-8")
    service = (
        repository_root
        / "apps"
        / "py-runtime"
        / "src"
        / "services"
        / "accounts"
        / "login_sessions.py"
    ).read_text(encoding="utf-8")

    assert 'prefix="/api/v1/accounts/{account_id}/connection"' in source
    assert 'router.post("/login-sessions"' in source
    assert 'router.post("/login-sessions/{session_id}/probe"' in source
    assert 'router.delete("/login-sessions/{session_id}"' in source
    assert 'router.delete("/session"' in source
    assert "https://www.tiktok.com/login" in service
    assert "password" not in service.lower()
    assert "cookie" not in service.lower()
