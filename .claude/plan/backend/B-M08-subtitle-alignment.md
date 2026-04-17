# B-M08 · 字幕对齐中心 后端

**当前状态（2026-04-17）**: 已完成（V1 字幕轨生成、查询、更新与删除闭环）。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**前端对应**: M08 `subtitle_alignment_center`  
**优先级**: P1  
**路由前缀**: `/api/subtitles`

---

## 一、数据模型

#### `subtitle_tracks`
```python
id: str (PK)
project_id: str (FK → projects.id CASCADE)
revision: int
source: str           # manual / ai_generated / imported_srt
status: str           # draft / generating / ready / error
based_on_voice_track_id: str | None
style_config_json: str | None  # 字体/颜色/位置
ai_job_id: str | None
created_at: str
```

#### `subtitle_segments`
```python
id: str (PK)
track_id: str (FK → subtitle_tracks.id CASCADE)
segment_index: int
text: str
start_ms: int
end_ms: int
confidence: float | None  # AI 置信度
locked: bool = False       # 用户已手动校正，不被覆盖
created_at: str
updated_at: str
```

---

## 二、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/subtitles/projects/{project_id}/tracks` | 获取项目字幕轨列表 |
| POST | `/api/subtitles/projects/{project_id}/tracks/generate` | 触发 AI 字幕生成（长任务） |
| POST | `/api/subtitles/projects/{project_id}/tracks/from-script` | 从脚本文本创建草稿字幕（按句切分） |
| GET | `/api/subtitles/tracks/{track_id}` | 获取字幕轨详情（含段落） |
| PATCH | `/api/subtitles/tracks/{track_id}/segments/{segment_id}` | 编辑单条字幕（文本/时间码/locked） |
| POST | `/api/subtitles/tracks/{track_id}/align` | 触发字幕对齐（长任务） |
| POST | `/api/subtitles/tracks/{track_id}/apply-to-timeline` | 将字幕轨写入时间线 |
| DELETE | `/api/subtitles/tracks/{track_id}` | 删除字幕轨版本 |

---

## 三、Schema (Pydantic)

```python
class SubtitleSegmentDto(BaseModel):
    id: str
    segmentIndex: int
    text: str
    startMs: int
    endMs: int
    confidence: float | None
    locked: bool

class SubtitleTrackDto(BaseModel):
    id: str
    projectId: str
    revision: int
    source: str
    status: str
    segments: list[SubtitleSegmentDto]
    createdAt: str

class SubtitleSegmentUpdateInput(BaseModel):
    text: str | None = None
    startMs: int | None = None
    endMs: int | None = None
    locked: bool | None = None
```

---

## 四、V1 简化方案

- **从脚本生成草稿**：`POST .../from-script` 按中文句号/问号/感叹号切分脚本，自动分配均匀时间码，不调用 AI
- **AI 字幕生成**：无 Provider 时返回 `pending_provider`
- **时间码对齐**：V1 不做真实对齐，返回当前段落数据不变

---

## 五、新文件清单

```
domain/models/subtitle_track.py
schemas/subtitles.py
repositories/subtitle_repository.py
services/subtitle_service.py
api/routes/subtitles.py
```

---

## 六、验收标准

- [ ] `GET .../tracks` 返回字幕轨列表（空数组不崩溃）
- [ ] `POST .../from-script` 创建草稿字幕段落（≥3段）
- [ ] 单段落 PATCH 更新持久化
- [ ] locked 字段保护用户校正不被覆盖
