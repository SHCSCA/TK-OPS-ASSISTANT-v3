# M05 到 M14 导出交接设计

## 背景

M05 已能在时间线保存、预检通过后跳转到 `/renders/export?from=workspace&projectId=...&timelineId=...`。但 M14 当前只展示渲染任务列表，用户看不到来自工作台的时间线上下文，也不知道是否接上了正确项目。

## 用户体验

当 `from=workspace` 时，M14 顶部显示“来自 AI 剪辑工作台”的交接卡：

- 项目匹配：显示当前项目名称、项目 ID、时间线 ID，并提示“可以继续配置导出任务”。
- 项目不匹配：提示当前项目与工作台传入项目不一致，要求回到创作总览或重新从 M05 进入。
- 缺少 `timelineId`：提示交接信息不完整，要求回到 M05 重新执行导出前预检。
- 普通进入 M14：不显示交接卡，保留现有渲染任务中心体验。

卡片只表达上下文和下一步，不伪造导出结果。

## RenderTask 时间线契约

上一轮交接卡不自动创建渲染任务。本轮仅在用户手动创建任务时，把有效交接里的 `timelineId` 保存为 `RenderTask.timeline_id`。

要求：

- `RenderTaskCreateInput` 接受 `timeline_id`。
- `RenderTaskDto` 返回 `timeline_id`。
- 数据库存储 nullable `timeline_id`，兼容已有任务。
- M14 创建任务时，只有 `workspaceHandoff.canCreateFromHandoff` 为 true 才带上 `timeline_id`。
- M14 任务详情显示“时间线 ID”。
- 缺少 `timelineId` 或项目不匹配时，创建入口保持禁用。

这只是导出任务与时间线的真实关联，不代表本轮实现完整时间线合成。

## 架构

新增纯函数模块 `renderWorkspaceHandoff.ts`：

- 输入：`route.query`、当前项目上下文。
- 输出：`status`、`tone`、`title`、`description`、`projectId`、`timelineId`、`canCreateFromHandoff`。

新增展示组件 `RenderWorkspaceHandoffCard.vue`：

- 只负责展示结构化状态。
- 不读取 store、不发请求、不创建任务。

`RenderExportCenterPage.vue`：

- 通过 `useRoute()` 获取 query。
- 通过当前 `projectStore.currentProject` 传给 helper。
- 在摘要区前渲染交接卡。
- 新建任务抽屉仍沿用现有手动创建逻辑。
- 有效交接状态下，创建任务 payload 带上 `timeline_id`。

## 错误与状态

错误反馈全部以中文可见文案展示在交接卡内。项目缺失继续由 `ProjectContextGuard` 处理。M14 页面不直接 `fetch`，仍通过 `rendersStore` 与 Runtime 适配层读取任务。

## 测试

前端测试覆盖：

- 工作台 query 匹配当前项目时显示项目和时间线。
- 工作台 query 缺少 `timelineId` 时显示阻断。
- 工作台 query 项目不匹配时显示阻断。
- 普通进入 M14 不显示交接卡。
- 有效工作台交接下创建任务时，POST payload 包含 `timeline_id`。
- Runtime 创建任务后返回的 DTO 包含 `timeline_id`。

同时保留现有“Runtime 返回完成任务和真实输出路径”的测试。

## 非目标

- 不新增导出模板配置。
- 不实现 FFmpeg 时间线合成。
- 不改 M05 导出就绪卡。
- 不新增页面或路由。
- 不把结构预览伪装成真实视频输出。
