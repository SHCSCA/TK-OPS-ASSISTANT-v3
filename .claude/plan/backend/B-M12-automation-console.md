# B-M12 · 自动化执行中心 后端

**当前状态（2026-04-17）**: 已完成（V1 自动化任务、触发、运行记录、取消与日志闭环）。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**前端对应**: M12 `automation_console`  
**优先级**: P2  
**路由前缀**: `/api/automation`

---

## 一、数据模型

#### `automation_tasks`（任务定义）
```python
id: str (PK)
name: str
type: str             # collect / reply / sync / validate
project_id: str | None (FK → projects.id)
account_id: str | None (FK → accounts.id)
workspace_id: str | None (FK → device_workspaces.id)
schedule_json: str | None  # cron 表达式或一次性时间
retry_policy_json: str | None  # max_retries / backoff
status: str           # enabled / disabled / archived
created_at: str
updated_at: str
```

#### `automation_task_runs`（执行记录）
```python
id: str (PK)
task_id: str (FK → automation_tasks.id CASCADE)
status: str           # queued / running / completed / failed / cancelled / paused
progress: int = 0
error_message: str | None
started_at: str | None
completed_at: str | None
created_at: str
```

#### `automation_logs`（执行日志）
```python
id: str (PK)
run_id: str (FK → automation_task_runs.id CASCADE)
level: str            # info / warning / error
message: str
created_at: str
```

---

## 二、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/automation/tasks` | 获取任务定义列表 |
| POST | `/api/automation/tasks` | 创建任务定义 |
| PATCH | `/api/automation/tasks/{id}` | 更新任务（开关/计划/策略） |
| DELETE | `/api/automation/tasks/{id}` | 删除任务 |
| POST | `/api/automation/tasks/{id}/start` | 手动触发运行 |
| GET | `/api/automation/runs` | 获取运行记录（支持 ?task_id=&status=） |
| GET | `/api/automation/runs/{run_id}` | 运行详情 |
| POST | `/api/automation/runs/{run_id}/cancel` | 取消运行 |
| GET | `/api/automation/runs/{run_id}/logs` | 获取运行日志（分页） |

---

## 三、V1 简化

- `POST .../start` 创建 run 记录（status=queued）→ ws 广播 task.started → 5s 后标记 manual_required
- 日志接口返回 `automation_logs` 记录
- 不做真实采集/回复/同步，API 层完整，执行层为占位

---

## 四、新文件清单

```
domain/models/automation.py
schemas/automation.py
repositories/automation_repository.py
services/automation_service.py
api/routes/automation.py
```

---

## 五、验收标准

- [ ] 任务定义 CRUD 完整
- [ ] 手动触发创建 run 记录，ws 广播 task.started
- [ ] 运行日志接口返回数据（可以是占位 INFO 日志）
- [ ] cancel 更新 run.status = cancelled
