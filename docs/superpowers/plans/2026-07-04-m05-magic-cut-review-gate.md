# M05 Magic Cut Review Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 M05 智能粗剪从“AI 生成后直接修改时间线”改为“AI 生成可审阅建议，用户确认后才应用到时间线”。

**Architecture:** Runtime 将 `magic_cut` 拆成生成建议草稿与确认应用两个阶段。建议草稿独立持久化，不写入 `tracks_json`，确认应用时复用现有 `delete_clip` / `trim_clip` / `move_clip` / `split_clip` 原子操作并保留失败可追踪结果。前端继续通过 Runtime adapter 和 Pinia store 发起请求，右侧基础属性中的 AI 建议区负责审阅与确认，预览和时间线只显示轻量影响提示。

**Tech Stack:** Python + FastAPI + SQLAlchemy + SQLite Runtime；Vue 3 + TypeScript + Pinia + Vitest Desktop。

---

## Approval Gate

本计划改变 Runtime 契约和现有测试预期。根据 `AGENTS.md`，必须先获得本计划批准，再补充对应 design spec，最后进入实现。未经批准不得直接修改生产代码。

## Evidence Used

- `docs/superpowers/specs/2026-05-15-m05-basic-editing-workbench-ui-design.md` 明确要求 AI 建议不能直接修改时间线，必须先审阅确认。
- `apps/py-runtime/src/services/workspace_service.py:487` 当前 `run_ai_command` 在后台任务内直接调用 `apply_magic_cut_operations`。
- `apps/py-runtime/src/services/magic_cut.py:131` 当前 `apply_magic_cut_operations` 直接执行时间线原子操作并落盘。
- `tests/runtime/test_workspace_service.py:1322` 当前断言 `magic_cut` 会直接修改并持久化时间线。
- `apps/desktop/src/modules/workspace/WorkspaceInspector.vue` 当前 AI 建议区只显示 `lastCommandResult.message`，没有建议列表和确认入口。

## File Map

### Runtime

- Create: `apps/py-runtime/src/domain/models/magic_cut.py`
  - 持久化智能粗剪建议草稿。
- Create: `apps/py-runtime/src/repositories/magic_cut_repository.py`
  - 读写当前项目、当前时间线的最新建议草稿。
- Create: `apps/py-runtime/src/services/magic_cut_suggestion_service.py`
  - 生成建议草稿、读取建议草稿、应用建议草稿。
- Modify: `apps/py-runtime/src/domain/models/__init__.py`
  - 导出新 ORM 模型。
- Modify: `apps/py-runtime/src/persistence/engine.py`
  - 补齐本地 SQLite 自修复建表逻辑。
- Modify: `apps/py-runtime/src/api/routes/workspace.py`
  - 保留 `/ai-commands` 生成入口，新增读取和应用建议入口。
- Modify: `apps/py-runtime/src/schemas/workspace.py`
  - 增加建议、应用输入、应用结果 DTO。
- Modify: `apps/py-runtime/src/services/workspace_service.py`
  - `magic_cut` 任务只生成建议草稿，不直接应用时间线。
- Modify: `apps/py-runtime/src/services/magic_cut.py`
  - 保留解析与应用函数，新增 suggestion normalization helper。
- Test: `tests/runtime/test_workspace_service.py`
  - 将直接应用断言改为生成建议草稿断言，新增确认应用断言。
- Test: `tests/contracts/test_workspace_runtime_contract.py`
  - 登记新接口和错误信封。

### Desktop

- Modify: `apps/desktop/src/types/runtime.ts`
  - 增加建议 DTO 类型。
- Modify: `apps/desktop/src/app/runtime-client.ts`
  - 增加读取、应用、忽略建议接口封装。
- Modify: `apps/desktop/src/stores/editing-workspace.ts`
  - 保存 `magicCutSuggestion` 状态，生成成功后加载建议，不刷新时间线。
- Modify: `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`
  - AI 建议区显示建议数量、列表、应用/忽略入口。
- Create: `apps/desktop/src/modules/workspace/WorkspaceMagicCutSuggestions.vue`
  - 聚焦建议卡片和确认动作，避免继续膨胀 `WorkspaceInspector.vue`。
- Modify: `apps/desktop/src/modules/workspace/WorkspaceCommandFeedbackBar.vue`
  - 生成完成时显示“查看 AI 建议”，不表达“已应用”。
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
  - 接线应用建议、忽略建议、定位建议影响片段。
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`
  - 覆盖生成建议、应用建议、失败保留原时间线。
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
  - 覆盖右侧建议区审阅与确认。
- Test: `apps/desktop/tests/workspace-command-feedback.spec.ts`
  - 覆盖生成完成文案和查看建议入口。

### Docs

- Modify: `docs/RUNTIME-API-CALLS.md`
  - 登记新接口、请求参数、返回结果、错误码、示例。
- Modify: `docs/PROJECT-STATUS.md`
  - 更新 M05 智能粗剪状态。

## Data Contract

### Runtime DTO Shape

```python
class MagicCutSuggestionOperationDto(BaseModel):
    id: str
    action: str
    clipId: str
    trackId: str | None = None
    targetTrackId: str | None = None
    originalStartMs: int | None = None
    originalDurationMs: int | None = None
    suggestedStartMs: int | None = None
    suggestedDurationMs: int | None = None
    splitAtMs: int | None = None
    reason: str
    risk: str | None = None


class MagicCutSuggestionDraftDto(BaseModel):
    id: str
    projectId: str
    timelineId: str
    timelineVersionToken: str
    status: str
    summary: str
    operations: list[MagicCutSuggestionOperationDto]
    createdAt: str
    updatedAt: str
    appliedAt: str | None = None


class MagicCutSuggestionApplyInput(BaseModel):
    operationIds: list[str] = Field(default_factory=list)
    confirmTimelineVersionToken: str
```

### Runtime Routes

```text
POST /api/workspace/projects/{project_id}/ai-commands
GET  /api/workspace/projects/{project_id}/magic-cut-suggestions/latest?timelineId={timeline_id}
POST /api/workspace/magic-cut-suggestions/{suggestion_id}/apply
POST /api/workspace/magic-cut-suggestions/{suggestion_id}/dismiss
```

### Error Codes

| Code | Meaning | User Message |
| --- | --- | --- |
| `workspace.magic_cut_suggestion_not_found` | 建议草稿不存在或不属于当前项目 | 智能粗剪建议不存在，请重新生成。 |
| `workspace.magic_cut_timeline_changed` | 用户确认时的时间线版本已变化 | 时间线已变化，请重新生成智能粗剪建议。 |
| `workspace.magic_cut_apply_failed` | 所选建议全部应用失败 | 应用失败，已保留原时间线。 |

## Implementation Tasks

### Task 1: Runtime Suggestion Persistence

**Files:**
- Create: `apps/py-runtime/src/domain/models/magic_cut.py`
- Create: `apps/py-runtime/src/repositories/magic_cut_repository.py`
- Modify: `apps/py-runtime/src/domain/models/__init__.py`
- Modify: `apps/py-runtime/src/persistence/engine.py`
- Test: `tests/runtime/test_workspace_service.py`

- [ ] **Step 1: Write failing persistence test**

Add a test that creates a timeline, saves a magic cut suggestion draft, loads the latest draft for the same timeline, and asserts no timeline tracks changed.

```python
def test_magic_cut_suggestion_draft_persists_without_changing_timeline(tmp_path: Path) -> None:
    service = _workspace_service(tmp_path)
    timeline_id = _create_timeline(service)

    draft = service.create_magic_cut_suggestion_draft(
        "project-workspace",
        timeline_id,
        summary="建议压缩开场节奏。",
        operations=[{
            "id": "suggestion-trim-open",
            "action": "trim",
            "clipId": "clip-video-1",
            "suggestedStartMs": 0,
            "suggestedDurationMs": 3000,
            "reason": "开场停顿过长。",
        }],
        ai_job_id="job-magic-cut",
    )

    latest = service.get_latest_magic_cut_suggestion("project-workspace", timeline_id)
    loaded = service.get_project_timeline("project-workspace")

    assert latest is not None
    assert latest.id == draft.id
    assert latest.status == "pending_review"
    assert latest.operations[0].reason == "开场停顿过长。"
    assert loaded.timeline is not None
    assert loaded.timeline.tracks[0].clips[0].durationMs == 4200
```

- [ ] **Step 2: Run test and confirm RED**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py::test_magic_cut_suggestion_draft_persists_without_changing_timeline -q
```

Expected: fail because `create_magic_cut_suggestion_draft` does not exist.

- [ ] **Step 3: Add minimal model and repository**

Create `MagicCutSuggestionDraft` with:

```python
class MagicCutSuggestionDraft(Base):
    __tablename__ = "magic_cut_suggestion_drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    timeline_id: Mapped[str] = mapped_column(String, ForeignKey("timelines.id", ondelete="CASCADE"), nullable=False)
    ai_job_id: Mapped[str | None] = mapped_column(String, ForeignKey("ai_job_records.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    operations_json: Mapped[str] = mapped_column(Text, nullable=False)
    timeline_version_token: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
    applied_at: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Add repository methods:

```python
def create_pending(...): ...
def get_latest(project_id: str, timeline_id: str) -> MagicCutSuggestionDraft | None: ...
def get_by_id(suggestion_id: str) -> MagicCutSuggestionDraft | None: ...
def mark_applied(suggestion_id: str) -> MagicCutSuggestionDraft | None: ...
def mark_dismissed(suggestion_id: str) -> MagicCutSuggestionDraft | None: ...
```

- [ ] **Step 4: Add schema repair**

Add `magic_cut_suggestion_drafts` table creation in `persistence/engine.py` using the same local repair style used for existing tables.

- [ ] **Step 5: Run runtime test**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py::test_magic_cut_suggestion_draft_persists_without_changing_timeline -q
```

Expected: pass.

### Task 2: Runtime Generation Stops Direct Application

**Files:**
- Modify: `apps/py-runtime/src/services/workspace_service.py`
- Modify: `apps/py-runtime/src/services/magic_cut.py`
- Modify: `apps/py-runtime/src/schemas/workspace.py`
- Test: `tests/runtime/test_workspace_service.py`

- [ ] **Step 1: Replace direct application test with review-gate test**

Change `test_run_magic_cut_applies_ai_operations_and_persists_timeline` into:

```python
def test_run_magic_cut_generates_reviewable_suggestions_without_persisting_timeline(...):
    # arrange AI returns trim and move operations
    # act run magic_cut and await task
    latest = service.get_latest_magic_cut_suggestion("project-workspace", timeline_id)
    loaded = service.get_project_timeline("project-workspace")

    assert latest is not None
    assert latest.status == "pending_review"
    assert [item.action for item in latest.operations] == ["trim", "move"]
    assert loaded.timeline.tracks[0].clips[0].durationMs == 4200
    assert loaded.timeline.tracks[0].clips[1].startMs == 4200
```

- [ ] **Step 2: Run test and confirm RED**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py::test_run_magic_cut_generates_reviewable_suggestions_without_persisting_timeline -q
```

Expected: fail because current task directly applies operations.

- [ ] **Step 3: Normalize operations into suggestions**

Add a helper in `magic_cut.py`:

```python
def build_magic_cut_suggestions(
    tracks_json: str,
    operations: list[dict[str, object]],
) -> list[dict[str, object]]:
    ...
```

Each suggestion must include original clip timing from the current timeline when available, generated `id`, `action`, `clipId`, suggested timing, and Chinese fallback `reason`.

- [ ] **Step 4: Change task behavior**

In `WorkspaceService.run_ai_command`, replace:

```python
applied, failed, op_message = apply_magic_cut_operations(...)
```

with:

```python
suggestions = build_magic_cut_suggestions(timeline.tracks_json, operations)
draft = self.create_magic_cut_suggestion_draft(
    project_id,
    timeline.id,
    summary=summary,
    operations=suggestions,
    ai_job_id=result.ai_job_id,
)
await progress_callback(100, f"已生成 {len(suggestions)} 条智能粗剪建议，等待审阅。")
```

- [ ] **Step 5: Run runtime magic cut tests**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py -q
```

Expected: pass after updating direct-application assertions.

### Task 3: Runtime Confirm Apply

**Files:**
- Modify: `apps/py-runtime/src/services/workspace_service.py`
- Modify: `apps/py-runtime/src/api/routes/workspace.py`
- Modify: `apps/py-runtime/src/schemas/workspace.py`
- Test: `tests/runtime/test_workspace_service.py`
- Test: `tests/contracts/test_workspace_runtime_contract.py`

- [ ] **Step 1: Write apply test**

```python
def test_apply_magic_cut_suggestion_updates_timeline_after_confirmation(tmp_path: Path) -> None:
    service = _workspace_service(tmp_path)
    timeline_id = _create_timeline(service)
    draft = service.create_magic_cut_suggestion_draft(...)

    result = service.apply_magic_cut_suggestion(
        draft.id,
        MagicCutSuggestionApplyInput(
            operationIds=["suggestion-trim-open"],
            confirmTimelineVersionToken=draft.timelineVersionToken,
        ),
    )

    loaded = service.get_project_timeline("project-workspace")
    assert result.appliedCount == 1
    assert result.failedCount == 0
    assert loaded.timeline.tracks[0].clips[0].durationMs == 3000
```

- [ ] **Step 2: Write version mismatch test**

```python
def test_apply_magic_cut_suggestion_rejects_changed_timeline(tmp_path: Path) -> None:
    service = _workspace_service(tmp_path)
    timeline_id = _create_timeline(service)
    draft = service.create_magic_cut_suggestion_draft(...)
    service.move_clip("clip-video-1", {"startMs": 500, "targetTrackId": "track-video"}, timeline_id=timeline_id)

    with pytest.raises(HTTPException) as exc:
        service.apply_magic_cut_suggestion(
            draft.id,
            MagicCutSuggestionApplyInput(
                operationIds=["suggestion-trim-open"],
                confirmTimelineVersionToken=draft.timelineVersionToken,
            ),
        )

    assert exc.value.status_code == 409
    assert "时间线已变化" in str(exc.value.detail)
```

- [ ] **Step 3: Run tests and confirm RED**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py::test_apply_magic_cut_suggestion_updates_timeline_after_confirmation tests\runtime\test_workspace_service.py::test_apply_magic_cut_suggestion_rejects_changed_timeline -q
```

Expected: fail because apply API does not exist.

- [ ] **Step 4: Implement service and routes**

Add:

```python
def get_latest_magic_cut_suggestion(self, project_id: str, timeline_id: str) -> MagicCutSuggestionDraftDto | None: ...
def apply_magic_cut_suggestion(self, suggestion_id: str, payload: MagicCutSuggestionApplyInput) -> MagicCutSuggestionApplyResultDto: ...
def dismiss_magic_cut_suggestion(self, suggestion_id: str) -> MagicCutSuggestionDraftDto: ...
```

Add routes:

```python
@router.get("/projects/{project_id}/magic-cut-suggestions/latest")
def get_latest_magic_cut_suggestion(project_id: str, timelineId: str, request: Request) -> dict[str, object]: ...

@router.post("/magic-cut-suggestions/{suggestion_id}/apply")
def apply_magic_cut_suggestion(suggestion_id: str, payload: MagicCutSuggestionApplyInput, request: Request) -> dict[str, object]: ...

@router.post("/magic-cut-suggestions/{suggestion_id}/dismiss")
def dismiss_magic_cut_suggestion(suggestion_id: str, request: Request) -> dict[str, object]: ...
```

- [ ] **Step 5: Run runtime and contract tests**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py tests\contracts\test_workspace_runtime_contract.py -q
```

Expected: pass.

### Task 4: Desktop Runtime Client and Store

**Files:**
- Modify: `apps/desktop/src/types/runtime.ts`
- Modify: `apps/desktop/src/app/runtime-client.ts`
- Modify: `apps/desktop/src/stores/editing-workspace.ts`
- Test: `apps/desktop/tests/editing-workspace-store.spec.ts`
- Test: `apps/desktop/tests/runtime-client-workspace.spec.ts`

- [ ] **Step 1: Write failing store tests**

Add tests:

```typescript
it("智能粗剪完成后加载建议而不立即刷新时间线", async () => {
  const store = useEditingWorkspaceStore();
  await store.runMagicCut("project-1");
  store.applyCommandTerminalTask(taskSucceeded("已生成 2 条智能粗剪建议，等待审阅。"));

  expect(store.magicCutSuggestion?.operations).toHaveLength(2);
  expect(store.lastCommandResult?.message).toContain("等待审阅");
});

it("确认应用建议后刷新时间线并运行预检", async () => {
  const result = await store.applyMagicCutSuggestion(["suggestion-trim-open"]);

  expect(result?.appliedCount).toBe(1);
  expect(store.timeline?.tracks[0].clips[0].durationMs).toBe(3000);
  expect(store.precheck?.status).toBe("ready");
});
```

- [ ] **Step 2: Run tests and confirm RED**

Run:

```powershell
npm --prefix apps/desktop run test -- editing-workspace-store.spec.ts runtime-client-workspace.spec.ts
```

Expected: fail because client/store methods and types do not exist.

- [ ] **Step 3: Add TypeScript types and client methods**

Add:

```typescript
export type MagicCutSuggestionDraftDto = { ... };
export type MagicCutSuggestionApplyInput = { operationIds: string[]; confirmTimelineVersionToken: string };
export type MagicCutSuggestionApplyResultDto = { suggestion: MagicCutSuggestionDraftDto; timeline: WorkspaceTimelineDto; appliedCount: number; failedCount: number; message: string };
```

Add runtime client methods:

```typescript
export async function fetchLatestMagicCutSuggestion(projectId: string, timelineId: string): Promise<MagicCutSuggestionDraftDto | null> { ... }
export async function applyMagicCutSuggestion(suggestionId: string, input: MagicCutSuggestionApplyInput): Promise<MagicCutSuggestionApplyResultDto> { ... }
export async function dismissMagicCutSuggestion(suggestionId: string): Promise<MagicCutSuggestionDraftDto> { ... }
```

- [ ] **Step 4: Add store state and actions**

Add state:

```typescript
magicCutSuggestion: null as MagicCutSuggestionDraftDto | null,
magicCutSuggestionStatus: "idle" as "idle" | "loading" | "ready" | "applying" | "error",
magicCutSuggestionError: null as RuntimeRequestErrorShape | null,
```

Add actions:

```typescript
async loadMagicCutSuggestion(): Promise<MagicCutSuggestionDraftDto | null> { ... }
async applyMagicCutSuggestion(operationIds: string[]): Promise<MagicCutSuggestionApplyResultDto | null> { ... }
async dismissMagicCutSuggestion(): Promise<void> { ... }
```

- [ ] **Step 5: Run desktop store tests**

Run:

```powershell
npm --prefix apps/desktop run test -- editing-workspace-store.spec.ts runtime-client-workspace.spec.ts
```

Expected: pass.

### Task 5: Desktop Review UI

**Files:**
- Create: `apps/desktop/src/modules/workspace/WorkspaceMagicCutSuggestions.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceCommandFeedbackBar.vue`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
- Test: `apps/desktop/tests/workspace-command-feedback.spec.ts`

- [ ] **Step 1: Write failing page test**

Add:

```typescript
it("智能粗剪生成建议后在右侧审阅，确认后才修改时间线", async () => {
  const { wrapper } = await mountApp("/workspace/editing");

  await wrapper.get('[data-testid="workspace-magic-cut-button"]').trigger("click");
  await emitTaskSucceeded("已生成 2 条智能粗剪建议，等待审阅。");
  await flushPromises();

  expect(wrapper.text()).toContain("AI 粗剪建议 · 2 条待审阅");
  expect(wrapper.text()).toContain("应用选中建议");
  expect(wrapper.text()).not.toContain("时间线已刷新，预检已完成");

  await wrapper.get('[data-testid="workspace-magic-cut-apply-selected"]').trigger("click");
  await flushPromises();

  expect(wrapper.text()).toContain("已应用 2 条建议");
  expect(wrapper.text()).toContain("时间线本地预检通过");
});
```

- [ ] **Step 2: Run test and confirm RED**

Run:

```powershell
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts workspace-command-feedback.spec.ts
```

Expected: fail because review UI and action events do not exist.

- [ ] **Step 3: Create suggestion component**

Component props:

```typescript
defineProps<{
  suggestion: MagicCutSuggestionDraftDto | null;
  status: "idle" | "loading" | "ready" | "applying" | "error";
  errorMessage: string | null;
}>();
```

Component emits:

```typescript
defineEmits<{
  apply: [operationIds: string[]];
  dismiss: [];
  focus: [payload: { clipId: string; trackId?: string | null }];
}>();
```

Required visible text:

```text
AI 粗剪建议 · N 条待审阅
应用选中建议
忽略全部
应用后将修改当前时间线，可通过撤销恢复。
```

- [ ] **Step 4: Wire inspector and page**

Pass store state into `WorkspaceInspector`, render `WorkspaceMagicCutSuggestions` inside the existing AI suggestion `details`, and route apply/dismiss events back to store actions.

- [ ] **Step 5: Run page tests**

Run:

```powershell
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts workspace-command-feedback.spec.ts workspace-layout-contract.spec.ts page-responsive-layout-contract.spec.ts
```

Expected: pass.

### Task 6: Documentation and Full Verification

**Files:**
- Modify: `docs/RUNTIME-API-CALLS.md`
- Modify: `docs/PROJECT-STATUS.md`
- Test: `tests/contracts/test_text_encoding_contract.py`

- [ ] **Step 1: Update API docs**

Document:

```text
GET /api/workspace/projects/{project_id}/magic-cut-suggestions/latest
POST /api/workspace/magic-cut-suggestions/{suggestion_id}/apply
POST /api/workspace/magic-cut-suggestions/{suggestion_id}/dismiss
```

Each entry must include method, route, request params, response fields, error codes, and example.

- [ ] **Step 2: Update project status**

In M05 row, replace direct AI command wording with:

```text
智能粗剪改为先生成可审阅建议，用户确认后才应用到时间线；应用后刷新预检并保留失败恢复提示。
```

- [ ] **Step 3: Run full verification**

Run:

```powershell
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
.\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py tests\contracts -q
git diff --check
```

Expected: all commands pass.

## Rollback Point

- If Runtime suggestion persistence causes migration instability, revert only Task 1-3 commits; M05 remains at current direct application behavior.
- If Desktop review UI fails responsive checks, keep Runtime suggestion APIs but hide apply controls behind the existing AI suggestion `details` until compact layout passes.
- If provider output parsing is unreliable, keep generated draft status as `failed_parse` and show “AI 返回内容无法生成建议，请重新生成”， without touching timeline.

## Completion Criteria

- `magic_cut` generation no longer changes `tracks_json`.
- Users can see pending suggestions in the right inspector before any timeline mutation.
- Applying suggestions requires an explicit user action and timeline version token confirmation.
- Failed generation and failed application both preserve the current timeline.
- Runtime API docs are updated with new routes and error envelopes.
- Frontend and Runtime tests prove generation, review, apply, dismiss, failure, and stale timeline behavior.

## Self-Review

- Spec coverage: This plan covers the existing M05 UI requirement that AI suggestions are reviewable and confirmed before timeline mutation.
- 完整性检查：全部任务已明确到文件、接口与验证命令。
- Type consistency: DTO names use `MagicCutSuggestion*` across Runtime and Desktop.
- Scope check: The plan only changes M05 `magic_cut`; it does not expand to render, publish, review center, or full asset management.
