# M05 智能粗剪审阅门禁设计规格

## 1. 对应计划

对应计划：`docs/superpowers/plans/2026-07-04-m05-magic-cut-review-gate.md`

本规格覆盖 M05 AI 剪辑工作台的 `magic_cut` 智能粗剪审阅门禁。目标是把当前“AI 生成后直接修改时间线”的链路改为“AI 生成建议草稿，用户审阅确认后才应用到时间线”。

## 2. 背景问题

当前 M05 文档已经明确：

- `docs/PRD.md` 要求 AI 输出不应直接覆盖用户已编辑内容，必须走新版本或覆盖确认路径。
- `docs/superpowers/specs/2026-05-15-m05-basic-editing-workbench-ui-design.md` 要求 AI 建议不能直接修改时间线，必须先审阅确认。
- 当前 Runtime 的 `WorkspaceService.run_ai_command` 在 `magic_cut` 任务中解析 AI 返回后直接调用 `apply_magic_cut_operations`，会立即执行删除、裁剪、移动或分割并保存时间线。
- 当前前端 `editing-workspace` store 在 AI 任务成功后直接刷新时间线并运行预检，用户无法先查看建议、比较影响或拒绝变更。
- 当前 `WorkspaceInspector` 的 AI 建议区只显示命令结果文案，没有建议列表、选择、定位、应用或忽略入口。

这会造成两个直接风险：

1. AI 可能覆盖创作者已经手工调整过的时间线，破坏用户信任。
2. 用户无法判断 AI 粗剪到底改了哪些片段，也无法选择性应用建议。

## 3. 设计目标

- 智能粗剪生成阶段只创建建议草稿，不修改 `Timeline.tracks_json`。
- 用户能在右侧基础属性面板中审阅建议、理解影响、定位片段。
- 用户必须通过明确动作应用全部或选中建议。
- 应用建议时必须校验时间线版本，避免基于过期时间线修改用户新编辑内容。
- 应用失败或时间线过期时必须保留当前时间线，并给出中文可恢复反馈。
- 前后端契约必须通过 Runtime adapter 和 Pinia store 接入，不允许组件直接拼接业务规则或直接 fetch。
- 实现必须拆分到模型、仓储、服务、路由、类型、store 和独立组件，避免继续膨胀已有大文件。

## 4. 非目标

- 不实现完整 AI 剪辑历史、版本分支或多方案对比系统。
- 不新增新的 AI Provider，也不绕过现有 `AITextGenerationService` 和能力配置总线。
- 不扩展到渲染、发布、复盘或完整资产管理。
- 不实现复杂撤销栈；本轮只要求应用前确认、应用失败保留原时间线，并复用现有撤销能力。
- 不把建议草稿存入 `Timeline.tracks_json` 或前端本地状态作为唯一真源。

## 5. 用户体验设计

### 5.1 生成建议

用户点击“智能粗剪”后：

1. 前端仍先检查 `magic_cut` 能力可用性。
2. Runtime 任务进入队列后，顶部反馈显示“正在生成智能粗剪建议”。
3. AI 返回可解析操作后，Runtime 保存建议草稿。
4. 任务成功反馈改为“已生成 N 条智能粗剪建议，等待审阅。”。
5. 前端加载最新建议草稿，但不刷新时间线为 AI 修改结果。

生成阶段禁止出现以下文案：

- “时间线已刷新”
- “已应用”
- “智能粗剪完成并保存”

### 5.2 审阅建议

右侧基础属性面板新增独立建议组件 `WorkspaceMagicCutSuggestions.vue`，放在现有 AI 建议折叠区内。

默认标题：

```text
AI 粗剪建议 · N 条待审阅
```

每条建议至少展示：

- 建议类型：裁剪、移动、分割、删除。
- 影响对象：片段名称、片段 ID 或轨道名称。
- 原时间：开始时间、时长或分割点。
- 建议时间：建议开始时间、建议时长或目标轨道。
- 原因：AI 给出的中文原因；缺失时使用中文兜底原因。
- 风险：删除、跨轨移动、时间线过期等风险提示。

建议卡片支持：

- 勾选建议。
- 定位片段。
- 应用单条建议。
- 取消勾选建议。

批量动作：

- `应用选中建议`
- `应用全部建议`
- `忽略全部`

应用前必须显示确认语义：

```text
应用后将修改当前时间线，可通过撤销恢复。
```

### 5.3 应用建议

用户点击应用后：

1. 前端提交建议 ID、选中 operation IDs 和确认的时间线版本 token。
2. Runtime 重新加载建议草稿和当前时间线。
3. Runtime 比对时间线版本 token。
4. token 一致时才复用 `delete_clip`、`trim_clip`、`move_clip`、`split_clip` 原子操作。
5. 应用成功后返回更新时间线、建议状态和应用统计。
6. 前端刷新时间线、刷新预览、运行预检，并显示应用结果。

本轮应用语义采用原子操作：用户提交的 `operationIds` 要么全部应用成功，要么全部回滚并保留原时间线。`operationIds` 为空数组时表示应用全部待审阅建议；`operationIds` 非空时只应用选中建议，未选中建议随本草稿结束，不再保留为待审阅项。

Runtime 应用前必须创建时间线快照。任一操作失败时，必须通过同一数据库事务回滚，或用快照恢复 `tracks_json` 和时间线状态后再返回错误。失败响应不返回部分成功结果，`failedCount` 只在成功响应中用于表示 0。

成功文案：

```text
已应用 N 条智能粗剪建议，时间线本地预检通过。
```

全部失败文案：

```text
应用失败，已保留原时间线。
```

### 5.4 忽略建议

用户点击忽略后：

1. Runtime 将建议草稿状态更新为 `dismissed`。
2. 前端清空当前建议区。
3. 时间线不变。

忽略文案：

```text
已忽略本次智能粗剪建议，时间线未修改。
```

## 6. Runtime 架构

### 6.1 新模型

新增 `MagicCutSuggestionDraft` ORM 模型：

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

状态枚举：

| 状态 | 含义 |
| --- | --- |
| `pending_review` | 已生成，等待用户审阅 |
| `applied` | 建议已应用完成 |
| `dismissed` | 用户已忽略 |
| `failed_parse` | AI 返回内容无法生成可审阅建议 |

`failed_parse` 状态必须持久化为空建议草稿，`operations_json` 为 `[]`，`summary` 保存解析失败的中文说明。前端读取到该状态时显示“AI 返回内容无法生成建议，请重新生成”，提供重新生成入口，不提供应用按钮。对 `failed_parse` 草稿调用应用接口必须返回 `workspace.magic_cut_suggestion_not_reviewable`。

### 6.2 时间线版本 token

`timeline_version_token` 用于防止过期建议修改新时间线。实现必须基于当前时间线可重复计算，并固定使用以下算法：

1. 构造对象：`{"timelineId": timeline.id, "updatedAt": timeline.updated_at, "tracksJson": timeline.tracks_json}`。
2. 使用 `json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))` 序列化。
3. 使用 SHA-256 计算摘要。
4. token 格式为 `sha256:{hex_digest}`。

应用建议时，如果请求中的 `confirmTimelineVersionToken` 与建议草稿保存的 token 或当前时间线 token 不一致，Runtime 返回 409。

### 6.3 仓储

新增 `MagicCutSuggestionRepository`：

- `create_pending(project_id, timeline_id, summary, operations_json, timeline_version_token, ai_job_id) -> MagicCutSuggestionDraft`
- `get_latest(project_id, timeline_id) -> MagicCutSuggestionDraft | None`
- `get_by_id(suggestion_id) -> MagicCutSuggestionDraft | None`
- `mark_applied(suggestion_id, applied_at) -> MagicCutSuggestionDraft | None`
- `mark_dismissed(suggestion_id) -> MagicCutSuggestionDraft | None`

仓储只负责持久化，不执行时间线业务规则。

### 6.4 服务

新增 `apps/py-runtime/src/services/magic_cut_suggestion_service.py`，提供 `MagicCutSuggestionService`，负责：

- 将 AI operations 标准化为建议项。
- 保存建议草稿。
- 保存解析失败草稿。
- 读取最新建议草稿。
- 应用选中建议。
- 忽略建议。
- 将 ORM 对象转换为 DTO。

`WorkspaceService.run_ai_command` 在 `magic_cut` 任务中只负责：

1. 调用 AI 文本生成。
2. 解析 AI 返回。
3. 有可审阅操作时调用 `MagicCutSuggestionService.create_from_operations(project_id, timeline, operations, summary, ai_job_id)`。
4. 没有可审阅操作时调用 `MagicCutSuggestionService.create_failed_parse(project_id, timeline, summary, ai_job_id)`。
5. 有可审阅建议时推送“等待审阅”的任务完成反馈；解析失败时推送“AI 返回内容无法生成建议，请重新生成”。

`apply_magic_cut_operations` 保留为确认应用阶段的原子操作执行能力，不再在生成阶段调用。

### 6.5 数据库迁移与 SQLite 自修复

实现必须新增 Alembic 迁移文件：

```text
apps/py-runtime/alembic/versions/0014_magic_cut_suggestion_drafts.py
```

迁移必须创建 `magic_cut_suggestion_drafts` 表、项目和时间线索引，并定义与 ORM 一致的外键。迁移文件必须可重复执行升级/降级测试。

`apps/py-runtime/src/persistence/engine.py` 必须补齐 `magic_cut_suggestion_drafts` 表创建逻辑，遵循现有本地自修复风格。

失败时必须使用 `log.exception("智能粗剪建议保存失败")` 记录上下文，并向 UI 返回中文错误，不暴露 traceback。

## 7. Runtime API 契约

所有接口继续使用统一信封：

- 成功：`{ "ok": true, "data": { "id": "suggestion-123" } }`
- 失败：`{ "ok": false, "error": "时间线已变化，请重新生成智能粗剪建议。", "error_code": "workspace.magic_cut_timeline_changed" }`

### 7.1 生成入口

```text
POST /api/workspace/projects/{project_id}/ai-commands
```

`capabilityId = "magic_cut"` 时语义改为“生成建议草稿”，不是“直接应用时间线”。

成功入队响应保持现有 `WorkspaceAICommandResultDto`，任务完成消息改为：

```text
已生成 N 条智能粗剪建议，等待审阅。
```

### 7.2 读取最新建议

```text
GET /api/workspace/projects/{project_id}/magic-cut-suggestions/latest?timelineId={timeline_id}
```

响应：

```json
{
  "ok": true,
  "data": {
    "id": "suggestion-123",
    "projectId": "project-workspace",
    "timelineId": "timeline-main",
    "timelineVersionToken": "sha256:0f4c9d2a8c7b6e5d4f3a29180766554433221100ffeeddccbbaa998877665544",
    "status": "pending_review",
    "summary": "建议压缩开场并移动冗余片段。",
    "operations": [
      {
        "id": "suggestion-trim-open",
        "action": "trim",
        "clipId": "clip-video-1",
        "trackId": "managed-video-storyboard",
        "originalStartMs": 0,
        "originalDurationMs": 4200,
        "suggestedStartMs": 0,
        "suggestedDurationMs": 3000,
        "reason": "开场停顿过长。",
        "risk": null
      }
    ],
    "createdAt": "2026-07-04T10:00:00Z",
    "updatedAt": "2026-07-04T10:00:00Z",
    "appliedAt": null
  }
}
```

没有建议时返回：

```json
{ "ok": true, "data": null }
```

### 7.3 应用建议

```text
POST /api/workspace/magic-cut-suggestions/{suggestion_id}/apply
```

请求：

```json
{
  "operationIds": ["suggestion-trim-open"],
  "confirmTimelineVersionToken": "sha256:0f4c9d2a8c7b6e5d4f3a29180766554433221100ffeeddccbbaa998877665544"
}
```

`operationIds` 为空数组时表示应用全部仍处于待审阅状态的建议。

响应：

```json
{
  "ok": true,
  "data": {
    "suggestion": {
      "id": "suggestion-123",
      "projectId": "project-workspace",
      "timelineId": "timeline-main",
      "timelineVersionToken": "sha256:0f4c9d2a8c7b6e5d4f3a29180766554433221100ffeeddccbbaa998877665544",
      "status": "applied",
      "summary": "建议压缩开场并移动冗余片段。",
      "operations": [
        {
          "id": "suggestion-trim-open",
          "action": "trim",
          "clipId": "clip-video-1",
          "trackId": "managed-video-storyboard",
          "originalStartMs": 0,
          "originalDurationMs": 4200,
          "suggestedStartMs": 0,
          "suggestedDurationMs": 3000,
          "reason": "开场停顿过长。",
          "risk": null
        }
      ],
      "createdAt": "2026-07-04T10:00:00Z",
      "updatedAt": "2026-07-04T10:02:00Z",
      "appliedAt": "2026-07-04T10:02:00Z"
    },
    "timeline": {
      "id": "timeline-main",
      "projectId": "project-workspace",
      "name": "主时间线",
      "status": "ready",
      "durationSeconds": 25,
      "tracks": []
    },
    "appliedCount": 1,
    "failedCount": 0,
    "message": "已应用 1 条智能粗剪建议。"
  }
}
```

### 7.4 忽略建议

```text
POST /api/workspace/magic-cut-suggestions/{suggestion_id}/dismiss
```

响应：

```json
{
  "ok": true,
  "data": {
    "suggestion": {
      "id": "suggestion-123",
      "projectId": "project-workspace",
      "timelineId": "timeline-main",
      "timelineVersionToken": "sha256:0f4c9d2a8c7b6e5d4f3a29180766554433221100ffeeddccbbaa998877665544",
      "status": "dismissed",
      "summary": "建议压缩开场并移动冗余片段。",
      "operations": [],
      "createdAt": "2026-07-04T10:00:00Z",
      "updatedAt": "2026-07-04T10:03:00Z",
      "appliedAt": null
    },
    "message": "已忽略本次智能粗剪建议，时间线未修改。"
  }
}
```

### 7.5 错误码

响应字段统一使用 `error_code`，不得使用 `code`。

| error_code | HTTP | 触发条件 | 中文提示 |
| --- | ---: | --- |
| `workspace.magic_cut_suggestion_not_found` | 404 | 建议 ID 不存在，或不属于当前项目/时间线 | 智能粗剪建议不存在，请重新生成。 |
| `workspace.magic_cut_timeline_changed` | 409 | 当前时间线 token 与建议 token 不一致 | 时间线已变化，请重新生成智能粗剪建议。 |
| `workspace.magic_cut_apply_failed` | 409 | 任一选中操作应用失败且已回滚 | 应用失败，已保留原时间线。 |
| `workspace.magic_cut_suggestion_not_reviewable` | 409 | 草稿状态为 `applied`、`dismissed` 或 `failed_parse` | 当前建议已处理，请重新生成。 |
| `workspace.magic_cut_invalid_operation` | 400 | `operationIds` 包含不存在、重复或不可执行操作 | 智能粗剪建议内容无效，请重新生成。 |

## 8. DTO 设计

### 8.1 Runtime DTO

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


class MagicCutSuggestionApplyResultDto(BaseModel):
    suggestion: MagicCutSuggestionDraftDto
    timeline: WorkspaceTimelineDto
    appliedCount: int
    failedCount: int
    message: str
```

### 8.2 Desktop 类型

前端类型与 Runtime DTO 字段保持同名驼峰格式：

```typescript
export type MagicCutSuggestionOperationDto = {
  id: string;
  action: string;
  clipId: string;
  trackId?: string | null;
  targetTrackId?: string | null;
  originalStartMs?: number | null;
  originalDurationMs?: number | null;
  suggestedStartMs?: number | null;
  suggestedDurationMs?: number | null;
  splitAtMs?: number | null;
  reason: string;
  risk?: string | null;
};
```

前端不得重新解释 AI 原始输出，只消费 Runtime 标准化后的建议 DTO。

## 9. Desktop 架构

### 9.1 Runtime client

在 `apps/desktop/src/app/runtime-client.ts` 增加：

```typescript
fetchLatestMagicCutSuggestion(projectId: string, timelineId: string)
applyMagicCutSuggestion(suggestionId: string, input: MagicCutSuggestionApplyInput)
dismissMagicCutSuggestion(suggestionId: string)
```

所有方法必须继续使用 `requestRuntime`，不得组件内直接 fetch。

### 9.2 Store 状态

在 `editing-workspace` store 增加：

```typescript
magicCutSuggestion: MagicCutSuggestionDraftDto | null;
magicCutSuggestionStatus: "idle" | "loading" | "ready" | "applying" | "error";
magicCutSuggestionError: RuntimeRequestErrorShape | null;
```

新增 action：

```typescript
loadMagicCutSuggestion(): Promise<MagicCutSuggestionDraftDto | null>
applyMagicCutSuggestion(operationIds: string[]): Promise<MagicCutSuggestionApplyResultDto | null>
dismissMagicCutSuggestion(): Promise<void>
```

`applyCommandTerminalTask` 在 `magic_cut` 成功后不再立即 `load + runPrecheck`。它只加载建议草稿并保留“等待审阅”反馈。

### 9.3 UI 组件

新增 `WorkspaceMagicCutSuggestions.vue`。

Props：

```typescript
defineProps<{
  suggestion: MagicCutSuggestionDraftDto | null;
  status: "idle" | "loading" | "ready" | "applying" | "error";
  errorMessage: string | null;
}>();
```

Emits：

```typescript
defineEmits<{
  apply: [operationIds: string[]];
  dismiss: [];
  focus: [payload: { clipId: string; trackId?: string | null }];
}>();
```

组件必须覆盖：

- 加载中：`正在读取智能粗剪建议`
- 空状态：`暂无可应用建议。`
- 待审阅：建议列表和操作按钮。
- 应用中：禁用按钮并显示 `正在应用建议`
- 错误：显示中文错误和重新读取入口。

### 9.4 页面接线

`AIEditingWorkspacePage.vue` 只负责把 store 状态和事件接给 `WorkspaceInspector`，不直接处理建议业务规则。

`WorkspaceInspector.vue` 只承载建议组件，不解析 AI 输出，不执行 Runtime 请求。

`WorkspaceCommandFeedbackBar.vue` 生成完成时展示“查看 AI 建议”，不使用“已应用”类措辞。

## 10. 状态流转

```text
idle
  -> generating
  -> pending_review
  -> applying
  -> applied

pending_review
  -> dismissed
  -> stale
  -> error

generating
  -> failed_parse
```

状态解释：

- `generating` 属于任务状态，由 TaskBus 管理。
- `pending_review` 属于建议草稿状态，由 Runtime 持久化。
- `applying` 属于前端临时状态，Runtime 完成后落到 `applied`；失败时回到 `pending_review` 并显示错误。
- `stale` 不需要持久化为草稿状态；应用接口返回 409 后前端提示重新生成。
- `failed_parse` 属于建议草稿状态，由 latest 接口返回，前端只允许重新生成或忽略。

## 11. 异常与日志

Runtime 必须记录：

- 建议生成失败：`log.exception("智能粗剪建议生成失败")`
- 建议保存失败：`log.exception("智能粗剪建议保存失败")`
- 建议应用失败：`log.exception("智能粗剪建议应用失败")`
- 时间线版本不一致：`log.warning("智能粗剪建议应用被拒绝 timeline_changed suggestion_id=%s timeline_id=%s", suggestion_id, timeline_id)`

UI 可见错误必须是中文，不能展示 traceback 或 Provider 原始堆栈。

应用建议前必须保留原时间线快照；任一操作失败时必须事务回滚或恢复快照。失败路径返回 `workspace.magic_cut_apply_failed`，并保证响应后的时间线与应用前一致。

## 12. 测试要求

### 12.1 Runtime 测试

必须覆盖：

- `magic_cut` 生成建议草稿后不修改时间线。
- 建议草稿可持久化并读取最新。
- 应用建议后才修改时间线。
- 时间线版本变化时拒绝应用。
- 忽略建议不会修改时间线。
- 任一操作失败时回滚并保留原时间线。
- AI 返回无法解析时创建 `failed_parse` 草稿，latest 接口可读取，应用接口返回 `workspace.magic_cut_suggestion_not_reviewable`。
- 新接口保持统一 JSON 信封、`error_code` 字段和中文错误。
- Alembic 迁移能创建并回滚 `magic_cut_suggestion_drafts` 表。

建议测试命令：

```powershell
.\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py tests\contracts\test_workspace_runtime_contract.py -q
```

### 12.2 Desktop 测试

必须覆盖：

- 智能粗剪任务成功后加载建议，不刷新时间线为 AI 修改结果。
- 右侧显示“AI 粗剪建议 · N 条待审阅”。
- 选中建议后才能应用选中建议。
- 应用建议后刷新时间线、预览和预检。
- 忽略建议后建议区回到空态。
- 时间线过期错误展示“时间线已变化，请重新生成智能粗剪建议。”。
- `failed_parse` 草稿展示“AI 返回内容无法生成建议，请重新生成”，且不显示应用按钮。
- `WorkspaceCommandFeedbackBar` 不再表达“已应用”。
- 建议组件在 320-420px 宽度面板内按钮可换行、列表可滚动，不挤压时间线。

建议测试命令：

```powershell
npm --prefix apps/desktop run test -- editing-workspace-store.spec.ts runtime-client-workspace.spec.ts ai-editing-workspace-page.spec.ts workspace-command-feedback.spec.ts
npm --prefix apps/desktop run test -- workspace-layout-contract.spec.ts page-responsive-layout-contract.spec.ts
```

### 12.3 全量验证

实现完成后必须运行：

```powershell
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
.\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py tests\contracts -q
git diff --check
```

## 13. 文档要求

实现时必须同步更新：

- `docs/RUNTIME-API-CALLS.md`
  - 新增三个 magic cut suggestion 接口。
  - 包含接口地址、方法、参数、返回、错误码、示例。
  - 更新 `POST /api/workspace/projects/{project_id}/ai-commands` 中 `capabilityId = "magic_cut"` 的语义，明确它生成建议草稿而非直接应用时间线。
  - 明确失败信封使用 `error_code` 字段，并登记本规格的错误码表。
- `docs/PROJECT-STATUS.md`
  - 将 M05 智能粗剪状态改为“生成建议、审阅确认后应用”。

文档不得写成计划口吻，必须描述已实现后的行为。

## 14. 交付验收

交付时必须满足：

- `magic_cut` 生成阶段不会修改 `tracks_json`。
- 用户在右侧基础属性面板看到待审阅建议。
- 用户应用建议前能理解影响片段、原因和风险。
- 用户明确确认后才修改时间线。
- 过期建议不能应用。
- 应用失败保留原时间线。
- 前后端测试覆盖生成、审阅、应用、忽略、失败和过期时间线。
- 前后端测试覆盖 `failed_parse` 和响应式建议区。
- API 文档和项目状态文档已同步。

## 15. 后续衔接

本规格完成后，M05 下一轮再处理以下体验问题：

- 剪映式大预览框与真实媒体播放头双向同步。
- 16:9 / 9:16 升级为工作台与导出上下文状态。
- 三轨从“末尾对齐”升级到“段落级对齐检查”。
- 紧凑窗口下素材池和属性面板改为抽屉或标签化面板。
- 删除片段增加更明确的撤销或确认反馈。

这些问题不混入本轮实现，避免智能粗剪审阅门禁被 UI 大改拖慢。

## 16. 自检

- 本规格与已批准 plan 一致。
- 本规格不引入新 Provider、不扩展渲染发布范围。
- Runtime 写入路径仍由服务层和仓储层处理。
- 前端请求仍通过 Runtime adapter 和 Pinia store。
- 错误、日志、状态反馈均有明确要求。
- 没有未定义的空白任务或模糊验收项。
