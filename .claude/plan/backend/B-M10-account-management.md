# B-M10 · 账号管理 后端

**当前状态（2026-04-17）**: 已完成（V1 账号、分组、成员管理与状态刷新闭环，含 `status-check` 兼容别名）。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**前端对应**: M10 `account_management`  
**优先级**: P2  
**路由前缀**: `/api/accounts`

---

## 一、数据模型

#### `accounts`
```python
id: str (PK)
platform: str         # tiktok
handle: str           # @用户名
display_name: str
avatar_url: str | None
status: str           # active / limited / offline / error
health_status: str    # healthy / warning / unknown
notes: str = ""
last_checked_at: str | None
created_at: str
updated_at: str
```

#### `account_groups`
```python
id: str (PK)
name: str
description: str = ""
created_at: str
```

#### `account_group_members`
```python
account_id: str (FK → accounts.id CASCADE)
group_id: str (FK → account_groups.id CASCADE)
PRIMARY KEY (account_id, group_id)
```

---

## 二、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/accounts` | 获取账号列表（支持 ?group_id=&status=） |
| POST | `/api/accounts` | 新建账号 |
| PATCH | `/api/accounts/{account_id}` | 更新账号信息 |
| DELETE | `/api/accounts/{account_id}` | 删除账号 |
| POST | `/api/accounts/{account_id}/status-check` | 手动触发状态检查 |
| GET | `/api/accounts/groups` | 获取分组列表 |
| POST | `/api/accounts/groups` | 创建分组 |
| POST | `/api/accounts/{account_id}/groups/{group_id}` | 添加账号到分组 |
| DELETE | `/api/accounts/{account_id}/groups/{group_id}` | 从分组移除 |

---

## 三、Schema (Pydantic)

```python
class AccountDto(BaseModel):
    id: str
    platform: str
    handle: str
    displayName: str
    avatarUrl: str | None
    status: str
    healthStatus: str
    groups: list[str]  # group name 列表
    lastCheckedAt: str | None
    createdAt: str

class CreateAccountInput(BaseModel):
    platform: str = "tiktok"
    handle: str
    displayName: str
    avatarUrl: str | None = None

class AccountUpdateInput(BaseModel):
    displayName: str | None = None
    status: str | None = None
    notes: str | None = None
```

---

## 四、V1 简化

- 纯 CRUD，不接入真实平台 API
- `status-check` 接口：返回当前状态不变，记录 `last_checked_at`
- 敏感信息（Cookie、Token）不存入此表，由安全存储单独处理

---

## 五、新文件清单

```
domain/models/account.py
schemas/accounts.py
repositories/account_repository.py
services/account_service.py
api/routes/accounts.py
```

---

## 六、验收标准

- [ ] CRUD 全部接口正常
- [ ] 分组 CRUD 正常
- [ ] 账号列表支持 group_id 筛选
- [ ] 删除账号时清理 group_members 关联
