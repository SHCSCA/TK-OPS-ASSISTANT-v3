# B-M09 · 资产中心 后端

**当前状态（2026-04-17）**: 已完成（V1 资产列表、导入、详情、更新、删除与引用闭环）。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**前端对应**: M09 `asset_library`  
**优先级**: P1  
**路由前缀**: `/api/assets`

---

## 一、数据模型

#### `assets`
```python
id: str (PK)
project_id: str | None  # None = 全局资产
scope: str              # project / global
kind: str               # video / image / audio / subtitle_template / cover
file_path: str          # 本地绝对路径
mime_type: str | None
size_bytes: int
source: str             # imported / generated / uploaded
checksum: str | None    # SHA256，用于去重
tags: str               # JSON 数组
metadata_json: str | None  # 宽表，视频宽高/时长等
status: str             # active / deleted / missing
created_at: str
updated_at: str
```

#### `asset_references`
```python
id: str (PK)
asset_id: str (FK → assets.id CASCADE)
project_id: str | None
ref_type: str    # timeline_clip / voice_track / subtitle_track / cover
ref_id: str      # 引用对象 ID
usage: str       # 描述用途
created_at: str
```

---

## 二、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/assets` | 获取资产列表（支持 ?project_id=&kind=&scope=） |
| POST | `/api/assets/import` | 导入本地文件为资产 |
| GET | `/api/assets/{asset_id}` | 获取资产详情 |
| PATCH | `/api/assets/{asset_id}` | 更新资产元数据（名称/标签） |
| DELETE | `/api/assets/{asset_id}` | 删除资产（先检查引用） |
| GET | `/api/assets/{asset_id}/references` | 获取资产引用列表 |

---

## 三、Schema (Pydantic)

```python
class AssetDto(BaseModel):
    id: str
    projectId: str | None
    scope: str
    kind: str
    filePath: str
    mimeType: str | None
    sizeBytes: int
    source: str
    tags: list[str]
    status: str
    createdAt: str

class AssetImportInput(BaseModel):
    filePath: str  # 本地绝对路径
    kind: str
    projectId: str | None = None
    tags: list[str] = []

class AssetUpdateInput(BaseModel):
    tags: list[str] | None = None
```

---

## 四、V1 简化方案

- 纯 CRUD + 文件存在性检查（`os.path.exists`）
- `DELETE` 前查 `asset_references`，有引用则返回 `error_code: asset_has_references`
- 缩略图生成、波形预览延后
- `imported_videos` 生成后可注册为 assets（可选）

---

## 五、新文件清单

```
domain/models/asset.py
schemas/assets.py
repositories/asset_repository.py
services/asset_service.py
api/routes/assets.py
```

---

## 六、验收标准

- [ ] `GET /api/assets` 支持 kind 筛选，返回列表
- [ ] `POST /api/assets/import` 导入本地文件，返回 AssetDto
- [ ] `DELETE` 有引用时返回 error_code，无引用时成功删除
