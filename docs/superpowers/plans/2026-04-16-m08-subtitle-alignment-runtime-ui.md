# M08 字幕对齐中心 Runtime 与 UI 闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 M08 字幕对齐中心从“前端模拟对齐 + 页面内临时字幕”推进到可验证的 Runtime 契约、真实项目脚本文本输入、字幕轨版本记录和中文可见状态反馈。

**Architecture:** 本批采用最小闭环，不接入真实外部字幕对齐 Provider，不生成假精准时间码。Runtime 新增 `/api/subtitles` 路由、schema、repository、service，复用现有 `subtitle_tracks` 表的 `segments_json` 和 `style_json` 保存字幕段落与样式；前端统一通过 `runtime-client.ts` 和 `subtitle-alignment` Pinia store 消费。无音频、无 Provider 或缺脚本文本时返回明确 `blocked` / 中文错误，不伪造成“已完成精准对齐”。

**Tech Stack:** Tauri 2 + Vue 3 + TypeScript + Pinia + Vitest；Python + FastAPI + SQLAlchemy + SQLite + pytest；统一 Runtime JSON 信封 `{ ok: true, data } / { ok: false, error }`。

---

## Status

- 状态：Implemented，用户已于 2026-04-16 确认通过并完成 M08-A 实现。
- 创建时间：2026-04-16。
- 前置已完成：M09 资产中心、Runtime UTC 时间显示清理、M07 配音中心 Runtime/UI 闭环均已推送到 `main`；最近提交 `da5c5ff`。
- 本计划只覆盖 M08-A，不接入真实外部字幕对齐 Provider，不生成假音频转写结果，不做字幕模板资产管理扩展，不改第 16 页范围。
- 实现结果：已新增 `/api/subtitles` Runtime 契约、后端 service/repository/route、前端 Runtime client/store、字幕校对台组件拆分和唯一接口文档登记。
- 验证结果：`npm --prefix apps/desktop run test`、`npm --prefix apps/desktop run build`、`venv\Scripts\python.exe -m pytest tests\contracts -q`、`venv\Scripts\python.exe -m pytest tests\runtime -q`、`venv\Scripts\python.exe -m pytest tests\contracts\test_text_encoding_contract.py -q` 已通过。

## Current Facts

- `docs/PRD.md` 要求 `subtitle_alignment_center` 生成、编辑、校正并导出与音视频对齐的字幕轨，输出 `SubtitleTrack`、字幕样式配置和导出文件。
- `docs/UI-DESIGN-PRD.md` 要求字幕页使用 Studio 模板：左侧列表或段落导航，中部主编辑区，右侧参数、版本、预览或日志；字幕轨、时间码和 Detail Panel 必须可辨识。
- `docs/ARCHITECTURE-BOOTSTRAP.md` 已定义 `SubtitleTrack` 归属 Runtime domain models，并由 `subtitle_alignment_center`、`ai_editing_workspace`、`SubtitleService` 消费。
- `apps/py-runtime/src/domain/models/timeline.py` 已有 `SubtitleTrack` 表：`id/project_id/timeline_id/source/language/style_json/segments_json/status/created_at`。
- `apps/desktop/src/pages/subtitles/SubtitleAlignmentCenterPage.vue` 当前直接调用 `fetchImportedVideos`，失败时静默吞掉，并使用页面内播放/时间线状态。
- `apps/desktop/src/stores/subtitle-alignment.ts` 当前 `align()` 使用 `setTimeout` 模拟，`addSubtitle()` 用随机 ID 和“新字幕内容”，没有 Runtime 读写链路。
- `docs/RUNTIME-API-CALLS.md` 目前没有 M08 `/api/subtitles` 唯一契约登记。
- 当前工作区存在无关改动：`apps/desktop/src-tauri/Cargo.toml`、`scripts/stitch-connect.js`、`scripts/stitch-generate-dashboard.js`。M08 执行不得暂存或重写这些文件。

## Council Decision

本轮未 spawn 真实 subagent；Project Leader 在当前线程模拟必要角色。

| 角色 | 结论 | 关键判断 | 风险 | 验收建议 |
| --- | --- | --- | --- | --- |
| Product Manager | 通过 | M08-A 只做字幕轨真实闭环，不扩展成字幕模板商城或团队协作页 | 输出范围漂移到导出/模板资产管理 | 以 `SubtitleTrack` 版本记录和中文状态为通过依据 |
| TK Operations | 通过 | 字幕能力服务 TikTok 创作者的视频制作链路，必须能解释字幕来源和后续回写价值 | 假精准时间码会误导创作者 | 缺音频时必须显示“待配置/待接入”，不能声称完成 |
| Creative Director | 有条件通过 | 页面应像“字幕校对台”，视觉锚点来自时间码、字幕段落和预览叠字，不做后台表格 | 继续堆按钮、列表和占位视频会降低体验 | 使用字幕带、时间码标尺、右侧诊断/版本面板 |
| Interaction Designer | 通过 | 主路径为读取脚本 -> 生成字幕草稿 -> 选中段落 -> 校正文本/时间码 -> 保存版本 | 静默失败、alert、假播放按钮 | loading、empty、ready、aligning、blocked、error 都要有中文反馈 |
| Backend Runtime Lead | 有条件通过 | `/api/subtitles` route 必须薄，业务在 service，错误进入统一信封 | route 内拼业务、500 暴露 traceback | contract/service tests 覆盖成功和失败信封 |
| Data & Contract Agent | 通过 | 沿用 `subtitle_tracks`，`segments_json` 存字幕段，`style_json` 存样式配置 | 新增表扩大迁移范围 | DTO camelCase，前后端字段一致 |
| AI Pipeline Agent | 有条件通过 | `pending_provider` 不是 Provider 成功；真实对齐后续独立计划补 AI 日志、耗时、失败原因 | 假 AI 对齐结果回流 | 无 Provider 必须 `blocked`，`task=null` |
| Frontend Lead | 通过 | 必须拆组件，页面只做装配；所有 HTTP 走 Runtime client/store | 继续页面内直接 fetch 或 alert | client/store/page 测试覆盖 |
| QA & Verification Agent | 通过 | 后端 contract/service、前端 client/store/page、build 都必须跑 | 只测页面不测契约 | 增加 M08 专项测试并跑一条主链回归 |
| Independent Reviewer | 8.3 / 10 | 范围清楚，风险主要是不能假时间码、不能静默失败 | P1：契约文档不同步 | 文档、测试、UI 状态矩阵齐全后可执行 |

## Goals

- 新增 M08 Runtime API 契约和调用文档，保持 `docs/RUNTIME-API-CALLS.md` 为唯一接口文档。
- 新增最小 `/api/subtitles` 后端闭环：项目字幕轨列表、生成字幕草稿、字幕轨详情、更新字幕轨、删除字幕轨。
- 生成动作必须创建真实 `SubtitleTrack` 记录；无 Provider 或无音频时状态为 `blocked`，返回中文 message。
- 字幕段落必须来自真实项目脚本文本切分，不能写 5 条静态假字幕。
- 前端移除 `setTimeout` 模拟对齐和随机假字幕，所有生成、读取、更新、删除通过 Runtime client/store。
- 页面拆成 Studio 工作台组件：字幕段落列表、字幕预览、时间码校正、样式面板、版本列表/诊断。
- 覆盖 loading / empty / ready / aligning / blocked / error / disabled 状态。

## Non-Goals

- 不接入真实 OpenAI、Whisper、Azure、本地 ASR 或任何外部字幕对齐 Provider。
- 不生成假精准时间码、假转写、假视频预览、假任务进度。
- 不实现 SRT 文件导入/导出落盘；导出作为后续独立批次。
- 不把字幕模板写成本地孤立配置；字幕模板资产化留给资产中心后续批次。
- 不修改 `SubtitleTrack` 数据库表结构，除非实现阶段发现现有字段无法保存最小真实草稿。
- 不引入 GSAP、Three.js、WebGL 或重型动效依赖。

## File Map

Backend:

- Create: `apps/py-runtime/src/schemas/subtitles.py`，定义 M08 DTO、输入体和结果体。
- Create: `apps/py-runtime/src/repositories/subtitle_repository.py`，封装 `SubtitleTrack` 查询、创建、更新、删除。
- Create: `apps/py-runtime/src/services/subtitle_service.py`，封装脚本读取、段落切分、草稿创建、样式与状态语义。
- Create: `apps/py-runtime/src/api/routes/subtitles.py`，注册 `/api/subtitles` 路由。
- Modify: `apps/py-runtime/src/api/routes/__init__.py`，导出 `subtitles_router`。
- Modify: `apps/py-runtime/src/app/factory.py`，实例化 repository/service 并 include router。
- Test: `tests/contracts/test_subtitle_runtime_contract.py`。
- Test: `tests/runtime/test_subtitle_service.py`。

Frontend:

- Modify: `apps/desktop/src/types/runtime.ts`，新增 `SubtitleTrackDto`、`SubtitleSegmentDto`、`SubtitleStyleDto`、`SubtitleTrackGenerateInput`、`SubtitleTrackUpdateInput`、`SubtitleTrackGenerateResultDto` 等类型。
- Modify: `apps/desktop/src/app/runtime-client.ts`，新增 `fetchSubtitleTracks()`、`generateSubtitleTrack()`、`fetchSubtitleTrack()`、`updateSubtitleTrack()`、`deleteSubtitleTrack()`。
- Modify: `apps/desktop/src/stores/subtitle-alignment.ts`，移除模拟对齐，接入 Runtime client，保留 UI 选择和编辑状态。
- Rewrite: `apps/desktop/src/pages/subtitles/SubtitleAlignmentCenterPage.vue`，仅负责页面装配。
- Create: `apps/desktop/src/modules/subtitles/SubtitleSegmentList.vue`。
- Create: `apps/desktop/src/modules/subtitles/SubtitlePreviewStage.vue`。
- Create: `apps/desktop/src/modules/subtitles/SubtitleTimingPanel.vue`。
- Create: `apps/desktop/src/modules/subtitles/SubtitleStylePanel.vue`。
- Create: `apps/desktop/src/modules/subtitles/SubtitleVersionPanel.vue`。
- Test: `apps/desktop/tests/runtime-client-subtitles.spec.ts`。
- Test: `apps/desktop/tests/subtitle-alignment-store.spec.ts`。
- Test: `apps/desktop/tests/subtitle-alignment-page.spec.ts`。

Docs:

- Modify: `docs/RUNTIME-API-CALLS.md`，新增 M08 字幕对齐中心接口与前端调用登记。
- Create after approval: `docs/superpowers/specs/2026-04-16-m08-subtitle-alignment-runtime-ui-design.md`。

## Runtime Contract

### `GET /api/subtitles/projects/{project_id}/tracks`

返回项目下字幕轨版本列表，按 `createdAt DESC`。

```json
{
  "ok": true,
  "data": [
    {
      "id": "subtitle-1",
      "projectId": "project-1",
      "timelineId": null,
      "source": "script",
      "language": "zh-CN",
      "style": {
        "preset": "creator-default",
        "fontSize": 32,
        "position": "bottom",
        "textColor": "#FFFFFF",
        "background": "rgba(0,0,0,0.62)"
      },
      "segments": [
        {
          "segmentIndex": 0,
          "text": "第一段脚本",
          "startMs": null,
          "endMs": null,
          "confidence": null,
          "locked": false
        }
      ],
      "status": "blocked",
      "createdAt": "2026-04-16T00:00:00Z"
    }
  ]
}
```

### `POST /api/subtitles/projects/{project_id}/tracks/generate`

请求体：

```json
{
  "sourceText": "第一段脚本\n第二段脚本",
  "language": "zh-CN",
  "stylePreset": "creator-default"
}
```

无 Provider 或无音频时返回真实阻断状态：

```json
{
  "ok": true,
  "data": {
    "track": {
      "id": "subtitle-1",
      "projectId": "project-1",
      "timelineId": null,
      "source": "script",
      "language": "zh-CN",
      "style": {
        "preset": "creator-default",
        "fontSize": 32,
        "position": "bottom",
        "textColor": "#FFFFFF",
        "background": "rgba(0,0,0,0.62)"
      },
      "segments": [],
      "status": "blocked",
      "createdAt": "2026-04-16T00:00:00Z"
    },
    "task": null,
    "message": "尚未配置可用字幕对齐 Provider，已保存字幕草稿。"
  }
}
```

空脚本失败响应：

```json
{
  "ok": false,
  "error": "字幕源文本为空，请先在脚本与选题中心创建内容。"
}
```

### `PATCH /api/subtitles/tracks/{track_id}`

请求体：

```json
{
  "segments": [
    {
      "segmentIndex": 0,
      "text": "修正后的字幕",
      "startMs": 0,
      "endMs": 2100,
      "confidence": null,
      "locked": true
    }
  ],
  "style": {
    "preset": "creator-default",
    "fontSize": 32,
    "position": "bottom",
    "textColor": "#FFFFFF",
    "background": "rgba(0,0,0,0.62)"
  }
}
```

返回更新后的 `SubtitleTrackDto`。

### `GET /api/subtitles/tracks/{track_id}`

返回单条字幕轨详情，包含字幕段和样式。

### `DELETE /api/subtitles/tracks/{track_id}`

删除尚未被时间线引用的字幕轨。若后续存在时间线引用，必须返回 409 统一错误信封。

## Data Model DTO

`SubtitleStyleDto`

```ts
export type SubtitleStyleDto = {
  preset: string;
  fontSize: number;
  position: "bottom" | "center" | "top";
  textColor: string;
  background: string;
};
```

`SubtitleSegmentDto`

```ts
export type SubtitleSegmentDto = {
  segmentIndex: number;
  text: string;
  startMs: number | null;
  endMs: number | null;
  confidence: number | null;
  locked: boolean;
};
```

`SubtitleTrackDto`

```ts
export type SubtitleTrackDto = {
  id: string;
  projectId: string;
  timelineId: string | null;
  source: "script" | "manual" | "provider";
  language: string;
  style: SubtitleStyleDto;
  segments: SubtitleSegmentDto[];
  status: "blocked" | "ready" | "error" | "aligning";
  createdAt: string;
};
```

## Implementation Tasks

### Task 1: 更新唯一接口文档并写后端契约红测

**Files:**

- Modify: `docs/RUNTIME-API-CALLS.md`
- Create: `tests/contracts/test_subtitle_runtime_contract.py`

- [ ] **Step 1: 在 `docs/RUNTIME-API-CALLS.md` 新增 M08 字幕对齐中心章节**

新增内容必须包含：

- `SubtitleStyleDto`
- `SubtitleSegmentDto`
- `SubtitleTrackDto`
- `SubtitleTrackGenerateInput`
- `SubtitleTrackUpdateInput`
- `SubtitleTrackGenerateResultDto`
- `GET /api/subtitles/projects/{project_id}/tracks`
- `POST /api/subtitles/projects/{project_id}/tracks/generate`
- `GET /api/subtitles/tracks/{track_id}`
- `PATCH /api/subtitles/tracks/{track_id}`
- `DELETE /api/subtitles/tracks/{track_id}`
- 前端调用函数登记
- 测试入口登记

- [ ] **Step 2: 写失败的契约测试**

创建 `tests/contracts/test_subtitle_runtime_contract.py`，核心断言如下：

```python
def test_subtitle_track_generation_blocks_without_provider_and_preserves_segments(runtime_client):
    project_response = runtime_client.post(
        "/api/dashboard/projects",
        json={"name": "字幕项目", "description": "覆盖字幕对齐契约"},
    )
    project_id = project_response.json()["data"]["id"]

    response = runtime_client.post(
        f"/api/subtitles/projects/{project_id}/tracks/generate",
        json={
            "sourceText": "第一段脚本\n\n第二段脚本",
            "language": "zh-CN",
            "stylePreset": "creator-default",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    track = payload["data"]["track"]
    assert track["status"] == "blocked"
    assert track["source"] == "script"
    assert track["segments"][0]["text"] == "第一段脚本"
    assert track["segments"][0]["startMs"] is None
    assert payload["data"]["task"] is None
    assert "字幕对齐 Provider" in payload["data"]["message"]
```

再补同文件测试：

```python
def test_subtitle_track_generation_rejects_empty_source_text(runtime_client):
    response = runtime_client.post(
        "/api/subtitles/projects/project-1/tracks/generate",
        json={
            "sourceText": "   \n  ",
            "language": "zh-CN",
            "stylePreset": "creator-default",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert "字幕源文本为空" in payload["error"]
```

- [ ] **Step 3: 运行红测**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\contracts\test_subtitle_runtime_contract.py -q
```

Expected: FAIL，原因是 `/api/subtitles` 路由尚未注册。

### Task 2: 实现 M08 Runtime 最小后端闭环

**Files:**

- Create: `apps/py-runtime/src/schemas/subtitles.py`
- Create: `apps/py-runtime/src/repositories/subtitle_repository.py`
- Create: `apps/py-runtime/src/services/subtitle_service.py`
- Create: `apps/py-runtime/src/api/routes/subtitles.py`
- Modify: `apps/py-runtime/src/api/routes/__init__.py`
- Modify: `apps/py-runtime/src/app/factory.py`
- Test: `tests/runtime/test_subtitle_service.py`

- [ ] **Step 1: 写 service 单测**

创建 `tests/runtime/test_subtitle_service.py`，覆盖：

- `generate_track()` 使用真实 `sourceText` 切分字幕段，保留中文。
- 无 Provider 时返回 `status="blocked"`、`task=None` 和中文 message。
- `update_track()` 能持久化手动校正后的 `segments_json` 和 `style_json`。
- 空文本返回中文 400。
- 删除不存在字幕轨返回中文 404。

核心断言：

```python
def test_generate_track_creates_blocked_track_with_segments(service):
    result = service.generate_track(
        "project-subtitles",
        SubtitleTrackGenerateInput(
            sourceText="第一段脚本\n\n第二段脚本",
            language="zh-CN",
            stylePreset="creator-default",
        ),
    )

    assert result.track.status == "blocked"
    assert result.track.style.preset == "creator-default"
    assert result.track.segments[0].text == "第一段脚本"
    assert result.track.segments[0].startMs is None
    assert result.task is None
    assert "字幕对齐 Provider" in result.message
```

- [ ] **Step 2: 创建 `schemas/subtitles.py`**

核心 schema：

```python
class SubtitleStyleDto(BaseModel):
    preset: str = "creator-default"
    fontSize: int = Field(default=32, ge=18, le=72)
    position: str = "bottom"
    textColor: str = "#FFFFFF"
    background: str = "rgba(0,0,0,0.62)"


class SubtitleSegmentDto(BaseModel):
    segmentIndex: int
    text: str
    startMs: int | None = None
    endMs: int | None = None
    confidence: float | None = None
    locked: bool = False


class SubtitleTrackDto(BaseModel):
    id: str
    projectId: str
    timelineId: str | None
    source: str
    language: str
    style: SubtitleStyleDto
    segments: list[SubtitleSegmentDto]
    status: str
    createdAt: str
```

- [ ] **Step 3: 创建 repository**

`apps/py-runtime/src/repositories/subtitle_repository.py` 必须包含：

- `list_tracks(project_id: str) -> list[SubtitleTrack]`，按 `created_at DESC`。
- `create_track(track: SubtitleTrack) -> SubtitleTrack`。
- `get_track(track_id: str) -> SubtitleTrack | None`。
- `update_track(track_id, segments_json, style_json, status) -> SubtitleTrack | None`。
- `delete_track(track_id: str) -> bool`。

- [ ] **Step 4: 创建 service**

`SubtitleService` 要求：

- 使用 `sourceText.splitlines()` 切段，过滤空行，保留中文。
- 默认 style 使用 `creator-default`。
- 无 Provider 时 `status="blocked"`，`source="script"`，`task=None`。
- JSON 写入必须 `ensure_ascii=False`。
- 所有数据库异常 `log.exception(...)` 后转为中文 `HTTPException`。
- 空文本返回 400：“字幕源文本为空，请先在脚本与选题中心创建内容。”

- [ ] **Step 5: 注册 route 和 factory 依赖**

`apps/py-runtime/src/api/routes/subtitles.py` 需要提供：

- `GET /api/subtitles/projects/{project_id}/tracks`
- `POST /api/subtitles/projects/{project_id}/tracks/generate`
- `GET /api/subtitles/tracks/{track_id}`
- `PATCH /api/subtitles/tracks/{track_id}`
- `DELETE /api/subtitles/tracks/{track_id}`

所有 route 只调用 `SubtitleService`，返回 `ok_response(...)`。

- [ ] **Step 6: 运行后端验证**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\runtime\test_subtitle_service.py tests\contracts\test_subtitle_runtime_contract.py -q
```

Expected: PASS。

### Task 3: 前端 Runtime client 与 store TDD

**Files:**

- Modify: `apps/desktop/src/types/runtime.ts`
- Modify: `apps/desktop/src/app/runtime-client.ts`
- Modify: `apps/desktop/src/stores/subtitle-alignment.ts`
- Test: `apps/desktop/tests/runtime-client-subtitles.spec.ts`
- Test: `apps/desktop/tests/subtitle-alignment-store.spec.ts`

- [ ] **Step 1: 写 Runtime client 红测**

创建 `apps/desktop/tests/runtime-client-subtitles.spec.ts`，覆盖：

- `fetchSubtitleTracks(projectId)` 使用 `GET /api/subtitles/projects/{project_id}/tracks`。
- `generateSubtitleTrack(projectId, input)` 使用 `POST /api/subtitles/projects/{project_id}/tracks/generate`。
- `fetchSubtitleTrack(trackId)` 使用 `GET /api/subtitles/tracks/{track_id}`。
- `updateSubtitleTrack(trackId, input)` 使用 `PATCH /api/subtitles/tracks/{track_id}`。
- `deleteSubtitleTrack(trackId)` 使用 `DELETE /api/subtitles/tracks/{track_id}`。
- Runtime 错误信封会转换为 `RuntimeRequestError`，中文 message 保留。

- [ ] **Step 2: 写 store 红测**

创建 `apps/desktop/tests/subtitle-alignment-store.spec.ts`，覆盖：

- `load(projectId)` 并行加载脚本文档和字幕轨。
- `generate()` 成功但 blocked 时保存 `generationResult`、更新 `tracks`、选中新版本。
- 空脚本不发起生成，进入中文错误态。
- `updateSelectedTrack()` 保存手动校正后的字幕段和样式。
- `deleteTrack()` 刷新列表并清空选中态。

- [ ] **Step 3: 运行红测**

Run:

```powershell
npm --prefix apps/desktop run test -- runtime-client-subtitles.spec.ts subtitle-alignment-store.spec.ts
```

Expected: FAIL，原因是 client/store 尚未实现。

- [ ] **Step 4: 实现 Runtime 类型和 client 函数**

`apps/desktop/src/types/runtime.ts` 新增 `Subtitle*` 类型；`apps/desktop/src/app/runtime-client.ts` 新增：

```typescript
export async function fetchSubtitleTracks(projectId: string): Promise<SubtitleTrackDto[]> {
  return requestRuntime<SubtitleTrackDto[]>(`/api/subtitles/projects/${projectId}/tracks`);
}

export async function generateSubtitleTrack(
  projectId: string,
  input: SubtitleTrackGenerateInput
): Promise<SubtitleTrackGenerateResultDto> {
  return requestRuntime<SubtitleTrackGenerateResultDto>(
    `/api/subtitles/projects/${projectId}/tracks/generate`,
    {
      body: JSON.stringify(input),
      method: "POST"
    }
  );
}
```

并补齐 `fetchSubtitleTrack()`、`updateSubtitleTrack()`、`deleteSubtitleTrack()`。

- [ ] **Step 5: 重构 store**

`subtitle-alignment` store 必须：

- 移除 `setTimeout`。
- 移除随机假字幕和“新字幕内容”默认假数据。
- 状态扩展为 `"idle" | "loading" | "ready" | "aligning" | "blocked" | "saving" | "error"`。
- 字段包含 `document`、`tracks`、`selectedTrackId`、`generationResult`、`activeSegmentIndex`、`draftSegments`、`style`。
- `load(projectId)` 加载脚本文档和字幕轨。
- `generate()` 使用脚本正文调用 Runtime。
- `updateSelectedTrack()` 通过 `updateSubtitleTrack()` 保存段落和样式。
- `deleteTrack(trackId)` 删除后重新读取列表。
- Runtime 错误转为 `error.message` 并渲染到页面。

- [ ] **Step 6: 运行前端 client/store 验证**

Run:

```powershell
npm --prefix apps/desktop run test -- runtime-client-subtitles.spec.ts subtitle-alignment-store.spec.ts
```

Expected: PASS。

### Task 4: 拆分并重做字幕对齐中心 UI

**Files:**

- Rewrite: `apps/desktop/src/pages/subtitles/SubtitleAlignmentCenterPage.vue`
- Create: `apps/desktop/src/modules/subtitles/SubtitleSegmentList.vue`
- Create: `apps/desktop/src/modules/subtitles/SubtitlePreviewStage.vue`
- Create: `apps/desktop/src/modules/subtitles/SubtitleTimingPanel.vue`
- Create: `apps/desktop/src/modules/subtitles/SubtitleStylePanel.vue`
- Create: `apps/desktop/src/modules/subtitles/SubtitleVersionPanel.vue`
- Test: `apps/desktop/tests/subtitle-alignment-page.spec.ts`

- [ ] **Step 1: 写页面红测**

创建 `apps/desktop/tests/subtitle-alignment-page.spec.ts`，覆盖：

- 有项目时显示 “M08 字幕对齐中心”、“字幕校对台”、真实脚本文本段落。
- 点击 “生成字幕草稿” 后显示 “尚未配置可用字幕对齐 Provider” 和 “待配置 Provider”。
- 页面不调用 `window.alert`。
- 没有项目时显示 “请先选择项目” 并禁用生成入口。
- 页面文本不包含乱码片段。

- [ ] **Step 2: 创建组件**

组件职责：

- `SubtitleSegmentList.vue`：展示字幕段落、文本编辑、选中态、loading/empty/error。
- `SubtitlePreviewStage.vue`：展示黑底预览、当前字幕叠字、blocked/ready/error 状态，不显示假视频播放。
- `SubtitleTimingPanel.vue`：展示当前段落时间码，支持毫秒级输入和 +/- 微调。
- `SubtitleStylePanel.vue`：展示本批可保存的样式字段，不从页面本地孤立保存模板资产。
- `SubtitleVersionPanel.vue`：展示字幕轨版本、中文状态、删除确认。

- [ ] **Step 3: 重写页面根组件**

页面只做装配：

- 读取 `projectStore.currentProject`。
- 调用 `store.load(projectId)`。
- 顶部显示 `M08 字幕对齐中心`、项目名、生成按钮。
- 左侧为 `SubtitleSegmentList`。
- 中部为 `SubtitlePreviewStage`。
- 右侧为 `SubtitleTimingPanel`、`SubtitleStylePanel`、`SubtitleVersionPanel`。
- 不直接调用 `fetch` 或 Runtime client。
- 不使用 `alert()`。

- [ ] **Step 4: UI 状态文案**

必须全部中文可见：

- “字幕对齐中心”
- “字幕校对台”
- “生成字幕草稿”
- “正在读取脚本和字幕版本”
- “请先在脚本与选题中心创建内容”
- “尚未配置可用字幕对齐 Provider，已保存字幕草稿。”
- “待配置 Provider”
- “保存字幕校正”
- “删除字幕版本”

- [ ] **Step 5: 运行页面验证**

Run:

```powershell
npm --prefix apps/desktop run test -- subtitle-alignment-page.spec.ts
```

Expected: PASS。

### Task 5: 总验证、文档状态同步和验收

**Files:**

- Modify: `docs/superpowers/plans/2026-04-16-m08-subtitle-alignment-runtime-ui.md`
- Modify: `docs/superpowers/specs/2026-04-16-m08-subtitle-alignment-runtime-ui-design.md`

- [ ] **Step 1: 运行前端验证**

Run:

```powershell
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
```

Expected: PASS。若 Material Symbols 字体 warning 仍出现且不导致失败，记录为非阻断。

- [ ] **Step 2: 运行后端验证**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\contracts -q
venv\Scripts\python.exe -m pytest tests\runtime -q
venv\Scripts\python.exe -m pytest tests\contracts\test_text_encoding_contract.py -q
```

Expected: PASS。

- [ ] **Step 3: 运行提交前检查**

Run:

```powershell
git diff --check
git status --short
```

Expected:

- `git diff --check` 无错误。
- `git status --short` 中 M08 文件清晰可分；不得混入 `apps/desktop/src-tauri/Cargo.toml`、`scripts/stitch-connect.js`、`scripts/stitch-generate-dashboard.js`。

- [ ] **Step 4: 触发验收门**

使用 `$tkops-acceptance-gate`，验收输入必须包含：

- 改动摘要。
- Runtime 成功和失败信封证据。
- 前端状态覆盖：loading、empty、ready、aligning、blocked、error、disabled。
- 测试命令结果。
- 未解决风险。
- Reviewer 评分。

通过条件：

- M08 Runtime 契约和前端调用一致。
- 没有假精准时间码、假转写、假视频预览。
- UI 不使用 alert，不静默失败。
- 文档 `docs/RUNTIME-API-CALLS.md` 已更新。
- Reviewer 评分 >= 7.0。

## Test Plan

后端：

```powershell
venv\Scripts\python.exe -m pytest tests\contracts\test_subtitle_runtime_contract.py -q
venv\Scripts\python.exe -m pytest tests\runtime\test_subtitle_service.py -q
venv\Scripts\python.exe -m pytest tests\contracts -q
venv\Scripts\python.exe -m pytest tests\runtime -q
```

前端：

```powershell
npm --prefix apps/desktop run test -- runtime-client-subtitles.spec.ts subtitle-alignment-store.spec.ts subtitle-alignment-page.spec.ts
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
```

文档与编码：

```powershell
venv\Scripts\python.exe -m pytest tests\contracts\test_text_encoding_contract.py -q
git diff --check
```

## Risks And Guardrails

- 不得把 `.claude/plan/modules/M08-subtitle-alignment-center.md` 中“至少 5 条静态条目”当作当前实现验收；AGENTS.md 禁止假业务数据，本计划以真实脚本切分为准。
- 无 Provider 时仍要创建可追踪字幕草稿，但不能误导用户“自动对齐完成”；状态必须为 `blocked` 或等价阻断状态。
- 真实字幕对齐需要 AI Provider、音频/视频源、TaskBus、ASR/对齐日志和资产/时间线回写，必须作为后续独立 plan。
- 本轮 UI 可以展示字幕叠字预览，但不得显示假视频播放进度或假导出成功。
- 删除引用阻断如果本轮没有真实时间线引用关系，只保留服务边界；后续时间线集成时补 409 测试。

## Completion Status

- Design spec 已创建：`docs/superpowers/specs/2026-04-16-m08-subtitle-alignment-runtime-ui-design.md`。
- M08-A 已按本计划实现：真实脚本文本切分、`SubtitleTrack` 落库、无 Provider 阻断态、前端字幕校对台、版本保存与删除、唯一接口文档同步。
- 本批未接入真实字幕对齐 Provider、SRT/VTT 导入导出、TaskBus 长任务和时间线回写；这些能力仍需后续独立 plan。
