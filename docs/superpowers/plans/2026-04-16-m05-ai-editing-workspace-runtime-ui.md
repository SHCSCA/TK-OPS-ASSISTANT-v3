# M05 AI 剪辑工作台 Runtime 与 UI 最小闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 M05 AI 剪辑工作台从页面内静态时间线升级为真实 Runtime 驱动的项目时间线草稿、轨道/片段展示、保存与 AI 命令阻断反馈闭环。

**Architecture:** 本批为 M05-A，只做时间线最小真实数据路径，不做真实媒体渲染、真实视频预览、AI Provider 调用或复杂非线性剪辑引擎。Runtime 复用现有 `timelines` 表的 `tracks_json` 保存结构化轨道与片段，通过 `/api/workspace` 提供当前项目时间线读取、创建、更新和 AI 命令阻断响应；前端统一经 `runtime-client.ts`、Pinia store 和拆分后的 workspace 组件消费。

**Tech Stack:** Tauri 2 + Vue 3 + TypeScript + Pinia + Vitest；Python 3.13 + FastAPI + SQLAlchemy + SQLite + pytest；统一 Runtime JSON 信封 `{ "ok": true, "data": ... } / { "ok": false, "error": "中文错误" }`。

---

## Status

- 状态：Implemented，已于 2026-04-17 合并到 `main`。
- 创建时间：2026-04-16。
- 工作分支：`codex/m05-ai-editing-workspace-runtime-ui` 已通过 merge commit `6133b99` 合入 `main`。
- 隔离工作区：`C:\Users\wz\.config\superpowers\worktrees\TK-OPS-ASSISTANT-v3\m05-ai-editing-workspace-runtime-ui`，现保留为历史实施记录。
- 当前目录 `main` 上存在另一 AI 的 M16 未提交改动；本分支从 `aaf1655 feat: implement M08 subtitle alignment workflow` 创建，未继承 M16 脏改动。
- 基线验证：
  - `npm --prefix apps/desktop run test`：19 files / 49 tests passed。
  - `apps\py-runtime\venv\Scripts\python.exe -m pytest tests\contracts -q`：32 passed。
  - `apps\py-runtime\venv\Scripts\python.exe -m pytest tests\runtime -q`：79 passed。
- 环境说明：本 worktree 的 Runtime venv 位于 `apps/py-runtime/venv`，补装了 `pytest-asyncio` 用于运行现有异步测试；不改依赖文件。
- 实施结果：M05-A 已落地真实时间线草稿读取、创建、保存与 AI `blocked` 返回，页面已拆分为 page/store/modules/styles，主线不再依赖静态假轨道。
- 主线回归：本次在 `main` 上重新通过前端全量测试、前端构建、`tests/runtime/test_workspace_service.py` 所在 Runtime 回归，以及 `apps/desktop/tests/runtime-client-workspace.spec.ts`、`apps/desktop/tests/editing-workspace-store.spec.ts`、`apps/desktop/tests/ai-editing-workspace-page.spec.ts` 所覆盖的 M05 链路。
- 剩余边界：真实媒体预览、AI Provider、渲染联动仍在后续阶段，不在 M05-A 内伪造完成态。

## Current Facts

- `.claude/plan/tkops-frontend-modules.md` 将 M05 AI 剪辑工作台列为 P0 批次一。
- `.claude/plan/backend/README.md` 将 B-M05 后端列为 P0，路由前缀为 `/api/workspace`。
- `.claude/plan/modules/M05-ai-editing-workspace.md` 的 V1 静态轨道方案与当前 `AGENTS.md` 的真实数据约束冲突；本计划以真实 Runtime 数据或中性空态替代静态假轨道。
- `docs/PRD.md` 要求 `ai_editing_workspace` 成为视频、音轨、字幕和 AI 输出的统一时间线工作台，输出可渲染的完整时间线工程。
- `docs/UI-DESIGN-PRD.md` 要求 AI 剪辑工作台采用 Timeline 模板：顶部项目/工具条，中部预览 + 时间线，左侧片段/轨道导航，右侧属性面板，底部时间码与保存状态。
- `docs/ARCHITECTURE-BOOTSTRAP.md` 已将 `/api/workspace` 分配给时间线、片段编排和工作台状态。
- 当前 `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue` 约 858 行，包含页面状态、静态素材、静态轨道和样式，超过仓库 600 行强制拆分阈值。
- 当前 `Timeline` 表已存在字段：`id/project_id/name/status/duration_seconds/tracks_json/source/created_at/updated_at`，本批不新增迁移。
- 当前已有 `AIJobRecord` 与 `AIJobRepository`，但本批不触发真实 AI Provider；AI 命令返回 `blocked` 说明，不伪造成生成中或完成。

## Council Decision

Council roles:
- Product Manager
- Creative Director
- Interaction Designer
- Motion Engineer
- Frontend Lead
- Backend Runtime Lead
- Data & Contract Agent
- AI Pipeline Agent
- QA & Verification Agent
- Independent Reviewer

Facts found:
- M05 是产品核心页，但当前实现仍以页面内静态数据支撑视觉。
- 现有 `Timeline` 表足够承载 M05-A 的草稿时间线，不需要本批扩表到 `timeline_tracks` / `timeline_clips`。
- `.claude` 的“静态示例轨道”只能作为历史视觉蓝图，不能作为当前交付验收标准。

Role consensus:
- M05-A 先建立真实 Timeline 草稿闭环，避免一次性引入复杂媒体引擎、TaskBus AI 命令和多表时间线。
- UI 必须从 858 行单文件拆出组件、store、类型和样式，页面只负责项目上下文与布局编排。
- 无时间线、无轨道、无片段、AI Provider 未接入时都必须显示中文空态或阻断态，不生成假片段、假时码、假预览。

Leader decision:
- 批准 M05-A 以 `tracks_json` 结构化 JSON 做最小持久化。
- 批准 `/api/workspace/projects/{project_id}/timeline` 返回项目当前草稿，若不存在返回 `timeline: null`。
- 批准 `POST /api/workspace/projects/{project_id}/timeline` 创建空草稿，不自动填充示例轨道。
- 批准 `PATCH /api/workspace/timelines/{timeline_id}` 保存轨道与片段 JSON。
- 批准 `POST /api/workspace/projects/{project_id}/ai-commands` 返回 `blocked`，说明本阶段尚未接入 AI 剪辑 Provider 或 TaskBus。

Ownership map:
- Runtime contract: `schemas/workspace.py`、`repositories/timeline_repository.py`、`services/workspace_service.py`、`api/routes/workspace.py`。
- Frontend data: `types/runtime.ts`、`app/runtime-client.ts`、`stores/editing-workspace.ts`。
- Frontend UI: `pages/workspace/AIEditingWorkspacePage.vue`、`modules/workspace/*`、`styles/workspace.css`。
- Documentation: `docs/RUNTIME-API-CALLS.md`、本 plan、对应 design spec。
- Tests: `tests/contracts/test_workspace_runtime_contract.py`、`tests/runtime/test_workspace_service.py`、`apps/desktop/tests/runtime-client-workspace.spec.ts`、`apps/desktop/tests/editing-workspace-store.spec.ts`、`apps/desktop/tests/ai-editing-workspace-page.spec.ts`。

Acceptance gates:
- Runtime 成功/失败信封一致。
- 前端页面不直接 fetch。
- 无假素材、假轨道、假 AI 完成、假视频播放。
- 页面覆盖 loading、empty、ready、saving、blocked、error、disabled。
- 858 行页面被拆分，单文件不再继续膨胀。
- `docs/RUNTIME-API-CALLS.md` 同步登记 M05 接口。

## Scope

### In Scope

- 当前项目时间线读取。
- 空时间线草稿创建。
- 轨道与片段结构化 JSON 保存。
- 页面读取 Runtime 数据并展示多轨时间线。
- 无数据时显示中性空态，引导用户创建时间线草稿。
- AI 魔法剪按钮调用 Runtime 后显示 `blocked` 中文说明。
- 页面组件拆分、store 拆分、样式拆分。
- Runtime contract/service tests、frontend client/store/page tests。

### Out Of Scope

- 不新增 `timeline_tracks`、`timeline_clips`、`workspace_ai_commands` 数据表。
- 不接入真实 FFmpeg、视频解码、Canvas/WebGL 播放或缩略图生成。
- 不接入真实 AI 视频生成、魔法剪、降噪、风格迁移 Provider。
- 不创建假视频片段、假字幕轨、假音频波形或假预览进度。
- 不改路由树、导航分组或产品 16 页范围。
- 不触碰当前主工作区 M16 改动。

## Runtime Contract

### `GET /api/workspace/projects/{project_id}/timeline`

返回项目当前草稿时间线；没有时间线时返回 `timeline: null`。

```json
{
  "ok": true,
  "data": {
    "timeline": null,
    "message": "当前项目还没有时间线草稿。"
  }
}
```

有时间线时：

```json
{
  "ok": true,
  "data": {
    "timeline": {
      "id": "timeline-1",
      "projectId": "project-1",
      "name": "主时间线",
      "status": "draft",
      "durationSeconds": null,
      "source": "manual",
      "tracks": [
        {
          "id": "track-video-1",
          "kind": "video",
          "name": "视频轨 1",
          "orderIndex": 0,
          "locked": false,
          "muted": false,
          "clips": []
        }
      ],
      "createdAt": "2026-04-16T00:00:00Z",
      "updatedAt": "2026-04-16T00:00:00Z"
    },
    "message": "已读取时间线草稿。"
  }
}
```

### `POST /api/workspace/projects/{project_id}/timeline`

请求：

```json
{
  "name": "主时间线"
}
```

响应创建真实空草稿：

```json
{
  "ok": true,
  "data": {
    "timeline": {
      "id": "timeline-1",
      "projectId": "project-1",
      "name": "主时间线",
      "status": "draft",
      "durationSeconds": null,
      "source": "manual",
      "tracks": [],
      "createdAt": "2026-04-16T00:00:00Z",
      "updatedAt": "2026-04-16T00:00:00Z"
    },
    "message": "已创建时间线草稿。"
  }
}
```

### `PATCH /api/workspace/timelines/{timeline_id}`

请求：

```json
{
  "name": "主时间线",
  "durationSeconds": 90,
  "tracks": [
    {
      "id": "track-video-1",
      "kind": "video",
      "name": "视频轨 1",
      "orderIndex": 0,
      "locked": false,
      "muted": false,
      "clips": [
        {
          "id": "clip-1",
          "trackId": "track-video-1",
          "sourceType": "asset",
          "sourceId": "asset-1",
          "label": "开场素材",
          "startMs": 0,
          "durationMs": 3000,
          "inPointMs": 0,
          "outPointMs": 3000,
          "status": "ready"
        }
      ]
    }
  ]
}
```

### `POST /api/workspace/projects/{project_id}/ai-commands`

请求：

```json
{
  "timelineId": "timeline-1",
  "capabilityId": "magic_cut",
  "parameters": {
    "selectedClipId": "clip-1"
  }
}
```

本批阻断响应：

```json
{
  "ok": true,
  "data": {
    "status": "blocked",
    "task": null,
    "message": "AI 剪辑命令尚未接入 Provider，本阶段仅保存时间线草稿。"
  }
}
```

## File Map

Runtime:

- Create: `apps/py-runtime/src/schemas/workspace.py`
  - 定义 `TimelineDto`、`TimelineTrackDto`、`TimelineClipDto`、`TimelineCreateInput`、`TimelineUpdateInput`、`WorkspaceTimelineResultDto`、`WorkspaceAICommandInput`、`WorkspaceAICommandResultDto`。
- Create: `apps/py-runtime/src/repositories/timeline_repository.py`
  - 查询项目当前时间线、创建空草稿、更新时间线。
- Create: `apps/py-runtime/src/services/workspace_service.py`
  - 业务校验、JSON parse/serialize、错误转换和 AI 命令阻断结果。
- Create: `apps/py-runtime/src/api/routes/workspace.py`
  - 暴露 `/api/workspace` 路由。
- Modify: `apps/py-runtime/src/api/routes/__init__.py`
  - 导出 workspace router。
- Modify: `apps/py-runtime/src/app/factory.py`
  - 初始化 `TimelineRepository`、`WorkspaceService` 并注册路由。
- Test: `tests/contracts/test_workspace_runtime_contract.py`
- Test: `tests/runtime/test_workspace_service.py`

Frontend:

- Modify: `apps/desktop/src/types/runtime.ts`
  - 新增 Workspace DTO 和输入类型。
- Modify: `apps/desktop/src/app/runtime-client.ts`
  - 新增 `fetchWorkspaceTimeline()`、`createWorkspaceTimeline()`、`updateWorkspaceTimeline()`、`runWorkspaceAICommand()`。
- Create: `apps/desktop/src/stores/editing-workspace.ts`
  - 管理加载、空态、保存、阻断、错误、选中轨道/片段。
- Rewrite: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
  - 页面只负责项目上下文、store 编排和组件布局。
- Create: `apps/desktop/src/modules/workspace/WorkspaceToolbar.vue`
- Create: `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`
- Create: `apps/desktop/src/modules/workspace/WorkspacePreviewStage.vue`
- Create: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Create: `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`
- Create: `apps/desktop/src/modules/workspace/WorkspaceStateNotice.vue`
- Create: `apps/desktop/src/styles/workspace.css`
- Test: `apps/desktop/tests/runtime-client-workspace.spec.ts`
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

Docs:

- Modify: `docs/RUNTIME-API-CALLS.md`
  - 新增 M05 `/api/workspace` 接口与前端调用登记。
- Create: `docs/superpowers/specs/2026-04-16-m05-ai-editing-workspace-runtime-ui-design.md`

## Task 1: Runtime Contract Tests

**Files:**
- Create: `tests/contracts/test_workspace_runtime_contract.py`
- Create: `tests/runtime/test_workspace_service.py`

- [ ] **Step 1: Write contract tests for empty timeline and create**

Create `tests/contracts/test_workspace_runtime_contract.py` with:

```python
from __future__ import annotations

from fastapi.testclient import TestClient


def _assert_ok(payload: dict[str, object]) -> object:
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    return payload["data"]


def test_workspace_timeline_contract_returns_empty_state(runtime_client: TestClient) -> None:
    response = runtime_client.get("/api/workspace/projects/project-empty/timeline")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert set(data) == {"timeline", "message"}
    assert data["timeline"] is None
    assert "没有时间线" in data["message"]


def test_workspace_timeline_contract_creates_and_updates_draft(runtime_client: TestClient) -> None:
    create_response = runtime_client.post(
        "/api/workspace/projects/project-1/timeline",
        json={"name": "主时间线"},
    )

    assert create_response.status_code == 201
    create_data = _assert_ok(create_response.json())
    timeline = create_data["timeline"]
    assert set(timeline) == {
        "id",
        "projectId",
        "name",
        "status",
        "durationSeconds",
        "source",
        "tracks",
        "createdAt",
        "updatedAt",
    }
    assert timeline["projectId"] == "project-1"
    assert timeline["tracks"] == []

    update_response = runtime_client.patch(
        f"/api/workspace/timelines/{timeline['id']}",
        json={
            "name": "主时间线",
            "durationSeconds": 12,
            "tracks": [
                {
                    "id": "track-video-1",
                    "kind": "video",
                    "name": "视频轨 1",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [],
                }
            ],
        },
    )

    assert update_response.status_code == 200
    update_data = _assert_ok(update_response.json())
    assert update_data["timeline"]["durationSeconds"] == 12
    assert update_data["timeline"]["tracks"][0]["kind"] == "video"
```

- [ ] **Step 2: Write contract test for blocked AI command**

Append:

```python
def test_workspace_ai_command_returns_blocked_contract(runtime_client: TestClient) -> None:
    response = runtime_client.post(
        "/api/workspace/projects/project-1/ai-commands",
        json={
            "timelineId": "timeline-1",
            "capabilityId": "magic_cut",
            "parameters": {"selectedClipId": "clip-1"},
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert set(data) == {"status", "task", "message"}
    assert data["status"] == "blocked"
    assert data["task"] is None
    assert "尚未接入" in data["message"]
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```powershell
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\contracts\test_workspace_runtime_contract.py -q
```

Expected: fails because `/api/workspace` route is not registered.

## Task 2: Runtime Schema, Repository, Service

**Files:**
- Create: `apps/py-runtime/src/schemas/workspace.py`
- Create: `apps/py-runtime/src/repositories/timeline_repository.py`
- Create: `apps/py-runtime/src/services/workspace_service.py`
- Test: `tests/runtime/test_workspace_service.py`

- [ ] **Step 1: Add workspace schemas**

Create `apps/py-runtime/src/schemas/workspace.py` with Pydantic DTOs using camelCase aliases in field names directly, matching existing Runtime DTO style.

Key requirements:
- `TimelineTrackDto.clips` defaults to `[]`.
- `TimelineUpdateInput.tracks` is required when saving.
- `WorkspaceAICommandResultDto.status` supports `blocked`.

- [ ] **Step 2: Add repository**

Create `TimelineRepository` with:

- `get_current_for_project(project_id: str) -> Timeline | None`
- `create_empty(project_id: str, name: str) -> Timeline`
- `update_timeline(timeline_id: str, *, name: str | None, duration_seconds: float | None, tracks_json: str) -> Timeline | None`

Repository must:
- use `common.time.utc_now_iso()`;
- order current lookup by `updated_at DESC`;
- set `status="draft"` and `source="manual"` for created timelines;
- store empty tracks as `"[]"`.

- [ ] **Step 3: Add service**

Create `WorkspaceService` with:

- `get_project_timeline(project_id: str) -> WorkspaceTimelineResultDto`
- `create_project_timeline(project_id: str, payload: TimelineCreateInput) -> WorkspaceTimelineResultDto`
- `update_timeline(timeline_id: str, payload: TimelineUpdateInput) -> WorkspaceTimelineResultDto`
- `run_ai_command(project_id: str, payload: WorkspaceAICommandInput) -> WorkspaceAICommandResultDto`

Service must:
- catch repository exceptions with `log.exception(...)`;
- convert failures to Chinese `HTTPException`;
- parse invalid `tracks_json` as `[]` and log an exception;
- reject unknown track kinds with `400` and message `时间线轨道类型不支持。`;
- return blocked AI command message without creating fake tasks.

- [ ] **Step 4: Add service tests**

Create tests covering:

- empty project returns `timeline is None`;
- create stores empty draft;
- update persists one video track;
- invalid track kind raises `400`;
- AI command returns `blocked`.

- [ ] **Step 5: Run service tests**

Run:

```powershell
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py -q
```

Expected: PASS after implementation.

## Task 3: Runtime Routes And Factory Wiring

**Files:**
- Create: `apps/py-runtime/src/api/routes/workspace.py`
- Modify: `apps/py-runtime/src/api/routes/__init__.py`
- Modify: `apps/py-runtime/src/app/factory.py`
- Modify: `docs/RUNTIME-API-CALLS.md`

- [ ] **Step 1: Add thin route handlers**

Create routes:

- `GET /api/workspace/projects/{project_id}/timeline`
- `POST /api/workspace/projects/{project_id}/timeline`
- `PATCH /api/workspace/timelines/{timeline_id}`
- `POST /api/workspace/projects/{project_id}/ai-commands`

Routes must only call `WorkspaceService` and wrap `ok_response(...)`.

- [ ] **Step 2: Register route and service**

In `factory.py`, instantiate:

```python
timeline_repository = TimelineRepository(session_factory=session_factory)
workspace_service = WorkspaceService(timeline_repository)
```

Expose on `app.state` and include `workspace_router`.

- [ ] **Step 3: Update Runtime API docs**

Add a `M05 AI 剪辑工作台` section to `docs/RUNTIME-API-CALLS.md` with:

- DTO tables.
- Endpoint table.
- Request/response examples.
- Frontend methods.
- Error behavior.

- [ ] **Step 4: Run contract tests**

Run:

```powershell
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\contracts\test_workspace_runtime_contract.py -q
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\contracts -q
```

Expected: PASS.

## Task 4: Frontend Runtime Types And Client

**Files:**
- Modify: `apps/desktop/src/types/runtime.ts`
- Modify: `apps/desktop/src/app/runtime-client.ts`
- Test: `apps/desktop/tests/runtime-client-workspace.spec.ts`

- [ ] **Step 1: Add failing Runtime client test**

Create `apps/desktop/tests/runtime-client-workspace.spec.ts` that verifies:

- `fetchWorkspaceTimeline("project-1")` calls `GET /api/workspace/projects/project-1/timeline`.
- `createWorkspaceTimeline("project-1", { name: "主时间线" })` calls `POST`.
- `updateWorkspaceTimeline("timeline-1", input)` calls `PATCH`.
- `runWorkspaceAICommand("project-1", input)` calls `POST /ai-commands`.

- [ ] **Step 2: Add TypeScript DTOs**

Add:

- `WorkspaceTimelineClipDto`
- `WorkspaceTimelineTrackDto`
- `WorkspaceTimelineDto`
- `WorkspaceTimelineResultDto`
- `WorkspaceTimelineCreateInput`
- `WorkspaceTimelineUpdateInput`
- `WorkspaceAICommandInput`
- `WorkspaceAICommandResultDto`

Use frontend field names exactly matching Runtime camelCase.

- [ ] **Step 3: Add Runtime client functions**

Add:

```typescript
export async function fetchWorkspaceTimeline(projectId: string): Promise<WorkspaceTimelineResultDto>
export async function createWorkspaceTimeline(projectId: string, input: WorkspaceTimelineCreateInput): Promise<WorkspaceTimelineResultDto>
export async function updateWorkspaceTimeline(timelineId: string, input: WorkspaceTimelineUpdateInput): Promise<WorkspaceTimelineResultDto>
export async function runWorkspaceAICommand(projectId: string, input: WorkspaceAICommandInput): Promise<WorkspaceAICommandResultDto>
```

- [ ] **Step 4: Run client test**

Run:

```powershell
npm --prefix apps/desktop run test -- runtime-client-workspace.spec.ts
```

Expected: PASS.

## Task 5: Editing Workspace Store

**Files:**
- Create: `apps/desktop/src/stores/editing-workspace.ts`
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`

- [ ] **Step 1: Add failing store test**

Test requirements:

- loading a project with `timeline: null` sets `status="empty"`;
- creating a timeline sets `status="ready"` and stores timeline;
- saving tracks keeps timeline and sets `status="ready"`;
- AI command blocked stores `blockedMessage`;
- Runtime error sets `status="error"` and keeps existing draft.

- [ ] **Step 2: Implement store**

State:

- `timeline`
- `status: "idle" | "loading" | "empty" | "ready" | "saving" | "blocked" | "error"`
- `error`
- `blockedMessage`
- `selectedTrackId`
- `selectedClipId`

Actions:

- `load(projectId)`
- `createDraft(projectId)`
- `saveTimeline()`
- `runMagicCut(projectId)`
- `selectTrack(trackId)`
- `selectClip(clipId)`

The store must not generate sample tracks. Creating a track is not in M05-A unless the user edits and saves a real track object.

- [ ] **Step 3: Run store test**

Run:

```powershell
npm --prefix apps/desktop run test -- editing-workspace-store.spec.ts
```

Expected: PASS.

## Task 6: UI Split And Page Runtime Integration

**Files:**
- Rewrite: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Create: `apps/desktop/src/modules/workspace/WorkspaceToolbar.vue`
- Create: `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`
- Create: `apps/desktop/src/modules/workspace/WorkspacePreviewStage.vue`
- Create: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Create: `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`
- Create: `apps/desktop/src/modules/workspace/WorkspaceStateNotice.vue`
- Create: `apps/desktop/src/styles/workspace.css`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: Add failing page test**

Test requirements:

- route `/workspace/editing` fetches current project timeline through Runtime client mocks;
- empty state says `当前项目还没有时间线草稿`;
- clicking `创建时间线草稿` calls `POST /api/workspace/projects/{id}/timeline`;
- ready state renders track names returned by Runtime;
- clicking `AI 魔法剪` shows blocked Chinese message;
- page does not contain old static clip names from the previous implementation.

- [ ] **Step 2: Split page components**

Component responsibilities:

- `WorkspaceToolbar.vue`: tools, save, AI action, disabled/busy states.
- `WorkspaceAssetRail.vue`: neutral asset rail and empty hints; no fake assets.
- `WorkspacePreviewStage.vue`: neutral preview stage, selected clip label if any; no fake playback.
- `WorkspaceTimeline.vue`: render real tracks and clips from DTO.
- `WorkspaceInspector.vue`: selected track/clip details and blocked/error feedback.
- `WorkspaceStateNotice.vue`: loading, empty, error, blocked notices with retry/create actions.

- [ ] **Step 3: Rewrite page shell**

`AIEditingWorkspacePage.vue` must:

- wrap `ProjectContextGuard`;
- use current project context store;
- call `editingWorkspaceStore.load(currentProjectId)` on mount and project change;
- pass DTOs to components;
- keep page-level code focused on orchestration.

- [ ] **Step 4: Add workspace styles**

Move workspace CSS to `apps/desktop/src/styles/workspace.css`.

CSS requirements:

- desktop wide layout: left rail / preview + timeline / inspector;
- compact layout: rail and inspector collapse above or below timeline;
- use existing CSS variables;
- no decorative orbs, no one-note palette, no nested cards;
- `prefers-reduced-motion` disables scanning/repeated animations.

- [ ] **Step 5: Run page tests**

Run:

```powershell
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts
npm --prefix apps/desktop run test
```

Expected: PASS.

## Task 7: Verification And Acceptance Prep

**Files:**
- Modify: `docs/superpowers/plans/2026-04-16-m05-ai-editing-workspace-runtime-ui.md`

- [ ] **Step 1: Run targeted verification**

Run:

```powershell
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\contracts\test_workspace_runtime_contract.py -q
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py -q
npm --prefix apps/desktop run test -- runtime-client-workspace.spec.ts editing-workspace-store.spec.ts ai-editing-workspace-page.spec.ts
```

Expected: PASS.

- [ ] **Step 2: Run regression verification**

Run:

```powershell
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\contracts -q
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\runtime -q
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
git diff --check
```

Expected: PASS.

- [ ] **Step 3: Manual UI verification**

Start app if needed:

```powershell
npm run app:dev
```

Check:

- Wide desktop: rail, preview, timeline, inspector visible and stable.
- Compact window: timeline remains readable, inspector does not squeeze the main area.
- Empty state: no fake tracks or fake clips.
- Ready state: tracks come from Runtime.
- Blocked state: AI 魔法剪 message is Chinese and recoverable.
- Light/Dark: tracks, chips, disabled and error states remain readable.

- [ ] **Step 4: Acceptance gate input**

Prepare `tkops-acceptance-gate` input with:

- changed file summary;
- Runtime contract evidence;
- frontend state coverage;
- tests/build output;
- no fake data statement;
- residual risks;
- reviewer score target >= 7.0.

## Risks And Guardrails

- Existing `Timeline` stores `tracks_json` rather than normalized tracks/clips. This is acceptable for M05-A but must not block a future normalized migration.
- AI command blocking must not create fake running tasks. If a future implementation needs TaskBus, it must be a new plan.
- Current page is over 600 lines; implementation must split it instead of adding new code inside the large file.
- Rendering and true media preview belong to M14/render and media pipeline plans; M05-A only displays timeline structure.
- The current main working directory has M16 dirty changes. Do not copy or merge those files into this branch unless the user explicitly asks.

## Test Plan

Runtime:

```powershell
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\contracts\test_workspace_runtime_contract.py -q
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py -q
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\contracts -q
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\runtime -q
```

Frontend:

```powershell
npm --prefix apps/desktop run test -- runtime-client-workspace.spec.ts editing-workspace-store.spec.ts ai-editing-workspace-page.spec.ts
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
```

Docs and encoding:

```powershell
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\contracts\test_text_encoding_contract.py -q
git diff --check
```
