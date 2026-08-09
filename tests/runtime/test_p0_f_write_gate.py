from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.write_gate import (
    RUNTIME_WRITE_GATE_CLOSED,
    RuntimeWriteGate,
    RuntimeWriteGateState,
    install_runtime_write_gate_middleware,
)
from errors import DomainError
from persistence.migration.cutover import DurableCutoverJournal


def test_write_gate_returns_visible_503_until_durable_open(
    tmp_path: Path,
) -> None:
    journal = DurableCutoverJournal(tmp_path / "cutover.json")
    started = journal.begin(
        log_id="log_write_gate_test",
        evidence={"automaticRestoreAllowed": True},
    )

    def write_transition(stage: str, evidence) -> None:  # type: ignore[no-untyped-def]
        journal.append(
            cutover_event_id=started.cutover_event_id,
            log_id="log_write_gate_test",
            stage=stage,
            evidence=evidence,
        )

    gate = RuntimeWriteGate(
        cutover_event_id=started.cutover_event_id,
        transition_writer=write_transition,
    )
    app = FastAPI()
    install_runtime_write_gate_middleware(app, gate)

    @app.post("/api/v1/items")
    def create_item() -> dict[str, bool]:
        return {"created": True}

    with TestClient(app) as client:
        blocked = client.post("/api/v1/items")
        assert blocked.status_code == 503
        assert blocked.headers["retry-after"] == "1"
        payload = blocked.json()
        assert payload["ok"] is False
        assert payload["error_code"] == RUNTIME_WRITE_GATE_CLOSED
        assert payload["log_id"].startswith("log_")
        assert payload["meta"]["cutoverEventId"] == started.cutover_event_id

        gate.open()
        accepted = client.post("/api/v1/items")

    assert accepted.status_code == 200
    assert journal.automatic_restore_allowed(started.cutover_event_id) is False


def test_write_gate_stays_closed_when_open_evidence_cannot_persist() -> None:
    def fail_transition(_stage: str, _evidence: object) -> None:
        raise OSError("模拟证据磁盘不可写")

    gate = RuntimeWriteGate(
        cutover_event_id="cut_1234567890abcdef",
        transition_writer=fail_transition,
    )

    with pytest.raises(OSError, match="模拟证据磁盘不可写"):
        gate.open()

    assert gate.snapshot().state is RuntimeWriteGateState.STARTUP_CLOSED
    with pytest.raises(DomainError) as captured:
        gate.require_write_allowed()
    assert getattr(captured.value, "error_code", None) == RUNTIME_WRITE_GATE_CLOSED


def test_runtime_factory_records_cutover_event_and_lifespan_gate(
    runtime_app,
) -> None:
    gate = runtime_app.state.runtime_write_gate
    report = runtime_app.state.migration_report
    assert gate.snapshot().state is RuntimeWriteGateState.STARTUP_CLOSED

    stored_event = runtime_app.state.runtime_event_repository.get(
        f"evt_{report.cutover_event_id}"
    )
    assert stored_event is not None
    assert stored_event.topic == "system:migrations"
    assert stored_event.payload["cutoverEventId"] == report.cutover_event_id

    with TestClient(runtime_app, base_url="http://127.0.0.1:43119"):
        assert gate.snapshot().state is RuntimeWriteGateState.OPEN

    assert gate.snapshot().state is RuntimeWriteGateState.SHUTDOWN_CLOSED
    document = json.loads(
        Path(report.cutover_journal_path).read_text(encoding="utf-8")
    )
    stages = [
        item["stage"]
        for item in document["events"]
        if item["cutoverEventId"] == report.cutover_event_id
    ]
    assert "write_gate_opened" in stages
    assert "write_gate_closed" in stages
