from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from common.identifiers import is_stable_id
from errors import DomainError, ErrorCode

log = logging.getLogger(__name__)

_INPUT_PREFIX = "ai-input://"
_OUTPUT_PREFIX = "ai-output://"


@dataclass(frozen=True, slots=True)
class StoredExecutionContent:
    reference: str
    content_hash: str
    byte_size: int


class AIExecutionContentStore:
    """保存账号隔离的执行输入与输出正文。"""

    def __init__(self, root: Path, *, output_max_bytes: int) -> None:
        if output_max_bytes < 1:
            raise ValueError("AI 输出上限必须大于零")
        self._root = root.resolve()
        self._output_max_bytes = output_max_bytes

    def store_input(
        self,
        account_id: str,
        execution_id: str,
        value: dict[str, object],
    ) -> StoredExecutionContent:
        payload = _canonical_json(value)
        path = self._input_path(account_id, execution_id)
        self._store(path, payload, resource_id=execution_id, kind="input")
        return StoredExecutionContent(
            reference=f"{_INPUT_PREFIX}{account_id}/{execution_id}",
            content_hash=_sha256(payload),
            byte_size=len(payload),
        )

    def read_input(
        self,
        account_id: str,
        reference: str,
    ) -> tuple[dict[str, object], str]:
        execution_id = _id_from_ref(reference, _INPUT_PREFIX, account_id)
        payload = self._read(
            self._input_path(account_id, execution_id),
            resource_id=execution_id,
            kind="input",
        )
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _content_invalid("AI 执行输入已损坏") from exc
        if not isinstance(value, dict):
            raise _content_invalid("AI 执行输入结构无效")
        return dict(value), _sha256(payload)

    def store_output(
        self,
        account_id: str,
        execution_id: str,
        output_id: str,
        text: str,
    ) -> StoredExecutionContent:
        payload = text.encode("utf-8")
        if len(payload) > self._output_max_bytes:
            raise DomainError(
                ErrorCode.AI_PROVIDER_RESPONSE_INVALID,
                "Provider 输出超过配置总线安全上限",
                status_code=502,
                loggable=True,
            )
        path = self._output_path(account_id, execution_id, output_id)
        self._store(path, payload, resource_id=output_id, kind="output")
        return StoredExecutionContent(
            reference=(
                f"{_OUTPUT_PREFIX}{account_id}/{execution_id}/{output_id}"
            ),
            content_hash=_sha256(payload),
            byte_size=len(payload),
        )

    def read_output(
        self,
        account_id: str,
        reference: str,
    ) -> tuple[str, str]:
        execution_id, output_id = _output_ids(reference, account_id)
        payload = self._read(
            self._output_path(account_id, execution_id, output_id),
            resource_id=output_id,
            kind="output",
        )
        try:
            return payload.decode("utf-8"), _sha256(payload)
        except UnicodeDecodeError as exc:
            raise _content_invalid("AI 执行输出已损坏") from exc

    def remove_input(self, account_id: str, reference: str) -> None:
        try:
            execution_id = _id_from_ref(
                reference,
                _INPUT_PREFIX,
                account_id,
            )
            self._input_path(account_id, execution_id).unlink(
                missing_ok=True
            )
        except (DomainError, OSError):
            log.exception(
                "清理未提交 AI 执行输入失败",
                extra={"account_id": account_id},
            )

    def remove_output(self, account_id: str, reference: str) -> None:
        try:
            execution_id, output_id = _output_ids(reference, account_id)
            self._output_path(account_id, execution_id, output_id).unlink(
                missing_ok=True
            )
        except (DomainError, OSError):
            log.exception(
                "清理未提交 AI 执行输出失败",
                extra={"account_id": account_id},
            )

    def _input_path(self, account_id: str, execution_id: str) -> Path:
        return self._scoped_path(
            account_id,
            "inputs",
            f"{execution_id}.json",
            stable_ids=(execution_id,),
        )

    def _output_path(
        self,
        account_id: str,
        execution_id: str,
        output_id: str,
    ) -> Path:
        return self._scoped_path(
            account_id,
            "outputs",
            execution_id,
            f"{output_id}.txt",
            stable_ids=(execution_id, output_id),
        )

    def _scoped_path(
        self,
        account_id: str,
        *parts: str,
        stable_ids: tuple[str, ...],
    ) -> Path:
        if not is_stable_id(account_id) or any(
            not is_stable_id(item) for item in stable_ids
        ):
            raise _content_invalid("AI 执行内容引用无效")
        path = (
            self._root / account_id / "ai-executions" / Path(*parts)
        ).resolve()
        if self._root not in path.parents:
            raise _content_invalid("AI 执行内容超出账号目录")
        return path

    def _store(
        self,
        path: Path,
        payload: bytes,
        *,
        resource_id: str,
        kind: str,
    ) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(path, payload)
        except OSError as exc:
            log.exception(
                "保存 AI 执行受控内容失败",
                extra={
                    "resource_type": f"ai_execution_{kind}",
                    "resource_id": resource_id,
                },
            )
            raise _content_invalid(
                "AI 执行受控内容保存失败"
            ) from exc

    @staticmethod
    def _read(path: Path, *, resource_id: str, kind: str) -> bytes:
        try:
            return path.read_bytes()
        except OSError as exc:
            log.exception(
                "读取 AI 执行受控内容失败",
                extra={
                    "resource_type": f"ai_execution_{kind}",
                    "resource_id": resource_id,
                },
            )
            raise _content_invalid(
                "AI 执行受控内容不可读"
            ) from exc


def _id_from_ref(reference: str, prefix: str, account_id: str) -> str:
    scoped_prefix = f"{prefix}{account_id}/"
    if not reference.startswith(scoped_prefix):
        raise _content_invalid("AI 执行内容不属于当前账号")
    value = reference.removeprefix(scoped_prefix)
    if "/" in value or not is_stable_id(value):
        raise _content_invalid("AI 执行内容引用无效")
    return value


def _output_ids(reference: str, account_id: str) -> tuple[str, str]:
    scoped_prefix = f"{_OUTPUT_PREFIX}{account_id}/"
    if not reference.startswith(scoped_prefix):
        raise _content_invalid("AI 执行输出不属于当前账号")
    values = reference.removeprefix(scoped_prefix).split("/")
    if len(values) != 2 or any(not is_stable_id(item) for item in values):
        raise _content_invalid("AI 执行输出引用无效")
    return values[0], values[1]


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _content_invalid(message: str) -> DomainError:
    return DomainError(
        ErrorCode.AI_EXECUTION_INVALID,
        message,
        status_code=409,
        loggable=True,
    )


__all__ = ["AIExecutionContentStore", "StoredExecutionContent"]
