# M05 AI 剪辑工作台总装台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 M05 AI 剪辑工作台能把当前项目的脚本、分镜、配音轨和字幕轨汇入同一条真实时间线，并以 9:16 成片预览、多轨时间线、来源检查和预检反馈呈现。

**Architecture:** 新增独立 `WorkspaceAssemblyService` 负责读取脚本、分镜、配音、字幕和当前时间线，生成稳定 ID 的托管轨道并保留用户手动轨道；现有 `WorkspaceService` 继续负责时间线 CRUD、片段移动、裁剪、替换、预览和预检。前端只通过 Runtime adapter 和 Pinia store 触发汇入，不在页面层拼接业务规则。

**Tech Stack:** Python FastAPI + SQLAlchemy Repository + Pydantic DTO；Vue 3 + TypeScript + Pinia + Vitest；Pytest runtime/contract tests；Vite build。

---

## Scope

本轮实现 M05 “总装台”底座，不做重型剪辑器。

交付内容：

- Runtime 新增 `POST /api/workspace/projects/{project_id}/timeline/assemble`。
- Runtime 根据当前项目最新脚本、分镜、最新 ready 配音轨、最新字幕轨生成或更新时间线托管轨道。
- M05 页面新增“汇入创作结果”动作，显示真实来源状态、装配结果、预检问题和保存状态。
- M05 布局参考剪映的基础工作区结构：左上素材来源，中上播放器，右上基础属性，底部横向时间线。
- M05 预览区改成 9:16 手机预览窗口，显示当前片段文本、字幕或来源摘要。
- 多轨时间线区清晰区分视频 / 音频 / 字幕轨，不再只显示单一片段来源。
- 更新 Runtime API 文档和测试。

不做内容：

- 不接入 AI 视频生成 Provider。
- 不做真实视频播放和逐帧渲染。
- 不做复杂特效、关键帧、转场编辑。
- 不做剪映里的贴纸、特效、滤镜、转场、动画、调节、模板商城和素材商店。
- 不做多层高级轨道混剪，只保留视频 / 音频 / 字幕三类基础轨道和基础片段选择。
- 不覆盖用户手动创建的非托管轨道。
- 不把配音、字幕、分镜页面的业务逻辑复制进 M05 UI 层。

## Basic Jianying-Like Layout

布局只借鉴剪映的基础信息结构，不复制完整功能集：

```text
┌──────────────────────────┬──────────────────────────┬──────────────────────────┐
│ 素材来源                  │ 播放器                    │ 基础属性                  │
│ 脚本 / 分镜 / 配音 / 字幕 │ 9:16 手机预览             │ 画面 / 音频 / 字幕基础字段 │
├──────────────────────────┴──────────────────────────┴──────────────────────────┤
│ 基础工具条：选择、切分、删除、撤销/重做预留、吸附、缩放                         │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 多轨时间线：视频轨、配音轨、字幕轨                                               │
└──────────────────────────────────────────────────────────────────────────────────┘
```

保留：

- 素材来源列表：只展示当前项目真实来源和已汇入片段。
- 播放器：9:16 手机画幅，显示当前片段文案 / 字幕 / 来源摘要。
- 基础属性：只展示选中片段的基础字段，不做高级调色或动画参数。
- 底部时间线：视频、音频、字幕三类轨道，支持选中、预检和后续基础切分扩展位。

移除：

- 顶部素材商城式分类和模板资源。
- 贴纸、特效、滤镜、转场、动画、调节等高级剪辑面板。
- 多层复杂合成、关键帧、遮罩、曲线、调色和专业音频混音。

## File Map

Runtime:

- Create: `apps/py-runtime/src/services/workspace_assembly.py`
  - 读取脚本 / 分镜 / 配音 / 字幕仓储。
  - 生成托管轨道：`managed-video-storyboard`、`managed-audio-voice`、`managed-subtitle-track`。
  - 保留非托管轨道。
  - 返回 `WorkspaceTimelineResultDto` 和装配状态。
- Modify: `apps/py-runtime/src/schemas/workspace.py`
  - 增加 `TimelineClipMetadataDto`、`WorkspaceAssemblySourceDto`、`WorkspaceAssemblyStateDto`、`WorkspaceTimelineAssembleInput`。
  - 扩展 `TimelineClipDto.metadata` 和 `WorkspaceTimelineResultDto.assemblyState`。
- Modify: `apps/py-runtime/src/api/routes/workspace.py`
  - 新增 `/projects/{project_id}/timeline/assemble` 路由。
- Modify: `apps/py-runtime/src/app/factory.py`
  - 注入 `WorkspaceAssemblyService`，挂载 `app.state.workspace_assembly_service`。
- Test: `tests/runtime/test_workspace_assembly_service.py`
  - 覆盖从脚本 / 分镜 / 配音 / 字幕汇入时间线、保留手动轨道、缺来源降级。
- Test: `tests/contracts/test_workspace_runtime_contract.py`
  - 覆盖新接口 JSON 信封和字段形状。

Desktop:

- Modify: `apps/desktop/src/types/runtime.ts`
  - 对齐 workspace DTO：`metadata`、`version`、`assetReferenceStatus`、`activeTask`、`saveState`、`assemblyState`、`assemble` 输入。
- Modify: `apps/desktop/src/app/runtime-client.ts`
  - 新增 `assembleWorkspaceTimeline(projectId, input)`。
- Modify: `apps/desktop/src/stores/editing-workspace.ts`
  - 新增 `assembleTimeline()`、`assemblyState`、`saveState`、`precheck` 状态。
  - 保持异常通过 `RuntimeRequestError` 统一转换。
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
  - 增加“汇入创作结果”和“渲染前预检”按钮。
  - 页面读取 `assemblyState`、`saveState`、`precheck` 并传给模块。
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`
  - 调整工作台布局为剪映式基础三栏上区 + 底部横向时间线；紧凑窗口单列。
- Modify: `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`
  - 按来源显示脚本、分镜、配音、字幕和时间线片段数量。
- Modify: `apps/desktop/src/modules/workspace/WorkspacePreviewStage.vue`
  - 9:16 手机窗口、当前片段字幕 / 文案叠加、无真实媒体时显示中性状态。
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
  - 展示托管轨道和非托管轨道，轨道头显示来源、锁定、静音和片段数。
- Modify: `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`
  - 展示选中片段 metadata、来源、时间码和预检问题。
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`
  - 覆盖 store 汇入、预检和错误状态。
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
  - 覆盖按钮交互、装配结果显示、9:16 预览和任务反馈。
- Test: `apps/desktop/tests/workspace-layout-contract.spec.ts`
  - 覆盖预览窗口 9:16、紧凑布局、时间线不横向撑破页面。

Docs:

- Modify: `docs/RUNTIME-API-CALLS.md`
  - 追加新接口地址、方法、请求、返回、错误码和示例。
- Modify after implementation: `CHANGELOG.md`
  - 记录 M05 总装台能力。

## Runtime Assembly Contract

Endpoint:

```http
POST /api/workspace/projects/{project_id}/timeline/assemble
Content-Type: application/json
```

Request:

```json
{
  "mode": "merge_managed",
  "timelineName": "主时间线"
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "timeline": {
      "id": "timeline-1",
      "projectId": "project-1",
      "name": "主时间线",
      "status": "draft",
      "durationSeconds": 15,
      "source": "manual",
      "tracks": []
    },
    "activeTask": null,
    "saveState": {
      "saved": true,
      "updatedAt": "2026-05-13T10:00:00Z",
      "source": "assembly",
      "message": "已汇入脚本、分镜、配音和字幕。"
    },
    "assemblyState": {
      "status": "ready",
      "sources": [
        {
          "kind": "script",
          "status": "ready",
          "label": "脚本文案",
          "revision": 3,
          "segmentCount": 5,
          "message": "已读取最新脚本版本。"
        }
      ],
      "issues": []
    },
    "message": "已汇入创作结果。"
  }
}
```

Error handling:

- 404: 项目不存在或时间线不存在。
- 400: `mode` 不受支持。
- 500: 仓储读取、JSON 解析或保存失败。服务层必须 `log.exception(...)` 并返回中文 `HTTPException.detail`。

## Implementation Tasks

### Task 1: Runtime DTO contract

**Files:**

- Modify: `apps/py-runtime/src/schemas/workspace.py`
- Modify: `apps/desktop/src/types/runtime.ts`
- Test: `tests/contracts/test_workspace_runtime_contract.py`
- Test: `apps/desktop/tests/runtime-client-b-s4.spec.ts`

- [ ] **Step 1: Add failing contract assertions for assembly fields**

Add this test to `tests/contracts/test_workspace_runtime_contract.py`:

```python
def test_workspace_assembly_contract_returns_sources_and_timeline(runtime_client: TestClient) -> None:
    response = runtime_client.post(
        "/api/workspace/projects/project-workspace/timeline/assemble",
        json={"mode": "merge_managed", "timelineName": "主时间线"},
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert set(data) == {"timeline", "activeTask", "saveState", "assemblyState", "message"}
    assert data["timeline"] is not None
    assert data["saveState"]["source"] == "assembly"
    assert set(data["assemblyState"]) == {"status", "sources", "issues"}
    assert isinstance(data["assemblyState"]["sources"], list)
```

Run: `pytest tests/contracts/test_workspace_runtime_contract.py::test_workspace_assembly_contract_returns_sources_and_timeline -q`

Expected: FAIL because the route does not exist.

- [ ] **Step 2: Extend Python workspace schemas**

Add these models to `apps/py-runtime/src/schemas/workspace.py`:

```python
class TimelineClipMetadataDto(BaseModel):
    sourceKind: str | None = None
    sourceRevision: int | None = None
    segmentIndex: int | None = Field(default=None, ge=0)
    segmentId: str | None = None
    text: str | None = None
    visualPrompt: str | None = None


class WorkspaceAssemblySourceDto(BaseModel):
    kind: str
    status: str
    label: str
    revision: int | None = None
    trackId: str | None = None
    segmentCount: int = Field(default=0, ge=0)
    message: str


class WorkspaceAssemblyStateDto(BaseModel):
    status: str
    sources: list[WorkspaceAssemblySourceDto] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class WorkspaceTimelineAssembleInput(BaseModel):
    mode: str = "merge_managed"
    timelineName: str = "主时间线"
```

Extend `TimelineClipDto`:

```python
metadata: TimelineClipMetadataDto = Field(default_factory=TimelineClipMetadataDto)
```

Extend `WorkspaceTimelineResultDto`:

```python
assemblyState: WorkspaceAssemblyStateDto | None = None
```

- [ ] **Step 3: Extend desktop runtime types**

Update `apps/desktop/src/types/runtime.ts` with matching types:

```ts
export type WorkspaceTimelineClipMetadataDto = {
  sourceKind: string | null;
  sourceRevision: number | null;
  segmentIndex: number | null;
  segmentId: string | null;
  text: string | null;
  visualPrompt: string | null;
};

export type WorkspaceAssemblySourceDto = {
  kind: string;
  status: string;
  label: string;
  revision: number | null;
  trackId: string | null;
  segmentCount: number;
  message: string;
};

export type WorkspaceAssemblyStateDto = {
  status: string;
  sources: WorkspaceAssemblySourceDto[];
  issues: string[];
};

export type WorkspaceTimelineAssembleInput = {
  mode?: "merge_managed";
  timelineName?: string;
};
```

Extend `WorkspaceTimelineClipDto` and `WorkspaceTimelineResultDto`:

```ts
metadata?: WorkspaceTimelineClipMetadataDto;
```

```ts
activeTask?: WorkspaceActiveTaskDto | null;
saveState?: WorkspaceSaveStateDto | null;
assemblyState?: WorkspaceAssemblyStateDto | null;
```

- [ ] **Step 4: Run contract tests**

Run: `pytest tests/contracts/test_workspace_runtime_contract.py -q`

Expected: new assembly test still fails because service and route are not implemented; existing tests keep passing.

### Task 2: Runtime assembly service

**Files:**

- Create: `apps/py-runtime/src/services/workspace_assembly.py`
- Modify: `apps/py-runtime/src/app/factory.py`
- Modify: `apps/py-runtime/src/api/routes/workspace.py`
- Test: `tests/runtime/test_workspace_assembly_service.py`
- Test: `tests/contracts/test_workspace_runtime_contract.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/runtime/test_workspace_assembly_service.py` with these cases:

```python
def test_assembly_creates_managed_tracks_from_latest_sources(tmp_path: Path) -> None:
    service = _make_assembly_service(tmp_path)
    _seed_script(service.context, segment_count=2)
    _seed_storyboard(service.context, scene_count=2)
    _seed_voice_track(service.context, status="ready")
    _seed_subtitle_track(service.context, status="aligned")

    result = service.assemble_project_timeline(
        "project-workspace",
        WorkspaceTimelineAssembleInput(mode="merge_managed", timelineName="主时间线"),
    )

    assert result.timeline is not None
    assert [track.id for track in result.timeline.tracks[:3]] == [
        "managed-video-storyboard",
        "managed-audio-voice",
        "managed-subtitle-track",
    ]
    assert result.timeline.tracks[0].clips[0].metadata.sourceKind == "storyboard"
    assert result.timeline.tracks[1].clips[0].sourceType == "voice_track"
    assert result.timeline.tracks[2].clips[0].sourceType == "subtitle_track"
    assert result.saveState is not None
    assert result.saveState.source == "assembly"
    assert result.assemblyState is not None
    assert result.assemblyState.status == "ready"
```

Add a second test:

```python
def test_assembly_preserves_manual_tracks(tmp_path: Path) -> None:
    service = _make_assembly_service(tmp_path)
    timeline_id = _seed_existing_timeline_with_manual_track(service.context)
    _seed_script(service.context, segment_count=1)

    result = service.assemble_project_timeline(
        "project-workspace",
        WorkspaceTimelineAssembleInput(mode="merge_managed", timelineName="主时间线"),
    )

    assert result.timeline is not None
    track_ids = [track.id for track in result.timeline.tracks]
    assert "manual-video-track" in track_ids
    assert result.timeline.id == timeline_id
```

Run: `pytest tests/runtime/test_workspace_assembly_service.py -q`

Expected: FAIL because `WorkspaceAssemblyService` does not exist.

- [ ] **Step 2: Implement focused assembly helpers**

Create `apps/py-runtime/src/services/workspace_assembly.py` with a small public service and private helper functions:

```python
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from common.time import utc_now_iso
from repositories.script_repository import ScriptRepository, StoredScriptVersion
from repositories.storyboard_repository import StoryboardRepository, StoredStoryboardVersion
from repositories.subtitle_repository import SubtitleRepository
from repositories.timeline_repository import TimelineRepository
from repositories.voice_repository import VoiceRepository
from schemas.workspace import (
    TimelineClipDto,
    TimelineClipMetadataDto,
    TimelineTrackDto,
    WorkspaceAssemblySourceDto,
    WorkspaceAssemblyStateDto,
    WorkspaceSaveStateDto,
    WorkspaceTimelineAssembleInput,
    WorkspaceTimelineResultDto,
)
from services.workspace_service import WorkspaceService

log = logging.getLogger(__name__)

MANAGED_TRACK_IDS = {
    "managed-video-storyboard",
    "managed-audio-voice",
    "managed-subtitle-track",
}

@dataclass(frozen=True, slots=True)
class AssemblySegment:
    index: int
    segment_id: str
    start_ms: int
    end_ms: int
    text: str
    visual_prompt: str


class WorkspaceAssemblyService:
    def __init__(
        self,
        *,
        timeline_repository: TimelineRepository,
        script_repository: ScriptRepository,
        storyboard_repository: StoryboardRepository,
        voice_repository: VoiceRepository,
        subtitle_repository: SubtitleRepository,
        workspace_service: WorkspaceService,
    ) -> None:
        self._timeline_repository = timeline_repository
        self._script_repository = script_repository
        self._storyboard_repository = storyboard_repository
        self._voice_repository = voice_repository
        self._subtitle_repository = subtitle_repository
        self._workspace_service = workspace_service
```

Keep helper responsibilities split:

- `_load_latest_script()`
- `_load_latest_storyboard()`
- `_build_script_segments()`
- `_build_storyboard_track()`
- `_build_voice_track()`
- `_build_subtitle_track()`
- `_merge_managed_tracks()`
- `_build_assembly_state()`

Each helper catches only expected JSON parsing failures locally; repository and save failures are caught at `assemble_project_timeline()` and logged with `log.exception("汇入创作结果失败")`.

- [ ] **Step 3: Implement service public method**

Add this method:

```python
def assemble_project_timeline(
    self,
    project_id: str,
    payload: WorkspaceTimelineAssembleInput,
) -> WorkspaceTimelineResultDto:
    if payload.mode != "merge_managed":
        raise HTTPException(status_code=400, detail="时间线汇入模式不受支持。")

    try:
        timeline = self._timeline_repository.get_current_for_project(project_id)
        if timeline is None:
            timeline = self._timeline_repository.create_empty(
                project_id,
                payload.timelineName.strip() or "主时间线",
            )

        existing_tracks = self._workspace_service._parse_tracks(timeline.tracks_json)  # type: ignore[attr-defined]
        assembly = self._assemble_tracks(project_id)
        merged_tracks = self._merge_managed_tracks(existing_tracks, assembly["tracks"])
        duration_seconds = _resolve_duration_seconds(merged_tracks)
        updated = self._timeline_repository.update_timeline(
            timeline.id,
            name=payload.timelineName.strip() or timeline.name,
            duration_seconds=duration_seconds,
            tracks_json=json.dumps(merged_tracks, ensure_ascii=False),
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("汇入创作结果失败")
        raise HTTPException(status_code=500, detail="汇入创作结果失败。") from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="时间线不存在。")

    result = self._workspace_service._build_timeline_result(  # type: ignore[attr-defined]
        updated,
        message="已汇入创作结果。",
        save_source="assembly",
        save_message="已汇入脚本、分镜、配音和字幕。",
    )
    result.assemblyState = assembly["state"]
    return result
```

If private method reuse is considered too coupled during implementation, extract `_parse_tracks` and `_build_timeline_result` from `WorkspaceService` into a shared `services/workspace_timeline_helpers.py` before wiring the service. Keep the helper file under 250 lines and cover it through the same tests.

- [ ] **Step 4: Wire route and factory**

In `apps/py-runtime/src/app/factory.py`, build the assembly service after `workspace_service`:

```python
workspace_assembly_service = WorkspaceAssemblyService(
    timeline_repository=timeline_repository,
    script_repository=script_repository,
    storyboard_repository=storyboard_repository,
    voice_repository=voice_repository,
    subtitle_repository=subtitle_repository,
    workspace_service=workspace_service,
)
app.state.workspace_assembly_service = workspace_assembly_service
```

In `apps/py-runtime/src/api/routes/workspace.py`, add:

```python
from schemas.workspace import WorkspaceTimelineAssembleInput
from services.workspace_assembly import WorkspaceAssemblyService


def _assembly_svc(request: Request) -> WorkspaceAssemblyService:
    return request.app.state.workspace_assembly_service  # type: ignore[no-any-return]


@router.post("/projects/{project_id}/timeline/assemble")
def assemble_project_timeline(
    project_id: str,
    payload: WorkspaceTimelineAssembleInput,
    request: Request,
) -> dict[str, object]:
    result = _assembly_svc(request).assemble_project_timeline(project_id, payload)
    return ok_response(result.model_dump(mode="json"))
```

- [ ] **Step 5: Run runtime tests**

Run:

```bash
pytest tests/runtime/test_workspace_assembly_service.py tests/runtime/test_workspace_service.py tests/contracts/test_workspace_runtime_contract.py -q
```

Expected: PASS.

### Task 3: Runtime client and store

**Files:**

- Modify: `apps/desktop/src/app/runtime-client.ts`
- Modify: `apps/desktop/src/stores/editing-workspace.ts`
- Test: `apps/desktop/tests/runtime-client-b-s4.spec.ts`
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`

- [ ] **Step 1: Add failing runtime-client expectation**

In `apps/desktop/tests/runtime-client-b-s4.spec.ts`, call the new client function:

```ts
await runtimeClient.assembleWorkspaceTimeline("project-1", {
  mode: "merge_managed",
  timelineName: "主时间线"
});
```

Add expected request:

```ts
{
  path: "/api/workspace/projects/project-1/timeline/assemble",
  method: "POST",
  body: { mode: "merge_managed", timelineName: "主时间线" }
}
```

Run: `npm --prefix apps/desktop run test -- runtime-client-b-s4.spec.ts`

Expected: FAIL because `assembleWorkspaceTimeline` is missing.

- [ ] **Step 2: Implement runtime client**

Add to `apps/desktop/src/app/runtime-client.ts`:

```ts
export async function assembleWorkspaceTimeline(
  projectId: string,
  input: WorkspaceTimelineAssembleInput = {}
): Promise<WorkspaceTimelineResultDto> {
  return requestRuntime<WorkspaceTimelineResultDto>(
    `/api/workspace/projects/${projectId}/timeline/assemble`,
    {
      body: JSON.stringify({
        mode: input.mode ?? "merge_managed",
        timelineName: input.timelineName ?? "主时间线"
      }),
      method: "POST"
    }
  );
}
```

- [ ] **Step 3: Add failing store test**

Create `apps/desktop/tests/editing-workspace-store.spec.ts`:

```ts
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useEditingWorkspaceStore } from "@/stores/editing-workspace";

vi.mock("@/app/runtime-client", async () => {
  const actual = await vi.importActual<typeof import("@/app/runtime-client")>("@/app/runtime-client");
  return {
    ...actual,
    assembleWorkspaceTimeline: vi.fn()
  };
});

describe("editing workspace store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("汇入创作结果后同步 timeline、assemblyState 和 saveState", async () => {
    const runtimeClient = await import("@/app/runtime-client");
    vi.mocked(runtimeClient.assembleWorkspaceTimeline).mockResolvedValue({
      timeline: workspaceTimeline(),
      message: "已汇入创作结果。",
      saveState: {
        saved: true,
        updatedAt: "2026-05-13T10:00:00Z",
        source: "assembly",
        message: "已汇入脚本、分镜、配音和字幕。"
      },
      assemblyState: {
        status: "ready",
        issues: [],
        sources: [
          {
            kind: "script",
            status: "ready",
            label: "脚本文案",
            revision: 3,
            trackId: null,
            segmentCount: 2,
            message: "已读取最新脚本版本。"
          }
        ]
      }
    });

    const store = useEditingWorkspaceStore();
    await store.assembleTimeline("project-1");

    expect(store.status).toBe("ready");
    expect(store.timeline?.tracks[0]?.id).toBe("managed-video-storyboard");
    expect(store.assemblyState?.sources[0]?.kind).toBe("script");
    expect(store.saveState?.source).toBe("assembly");
  });
});
```

Use a local `workspaceTimeline()` fixture with one `managed-video-storyboard` track.

- [ ] **Step 4: Implement store action**

In `apps/desktop/src/stores/editing-workspace.ts`:

```ts
import { assembleWorkspaceTimeline, precheckTimeline } from "@/app/runtime-client";
import type { TimelinePrecheckDto, WorkspaceAssemblyStateDto, WorkspaceSaveStateDto } from "@/types/runtime";
```

Add state:

```ts
assemblyState: WorkspaceAssemblyStateDto | null;
precheck: TimelinePrecheckDto | null;
saveState: WorkspaceSaveStateDto | null;
```

Add action:

```ts
async assembleTimeline(projectId?: string): Promise<WorkspaceTimelineDto | null> {
  const pid = projectId || this.projectId;
  if (!pid) {
    this.applyInputError("请先选择项目。");
    return null;
  }

  this.status = "saving";
  this.error = null;
  this.projectId = pid;

  try {
    const result = await assembleWorkspaceTimeline(pid, {
      mode: "merge_managed",
      timelineName: this.timeline?.name ?? "主时间线"
    });
    this.applyTimelineResult(result);
    return result.timeline;
  } catch (error) {
    this.applyRuntimeError(error);
    return null;
  }
}
```

Update `applyTimelineResult`:

```ts
this.assemblyState = result.assemblyState ?? this.assemblyState;
this.saveState = result.saveState ?? null;
```

Add `runPrecheck()` that calls `precheckTimeline(this.timeline.id)` and stores the result; if no timeline, call `applyInputError("当前项目还没有时间线草稿。")`.

- [ ] **Step 5: Run frontend store/client tests**

Run:

```bash
npm --prefix apps/desktop run test -- runtime-client-b-s4.spec.ts editing-workspace-store.spec.ts
```

Expected: PASS.

### Task 4: M05 page interaction and modules

**Files:**

- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspacePreviewStage.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
- Test: `apps/desktop/tests/workspace-layout-contract.spec.ts`

- [ ] **Step 1: Add failing page test for assembly button and 9:16 preview**

Extend `apps/desktop/tests/ai-editing-workspace-page.spec.ts`:

```ts
if (path === "/api/workspace/projects/project-1/timeline/assemble" && method === "POST") {
  timelineState = assembledWorkspaceTimeline();
  return okJsonResponse({
    timeline: timelineState,
    message: "已汇入创作结果。",
    saveState: {
      saved: true,
      updatedAt: now(),
      source: "assembly",
      message: "已汇入脚本、分镜、配音和字幕。"
    },
    assemblyState: {
      status: "ready",
      issues: [],
      sources: [
        { kind: "script", status: "ready", label: "脚本文案", revision: 3, trackId: null, segmentCount: 2, message: "已读取最新脚本版本。" },
        { kind: "voice", status: "ready", label: "配音轨", revision: 1, trackId: "voice-track-1", segmentCount: 2, message: "已读取最新配音轨。" }
      ]
    }
  });
}
```

Assertions:

```ts
await wrapper.get('[data-testid="workspace-assemble-button"]').trigger("click");
await flushPromises();

expect(wrapper.text()).toContain("已汇入脚本、分镜、配音和字幕");
expect(wrapper.text()).toContain("分镜视频轨");
expect(wrapper.text()).toContain("配音轨");
expect(wrapper.text()).toContain("字幕轨");
expect(wrapper.text()).not.toContain("贴纸");
expect(wrapper.text()).not.toContain("特效");
expect(wrapper.text()).not.toContain("滤镜");
expect(wrapper.text()).not.toContain("转场");
expect(wrapper.get('[data-testid="workspace-preview-phone"]').attributes("data-ratio")).toBe("9:16");
```

Run: `npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts`

Expected: FAIL because button and preview test id are missing.

- [ ] **Step 2: Add page actions**

In `AIEditingWorkspacePage.vue`, add buttons:

```vue
<Button
  variant="primary"
  data-testid="workspace-assemble-button"
  :running="status === 'saving'"
  :disabled="!currentProjectId || status === 'loading' || isGenerating"
  @click="handleAssemble"
>
  <template #leading><span class="material-symbols-outlined">account_tree</span></template>
  汇入创作结果
</Button>
<Button
  variant="secondary"
  data-testid="workspace-precheck-button"
  :disabled="!timeline || status === 'loading'"
  @click="handlePrecheck"
>
  <template #leading><span class="material-symbols-outlined">rule_settings</span></template>
  渲染前预检
</Button>
```

Add handlers:

```ts
async function handleAssemble(): Promise<void> {
  if (currentProjectId.value) {
    await workspaceStore.assembleTimeline(currentProjectId.value);
  }
}

async function handlePrecheck(): Promise<void> {
  await workspaceStore.runPrecheck();
}
```

Pass `assemblyState`, `precheck`, and `saveState` to modules.

- [ ] **Step 3: Apply basic Jianying-like layout shell**

In `AIEditingWorkspacePage.vue`, keep the work surface in this order:

```vue
<div v-if="timeline" class="workspace-editor-shell scroll-area">
  <section class="workspace-editor-top">
    <WorkspaceAssetRail class="workspace-editor-panel workspace-editor-panel--sources" />
    <WorkspacePreviewStage class="workspace-editor-panel workspace-editor-panel--player" />
    <WorkspaceInspector class="workspace-editor-panel workspace-editor-panel--properties" />
  </section>
  <section class="workspace-editor-tools" aria-label="基础剪辑工具">
    <button type="button" disabled><span class="material-symbols-outlined">undo</span></button>
    <button type="button" disabled><span class="material-symbols-outlined">redo</span></button>
    <button type="button" disabled><span class="material-symbols-outlined">content_cut</span></button>
    <button type="button" disabled><span class="material-symbols-outlined">delete</span></button>
    <button type="button" disabled><span class="material-symbols-outlined">zoom_in</span></button>
  </section>
  <WorkspaceTimeline class="workspace-editor-timeline" />
</div>
```

The disabled tool buttons are visible placeholders for basic editing only. They must not trigger fake edits until Runtime clip operations are wired.

CSS target:

```css
.workspace-editor-shell {
  display: grid;
  gap: var(--space-3);
  min-height: 0;
}

.workspace-editor-top {
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) minmax(360px, 1.4fr) minmax(280px, 0.9fr);
  gap: var(--space-3);
  min-width: 0;
}

.workspace-editor-tools {
  align-items: center;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  display: flex;
  gap: 8px;
  padding: 8px 10px;
}

.workspace-editor-timeline {
  min-height: 300px;
}
```

At compact width, `.workspace-editor-top` becomes one column and the timeline remains below the panels.

- [ ] **Step 4: Update asset rail**

Change `WorkspaceAssetRail.vue` props:

```ts
assemblyState: WorkspaceAssemblyStateDto | null;
selectedClip: WorkspaceTimelineClipDto | null;
timeline: WorkspaceTimelineDto | null;
```

Render source cards from `assemblyState.sources`; fallback to timeline clip summary when `assemblyState` is null. Use Chinese labels:

```ts
function sourceKindLabel(kind: string): string {
  if (kind === "script") return "脚本文案";
  if (kind === "storyboard") return "分镜";
  if (kind === "voice") return "配音";
  if (kind === "subtitle") return "字幕";
  return kind;
}
```

- [ ] **Step 5: Update 9:16 preview**

In `WorkspacePreviewStage.vue`, wrap the canvas:

```vue
<div
  class="workspace-preview-stage__phone"
  data-testid="workspace-preview-phone"
  data-ratio="9:16"
>
  <div class="workspace-preview-stage__screen">
    <strong>{{ headline }}</strong>
    <p>{{ previewText }}</p>
  </div>
</div>
```

CSS:

```css
.workspace-preview-stage__phone {
  aspect-ratio: 9 / 16;
  width: min(360px, 100%);
  max-height: 640px;
  margin: 0 auto;
  background: #050706;
  border: 1px solid var(--border-default);
  border-radius: 24px;
  display: grid;
  padding: 16px;
}

.workspace-preview-stage__screen {
  align-content: end;
  display: grid;
  gap: 10px;
  min-width: 0;
  overflow: hidden;
}
```

Use selected clip metadata text first:

```ts
const previewText = computed(() => {
  return props.selectedClip?.metadata?.text || props.selectedClip?.prompt || description.value;
});
```

- [ ] **Step 6: Update timeline and inspector**

Timeline:

- Track header shows `视频轨 / 音频轨 / 字幕轨` and managed/manual source.
- Clip card shows metadata segment ID and duration.
- Do not add drag editing in this phase.

Inspector:

- Shows selected clip source type, source ID, segment ID, text, visual prompt, status, time range.
- Shows `precheck.issues` when present.
- Shows `saveState.message` when present.

- [ ] **Step 7: Add layout contract**

Create `apps/desktop/tests/workspace-layout-contract.spec.ts`:

```ts
import { describe, expect, it } from "vitest";
import { readSource } from "./test-utils";

describe("M05 workspace layout contract", () => {
  it("uses a 9:16 preview frame and responsive workspace columns", () => {
    const preview = readSource("../src/modules/workspace/WorkspacePreviewStage.vue");
    const css = readSource("../src/pages/workspace/AIEditingWorkspacePage.css");

    expect(preview).toContain('data-ratio="9:16"');
    expect(preview).toContain("aspect-ratio: 9 / 16");
    expect(css).toContain(".workspace-editor-top");
    expect(css).toContain(".workspace-editor-tools");
    expect(css).toContain(".workspace-editor-timeline");
    expect(css).toContain("container-name: editing-workspace");
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)/);
  });
});
```

If `readSource` is not exported in existing test utils, implement a local helper in the spec:

```ts
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function readSource(relativePath: string): string {
  return readFileSync(resolve(__dirname, relativePath), "utf8");
}
```

- [ ] **Step 8: Run page tests**

Run:

```bash
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts editing-workspace-store.spec.ts workspace-layout-contract.spec.ts
```

Expected: PASS.

### Task 5: Docs and verification

**Files:**

- Modify: `docs/RUNTIME-API-CALLS.md`
- Modify: `CHANGELOG.md`
- No version bump until implementation is complete and user asks to release.

- [ ] **Step 1: Update Runtime API docs**

Append a section for:

````markdown
### POST `/api/workspace/projects/{project_id}/timeline/assemble`

用途：把当前项目最新脚本、分镜、配音轨和字幕轨汇入 M05 时间线。

请求：

```json
{
  "mode": "merge_managed",
  "timelineName": "主时间线"
}
```

成功返回：

```json
{
  "ok": true,
  "data": {
    "timeline": {},
    "saveState": {},
    "assemblyState": {
      "status": "ready",
      "sources": [],
      "issues": []
    },
    "message": "已汇入创作结果。"
  }
}
```

错误码：

| 状态码 | 说明 | UI 处理 |
| --- | --- | --- |
| 400 | 汇入模式不支持 | 显示中文错误并保留原时间线 |
| 404 | 项目或时间线不存在 | 引导用户回到创作总览选择项目 |
| 500 | 汇入失败 | 显示错误、保留重试按钮、日志可追踪 |
````

- [ ] **Step 2: Update changelog**

Add under Unreleased:

```markdown
- M05 AI 剪辑工作台新增“汇入创作结果”，可把脚本、分镜、配音轨和字幕轨汇入同一条时间线，并提供 9:16 预览、来源状态和渲染前预检入口。
```

- [ ] **Step 3: Run focused verification**

Run:

```bash
pytest tests/runtime/test_workspace_assembly_service.py tests/runtime/test_workspace_service.py tests/contracts/test_workspace_runtime_contract.py -q
npm --prefix apps/desktop run test -- runtime-client-b-s4.spec.ts editing-workspace-store.spec.ts ai-editing-workspace-page.spec.ts workspace-layout-contract.spec.ts
```

Expected: all tests PASS.

- [ ] **Step 4: Run main-chain regression**

Run:

```bash
npm --prefix apps/desktop run build
pytest tests/contracts/test_runtime_contract_inventory.py -q
```

Expected: build succeeds and route inventory remains consistent. If `test_runtime_contract_inventory.py` expects a documented route count, update only the documented workspace route entry and rerun.

- [ ] **Step 5: Browser verification**

With Runtime and Vite running:

1. Open `http://127.0.0.1:1420/workspace/editing`.
2. Click `汇入创作结果`.
3. Verify the page shows source cards for脚本 / 分镜 / 配音 / 字幕.
4. Verify the preview phone frame has 9:16 proportions and does not overlap at 1366px and compact width.
5. Click a video/audio/subtitle clip and verify inspector fields change.
6. Click `渲染前预检` and verify issues or ready state are visible.

Expected: no console errors, route remains `/workspace/editing`, no silent click failure.

## Self-Review

- Spec coverage: This plan covers Runtime assembly, frontend interaction, layout, docs and verification. It intentionally excludes AI video generation and real media playback.
- Placeholder scan: No unresolved placeholder markers are used.
- Type consistency: `WorkspaceTimelineAssembleInput`, `WorkspaceAssemblyStateDto`, `WorkspaceAssemblySourceDto`, `WorkspaceSaveStateDto`, and `TimelineClipMetadataDto` are named consistently across backend, frontend and tests.
- Scope check: The work is one coherent subsystem: M05 assembly into timeline. It does not modify M07/M08 generation logic except consuming their existing tracks.

## Approval Gate

本计划需要用户确认后，按仓库规则继续生成 `docs/superpowers/specs/2026-05-13-m05-editing-workspace-assembly-design.md`。设计文档通过后才能进入代码实现。
