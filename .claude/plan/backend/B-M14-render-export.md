# B-M14 · 渲染与导出中心 后端

**当前状态（2026-04-17）**: 已完成（V1 导出配置、渲染任务、取消与重试闭环）。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**前端对应**: M14 `render_export_center`  
**优先级**: P1  
**路由前缀**: `/api/renders`

---

## 一、数据模型

#### `export_profiles`（导出配置模板）
```python
id: str (PK)
name: str
format: str           # mp4 / mov / webm
resolution: str       # 1080x1920 / 1920x1080
fps: int = 30
video_bitrate: str    # 8000k
audio_policy: str     # merge_all / voice_only / music_only
subtitle_policy: str  # burn_in / sidecar / none
config_json: str | None
is_default: bool = False
created_at: str
```

#### `render_tasks`
```python
id: str (PK)
project_id: str (FK → projects.id)
timeline_id: str | None  # FK → timelines.id
export_profile_id: str | None (FK → export_profiles.id)
status: str              # queued / rendering / completed / failed / cancelled
progress: int = 0        # 0-100
output_path: str | None  # 生成文件的本地路径
output_asset_id: str | None  # 注册到资产中心后
error_message: str | None
created_at: str
started_at: str | None
completed_at: str | None
```

---

## 二、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/renders/profiles` | 获取导出配置列表 |
| POST | `/api/renders/profiles` | 创建导出配置 |
| GET | `/api/renders/tasks` | 获取渲染任务列表（支持 ?project_id=&status=） |
| POST | `/api/renders/projects/{project_id}/tasks` | 新建渲染任务 |
| GET | `/api/renders/tasks/{task_id}` | 获取任务详情 |
| POST | `/api/renders/tasks/{task_id}/cancel` | 取消排队/运行中任务 |
| POST | `/api/renders/tasks/{task_id}/retry` | 失败后重试 |

---

## 三、Schema (Pydantic)

```python
class ExportProfileDto(BaseModel):
    id: str
    name: str
    format: str
    resolution: str
    fps: int
    audioPolicy: str
    subtitlePolicy: str
    isDefault: bool

class RenderTaskDto(BaseModel):
    id: str
    projectId: str
    status: str
    progress: int
    outputPath: str | None
    errorMessage: str | None
    createdAt: str
    startedAt: str | None
    completedAt: str | None

class CreateRenderTaskInput(BaseModel):
    exportProfileId: str
    timelineId: str | None = None
```

---

## 四、长任务设计（V1 简化）

- V1 不做真实 FFmpeg 渲染，创建任务后状态为 `queued`，ws 广播 `task.started`
- 状态流转：queued → rendering（模拟 2s 延迟）→ completed（模拟成功）
- 真实 FFmpeg 集成在 V2 实现

---

## 五、WebSocket 事件

```json
{"type": "task.progress", "taskId": "xxx", "taskType": "render", "progress": 45, "message": "渲染第 45 帧..."}
{"type": "task.completed", "taskId": "xxx", "outputPath": "/path/to/output.mp4"}
{"type": "task.failed", "taskId": "xxx", "error": "FFmpeg 编码失败", "error_code": "render_encode_error"}
```

---

## 六、新文件清单

```
domain/models/render_task.py
schemas/renders.py
repositories/render_repository.py
services/render_service.py
api/routes/renders.py
```

---

## 七、验收标准

- [ ] `GET /api/renders/tasks` 返回按状态分组的任务列表
- [ ] 新建任务 → status=queued，ws 广播 task.started
- [ ] cancel/retry 接口功能正常
- [ ] 默认导出配置 `GET /api/renders/profiles` 至少1条
