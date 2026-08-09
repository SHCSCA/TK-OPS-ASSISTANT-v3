from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from app.logging import (
    configure_logging,
    redact_log_text,
    redact_log_value,
    shutdown_logging,
)


def test_runtime_jsonl_redacts_message_exception_and_context(
    tmp_path: Path,
) -> None:
    configure_logging(tmp_path, "INFO")
    private_path = tmp_path / "profiles" / "account-secret.json"
    try:
        try:
            raise RuntimeError(
                f"token=exception-secret; path={private_path}"
            )
        except RuntimeError:
            logging.getLogger("persistence.migration.runner").exception(
                "数据库迁移失败，文件=%s，Authorization: Bearer message-secret",
                private_path,
                extra={
                    "context": {
                        "credential": "context-secret",
                        "providerRequestBody": {
                            "prompt": "生成未公开的账号脚本",
                        },
                        "nested": [
                            {"password": "nested-secret"},
                            {"source": str(private_path)},
                        ],
                        "prompt_profile_id": "prompt_profile_safe",
                    }
                },
            )
    finally:
        shutdown_logging()

    entries = [
        json.loads(line)
        for line in (tmp_path / "runtime.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert entries[-1]["logger"] == "persistence.migration.runner"
    plain_entry = repr(entries[-1])
    assert entries[-1]["message"].startswith("数据库迁移失败")
    assert entries[-1]["exception"] == "RuntimeError: 异常详情已脱敏"
    assert entries[-1]["context"]["credential"] == "[已脱敏]"
    assert entries[-1]["context"]["providerRequestBody"] == "[已脱敏]"
    assert entries[-1]["context"]["nested"][0]["password"] == "[已脱敏]"
    assert entries[-1]["context"]["nested"][1]["source"] == "[本地路径已隐藏]"
    assert (
        entries[-1]["context"]["prompt_profile_id"]
        == "prompt_profile_safe"
    )
    for private_value in (
        str(private_path),
        "message-secret",
        "exception-secret",
        "context-secret",
        "nested-secret",
        "生成未公开的账号脚本",
    ):
        assert private_value not in plain_entry
    assert "Authorization: Bearer [已脱敏]" in entries[-1]["message"]


def test_runtime_jsonl_redacts_prompt_and_provider_request_body(
    tmp_path: Path,
) -> None:
    configure_logging(tmp_path, "INFO")
    try:
        logger = logging.getLogger("providers.video")
        logger.error("Prompt: 不应进入日志的完整提示词")
        logger.error(
            'Provider request body: {"input":"private-provider-body"}'
        )
    finally:
        shutdown_logging()

    serialized = (tmp_path / "runtime.jsonl").read_text(encoding="utf-8")
    assert "不应进入日志的完整提示词" not in serialized
    assert "private-provider-body" not in serialized
    assert serialized.count("[已脱敏]") >= 2


def test_runtime_jsonl_redaction_keeps_following_json_fields(
    tmp_path: Path,
) -> None:
    configure_logging(tmp_path, "INFO")
    try:
        logging.getLogger("services.runtime").error(
            '{"token":"private-token","request_id":"req_safe",'
            '"operation_id":"op_safe"}'
        )
    finally:
        shutdown_logging()

    entry = json.loads(
        (tmp_path / "runtime.jsonl").read_text(encoding="utf-8")
    )
    assert "private-token" not in entry["message"]
    assert json.loads(entry["message"]) == {
        "token": "[已脱敏]",
        "request_id": "req_safe",
        "operation_id": "op_safe",
    }


def test_unquoted_sensitive_text_only_stops_at_controlled_trace_fields() -> None:
    prompt = redact_log_text(
        "Prompt: 第一段未公开内容，第二段仍是未公开内容"
    )
    password = redact_log_text(
        "password=第一段密码; 第二段仍是密码"
    )
    traced = redact_log_text(
        "credential=private-value，request_id=req_safe"
    )

    assert prompt == "Prompt: [已脱敏]"
    assert password == "password=[已脱敏]"
    assert traced == "credential=[已脱敏]，request_id=req_safe"


def test_json_sensitive_body_preserves_trace_fields_and_is_idempotent() -> None:
    source = (
        '{"providerRequestBody":{"prompt":"private-prompt"},'
        '"request_id":"req_safe"}'
    )
    redacted = redact_log_text(source)

    assert json.loads(redacted) == {
        "providerRequestBody": "[已脱敏]",
        "request_id": "req_safe",
    }
    assert redact_log_text(redacted) == redacted


def test_structured_api_route_is_preserved_but_local_path_is_hidden() -> None:
    result = redact_log_value(
        {
            "path": "/api/v1/tasks/task_123",
            "request_path": "/api/settings/config",
            "localPath": "/home/tk-ops/private.json",
            "invalidRoute": "/api/v1/../private.json",
        }
    )

    assert result["path"] == "/api/v1/tasks/task_123"
    assert result["request_path"] == "/api/settings/config"
    assert result["localPath"] == "[本地路径已隐藏]"
    assert result["invalidRoute"] == "[本地路径已隐藏]"


def test_failed_reconfiguration_keeps_existing_runtime_handler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_log_dir = tmp_path / "first"
    configure_logging(first_log_dir, "INFO")
    original_handlers = tuple(
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_tk_ops_runtime_handler", False)
    )

    def fail_to_open(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise OSError("模拟日志目录不可写")

    monkeypatch.setattr(logging, "FileHandler", fail_to_open)
    try:
        with pytest.raises(OSError, match="模拟日志目录不可写"):
            configure_logging(tmp_path / "second", "INFO")

        assert tuple(
            handler
            for handler in logging.getLogger().handlers
            if getattr(handler, "_tk_ops_runtime_handler", False)
        ) == original_handlers
        logging.getLogger("runtime.reconfigure").error("重配置失败后仍可记录")
    finally:
        shutdown_logging()

    assert "重配置失败后仍可记录" in (
        first_log_dir / "runtime.jsonl"
    ).read_text(encoding="utf-8")
