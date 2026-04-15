# Wire Runtime Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire automation, device workspaces, publishing, renders, and review pages to the existing Runtime HTTP APIs through typed DTOs, runtime-client functions, and Pinia stores.

**Architecture:** Keep the existing Runtime client as the only HTTP boundary, add focused DTO/input/result types in `apps/desktop/src/types/runtime.ts`, add thin API wrappers in `apps/desktop/src/app/runtime-client.ts`, and keep page components consuming Pinia stores. Page templates and scoped CSS must remain unchanged; only `<script setup>` sections are changed.

**Tech Stack:** Vue 3, TypeScript, Pinia, Vite, Vitest, FastAPI Runtime JSON envelope.

---

## Context Findings

- Existing `apps/desktop/src/types/runtime.ts` DTOs use camelCase, but `apps/desktop/src/app/runtime-client.ts` has no snake_case to camelCase conversion.
- Backend schemas in `apps/py-runtime/src/schemas/*.py` expose snake_case JSON by default because no alias generator is shown in these schema files.
- To match the actual JSON response and avoid silent undefined fields, new DTOs for these five modules should use snake_case fields.
- Existing pages already reference snake_case in some templates, for example device workspaces use `root_path`, `last_used_at`, `error_count`, and `created_at`.
- Publishing and renders templates currently use camelCase UI fields such as `accountName`, `scheduledAt`, `projectName`, `fileName`, and `createdAt`; their script sections need computed view-model adapters while keeping templates unchanged.
- Review endpoint requires a `project_id`; the current review page project selector has no `v-model`. Because templates must not be modified, the implementation should load current project context via the existing dashboard context API and use that `projectId` for review operations.

## File Map

- Modify `apps/desktop/src/types/runtime.ts`: add DTO, create input, update input, and operation result types for automation, device workspaces, publishing, renders, and review.
- Modify `apps/desktop/src/app/runtime-client.ts`: import the new types and add simple HTTP wrapper functions for all listed endpoints.
- Create `apps/desktop/src/stores/automation.ts`: task list, selected runs, loading/error state, CRUD, trigger, load runs.
- Create `apps/desktop/src/stores/device-workspaces.ts`: workspace list, loading/error state, CRUD, health check.
- Create `apps/desktop/src/stores/publishing.ts`: plan list, precheck result, submit receipt, loading/error state, CRUD, precheck, submit, cancel.
- Create `apps/desktop/src/stores/renders.ts`: render task list, loading/error state, CRUD, cancel.
- Create `apps/desktop/src/stores/review.ts`: current project review summary, loading/analyzing/error state, load summary, analyze, update summary.
- Modify `apps/desktop/src/pages/automation/AutomationConsolePage.vue`: replace local mock refs and alert stubs with `useAutomationStore()`.
- Modify `apps/desktop/src/pages/devices/DeviceWorkspaceManagementPage.vue`: replace local workspace refs and alert stubs with `useDeviceWorkspacesStore()`.
- Modify `apps/desktop/src/pages/publishing/PublishingCenterPage.vue`: replace local plan refs and alert stubs with `usePublishingStore()`.
- Modify `apps/desktop/src/pages/renders/RenderExportCenterPage.vue`: replace mock render tasks and delete stub with `useRendersStore()`.
- Modify `apps/desktop/src/pages/review/ReviewOptimizationCenterPage.vue`: replace static suggestions with `useReviewStore()` plus current project context.
- Create `apps/desktop/src/app/runtime-client.spec.ts`: tests for endpoint paths, methods, query params, and JSON body behavior.
- Create `apps/desktop/src/stores/runtime-pages.spec.ts`: tests for store load/action behavior with mocked runtime-client functions.

## Naming Decision

Use snake_case for the new Runtime DTO types because the backend schemas return snake_case and the current Runtime client does not transform response keys. For page templates that already expect camelCase, create local computed view-models in the page script only; do not add business logic to `runtime-client.ts`.

## Task 1: Runtime Type Contracts

**Files:**
- Modify: `apps/desktop/src/types/runtime.ts`
- Test: `apps/desktop/src/app/runtime-client.spec.ts`

- [ ] **Step 1: Write a failing type/import coverage test**

Create `apps/desktop/src/app/runtime-client.spec.ts` with an initial import test that references functions which do not exist yet:

```typescript
import { describe, expect, it } from "vitest";
import {
  fetchAutomationTasks,
  fetchDeviceWorkspaces,
  fetchPublishPlans,
  fetchRenderTasks,
  fetchReviewSummary
} from "./runtime-client";

describe("runtime page API exports", () => {
  it("exports API functions for the five wired pages", () => {
    expect(fetchAutomationTasks).toBeTypeOf("function");
    expect(fetchDeviceWorkspaces).toBeTypeOf("function");
    expect(fetchPublishPlans).toBeTypeOf("function");
    expect(fetchRenderTasks).toBeTypeOf("function");
    expect(fetchReviewSummary).toBeTypeOf("function");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix apps/desktop run test -- runtime-client.spec.ts`

Expected: FAIL because `runtime-client.ts` does not export the five functions yet.

- [ ] **Step 3: Add Runtime DTO and input types**

Append these type groups before the existing `export type { ImportedVideo, ImportedVideoStatus } from "./video";` line in `apps/desktop/src/types/runtime.ts`:

```typescript
export type AutomationTaskCreateInput = {
  name: string;
  type: string;
  cron_expr?: string | null;
  config_json?: string | null;
};

export type AutomationTaskUpdateInput = {
  name?: string | null;
  type?: string | null;
  enabled?: boolean | null;
  cron_expr?: string | null;
  config_json?: string | null;
};

export type AutomationTaskDto = {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  cron_expr: string | null;
  last_run_at: string | null;
  last_run_status: string | null;
  run_count: number;
  config_json: string | null;
  created_at: string;
  updated_at: string;
};

export type AutomationTaskRunDto = {
  id: string;
  task_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  log_text: string | null;
  created_at: string;
};

export type TriggerTaskResultDto = {
  task_id: string;
  run_id: string;
  status: string;
  message: string;
};

export type DeviceWorkspaceCreateInput = {
  name: string;
  root_path: string;
};

export type DeviceWorkspaceUpdateInput = {
  name?: string | null;
  root_path?: string | null;
  status?: string | null;
};

export type DeviceWorkspaceDto = {
  id: string;
  name: string;
  root_path: string;
  status: string;
  error_count: number;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
};

export type HealthCheckResultDto = {
  workspace_id: string;
  status: string;
  checked_at: string;
};

export type PublishPlanCreateInput = {
  title: string;
  account_id?: string | null;
  account_name?: string | null;
  project_id?: string | null;
  video_asset_id?: string | null;
  scheduled_at?: string | null;
};

export type PublishPlanUpdateInput = {
  title?: string | null;
  account_name?: string | null;
  status?: string | null;
  scheduled_at?: string | null;
};

export type PublishPlanDto = {
  id: string;
  title: string;
  account_id: string | null;
  account_name: string | null;
  project_id: string | null;
  video_asset_id: string | null;
  status: string;
  scheduled_at: string | null;
  submitted_at: string | null;
  published_at: string | null;
  error_message: string | null;
  precheck_result_json: string | null;
  created_at: string;
  updated_at: string;
};

export type PrecheckItemResult = {
  code: string;
  label: string;
  result: string;
  message?: string | null;
};

export type PrecheckResultDto = {
  plan_id: string;
  items: PrecheckItemResult[];
  has_errors: boolean;
  checked_at: string;
};

export type SubmitPlanResultDto = {
  plan_id: string;
  status: string;
  submitted_at: string;
  message: string;
};

export type RenderTaskCreateInput = {
  project_id?: string | null;
  project_name?: string | null;
  preset?: string;
  format?: string;
};

export type RenderTaskUpdateInput = {
  preset?: string | null;
  format?: string | null;
  status?: string | null;
  progress?: number | null;
  output_path?: string | null;
  error_message?: string | null;
};

export type RenderTaskDto = {
  id: string;
  project_id: string | null;
  project_name: string | null;
  preset: string;
  format: string;
  status: string;
  progress: number;
  output_path: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CancelRenderResultDto = {
  task_id: string;
  status: string;
  message: string;
};

export type ReviewSuggestion = {
  code: string;
  category: string;
  title: string;
  description: string;
  priority: string;
};

export type ReviewSummaryUpdateInput = {
  project_name?: string | null;
  total_views?: number | null;
  total_likes?: number | null;
  total_comments?: number | null;
  avg_watch_time_sec?: number | null;
  completion_rate?: number | null;
};

export type ReviewSummaryDto = {
  id: string;
  project_id: string;
  project_name: string | null;
  total_views: number;
  total_likes: number;
  total_comments: number;
  avg_watch_time_sec: number;
  completion_rate: number;
  suggestions: ReviewSuggestion[];
  last_analyzed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AnalyzeProjectResultDto = {
  project_id: string;
  status: string;
  message: string;
  analyzed_at: string;
};
```

- [ ] **Step 4: Run the type/export test again**

Run: `npm --prefix apps/desktop run test -- runtime-client.spec.ts`

Expected: still FAIL because API functions are not implemented yet. This confirms Task 1 only added contracts.

## Task 2: Runtime Client API Wrappers

**Files:**
- Modify: `apps/desktop/src/app/runtime-client.ts`
- Test: `apps/desktop/src/app/runtime-client.spec.ts`

- [ ] **Step 1: Expand the failing runtime-client tests**

Replace `apps/desktop/src/app/runtime-client.spec.ts` with tests that mock `fetch` and verify concrete endpoint behavior:

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cancelPublishPlan,
  cancelRenderTask,
  createAutomationTask,
  createDeviceWorkspace,
  createPublishPlan,
  createRenderTask,
  deleteAutomationTask,
  deleteDeviceWorkspace,
  deletePublishPlan,
  deleteRenderTask,
  fetchAutomationTaskRuns,
  fetchAutomationTasks,
  fetchDeviceWorkspaces,
  fetchPublishPlans,
  fetchRenderTasks,
  fetchReviewSummary,
  runPublishingPrecheck,
  submitPublishPlan,
  triggerAutomationTask,
  updateReviewSummary
} from "./runtime-client";

function mockRuntimeResponse(data: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ ok: true, data })
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("runtime page API wrappers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("calls automation endpoints with filters and special operations", async () => {
    const fetchMock = mockRuntimeResponse([]);
    await fetchAutomationTasks("running", "collect");
    await createAutomationTask({ name: "每日采集", type: "collect" });
    await triggerAutomationTask("task-1");
    await fetchAutomationTaskRuns("task-1");
    await deleteAutomationTask("task-1");

    expect(fetchMock.mock.calls[0][0]).toContain("/api/automation/tasks?status=running&type=collect");
    expect(fetchMock.mock.calls[1][0]).toContain("/api/automation/tasks");
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "POST" });
    expect(fetchMock.mock.calls[2][0]).toContain("/api/automation/tasks/task-1/trigger");
    expect(fetchMock.mock.calls[3][0]).toContain("/api/automation/tasks/task-1/runs");
    expect(fetchMock.mock.calls[4][1]).toMatchObject({ method: "DELETE" });
  });

  it("calls device workspace endpoints", async () => {
    const fetchMock = mockRuntimeResponse([]);
    await fetchDeviceWorkspaces();
    await createDeviceWorkspace({ name: "PC-01", root_path: "C:/TK" });
    await deleteDeviceWorkspace("ws-1");

    expect(fetchMock.mock.calls[0][0]).toContain("/api/devices/workspaces");
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "POST" });
    expect(fetchMock.mock.calls[2][0]).toContain("/api/devices/workspaces/ws-1");
    expect(fetchMock.mock.calls[2][1]).toMatchObject({ method: "DELETE" });
  });

  it("calls publishing endpoints", async () => {
    const fetchMock = mockRuntimeResponse([]);
    await fetchPublishPlans("draft");
    await createPublishPlan({ title: "发布计划" });
    await runPublishingPrecheck("plan-1");
    await submitPublishPlan("plan-1");
    await cancelPublishPlan("plan-1");
    await deletePublishPlan("plan-1");

    expect(fetchMock.mock.calls[0][0]).toContain("/api/publishing/plans?status=draft");
    expect(fetchMock.mock.calls[2][0]).toContain("/api/publishing/plans/plan-1/precheck");
    expect(fetchMock.mock.calls[3][0]).toContain("/api/publishing/plans/plan-1/submit");
    expect(fetchMock.mock.calls[4][0]).toContain("/api/publishing/plans/plan-1/cancel");
    expect(fetchMock.mock.calls[5][1]).toMatchObject({ method: "DELETE" });
  });

  it("calls render endpoints", async () => {
    const fetchMock = mockRuntimeResponse([]);
    await fetchRenderTasks("running");
    await createRenderTask({ project_name: "测试项目", preset: "1080p", format: "mp4" });
    await cancelRenderTask("render-1");
    await deleteRenderTask("render-1");

    expect(fetchMock.mock.calls[0][0]).toContain("/api/renders/tasks?status=running");
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "POST" });
    expect(fetchMock.mock.calls[2][0]).toContain("/api/renders/tasks/render-1/cancel");
    expect(fetchMock.mock.calls[3][1]).toMatchObject({ method: "DELETE" });
  });

  it("calls review endpoints", async () => {
    const fetchMock = mockRuntimeResponse({ id: "summary-1" });
    await fetchReviewSummary("project-1");
    await updateReviewSummary("project-1", { total_views: 100 });

    expect(fetchMock.mock.calls[0][0]).toContain("/api/review/projects/project-1/summary");
    expect(fetchMock.mock.calls[1][0]).toContain("/api/review/projects/project-1/summary");
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "PATCH" });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix apps/desktop run test -- runtime-client.spec.ts`

Expected: FAIL because the imported API wrappers do not exist.

- [ ] **Step 3: Add imports for new Runtime types**

Update the `import type { ... } from "@/types/runtime";` block in `apps/desktop/src/app/runtime-client.ts` to include every new type used by the API wrappers.

- [ ] **Step 4: Add thin Runtime API wrappers**

Add sections after the Accounts functions and before `requestRuntime<T>()`. Use this implementation shape:

```typescript
// Automation
export async function fetchAutomationTasks(status?: string, type?: string): Promise<AutomationTaskDto[]> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (type) params.append("type", type);
  const query = params.toString();
  return requestRuntime<AutomationTaskDto[]>(`/api/automation/tasks${query ? `?${query}` : ""}`);
}

export async function createAutomationTask(input: AutomationTaskCreateInput): Promise<AutomationTaskDto> {
  return requestRuntime<AutomationTaskDto>("/api/automation/tasks", {
    body: JSON.stringify(input),
    method: "POST"
  });
}
```

Continue the same pattern for:

- `fetchAutomationTask(id)`
- `updateAutomationTask(id, input)`
- `deleteAutomationTask(id)`
- `triggerAutomationTask(id)`
- `fetchAutomationTaskRuns(id)`
- `fetchDeviceWorkspaces()`
- `createDeviceWorkspace(input)`
- `fetchDeviceWorkspace(id)`
- `updateDeviceWorkspace(id, input)`
- `deleteDeviceWorkspace(id)`
- `checkDeviceWorkspaceHealth(id)`
- `fetchPublishPlans(status?)`
- `createPublishPlan(input)`
- `fetchPublishPlan(id)`
- `updatePublishPlan(id, input)`
- `deletePublishPlan(id)`
- `runPublishingPrecheck(id)`
- `submitPublishPlan(id)`
- `cancelPublishPlan(id)`
- `fetchRenderTasks(status?)`
- `createRenderTask(input)`
- `fetchRenderTask(id)`
- `updateRenderTask(id, input)`
- `deleteRenderTask(id)`
- `cancelRenderTask(id)`
- `fetchReviewSummary(projectId)`
- `analyzeReviewProject(projectId)`
- `updateReviewSummary(projectId, input)`

- [ ] **Step 5: Run runtime-client tests**

Run: `npm --prefix apps/desktop run test -- runtime-client.spec.ts`

Expected: PASS.

## Task 3: Pinia Stores

**Files:**
- Create: `apps/desktop/src/stores/automation.ts`
- Create: `apps/desktop/src/stores/device-workspaces.ts`
- Create: `apps/desktop/src/stores/publishing.ts`
- Create: `apps/desktop/src/stores/renders.ts`
- Create: `apps/desktop/src/stores/review.ts`
- Test: `apps/desktop/src/stores/runtime-pages.spec.ts`

- [ ] **Step 1: Write failing store tests**

Create `apps/desktop/src/stores/runtime-pages.spec.ts` that mocks `@/app/runtime-client` and asserts each store loads items and sets error on rejected load.

```typescript
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

vi.mock("@/app/runtime-client", () => ({
  fetchAutomationTasks: vi.fn(),
  createAutomationTask: vi.fn(),
  triggerAutomationTask: vi.fn(),
  fetchAutomationTaskRuns: vi.fn(),
  deleteAutomationTask: vi.fn(),
  fetchDeviceWorkspaces: vi.fn(),
  createDeviceWorkspace: vi.fn(),
  checkDeviceWorkspaceHealth: vi.fn(),
  deleteDeviceWorkspace: vi.fn(),
  fetchPublishPlans: vi.fn(),
  createPublishPlan: vi.fn(),
  runPublishingPrecheck: vi.fn(),
  submitPublishPlan: vi.fn(),
  cancelPublishPlan: vi.fn(),
  fetchRenderTasks: vi.fn(),
  createRenderTask: vi.fn(),
  deleteRenderTask: vi.fn(),
  cancelRenderTask: vi.fn(),
  fetchReviewSummary: vi.fn(),
  analyzeReviewProject: vi.fn(),
  updateReviewSummary: vi.fn()
}));

describe("runtime page stores", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("loads automation tasks", async () => {
    const client = await import("@/app/runtime-client");
    vi.mocked(client.fetchAutomationTasks).mockResolvedValue([{ id: "task-1", name: "采集", type: "collect", enabled: true, cron_expr: null, last_run_at: null, last_run_status: null, run_count: 0, config_json: null, created_at: "2026-04-15", updated_at: "2026-04-15" }]);
    const { useAutomationStore } = await import("./automation");
    const store = useAutomationStore();
    await store.loadTasks();
    expect(store.tasks).toHaveLength(1);
    expect(store.error).toBeNull();
  });

  it("records device workspace load errors", async () => {
    const client = await import("@/app/runtime-client");
    vi.mocked(client.fetchDeviceWorkspaces).mockRejectedValue(new Error("加载失败"));
    const { useDeviceWorkspacesStore } = await import("./device-workspaces");
    const store = useDeviceWorkspacesStore();
    await store.loadWorkspaces();
    expect(store.error).toBe("加载失败");
    expect(store.loading).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm --prefix apps/desktop run test -- runtime-pages.spec.ts`

Expected: FAIL because the five store files do not exist.

- [ ] **Step 3: Create store files**

Implement each store with:

- State fields: primary array or summary, `loading: false`, `error: null as string | null`.
- Actions wrapping runtime-client calls in `try/catch/finally`.
- Error conversion helper local to each store or repeated minimal expression: `this.error = e instanceof Error ? e.message : "操作失败";`.
- Reload list after create/update/delete/special operations where the UI needs current state.

Store action names:

- Automation: `loadTasks`, `addTask`, `updateTask`, `removeTask`, `triggerTask`, `loadRuns`.
- Device workspaces: `loadWorkspaces`, `addWorkspace`, `updateWorkspace`, `removeWorkspace`, `checkHealth`.
- Publishing: `loadPlans`, `addPlan`, `updatePlan`, `removePlan`, `precheck`, `submit`, `cancel`.
- Renders: `loadTasks`, `addTask`, `updateTask`, `removeTask`, `cancel`.
- Review: `loadSummary`, `analyze`, `updateSummary`.

- [ ] **Step 4: Run store tests**

Run: `npm --prefix apps/desktop run test -- runtime-pages.spec.ts`

Expected: PASS.

## Task 4: Page Script Wiring

**Files:**
- Modify: `apps/desktop/src/pages/automation/AutomationConsolePage.vue`
- Modify: `apps/desktop/src/pages/devices/DeviceWorkspaceManagementPage.vue`
- Modify: `apps/desktop/src/pages/publishing/PublishingCenterPage.vue`
- Modify: `apps/desktop/src/pages/renders/RenderExportCenterPage.vue`
- Modify: `apps/desktop/src/pages/review/ReviewOptimizationCenterPage.vue`
- Test: existing build plus store tests.

- [ ] **Step 1: Update Automation script only**

Replace local `tasks = ref<AutoTask[]>([])` with `const automationStore = useAutomationStore();` and `const tasks = computed(() => automationStore.tasks);`. Add `onMounted(() => automationStore.loadTasks())`. Replace `handleRunTask` with `await automationStore.triggerTask(id)`. Replace `handleCreateTask` with `await automationStore.addTask({ name: addForm.value.name, type: addForm.value.type })`, then clear the form and close the drawer.

- [ ] **Step 2: Update Device Workspace script only**

Use `useDeviceWorkspacesStore()`, expose `workspaces` as a computed store array, load on mounted, create with `{ name, root_path }`, health check with selected ID, and delete with selected ID. Preserve the existing `statusLabel` function and all template field names.

- [ ] **Step 3: Update Publishing script only**

Use `usePublishingStore()`, load plans on mounted, and create a local computed view-model array:

```typescript
const plans = computed(() => publishingStore.plans.map((plan) => ({
  id: plan.id,
  title: plan.title,
  accountName: plan.account_name ?? "",
  scheduledAt: plan.scheduled_at,
  status: plan.status
})));
```

Use `publishingStore.precheckResult?.items` for `precheckItems`, falling back to pending items. Implement create, precheck, submit, and cancel through store actions.

- [ ] **Step 4: Update Render script only**

Use `useRendersStore()`, load tasks on mounted, and create a local computed view-model array matching the existing template shape:

```typescript
const tasks = computed(() => rendersStore.tasks.map((task) => ({
  id: task.id,
  projectName: task.project_name ?? "未命名项目",
  fileName: task.output_path?.split(/[\\/]/).pop() || `${task.id}.${task.format}`,
  status: task.status === "succeeded" ? "completed" : task.status === "queued" ? "pending" : task.status,
  progress: task.progress,
  format: task.format.toUpperCase(),
  duration: task.finished_at && task.started_at ? "已完成" : "处理中",
  createdAt: task.created_at,
  logs: task.error_message ? [{ time: task.updated_at, msg: task.error_message }] : []
})));
```

Replace delete with `await rendersStore.removeTask(id)`. For new task, call `rendersStore.addTask({ preset: "1080p", format: "mp4" })`.

- [ ] **Step 5: Update Review script only**

Use `useReviewStore()` and existing `fetchCurrentProjectContext()` from runtime-client. On mount, load current project context and then call `reviewStore.loadSummary(projectId)`. Map `reviewStore.summary?.suggestions` to the existing `Suggestion` shape by using `code` as `id`. Replace analyze with `reviewStore.analyze(projectId)`. Keep apply/ignore local because no backend endpoint exists for accepting or dismissing suggestions.

- [ ] **Step 6: Run focused tests**

Run: `npm --prefix apps/desktop run test -- runtime-client.spec.ts runtime-pages.spec.ts`

Expected: PASS.

## Task 5: Full Verification

**Files:**
- No new files.

- [ ] **Step 1: Run all frontend tests**

Run: `npm --prefix apps/desktop run test`

Expected: PASS.

- [ ] **Step 2: Run desktop build**

Run: `npm --prefix apps/desktop run build`

Expected: PASS with no unresolved imports or TypeScript errors.

- [ ] **Step 3: Inspect git diff boundaries**

Run: `git diff -- apps/desktop/src/types/runtime.ts apps/desktop/src/app/runtime-client.ts apps/desktop/src/stores apps/desktop/src/pages/automation/AutomationConsolePage.vue apps/desktop/src/pages/devices/DeviceWorkspaceManagementPage.vue apps/desktop/src/pages/publishing/PublishingCenterPage.vue apps/desktop/src/pages/renders/RenderExportCenterPage.vue apps/desktop/src/pages/review/ReviewOptimizationCenterPage.vue`

Expected: Page diffs only touch `<script setup>` sections. No backend files, templates, or scoped CSS are modified.

## Rollback Point

If the build fails because existing page templates contain unrelated mojibake or malformed strings, do not broaden the task into template/CSS rewriting. First report the exact pre-existing parse errors, then ask whether the page text corruption should be repaired under a separate approved plan because the current task explicitly forbids template changes.

## Approval Gate

Implementation must not begin until this plan is approved, per `AGENTS.md` section 14.

