# B-M07 · 配音中心 后端

**当前状态（2026-04-17）**: 已完成（V1 音色列表、配音轨查询、生成与删除闭环）。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**前端对应**: M07 `voice_studio`  
**优先级**: P1  
**路由前缀**: `/api/voice`

---

## 一、数据模型

### 新建表

#### `voice_profiles`（音色配置）
```python
id: str (PK)
provider: str       # openai / azure / local
voice_id: str       # Provider 侧的音色 ID
display_name: str   # 展示名称（如"磁性男声"）
locale: str         # zh-CN / en-US
tags: str           # JSON 数组，如 ["磁性", "稳重"]
config_json: str | None  # 额外参数
enabled: bool = True
created_at: str
```

#### `voice_tracks`（配音轨版本）
```python
id: str (PK)
project_id: str (FK → projects.id CASCADE)
revision: int
source_text: str        # 完整脚本文本
profile_id: str | None (FK → voice_profiles.id)
status: str             # draft / generating / ready / error
audio_asset_id: str | None  # 生成完毕后关联到资产中心
ai_job_id: str | None (FK → ai_job_records.id)
error_message: str | None
created_at: str
```

#### `voice_track_segments`（段落级配音）
```python
id: str (PK)
track_id: str (FK → voice_tracks.id CASCADE)
segment_index: int
text: str           # 段落文本
start_ms: int | None  # 在整轨中的起始时间码
end_ms: int | None
audio_asset_id: str | None
created_at: str
```

---

## 二、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/voice/profiles` | 获取全部音色列表 |
| POST | `/api/voice/profiles/test` | 试听音色（触发短 TTS，返回 audio_url） |
| GET | `/api/voice/projects/{project_id}/tracks` | 获取项目配音轨列表 |
| POST | `/api/voice/projects/{project_id}/tracks/generate` | 触发 TTS 配音（长任务） |
| GET | `/api/voice/tracks/{track_id}` | 获取配音轨详情（含段落列表） |
| POST | `/api/voice/tracks/{track_id}/apply-to-timeline` | 将配音轨推送到时间线 |
| DELETE | `/api/voice/tracks/{track_id}` | 删除配音轨版本 |

---

## 三、Schema (Pydantic)

```python
class VoiceProfileDto(BaseModel):
    id: str
    provider: str
    voiceId: str
    displayName: str
    locale: str
    tags: list[str]
    enabled: bool

class VoiceTrackGenerateInput(BaseModel):
    profileId: str
    sourceText: str
    # 可选参数
    speed: float = 1.0
    pitch: float = 0.0

class VoiceTrackSegmentDto(BaseModel):
    id: str
    segmentIndex: int
    text: str
    startMs: int | None
    endMs: int | None
    audioAssetId: str | None

class VoiceTrackDto(BaseModel):
    id: str
    projectId: str
    revision: int
    status: str
    profileId: str | None
    aiJobId: str | None
    segments: list[VoiceTrackSegmentDto]
    createdAt: str
```

---

## 四、长任务设计

```
POST /api/voice/projects/{id}/tracks/generate
  → 创建 voice_tracks (status=generating)
  → 创建 ai_job_records (capability_id=tts_generation)
  → 启动后台任务（线程/asyncio）
  → 返回 {"ok": true, "data": {"trackId": "...", "status": "generating"}}

后台任务流程：
  1. 将文本按句/段切分
  2. 逐段调用 TTS Provider
  3. 每段完成 → ws_manager.broadcast(task.progress)
  4. 生成完毕 → 合并音频 → 写入资产中心
  5. 更新 voice_tracks.status = "ready"
  6. ws_manager.broadcast(task.completed)
  7. 失败 → status = "error" + ws_manager.broadcast(task.failed)
```

---

## 五、V1 简化方案

- **音色列表**：优先从 `system_config` 或静态 JSON 读取，无需 `voice_profiles` 表（但建议建表）
- **TTS 生成**：无 Provider 配置时，创建记录后立即返回 `pending_provider`，前端展示"待配置 AI Provider"
- **音频文件**：有真实 TTS 时，生成的 mp3 存到 `config.cache_dir/voice/{track_id}/`，再注册到资产中心

---

## 六、新文件清单

```
domain/models/voice_track.py      # VoiceProfile / VoiceTrack / VoiceTrackSegment
schemas/voice.py
repositories/voice_repository.py
services/voice_service.py
api/routes/voice.py
```

---

## 七、验收标准

- [ ] `GET /api/voice/profiles` 返回音色列表（≥1条，可来自静态配置）
- [ ] `POST .../generate` 创建 voice_tracks 记录，返回 trackId + status
- [ ] `GET /api/voice/tracks/{id}` 返回轨道详情含段落列表
- [ ] 无 Provider 时不崩溃，返回合理 error_code
- [ ] 新路由注册到 factory.py
