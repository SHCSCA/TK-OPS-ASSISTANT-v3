# B-M13 · 发布中心 后端

**当前状态（2026-04-17）**: 已完成（V1 发布计划、预检、提交、取消与回执闭环）。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**前端对应**: M13 `publishing_center`  
**优先级**: P2  
**路由前缀**: `/api/publishing`

---

## 一、数据模型

#### `publish_plans`
```python
id: str (PK)
project_id: str (FK → projects.id)
render_task_id: str | None (FK → render_tasks.id)
account_id: str (FK → accounts.id)
workspace_id: str | None (FK → device_workspaces.id)
scheduled_at: str | None   # ISO 8601 定时发布时间
status: str                # draft / precheck_required / ready / submitting / published / failed / cancelled
metadata_json: str | None  # 标题/描述/标签/备注
created_at: str
updated_at: str
```

#### `publish_precheck_items`
```python
id: str (PK)
plan_id: str (FK → publish_plans.id CASCADE)
code: str        # account_online / render_ready / workspace_bound / duration_valid
severity: str    # error / warning / info
message: str
passed: bool
checked_at: str
```

#### `publish_receipts`
```python
id: str (PK)
plan_id: str (FK → publish_plans.id)
status: str         # success / failed / manual_required
external_url: str | None  # 发布成功后平台链接
error_message: str | None
completed_at: str
```

---

## 二、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/publishing/plans` | 获取发布计划列表（支持 ?project_id=&status=） |
| POST | `/api/publishing/plans` | 创建发布计划草稿 |
| PATCH | `/api/publishing/plans/{id}` | 更新计划（时间/账号/元数据） |
| DELETE | `/api/publishing/plans/{id}` | 删除草稿 |
| POST | `/api/publishing/plans/{id}/precheck` | 执行发布前预检 |
| POST | `/api/publishing/plans/{id}/submit` | 提交发布（需预检通过） |
| POST | `/api/publishing/plans/{id}/cancel` | 取消发布 |
| GET | `/api/publishing/plans/{id}/receipt` | 获取发布回执 |

---

## 三、预检逻辑

```python
PRECHECK_RULES = [
    ("account_online", "error",   lambda plan: account.status == "active"),
    ("render_ready",   "error",   lambda plan: render_task.status == "completed"),
    ("workspace_bound","warning", lambda plan: plan.workspace_id is not None),
    ("has_title",      "warning", lambda plan: "title" in metadata_json),
]
# 预检通过条件：无 severity=error 的 passed=False 项
```

---

## 四、V1 简化

- `submit` 接口：预检必须通过 → 创建 `publish_receipts`（status=manual_required）
- ws 广播 `task.started`，5s 后广播 `task.completed`（模拟）
- 不接入真实 TikTok 发布 API

---

## 五、新文件清单

```
domain/models/publish_plan.py
schemas/publishing.py
repositories/publishing_repository.py
services/publishing_service.py
api/routes/publishing.py
```

---

## 六、验收标准

- [ ] 计划 CRUD 完整
- [ ] precheck 返回各项检查结果（至少4条规则）
- [ ] submit 在无 error 级预检失败时才允许
- [ ] 回执接口返回 manual_required 状态
