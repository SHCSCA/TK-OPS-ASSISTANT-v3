# 视频导入 TaskBus Pilot 实施计划

> 日期：2026-04-15
> 任务等级：A 档（前后端契约 + 页面状态 + 长任务接入）
> 依赖：`docs/superpowers/specs/2026-04-15-websocket-task-infra-design.md`

## Context

视频拆解中心已经具备真实导入、列表查询和后台 FFprobe 解析能力，但当前页面仍有自己的 WebSocket 连接，并监听旧式 `video_status_changed` 事件。与此同时，仓库已经新增通用 `TaskManager`、`/api/tasks`、`TaskBus` 与任务事件类型。

下一步应把视频导入作为第一个真实业务 pilot 接入 TaskBus，验证统一长任务基础设施可以支撑业务页面，而不是继续让各页面各自维护 WebSocket 状态。

## Goal

- 视频导入仍快速返回 `ImportedVideo`，不破坏现有导入合同。
- 导入后后台解析任务通过标准 TaskBus 事件通知前端。
- 前端视频拆解页停止创建独立 WebSocket，改用统一 `TaskBus`。
- 视频卡片能展示导入/解析进度、完成、失败状态，并在任务结束后刷新视频列表。
- 保留真实 Runtime 数据路径，不增加假进度或假视频指标。

## Non-goals

- 不一次性迁移配音、字幕、渲染、发布预检。
- 不改变 `ImportedVideo` 主模型字段。
- 不引入任务持久化。
- 不引入新动效依赖。
- 不把视频拆解扩展到转写、切段、AI 结构拆解。

## Scope

允许修改：

- `apps/py-runtime/src/services/task_manager.py`
- `apps/py-runtime/src/services/video_import_service.py`
- `apps/py-runtime/src/tasks/video_tasks.py`
- `apps/py-runtime/src/api/routes/video_deconstruction.py`
- `apps/desktop/src/stores/video-import.ts`
- `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue`
- `apps/desktop/src/types/task-events.ts`
- `tests/runtime/*`
- `tests/contracts/*`
- `apps/desktop/tests/*`

禁止修改：

- 旧壳目录。
- 与视频导入无关的业务页面。
- 账号、设备、发布、复盘等模块的数据模型。
- UI 设计系统全局重构。

## Proposed Direction

1. 后端让视频导入后台任务进入 `TaskManager`。
2. `TaskManager.submit()` 支持可选 `task_id`，视频导入使用 `video_id` 作为任务 ID，保证前端能用导入响应中的 `video.id` 直接关联任务。
3. `process_video_import_task()` 接收进度回调，关键阶段上报 TaskBus 标准事件。
4. 视频导入响应仍保持 `ImportedVideo` 数据形状，避免破坏现有合同测试。
5. 前端 `video-import` store 接入 `useTaskBusStore()`，删除页面私有 WebSocket。
6. 视频拆解页基于 `TaskBus.tasks.get(video.id)` 显示任务进度和状态。
7. 任务完成、失败或取消时刷新当前项目视频列表。

## Council Notes

- Product Manager：该改动服务“真实视频素材进入创作链路”，属于 16 页内的核心管线能力。
- TK Operations：先解决导入进度和失败反馈，比继续扩展 AI 拆解更有运营价值。
- Runtime Lead：保留导入响应形状，用标准任务事件承载长任务状态，是最低风险契约。
- Frontend Lead：统一到 TaskBus 后，后续配音/字幕/渲染可以复用同一交互模式。
- QA：必须覆盖合同兼容、任务事件、页面状态三类验证。
- Reviewer：无 P0；P1 是必须避免破坏现有导入合同。

## Acceptance

- 导入接口返回的 `ImportedVideo` 合同保持兼容。
- 视频导入任务产生标准 `task.started`、`task.progress`、`task.completed` 或 `task.failed` 事件。
- 前端视频拆解页不再创建私有 WebSocket。
- 页面能显示与 `video.id` 关联的任务状态。
- 任务结束后刷新视频列表。
- 验证命令通过：
  - `npm --prefix apps/desktop run build`
  - `npm --prefix apps/desktop run test`
  - `venv\Scripts\python.exe -m pytest tests\runtime -q`
  - `venv\Scripts\python.exe -m pytest tests\contracts -q`

## Rollback

如果 TaskBus 接入出现阻断，回退点是：

- 保留当前导入合同和视频列表。
- 回退 `video-import` store 对 TaskBus 的依赖。
- 后端继续使用现有后台解析任务。

不得回退到旧壳，也不得新增第二套长期 WebSocket 机制。
