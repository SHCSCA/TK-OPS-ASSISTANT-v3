# M07 配音中心 Runtime 与 UI 闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 M07 配音中心从“乱码页面 + 前端模拟生成”推进到可验证的 Runtime 契约、真实项目脚本文本输入、音色选择、配音版本记录和中文可见状态反馈。

**Architecture:** 本批采用最小闭环，不先扩大真实 TTS Provider 接入范围。Runtime 新增 `/api/voice` 路由、schema、repository、service，并优先复用现有 `voice_tracks` 表的 `segments_json` 保存段落映射；前端通过 `runtime-client.ts` 和 `voice-studio` Pinia store 消费，不在页面内直接 fetch。无 TTS Provider 时创建明确的 `blocked` 配音轨记录并展示“待配置 AI Provider”，不得伪造成真实音频。

**Tech Stack:** Tauri 2 + Vue 3 + TypeScript + Pinia + Vitest；Python + FastAPI + SQLAlchemy + SQLite + pytest；统一 Runtime JSON 信封 `{ ok: true, data } / { ok: false, error }`。

---

## Status

- 状态：Implemented，用户已于 2026-04-16 确认通过，M07-A Runtime/UI/测试闭环已完成并进入验收。
- 创建时间：2026-04-16。
- 前置已完成：M09 资产中心已合并推送；UTC 时间清理已推送到 `main`，提交 `c8f143b`。
- 本计划只覆盖 M07-A，不接入真实外部 TTS Provider，不生成假音频，不改第 16 页范围。

## Context

当前 M07 现状：

- `apps/desktop/src/pages/voice/VoiceStudioPage.vue` 已存在，但中文文案和注释出现乱码，且页面根组件承担过多 UI 与业务状态。
- `apps/desktop/src/stores/voice-studio.ts` 已存在，能读取脚本文档，但 `generate()` 只是 `setTimeout` 模拟，不走 Runtime。
- `apps/py-runtime/src/domain/models/timeline.py` 已包含 `VoiceTrack` 表，字段为 `id/project_id/timeline_id/source/provider/voice_name/file_path/segments_json/status/created_at`。
- `apps/py-runtime/src/api/routes/` 目前没有 `voice.py`，`app/factory.py` 也未注册 voice service。
- `docs/RUNTIME-API-CALLS.md` 目前只登记到 M09 资产中心和 M09-M15 调用表，缺少 M07 `/api/voice` 唯一契约说明。

## Goals

- 修复配音中心前端 UTF-8 中文乱码，全部用户可见文案保持中文。
- 新增 M07 Runtime API 契约和调用文档，保持 `docs/RUNTIME-API-CALLS.md` 为唯一接口文档。
- 新增最小 `/api/voice` 后端闭环：音色列表、项目配音轨列表、生成配音轨、配音轨详情、删除配音轨。
- 生成动作必须创建真实 `VoiceTrack` 记录；无 Provider 时状态为 `blocked`，错误和下一步可见。
- 前端移除模拟延迟，所有生成和版本读取通过 Runtime client/store。
- 页面拆成小组件，采用 Studio 工作台结构：脚本段落、音色选择、参数面板、波形/状态预览、版本列表。
- 覆盖 loading / empty / ready / generating / blocked / error 状态。

## Non-Goals

- 不接入真实 TTS Provider、OpenAI/Azure 音频输出或音频合成文件。
- 不新增复杂音频波形解析、剪辑时间线落轨或媒体混音能力。
- 不新增 `voice_profiles` 表；本批使用静态/配置化音色 DTO，后续真实 Provider 接入时再迁移。
- 不修改产品 16 页范围，不回退旧 PySide6 壳。

## File Map

Backend:

- Create: `apps/py-runtime/src/schemas/voice.py`，定义 M07 DTO 与请求体。
- Create: `apps/py-runtime/src/repositories/voice_repository.py`，封装 `VoiceTrack` 查询、创建、删除。
- Create: `apps/py-runtime/src/services/voice_service.py`，封装音色列表、段落切分、生成状态和错误语义。
- Create: `apps/py-runtime/src/api/routes/voice.py`，注册 `/api/voice` 路由。
- Modify: `apps/py-runtime/src/api/routes/__init__.py`，导出 `voice_router`。
- Modify: `apps/py-runtime/src/app/factory.py`，实例化 repository/service 并 include router。
- Test: `tests/contracts/test_voice_runtime_contract.py`。
- Test: `tests/runtime/test_voice_service.py`。

Frontend:

- Modify: `apps/desktop/src/types/runtime.ts`，新增 `VoiceProfileDto`、`VoiceTrackDto`、`VoiceTrackGenerateInput`、`VoiceTrackGenerateResultDto` 等类型。
- Modify: `apps/desktop/src/app/runtime-client.ts`，新增 `fetchVoiceProfiles()`、`fetchVoiceTracks()`、`generateVoiceTrack()`、`fetchVoiceTrack()`、`deleteVoiceTrack()`。
- Modify: `apps/desktop/src/stores/voice-studio.ts`，移除模拟生成，接入 Runtime client。
- Rewrite: `apps/desktop/src/pages/voice/VoiceStudioPage.vue`，仅负责页面装配。
- Create: `apps/desktop/src/modules/voice/VoiceScriptPanel.vue`。
- Create: `apps/desktop/src/modules/voice/VoiceProfileRail.vue`。
- Create: `apps/desktop/src/modules/voice/VoiceParamsPanel.vue`。
- Create: `apps/desktop/src/modules/voice/VoicePreviewStage.vue`。
- Create: `apps/desktop/src/modules/voice/VoiceVersionPanel.vue`。
- Test: `apps/desktop/tests/runtime-client-voice.spec.ts`。
- Test: `apps/desktop/tests/voice-studio-store.spec.ts`。
- Test: `apps/desktop/tests/voice-studio-page.spec.ts`。

Docs:

- Modify: `docs/RUNTIME-API-CALLS.md`，新增 M07 配音中心接口与前端调用登记。
- Create: `docs/superpowers/specs/2026-04-16-m07-voice-studio-runtime-ui-design.md`。

## Runtime Contract

### `GET /api/voice/profiles`

返回可用音色列表。V1 从 Runtime 配置或服务内置安全默认值读取，不伪造 Provider 健康。

```json
{
  "ok": true,
  "data": [
    {
      "id": "alloy-zh",
      "provider": "pending_provider",
      "voiceId": "alloy",
      "displayName": "清晰叙述",
      "locale": "zh-CN",
      "tags": ["清晰", "旁白"],
      "enabled": true
    }
  ]
}
```

### `GET /api/voice/projects/{project_id}/tracks`

返回项目下的配音轨版本列表。

```json
{
  "ok": true,
  "data": [
    {
      "id": "voice-1",
      "projectId": "project-1",
      "timelineId": null,
      "source": "tts",
      "provider": "pending_provider",
      "voiceName": "清晰叙述",
      "filePath": null,
      "segments": [
        {
          "segmentIndex": 0,
          "text": "第一段脚本",
          "startMs": null,
          "endMs": null,
          "audioAssetId": null
        }
      ],
      "status": "blocked",
      "createdAt": "2026-04-16T00:00:00Z"
    }
  ]
}
```

### `POST /api/voice/projects/{project_id}/tracks/generate`

请求体：

```json
{
  "profileId": "alloy-zh",
  "sourceText": "第一段脚本\n第二段脚本",
  "speed": 1.0,
  "pitch": 0,
  "emotion": "calm"
}
```

无 Provider 时返回真实阻断状态，不返回假音频：

```json
{
  "ok": true,
  "data": {
    "track": {
      "id": "voice-1",
      "projectId": "project-1",
      "timelineId": null,
      "source": "tts",
      "provider": "pending_provider",
      "voiceName": "清晰叙述",
      "filePath": null,
      "segments": [],
      "status": "blocked",
      "createdAt": "2026-04-16T00:00:00Z"
    },
    "task": null,
    "message": "尚未配置可用 TTS Provider，已保存配音版本草稿。"
  }
}
```

### `GET /api/voice/tracks/{track_id}`

返回单条配音轨详情，含段落映射。

### `DELETE /api/voice/tracks/{track_id}`

删除未被时间线引用的配音轨。若后续存在时间线引用，必须返回统一错误信封。

## Implementation Tasks

### Task 1: 更新唯一接口文档并写后端契约红测

**Files:**

- Modify: `docs/RUNTIME-API-CALLS.md`
- Create: `tests/contracts/test_voice_runtime_contract.py`

- [ ] **Step 1: 在 `docs/RUNTIME-API-CALLS.md` 新增 M07 配音中心章节**

新增内容必须包含：

- `VoiceProfileDto`
- `VoiceTrackSegmentDto`
- `VoiceTrackDto`
- `VoiceTrackGenerateInput`
- `VoiceTrackGenerateResultDto`
- `/api/voice/profiles`
- `/api/voice/projects/{project_id}/tracks`
- `/api/voice/projects/{project_id}/tracks/generate`
- `/api/voice/tracks/{track_id}`
- `/api/voice/tracks/{track_id}` 删除语义
- 前端调用函数登记
- 测试入口登记

- [ ] **Step 2: 写失败的契约测试**

测试文件应验证：

```python
def test_voice_profiles_contract_returns_runtime_envelope(client):
    response = client.get("/api/voice/profiles")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"][0]["displayName"]
```

```python
def test_generate_voice_track_blocks_without_provider(client):
    response = client.post(
        "/api/voice/projects/project-1/tracks/generate",
        json={
            "profileId": "alloy-zh",
            "sourceText": "第一段脚本\n第二段脚本",
            "speed": 1.0,
            "pitch": 0,
            "emotion": "calm",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["track"]["status"] == "blocked"
    assert payload["data"]["task"] is None
    assert "TTS Provider" in payload["data"]["message"]
```

- [ ] **Step 3: 运行红测**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\contracts\test_voice_runtime_contract.py -q
```

Expected: FAIL，原因是 `/api/voice` 路由尚不存在。

### Task 2: 实现 M07 Runtime 最小后端闭环

**Files:**

- Create: `apps/py-runtime/src/schemas/voice.py`
- Create: `apps/py-runtime/src/repositories/voice_repository.py`
- Create: `apps/py-runtime/src/services/voice_service.py`
- Create: `apps/py-runtime/src/api/routes/voice.py`
- Modify: `apps/py-runtime/src/api/routes/__init__.py`
- Modify: `apps/py-runtime/src/app/factory.py`
- Test: `tests/runtime/test_voice_service.py`

- [ ] **Step 1: 写 service 单测**

覆盖：

- `list_profiles()` 至少返回一个中文可见音色。
- `generate_track()` 会按空行切分段落。
- 无 Provider 时不会崩溃，返回 `status="blocked"` 和中文 message。
- 空脚本文本返回中文错误。

- [ ] **Step 2: 创建 `schemas/voice.py`**

核心类型：

```python
class VoiceProfileDto(BaseModel):
    id: str
    provider: str
    voiceId: str
    displayName: str
    locale: str
    tags: list[str]
    enabled: bool

class VoiceTrackSegmentDto(BaseModel):
    segmentIndex: int
    text: str
    startMs: int | None
    endMs: int | None
    audioAssetId: str | None

class VoiceTrackDto(BaseModel):
    id: str
    projectId: str
    timelineId: str | None
    source: str
    provider: str | None
    voiceName: str
    filePath: str | None
    segments: list[VoiceTrackSegmentDto]
    status: str
    createdAt: str

class VoiceTrackGenerateInput(BaseModel):
    profileId: str
    sourceText: str
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: int = Field(default=0, ge=-50, le=50)
    emotion: str = "calm"
```

- [ ] **Step 3: 实现 repository**

要求：

- 查询项目下 tracks 按 `created_at DESC` 排序。
- 创建 `VoiceTrack` 时写入 `segments_json`，不得写假 `file_path`。
- 删除前检查记录存在，不存在返回中文 404。

- [ ] **Step 4: 实现 service**

要求：

- 段落切分使用 `sourceText.splitlines()`，过滤空行，保留原始中文。
- 使用 `apps/py-runtime/src/common/time.py` 的 `utc_now_iso()`。
- 无 Provider 时 `provider="pending_provider"`，`status="blocked"`。
- 所有异常在 service 或路由层转换为中文可见错误，不向 UI 暴露 traceback。

- [ ] **Step 5: 注册路由和依赖**

更新 `api/routes/__init__.py` 和 `app/factory.py`：

- 创建 `voice_repository = VoiceRepository(session_factory=session_factory)`。
- 创建 `voice_service = VoiceService(voice_repository)`。
- 写入 `app.state.voice_repository` 和 `app.state.voice_service`。
- include `voice_router`。

- [ ] **Step 6: 运行后端验证**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\runtime\test_voice_service.py tests\contracts\test_voice_runtime_contract.py -q
venv\Scripts\python.exe -m pytest tests\runtime -q
venv\Scripts\python.exe -m pytest tests\contracts -q
```

Expected: PASS。

### Task 3: 实现前端 Runtime client、类型和 store

**Files:**

- Modify: `apps/desktop/src/types/runtime.ts`
- Modify: `apps/desktop/src/app/runtime-client.ts`
- Modify: `apps/desktop/src/stores/voice-studio.ts`
- Create: `apps/desktop/tests/runtime-client-voice.spec.ts`
- Create: `apps/desktop/tests/voice-studio-store.spec.ts`

- [ ] **Step 1: 写 Runtime client 红测**

验证调用路径：

```typescript
await fetchVoiceProfiles();
await fetchVoiceTracks("project-1");
await generateVoiceTrack("project-1", {
  profileId: "alloy-zh",
  sourceText: "第一段",
  speed: 1,
  pitch: 0,
  emotion: "calm"
});
await fetchVoiceTrack("voice-1");
await deleteVoiceTrack("voice-1");
```

Expected calls:

- `GET /api/voice/profiles`
- `GET /api/voice/projects/project-1/tracks`
- `POST /api/voice/projects/project-1/tracks/generate`
- `GET /api/voice/tracks/voice-1`
- `DELETE /api/voice/tracks/voice-1`

- [ ] **Step 2: 新增 TypeScript DTO**

类型名必须和文档一致：

- `VoiceProfileDto`
- `VoiceTrackSegmentDto`
- `VoiceTrackDto`
- `VoiceTrackGenerateInput`
- `VoiceTrackGenerateResultDto`

- [ ] **Step 3: 新增 Runtime client 函数**

所有函数必须通过 `requestRuntime<T>()`，不得在 store 或页面内直接 `fetch`。

- [ ] **Step 4: 改造 `voice-studio` store**

状态至少包含：

- `profiles`
- `tracks`
- `selectedTrackId`
- `generationResult`
- `status: "idle" | "loading" | "ready" | "generating" | "blocked" | "error"`

行为至少包含：

- `load(projectId)`
- `selectProfile(profileId)`
- `generate()`
- `selectTrack(trackId)`
- `deleteTrack(trackId)`

- [ ] **Step 5: 运行前端 store/client 验证**

Run:

```powershell
npm --prefix apps/desktop run test -- runtime-client-voice.spec.ts voice-studio-store.spec.ts
```

Expected: PASS。

### Task 4: 拆分并重做配音中心 UI

**Files:**

- Rewrite: `apps/desktop/src/pages/voice/VoiceStudioPage.vue`
- Create: `apps/desktop/src/modules/voice/VoiceScriptPanel.vue`
- Create: `apps/desktop/src/modules/voice/VoiceProfileRail.vue`
- Create: `apps/desktop/src/modules/voice/VoiceParamsPanel.vue`
- Create: `apps/desktop/src/modules/voice/VoicePreviewStage.vue`
- Create: `apps/desktop/src/modules/voice/VoiceVersionPanel.vue`
- Create: `apps/desktop/tests/voice-studio-page.spec.ts`

- [ ] **Step 1: 写页面测试**

覆盖：

- 加载态显示“正在读取脚本和配音版本”。
- 无当前项目时显示中文引导，不触发生成。
- 空脚本时显示“请先在脚本与选题中心创建内容”。
- 点击生成后调用 store 的 `generate()`。
- 返回 `blocked` 时显示“尚未配置可用 TTS Provider”。
- 版本列表显示 `blocked/ready/error` 中文状态。

- [ ] **Step 2: 重写页面根组件**

页面只做装配：

```vue
<template>
  <section class="voice-studio-page">
    <VoiceScriptPanel />
    <VoicePreviewStage />
    <VoiceProfileRail />
    <VoiceParamsPanel />
    <VoiceVersionPanel />
  </section>
</template>
```

具体实现可按布局需要调整，但页面根组件不得继续塞入全部样式和业务逻辑。

- [ ] **Step 3: 设计 Studio 布局**

宽屏：

- 左侧：脚本段落列表。
- 中间：波形/生成状态/当前段落预览。
- 右侧：音色与版本。
- 底部或局部面板：语速、音调、情绪。

紧凑窗口：

- 脚本和预览纵向堆叠。
- 右侧版本面板改为下方区域或抽屉式区域。
- 不出现横向溢出。

- [ ] **Step 4: UI 文案和状态**

必须全部中文可见：

- “配音中心”
- “读取脚本文本”
- “生成配音版本”
- “待配置 AI Provider”
- “暂无配音版本”
- “生成失败，请检查 Provider 配置或稍后重试”

禁止出现乱码、英文占位和 `alert()`。

- [ ] **Step 5: 动效与体验**

允许：

- 音色卡 hover 轻微边框强调。
- 生成中波形条 CSS 轻微脉冲。
- 版本切换淡入。

禁止：

- 引入 GSAP、Three.js、WebGL。
- 使用装饰光球或无业务意义动效。
- 因动画导致布局跳动。

- [ ] **Step 6: 运行 UI 验证**

Run:

```powershell
npm --prefix apps/desktop run test -- voice-studio-page.spec.ts voice-studio-store.spec.ts runtime-client-voice.spec.ts
npm --prefix apps/desktop run build
```

Expected: PASS，允许继续保留已知 Material Symbols 构建警告，前提是构建 exit code 为 0。

### Task 5: 集成验收与提交

**Files:**

- All files touched by Tasks 1-4.

- [ ] **Step 1: 运行完整相关验证矩阵**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\runtime\test_voice_service.py tests\contracts\test_voice_runtime_contract.py -q
venv\Scripts\python.exe -m pytest tests\runtime -q
venv\Scripts\python.exe -m pytest tests\contracts -q
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
git diff --check
```

- [ ] **Step 2: 文档一致性检查**

检查：

- `docs/RUNTIME-API-CALLS.md` 是否有 M07 唯一接口说明。
- `docs/superpowers/specs/2026-04-16-m07-voice-studio-runtime-ui-design.md` 是否记录实现细节、UI 状态和测试结果。
- 页面、store、client、backend route 是否与文档路径一致。

- [ ] **Step 3: 验收门槛**

必须满足：

- Reviewer 评分 >= 7.0。
- 无乱码。
- 无假音频、假 Provider、假任务成功。
- Runtime 返回统一信封。
- 前端无直接 fetch。
- 生成失败或 Provider 缺失有中文可见反馈。
- M07 页面至少通过宽屏和紧凑窗口人工检查一次。

- [ ] **Step 4: 提交**

Commit message:

```powershell
git commit -m "feat: implement M07 voice studio runtime flow"
```

## Verification Matrix

Backend:

```powershell
venv\Scripts\python.exe -m pytest tests\runtime\test_voice_service.py tests\contracts\test_voice_runtime_contract.py -q
venv\Scripts\python.exe -m pytest tests\runtime -q
venv\Scripts\python.exe -m pytest tests\contracts -q
```

Frontend:

```powershell
npm --prefix apps/desktop run test -- runtime-client-voice.spec.ts voice-studio-store.spec.ts voice-studio-page.spec.ts
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
```

Repository:

```powershell
git diff --check
```

## Risks

- 现有 `VoiceTrack` 表字段较轻，真实 Provider 接入时可能需要扩展 `ai_job_id`、`updated_at`、`error_message`、`profile_id` 等字段；本批不做迁移，避免扩大范围。
- 当前 `VoiceStudioPage.vue` 已有明显乱码，实施时必须整体按 UTF-8 重写相关组件，不能只局部替换。
- 无 Provider 时仍要创建可追踪记录，但不能误导用户“生成完成”；状态必须是 `blocked` 或等价阻断状态。
- 真实 TTS 接入需要 AI Provider 边界、密钥、音频落盘、资产注册、TaskBus 进度联动，必须作为后续独立 plan。

## Approval Requirement

本计划通过后，下一步先创建对应 spec：

`docs/superpowers/specs/2026-04-16-m07-voice-studio-runtime-ui-design.md`

spec 通过后才能进入实现。
