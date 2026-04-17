# B-M11 · 设备与工作区管理 后端

**当前状态（2026-04-17）**: 已完成（V1 工作区、健康检查、浏览器实例与执行绑定闭环）。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**前端对应**: M11 `device_workspace_management`  
**优先级**: P2  
**路由前缀**: `/api/devices`

---

## 一、数据模型

#### `device_workspaces`
```python
id: str (PK)
name: str
root_path: str        # 本地目录路径
status: str           # online / offline / running / error
error_count: int = 0
last_used_at: str | None
metadata_json: str | None  # 预留扩展
created_at: str
updated_at: str
```

#### `browser_instances`
```python
id: str (PK)
workspace_id: str (FK → device_workspaces.id CASCADE)
name: str
profile_path: str     # 浏览器用户数据目录
browser_type: str     # chrome / edge / firefox
status: str           # running / stopped / error
last_seen_at: str | None
created_at: str
```

#### `execution_bindings`
```python
id: str (PK)
account_id: str (FK → accounts.id CASCADE)
workspace_id: str (FK → device_workspaces.id CASCADE)
browser_instance_id: str | None (FK → browser_instances.id)
status: str          # active / inactive
purpose: str         # publish / collect / reply
created_at: str
```

---

## 二、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/devices/workspaces` | 获取工作区列表 |
| POST | `/api/devices/workspaces` | 创建工作区 |
| PATCH | `/api/devices/workspaces/{id}` | 更新工作区 |
| DELETE | `/api/devices/workspaces/{id}` | 删除工作区 |
| POST | `/api/devices/workspaces/{id}/health-check` | 目录存在性 + 状态检查 |
| GET | `/api/devices/browser-instances` | 获取浏览器实例列表（支持 ?workspace_id=） |
| POST | `/api/devices/browser-instances` | 注册浏览器实例 |
| DELETE | `/api/devices/browser-instances/{id}` | 删除浏览器实例 |
| GET | `/api/devices/bindings` | 获取执行绑定列表 |
| POST | `/api/devices/bindings` | 创建绑定（账号↔工作区↔浏览器） |
| DELETE | `/api/devices/bindings/{id}` | 解除绑定 |

---

## 三、V1 简化

- 工作区 health-check：`os.path.isdir(root_path)` + 更新 status
- 浏览器实例：只存路径配置，不做真实启动
- 绑定 CRUD：不做自动激活

---

## 四、新文件清单

```
domain/models/device_workspace.py
schemas/devices.py
repositories/device_repository.py
services/device_service.py
api/routes/devices.py
```

---

## 五、验收标准

- [ ] 工作区 CRUD + health-check（目录存在返回 online，不存在返回 offline）
- [ ] 浏览器实例 CRUD
- [ ] 绑定创建/删除
- [ ] 删除工作区时级联清理 browser_instances 和 bindings
