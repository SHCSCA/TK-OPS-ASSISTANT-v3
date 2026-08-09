from __future__ import annotations

import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import BinaryIO
from uuid import uuid4

log = logging.getLogger(__name__)


class MigrationLockError(RuntimeError):
    """迁移锁无法安全获取或释放。"""


class MigrationLockTimeoutError(MigrationLockError):
    """等待其他 Runtime 释放迁移锁超时。"""


class MigrationLock:
    """使用操作系统文件锁协调多个 Runtime 进程的数据库迁移。"""

    def __init__(
        self,
        path: Path,
        timeout_seconds: float,
        *,
        poll_interval_seconds: float = 0.05,
    ) -> None:
        if timeout_seconds < 0:
            raise ValueError("迁移锁超时不能小于零")
        if poll_interval_seconds <= 0:
            raise ValueError("迁移锁轮询间隔必须大于零")
        self.path = path.resolve()
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self._stream: BinaryIO | None = None
        self._token = uuid4().hex

    @property
    def acquired(self) -> bool:
        return self._stream is not None

    def acquire(self) -> "MigrationLock":
        if self.acquired:
            raise MigrationLockError("当前迁移锁对象已经持有锁")

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            stream = self.path.open("a+b")
            _ensure_lock_byte(stream)
        except OSError as exc:
            log.exception("迁移锁文件打开失败")
            raise MigrationLockError("迁移锁文件无法打开，请查看日志") from exc

        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                _try_lock(stream)
                self._stream = stream
                try:
                    self._write_owner_metadata()
                except OSError as exc:
                    self._stream = None
                    try:
                        _unlock(stream)
                    except OSError:
                        log.exception("迁移锁异常清理失败")
                    finally:
                        stream.close()
                    log.exception("迁移锁持有者信息写入失败")
                    raise MigrationLockError(
                        "迁移锁状态写入失败，请查看日志"
                    ) from exc
                log.info("数据库迁移锁已获取: lock=%s", self.path.name)
                return self
            except MigrationLockError:
                raise
            except OSError as exc:
                if time.monotonic() >= deadline:
                    stream.close()
                    log.warning("等待数据库迁移锁超时: lock=%s", self.path.name)
                    raise MigrationLockTimeoutError(
                        "另一个 Runtime 正在迁移数据库，等待迁移锁超时"
                    ) from exc
                time.sleep(min(self.poll_interval_seconds, max(0, deadline - time.monotonic())))

    def release(self) -> None:
        stream = self._stream
        if stream is None:
            return
        self._stream = None
        try:
            _unlock(stream)
            log.info("数据库迁移锁已释放: lock=%s", self.path.name)
        except OSError as exc:
            log.exception("数据库迁移锁释放失败")
            raise MigrationLockError("数据库迁移锁释放失败，请查看日志") from exc
        finally:
            stream.close()

    def __enter__(self) -> "MigrationLock":
        return self.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self.release()
        except MigrationLockError:
            if exc is None:
                raise
            log.exception("迁移主体失败后迁移锁释放也失败，保留主体异常")

    def _write_owner_metadata(self) -> None:
        assert self._stream is not None
        payload = {
            "pid": os.getpid(),
            "token": self._token,
            "acquiredAt": datetime.now(UTC).isoformat(),
        }
        self._stream.seek(0)
        self._stream.truncate()
        self._stream.write(json.dumps(payload, ensure_ascii=True).encode("utf-8"))
        self._stream.flush()
        os.fsync(self._stream.fileno())


def _ensure_lock_byte(stream: BinaryIO) -> None:
    stream.seek(0, os.SEEK_END)
    if stream.tell() == 0:
        stream.write(b"\0")
        stream.flush()
    stream.seek(0)


if os.name == "nt":
    import msvcrt

    def _try_lock(stream: BinaryIO) -> None:
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(stream: BinaryIO) -> None:
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _try_lock(stream: BinaryIO) -> None:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(stream: BinaryIO) -> None:
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
