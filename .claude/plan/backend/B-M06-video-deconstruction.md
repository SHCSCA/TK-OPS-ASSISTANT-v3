# B-M06 · 视频拆解中心扩展 后端

**当前状态（2026-04-17）**: 已完成（V1 导入、转写、切段、结构抽取与应用到脚本闭环）。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**前端对应**: M06 `video_deconstruction_center`（扩展）  
**优先级**: P1（在现有基础上扩展）  
**路由前缀**: `/api/video-deconstruction`（扩展现有路由）

---

## 一、数据模型（新增，复用现有 imported_videos）

#### `video_transcripts`（转写结果）
```python
id: str (PK)
imported_video_id: str (FK → imported_videos.id CASCADE)
language: str | None      # zh-CN / en
text: str | None          # 完整转写文本
status: str               # pending / generating / ready / error
ai_job_id: str | None
created_at: str
```

#### `video_segments`（切段结果）
```python
id: str (PK)
imported_video_id: str (FK → imported_videos.id CASCADE)
segment_index: int
start_ms: int
end_ms: int
label: str | None         # intro / main / cta / outro
transcript_text: str | None
metadata_json: str | None
created_at: str
```

#### `video_structure_extractions`（结构抽取）
```python
id: str (PK)
imported_video_id: str (FK → imported_videos.id CASCADE)
script_json: str | None    # 提取到的脚本结构（段落列表）
storyboard_json: str | None  # 提取到的镜头节奏建议
status: str                # pending / generating / ready / error
ai_job_id: str | None
created_at: str
```

---

## 二、API 端点（新增）

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/video-deconstruction/videos/{id}/transcribe` | 触发转写（长任务） |
| GET | `/api/video-deconstruction/videos/{id}/transcript` | 获取转写结果 |
| POST | `/api/video-deconstruction/videos/{id}/segment` | 触发切段（长任务） |
| GET | `/api/video-deconstruction/videos/{id}/segments` | 获取切段结果列表 |
| POST | `/api/video-deconstruction/videos/{id}/extract-structure` | 触发结构抽取（长任务） |
| GET | `/api/video-deconstruction/videos/{id}/structure` | 获取结构抽取结果 |
| POST | `/api/video-deconstruction/extractions/{id}/apply-to-project` | 回流到脚本/分镜 |

---

## 三、V1 简化

- **转写**：无真实 ASR Provider 时，创建 transcript 记录，返回 pending_provider
- **切段**：按固定时长（30s）自动切分为 segments（规则切段）
- **结构抽取**：如有转写文本，按段落生成简单 script_json 草稿
- **回流**：创建新 script_versions 记录（source=video_extraction）

---

## 四、新文件清单

```
domain/models/video_deconstruction.py  # Transcript / Segment / StructureExtraction
schemas/video_deconstruction.py        # 扩展现有 schema 文件
repositories/video_deconstruction_repository.py  # 扩展现有 repo
services/video_deconstruction_service.py         # 扩展现有 service（新增转写/切段方法）
api/routes/video_deconstruction.py     # 在现有路由文件追加新端点
```

---

## 五、验收标准

- [ ] `POST .../transcribe` 创建 transcript 记录，返回 status=generating/pending_provider
- [ ] `POST .../segment` 按规则切分，返回 ≥3 个 segments
- [ ] `POST .../apply-to-project` 创建新 script_version（source=video_extraction）
- [ ] 现有导入功能不受影响
