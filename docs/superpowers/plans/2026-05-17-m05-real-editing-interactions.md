# M05 真实编辑交互 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 M05 剪辑台支持真实鼠标拖拽移动、拖拽裁剪、资产入轨/替换、播放器联动和可定位预检。

**Architecture:** 前端拆出时间线几何、磁吸和拖拽 composable，页面组件只负责渲染与事件转发。Runtime 继续作为时间线修改唯一业务入口，负责素材合法性、锁定轨道、重叠、最小时长和保存结果校验。每个任务完成后独立测试、独立提交。

**Tech Stack:** Vue 3 + Pinia + TypeScript + Vitest；Python + FastAPI + Pydantic + pytest；Runtime HTTP JSON 信封。

---

## Scope

实现内容：

- 拆分时间线几何、磁吸、拖拽交互边界，控制单文件继续膨胀。
- 支持同轨片段拖拽移动和基础磁吸预览。
- 支持左右边缘拖拽裁剪和失败回滚。
- 支持资产中心素材加入时间线、替换选中片段。
- 支持播放器、属性面板、预检结果与当前片段联动。
- 每个任务完成后汇报、测试、提交。

不做内容：

- 不做跨轨自由拖拽。
- 不做撤销、重做、多选、组合。
- 不做真实媒体文件切割。
- 不做贴纸、滤镜、转场、关键帧、复杂混音。
- 不绕过 Runtime 或资产中心。

## File Map

Frontend helpers and composables:

- Create: `apps/desktop/src/modules/workspace/workspaceTimelineGeometry.ts`
- Create: `apps/desktop/src/modules/workspace/workspaceTimelineSnap.ts`
- Create: `apps/desktop/src/modules/workspace/useWorkspaceTimelineDrag.ts`
- Modify: `apps/desktop/src/modules/workspace/workspaceTimelineViewModel.ts`
- Test: `apps/desktop/tests/workspace-timeline-geometry.spec.ts`
- Test: `apps/desktop/tests/workspace-timeline-drag.spec.ts`
- Test: `apps/desktop/tests/workspace-timeline-view-model.spec.ts`

Frontend UI and state:

- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimelineToolbar.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspacePreviewStage.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/stores/editing-workspace.ts`
- Modify: `apps/desktop/src/types/runtime.ts`
- Modify: `apps/desktop/src/app/runtime-client.ts`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`
- Test: `apps/desktop/tests/workspace-asset-rail.spec.ts`
- Test: `apps/desktop/tests/workspace-layout-contract.spec.ts`

Runtime:

- Modify: `apps/py-runtime/src/schemas/workspace.py`
- Modify: `apps/py-runtime/src/api/routes/workspace.py`
- Modify: `apps/py-runtime/src/services/workspace_service.py`
- Test: `tests/runtime/test_workspace_service.py`
- Test: `tests/contracts/test_workspace_runtime_contract.py`

Docs:

- Modify: `docs/RUNTIME-API-CALLS.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/plans/2026-05-17-m05-real-editing-interactions.md`

Release metadata:

- Modify: `package.json`
- Modify via `npm run version:sync`: `apps/desktop/src-tauri/Cargo.toml`
- Modify via `npm run version:sync`: `apps/desktop/src-tauri/tauri.conf.json`
- Modify via `npm run version:sync`: `apps/py-runtime/pyproject.toml`

## Execution Record

| Task | Commit | Status |
| --- | --- | --- |
| Task 0 计划与设计 | `d4cfdbe` | 已提交 |
| Task 1 时间线几何与磁吸 | `e11ac8e` | 已提交 |
| Task 2 拖拽状态拆分 | `db45801` | 已提交 |
| Task 3 拖拽移动保存 | `23a4e8f` | 已提交 |
| Task 4 拖拽裁剪保存 | `5bd4756` | 已提交 |
| Task 5 Runtime 资产入轨 | `a674ea2` | 已提交 |
| Task 6 前端资产加入与替换 | `be2e1a2` | 已提交 |
| Task 7 播放器、属性面板与预检定位 | `0c42ec0` | 已提交 |
| Task 8 文档、发布号与全量验证 | `8b38d28` / `7c8b9f8` | 已提交 |
| Task 9 素材栏密度与时间轴选择稳定性收口 | `5d5fea4` / `bc2b73d` / `8f12b0f` / `fcd7083` / `07c39ad` / `be037dd` | 已提交 |

## Verification Record

- `npm --prefix apps/desktop run test`：53 个测试文件、245 条测试通过。
- `pytest tests/runtime/test_workspace_service.py tests/contracts/test_workspace_runtime_contract.py -q`：36 条测试通过，保留现有 pytest 配置警告。
- `pytest tests/contracts/test_runtime_contract_inventory.py -q`：2 条测试通过，HTTP 文档路由与代码路由一致。
- `npm --prefix apps/desktop run build`：Vite 构建通过。
- `npm run version:check`：发布号镜像检查通过。
- `git diff --check`：无空白错误。
- 2026-05-17 收口复核：真实浏览器在 `/workspace/editing` 复核时间轴选中与素材栏 Tab 切换，未复现选中态闪动或上方面板跳动。

## Task 0: 计划、设计与分支基线

**Files:**

- Create: `docs/superpowers/specs/2026-05-17-m05-real-editing-interactions-design.md`
- Create: `docs/superpowers/plans/2026-05-17-m05-real-editing-interactions.md`

- [ ] **Step 1: Create branch**

Run:

```powershell
git checkout -b codex/m05-real-editing-interactions
```

Expected: branch is `codex/m05-real-editing-interactions`.

- [ ] **Step 2: Save design and implementation plan**

Create the spec and this plan. The documents must define scope, architecture, file map, task order, verification and commit policy.

- [ ] **Step 3: Verify documentation-only diff**

Run:

```powershell
git diff --check
git status --short --branch
```

Expected: only the two new M05 docs are staged or modified, except existing untracked local notes that must stay uncommitted.

- [ ] **Step 4: Commit Task 0**

Run:

```powershell
git add docs/superpowers/specs/2026-05-17-m05-real-editing-interactions-design.md docs/superpowers/plans/2026-05-17-m05-real-editing-interactions.md
git commit -m "docs: 规划 M05 真实编辑交互"
```

Expected: documentation commit succeeds.

## Task 1: 拆分时间线几何与磁吸计算

**Files:**

- Create: `apps/desktop/src/modules/workspace/workspaceTimelineGeometry.ts`
- Create: `apps/desktop/src/modules/workspace/workspaceTimelineSnap.ts`
- Modify: `apps/desktop/src/modules/workspace/workspaceTimelineViewModel.ts`
- Test: `apps/desktop/tests/workspace-timeline-geometry.spec.ts`
- Test: `apps/desktop/tests/workspace-timeline-view-model.spec.ts`

- [ ] **Step 1: Add failing geometry tests**

Create tests for `msToPercent`, `percentToMs`, `clientXToTimelineMs`, and clamping. The tests must cover 0ms, duration end, negative input and values beyond duration.

- [ ] **Step 2: Add failing snap tests**

Add tests for snap candidates from clip starts, clip ends, playhead and zero. Expected behavior: within threshold returns the candidate; outside threshold returns original value.

- [ ] **Step 3: Implement geometry helper**

Create pure functions with no DOM mutation:

- `clampTimelineMs(value, durationMs)`
- `msToPercent(value, durationMs)`
- `percentToMs(percent, durationMs)`
- `clientXToTimelineMs(clientX, rect, durationMs)`

- [ ] **Step 4: Implement snap helper**

Create pure functions:

- `buildSnapCandidates(clips, options)`
- `resolveTimelineSnap(desiredMs, candidates, thresholdMs)`

Keep existing `resolveSnapStartMs` as a compatibility wrapper that delegates to the new helper.

- [ ] **Step 5: Verify and commit Task 1**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/workspace-timeline-geometry.spec.ts tests/workspace-timeline-view-model.spec.ts
git diff --check
git add apps/desktop/src/modules/workspace/workspaceTimelineGeometry.ts apps/desktop/src/modules/workspace/workspaceTimelineSnap.ts apps/desktop/src/modules/workspace/workspaceTimelineViewModel.ts apps/desktop/tests/workspace-timeline-geometry.spec.ts apps/desktop/tests/workspace-timeline-view-model.spec.ts
git commit -m "feat: 拆分 M05 时间线几何与磁吸计算"
```

## Task 2: 拆分拖拽交互状态

**Files:**

- Create: `apps/desktop/src/modules/workspace/useWorkspaceTimelineDrag.ts`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Test: `apps/desktop/tests/workspace-timeline-drag.spec.ts`
- Test: `apps/desktop/tests/workspace-layout-contract.spec.ts`

- [ ] **Step 1: Add failing drag-state tests**

Test start, update, finish and cancel states for move and trim gestures. The composable must return a preview object and never call Runtime directly.

- [ ] **Step 2: Implement drag composable**

Create `useWorkspaceTimelineDrag` with:

- `dragPreview`
- `startMoveDrag`
- `startTrimDrag`
- `updateDrag`
- `finishDrag`
- `cancelDrag`

The composable receives pure callbacks for geometry, snap and event emission.

- [ ] **Step 3: Wire passive timeline events**

Modify `WorkspaceTimeline.vue` to emit:

- `move-preview`
- `move-commit`
- `trim-preview`
- `trim-commit`
- `drag-cancel`

Do not call store or Runtime from the component.

- [ ] **Step 4: Verify and commit Task 2**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/workspace-timeline-drag.spec.ts tests/workspace-layout-contract.spec.ts
git diff --check
git add apps/desktop/src/modules/workspace/useWorkspaceTimelineDrag.ts apps/desktop/src/modules/workspace/WorkspaceTimeline.vue apps/desktop/tests/workspace-timeline-drag.spec.ts apps/desktop/tests/workspace-layout-contract.spec.ts
git commit -m "feat: 拆分 M05 时间线拖拽状态"
```

## Task 3: 实现拖拽移动保存与失败回滚

**Files:**

- Modify: `apps/desktop/src/stores/editing-workspace.ts`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: Add failing store tests**

Add tests that commit a move preview to Runtime, then verify:

- success refreshes timeline and keeps selected clip.
- failure clears saving status and preserves original timeline.
- locked-track errors are shown in Chinese.

- [ ] **Step 2: Implement store action**

Add `commitMovePreview(payload)` to call existing `moveWorkspaceClip`. The action must set `status="saving"` during the request and clear preview state after completion.

- [ ] **Step 3: Wire page handlers**

`AIEditingWorkspacePage.vue` receives `move-commit` from `WorkspaceTimeline.vue`, calls the store action, then updates precheck state if a timeline exists.

- [ ] **Step 4: Verify and commit Task 3**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/editing-workspace-store.spec.ts tests/ai-editing-workspace-page.spec.ts
git diff --check
git add apps/desktop/src/stores/editing-workspace.ts apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue apps/desktop/src/modules/workspace/WorkspaceTimeline.vue apps/desktop/tests/editing-workspace-store.spec.ts apps/desktop/tests/ai-editing-workspace-page.spec.ts
git commit -m "feat: 接入 M05 片段拖拽移动保存"
```

## Task 4: 实现拖拽裁剪保存与失败回滚

**Files:**

- Modify: `apps/desktop/src/stores/editing-workspace.ts`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`
- Test: `apps/desktop/tests/workspace-timeline-drag.spec.ts`

- [ ] **Step 1: Add failing trim tests**

Add tests for left-edge and right-edge drag commits. Cover minimum duration, negative start prevention and Runtime error rollback.

- [ ] **Step 2: Implement store action**

Add `commitTrimPreview(payload)` to call `trimWorkspaceClip`. The input must match existing Runtime contract:

- left edge: `startMs`, `durationMs`, `inPointMs`
- right edge: `durationMs`

- [ ] **Step 3: Wire UI preview labels**

Show a compact preview label for start, end and duration while trimming.

- [ ] **Step 4: Verify and commit Task 4**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/editing-workspace-store.spec.ts tests/workspace-timeline-drag.spec.ts
git diff --check
git add apps/desktop/src/stores/editing-workspace.ts apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue apps/desktop/src/modules/workspace/WorkspaceTimeline.vue apps/desktop/tests/editing-workspace-store.spec.ts apps/desktop/tests/workspace-timeline-drag.spec.ts
git commit -m "feat: 接入 M05 片段拖拽裁剪保存"
```

## Task 5: Runtime 资产入轨与替换规则

**Files:**

- Modify: `apps/py-runtime/src/schemas/workspace.py`
- Modify: `apps/py-runtime/src/api/routes/workspace.py`
- Modify: `apps/py-runtime/src/services/workspace_service.py`
- Modify: `apps/desktop/src/types/runtime.ts`
- Modify: `apps/desktop/src/app/runtime-client.ts`
- Test: `tests/runtime/test_workspace_service.py`
- Test: `tests/contracts/test_workspace_runtime_contract.py`
- Test: `apps/desktop/tests/runtime-client-workspace.spec.ts`

- [ ] **Step 1: Add failing Runtime tests**

Add tests for inserting a video asset at playhead, inserting audio at track end, rejecting unavailable assets, and replacing a selected video clip.

- [ ] **Step 2: Add schema and route**

Add:

- `ClipInsertAssetInput`
- `POST /api/workspace/timelines/{timeline_id}/clips/insert-asset`

Keep `replace_clip` as the replacement endpoint and tighten asset validation there.

- [ ] **Step 3: Implement Runtime service**

Add `insert_asset_clip(timeline_id, payload)`:

- resolve asset by ID.
- choose target track by asset type.
- choose start by requested `startMs` or target track end.
- reject overlap, locked track and unavailable source.
- save and return `WorkspaceTimelineResultDto`.

- [ ] **Step 4: Add frontend client types**

Add `insertWorkspaceAssetClip(timelineId, input)` and corresponding TypeScript input type.

- [ ] **Step 5: Verify and commit Task 5**

Run:

```powershell
pytest tests/runtime/test_workspace_service.py tests/contracts/test_workspace_runtime_contract.py -q
npm --prefix apps/desktop run test -- tests/runtime-client-workspace.spec.ts
git diff --check
git add apps/py-runtime/src/schemas/workspace.py apps/py-runtime/src/api/routes/workspace.py apps/py-runtime/src/services/workspace_service.py apps/desktop/src/types/runtime.ts apps/desktop/src/app/runtime-client.ts tests/runtime/test_workspace_service.py tests/contracts/test_workspace_runtime_contract.py apps/desktop/tests/runtime-client-workspace.spec.ts
git commit -m "feat: 接入 M05 资产入轨 Runtime 能力"
```

## Task 6: 前端资产加入与替换闭环

**Files:**

- Modify: `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`
- Modify: `apps/desktop/src/stores/editing-workspace.ts`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Test: `apps/desktop/tests/workspace-asset-rail.spec.ts`
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: Add failing asset UI tests**

Tests must cover:

- asset tab renders current project assets.
- “加入时间线” emits insert event.
- “替换片段” is enabled only when a compatible clip is selected.
- unavailable asset shows disabled action with Chinese reason.

- [ ] **Step 2: Implement store actions**

Add:

- `insertAssetAtPlayhead(assetId)`
- `replaceSelectedClipWithAsset(assetId)`

Both actions call Runtime client, refresh timeline and show visible errors.

- [ ] **Step 3: Wire asset rail events**

`WorkspaceAssetRail.vue` emits asset insert and replace events. Page calls store actions and refreshes precheck.

- [ ] **Step 4: Verify and commit Task 6**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/workspace-asset-rail.spec.ts tests/editing-workspace-store.spec.ts tests/ai-editing-workspace-page.spec.ts
git diff --check
git add apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue apps/desktop/src/stores/editing-workspace.ts apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue apps/desktop/tests/workspace-asset-rail.spec.ts apps/desktop/tests/editing-workspace-store.spec.ts apps/desktop/tests/ai-editing-workspace-page.spec.ts
git commit -m "feat: 接入 M05 资产加入与替换交互"
```

## Task 7: 播放器、属性面板和预检定位联动

**Files:**

- Modify: `apps/desktop/src/modules/workspace/WorkspacePreviewStage.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`
- Modify: `apps/desktop/src/stores/editing-workspace.ts`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/types/runtime.ts`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
- Test: `apps/desktop/tests/workspace-layout-contract.spec.ts`

- [ ] **Step 1: Add failing integration tests**

Tests must cover:

- playback context follows playhead.
- selecting audio/subtitle/video clips changes preview text.
- precheck issue can select target clip or track.
- inspector save state is visible during Runtime action.

- [ ] **Step 2: Implement preview context helper**

Keep logic outside the component. Compute current clip by playhead and selected clip, then pass display context to `WorkspacePreviewStage.vue`.

- [ ] **Step 3: Implement precheck target selection**

Store exposes `focusPrecheckIssue(issue)` and selects the corresponding clip or track when metadata exists.

- [ ] **Step 4: Verify and commit Task 7**

Run:

```powershell
npm --prefix apps/desktop run test -- tests/ai-editing-workspace-page.spec.ts tests/workspace-layout-contract.spec.ts
git diff --check
git add apps/desktop/src/modules/workspace/WorkspacePreviewStage.vue apps/desktop/src/modules/workspace/WorkspaceInspector.vue apps/desktop/src/stores/editing-workspace.ts apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue apps/desktop/src/types/runtime.ts apps/desktop/tests/ai-editing-workspace-page.spec.ts apps/desktop/tests/workspace-layout-contract.spec.ts
git commit -m "feat: 联动 M05 播放器属性与预检定位"
```

## Task 8: Final verification and docs

**Files:**

- Modify: `docs/RUNTIME-API-CALLS.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/plans/2026-05-17-m05-real-editing-interactions.md`
- Modify: `package.json`
- Modify via `npm run version:sync`: `apps/desktop/src-tauri/Cargo.toml`
- Modify via `npm run version:sync`: `apps/desktop/src-tauri/tauri.conf.json`
- Modify via `npm run version:sync`: `apps/py-runtime/pyproject.toml`

- [x] **Step 1: Update Runtime API docs**

Document asset insert, drag move/trim behavior, error codes and frontend callers.

- [x] **Step 2: Update changelog**

Add one M05 entry covering drag move, drag trim, asset insert/replace and precheck targeting.

- [x] **Step 3: Sync release metadata**

Set the root release number for this phase and run:

```powershell
npm run version:sync
```

Expected: Tauri and Python Runtime mirrors match the root release number.

- [x] **Step 4: Run full verification**

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

- [x] **Step 5: Commit Task 8**

Run:

```powershell
git add docs/RUNTIME-API-CALLS.md CHANGELOG.md docs/superpowers/plans/2026-05-17-m05-real-editing-interactions.md package.json apps/desktop/src-tauri/Cargo.toml apps/desktop/src-tauri/tauri.conf.json apps/py-runtime/pyproject.toml
git commit -m "docs: 更新 M05 真实编辑交互说明"
```

## Execution Policy

- 每完成一个任务，必须汇报状态、测试结果和提交 SHA。
- 每个任务提交前必须运行该任务列出的测试和 `git diff --check`。
- `.superpowers/` 与未确认的 V2 参考方案文档不纳入提交。
- 子代理可以实现独立任务；主代理必须进行范围复核、测试复核和提交复核。
