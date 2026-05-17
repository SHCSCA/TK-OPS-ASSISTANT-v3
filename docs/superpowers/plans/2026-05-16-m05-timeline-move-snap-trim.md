# M05 时间线移动磁吸与裁剪 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 M05 时间线从“可选择、可分割、可删除”推进到可移动、可磁吸、可按播放头分割、可基础裁剪的真实编辑状态。

**Architecture:** Runtime 继续作为时间线业务规则唯一执行点，前端只提交明确的移动、裁剪和播放头意图。前端将播放头、选中片段、工具状态收敛到 `editing-workspace` store，并用 `workspaceTimelineViewModel` 计算可视位置、磁吸候选和裁剪手柄状态。

**Tech Stack:** Vue 3 + Pinia + TypeScript + Vitest；Python + FastAPI + Pydantic + pytest；Runtime HTTP JSON 信封。

---

## Scope

实现内容：

- 时间线点击可更新真实 `playheadMs`，播放头位置进入 store 与页面上下文。
- 分割片段优先使用当前播放头；播放头不在选中片段内部时显示中文错误，不再退回到中点分割。
- 移动工具启用为 `左移 / 右移` 两个基础步进动作，默认步进 500ms，按磁吸候选贴近相邻片段边界。
- Runtime `move_clip` 增加锁定轨道、负起点和同轨重叠校验；返回可见中文错误。
- 裁剪工具启用左边缘 / 右边缘基础裁剪动作，默认步进 500ms，保证片段最小时长 500ms。
- 时间线片段显示左右裁剪手柄、选中态和播放头落点状态。
- 更新 Runtime API 文档、changelog 与覆盖测试。

不做内容：

- 不做鼠标拖拽自由移动。
- 不做跨轨道拖拽。
- 不做撤销 / 重做。
- 不做真实媒体文件切割或重新渲染。
- 不引入新页面或旧壳逻辑。

## File Map

Runtime:

- Modify: `apps/py-runtime/src/services/workspace_service.py`
- Test: `tests/runtime/test_workspace_service.py`
- Test: `tests/contracts/test_workspace_runtime_contract.py`

Desktop runtime contract:

- Modify: `apps/desktop/src/types/runtime.ts`
- Modify: `apps/desktop/src/app/runtime-client.ts`
- Test: `apps/desktop/tests/runtime-client-b-s4.spec.ts`

Desktop timeline state and view model:

- Modify: `apps/desktop/src/stores/editing-workspace.ts`
- Modify: `apps/desktop/src/modules/workspace/workspaceTimelineViewModel.ts`
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`
- Test: `apps/desktop/tests/workspace-timeline-view-model.spec.ts`

Desktop UI:

- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimelineToolbar.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`
- Test: `apps/desktop/tests/workspace-timeline-toolbar.spec.ts`
- Test: `apps/desktop/tests/workspace-layout-contract.spec.ts`

Docs:

- Modify: `docs/RUNTIME-API-CALLS.md`
- Modify: `CHANGELOG.md`

## Task 1: Runtime 移动与裁剪规则收紧

**Files:**

- Modify: `apps/py-runtime/src/services/workspace_service.py`
- Test: `tests/runtime/test_workspace_service.py`
- Test: `tests/contracts/test_workspace_runtime_contract.py`

- [ ] **Step 1: Write failing Runtime tests**

Add focused tests to `tests/runtime/test_workspace_service.py`:

```python
def test_move_clip_rejects_overlap_with_same_track_neighbor(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    result = service.assemble_project_timeline("project-001", {"mode": "merge_managed"})
    clip_id = result.timeline.tracks[0].clips[1].id

    with pytest.raises(HTTPException) as exc_info:
        service.move_clip(clip_id, {"targetTrackId": result.timeline.tracks[0].id, "startMs": 1000})

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "片段移动后会与同轨片段重叠。"


def test_trim_clip_keeps_minimum_duration(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    result = service.assemble_project_timeline("project-001", {"mode": "merge_managed"})
    clip = result.timeline.tracks[0].clips[0]

    with pytest.raises(HTTPException) as exc_info:
        service.trim_clip(clip.id, {"durationMs": 200})

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "片段裁剪后至少需要保留 500ms。"
```

Add contract assertions to `tests/contracts/test_workspace_runtime_contract.py`:

```python
def test_workspace_clip_move_and_trim_contracts_are_documented() -> None:
    route_paths = collect_route_paths()

    assert ("POST", "/api/workspace/clips/{clip_id}/move") in route_paths
    assert ("POST", "/api/workspace/clips/{clip_id}/trim") in route_paths
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/runtime/test_workspace_service.py::test_move_clip_rejects_overlap_with_same_track_neighbor tests/runtime/test_workspace_service.py::test_trim_clip_keeps_minimum_duration -q
```

Expected: both tests fail because `move_clip` currently accepts overlap and `trim_clip` accepts too-short durations.

- [ ] **Step 3: Implement Runtime validation**

In `apps/py-runtime/src/services/workspace_service.py`, add helper methods near existing timeline helpers:

```python
def _clip_bounds(self, clip: dict[str, object]) -> tuple[int, int]:
    start_ms = int(clip.get("startMs") or 0)
    duration_ms = int(clip.get("durationMs") or 0)
    return start_ms, start_ms + duration_ms


def _assert_clip_has_min_duration(self, clip: dict[str, object]) -> None:
    duration_ms = int(clip.get("durationMs") or 0)
    if duration_ms < 500:
        raise HTTPException(status_code=400, detail="片段裁剪后至少需要保留 500ms。")


def _assert_no_same_track_overlap(
    self,
    track: dict[str, object],
    candidate: dict[str, object],
    *,
    ignore_clip_id: str,
) -> None:
    candidate_start, candidate_end = self._clip_bounds(candidate)
    for item in track.get("clips", []):
        if item.get("id") == ignore_clip_id:
            continue
        item_start, item_end = self._clip_bounds(item)
        if candidate_start < item_end and candidate_end > item_start:
            raise HTTPException(status_code=400, detail="片段移动后会与同轨片段重叠。")
```

Update `move_clip`:

```python
if bool(target_track.get("locked")):
    raise HTTPException(status_code=400, detail="锁定轨道不能移动片段。")

start_ms = int(input_data["startMs"])
if start_ms < 0:
    raise HTTPException(status_code=400, detail="片段起点不能小于 0。")

moved_clip["startMs"] = start_ms
self._assert_no_same_track_overlap(target_track, moved_clip, ignore_clip_id=clip_id)
```

Update `trim_clip` after field assignment:

```python
if int(trimmed_clip.get("startMs") or 0) < 0:
    raise HTTPException(status_code=400, detail="片段起点不能小于 0。")
self._assert_clip_has_min_duration(trimmed_clip)
```

- [ ] **Step 4: Verify Runtime tests pass**

Run:

```powershell
pytest tests/runtime/test_workspace_service.py tests/contracts/test_workspace_runtime_contract.py -q
```

Expected: all selected Runtime and contract tests pass.

## Task 2: Store 播放头、移动和裁剪动作

**Files:**

- Modify: `apps/desktop/src/stores/editing-workspace.ts`
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`

- [ ] **Step 1: Write failing store tests**

Add tests to `apps/desktop/tests/editing-workspace-store.spec.ts`:

```ts
it("splits selected clip at current playhead when playhead is inside the clip", async () => {
  const store = useEditingWorkspaceStore();
  store.applyTimelineResult(timelineResultWithClip({ id: "clip-1", startMs: 1000, durationMs: 4000 }));
  store.selectClip("clip-1");
  store.setPlayheadMs(2500);

  await store.splitSelectedClip();

  expect(splitWorkspaceClipSpy).toHaveBeenCalledWith("clip-1", { splitAtMs: 2500 });
});

it("moves selected clip by the requested delta through Runtime", async () => {
  const store = useEditingWorkspaceStore();
  store.applyTimelineResult(timelineResultWithClip({ id: "clip-1", trackId: "track-video", startMs: 5000, durationMs: 2000 }));
  store.selectTrack("track-video");
  store.selectClip("clip-1");

  await store.moveSelectedClipBy(-500);

  expect(moveWorkspaceClipSpy).toHaveBeenCalledWith("clip-1", {
    targetTrackId: "track-video",
    startMs: 4500
  });
});

it("trims selected clip from the right edge through Runtime", async () => {
  const store = useEditingWorkspaceStore();
  store.applyTimelineResult(timelineResultWithClip({ id: "clip-1", startMs: 0, durationMs: 3000 }));
  store.selectClip("clip-1");

  await store.trimSelectedClip("right", -500);

  expect(trimWorkspaceClipSpy).toHaveBeenCalledWith("clip-1", { durationMs: 2500 });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/editing-workspace-store.spec.ts
```

Expected: failures mention missing `setPlayheadMs`, `moveSelectedClipBy`, and `trimSelectedClip`.

- [ ] **Step 3: Implement store state and actions**

In `EditingWorkspaceState`, add:

```ts
playheadMs: number;
```

Initialize it:

```ts
playheadMs: 0,
```

Add actions:

```ts
setPlayheadMs(value: number): void {
  const durationMs = Math.max(0, Math.round((this.timeline?.durationSeconds ?? 0) * 1000));
  this.playheadMs = Math.min(durationMs, Math.max(0, Math.round(value)));
},

async moveSelectedClipBy(deltaMs: number): Promise<WorkspaceTimelineDto | null> {
  const clip = this.findClipById(this.selectedClipId);
  if (!clip) {
    this.applyInputError("请先选择要移动的片段。");
    return null;
  }
  this.status = "saving";
  this.error = null;
  try {
    const result = await moveWorkspaceClip(clip.id, {
      targetTrackId: clip.trackId,
      startMs: Math.max(0, clip.startMs + deltaMs)
    });
    this.applyTimelineResult(result);
    return result.timeline;
  } catch (error) {
    this.applyRuntimeError(error);
    return null;
  }
},

async trimSelectedClip(edge: "left" | "right", deltaMs: number): Promise<WorkspaceTimelineDto | null> {
  const clip = this.findClipById(this.selectedClipId);
  if (!clip) {
    this.applyInputError("请先选择要裁剪的片段。");
    return null;
  }

  const input =
    edge === "left"
      ? {
          startMs: Math.max(0, clip.startMs + deltaMs),
          durationMs: clip.durationMs - deltaMs,
          inPointMs: Math.max(0, clip.inPointMs + deltaMs)
        }
      : { durationMs: clip.durationMs + deltaMs };

  this.status = "saving";
  this.error = null;
  try {
    const result = await trimWorkspaceClip(clip.id, input);
    this.applyTimelineResult(result);
    return result.timeline;
  } catch (error) {
    this.applyRuntimeError(error);
    return null;
  }
}
```

Update `splitSelectedClip` so it rejects invalid playback position:

```ts
if (this.playheadMs <= clip.startMs || this.playheadMs >= clip.startMs + clip.durationMs) {
  this.applyInputError("播放头必须位于选中片段内部才能分割。");
  return null;
}
```

- [ ] **Step 4: Verify store tests pass**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/editing-workspace-store.spec.ts
```

Expected: all store tests pass.

## Task 3: View model 增加磁吸候选与播放头计算

**Files:**

- Modify: `apps/desktop/src/modules/workspace/workspaceTimelineViewModel.ts`
- Test: `apps/desktop/tests/workspace-timeline-view-model.spec.ts`

- [ ] **Step 1: Write failing view-model tests**

Add tests:

```ts
it("computes nearest snap position from clip edges", () => {
  const track = {
    id: "track-video",
    kind: "video",
    name: "视频轨",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips: [
      clip({ id: "left", startMs: 0, durationMs: 3000 }),
      clip({ id: "target", startMs: 3500, durationMs: 2000 }),
      clip({ id: "right", startMs: 6000, durationMs: 2000 })
    ]
  };

  expect(resolveSnapStartMs(track.clips, "target", 3020, 120)).toBe(3000);
  expect(resolveSnapStartMs(track.clips, "target", 5980, 120)).toBe(6000);
  expect(resolveSnapStartMs(track.clips, "target", 4200, 120)).toBe(4200);
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/workspace-timeline-view-model.spec.ts
```

Expected: failure says `resolveSnapStartMs` is not exported.

- [ ] **Step 3: Implement helper**

Add export to `workspaceTimelineViewModel.ts`:

```ts
export function resolveSnapStartMs(
  clips: WorkspaceTimelineClipDto[],
  movingClipId: string,
  desiredStartMs: number,
  thresholdMs = 120
): number {
  const desired = Math.max(0, Math.round(desiredStartMs));
  const candidates = clips
    .filter((clip) => clip.id !== movingClipId)
    .flatMap((clip) => [clip.startMs, clip.startMs + clip.durationMs]);

  const nearest = candidates
    .map((candidate) => ({ candidate, distance: Math.abs(candidate - desired) }))
    .sort((left, right) => left.distance - right.distance)[0];

  if (!nearest || nearest.distance > thresholdMs) return desired;
  return nearest.candidate;
}
```

- [ ] **Step 4: Verify view-model tests pass**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/workspace-timeline-view-model.spec.ts
```

Expected: all view-model tests pass.

## Task 4: Toolbar 与时间线 UI 启用移动、裁剪和播放头

**Files:**

- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimelineToolbar.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`
- Test: `apps/desktop/tests/workspace-timeline-toolbar.spec.ts`
- Test: `apps/desktop/tests/workspace-layout-contract.spec.ts`

- [ ] **Step 1: Write failing UI tests**

Add to `apps/desktop/tests/workspace-timeline-toolbar.spec.ts`:

```ts
it("emits move and trim commands from enabled controls", async () => {
  const wrapper = mount(WorkspaceTimelineToolbar, {
    props: {
      statusLabel: "片段：clip-1",
      canDelete: true,
      canMove: true,
      canSplit: true,
      canTrim: true
    }
  });

  await wrapper.find('[data-testid="workspace-tool-move-left"]').trigger("click");
  await wrapper.find('[data-testid="workspace-tool-trim-right"]').trigger("click");

  expect(wrapper.emitted("move")).toEqual([[-500]]);
  expect(wrapper.emitted("trim")).toEqual([["right", -500]]);
});
```

Add to `apps/desktop/tests/workspace-layout-contract.spec.ts`:

```ts
it("keeps timeline trim handles and playhead selectors stable", () => {
  const source = readFileSync("src/modules/workspace/WorkspaceTimeline.vue", "utf8");

  expect(source).toContain('data-testid="workspace-playhead"');
  expect(source).toContain('data-testid="workspace-trim-left"');
  expect(source).toContain('data-testid="workspace-trim-right"');
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/workspace-timeline-toolbar.spec.ts tests/workspace-layout-contract.spec.ts
```

Expected: failures mention missing props, emitted events, and data-testid selectors.

- [ ] **Step 3: Implement toolbar events**

In `WorkspaceTimelineToolbar.vue`, add props:

```ts
canMove?: boolean;
canTrim?: boolean;
```

Add emits:

```ts
move: [deltaMs: number];
trim: [edge: "left" | "right", deltaMs: number];
```

Replace disabled `move` tool with two step controls:

```vue
<button
  class="workspace-timeline-toolbar__button"
  data-testid="workspace-tool-move-left"
  type="button"
  :disabled="disabled || !canMove"
  title="左移 0.5 秒"
  @click="$emit('move', -500)"
>
  <span class="workspace-timeline-toolbar__icon" data-icon="move-left" aria-hidden="true"></span>
  <span class="workspace-timeline-toolbar__label">左移</span>
</button>
```

Add trim controls:

```vue
<button
  class="workspace-timeline-toolbar__button"
  data-testid="workspace-tool-trim-right"
  type="button"
  :disabled="disabled || !canTrim"
  title="右侧收短 0.5 秒"
  @click="$emit('trim', 'right', -500)"
>
  <span class="workspace-timeline-toolbar__icon" data-icon="trim-right" aria-hidden="true"></span>
  <span class="workspace-timeline-toolbar__label">右裁</span>
</button>
```

- [ ] **Step 4: Implement timeline playhead and trim handles**

In `WorkspaceTimeline.vue`, add props and emits:

```ts
playheadMs: number;
```

```ts
playhead: [positionMs: number];
trim: [payload: { clipId: string; edge: "left" | "right"; deltaMs: number }];
```

Render playhead:

```vue
<span
  class="workspace-timeline__playhead"
  data-testid="workspace-playhead"
  :style="{ left: `${computePlayheadPercent(playheadMs, durationMs)}%` }"
/>
```

Render trim handles inside selected clip:

```vue
<button
  v-if="clip.id === selectedClipId"
  class="workspace-timeline__trim-handle workspace-timeline__trim-handle--left"
  data-testid="workspace-trim-left"
  type="button"
  title="左侧收短 0.5 秒"
  @click.stop="$emit('trim', { clipId: clip.id, edge: 'left', deltaMs: 500 })"
/>
<button
  v-if="clip.id === selectedClipId"
  class="workspace-timeline__trim-handle workspace-timeline__trim-handle--right"
  data-testid="workspace-trim-right"
  type="button"
  title="右侧收短 0.5 秒"
  @click.stop="$emit('trim', { clipId: clip.id, edge: 'right', deltaMs: -500 })"
/>
```

- [ ] **Step 5: Wire page handlers**

In `AIEditingWorkspacePage.vue`, pass new props/events:

```vue
<WorkspaceTimelineToolbar
  :can-move="Boolean(selectedClip)"
  :can-trim="Boolean(selectedClip)"
  @move="handleMoveSelectedClip"
  @trim="handleTrimSelectedClip"
/>
<WorkspaceTimeline
  :playhead-ms="playheadMs"
  @playhead="handleSetPlayhead"
  @trim="handleTimelineTrim"
/>
```

Add handlers:

```ts
async function handleMoveSelectedClip(deltaMs: number): Promise<void> {
  await workspaceStore.moveSelectedClipBy(deltaMs);
}

async function handleTrimSelectedClip(edge: "left" | "right", deltaMs: number): Promise<void> {
  await workspaceStore.trimSelectedClip(edge, deltaMs);
}

function handleSetPlayhead(positionMs: number): void {
  workspaceStore.setPlayheadMs(positionMs);
}

async function handleTimelineTrim(payload: { clipId: string; edge: "left" | "right"; deltaMs: number }): Promise<void> {
  workspaceStore.selectClip(payload.clipId);
  await workspaceStore.trimSelectedClip(payload.edge, payload.deltaMs);
}
```

- [ ] **Step 6: Verify UI tests pass**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/workspace-timeline-toolbar.spec.ts tests/workspace-layout-contract.spec.ts
```

Expected: all UI tests pass.

## Task 5: Docs, changelog and final verification

**Files:**

- Modify: `docs/RUNTIME-API-CALLS.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update Runtime API docs**

In `docs/RUNTIME-API-CALLS.md`, update M05 notes:

```markdown
- 基础工具栏已开放选中片段的 `左移 / 右移`、`左裁 / 右裁`、`分割` 与 `删除`。
- 分割使用当前播放头位置；播放头必须位于选中片段内部。
- Runtime 会拒绝锁定轨道、负起点、同轨重叠和小于 500ms 的裁剪结果。
```

- [ ] **Step 2: Update changelog**

In `CHANGELOG.md`, add:

```markdown
- M05 时间线二阶段补齐播放头分割、步进移动、基础磁吸和边缘裁剪，Runtime 统一校验重叠、锁定轨道和最小时长。
```

- [ ] **Step 3: Run full verification**

Run:

```powershell
npm --prefix apps/desktop run test
pytest tests/runtime/test_workspace_service.py tests/contracts/test_workspace_runtime_contract.py -q
npm --prefix apps/desktop run build
git diff --check
```

Expected:

- Desktop Vitest: all tests pass.
- Runtime focused pytest: all tests pass.
- Vite build: exits 0.
- `git diff --check`: no whitespace errors.

## Self Review

- Spec coverage: plan covers playback split, move, snap candidate, trim, Runtime validation, UI controls, tests and docs.
- Placeholder scan: no unfinished implementation markers or undefined handoff placeholders are present.
- Type consistency: store actions use `moveWorkspaceClip`, `trimWorkspaceClip`, `splitWorkspaceClip` already defined in the Runtime Client; new UI emits `move`, `trim`, and `playhead` events with concrete payloads.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-16-m05-timeline-move-snap-trim.md`.

Recommended execution:

1. Subagent-Driven: dispatch independent workers for Runtime rules, store/view-model, and UI wiring, then review and integrate.
2. Inline Execution: execute task-by-task in this session with tests after each task.

## Execution Result

2026-05-17 已按 Subagent-Driven 方式完成本阶段落地：

- Runtime 已收紧 `move / trim / split` 的锁定轨道、负起点、同轨重叠、最小时长和播放头位置校验。
- 前端 Store 已接入 `playheadMs`、播放头分割、步进移动和左右裁剪。
- 时间线 UI 已开放左移、右移、左裁、右裁、播放头点击和选中片段裁剪手柄。
- 文档与 changelog 已同步本阶段能力边界。
- 验证通过：`npm --prefix apps/desktop run test`、`pytest tests/runtime/test_workspace_service.py tests/contracts/test_workspace_runtime_contract.py -q`、`npm --prefix apps/desktop run build`、`git diff --check`。
