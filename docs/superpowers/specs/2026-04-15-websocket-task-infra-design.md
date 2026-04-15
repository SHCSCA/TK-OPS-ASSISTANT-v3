# WebSocket 任务基础设施设计验收规格

> 日期：2026-04-15
> 对应计划：`docs/superpowers/plans/2026-04-15-websocket-task-infra.md`
> 状态：用于收口当前 TaskManager / TaskBus 基建验收

## 目标

建立 TK-OPS V1 的统一长任务基础设施，让视频导入、配音、字幕、渲染、发布预检等耗时操作后续都能使用同一套任务状态、取消、失败原因和 WebSocket 事件模型。

本规格只定义基础设施能力，不直接把所有业务模块迁移到 TaskBus。

## 后端契约

- `TaskManager` 负责内存态任务生命周期：`queued -> running -> succeeded | failed | cancelled`。
- 任务必须包含：`id`、`task_type`、`project_id`、`status`、`progress`、`message`、`created_at`、`updated_at`。
- 任务进度通过 `ProgressCallback(progress, message)` 上报，进度必须归一到 `0..100`。
- WebSocket 事件必须带 `schema_version: 1`。
- 任务 API 使用统一 JSON 信封：
  - `GET /api/tasks`
  - `GET /api/tasks/{task_id}`
  - `POST /api/tasks/{task_id}/cancel`
- 未找到任务返回 `404` 和中文错误：`任务不存在`。
- 不可取消任务返回 `409` 和中文错误：`任务不可取消`。

## 前端契约

- `TaskBus` 是桌面端统一 WebSocket 任务事件入口。
- 页面不得各自建立互不兼容的任务 WebSocket 连接。
- `TaskBus` 负责：
  - 解析 Runtime base URL 为 `/api/ws`。
  - 维护连接状态和重连。
  - 按 `taskId` 追踪任务。
  - 提供订阅/取消订阅能力。
  - 允许页面通过响应式状态读取当前任务。
- HTTP 查询仍通过 `runtime-client.ts` 的任务 API 包装函数完成。

## 事件格式

标准任务事件：

```json
{
  "schema_version": 1,
  "type": "task.progress",
  "taskId": "uuid",
  "taskType": "tts_generation",
  "projectId": "project-id",
  "status": "running",
  "progress": 45,
  "message": "正在处理"
}
```

允许的事件类型：

- `task.started`
- `task.progress`
- `task.completed`
- `task.failed`

取消任务在 V1 可复用 `task.failed` 事件，但事件 payload 的 `status` 必须是 `cancelled`。

## 错误与恢复

- 后端异常必须记录日志，不把 traceback 暴露给 UI。
- 失败任务必须保留可展示的 `message`。
- 前端必须能在 WebSocket 断线后通过 HTTP 重新读取活跃任务。
- 后续业务模块接入时，任务完成后必须刷新对应业务缓存或页面状态。

## 非目标

- V1 不做任务持久化。
- V1 不做跨进程任务恢复。
- V1 不要求一次性迁移所有长任务模块。
- V1 不新增 AI Provider 具体实现。

## 验收清单

- `TaskManager` 生命周期事件有单元测试覆盖。
- 失败任务、取消任务有单元测试覆盖。
- `ws_manager.broadcast()` 自动补齐 `schema_version`。
- `/api/tasks` 合同测试验证统一 JSON 信封。
- 未知任务返回 `404` 和中文错误。
- 前端构建通过，证明 `TaskBus` 和任务类型可编译。
- 合同测试全绿，避免旧视频导入契约漂移阻塞后续开发。

## 当前验证命令

```powershell
npm --prefix apps/desktop run build
venv\Scripts\python.exe -m pytest tests\runtime -q
venv\Scripts\python.exe -m pytest tests\contracts -q
```

## 后续迁移顺序

1. 视频导入/拆解：作为第一个真实业务 pilot，统一到 TaskBus 可见任务体验。
2. 配音中心：TTS 生成改为长任务。
3. 字幕对齐中心：字幕对齐改为长任务。
4. 渲染导出中心：渲染任务改为长任务。
5. 发布中心：发布预检和提交状态接入任务/事件模型。
