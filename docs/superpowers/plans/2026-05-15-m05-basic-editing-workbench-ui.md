# M05 基础剪辑工作台 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已确认的第三版 M05 UI 定稿落地到正式 AI 剪辑工作台页面，接入资产中心素材列表，并补齐缩略图、波形、字幕块、工具激活态、播放头和属性面板结构。

**Architecture:** 本轮只做 UI 落地和真实数据展示，不实现拖拽、分割、删除、替换片段等可变更时间线的剪辑动作。页面继续通过 `editing-workspace` store 和 Runtime adapter 获取时间线与资产数据，组件只消费 view model，不在 UI 层拼接业务规则。

**Tech Stack:** Vue 3 + TypeScript + Pinia + Vitest；现有 Runtime client；Scoped CSS + 设计令牌；Playwright/浏览器手动检查。

---

## Scope

实现内容：

- M05 左侧素材池增加 `分镜 / 配音 / 字幕 / 资产` 四个来源视图。
- `资产` 视图读取当前项目资产中心素材，显示视频、图片、音频、需处理、缺失等状态。
- 时间线改成深色基础剪辑台视觉：视频缩略图条、音频波形、字幕文本块、磁吸贴合、播放头、轨道高度层级。
- 顶部基础工具条替换为独立组件，包含选择、移动、分割、删除、磁吸、缩放视觉状态。
- 播放器改成第三版视觉：9:16 手机窗口、来源状态、字幕预览、播放控制区。
- 基础属性面板重组为片段信息、时间参数、素材来源、预检提醒、AI 建议折叠区。
- 保留现有加载、空态、错误、任务状态和汇入/预检/保存流程。

不实现内容：

- 不做真实拖拽。
- 不做真实分割、删除、替换片段。
- 不做真实媒体解码播放。
- 不在 UI 中直接读取本地文件路径。
- 不新增素材中心管理能力。
- 不让 AI 建议直接修改时间线。

## File Map

Create:

- `apps/desktop/src/modules/workspace/workspaceAssetViewModel.ts`
  - 将 `AssetDto`、`WorkspaceTimelineDto`、`WorkspaceAssemblyStateDto` 转成素材池卡片模型。
- `apps/desktop/src/modules/workspace/workspaceTimelineViewModel.ts`
  - 计算磁吸式片段布局、轨道高度层级、播放头位置和轨道视觉类型。
- `apps/desktop/src/modules/workspace/WorkspaceTimelineToolbar.vue`
  - 渲染选择、移动、分割、删除、磁吸、缩放工具状态。
- `apps/desktop/tests/workspace-asset-view-model.spec.ts`
  - 覆盖资产卡片状态、当前项目过滤、入轨状态。
- `apps/desktop/tests/workspace-timeline-view-model.spec.ts`
  - 覆盖磁吸布局、播放头位置、轨道高度层级。

Modify:

- `apps/desktop/src/stores/editing-workspace.ts`
  - 增加资产状态、资产错误和 `loadAssets()`。
- `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
  - 向素材池传入资产、资产状态、资产错误；使用新工具条；向属性面板传入 AI 命令结果。
- `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`
  - 调整页面网格和时间线高度。
- `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`
  - 实现四 Tab 素材池和资产卡片 UI。
- `apps/desktop/src/modules/workspace/WorkspacePreviewStage.vue`
  - 实现 9:16 手机预览、来源状态、播放控制区。
- `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
  - 实现深色多轨时间线、缩略图、波形、字幕块和播放头。
- `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`
  - 实现分区属性面板和 AI 建议默认折叠。
- `apps/desktop/tests/editing-workspace-store.spec.ts`
  - 覆盖资产加载成功和失败。
- `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
  - 覆盖资产 Tab、素材卡片、时间线视觉文本和工具条。
- `apps/desktop/tests/workspace-layout-contract.spec.ts`
  - 覆盖第三版 UI 结构和响应式边界。

## Task 1: Asset View Model

**Files:**

- Create: `apps/desktop/src/modules/workspace/workspaceAssetViewModel.ts`
- Test: `apps/desktop/tests/workspace-asset-view-model.spec.ts`

- [ ] **Step 1: Write failing tests for asset card mapping**

Create `apps/desktop/tests/workspace-asset-view-model.spec.ts`:

```ts
import { describe, expect, it } from "vitest";

import { buildWorkspaceAssetCards, sourceTypeLabel, type WorkspaceAssetCard } from "@/modules/workspace/workspaceAssetViewModel";
import type { AssetDto, WorkspaceTimelineDto } from "@/types/runtime";

describe("workspaceAssetViewModel", () => {
  it("maps current project assets into compact asset cards", () => {
    const cards = buildWorkspaceAssetCards({
      assets: [
        asset({ id: "asset-video", name: "warm-room.mp4", type: "video", projectId: "project-1", durationMs: 5000 }),
        asset({ id: "asset-audio", name: "room.wav", type: "audio", projectId: "project-1", durationMs: 18000 }),
        asset({ id: "asset-other", name: "other.mp4", type: "video", projectId: "project-2", durationMs: 1000 })
      ],
      projectId: "project-1",
      timeline: timelineWithAsset("asset-video")
    });

    expect(cards.map((card) => card.id)).toEqual(["asset-video", "asset-audio"]);
    expect(cards[0]).toMatchObject<Partial<WorkspaceAssetCard>>({
      id: "asset-video",
      type: "video",
      status: "已入轨",
      primaryAction: "替换片段"
    });
    expect(cards[1]).toMatchObject<Partial<WorkspaceAssetCard>>({
      id: "asset-audio",
      type: "audio",
      status: "可用",
      primaryAction: "加入音轨"
    });
  });

  it("marks unavailable assets with a recovery action", () => {
    const cards = buildWorkspaceAssetCards({
      assets: [
        asset({
          id: "asset-missing",
          name: "missing.mov",
          type: "video",
          projectId: "project-1",
          availability: { status: "missing", errorCode: "missing_file", errorMessage: "文件不存在", nextAction: "重新定位" }
        })
      ],
      projectId: "project-1",
      timeline: null
    });

    expect(cards[0].status).toBe("路径缺失");
    expect(cards[0].tone).toBe("danger");
    expect(cards[0].primaryAction).toBe("重新定位");
  });

  it("keeps source type labels in Chinese", () => {
    expect(sourceTypeLabel("storyboard")).toBe("分镜规划");
    expect(sourceTypeLabel("asset")).toBe("资产中心");
    expect(sourceTypeLabel("voice_track")).toBe("配音中心");
    expect(sourceTypeLabel("subtitle_track")).toBe("字幕对齐");
  });
});

function asset(input: Partial<AssetDto>): AssetDto {
  return {
    id: input.id ?? "asset-1",
    name: input.name ?? "素材.mp4",
    type: input.type ?? "video",
    source: "local",
    filePath: "G:/assets/demo.mp4",
    fileSizeBytes: 1024,
    durationMs: input.durationMs ?? null,
    thumbnailPath: null,
    tags: null,
    projectId: input.projectId ?? "project-1",
    metadataJson: null,
    sourceInfo: {
      source: "local",
      projectId: input.projectId ?? "project-1",
      groupId: null,
      filePath: "G:/assets/demo.mp4",
      metadataSummary: {}
    },
    availability: input.availability ?? {
      status: "available",
      errorCode: null,
      errorMessage: null,
      nextAction: null
    },
    referenceSummary: {
      total: 0,
      referenceTypes: [],
      blockingDelete: false
    },
    thumbnailStatus: {
      status: "missing",
      path: null,
      generatedAt: null
    },
    createdAt: "2026-05-15T10:00:00Z",
    updatedAt: "2026-05-15T10:00:00Z",
    ...input
  };
}

function timelineWithAsset(assetId: string): WorkspaceTimelineDto {
  return {
    id: "timeline-1",
    projectId: "project-1",
    name: "主时间线",
    status: "draft",
    durationSeconds: 15,
    source: "manual",
    tracks: [
      {
        id: "track-video",
        kind: "video",
        name: "视频主轨",
        orderIndex: 0,
        locked: false,
        muted: false,
        clips: [
          {
            id: "clip-1",
            trackId: "track-video",
            sourceType: "asset",
            sourceId: assetId,
            label: "资产视频",
            startMs: 0,
            durationMs: 5000,
            inPointMs: 0,
            outPointMs: null,
            status: "ready",
            metadata: {
              sourceKind: "asset",
              sourceRevision: null,
              segmentIndex: 0,
              segmentId: "S01",
              text: "测试字幕",
              visualPrompt: "测试画面"
            }
          }
        ]
      }
    ],
    createdAt: "2026-05-15T10:00:00Z",
    updatedAt: "2026-05-15T10:00:00Z"
  };
}
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
npm --prefix apps/desktop run test -- workspace-asset-view-model.spec.ts
```

Expected: FAIL because `workspaceAssetViewModel.ts` does not exist.

- [ ] **Step 3: Implement asset view model**

Create `apps/desktop/src/modules/workspace/workspaceAssetViewModel.ts`:

```ts
import type { AssetDto, WorkspaceTimelineDto } from "@/types/runtime";

export type WorkspaceAssetTone = "neutral" | "success" | "warning" | "danger";

export type WorkspaceAssetCard = {
  durationLabel: string;
  id: string;
  isOnTimeline: boolean;
  name: string;
  primaryAction: string;
  projectId: string | null;
  status: string;
  summary: string;
  thumbnailPath: string | null;
  tone: WorkspaceAssetTone;
  type: string;
};

export type BuildWorkspaceAssetCardsInput = {
  assets: AssetDto[];
  projectId: string;
  timeline: WorkspaceTimelineDto | null;
};

export function buildWorkspaceAssetCards(input: BuildWorkspaceAssetCardsInput): WorkspaceAssetCard[] {
  const timelineAssetIds = new Set(
    input.timeline?.tracks
      .flatMap((track) => track.clips)
      .filter((clip) => clip.sourceType === "asset" && clip.sourceId)
      .map((clip) => clip.sourceId as string) ?? []
  );

  return input.assets
    .filter((asset) => asset.projectId === input.projectId || asset.sourceInfo.projectId === input.projectId)
    .map((asset) => {
      const isOnTimeline = timelineAssetIds.has(asset.id);
      const availability = resolveAvailability(asset);
      return {
        durationLabel: formatDuration(asset.durationMs),
        id: asset.id,
        isOnTimeline,
        name: asset.name,
        primaryAction: resolvePrimaryAction(asset, isOnTimeline, availability.status),
        projectId: asset.projectId,
        status: isOnTimeline ? "已入轨" : availability.label,
        summary: buildAssetSummary(asset),
        thumbnailPath: asset.thumbnailPath ?? asset.thumbnailStatus.path,
        tone: isOnTimeline ? "success" : availability.tone,
        type: asset.type
      };
    });
}

export function sourceTypeLabel(sourceType: string): string {
  if (sourceType === "storyboard") return "分镜规划";
  if (sourceType === "asset") return "资产中心";
  if (sourceType === "imported_video") return "视频拆解";
  if (sourceType === "voice_track") return "配音中心";
  if (sourceType === "subtitle_track") return "字幕对齐";
  if (sourceType === "manual") return "手动片段";
  return sourceType;
}

function resolveAvailability(asset: AssetDto): { label: string; status: string; tone: WorkspaceAssetTone } {
  if (asset.availability.status === "missing") {
    return { label: "路径缺失", status: "missing", tone: "danger" };
  }
  if (asset.availability.status === "needs_transcode") {
    return { label: "需转码", status: "needs_transcode", tone: "warning" };
  }
  if (asset.availability.status !== "available") {
    return { label: asset.availability.errorMessage ?? "需检查", status: asset.availability.status, tone: "warning" };
  }
  return { label: "可用", status: "available", tone: "neutral" };
}

function resolvePrimaryAction(asset: AssetDto, isOnTimeline: boolean, availabilityStatus: string): string {
  if (availabilityStatus === "missing") return asset.availability.nextAction ?? "重新定位";
  if (availabilityStatus === "needs_transcode") return "检查";
  if (isOnTimeline) return "替换片段";
  if (asset.type === "audio") return "加入音轨";
  return "加入轨道";
}

function buildAssetSummary(asset: AssetDto): string {
  const duration = formatDuration(asset.durationMs);
  const size = asset.fileSizeBytes ? `${Math.ceil(asset.fileSizeBytes / 1024)}KB` : "大小未知";
  return `${asset.type} · ${duration} · ${size}`;
}

function formatDuration(durationMs: number | null): string {
  if (!durationMs) return "无时长";
  const totalSeconds = Math.max(0, Math.floor(durationMs / 1000));
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
npm --prefix apps/desktop run test -- workspace-asset-view-model.spec.ts
```

Expected: PASS.

## Task 2: Timeline View Model

**Files:**

- Create: `apps/desktop/src/modules/workspace/workspaceTimelineViewModel.ts`
- Test: `apps/desktop/tests/workspace-timeline-view-model.spec.ts`

- [ ] **Step 1: Write failing tests for magnetic timeline layout**

Create `apps/desktop/tests/workspace-timeline-view-model.spec.ts`:

```ts
import { describe, expect, it } from "vitest";

import {
  buildTimelineRows,
  computePlayheadPercent,
  trackVisualClass
} from "@/modules/workspace/workspaceTimelineViewModel";
import type { WorkspaceTimelineTrackDto } from "@/types/runtime";

describe("workspaceTimelineViewModel", () => {
  it("renders continuous clips without visual gaps when clips touch in time", () => {
    const rows = buildTimelineRows([track("video", [
      clip("clip-1", 0, 5000),
      clip("clip-2", 5000, 5000),
      clip("clip-3", 10000, 5000)
    ])], 15000);

    expect(rows[0].clips.map((clip) => clip.leftPercent)).toEqual([0, 33.333, 66.667]);
    expect(rows[0].clips.map((clip) => clip.widthPercent)).toEqual([33.333, 33.333, 33.333]);
    expect(rows[0].clips.map((clip) => clip.joinClass)).toEqual(["start", "middle", "end"]);
  });

  it("uses clear visual classes for video, audio and subtitle tracks", () => {
    expect(trackVisualClass("video", "视频主轨")).toBe("video");
    expect(trackVisualClass("audio", "BGM 轨")).toBe("bgm");
    expect(trackVisualClass("audio", "配音轨")).toBe("voice");
    expect(trackVisualClass("subtitle", "字幕轨")).toBe("subtitle");
  });

  it("keeps the playhead inside timeline bounds", () => {
    expect(computePlayheadPercent(5000, 15000)).toBe(33.333);
    expect(computePlayheadPercent(-100, 15000)).toBe(0);
    expect(computePlayheadPercent(20000, 15000)).toBe(100);
  });
});

function track(kind: WorkspaceTimelineTrackDto["kind"], clips: ReturnType<typeof clip>[]): WorkspaceTimelineTrackDto {
  return {
    id: `track-${kind}`,
    kind,
    name: kind === "video" ? "视频主轨" : kind === "audio" ? "配音轨" : "字幕轨",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips: clips.map((item) => ({ ...item, trackId: `track-${kind}` }))
  };
}

function clip(id: string, startMs: number, durationMs: number) {
  return {
    id,
    trackId: "track-video",
    sourceType: "storyboard",
    sourceId: id,
    label: id,
    startMs,
    durationMs,
    inPointMs: 0,
    outPointMs: null,
    status: "ready",
    metadata: {
      sourceKind: "storyboard",
      sourceRevision: 1,
      segmentIndex: 0,
      segmentId: id,
      text: `${id} 字幕`,
      visualPrompt: `${id} 画面`
    }
  };
}
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
npm --prefix apps/desktop run test -- workspace-timeline-view-model.spec.ts
```

Expected: FAIL because `workspaceTimelineViewModel.ts` does not exist.

- [ ] **Step 3: Implement timeline view model**

Create `apps/desktop/src/modules/workspace/workspaceTimelineViewModel.ts`:

```ts
import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineTrackDto,
  WorkspaceTimelineTrackKind
} from "@/types/runtime";

export type TimelineClipJoinClass = "single" | "start" | "middle" | "end";
export type TimelineTrackVisualClass = "video" | "voice" | "bgm" | "subtitle";

export type TimelineClipView = {
  clip: WorkspaceTimelineClipDto;
  joinClass: TimelineClipJoinClass;
  leftPercent: number;
  widthPercent: number;
};

export type TimelineRowView = {
  clips: TimelineClipView[];
  heightClass: "tall" | "medium" | "compact";
  track: WorkspaceTimelineTrackDto;
  visualClass: TimelineTrackVisualClass;
};

export function buildTimelineRows(
  tracks: WorkspaceTimelineTrackDto[],
  durationMs: number
): TimelineRowView[] {
  const safeDuration = Math.max(1000, durationMs);
  return tracks
    .slice()
    .sort((a, b) => a.orderIndex - b.orderIndex)
    .map((track) => ({
      clips: track.clips
        .slice()
        .sort((a, b) => a.startMs - b.startMs)
        .map((clip, index, clips) => ({
          clip,
          joinClass: resolveJoinClass(index, clips.length),
          leftPercent: roundPercent((clip.startMs / safeDuration) * 100),
          widthPercent: roundPercent((clip.durationMs / safeDuration) * 100)
        })),
      heightClass: track.kind === "video" ? "tall" : track.kind === "subtitle" ? "compact" : "medium",
      track,
      visualClass: trackVisualClass(track.kind, track.name)
    }));
}

export function computePlayheadPercent(positionMs: number, durationMs: number): number {
  const safeDuration = Math.max(1000, durationMs);
  return roundPercent((Math.min(Math.max(positionMs, 0), safeDuration) / safeDuration) * 100);
}

export function trackVisualClass(kind: WorkspaceTimelineTrackKind, name: string): TimelineTrackVisualClass {
  if (kind === "subtitle") return "subtitle";
  if (kind === "audio" && /bgm|音乐|环境/i.test(name)) return "bgm";
  if (kind === "audio") return "voice";
  return "video";
}

function resolveJoinClass(index: number, count: number): TimelineClipJoinClass {
  if (count === 1) return "single";
  if (index === 0) return "start";
  if (index === count - 1) return "end";
  return "middle";
}

function roundPercent(value: number): number {
  return Number(value.toFixed(3));
}
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
npm --prefix apps/desktop run test -- workspace-timeline-view-model.spec.ts
```

Expected: PASS.

## Task 3: Store Asset Loading

**Files:**

- Modify: `apps/desktop/src/stores/editing-workspace.ts`
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`

- [ ] **Step 1: Add failing store tests for asset loading**

Append these tests inside `describe("M05 AI 剪辑工作台 store", ...)` in `apps/desktop/tests/editing-workspace-store.spec.ts`:

```ts
  it("加载工作台时同步读取当前项目资产", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ assets: [asset("asset-1", "project-1")] }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");

    expect(store.assets.map((asset) => asset.id)).toEqual(["asset-1"]);
    expect(store.assetStatus).toBe("ready");
    expect(store.assetError).toBeNull();
  });

  it("资产读取失败时保留时间线并显示资产错误", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ failAssets: true }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");

    expect(store.timeline?.id).toBe("timeline-1");
    expect(store.status).toBe("ready");
    expect(store.assetStatus).toBe("error");
    expect(store.assetError?.message).toBe("资产中心同步失败，请稍后重试。");
  });
```

Extend `createWorkspaceFetch` options and resolver in the same file:

```ts
function createWorkspaceFetch(options: {
  assets?: ReturnType<typeof asset>[];
  failAssets?: boolean;
  failSave?: boolean;
  timeline?: ReturnType<typeof timeline> | null;
} = {}) {
  return createRouteAwareFetch((path, method, init) => {
    if (path === "/api/assets" && method === "GET") {
      if (options.failAssets) {
        return errorJsonResponse(500, "资产中心同步失败，请稍后重试。");
      }
      return okJsonResponse(options.assets ?? []);
    }
```

Add helper:

```ts
function asset(id: string, projectId: string) {
  return {
    id,
    name: "warm-room.mp4",
    type: "video",
    source: "local",
    filePath: "G:/assets/warm-room.mp4",
    fileSizeBytes: 1024,
    durationMs: 5000,
    thumbnailPath: null,
    tags: null,
    projectId,
    metadataJson: null,
    sourceInfo: {
      source: "local",
      projectId,
      groupId: null,
      filePath: "G:/assets/warm-room.mp4",
      metadataSummary: {}
    },
    availability: {
      status: "available",
      errorCode: null,
      errorMessage: null,
      nextAction: null
    },
    referenceSummary: {
      total: 0,
      referenceTypes: [],
      blockingDelete: false
    },
    thumbnailStatus: {
      status: "missing",
      path: null,
      generatedAt: null
    },
    createdAt: now(),
    updatedAt: now()
  };
}
```

- [ ] **Step 2: Run failing store tests**

Run:

```bash
npm --prefix apps/desktop run test -- editing-workspace-store.spec.ts
```

Expected: FAIL because the store has no `assets`, `assetStatus`, or `assetError`.

- [ ] **Step 3: Implement asset state in store**

Modify `apps/desktop/src/stores/editing-workspace.ts`:

```ts
import {
  RuntimeRequestError,
  assembleWorkspaceTimeline,
  createWorkspaceTimeline,
  fetchAssets,
  fetchWorkspaceTimeline,
  precheckTimeline,
  runWorkspaceAICommand,
  updateWorkspaceTimeline
} from "@/app/runtime-client";
import type {
  AssetDto,
  RuntimeRequestErrorShape,
  TimelinePrecheckDto,
  WorkspaceAICommandResultDto,
  WorkspaceAssemblyStateDto,
  WorkspaceSaveStateDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineResultDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";

export type WorkspaceAssetStatus = "idle" | "loading" | "ready" | "error";

type EditingWorkspaceState = {
  assetError: RuntimeRequestErrorShape | null;
  assetStatus: WorkspaceAssetStatus;
  assets: AssetDto[];
  assemblyState: WorkspaceAssemblyStateDto | null;
  blockedMessage: string | null;
  error: RuntimeRequestErrorShape | null;
  lastCommandResult: WorkspaceAICommandResultDto | null;
  precheck: TimelinePrecheckDto | null;
  projectId: string;
  saveState: WorkspaceSaveStateDto | null;
  selectedClipId: string | null;
  selectedTrackId: string | null;
  status: EditingWorkspaceStatus;
  timeline: WorkspaceTimelineDto | null;
};
```

Initialize:

```ts
assetError: null,
assetStatus: "idle",
assets: [],
```

Update `load`:

```ts
    async load(projectId: string): Promise<void> {
      this.status = "loading";
      this.error = null;
      this.projectId = projectId;
      this.lastCommandResult = null;
      this.precheck = null;

      try {
        this.applyTimelineResult(await fetchWorkspaceTimeline(projectId));
      } catch (error) {
        this.applyRuntimeError(error);
      }

      await this.loadAssets(projectId);
    },
```

Add action:

```ts
    async loadAssets(projectId?: string): Promise<AssetDto[]> {
      const pid = projectId || this.projectId;
      if (!pid) {
        this.assets = [];
        this.assetStatus = "idle";
        this.assetError = null;
        return [];
      }

      this.assetStatus = "loading";
      this.assetError = null;

      try {
        const assets = await fetchAssets();
        this.assets = assets.filter((asset) => asset.projectId === pid || asset.sourceInfo.projectId === pid);
        this.assetStatus = "ready";
        return this.assets;
      } catch (error) {
        const runtimeError =
          error instanceof RuntimeRequestError
            ? error
            : new RuntimeRequestError("资产中心同步失败，请稍后重试。");
        this.assetStatus = "error";
        this.assetError = {
          details: runtimeError.details,
          message: runtimeError.message,
          requestId: runtimeError.requestId,
          status: runtimeError.status
        };
        return [];
      }
    },
```

- [ ] **Step 4: Run store tests**

Run:

```bash
npm --prefix apps/desktop run test -- editing-workspace-store.spec.ts
```

Expected: PASS.

## Task 4: Workspace Timeline Toolbar

**Files:**

- Create: `apps/desktop/src/modules/workspace/WorkspaceTimelineToolbar.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: Add failing page assertions for toolbar**

In `apps/desktop/tests/ai-editing-workspace-page.spec.ts`, after the page creates or assembles a timeline, add:

```ts
    expect(wrapper.get('[data-testid="workspace-timeline-toolbar"]').text()).toContain("选择");
    expect(wrapper.get('[data-testid="workspace-timeline-toolbar"]').text()).toContain("移动");
    expect(wrapper.get('[data-testid="workspace-timeline-toolbar"]').text()).toContain("分割");
    expect(wrapper.get('[data-testid="workspace-timeline-toolbar"]').text()).toContain("删除");
    expect(wrapper.get('[data-testid="workspace-timeline-toolbar"]').text()).toContain("磁吸");
    expect(wrapper.get('[data-testid="workspace-tool-select"]').classes()).toContain("workspace-timeline-toolbar__button--active");
```

- [ ] **Step 2: Run failing page test**

Run:

```bash
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts
```

Expected: FAIL because `workspace-timeline-toolbar` does not exist.

- [ ] **Step 3: Create toolbar component**

Create `apps/desktop/src/modules/workspace/WorkspaceTimelineToolbar.vue`:

```vue
<template>
  <section class="workspace-timeline-toolbar" data-testid="workspace-timeline-toolbar" aria-label="时间线基础工具">
    <div class="workspace-timeline-toolbar__tools">
      <button
        v-for="tool in tools"
        :key="tool.id"
        :data-testid="`workspace-tool-${tool.id}`"
        :class="{ 'workspace-timeline-toolbar__button--active': tool.active }"
        class="workspace-timeline-toolbar__button"
        type="button"
        :title="tool.description"
        disabled
      >
        <span class="workspace-tool-icon" :data-icon="tool.id" aria-hidden="true" />
        <span>{{ tool.label }}</span>
      </button>
    </div>
    <div class="workspace-timeline-toolbar__status">
      <strong>基础工具</strong>
      <span>{{ statusLabel }}</span>
    </div>
    <div class="workspace-timeline-toolbar__zoom" aria-label="时间线缩放">
      <span>缩放</span>
      <div class="workspace-timeline-toolbar__range" />
    </div>
  </section>
</template>

<script setup lang="ts">
const props = defineProps<{
  statusLabel: string;
}>();

const tools = [
  { active: true, description: "选择片段或轨道", id: "select", label: "选择" },
  { active: false, description: "移动片段，后续接入", id: "move", label: "移动" },
  { active: false, description: "基于播放头分割片段，后续接入", id: "cut", label: "分割" },
  { active: false, description: "删除选中片段，后续接入", id: "delete", label: "删除" },
  { active: true, description: "磁吸贴合已开启", id: "snap", label: "磁吸" }
] as const;

void props;
</script>

<style scoped>
.workspace-timeline-toolbar {
  align-items: center;
  background: #121b27;
  border: 1px solid #263242;
  border-radius: 8px;
  color: #cbd5e1;
  display: grid;
  gap: 12px;
  grid-template-columns: auto minmax(0, 1fr) auto;
  padding: 8px 10px;
}

.workspace-timeline-toolbar__tools {
  display: flex;
  gap: 6px;
}

.workspace-timeline-toolbar__button {
  align-items: center;
  background: #192433;
  border: 1px solid #334155;
  border-radius: 8px;
  color: #cbd5e1;
  display: inline-flex;
  gap: 6px;
  height: 34px;
  justify-content: center;
  padding: 0 9px;
}

.workspace-timeline-toolbar__button--active {
  background: #102b35;
  border-color: #06b6d4;
  color: #67e8f9;
}

.workspace-timeline-toolbar__button:disabled {
  cursor: default;
  opacity: 1;
}

.workspace-timeline-toolbar__status {
  align-items: baseline;
  display: flex;
  gap: 10px;
  min-width: 0;
}

.workspace-timeline-toolbar__status span {
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-timeline-toolbar__zoom {
  align-items: center;
  color: #94a3b8;
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.workspace-timeline-toolbar__range {
  background: #334155;
  border-radius: 999px;
  height: 5px;
  overflow: hidden;
  position: relative;
  width: 120px;
}

.workspace-timeline-toolbar__range::before {
  background: #06b6d4;
  border-radius: inherit;
  content: "";
  inset: 0 40% 0 0;
  position: absolute;
}

.workspace-tool-icon {
  border: 1.5px solid currentColor;
  border-radius: 5px;
  height: 18px;
  position: relative;
  width: 18px;
}

.workspace-tool-icon[data-icon="select"]::before {
  border-left: 8px solid currentColor;
  border-top: 13px solid transparent;
  content: "";
  left: 4px;
  position: absolute;
  top: 2px;
  transform: rotate(-14deg);
}

.workspace-tool-icon[data-icon="move"]::before {
  background: currentColor;
  box-shadow: 0 -5px 0 currentColor, 0 5px 0 currentColor;
  content: "";
  height: 2px;
  left: 3px;
  position: absolute;
  right: 3px;
  top: 8px;
}

.workspace-tool-icon[data-icon="cut"]::before,
.workspace-tool-icon[data-icon="cut"]::after {
  background: currentColor;
  border-radius: 999px;
  content: "";
  height: 2px;
  left: 2px;
  position: absolute;
  top: 8px;
  width: 13px;
}

.workspace-tool-icon[data-icon="cut"]::before {
  transform: rotate(35deg);
}

.workspace-tool-icon[data-icon="cut"]::after {
  transform: rotate(-35deg);
}

.workspace-tool-icon[data-icon="delete"]::before {
  border: 2px solid currentColor;
  border-radius: 0 0 3px 3px;
  border-top: 0;
  bottom: 2px;
  content: "";
  left: 4px;
  position: absolute;
  right: 4px;
  top: 6px;
}

.workspace-tool-icon[data-icon="delete"]::after {
  background: currentColor;
  border-radius: 999px;
  content: "";
  height: 2px;
  left: 3px;
  position: absolute;
  right: 3px;
  top: 3px;
}

.workspace-tool-icon[data-icon="snap"]::before {
  border: 2px solid currentColor;
  border-radius: 4px 0 0 4px;
  border-right: 0;
  content: "";
  height: 10px;
  left: 2px;
  position: absolute;
  top: 3px;
  width: 5px;
}

.workspace-tool-icon[data-icon="snap"]::after {
  border: 2px solid currentColor;
  border-left: 0;
  border-radius: 0 4px 4px 0;
  content: "";
  height: 10px;
  position: absolute;
  right: 2px;
  top: 3px;
  width: 5px;
}
</style>
```

- [ ] **Step 4: Wire toolbar in page**

In `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`, import the component:

```ts
import WorkspaceTimelineToolbar from "@/modules/workspace/WorkspaceTimelineToolbar.vue";
```

Replace the old `.workspace-tool-bar` block with:

```vue
<WorkspaceTimelineToolbar :status-label="toolBarStatus" />
```

- [ ] **Step 5: Run page test**

Run:

```bash
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts
```

Expected: PASS.

## Task 5: Asset Rail UI

**Files:**

- Modify: `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: Add failing page assertions for asset tab**

In `apps/desktop/tests/ai-editing-workspace-page.spec.ts`, add `/api/assets` handling:

```ts
        if (path === "/api/assets" && method === "GET") {
          return okJsonResponse([
            {
              id: "asset-video-1",
              name: "warm-room-lamp-vertical.mp4",
              type: "video",
              source: "local",
              filePath: "G:/assets/warm-room-lamp-vertical.mp4",
              fileSizeBytes: 1024,
              durationMs: 5000,
              thumbnailPath: null,
              tags: null,
              projectId: "project-1",
              metadataJson: null,
              sourceInfo: {
                source: "local",
                projectId: "project-1",
                groupId: null,
                filePath: "G:/assets/warm-room-lamp-vertical.mp4",
                metadataSummary: {}
              },
              availability: {
                status: "available",
                errorCode: null,
                errorMessage: null,
                nextAction: null
              },
              referenceSummary: {
                total: 0,
                referenceTypes: [],
                blockingDelete: false
              },
              thumbnailStatus: {
                status: "missing",
                path: null,
                generatedAt: null
              },
              createdAt: now(),
              updatedAt: now()
            }
          ]);
        }
```

Add assertions after initial load:

```ts
    expect(wrapper.text()).toContain("资产");
    expect(wrapper.text()).toContain("warm-room-lamp-vertical.mp4");
    expect(wrapper.text()).toContain("加入轨道");
```

- [ ] **Step 2: Run failing page test**

Run:

```bash
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts
```

Expected: FAIL because the asset rail does not show asset tab cards.

- [ ] **Step 3: Update page props**

In `AIEditingWorkspacePage.vue`, include store refs:

```ts
  assetError,
  assetStatus,
  assets,
```

Pass them into `WorkspaceAssetRail`:

```vue
<WorkspaceAssetRail
  class="stage-panel"
  :assembly-state="assemblyState"
  :asset-error="assetError"
  :asset-status="assetStatus"
  :assets="assets"
  :project-id="currentProjectId"
  :selected-clip="selectedClip"
  :timeline="timeline"
  @sync-assets="workspaceStore.loadAssets(currentProjectId)"
/>
```

- [ ] **Step 4: Replace asset rail template and script**

Modify `WorkspaceAssetRail.vue` script props and model:

```ts
import { computed, ref } from "vue";

import {
  buildWorkspaceAssetCards,
  sourceTypeLabel,
  type WorkspaceAssetCard
} from "@/modules/workspace/workspaceAssetViewModel";
import type {
  AssetDto,
  RuntimeRequestErrorShape,
  WorkspaceAssemblyStateDto,
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto
} from "@/types/runtime";

const props = defineProps<{
  assemblyState: WorkspaceAssemblyStateDto | null;
  assetError: RuntimeRequestErrorShape | null;
  assetStatus: "idle" | "loading" | "ready" | "error";
  assets: AssetDto[];
  projectId: string;
  selectedClip: WorkspaceTimelineClipDto | null;
  timeline: WorkspaceTimelineDto | null;
}>();

defineEmits<{
  "sync-assets": [];
}>();

const activeTab = ref<"storyboard" | "voice" | "subtitle" | "assets">("assets");

const assetCards = computed<WorkspaceAssetCard[]>(() =>
  buildWorkspaceAssetCards({
    assets: props.assets,
    projectId: props.projectId,
    timeline: props.timeline
  })
);
```

Use template structure:

```vue
<template>
  <aside class="workspace-asset-rail" aria-label="工作台素材池">
    <header class="workspace-asset-rail__heading">
      <div>
        <strong>素材池</strong>
        <p>{{ sourceSummary }}</p>
      </div>
      <button class="workspace-asset-rail__sync" type="button" @click="$emit('sync-assets')">同步</button>
    </header>

    <div class="workspace-asset-rail__tabs" role="tablist" aria-label="素材来源">
      <button type="button" :class="{ active: activeTab === 'storyboard' }" @click="activeTab = 'storyboard'">分镜</button>
      <button type="button" :class="{ active: activeTab === 'voice' }" @click="activeTab = 'voice'">配音</button>
      <button type="button" :class="{ active: activeTab === 'subtitle' }" @click="activeTab = 'subtitle'">字幕</button>
      <button data-testid="workspace-asset-tab-assets" type="button" :class="{ active: activeTab === 'assets' }" @click="activeTab = 'assets'">资产</button>
    </div>

    <div v-if="activeTab === 'assets'" class="workspace-asset-rail__asset-list scroll-area">
      <div v-if="assetStatus === 'loading'" class="workspace-asset-rail__empty">正在同步资产中心素材。</div>
      <div v-else-if="assetStatus === 'error'" class="workspace-asset-rail__empty" data-tone="danger">
        {{ assetError?.message ?? "资产中心同步失败。" }}
      </div>
      <div v-else-if="assetCards.length === 0" class="workspace-asset-rail__empty">当前项目还没有可用资产。</div>
      <article
        v-for="asset in assetCards"
        v-else
        :key="asset.id"
        class="workspace-asset-card"
        :data-tone="asset.tone"
      >
        <div class="workspace-asset-card__thumb" :data-type="asset.type" />
        <div class="workspace-asset-card__copy">
          <strong>{{ asset.name }}</strong>
          <p>{{ asset.summary }}</p>
          <footer>
            <span>{{ asset.status }}</span>
            <button type="button" disabled>{{ asset.primaryAction }}</button>
          </footer>
        </div>
      </article>
    </div>

    <div v-else class="workspace-asset-rail__list scroll-area">
      <!-- 复用现有 sourceEntries 列表，只按 activeTab 过滤。 -->
    </div>
  </aside>
</template>
```

Keep existing source summary helpers, and filter `sourceEntries` by active tab.

- [ ] **Step 5: Add scoped CSS for tabs and cards**

In `WorkspaceAssetRail.vue`, add:

```css
.workspace-asset-rail__tabs {
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  display: grid;
  gap: 4px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding: 4px;
}

.workspace-asset-rail__tabs button {
  background: transparent;
  border: 0;
  border-radius: 6px;
  color: var(--color-text-secondary);
  font: var(--font-body-sm);
  height: 28px;
}

.workspace-asset-rail__tabs button.active {
  background: var(--color-bg-surface);
  color: var(--color-brand-primary);
  font-weight: 700;
}

.workspace-asset-rail__sync,
.workspace-asset-card button {
  border: 1px solid color-mix(in srgb, var(--color-brand-primary) 32%, var(--color-border-default));
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-brand-primary) 10%, var(--color-bg-surface));
  color: var(--color-brand-primary);
  font: var(--font-caption);
  padding: 4px 9px;
}

.workspace-asset-rail__asset-list {
  display: grid;
  gap: 8px;
}

.workspace-asset-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  min-height: 76px;
  overflow: hidden;
}

.workspace-asset-card[data-tone="success"] {
  border-color: color-mix(in srgb, var(--color-success) 40%, var(--color-border-default));
}

.workspace-asset-card[data-tone="warning"] {
  border-color: color-mix(in srgb, var(--color-warning) 40%, var(--color-border-default));
}

.workspace-asset-card[data-tone="danger"] {
  border-color: color-mix(in srgb, var(--color-danger) 40%, var(--color-border-default));
}

.workspace-asset-card__thumb {
  background:
    radial-gradient(circle at 70% 30%, color-mix(in srgb, var(--color-brand-primary) 45%, transparent), transparent 30%),
    linear-gradient(135deg, #0f172a, #334155);
}

.workspace-asset-card__thumb[data-type="audio"] {
  background:
    repeating-linear-gradient(90deg, color-mix(in srgb, var(--color-brand-primary) 80%, white) 0 3px, transparent 3px 8px),
    #172033;
}

.workspace-asset-card__copy {
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 9px 10px;
}

.workspace-asset-card__copy strong,
.workspace-asset-card__copy p {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-asset-card__copy p {
  color: var(--color-text-secondary);
  margin: 0;
}

.workspace-asset-card footer {
  align-items: center;
  color: var(--color-text-tertiary);
  display: flex;
  font: var(--font-caption);
  justify-content: space-between;
}
```

- [ ] **Step 6: Run page test**

Run:

```bash
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts
```

Expected: PASS.

## Task 6: Preview Stage UI

**Files:**

- Modify: `apps/desktop/src/modules/workspace/WorkspacePreviewStage.vue`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: Add failing assertions for preview controls**

In `ai-editing-workspace-page.spec.ts`, after assemble:

```ts
    expect(wrapper.get('[data-testid="workspace-preview-phone"]').text()).toContain("9:16");
    expect(wrapper.get('[data-testid="workspace-preview-transport"]').text()).toContain("00:");
    expect(wrapper.text()).toContain("分镜占位");
```

- [ ] **Step 2: Run failing page test**

Run:

```bash
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts
```

Expected: FAIL because the new transport and source status are not rendered.

- [ ] **Step 3: Update preview template**

In `WorkspacePreviewStage.vue`, replace phone body with:

```vue
<div class="workspace-preview-stage__phone" data-testid="workspace-preview-phone" data-ratio="9:16">
  <div class="workspace-preview-stage__safe-area">
    <small>9:16</small>
    <div class="workspace-preview-stage__media-card" :data-source="selectedClip?.sourceType ?? 'empty'">
      <strong>{{ headline }}</strong>
      <span>{{ mediaSourceLabel }}</span>
    </div>
    <p class="workspace-preview-stage__subtitle">{{ previewText }}</p>
  </div>
  <div class="workspace-preview-stage__transport" data-testid="workspace-preview-transport">
    <button type="button" disabled>上一段</button>
    <button type="button" disabled>播放</button>
    <span>{{ currentTimeLabel }}</span>
    <div class="workspace-preview-stage__scrub" />
    <span>{{ durationLabel }}</span>
  </div>
</div>
```

Add computed:

```ts
const currentTimeLabel = computed(() => (props.selectedClip ? formatMs(props.selectedClip.startMs) : "00:00"));

const mediaSourceLabel = computed(() => {
  if (!props.selectedClip) return "暂无媒体";
  if (props.selectedClip.sourceType === "asset") return "资产中心素材";
  if (props.selectedClip.sourceType === "storyboard") return "分镜占位";
  if (props.selectedClip.sourceType === "voice_track") return "配音片段";
  if (props.selectedClip.sourceType === "subtitle_track") return "字幕片段";
  return sourceTypeLabel(props.selectedClip.sourceType);
});
```

- [ ] **Step 4: Add preview CSS**

Replace old phone/screen CSS with the third-version structure while keeping scoped selectors:

```css
.workspace-preview-stage__phone {
  aspect-ratio: 9 / 16;
  background:
    radial-gradient(circle at 50% 12%, color-mix(in srgb, var(--color-brand-primary) 26%, transparent), transparent 28%),
    linear-gradient(180deg, #090b0f, #121722);
  border: 1px solid color-mix(in srgb, #ffffff 10%, #0b1220);
  border-radius: 14px;
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 360px;
  overflow: hidden;
  padding: 18px;
  width: min(44vh, 280px);
}

.workspace-preview-stage__safe-area {
  border: 1px dashed rgba(255, 255, 255, 0.18);
  border-radius: 10px;
  color: #fff;
  display: grid;
  flex: 1;
  gap: 14px;
  grid-template-rows: auto minmax(130px, 1fr) auto;
  padding: 14px;
}

.workspace-preview-stage__safe-area small {
  color: rgba(255, 255, 255, 0.58);
  justify-self: center;
}

.workspace-preview-stage__media-card {
  align-self: start;
  background:
    radial-gradient(circle at 70% 28%, rgba(254, 243, 199, 0.8), transparent 24%),
    linear-gradient(135deg, rgba(8, 145, 178, 0.5), rgba(37, 99, 235, 0.35));
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  display: grid;
  gap: 8px;
  min-height: 132px;
  padding: 14px;
  place-items: center;
  text-align: center;
}

.workspace-preview-stage__media-card span {
  background: rgba(2, 6, 23, 0.68);
  border-radius: 999px;
  font-size: 11px;
  padding: 4px 8px;
}

.workspace-preview-stage__subtitle {
  background: rgba(0, 0, 0, 0.58);
  border-radius: 8px;
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.35;
  margin: 0;
  padding: 9px 12px;
  text-align: center;
}

.workspace-preview-stage__transport {
  align-items: center;
  background: rgba(15, 23, 42, 0.88);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  color: #e2e8f0;
  display: grid;
  font-size: 12px;
  gap: 8px;
  grid-template-columns: auto auto auto minmax(40px, 1fr) auto;
  height: 42px;
  margin-top: 12px;
  padding: 0 9px;
}

.workspace-preview-stage__transport button {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  color: #e2e8f0;
  height: 28px;
  padding: 0 9px;
}

.workspace-preview-stage__scrub {
  background: #334155;
  border-radius: 999px;
  height: 5px;
  overflow: hidden;
  position: relative;
}

.workspace-preview-stage__scrub::before {
  background: linear-gradient(90deg, #06b6d4, #60a5fa);
  border-radius: inherit;
  content: "";
  inset: 0 56% 0 0;
  position: absolute;
}
```

- [ ] **Step 5: Run page test**

Run:

```bash
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts
```

Expected: PASS.

## Task 7: Timeline Visual UI

**Files:**

- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Test: `apps/desktop/tests/workspace-layout-contract.spec.ts`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: Add failing layout contract checks**

Append to `apps/desktop/tests/workspace-layout-contract.spec.ts`:

```ts
  it("defines the third-version timeline visual language", () => {
    const timeline = readSource("../src/modules/workspace/WorkspaceTimeline.vue");

    expect(timeline).toContain("workspace-timeline__playhead");
    expect(timeline).toContain("workspace-timeline__waveform");
    expect(timeline).toContain("workspace-timeline__thumbnail-strip");
    expect(timeline).toContain("workspace-timeline__subtitle-block");
    expect(timeline).toContain("buildTimelineRows");
    expect(timeline).toContain("trackVisualClass");
  });
```

- [ ] **Step 2: Run failing contract test**

Run:

```bash
npm --prefix apps/desktop run test -- workspace-layout-contract.spec.ts
```

Expected: FAIL because the timeline visual classes and view model are not used.

- [ ] **Step 3: Use timeline view model in component**

In `WorkspaceTimeline.vue`, import:

```ts
import {
  buildTimelineRows,
  computePlayheadPercent,
  type TimelineClipView
} from "@/modules/workspace/workspaceTimelineViewModel";
```

Add computed:

```ts
const timelineRows = computed(() => buildTimelineRows(props.tracks, durationMs.value));

const playheadPercent = computed(() => {
  const selected = props.timeline?.tracks.flatMap((track) => track.clips).find((clip) => clip.id === props.selectedClipId);
  return computePlayheadPercent(selected?.startMs ?? 0, durationMs.value);
});

function clipPercentStyle(clipView: TimelineClipView): Record<string, string> {
  return {
    left: `${clipView.leftPercent}%`,
    width: `${clipView.widthPercent}%`
  };
}
```

- [ ] **Step 4: Replace timeline body template**

Inside `.workspace-timeline__tracks`, render rows:

```vue
<transition-group name="track-list">
  <article
    v-for="row in timelineRows"
    :key="row.track.id"
    class="workspace-track"
    :class="[`workspace-track--${row.heightClass}`, `workspace-track--${row.visualClass}`, { 'workspace-track--selected': selectedTrackId === row.track.id }]"
  >
    <button class="workspace-track__label" type="button" @click="$emit('select-track', row.track.id)">
      <span class="workspace-track__badge">{{ trackBadge(row.visualClass) }}</span>
      <div>
        <strong>{{ row.track.name }}</strong>
        <small>{{ trackKindLabel(row.track.kind) }} · {{ trackPolicy(row.track.id) }} · {{ row.track.clips.length }} 个片段</small>
      </div>
    </button>

    <div class="workspace-track__lane">
      <button
        v-for="clipView in row.clips"
        :key="clipView.clip.id"
        class="workspace-clip"
        :class="[
          `workspace-clip--${row.visualClass}`,
          `workspace-clip--${clipView.joinClass}`,
          { 'workspace-clip--selected': selectedClipId === clipView.clip.id }
        ]"
        :data-status="clipView.clip.status"
        type="button"
        :style="clipPercentStyle(clipView)"
        @click="$emit('select-clip', { clipId: clipView.clip.id, trackId: row.track.id })"
      >
        <span v-if="row.visualClass === 'video'" class="workspace-timeline__thumbnail-strip" aria-hidden="true">
          <i v-for="index in 5" :key="index" />
        </span>
        <span v-else-if="row.visualClass === 'voice' || row.visualClass === 'bgm'" class="workspace-timeline__waveform" aria-hidden="true">
          <i v-for="height in waveformHeights" :key="height" :style="{ '--bar-height': `${height}px` }" />
        </span>
        <span v-else class="workspace-timeline__subtitle-block">{{ clipView.clip.metadata?.text ?? clipView.clip.label }}</span>
        <strong>{{ clipView.clip.label }}</strong>
      </button>
      <span v-if="row.clips.length === 0" class="workspace-track__empty">当前轨道暂无片段</span>
    </div>
  </article>
</transition-group>
<span class="workspace-timeline__playhead" :style="{ left: `${playheadPercent}%` }">
  <span>{{ selectedStartLabel }}</span>
</span>
```

Add helpers:

```ts
const waveformHeights = [12, 20, 16, 25, 13, 22, 15, 28, 11, 19, 26, 14, 21, 12, 24];

const selectedStartLabel = computed(() => {
  const selected = props.timeline?.tracks.flatMap((track) => track.clips).find((clip) => clip.id === props.selectedClipId);
  return formatMs(selected?.startMs ?? 0);
});

function trackBadge(visualClass: string): string {
  if (visualClass === "video") return "V";
  if (visualClass === "bgm") return "B";
  if (visualClass === "voice") return "A";
  return "S";
}
```

- [ ] **Step 5: Add dark timeline CSS**

Replace timeline visual CSS in `WorkspaceTimeline.vue` with dark workbench styles that include:

```css
.workspace-timeline {
  background: #0f1722;
  border-color: #243040;
  color: #e2e8f0;
}

.workspace-timeline__body {
  display: grid;
  grid-template-columns: 138px minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.workspace-timeline__playhead {
  bottom: 0;
  color: #fff;
  pointer-events: none;
  position: absolute;
  top: 0;
  width: 2px;
  z-index: 5;
}

.workspace-timeline__playhead::before {
  background: linear-gradient(180deg, #ff7a92, #ff3158);
  box-shadow: 0 0 18px rgba(255, 49, 88, 0.44);
  content: "";
  inset: 26px 0 0 0;
  position: absolute;
  width: 2px;
}

.workspace-timeline__playhead span {
  background: linear-gradient(180deg, #ff6b86, #ff3158);
  border-radius: 7px 7px 9px 9px;
  box-shadow: 0 8px 20px rgba(255, 49, 88, 0.32);
  display: grid;
  font-size: 11px;
  font-weight: 900;
  height: 26px;
  left: 50%;
  place-items: center;
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  width: 54px;
}
```

Also add CSS for `.workspace-timeline__thumbnail-strip`, `.workspace-timeline__waveform`, `.workspace-timeline__subtitle-block`, `.workspace-track--tall`, `.workspace-track--medium`, `.workspace-track--compact`, and joined clip radius classes.

- [ ] **Step 6: Run tests**

Run:

```bash
npm --prefix apps/desktop run test -- workspace-timeline-view-model.spec.ts workspace-layout-contract.spec.ts ai-editing-workspace-page.spec.ts
```

Expected: PASS.

## Task 8: Inspector Structure

**Files:**

- Modify: `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: Add failing assertions for inspector sections**

In `ai-editing-workspace-page.spec.ts`, after assemble:

```ts
    expect(wrapper.text()).toContain("片段信息");
    expect(wrapper.text()).toContain("时间参数");
    expect(wrapper.text()).toContain("素材来源");
    expect(wrapper.text()).toContain("AI 粗剪建议");
    expect(wrapper.text()).toContain("默认折叠");
```

- [ ] **Step 2: Run failing page test**

Run:

```bash
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts
```

Expected: FAIL because inspector has not been reorganized.

- [ ] **Step 3: Pass last command result**

In `AIEditingWorkspacePage.vue`, include `lastCommandResult` in `storeToRefs`, then pass:

```vue
<WorkspaceInspector
  ...
  :last-command-result="lastCommandResult"
/>
```

Update props in `WorkspaceInspector.vue`:

```ts
  lastCommandResult: WorkspaceAICommandResultDto | null;
```

- [ ] **Step 4: Reorganize inspector template**

Use this structure in `WorkspaceInspector.vue`:

```vue
<aside class="workspace-inspector" aria-label="时间线检查器">
  <header class="workspace-inspector__heading">
    <span class="material-symbols-outlined">tune</span>
    <div>
      <strong>基础属性</strong>
      <p>{{ headingDescription }}</p>
    </div>
  </header>

  <section class="workspace-inspector__section">
    <header><strong>片段信息</strong><span>{{ statusLabel }}</span></header>
    <dl class="workspace-inspector__facts">
      <div><dt>时间线</dt><dd>{{ timeline?.name ?? "未创建" }}</dd></div>
      <div><dt>轨道</dt><dd>{{ selectedTrack?.name ?? "未选择" }}</dd></div>
      <div><dt>片段</dt><dd>{{ selectedClip?.label ?? "未选择" }}</dd></div>
      <div><dt>状态</dt><dd>{{ selectedClip?.status ?? "未选择" }}</dd></div>
    </dl>
  </section>

  <section class="workspace-inspector__section">
    <header><strong>时间参数</strong><span>{{ clipTimingLabel }}</span></header>
    <dl class="workspace-inspector__facts">
      <div><dt>起点</dt><dd>{{ selectedClip ? formatMs(selectedClip.startMs) : "未选择" }}</dd></div>
      <div><dt>时长</dt><dd>{{ selectedClip ? formatMs(selectedClip.durationMs) : "未选择" }}</dd></div>
    </dl>
  </section>

  <section class="workspace-inspector__section">
    <header><strong>素材来源</strong><span>{{ sourceLabel }}</span></header>
    <p>{{ sourceDescription }}</p>
  </section>

  <section class="workspace-inspector__section" :data-tone="precheck?.issues.length ? 'warning' : 'neutral'">
    <header><strong>预检提醒</strong><span>{{ precheckTitle }}</span></header>
    <p>{{ precheckDescription }}</p>
  </section>

  <details class="workspace-inspector__section workspace-inspector__ai">
    <summary>
      <strong>AI 粗剪建议</strong>
      <span>默认折叠</span>
    </summary>
    <p>{{ aiSuggestionText }}</p>
  </details>
</aside>
```

Add computed:

```ts
const sourceDescription = computed(() => {
  if (!props.selectedClip) return "选中片段后显示资产中心或创作链路来源。";
  if (props.selectedClip.sourceType === "asset") return "该片段来自资产中心素材，可在后续功能中替换或重新定位。";
  return `该片段来自${sourceKindLabel(props.selectedClip.metadata?.sourceKind ?? props.selectedClip.sourceType)}。`;
});

const aiSuggestionText = computed(() => {
  if (props.lastCommandResult?.message) return props.lastCommandResult.message;
  return "暂无可应用建议。AI 建议必须经确认后才会修改时间线。";
});
```

- [ ] **Step 5: Add inspector CSS**

Add section styling:

```css
.workspace-inspector__section {
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  display: grid;
  gap: 8px;
  padding: 12px;
}

.workspace-inspector__section header,
.workspace-inspector__ai summary {
  align-items: center;
  cursor: default;
  display: flex;
  justify-content: space-between;
}

.workspace-inspector__section header span,
.workspace-inspector__ai summary span {
  color: var(--color-text-tertiary);
  font: var(--font-caption);
}

.workspace-inspector__section[data-tone="warning"] {
  border-color: color-mix(in srgb, var(--color-warning) 40%, var(--color-border-default));
}

.workspace-inspector__ai {
  background: linear-gradient(180deg, color-mix(in srgb, var(--color-brand-primary) 10%, var(--color-bg-surface)), var(--color-bg-muted));
}
```

- [ ] **Step 6: Run page test**

Run:

```bash
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts
```

Expected: PASS.

## Task 9: Responsive Layout Contract

**Files:**

- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`
- Modify: `apps/desktop/tests/workspace-layout-contract.spec.ts`

- [ ] **Step 1: Add failing responsive assertions**

In `workspace-layout-contract.spec.ts`, update the M05 layout test to assert:

```ts
    expect(css).toMatch(/\.workspace-editor\s*{[\s\S]*grid-template-rows:\s*minmax\(0,\s*1fr\)\s+auto\s+minmax\(260px,\s*34vh\);/);
    expect(css).toMatch(/\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(270px,\s*330px\)\s+minmax\(520px,\s*1fr\)\s+minmax\(280px,\s*340px\);/);
```

- [ ] **Step 2: Run failing contract test**

Run:

```bash
npm --prefix apps/desktop run test -- workspace-layout-contract.spec.ts
```

Expected: FAIL because current CSS still uses the earlier layout values.

- [ ] **Step 3: Update page layout CSS**

Modify `AIEditingWorkspacePage.css`:

```css
.workspace-editor {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto minmax(260px, 34vh);
  gap: var(--space-3);
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.workspace-stage {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: minmax(270px, 330px) minmax(520px, 1fr) minmax(280px, 340px);
  align-items: stretch;
  min-height: 0;
  min-width: 0;
}
```

Keep existing container query behavior, but update breakpoints:

```css
@container editing-workspace (max-width: 1180px) {
  .workspace-stage {
    grid-template-columns: minmax(0, 330px) minmax(0, 1fr);
  }

  .stage-panel-wrapper--inspector {
    grid-column: 1 / -1;
    min-height: 180px;
  }
}

@container editing-workspace (max-width: 860px) {
  .workspace-editor {
    grid-template-rows: auto auto minmax(260px, 36vh);
    overflow-y: auto;
  }

  .workspace-stage {
    grid-template-columns: minmax(0, 1fr);
  }
}
```

- [ ] **Step 4: Run contract test**

Run:

```bash
npm --prefix apps/desktop run test -- workspace-layout-contract.spec.ts
```

Expected: PASS.

## Task 10: Final Verification

**Files:**

- Modify: `docs/RUNTIME-API-CALLS.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update docs for UI-only scope**

Append to `docs/RUNTIME-API-CALLS.md` under M05 workspace notes:

```md
### M05 UI 资产来源说明

- M05 剪辑工作台素材池通过 `GET /api/assets` 读取资产中心素材，并在前端按当前项目过滤。
- 本轮只展示资产状态，不在 UI 层直接读写本地文件。
- `替换片段`、`加入轨道`、`分割`、`删除` 先保留为不可触发的基础工具入口，后续接入 `/api/workspace/clips/{clip_id}/replace`、`move`、`trim` 等接口。
```

Append to `CHANGELOG.md`:

```md
- M05 AI 剪辑工作台 UI 定稿落地：增加资产中心素材入口、缩略图时间线、音频波形、字幕块、播放头、基础工具栏和属性面板结构。
```

- [ ] **Step 2: Run focused tests**

Run:

```bash
npm --prefix apps/desktop run test -- workspace-asset-view-model.spec.ts workspace-timeline-view-model.spec.ts editing-workspace-store.spec.ts ai-editing-workspace-page.spec.ts workspace-layout-contract.spec.ts
```

Expected: PASS.

- [ ] **Step 3: Run desktop build**

Run:

```bash
npm --prefix apps/desktop run build
```

Expected: PASS.

- [ ] **Step 4: Browser verification**

Start or reuse the desktop dev server, then inspect `/workspace/editing`:

```bash
npm --prefix apps/desktop run dev
```

Verify manually:

- 页面无横向大空白。
- 三栏和底部时间线在宽屏铺满。
- 紧凑窗口下不重叠、不撑破。
- 资产 Tab 显示真实空态或真实资产。
- 时间线片段磁吸贴合。
- 播放头可辨识。
- AI 建议默认折叠。

- [ ] **Step 5: Commit implementation**

Stage only M05 UI implementation files:

```bash
git add apps/desktop/src/modules/workspace apps/desktop/src/pages/workspace apps/desktop/src/stores/editing-workspace.ts apps/desktop/tests docs/RUNTIME-API-CALLS.md CHANGELOG.md
git commit -m "feat: refine m05 editing workbench ui"
```

## Self-Review

Spec coverage:

- 资产中心接入：Task 1、Task 3、Task 5。
- 缩略图、波形、字幕块、磁吸时间线：Task 2、Task 7。
- 工具激活态：Task 4。
- 播放器：Task 6。
- 属性面板和 AI 建议折叠：Task 8。
- 响应式与全局布局边界：Task 9。
- 文档和验证：Task 10。

Scope boundary:

- 计划没有实现拖拽、分割、删除、替换、真实播放或素材管理。
- 所有新增数据读取通过 Runtime client 和 Pinia store。
- 组件只消费 DTO 和 view model，不直接 fetch。

