# 视频导入 TaskBus Pilot 设计规格

> 日期：2026-04-15
> 对应计划：`docs/superpowers/plans/2026-04-15-video-import-taskbus-pilot.md`
> 依赖规格：`docs/superpowers/specs/2026-04-15-websocket-task-infra-design.md`

## Summary

将视频导入后台解析作为 TaskBus 的第一个真实业务 pilot。实现时必须保持 `POST /api/video-deconstruction/projects/{project_id}/import` 的现有响应形状，继续返回 `ImportedVideo`；任务状态通过标准 TaskBus 事件单独推送。

关键设计决策：视频导入任务的 `taskId` 使用 `video.id`。这样前端拿到导入响应后无需扩展 API 字段即可关联 TaskBus 状态。

## Backend Design

### TaskManager

修改 `TaskManager.submit()`：

- 增加可选参数 `task_id: str | None = None`。
- 未传时继续使用 `uuid4()`。
- 传入时使用该 ID 创建 `TaskInfo.id`。
- 若同 ID 仍在运行，返回或抛出明确错误；V1 推荐抛出 `ValueError("任务已存在")`，由调用方转为中文错误。

不得改变现有 `TaskInfo.to_dict()` 字段。

### VideoImportService

修改 `VideoImportService`：

- 构造函数注入 `task_manager`，默认可继续使用全局 `task_manager`，便于测试。
- `import_video()` 创建 `ImportedVideo` 后提交 TaskManager 任务。
- `task_type` 固定为 `video_import`。
- `task_id` 使用 `video_id`。
- `project_id` 使用当前项目 ID。
- `coro_factory` 调用 `process_video_import_task()`，并传入 `progress_callback`。
- `import_video()` 返回值仍是 `_to_dict(saved_video)`。

### Video Task

修改 `process_video_import_task()`：

- 增加参数 `progress_callback: ProgressCallback | None = None`。
- 开始解析前上报 `10, "正在读取视频文件"`。
- FFprobe 前上报 `40, "正在解析视频元信息"`。
- 写入仓库前上报 `80, "正在保存解析结果"`。
- 正常结束由 TaskManager 统一广播 `task.completed`。
- 如果 FFprobe 不可用但文件记录成功，任务应视为 succeeded；视频状态仍可保持 `imported`，并写入当前错误提示。
- 异常时更新视频状态为 `error`，重新抛出异常，让 TaskManager 记录 `failed` 并广播失败事件。

### Route

保持 `video_deconstruction.import_video` 为 `async def`，避免同步线程池中调用 `asyncio.create_task()` 没有 running loop。

## Frontend Design

### video-import store

修改 `apps/desktop/src/stores/video-import.ts`：

- 引入 `useTaskBusStore`。
- 删除 `initializeWebSocket()` 内的私有 WebSocket 创建逻辑。
- 提供 `connectTaskBus()` 或在 `initializeWebSocket()` 内委托 `taskBus.connect()`，以保持页面调用点兼容。
- `importVideoFile()` 成功返回视频后：
  - 将视频插入列表。
  - 订阅 `taskBus.subscribe(video.id, callback)`。
  - `task.completed`、`task.failed` 或 `cancelled` 后刷新 `loadVideos(projectId)`。
- 提供查询 helper：
  - `taskForVideo(videoId)` 或 getter 风格方法，用于页面取 `taskBus.tasks.get(videoId)`。
- 页面状态仍以真实视频列表为主，任务状态只作为覆盖层或辅助状态。

### VideoDeconstructionCenterPage

修改 `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue`：

- 保留现有工作区布局，不做视觉大改。
- 按 `video.id` 读取对应任务状态。
- 卡片状态展示规则：
  - 有任务且 `running/queued`：显示进度百分比和任务 message。
  - 有任务且 `failed`：显示失败 message，并提示可重新导入或删除记录。
  - 无任务：继续显示视频自身 `status`。
- 导入按钮的 disabled 仍受当前导入请求状态控制，不因历史任务阻塞。
- 不新增假进度；进度只来自 TaskBus 事件。

## Contract Decisions

- `POST /api/video-deconstruction/projects/{project_id}/import` 响应不增加 `taskId` 字段。
- `ImportedVideo` 字段保持不变。
- TaskBus 的 `taskId` 对视频导入等于 `ImportedVideo.id`。
- 旧式 `video_status_changed` 事件可以在过渡期保留，但前端视频页面不得继续依赖私有 WebSocket。

## Tests

### Runtime tests

新增或调整：

- `TaskManager.submit(task_id=...)` 使用指定 ID。
- 重复运行中的 `task_id` 有明确失败行为。
- 视频导入 service 提交 `task_type="video_import"`、`task_id=video.id`、`project_id=project_id`。
- `process_video_import_task()` 在成功路径调用 progress callback，并更新视频状态。
- FFprobe 不可用时任务成功完成，视频保持 `imported` 并写入提示。
- 异常时视频状态为 `error`，TaskManager 广播 failed。

### Contract tests

保持并强化：

- 视频导入响应字段集合仍为 `ImportedVideo` 字段，不增加 `taskId`。
- `/api/tasks/{video_id}` 能在任务运行期间返回任务信封；如果测试时任务已结束，可通过 service-level 测试覆盖该关联。

### Frontend tests

新增或调整：

- `video-import` store 调用 TaskBus connect，而不是创建私有 WebSocket。
- 导入成功后订阅 `video.id`。
- 收到 `task.completed` 或 `task.failed` 后刷新视频列表。
- 视频拆解页能渲染任务 progress/message。

## Ownership Map

- Backend Runtime Lead：
  - `apps/py-runtime/src/services/task_manager.py`
  - `apps/py-runtime/src/services/video_import_service.py`
  - `apps/py-runtime/src/tasks/video_tasks.py`
- Data & Contract：
  - `tests/runtime/test_task_manager.py`
  - `tests/runtime/test_video_import_service.py`
  - `tests/contracts/test_video_deconstruction_api.py`
- Frontend Lead：
  - `apps/desktop/src/stores/video-import.ts`
  - `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue`
  - `apps/desktop/tests/video-deconstruction.spec.ts`
- Project Leader 串行处理共享文件：
  - `apps/desktop/src/app/runtime-client.ts`
  - `apps/desktop/src/types/task-events.ts`

## Acceptance Gates

必须通过：

```powershell
npm --prefix apps/desktop run build
npm --prefix apps/desktop run test
venv\Scripts\python.exe -m pytest tests\runtime -q
venv\Scripts\python.exe -m pytest tests\contracts -q
```

验收时还需人工检查：

- 视频页面没有新增私有 WebSocket。
- TaskBus 是唯一任务 WebSocket 入口。
- 导入响应合同未破坏。
- 任务失败信息可展示为中文 UI 提示。
- 页面未新增假数据或假进度。
