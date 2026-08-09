from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from persistence.migration import MigrationLock, MigrationLockTimeoutError
import persistence.migration.lock as lock_module


def test_migration_lock_context_releases_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / "migration.lock"

    with MigrationLock(lock_path, timeout_seconds=0.2) as first_lock:
        assert first_lock.acquired

    with MigrationLock(lock_path, timeout_seconds=0.2) as second_lock:
        assert second_lock.acquired


def test_second_process_times_out_while_lock_is_held(tmp_path: Path) -> None:
    lock_path = tmp_path / "migration.lock"
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    process = context.Process(
        target=_hold_lock_in_child,
        args=(str(lock_path), ready, release),
    )
    process.start()
    try:
        assert ready.wait(timeout=20), "子进程未能及时获取迁移锁"
        started_at = time.monotonic()

        with pytest.raises(MigrationLockTimeoutError, match="等待迁移锁超时"):
            with MigrationLock(
                lock_path,
                timeout_seconds=0.2,
                poll_interval_seconds=0.02,
            ):
                pass

        assert time.monotonic() - started_at >= 0.18
    finally:
        release.set()
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=10)
    assert process.exitcode == 0


def test_zero_timeout_attempt_fails_immediately(tmp_path: Path) -> None:
    lock_path = tmp_path / "migration.lock"

    with MigrationLock(lock_path, timeout_seconds=1):
        with pytest.raises(MigrationLockTimeoutError):
            MigrationLock(lock_path, timeout_seconds=0).acquire()


def test_release_failure_does_not_mask_migration_body_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock_path = tmp_path / "migration.lock"

    def fail_unlock(_stream) -> None:  # type: ignore[no-untyped-def]
        raise OSError("模拟释放失败")

    monkeypatch.setattr(lock_module, "_unlock", fail_unlock)

    with pytest.raises(ValueError, match="迁移主体失败"):
        with MigrationLock(lock_path, timeout_seconds=1):
            raise ValueError("迁移主体失败")


def _hold_lock_in_child(lock_path: str, ready, release) -> None:  # type: ignore[no-untyped-def]
    with MigrationLock(Path(lock_path), timeout_seconds=10):
        ready.set()
        release.wait(timeout=30)
