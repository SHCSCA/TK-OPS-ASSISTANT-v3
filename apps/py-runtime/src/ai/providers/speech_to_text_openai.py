from __future__ import annotations

import json
import logging
import mimetypes
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SpeechToTextResult:
    text: str
    language: str | None = None


class SpeechToTextProviderError(RuntimeError):
    pass


class OpenAICompatibleSpeechToTextProvider:
    def transcribe(
        self,
        *,
        file_path: str,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout_seconds: int = 120,
    ) -> SpeechToTextResult:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"媒体文件不存在：{file_path}")

        endpoint = _resolve_transcription_endpoint(base_url)
        if endpoint == "":
            raise SpeechToTextProviderError("转录 Provider 缺少 Base URL。")
        if model.strip() == "":
            raise SpeechToTextProviderError("转录 Provider 缺少模型配置。")

        body, content_type = _build_multipart_body(
            path=path,
            fields={"model": model.strip()},
        )
        headers = {"Content-Type": content_type}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            log.exception("语音转录 Provider 返回 HTTP 错误 status=%s endpoint=%s", exc.code, endpoint)
            raise SpeechToTextProviderError(f"转录 Provider 返回 HTTP {exc.code}：{detail}") from exc
        except Exception as exc:
            log.exception("语音转录 Provider 调用失败 endpoint=%s", endpoint)
            raise SpeechToTextProviderError(f"转录 Provider 调用失败：{exc}") from exc

        text = str(payload.get("text") or "").strip() if isinstance(payload, dict) else ""
        if text == "":
            raise SpeechToTextProviderError("转录 Provider 未返回有效文本。")

        language = payload.get("language") if isinstance(payload, dict) else None
        return SpeechToTextResult(
            text=text,
            language=str(language).strip() if language else None,
        )


def _resolve_transcription_endpoint(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized == "":
        return ""
    if normalized.endswith("/audio/transcriptions"):
        return normalized
    if normalized.endswith("/responses"):
        normalized = normalized[: -len("/responses")]
    return f"{normalized}/audio/transcriptions"


def _build_multipart_body(
    *,
    path: Path,
    fields: dict[str, str],
) -> tuple[bytes, str]:
    boundary = f"----tkops-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )

    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    chunks.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode("utf-8"),
            path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"
