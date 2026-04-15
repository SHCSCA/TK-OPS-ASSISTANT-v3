# WebSocket 任务基础设施实施计划

> **任务等级**: S 档（跨模块基础设施）
> **日期**: 2026-04-15

## Context

8 个业务模块需要长任务 + WebSocket 进度推送。当前已有 `ws_manager.py`（ConnectionManager 广播单例）和 `video_tasks.py`（参考实现），但缺少通用 TaskManager 和前端 TaskBus。

## 架构设计

### 后端: TaskManager

```
services/task_manager.py   ← 核心调度器（注册/执行/取消/查询）
tasks/base.py              ← BaseTask 抽象基类
```

**TaskManager 职责**:
- 注册 task 函数 → 分配 taskId (UUID)
- asyncio.create_task 执行 → 状态机 (queued → running → succeeded/failed/cancelled)
- 进度回调 → ws_manager.broadcast(标准事件格式)
- 内存字典追踪活跃任务（V1 不持久化到 DB）
- 取消任务 → asyncio.Task.cancel()
- 查询任务状态 → GET /api/tasks/{taskId}

**标准事件格式** (CLAUDE.md 要求 schema_version):
```json
{
  "schema_version": 1,
  "type": "task.progress",
  "taskId": "uuid",
  "taskType": "tts_generation",
  "projectId": "xxx",
  "status": "running",
  "progress": 45,
  "message": "正在生成第 3/8 段..."
}
```

### 前端: TaskBus Store

```
stores/task-bus.ts   ← Pinia store, 统一 WS 连接 + 事件分发
types/task-events.ts ← 事件类型定义
```

**TaskBus 职责**:
- 单一 WebSocket 连接（自动重连 + 心跳）
- 按 taskId 追踪所有进行中任务
- 提供 subscribe(taskId, callback) 和 unsubscribe API
- 暴露 reactive 的 tasks Map 供页面直接绑定

### API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/tasks` | 列出活跃任务 |
| GET | `/api/tasks/{taskId}` | 查询单个任务状态 |
| POST | `/api/tasks/{taskId}/cancel` | 取消任务 |

## 文件清单

### 后端新增
1. `apps/py-runtime/src/services/task_manager.py` — TaskManager 类
2. `apps/py-runtime/src/api/routes/tasks.py` — 任务 API 路由

### 后端修改
3. `apps/py-runtime/src/api/routes/__init__.py` — 注册 tasks_router
4. `apps/py-runtime/src/app/factory.py` — include_router + 启动时注入 TaskManager
5. `apps/py-runtime/src/services/ws_manager.py` — 添加 schema_version 到 broadcast

### 前端新增
6. `apps/desktop/src/types/task-events.ts` — WS 事件类型定义
7. `apps/desktop/src/stores/task-bus.ts` — TaskBus Pinia store

### 前端修改
8. `apps/desktop/src/app/runtime-client.ts` — 添加 task API 函数
9. `apps/desktop/src/types/runtime.ts` — 添加 TaskInfo DTO

## 验证

```bash
npm --prefix apps/desktop run build
venv\Scripts\python.exe -m pytest tests/runtime -q
```
