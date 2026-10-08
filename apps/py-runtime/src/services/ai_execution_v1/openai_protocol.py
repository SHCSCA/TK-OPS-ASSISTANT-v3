from __future__ import annotations

from services.ai_execution_v1.types import (
    AIProviderRequest,
    AIProviderResult,
    DiscoveredProviderModel,
    ProviderCallError,
    ProviderFailureCategory,
    ProviderRevisionConfig,
    ProviderUsage,
)


def protocol_variant(provider: ProviderRevisionConfig) -> str:
    value = provider.extra_params.get("protocolVariant", "chat_completions")
    if value not in {"chat_completions", "responses"}:
        raise ProviderCallError(
            ProviderFailureCategory.INVALID_REQUEST,
            "Provider 协议类型无效",
        )
    return str(value)


def parse_models(
    payload: dict[str, object],
    *,
    limit: int,
) -> tuple[DiscoveredProviderModel, ...]:
    raw_models = payload.get("data", payload.get("models"))
    if not isinstance(raw_models, list):
        raise ProviderCallError(
            ProviderFailureCategory.INVALID_RESPONSE,
            "Provider 模型清单格式无效",
        )
    models: list[DiscoveredProviderModel] = []
    seen: set[str] = set()
    for item in raw_models[:limit]:
        if isinstance(item, str):
            model_id = item.strip()
            display_name = model_id
        elif isinstance(item, dict):
            raw_id = item.get("id", item.get("name"))
            if not isinstance(raw_id, str):
                continue
            model_id = raw_id.strip()
            raw_name = item.get("display_name", item.get("name"))
            display_name = (
                raw_name.strip() if isinstance(raw_name, str) else model_id
            )
        else:
            continue
        if not model_id or len(model_id) > 256 or model_id in seen:
            continue
        seen.add(model_id)
        models.append(
            DiscoveredProviderModel(model_id, display_name or model_id)
        )
    return tuple(models)


def chat_body(request: AIProviderRequest) -> dict[str, object]:
    messages = list(request.messages)
    if not messages:
        messages = [
            {"role": "user", "content": str(request.input_value or "")}
        ]
    return {
        "model": request.model.model_id,
        "messages": messages,
        "max_tokens": request.max_output_units,
        "temperature": request.temperature,
    }


def responses_body(request: AIProviderRequest) -> dict[str, object]:
    input_value = request.input_value
    if input_value is None:
        input_value = list(request.messages)
    return {
        "model": request.model.model_id,
        "input": input_value,
        "max_output_tokens": request.max_output_units,
        "temperature": request.temperature,
    }


def parse_generation_result(
    payload: dict[str, object],
    *,
    protocol: str,
    expected_model_id: str,
    response_hash: str,
    request_hash: str,
    duration_ms: int,
    response_id_hash: str | None,
) -> AIProviderResult:
    if payload.get("model") != expected_model_id:
        raise _invalid_generation_response()
    if protocol == "chat_completions":
        text, finish_reason = _parse_chat_output(payload)
    else:
        text, finish_reason = _parse_responses_output(payload)
    return AIProviderResult(
        output_text=text,
        request_hash=request_hash,
        response_hash=response_hash,
        response_id_hash=response_id_hash,
        finish_reason=finish_reason,
        usage=_parse_usage(payload.get("usage")),
        duration_ms=duration_ms,
    )


def _parse_chat_output(payload: dict[str, object]) -> tuple[str, str]:
    choices = payload.get("choices")
    if (
        not isinstance(choices, list)
        or not choices
        or not isinstance(choices[0], dict)
    ):
        raise _invalid_generation_response()
    choice = choices[0]
    message = choice.get("message")
    finish = choice.get("finish_reason")
    content = message.get("content") if isinstance(message, dict) else None
    if (
        not isinstance(content, str)
        or not content.strip()
        or not isinstance(finish, str)
        or not finish
    ):
        raise _invalid_generation_response()
    return content, finish


def _parse_responses_output(payload: dict[str, object]) -> tuple[str, str]:
    status = payload.get("status")
    output_text = payload.get("output_text")
    if not isinstance(output_text, str) or not output_text.strip():
        output_text = _collect_responses_text(payload.get("output"))
    if not isinstance(status, str) or not status or not output_text:
        raise _invalid_generation_response()
    return output_text, status


def _collect_responses_text(raw_output: object) -> str:
    if not isinstance(raw_output, list):
        return ""
    texts: list[str] = []
    for item in raw_output:
        if not isinstance(item, dict) or not isinstance(item.get("content"), list):
            continue
        for content in item["content"]:
            if (
                isinstance(content, dict)
                and isinstance(content.get("text"), str)
            ):
                texts.append(content["text"])
    return "".join(texts).strip()


def _parse_usage(raw: object) -> ProviderUsage:
    if not isinstance(raw, dict):
        return ProviderUsage(None, None, None, None)
    input_units = _optional_int(
        raw.get("prompt_tokens", raw.get("input_tokens"))
    )
    output_units = _optional_int(
        raw.get("completion_tokens", raw.get("output_tokens"))
    )
    cached_units = _optional_int(raw.get("cached_tokens"))
    total_units = _optional_int(raw.get("total_tokens"))
    return ProviderUsage(input_units, output_units, cached_units, total_units)


def _optional_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _invalid_generation_response() -> ProviderCallError:
    return ProviderCallError(
        ProviderFailureCategory.INVALID_RESPONSE,
        "Provider 生成响应结构无效",
        request_sent=True,
    )
