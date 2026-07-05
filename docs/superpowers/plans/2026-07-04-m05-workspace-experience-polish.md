# M05 AI 剪辑工作台体验收敛计划

## 背景

当前 M05 AI 剪辑工作台已经完成真实编辑交互与智能粗剪审阅门禁：用户可以创建时间线、汇入三轨、拖拽/裁剪/加入素材、运行预检，并且智能粗剪已改为先生成建议、审阅后应用。

本轮不重复实现智能粗剪门禁，也不扩展渲染、发布、复盘范围。目标是从真实用户使用角度继续打磨剪辑工作台：让预览更像可用的剪辑监看区，让高影响编辑动作更可控，让工作台上下文能够承接导出前的画幅选择。

## 范围

本轮只聚焦 `ai_editing_workspace`：

1. 预览画幅从 `WorkspacePreviewStage` 局部状态提升为工作台状态。
2. 真实媒体预览的 video/audio 播放头与时间线 playhead 双向同步。
3. 删除片段增加明确确认，避免 Delete/Backspace 误删。
4. 删除、撤销、重做、应用智能粗剪建议后的反馈文案更明确。
5. 补齐相关 Vitest 测试与轻量布局契约。

## 非目标

- 不做完整多轨媒体合成播放器。
- 不新增 Runtime API。
- 不做复杂版本分支或多步撤销栈。
- 不重构整个 `runtime-client.ts`、`AppShell.vue` 或所有大文件。
- 不改 16 页路由结构。

## 关键文件

- `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- `apps/desktop/src/modules/workspace/WorkspacePreviewStage.vue`
- `apps/desktop/src/modules/workspace/useWorkspacePlayback.ts`
- `apps/desktop/src/modules/workspace/useAIEditingWorkspaceActions.ts`
- `apps/desktop/src/stores/editing-workspace.ts`
- `apps/desktop/src/modules/workspace/workspacePreviewContext.ts`
- `apps/desktop/tests/workspace-preview-stage.spec.ts`
- `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
- `apps/desktop/tests/editing-workspace-store.spec.ts`

## 实施步骤

### 1. 画幅状态进入工作台上下文

- 在 `editing-workspace` store 中增加 `previewRatio: "9:16" | "16:9"`。
- 提供 `setPreviewRatio()` action。
- `AIEditingWorkspacePage.vue` 将 store 状态传给 `WorkspacePreviewStage`。
- `WorkspacePreviewStage.vue` 改为受控组件：通过 `previewRatio` prop 展示，通过 `ratio-change` emit 修改。

### 2. 媒体播放头同步

- 保留结构预览现有 scrubber 行为。
- 对 Runtime 明确返回的 video/audio 媒体预览：
  - 播放媒体时同步触发页面 `play` 状态。
  - 媒体 `timeupdate` 将 `currentTime` 转换为当前片段内的时间线 playhead。
  - 外部 timeline playhead 变化时，媒体元素 currentTime 跟随更新，避免拖动时间线后播放器停在旧位置。
  - 媒体暂停或结束时同步暂停工作台播放状态。
- 复用现有 `WorkspacePreviewContext.clip.startMs` 与 `media.durationMs`，不从片段 metadata 猜测媒体 URL。

### 3. 删除确认与反馈

- `useAIEditingWorkspaceActions.handleDeleteSelectedClip()` 调用 `requestDesktopConfirm()`。
- 确认文案包含片段名或片段 ID，并说明可通过撤销恢复。
- Delete/Backspace 快捷键仍可触发，但必须经过确认。
- 删除成功后沿用已有 undo snapshot，并确保保存状态/反馈文案说明“已删除，可撤销”。

### 4. 测试

新增或更新测试覆盖：

- 画幅切换通过 store/page 保持状态，不只是组件局部 ref。
- 媒体 `timeupdate` 会 emit `seek` 到对应时间线毫秒值。
- 外部 playhead 变化会同步媒体 currentTime。
- 媒体暂停/结束会 emit pause。
- 删除片段前必须确认；取消确认不调用 store 删除。
- 确认删除后调用 store 删除，并保留撤销能力。

## 验证命令

```bash
npm --prefix apps/desktop run test -- workspace-preview-stage.spec.ts ai-editing-workspace-page.spec.ts editing-workspace-store.spec.ts workspace-layout-contract.spec.ts
npm --prefix apps/desktop run build
npm run version:check
git diff --check
```

## 风险控制

- 不改 Runtime 契约，降低跨端回归风险。
- 先补测试再改组件，防止破坏已存在的结构预览和媒体契约。
- 媒体同步只在 `previewMode === "media"` 且 Runtime 返回合法 media 契约时启用。
- 删除确认只影响高风险动作，不阻塞移动、裁剪、选择等高频编辑。
