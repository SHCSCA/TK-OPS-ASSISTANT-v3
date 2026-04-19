# AI Provider Adapters And TTS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 `docs/RUNTIME-API-CALLS.md` 第 21.3、21.4、21.5、21.7、24 节落地 `apps/py-runtime` 的文本 Provider 适配层、统一 dispatch、OpenAI TTS 最小接入、`voice_service` 真实生成链路，以及对应测试与文档闭环。

**Architecture:** 保持现有 `routes -> services -> repositories` 分层不变，把文本生成与 TTS 的 Provider 调用下沉到新的 `apps/py-runtime/src/ai/providers/` 目录。`AITextGenerationService` 只负责能力选择、任务记录与 adapter dispatch；`VoiceService` 只负责配音业务编排，真实音频文件落盘与 Provider 调用拆给独立的小模块，继续保留无 TTS dispatcher 时的 `blocked` 兼容路径。

**Tech Stack:** FastAPI + SQLAlchemy + urllib.request + pytest + Pydantic + 本地文件系统

---

## 文件地图

### 新增文件

- `apps/py-runtime/src/ai/providers/__init__.py`  
  Provider registry 与 `dispatch_text_generation` / `dispatch_tts` 统一导出。
- `apps/py-runtime/src/ai/providers/base.py`  
  `TextGenerationRequest`、`TextGenerationResponse`、`TTSRequest`、`TTSResponse`、`TextGenerationAdapter`、`TTSAdapter`。
- `apps/py-runtime/src/ai/providers/_http.py`  
  Provider 公用 HTTP POST、JSON 解析、二进制读取、超时与错误映射。
- `apps/py-runtime/src/ai/providers/errors.py`  
  带 `error_code` 的 Provider 运行时异常定义。
- `apps/py-runtime/src/ai/providers/openai_responses.py`
- `apps/py-runtime/src/ai/providers/openai_chat.py`
- `apps/py-runtime/src/ai/providers/anthropic_messages.py`
- `apps/py-runtime/src/ai/providers/gemini_generate.py`
- `apps/py-runtime/src/ai/providers/cohere_chat.py`
- `apps/py-runtime/src/ai/providers/tts_openai.py`
- `apps/py-runtime/src/services/voice_artifact_store.py`  
  负责按 `{workspace}/voice/{track_id}.{format}` 生成目录并写入音频文件。
- `tests/runtime/test_ai_providers.py`
- `tests/runtime/test_ai_text_generation_service.py`

### 修改文件

- `apps/py-runtime/src/services/ai_text_generation_service.py`
- `apps/py-runtime/src/services/ai_capability_service.py`
- `apps/py-runtime/src/services/voice_service.py`
- `apps/py-runtime/src/repositories/voice_repository.py`
- `apps/py-runtime/src/app/factory.py`
- `apps/py-runtime/src/schemas/ai_capabilities.py`（仅当 HTTP DTO 必须补字段时）
- `tests/runtime/test_ai_capabilities.py`
- `tests/runtime/test_voice_service.py`
- `tests/contracts/test_ai_capabilities_contract.py`
- `tests/contracts/test_voice_runtime_contract.py`
- `tests/contracts/test_scripts_contract.py`
- `tests/contracts/test_storyboards_contract.py`
- `docs/RUNTIME-API-CALLS.md`

### 不在本轮处理

- 前端 `apps/desktop` 适配。
- `tts_azure.py`、`tts_elevenlabs.py`、`tts_volcengine.py`、`tts_minimax.py` 的真实实现。
- `/api/settings/ai-*` 之外的新 Runtime HTTP 路由。

### 子代理写入边界（供后续顺序派工）

- 子代理 1：只写 `apps/py-runtime/src/ai/providers/base.py`、`_http.py`、`errors.py`、`openai_responses.py`、`openai_chat.py`、`__init__.py`、`services/ai_text_generation_service.py`、对应 runtime tests。
- 子代理 2：只写 `anthropic_messages.py`、`gemini_generate.py`、`cohere_chat.py`、`services/ai_capability_service.py`、`app/factory.py`、对应 tests/contracts。
- 子代理 3：只写 `tts_openai.py`、`services/voice_artifact_store.py`、`services/voice_service.py`、`repositories/voice_repository.py`、对应 voice tests/contracts。
- 主代理（我）负责合并、文档回写、全量验证与最终审核。

---

## Task 1: 文本 Provider 基类与 HTTP 公共层

**Files:**
- Create: `apps/py-runtime/src/ai/providers/base.py`
- Create: `apps/py-runtime/src/ai/providers/_http.py`
- Create: `apps/py-runtime/src/ai/providers/errors.py`
- Test: `tests/runtime/test_ai_providers.py`

- [ ] **Step 1: 先写 failing test，锁定 provider 基类与统一错误对象**

```python
def test_text_generation_request_and_tts_request_contract():
    request = TextGenerationRequest(
        model="gpt-5.4",
        system_prompt="system",
        user_prompt="user",
        request_id="req-1",
    )
    assert request.model == "gpt-5.4"

    tts_request = TTSRequest(
        text="你好",
        voice_id="alloy",
        model="gpt-4o-mini-tts",
    )
    assert tts_request.output_format == "mp3"


def test_provider_http_error_keeps_error_code():
    exc = ProviderHTTPException(
        status_code=502,
        detail="AI Provider 认证失败，请检查 API Key",
        error_code="ai_provider_auth_failed",
    )
    assert exc.error_code == "ai_provider_auth_failed"
```

- [ ] **Step 2: 运行 test，确认先红**

Run:

```bash
pytest tests/runtime/test_ai_providers.py -q
```

Expected: 因 `ai.providers.base` / `ai.providers.errors` 尚不存在而失败。

- [ ] **Step 3: 写最小实现**

实现要求：

```python
@dataclass(frozen=True, slots=True)
class TextGenerationRequest: ...

@dataclass(frozen=True, slots=True)
class TTSRequest: ...

class TextGenerationAdapter(ABC):
    @abstractmethod
    def generate(...): ...

class TTSAdapter(ABC):
    @abstractmethod
    def synthesize(...): ...

class ProviderHTTPException(HTTPException):
    def __init__(self, *, status_code: int, detail: str, error_code: str): ...
```

- [ ] **Step 4: 在 `_http.py` 写统一 HTTP helper**

要求最少覆盖：

- Bearer / 自定义 Header / query param key 三类认证入口。
- JSON 响应解析。
- 二进制音频响应读取。
- `401/403/429/5xx/URLError/timeout` 向 `ProviderHTTPException` 的映射。

- [ ] **Step 5: 运行 test，确认转绿**

Run:

```bash
pytest tests/runtime/test_ai_providers.py -q
```

Expected: PASS

---

## Task 2: OpenAI / OpenAI-Compatible 迁移到统一 dispatch

**Files:**
- Create: `apps/py-runtime/src/ai/providers/openai_responses.py`
- Create: `apps/py-runtime/src/ai/providers/openai_chat.py`
- Create: `apps/py-runtime/src/ai/providers/__init__.py`
- Modify: `apps/py-runtime/src/services/ai_text_generation_service.py`
- Test: `tests/runtime/test_ai_text_generation_service.py`
- Test: `tests/runtime/test_ai_providers.py`

- [ ] **Step 1: 先写 failing test，锁定 `_PROTOCOL_MAP + adapter dispatch`**

```python
def test_generate_text_dispatches_openai_via_registry(...):
    service = AITextGenerationService(...)
    result = service.generate_text("script_generation", {"topic": "TK-OPS"})
    assert result.provider == "openai"
    assert result.text == "mocked-output"


def test_generate_text_dispatches_openai_compatible_via_registry(...):
    ...
```

- [ ] **Step 2: 运行 test，确认先红**

Run:

```bash
pytest tests/runtime/test_ai_text_generation_service.py -q
```

Expected: 仍命中旧分支逻辑或 registry 缺失而失败。

- [ ] **Step 3: 迁移旧调用函数到 adapter 文件**

要求：

- `openai_responses.py` 迁移现有 `_call_openai_responses` 逻辑。
- `openai_chat.py` 迁移现有 `_call_openai_compatible_chat` 逻辑。
- `ai/providers/__init__.py` 提供：

```python
_TEXT_ADAPTERS = {...}
_TTS_ADAPTERS = {...}

def dispatch_text_generation(...): ...
def dispatch_tts(...): ...
```

- [ ] **Step 4: 改造 `AITextGenerationService.generate_text()`**

要求：

- 删除硬编码 `if provider == ... elif ...`。
- 使用 `_PROTOCOL_MAP` 和 `dispatch_text_generation(...)`。
- 保留 `GeneratedTextResult` 不变。
- 继续记录 `AIJobRepository.create_running / mark_succeeded / mark_failed`。

- [ ] **Step 5: 运行迁移后的测试与回归**

Run:

```bash
pytest tests/runtime/test_ai_text_generation_service.py tests/runtime/test_ai_providers.py -q
```

Expected: PASS

---

## Task 3: 接入 Anthropic / Gemini / Cohere，并打通细粒度错误码

**Files:**
- Create: `apps/py-runtime/src/ai/providers/anthropic_messages.py`
- Create: `apps/py-runtime/src/ai/providers/gemini_generate.py`
- Create: `apps/py-runtime/src/ai/providers/cohere_chat.py`
- Modify: `apps/py-runtime/src/services/ai_text_generation_service.py`
- Modify: `apps/py-runtime/src/app/factory.py`
- Test: `tests/runtime/test_ai_providers.py`
- Test: `tests/runtime/test_ai_text_generation_service.py`

- [ ] **Step 1: 先写 failing tests，覆盖三种协议和错误码透传**

```python
def test_anthropic_adapter_parses_text_blocks(...): ...
def test_gemini_adapter_url_encodes_model(...): ...
def test_cohere_adapter_parses_v2_chat_response(...): ...
def test_provider_http_exception_error_code_survives_fastapi_handler(...): ...
```

- [ ] **Step 2: 运行 tests，确认先红**

Run:

```bash
pytest tests/runtime/test_ai_providers.py tests/runtime/test_ai_text_generation_service.py -q
```

- [ ] **Step 3: 分别实现三种 adapter**

每个 adapter 必须符合文档：

- `anthropic_messages.py`: `x-api-key` + `anthropic-version`
- `gemini_generate.py`: `:generateContent?key=...`
- `cohere_chat.py`: `/chat`

返回空文本时统一抛 `ProviderHTTPException(status_code=502, error_code="ai_provider_empty_response", ...)`

- [ ] **Step 4: 修改 `app.factory` 的 HTTPException 处理**

要求：

- 若异常对象存在 `error_code` 属性，则优先使用该值。
- 否则继续走当前 `_error_code_for_status(...)`。

目标效果：

```python
content=error_response(
    message,
    request_id=request_id,
    error_code=getattr(exc, "error_code", None) or _error_code_for_status(exc.status_code),
)
```

- [ ] **Step 5: 跑 adapter + service 测试**

Run:

```bash
pytest tests/runtime/test_ai_providers.py tests/runtime/test_ai_text_generation_service.py -q
```

Expected: PASS

---

## Task 4: 扩展 ProviderRuntimeConfig 与 AI 能力运行时元数据

**Files:**
- Modify: `apps/py-runtime/src/services/ai_capability_service.py`
- Modify if needed: `apps/py-runtime/src/schemas/ai_capabilities.py`
- Test: `tests/runtime/test_ai_capabilities.py`
- Test: `tests/contracts/test_ai_capabilities_contract.py`

- [ ] **Step 1: 先写 failing tests，锁定新的 runtime config 能力**

```python
def test_provider_runtime_config_exposes_protocol_family_and_supports_tts(...):
    runtime = service.get_provider_runtime_config("openai")
    assert runtime.protocol_family == "openai_responses"
    assert runtime.supports_tts is True
```

- [ ] **Step 2: 运行 tests，确认先红**

Run:

```bash
pytest tests/runtime/test_ai_capabilities.py tests/contracts/test_ai_capabilities_contract.py -q
```

- [ ] **Step 3: 扩展 `ProviderRuntimeConfig` 与内部 provider metadata**

要求：

- `ProviderRuntimeConfig` 至少新增 `supports_tts: bool`、`protocol_family: str`
- `openai` 标记为 `supports_tts=True`
- `openai_compatible` / `anthropic` / `gemini` / `cohere` 根据文档映射 `protocol_family`

- [ ] **Step 4: 确认 HTTP DTO 只在必要时变更**

边界：

- 若 `/api/settings/ai-capabilities` 与 `/api/settings/ai-providers/*` 当前 contract 不要求暴露 `supportsTts/protocolFamily`，则不要外泄到 HTTP DTO。
- 只在 service 内部与测试辅助层使用。

- [ ] **Step 5: 跑 AI capability 回归**

Run:

```bash
pytest tests/runtime/test_ai_capabilities.py tests/contracts/test_ai_capabilities_contract.py -q
```

Expected: PASS

---

## Task 5: OpenAI TTS Adapter + VoiceService 最小真实接入

**Files:**
- Create: `apps/py-runtime/src/ai/providers/tts_openai.py`
- Create: `apps/py-runtime/src/services/voice_artifact_store.py`
- Modify: `apps/py-runtime/src/services/voice_service.py`
- Modify: `apps/py-runtime/src/repositories/voice_repository.py`
- Modify: `apps/py-runtime/src/app/factory.py`
- Test: `tests/runtime/test_voice_service.py`
- Test: `tests/contracts/test_voice_runtime_contract.py`

- [ ] **Step 1: 先写 failing tests，覆盖可用 TTS 与 blocked fallback 两条路径**

```python
def test_generate_track_returns_blocked_when_tts_dispatcher_missing(...):
    result = service.generate_track(...)
    assert result.track.status == "blocked"
    assert result.task is None


def test_generate_track_returns_processing_task_when_openai_tts_available(...):
    result = service.generate_track(...)
    assert result.track.status == "processing"
    assert result.task["kind"] == "ai-voice"
```

- [ ] **Step 2: 运行 tests，确认先红**

Run:

```bash
pytest tests/runtime/test_voice_service.py tests/contracts/test_voice_runtime_contract.py -q
```

- [ ] **Step 3: 实现 `tts_openai.py`**

要求：

- 调用 `POST {base_url}/audio/speech`
- Bearer 鉴权
- 请求体包含 `model`、`input`、`voice`、`speed`、`response_format`
- 返回 `TTSResponse(audio_bytes=..., content_type=...)`

- [ ] **Step 4: 实现 `voice_artifact_store.py`**

要求：

- 目录规则：`{workspace}/voice/{track_id}.{format}`
- `workspace` 默认从 settings/runtime 当前配置解析
- 自动创建父目录
- 写入失败必须记录日志并抛中文可见错误

- [ ] **Step 5: 扩展 `voice_repository.py`**

最小新增：

```python
def update_track(self, track_id: str, *, file_path: str | None = None, status: str | None = None, provider: str | None = None) -> VoiceTrack | None:
    ...
```

- [ ] **Step 6: 改造 `VoiceService`**

要求：

- `__init__` 新增可选 `tts_dispatcher` 与 `voice_artifact_store`
- `generate_track()`：
  - dispatcher 缺失：保留当前 `blocked`
  - dispatcher 可用：创建 `status="processing"` 的 track，提交 `ai-voice` 任务
  - 任务完成后把音频落盘，更新 `file_path`、`status="ready"`、`provider`
- `regenerate_segment()` 本轮只要求继续保持 TaskBus 契约，不强制写真实分段音频拼接

- [ ] **Step 7: 在 `app.factory` 注入 dispatcher 与 artifact store**

注入边界：

- `AITextGenerationService` 与 `VoiceService` 共用 `AICapabilityService`
- 仅当 `openai` provider 可用于 TTS 时，`dispatch_tts` 才返回可用路径

- [ ] **Step 8: 跑 voice 回归**

Run:

```bash
pytest tests/runtime/test_voice_service.py tests/contracts/test_voice_runtime_contract.py -q
```

Expected: PASS

---

## Task 6: 文档回写与主链路回归

**Files:**
- Modify: `docs/RUNTIME-API-CALLS.md`
- Test: `tests/contracts/test_scripts_contract.py`
- Test: `tests/contracts/test_storyboards_contract.py`
- Test: `tests/contracts/test_ai_capabilities_contract.py`
- Test: `tests/contracts/test_voice_runtime_contract.py`
- Test: `tests/runtime/test_ai_capabilities.py`
- Test: `tests/runtime/test_ai_providers.py`
- Test: `tests/runtime/test_ai_text_generation_service.py`
- Test: `tests/runtime/test_voice_service.py`

- [ ] **Step 1: 回写文档**

必须更新：

- 21.3 Provider 适配器接口契约：标记已落地的 adapter
- 21.4 generate_text dispatch：写明 `_PROTOCOL_MAP`
- 21.5 TTS 调用层：标记本轮仅落地 `tts_openai`
- 21.7 统一错误码：写入已实现错误码
- 24 `ProviderRuntimeConfig`：说明 `supports_tts` / `protocol_family` 的当前实现状态

- [ ] **Step 2: 跑本轮最小验证集**

Run:

```bash
pytest tests/runtime/test_ai_providers.py tests/runtime/test_ai_text_generation_service.py tests/runtime/test_ai_capabilities.py tests/runtime/test_voice_service.py tests/contracts/test_ai_capabilities_contract.py tests/contracts/test_voice_runtime_contract.py tests/contracts/test_scripts_contract.py tests/contracts/test_storyboards_contract.py -q
```

Expected: PASS

- [ ] **Step 3: 跑文档-代码一致性检查**

Run:

```bash
@'
from __future__ import annotations
import re
import sys
from pathlib import Path

repo = Path('.').resolve()
src = repo / 'apps' / 'py-runtime' / 'src'
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from app.factory import create_app

app = create_app()
doc = (repo / 'docs' / 'RUNTIME-API-CALLS.md').read_text(encoding='utf-8')
doc_routes = set(re.findall(r'`(GET|POST|PUT|PATCH|DELETE) (/api[^` ]+)', doc))
code_routes = set()
for route in app.routes:
    path = getattr(route, 'path', '')
    methods = getattr(route, 'methods', None)
    if not path.startswith('/api/') or not methods:
        continue
    for method in methods:
        if method in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}:
            code_routes.add((method, path))
assert doc_routes - code_routes == set()
assert code_routes - doc_routes == set()
'@ | python -
```

Expected: 无断言失败。

---

## 验收标准

- `apps/py-runtime/src/ai/providers/` 不再是空目录，文本与 TTS provider 至少有 1 套真实可运行实现。
- `AITextGenerationService` 不再硬编码仅 `openai` / `openai_compatible` 两个分支。
- `ProviderRuntimeConfig` 具备 `supports_tts` 与 `protocol_family`。
- `voice_service.py` 在有 OpenAI TTS 配置时可返回 `processing + ai-voice task`，无配置时继续兼容 `blocked`。
- AI Provider 相关错误可通过统一 envelope 返回明确 `error_code`。
- `docs/RUNTIME-API-CALLS.md` 第 21/24 节与本轮实现一致。

## 回退点

- 若 Task 2 迁移后 `script_service` / `storyboard_service` 回归失败，先回退 `AITextGenerationService` 到旧逻辑，仅保留 adapter 文件与测试，不继续推进 Task 3。
- 若 Task 5 的 OpenAI TTS 落盘链路不稳定，保留 `tts_openai.py` 与 dispatcher，但 `voice_service.generate_track()` 暂时回退到 `blocked` 路径，不带着半成品文件写入进入主干。
