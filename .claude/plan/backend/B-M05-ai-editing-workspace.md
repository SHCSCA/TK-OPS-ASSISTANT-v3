# B-M05 · AI 剪辑工作台 后端

**当前状态（2026-04-17）**: 已完成（V1 时间线草稿、时间线更新与 AI 命令阻断闭环）。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**前端对应**: M05 `ai_editing_workspace`  
**优先级**: P0  
**路由前缀**: `/api/workspace`

---

## 一、数据模型

### 新建表

#### `timelines`
```python
id: str (PK, uuid)
project_id: str (FK → projects.id CASCADE)
revision: int
status: str  # draft / committed
duration_ms: int | None
is_current: bool  # 当前版本标记
created_at: str
updated_at: str
```

#### `timeline_tracks`
```python
id: str (PK)
timeline_id: str (FK → timelines.id CASCADE)
kind: str  # video / audio / subtitle
name: str  # V1/V2/A1
order_index: int
locked: bool = False
```

#### `timeline_clips`
```python
id: str (PK)
track_id: str (FK → timeline_tracks.id CASCADE)
asset_id: str | None  # FK → assets.id（资产中心接入后）
source_type: str  # asset / imported_video / ai_generated
source_id: str | None
position_ms: int  # 在轨道上的起始位置
duration_ms: int
in_point_ms: int = 0  # 素材裁剪入点
out_point_ms: int | None
metadata_json: str | None  # 额外属性
created_at: str
```

#### `workspace_ai_commands`
```python
id: str (PK)
project_id: str (FK → projects.id)
timeline_id: str (FK → timelines.id)
capability_id: str  # magic_cut / style_transfer / denoise
status: str  # pending / running / completed / failed
ai_job_id: str | None (FK → ai_job_records.id)
result_json: str | None  # AI 输出草稿，需用户确认才写入时间线
created_at: str
```

---

## 二、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/workspace/projects/{project_id}/timeline` | 获取当前时间线（含轨道和片段） |
| POST | `/api/workspace/projects/{project_id}/timeline` | 创建新时间线版本 |
| PATCH | `/api/workspace/timelines/{timeline_id}` | 更新时间线元数据 |
| GET | `/api/workspace/timelines/{timeline_id}/tracks` | 获取轨道列表 |
| POST | `/api/workspace/timelines/{timeline_id}/tracks` | 新增轨道 |
| PATCH | `/api/workspace/timeline-clips/{clip_id}` | 更新片段（位置/时长/裁剪点） |
| POST | `/api/workspace/timeline-clips` | 添加片段到轨道 |
| DELETE | `/api/workspace/timeline-clips/{clip_id}` | 删除片段 |
| POST | `/api/workspace/projects/{project_id}/ai-commands` | 触发 AI 命令（魔法剪/风格/降噪） |
| GET | `/api/workspace/ai-commands/{command_id}` | 查询 AI 命令状态 |
| POST | `/api/workspace/ai-commands/{command_id}/apply` | 确认将 AI 结果写入时间线 |
| POST | `/api/workspace/timelines/{timeline_id}/commit` | 提交版本快照 |

---

## 三、Schema (Pydantic)

```python
# 输出 DTO
class TimelineClipDto(BaseModel):
    id: str
    trackId: str
    sourceType: str
    sourceId: str | None
    positionMs: int
    durationMs: int
    inPointMs: int
    outPointMs: int | None
    metadata: dict | None

class TimelineTrackDto(BaseModel):
    id: str
    kind: str
    name: str
    orderIndex: int
    locked: bool
    clips: list[TimelineClipDto]

class TimelineDto(BaseModel):
    id: str
    projectId: str
    revision: int
    status: str
    durationMs: int | None
    tracks: list[TimelineTrackDto]

# AI 命令触发
class AICommandInput(BaseModel):
    capabilityId: str  # magic_cut / style_transfer / denoise
    parameters: dict = {}
```

---

## 四、V1 实现约束

- **时间线 CRUD 优先**：V1 先实现时间线、轨道、片段的增删改查，不做实际媒体处理
- **AI 命令简化**：创建 `workspace_ai_commands` 记录和 `ai_job_records`，返回 `pending` 状态，不调用真实 Provider
- **WebSocket 广播**：AI 命令状态变化通过 `ws_manager.broadcast` 推送
- **不需要媒体解析**：片段的时长和属性由前端传入，后端只存储和校验

---

## 五、新文件清单

```
apps/py-runtime/src/
  domain/models/timeline.py       # Timeline / TimelineTrack / TimelineClip
  domain/models/ai_command.py     # WorkspaceAICommand
  schemas/workspace.py            # DTO + Input schemas
  repositories/timeline_repository.py
  services/workspace_service.py
  api/routes/workspace.py
```

---

## 六、验收标准

- [ ] `GET /api/workspace/projects/{id}/timeline` 返回含轨道片段的完整时间线
- [ ] 新增/删除片段持久化到 SQLite
- [ ] 触发 AI 命令创建记录，返回 `pending` 状态
- [ ] 所有错误返回 `{"ok": false, "error_code": "..."}`
- [ ] 新路由注册到 `factory.py`
