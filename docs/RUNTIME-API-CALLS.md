# Runtime API 与前端调用唯一文档

> 本文件是 TK-OPS 前后端 Runtime 接口与前端调用关系的唯一真源。
> 任何新增、删除、重命名、字段调整、状态语义调整或调用入口调整，都必须在同一次变更中更新本文件。
> 编码约定：本文档和相关中文产品文档统一使用 UTF-8 无 BOM 保存；读取、生成、校验脚本必须显式按 UTF-8 处理，避免中文文案在 PowerShell、测试输出或 IDE 中出现乱码。

## 0. 状态图例与覆盖度总览(2026-04-17 快照)

> 本节回答："本文档当前已经登记到哪一步,哪些 Runtime 实际接口还没进入文档"。详细缺口与未来排期请看 `docs/BACKEND-REQUIREMENTS-2026-04-17.md`。

### 0.1 状态图例

| 标记 | 含义 |
| --- | --- |
| ✅ | 已完成：Route + Service + Schema + 前端调用 + Contract Test + 本文档 全部就绪 |
| 🚧 | 开发中：Route 已实现但本文档未覆盖,或前端尚未对接,或测试未补齐 |
| 📋 | 待开发：完全缺失,需走 plan/spec → 实现 → 文档 → 测试 全链路 |

### 0.2 模块覆盖度总览

| 模块 | 真实路由数 | 本文档覆盖 | 状态 | 备注 |
| --- | ---: | ---: | --- | --- |
| M01 License | 2 | 0 | 🚧 | 已落地但未在本文件登记;指纹接口待开发 |
| M02 Dashboard | 4 | 0 | 🚧 | 已落地但未登记;sparkline/quick-jump 待开发 |
| M03 Scripts | 4 | 0 | 🚧 | 已落地但未登记;变体/版本待开发 |
| M04 Storyboards | 3 | 0 | 🚧 | 已落地但未登记;Shot CRUD 待开发 |
| **M05 Workspace** | 4 | 4 | ✅ | 见 §4 |
| M06 Video Decon | 3 | 0 | 🚧 | 仅 import/list/delete,未登记;阶段接口待开发 |
| **M07 Voice** | 5 | 5 | ✅ | 见 §5 |
| **M08 Subtitles** | 5 | 5 | ✅ | 见 §6 |
| **M09 Assets** | 10 | 8 | 🚧 | 见 §7;refs/{id} 子接口待登记 |
| M10 Accounts | 13 | 0 | 🚧 | 全部 13 个端点已实现但未登记 |
| M11 Devices | 6 | 0 | 🚧 | workspaces CRUD + health-check 已实现未登记 |
| M12 Automation | 7 | 0 | 🚧 | tasks CRUD + trigger + runs 已实现未登记 |
| M13 Publishing | 8 | 0 | 🚧 | plans CRUD + precheck/submit/cancel 已实现未登记 |
| M14 Renders | 6 | 0 | 🚧 | tasks CRUD + cancel 已实现未登记 |
| M15 Review | 3 | 0 | 🚧 | summary/analyze 已实现未登记 |
| **M16 Settings** | 9 | 9 | ✅ | 见 §8 |
| Tasks/WS | 4 | 1 | 🚧 | tasks 列表/cancel 实现但未统一 TaskBus;ws 通道存在 |
| **§1 跨页基础设施** | 0 | 0 | 📋 | 自动保存/上传/分页/撤销/审计 全部待开发(见 BACKEND-REQUIREMENTS §1.8 ~ §1.13) |
| **合计** | **96** | **32 (33%)** | — | — |

### 0.3 截至本快照的关键事实

- **5 个模块**(M05/M07/M08/M09/M16)已经走完"实现 → 文档 → 前端 → 测试"四步,可作为"完整模板"参考
- **11 个模块**(M01/M02/M03/M04/M06/M10/M11/M12/M13/M14/M15)的接口已经存在,但本文档未登记;前端 client/store/test 也未对应,**这是当前最大的债**
- **跨页基础设施**(§1.8 自动保存 / §1.9 分片上传 / §1.10 分页 / §1.11 撤销重做 / §1.12 个人化 / §1.13 审计备份)目前完全未实现

### 0.4 阅读本文档时的注意点

- 本文档下文每一节(§4 ~ §8)只覆盖 ✅ 已完成模块。如需查阅 🚧 与 📋 状态接口,请到 `docs/BACKEND-REQUIREMENTS-2026-04-17.md` § 2 模块矩阵
- 当一个 🚧 模块完成"补登记"后,会从本节表格删除并新增到下文章节,同时本节"覆盖"列 +N
- 任何接口变更必须**同时**更新:本节统计表 + 对应章节 + 后端代码 + 前端 client + contract test

---

## 1. 使用规则

- 唯一性：不要再为单个模块创建并行 API 文档。模块计划、spec、测试说明可以引用本文件，但不能复制出另一套接口真源。
- 同步性：后端 route、service、schema、前端 `runtime-client.ts`、store、页面状态和 contract tests 任一项变化，都必须同步更新本文件。
- 入口约束：前端页面不得直接拼接 Runtime URL；所有 HTTP 调用必须先进入 `apps/desktop/src/app/runtime-client.ts`，再由 store 或页面消费。
- 信封约束：Runtime HTTP 成功统一返回 `{ "ok": true, "data": ... }`，失败统一返回 `{ "ok": false, "error": "中文可见错误" }`。
- 测试约束：接口变更必须同时更新 `tests/contracts/`；前端调用变更必须同时更新 `apps/desktop/tests/`。
- 文档优先级：当本文件与临时计划冲突时，先更新本文件，再进入实现；当本文件与 `docs/PRD.md`、`docs/UI-DESIGN-PRD.md`、`docs/ARCHITECTURE-BOOTSTRAP.md` 冲突时，先回到真源文档对齐。

## 2. 更新流程

每次接口或调用变更必须按以下顺序处理：

1. 更新本文件中的接口表、请求/响应字段、前端调用函数和测试入口。
2. 更新或新增后端 schema、route、service、repository。
3. 更新 `apps/desktop/src/types/runtime.ts`。
4. 更新 `apps/desktop/src/app/runtime-client.ts`。
5. 更新对应 Pinia store、页面状态和错误反馈。
6. 更新 contract tests、client tests、store/page tests。
7. 运行验证命令并记录结果。

验收时必须能回答：

- 后端接口在哪里定义。
- 前端通过哪个函数调用。
- 哪个 store 或页面消费。
- 成功和失败信封是什么。
- 哪个测试覆盖该契约。
- 本文件是否已同步更新。

## 3. 全局 Runtime 信封

成功响应：

```json
{
  "ok": true,
  "data": {}
}
```

失败响应：

```json
{
  "ok": false,
  "error": "操作失败，请稍后重试"
}
```

要求：

- `error` 必须是中文、用户可见、可恢复的提示。
- 不得向 UI 暴露 traceback。
- 后端异常必须记录日志。
- 404、409、422、500 等错误也必须通过统一信封转换。

## 4. M05 AI 剪辑工作台 ✅ 已交付

> 2026-04-17 新增：M05-A 只建立项目时间线草稿的真实 Runtime 闭环。工作台不得继续展示页面内静态假轨道、假素材、假视频进度或假 AI 结果。无时间线时返回中性空态；AI 魔法剪入口本批返回 `blocked`，不创建假任务。

### 5.1 数据对象

`WorkspaceTimelineClipDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 片段 ID |
| `trackId` | `string` | 所属轨道 ID |
| `sourceType` | `string` | `asset`、`imported_video`、`voice_track`、`subtitle_track`、`manual` 等来源 |
| `sourceId` | `string \| null` | 来源对象 ID |
| `label` | `string` | 片段显示名称 |
| `startMs` | `number` | 时间线起点 |
| `durationMs` | `number` | 片段时长 |
| `inPointMs` | `number` | 素材入点 |
| `outPointMs` | `number \| null` | 素材出点 |
| `status` | `string` | `ready`、`blocked`、`missing_source`、`error` 等状态 |

`WorkspaceTimelineTrackDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 轨道 ID |
| `kind` | `video \| audio \| subtitle` | 轨道类型 |
| `name` | `string` | 轨道名称 |
| `orderIndex` | `number` | 轨道排序 |
| `locked` | `boolean` | 是否锁定 |
| `muted` | `boolean` | 是否静音或隐藏 |
| `clips` | `WorkspaceTimelineClipDto[]` | 片段列表 |

`WorkspaceTimelineDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 时间线 ID |
| `projectId` | `string` | 项目 ID |
| `name` | `string` | 时间线名称 |
| `status` | `draft \| committed` | 时间线状态 |
| `durationSeconds` | `number \| null` | 当前时间线时长 |
| `source` | `manual \| imported_video \| generated` | 创建来源 |
| `tracks` | `WorkspaceTimelineTrackDto[]` | 轨道列表 |
| `createdAt` | `string` | UTC ISO 时间 |
| `updatedAt` | `string` | UTC ISO 时间 |

`WorkspaceTimelineResultDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `timeline` | `WorkspaceTimelineDto \| null` | 当前项目时间线；没有草稿时为 `null` |
| `message` | `string` | 中文结果说明 |

`WorkspaceAICommandResultDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | `blocked` | 本批固定为阻断态 |
| `task` | `object \| null` | 本批不创建任务，固定为 `null` |
| `message` | `string` | 中文阻断说明 |

### 5.2 后端接口与前端调用

| 状态 | 方法 | 路径 | 后端入口 | 前端调用 | 消费方 | 测试 |
| --- | --- | --- | --- | --- | --- | --- |
| 当前 | `GET` | `/api/workspace/projects/{project_id}/timeline` | `api/routes/workspace.py:get_project_timeline` | `fetchWorkspaceTimeline(projectId)` | `editing-workspace` store、AI 剪辑工作台页面 | `tests/contracts/test_workspace_runtime_contract.py`、`apps/desktop/tests/runtime-client-workspace.spec.ts` |
| 当前 | `POST` | `/api/workspace/projects/{project_id}/timeline` | `api/routes/workspace.py:create_project_timeline` | `createWorkspaceTimeline(projectId, input)` | `editing-workspace` store、空态创建入口 | `tests/contracts/test_workspace_runtime_contract.py`、`tests/runtime/test_workspace_service.py` |
| 当前 | `PATCH` | `/api/workspace/timelines/{timeline_id}` | `api/routes/workspace.py:update_timeline` | `updateWorkspaceTimeline(timelineId, input)` | `editing-workspace` store、保存时间线动作 | `tests/contracts/test_workspace_runtime_contract.py`、`tests/runtime/test_workspace_service.py` |
| 当前 | `POST` | `/api/workspace/projects/{project_id}/ai-commands` | `api/routes/workspace.py:run_ai_command` | `runWorkspaceAICommand(projectId, input)` | `editing-workspace` store、AI 魔法剪入口 | `tests/contracts/test_workspace_runtime_contract.py`、`tests/runtime/test_workspace_service.py` |

### 4.3 空态与阻断态

无时间线响应：

```json
{
  "ok": true,
  "data": {
    "timeline": null,
    "message": "当前项目还没有时间线草稿。"
  }
}
```

AI 魔法剪阻断响应：

```json
{
  "ok": true,
  "data": {
    "status": "blocked",
    "task": null,
    "message": "AI 剪辑命令尚未接入 Provider，本阶段仅保存时间线草稿。"
  }
}
```

### 4.4 实现约束

- 本批复用 `timelines.tracks_json`，不新增轨道/片段表。
- `POST /timeline` 创建真实空草稿，不自动填充示例轨道。
- `PATCH /timeline` 只接受 `video`、`audio`、`subtitle` 三类轨道。
- AI 命令未接入 Provider 时返回 `blocked`，不得创建假 TaskBus 任务。
- 页面必须通过 `runtime-client.ts` 与 Pinia store 消费，不得直接 `fetch`。

## 5. M07 配音中心 ✅ 已交付

> 2026-04-16 新增：M07 配音中心第一批只建立真实 Runtime 闭环和 UI 工作台底座。无可用 TTS Provider 时，`POST /api/voice/projects/{project_id}/tracks/generate` 必须创建真实 `VoiceTrack` 记录并返回 `blocked` 状态和中文说明，不得伪造成音频生成成功。页面不得继续使用前端 `setTimeout` 模拟生成，所有调用必须通过 `runtime-client.ts` 和 `voice-studio` store。

### 4.1 数据对象

`VoiceProfileDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 前端选择用的稳定音色 ID |
| `provider` | `string` | 当前为 `pending_provider` 或后续真实 Provider |
| `voiceId` | `string` | Provider 侧音色 ID 或占位配置 ID |
| `displayName` | `string` | 中文展示名称 |
| `locale` | `string` | 语言区域，如 `zh-CN` |
| `tags` | `string[]` | 中文标签 |
| `enabled` | `boolean` | 是否可选 |

`VoiceTrackSegmentDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `segmentIndex` | `number` | 段落序号，从 0 开始 |
| `text` | `string` | 段落文本 |
| `startMs` | `number | null` | 真实音频起始时间；无音频时为 `null` |
| `endMs` | `number | null` | 真实音频结束时间；无音频时为 `null` |
| `audioAssetId` | `string | null` | 后续资产中心音频资产 ID |

`VoiceTrackDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 配音轨 ID |
| `projectId` | `string` | 项目 ID |
| `timelineId` | `string | null` | 后续时间线 ID |
| `source` | `string` | 本批为 `tts` |
| `provider` | `string | null` | 当前无 Provider 时为 `pending_provider` |
| `voiceName` | `string` | 中文音色名称 |
| `filePath` | `string | null` | 真实音频路径；本批无 Provider 时为 `null` |
| `segments` | `VoiceTrackSegmentDto[]` | 段落映射 |
| `status` | `string` | `blocked`、`ready`、`error` 等 |
| `createdAt` | `string` | UTC ISO 时间 |

`VoiceTrackGenerateInput`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `profileId` | `string` | 选择的音色 ID |
| `sourceText` | `string` | 待配音脚本文本 |
| `speed` | `number` | 0.5 到 2.0 |
| `pitch` | `number` | -50 到 50 |
| `emotion` | `string` | `calm`、`happy`、`news`、`tender` |

`VoiceTrackGenerateResultDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `track` | `VoiceTrackDto` | 已创建的配音轨记录 |
| `task` | `object | null` | 本批无真实任务时为 `null` |
| `message` | `string` | 中文结果说明 |

### 4.2 后端接口与前端调用

| 状态 | 方法 | 路径 | 后端入口 | 前端调用 | 消费方 | 测试 |
| --- | --- | --- | --- | --- | --- | --- |
| 当前 | `GET` | `/api/voice/profiles` | `api/routes/voice.py:list_profiles` | `fetchVoiceProfiles()` | `voice-studio` store、`VoiceProfileRail.vue` | `tests/contracts/test_voice_runtime_contract.py`、`apps/desktop/tests/runtime-client-voice.spec.ts` |
| 当前 | `GET` | `/api/voice/projects/{project_id}/tracks` | `api/routes/voice.py:list_project_tracks` | `fetchVoiceTracks(projectId)` | `voice-studio` store、`VoiceVersionPanel.vue` | `tests/contracts/test_voice_runtime_contract.py`、`apps/desktop/tests/runtime-client-voice.spec.ts` |
| 当前 | `POST` | `/api/voice/projects/{project_id}/tracks/generate` | `api/routes/voice.py:generate_track` | `generateVoiceTrack(projectId, input)` | `voice-studio` store、`VoicePreviewStage.vue` | `tests/contracts/test_voice_runtime_contract.py`、`tests/runtime/test_voice_service.py`、`apps/desktop/tests/voice-studio-store.spec.ts` |
| 当前 | `GET` | `/api/voice/tracks/{track_id}` | `api/routes/voice.py:get_track` | `fetchVoiceTrack(trackId)` | `voice-studio` store、版本详情 | `tests/contracts/test_voice_runtime_contract.py`、`apps/desktop/tests/runtime-client-voice.spec.ts` |
| 当前 | `DELETE` | `/api/voice/tracks/{track_id}` | `api/routes/voice.py:delete_track` | `deleteVoiceTrack(trackId)` | `voice-studio` store、`VoiceVersionPanel.vue` | `tests/contracts/test_voice_runtime_contract.py`、`apps/desktop/tests/voice-studio-store.spec.ts` |

### 5.3 `POST /api/voice/projects/{project_id}/tracks/generate`

请求：

```json
{
  "profileId": "alloy-zh",
  "sourceText": "第一段脚本\n第二段脚本",
  "speed": 1.0,
  "pitch": 0,
  "emotion": "calm"
}
```

无 Provider 时成功响应：

```json
{
  "ok": true,
  "data": {
    "track": {
      "id": "voice-1",
      "projectId": "project-1",
      "timelineId": null,
      "source": "tts",
      "provider": "pending_provider",
      "voiceName": "清晰叙述",
      "filePath": null,
      "segments": [
        {
          "segmentIndex": 0,
          "text": "第一段脚本",
          "startMs": null,
          "endMs": null,
          "audioAssetId": null
        }
      ],
      "status": "blocked",
      "createdAt": "2026-04-16T00:00:00Z"
    },
    "task": null,
    "message": "尚未配置可用 TTS Provider，已保存配音版本草稿。"
  }
}
```

空脚本失败响应：

```json
{
  "ok": false,
  "error": "脚本文本为空，请先在脚本与选题中心创建内容。"
}
```

约束：

- 本批不创建 TaskBus 任务，不广播假进度。
- 不写假 `filePath`，无真实音频时必须为 `null`。
- `segments` 必须来自真实脚本文本切分。
- 真实 TTS Provider、音频落盘、资产注册和时间线落轨必须作为后续独立计划。

## 6. M08 字幕对齐中心 ✅ 已交付

> 2026-04-16 新增：M08 字幕对齐中心第一批只建立真实 Runtime 契约、字幕轨草稿记录和 UI 校对工作台。无可用字幕对齐 Provider 时，`POST /api/subtitles/projects/{project_id}/tracks/generate` 必须创建真实 `SubtitleTrack` 记录并返回 `blocked` 状态和中文说明，不得伪造成自动对齐完成。页面所有字幕读写必须通过 `runtime-client.ts` 和 `subtitle-alignment` store，不得继续使用页面内 `setTimeout`、随机假字幕或 `alert`。

### 6.1 数据对象

`SubtitleStyleDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `preset` | `string` | 当前样式预设，默认 `creator-default` |
| `fontSize` | `number` | 字号，默认 32，范围 18 到 72 |
| `position` | `bottom \| center \| top` | 字幕位置 |
| `textColor` | `string` | 字幕文字颜色 |
| `background` | `string` | 字幕背景，允许 `rgba(...)` |

`SubtitleSegmentDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `segmentIndex` | `number` | 字幕段序号，从 0 开始 |
| `text` | `string` | 字幕文本 |
| `startMs` | `number \| null` | 起始时间；无真实对齐时为 `null` |
| `endMs` | `number \| null` | 结束时间；无真实对齐时为 `null` |
| `confidence` | `number \| null` | 后续 Provider 置信度；本批为 `null` |
| `locked` | `boolean` | 用户是否手动锁定该段 |

`SubtitleTrackDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 字幕轨 ID |
| `projectId` | `string` | 项目 ID |
| `timelineId` | `string \| null` | 后续时间线 ID |
| `source` | `script \| manual \| provider` | 字幕来源，本批生成默认为 `script` |
| `language` | `string` | 语言，如 `zh-CN` |
| `style` | `SubtitleStyleDto` | 字幕样式 |
| `segments` | `SubtitleSegmentDto[]` | 字幕段落 |
| `status` | `blocked \| ready \| error \| aligning` | 字幕轨状态 |
| `createdAt` | `string` | UTC ISO 时间 |

`SubtitleTrackGenerateInput`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `sourceText` | `string` | 待生成字幕草稿的脚本文本 |
| `language` | `string` | 默认 `zh-CN` |
| `stylePreset` | `string` | 默认 `creator-default` |

`SubtitleTrackUpdateInput`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `segments` | `SubtitleSegmentDto[]` | 用户校正后的字幕段 |
| `style` | `SubtitleStyleDto` | 用户调整后的字幕样式 |

`SubtitleTrackGenerateResultDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `track` | `SubtitleTrackDto` | 已创建的字幕轨记录 |
| `task` | `object \| null` | 本批无真实任务时为 `null` |
| `message` | `string` | 中文结果说明 |

### 6.2 后端接口与前端调用

| 状态 | 方法 | 路径 | 后端入口 | 前端调用 | 消费方 | 测试 |
| --- | --- | --- | --- | --- | --- | --- |
| 当前 | `GET` | `/api/subtitles/projects/{project_id}/tracks` | `api/routes/subtitles.py:list_project_tracks` | `fetchSubtitleTracks(projectId)` | `subtitle-alignment` store、`SubtitleVersionPanel.vue` | `tests/contracts/test_subtitle_runtime_contract.py`、`apps/desktop/tests/runtime-client-subtitles.spec.ts` |
| 当前 | `POST` | `/api/subtitles/projects/{project_id}/tracks/generate` | `api/routes/subtitles.py:generate_track` | `generateSubtitleTrack(projectId, input)` | `subtitle-alignment` store、字幕对齐中心页面 | `tests/contracts/test_subtitle_runtime_contract.py`、`tests/runtime/test_subtitle_service.py`、`apps/desktop/tests/subtitle-alignment-store.spec.ts` |
| 当前 | `GET` | `/api/subtitles/tracks/{track_id}` | `api/routes/subtitles.py:get_track` | `fetchSubtitleTrack(trackId)` | `subtitle-alignment` store、版本详情 | `tests/contracts/test_subtitle_runtime_contract.py`、`apps/desktop/tests/runtime-client-subtitles.spec.ts` |
| 当前 | `PATCH` | `/api/subtitles/tracks/{track_id}` | `api/routes/subtitles.py:update_track` | `updateSubtitleTrack(trackId, input)` | `subtitle-alignment` store、`SubtitleSegmentList.vue`、`SubtitleTimingPanel.vue`、`SubtitleStylePanel.vue` | `tests/contracts/test_subtitle_runtime_contract.py`、`tests/runtime/test_subtitle_service.py`、`apps/desktop/tests/subtitle-alignment-store.spec.ts` |
| 当前 | `DELETE` | `/api/subtitles/tracks/{track_id}` | `api/routes/subtitles.py:delete_track` | `deleteSubtitleTrack(trackId)` | `subtitle-alignment` store、`SubtitleVersionPanel.vue` | `tests/contracts/test_subtitle_runtime_contract.py`、`apps/desktop/tests/subtitle-alignment-store.spec.ts` |

### 6.3 `POST /api/subtitles/projects/{project_id}/tracks/generate`

请求：

```json
{
  "sourceText": "第一段脚本\n第二段脚本",
  "language": "zh-CN",
  "stylePreset": "creator-default"
}
```

无 Provider 时成功响应：

```json
{
  "ok": true,
  "data": {
    "track": {
      "id": "subtitle-1",
      "projectId": "project-1",
      "timelineId": null,
      "source": "script",
      "language": "zh-CN",
      "style": {
        "preset": "creator-default",
        "fontSize": 32,
        "position": "bottom",
        "textColor": "#FFFFFF",
        "background": "rgba(0,0,0,0.62)"
      },
      "segments": [
        {
          "segmentIndex": 0,
          "text": "第一段脚本",
          "startMs": null,
          "endMs": null,
          "confidence": null,
          "locked": false
        }
      ],
      "status": "blocked",
      "createdAt": "2026-04-16T00:00:00Z"
    },
    "task": null,
    "message": "尚未配置可用字幕对齐 Provider，已保存字幕草稿。"
  }
}
```

空脚本失败响应：

```json
{
  "ok": false,
  "error": "字幕源文本为空，请先在脚本与选题中心创建内容。"
}
```

约束：

- 本批不创建 TaskBus 任务，不广播假进度。
- 字幕段必须来自真实脚本文本切分，不能写固定演示字幕。
- 无真实对齐时 `startMs`、`endMs`、`confidence` 必须为 `null`。
- 无 Provider 时状态必须为 `blocked`，不能误导为自动对齐完成。
- 真实字幕对齐 Provider、ASR、SRT/VTT 导入导出、TaskBus 长任务和时间线回写必须作为后续独立计划。

### 6.4 前端调用登记

| 函数 | 文件 | Runtime 路径 | 返回类型 | 主要消费方 | 更新要求 |
| --- | --- | --- | --- | --- | --- |
| `fetchSubtitleTracks(projectId)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/subtitles/projects/{project_id}/tracks` | `SubtitleTrackDto[]` | `subtitle-alignment` store、`SubtitleVersionPanel.vue` | 列表必须来自真实 Runtime 记录 |
| `generateSubtitleTrack(projectId, input)` | `apps/desktop/src/app/runtime-client.ts` | `POST /api/subtitles/projects/{project_id}/tracks/generate` | `SubtitleTrackGenerateResultDto` | `subtitle-alignment` store、字幕对齐中心页面 | 无 Provider 时必须展示 `blocked`，不得假成功 |
| `fetchSubtitleTrack(trackId)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/subtitles/tracks/{track_id}` | `SubtitleTrackDto` | `subtitle-alignment` store、版本详情 | 返回段落和样式映射 |
| `updateSubtitleTrack(trackId, input)` | `apps/desktop/src/app/runtime-client.ts` | `PATCH /api/subtitles/tracks/{track_id}` | `SubtitleTrackDto` | `subtitle-alignment` store、字幕段落、时间码、样式面板 | 保存失败必须显示中文错误 |
| `deleteSubtitleTrack(trackId)` | `apps/desktop/src/app/runtime-client.ts` | `DELETE /api/subtitles/tracks/{track_id}` | `void` | `subtitle-alignment` store、版本面板 | 删除后必须刷新列表并清空失效选中态 |

## 7. M09 资产中心 ✅ 已交付

> 2026-04-16 修订：Runtime 启动时会兼容修复旧版 `assets` 表，避免旧本地库缺少 `name`、`type`、`updated_at` 等列导致 `GET /api/assets` 直接 500，也避免旧版 `kind` / `file_name` 非空约束阻断新图片导入。点击“导入资产”必须弹出桌面文件选择器并支持多选；每个被选中的真实本地路径逐个通过 `importAsset(input)` 进入 Runtime。Tauri 主窗口 capability 必须包含 `dialog:allow-open`，否则文件选择器会被运行时权限拒绝；`tauri.conf.json` 必须启用 `app.security.assetProtocol` 并允许用户素材目录，否则 `convertFileSrc(filePath)` 生成的真实预览地址无法在 WebView 中读取。资产中心前端已采用素材墙、批量导入状态、真实本地预览、UTF-8 文档预览和全局右侧抽屉联动；页面不得回退到手动路径输入或图标占位预览。

### 7.1 数据对象

`AssetDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 资产 ID |
| `name` | `string` | 资产名称 |
| `type` | `string` | `video`、`audio`、`image`、`document`、`other` |
| `source` | `string` | `local`、`generated`、`imported` 等真实来源 |
| `filePath` | `string | null` | 本地文件路径 |
| `fileSizeBytes` | `number | null` | 文件大小，不能伪造 |
| `durationMs` | `number | null` | 媒体时长，未知时为 `null` |
| `thumbnailPath` | `string | null` | 缩略图路径，未生成时为 `null` |
| `tags` | `string | null` | JSON 字符串；前端展示前必须安全解析 |
| `projectId` | `string | null` | `null` 表示全局资产，非空表示项目资产 |
| `metadataJson` | `string | null` | 扩展元数据 JSON 字符串 |
| `createdAt` | `string` | 创建时间 |
| `updatedAt` | `string` | 更新时间 |

`AssetReferenceDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 引用 ID |
| `assetId` | `string` | 资产 ID |
| `referenceType` | `string` | `script`、`storyboard`、`timeline`、`render` 等引用类型 |
| `referenceId` | `string` | 引用对象 ID |
| `createdAt` | `string` | 创建时间 |

`AssetImportInput`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `filePath` | `string` | 真实本地文件路径，后端必须检查存在性 |
| `type` | `string` | `video`、`audio`、`image`、`document`、`other` |
| `source` | `string` | 默认 `local`，不得伪造来源 |
| `projectId` | `string | null` | 可选项目归属 |
| `tags` | `string | null` | 可选 JSON 字符串标签 |
| `metadataJson` | `string | null` | 可选扩展元数据 |

`AssetDeleteResult`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `deleted` | `boolean` | 删除是否完成 |

### 7.2 后端接口与前端调用

| 状态 | 方法 | 路径 | 后端入口 | 前端调用 | 消费方 | 测试 |
| --- | --- | --- | --- | --- | --- | --- |
| 当前 | `GET` | `/api/assets?type=&source=&project_id=&q=` | `api/routes/assets.py:list_assets` | `fetchAssets(type?, q?)` | `asset-library` store | `tests/contracts/test_runtime_page_modules_contract.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts` |
| 当前 | `POST` | `/api/assets` | `api/routes/assets.py:create_asset` | 暂无公开页面调用 | 后端测试/内部注册 | `tests/contracts/test_runtime_page_modules_contract.py` |
| 当前 | `POST` | `/api/assets/import` | `api/routes/assets.py:import_asset` | `importAsset(input)` | `asset-library` store、资产中心页面 | `tests/contracts/test_runtime_page_modules_contract.py`、`tests/runtime/test_asset_service.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts`、`apps/desktop/tests/runtime-stores-m09-m15.spec.ts`、`apps/desktop/tests/asset-library.spec.ts` |
| 当前 | `GET` | `/api/assets/{asset_id}` | `api/routes/assets.py:get_asset` | `fetchAsset(id)` | Runtime client、后续资产检查器编辑能力 | `tests/contracts/test_runtime_page_modules_contract.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts` |
| 当前 | `PATCH` | `/api/assets/{asset_id}` | `api/routes/assets.py:update_asset` | `updateAsset(id, input)` | Runtime client、后续资产检查器编辑能力 | `tests/contracts/test_runtime_page_modules_contract.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts` |
| 当前 | `DELETE` | `/api/assets/{asset_id}` | `api/routes/assets.py:delete_asset` | `deleteAsset(id)` | `asset-library` store | `tests/contracts/test_runtime_page_modules_contract.py`、`tests/runtime/test_asset_service.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts`、`apps/desktop/tests/runtime-stores-m09-m15.spec.ts` |
| 当前 | `GET` | `/api/assets/{asset_id}/references` | `api/routes/assets.py:list_asset_references` | `fetchAssetReferences(id)` | 资产检查器、删除确认 | `tests/contracts/test_runtime_page_modules_contract.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts` |
| 当前 | `POST` | `/api/assets/{asset_id}/references` | `api/routes/assets.py:add_asset_reference` | 暂无公开页面调用 | 后端测试/其他模块注册引用 | `tests/contracts/test_runtime_page_modules_contract.py` |
| 当前 | `DELETE` | `/api/assets/references/{ref_id}` | `api/routes/assets.py:delete_asset_reference` | 暂无公开页面调用 | 后端测试/后续引用管理 | `tests/contracts/test_runtime_page_modules_contract.py` |
| 当前 | `GET` | `/api/assets/references/{ref_id}` | `api/routes/assets.py:get_reference` | 暂无公开页面调用 | 后端测试/后续引用管理 | `tests/contracts/test_runtime_page_modules_contract.py` |

### 7.3 `POST /api/assets/import`

当前已实现接口。

请求：

```json
{
  "filePath": "D:/tkops/assets/clip.mp4",
  "type": "video",
  "source": "local",
  "projectId": "project-1",
  "tags": "[\"开场\", \"产品镜头\"]"
}
```

成功响应：

```json
{
  "ok": true,
  "data": {
    "id": "asset-1",
    "name": "clip.mp4",
    "type": "video",
    "source": "local",
    "filePath": "D:/tkops/assets/clip.mp4",
    "fileSizeBytes": 123456,
    "durationMs": null,
    "thumbnailPath": null,
    "tags": "[\"开场\", \"产品镜头\"]",
    "projectId": "project-1",
    "metadataJson": null,
    "createdAt": "2026-04-16T10:00:00",
    "updatedAt": "2026-04-16T10:00:00"
  }
}
```

失败响应：

```json
{
  "ok": false,
  "error": "文件不存在，请确认本地路径后重试"
}
```

约束：

- 必须检查真实本地文件是否存在。
- 必须记录真实文件大小。
- 不生成假缩略图。
- 不生成假 AI 标签。
- 不伪造媒体时长。
- 普通导入注册不进入 TaskBus；后续资产分析才进入 TaskBus。
- 页面点击导入时不得无响应，不得使用 `alert`/`prompt` 或手动路径输入作为核心流程；必须调用桌面文件选择器，支持一次多选并逐个注册真实路径。
- 资产预览不使用假缩略图：视频、图片、可嵌入文档优先通过 `@tauri-apps/api/core` 的 `convertFileSrc(filePath)` 渲染真实本地文件；有 `thumbnailPath` 时优先渲染真实缩略图路径。该能力依赖 Tauri `assetProtocol.enable = true`，并且 `scope` 至少覆盖用户常用素材目录。
- `.txt`、`.md`、`.json`、`.csv`、`.srt` 等文本类文档不得直接交给 iframe 猜测编码；前端必须读取 `convertFileSrc(filePath)` 返回的内容，并按 UTF-8 文本预览渲染。PDF 保持 iframe 嵌入预览。

### 7.4 删除与引用影响范围

删除前端流程：

1. 用户在资产检查器触发删除。
2. store 调用 `fetchAssetReferences(assetId)`。
3. 如果引用列表非空，页面展示引用影响范围并禁用直接删除。
4. 如果引用列表为空，store 调用 `deleteAsset(assetId)`。
5. 删除成功后刷新资产列表并清空检查器。

后端要求：

- `DELETE /api/assets/{asset_id}` 必须在服务层检查引用关系。
- 存在引用时返回统一错误信封，中文错误说明引用影响。
- 删除成功返回 `{ "deleted": true }`。

### 7.5 旧版本地库兼容

历史本地库可能已经存在旧版 `assets` 表，字段为 `kind`、`file_name` 等旧命名，缺少当前 `AssetDto` 依赖的 `name`、`type`、`duration_ms`、`thumbnail_path`、`tags`、`updated_at` 等列。Runtime 初始化必须在 `initialize_domain_schema(engine)` 中执行兼容修复：

- 只补齐当前模型查询必需的缺失列。
- `file_name` 回填到 `name`，`kind` 回填到 `type`。
- `updated_at` 为空时回填为 `created_at`。
- 如旧列 `kind`、`file_name`、`mime_type` 带有非空约束并会阻断新 ORM 插入，允许原地重建 `assets` 表；重建必须保留旧数据和旧列值，不清空用户本地资产。
- 兼容修复必须由 `tests/runtime/test_asset_schema_migration.py` 覆盖。

### 7.6 TaskBus WebSocket 依赖

前端任务总线连接 `ws://127.0.0.1:8000/api/ws`。Runtime 运行环境必须安装 `websockets` 或 `wsproto` 之一；当前项目依赖固定为 `websockets>=14.0,<16.0`。如果缺少该依赖，Uvicorn 会记录 `No supported WebSocket library detected`，升级请求会退化成普通 `GET /api/ws` 并持续返回 404。

## 8. M16 AI 与系统设置 ✅ 已交付

> 2026-04-16 新增：AI 与系统设置模块当前后端接口已经形成两个边界：系统配置总线 `/api/settings/*` 与 AI 能力配置 `/api/settings/ai-capabilities/*`。前端页面必须通过 `runtime-client.ts` 和 Pinia store 消费这些接口，不得在页面内直接 fetch。Provider API Key 只允许写入 SecretStore，接口只返回脱敏状态，不返回明文密钥。产品目标是支持多 Provider 与多模型选择；当前 Runtime 已输出多 Provider 注册表，并支持按模型发起真实连通性测试。

### 8.1 数据对象

`RuntimeHealthSnapshot`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `service` | `string` | Runtime 服务状态，当前在线时为 `online` |
| `version` | `string` | Runtime 版本 |
| `now` | `string` | Runtime 当前 UTC ISO 时间 |
| `mode` | `string` | 当前运行模式 |

`AppSettings`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `revision` | `number` | 配置修订号，由后端递增 |
| `runtime.mode` | `string` | Runtime 运行模式 |
| `runtime.workspaceRoot` | `string` | 本地工作区根目录 |
| `paths.cacheDir` | `string` | 缓存目录 |
| `paths.exportDir` | `string` | 导出目录 |
| `paths.logDir` | `string` | 日志目录 |
| `logging.level` | `string` | 日志级别，如 `DEBUG`、`INFO`、`WARNING`、`ERROR` |
| `ai.provider` | `string` | 默认 AI Provider |
| `ai.model` | `string` | 默认模型 |
| `ai.voice` | `string` | 默认音色 |
| `ai.subtitleMode` | `string` | 默认字幕策略 |

`RuntimeDiagnostics`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `databasePath` | `string` | 本地 SQLite 数据库路径 |
| `logDir` | `string` | 日志目录 |
| `revision` | `number` | 当前配置修订号 |
| `mode` | `string` | 当前运行模式 |
| `healthStatus` | `string` | 当前诊断状态，在线时为 `online` |

`AICapabilityConfig`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `capabilityId` | `string` | 能力 ID，见下方固定枚举 |
| `enabled` | `boolean` | 能力是否启用 |
| `provider` | `string` | 能力绑定的 Provider |
| `model` | `string` | 能力绑定的模型 |
| `agentRole` | `string` | 能力角色说明 |
| `systemPrompt` | `string` | 系统提示词 |
| `userPromptTemplate` | `string` | 用户提示词模板 |

固定能力 ID：

- `script_generation`
- `script_rewrite`
- `storyboard_generation`
- `tts_generation`
- `subtitle_alignment`
- `video_generation`
- `asset_analysis`

`AIProviderSecretStatus`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `provider` | `string` | Provider ID |
| `label` | `string` | 展示名称 |
| `configured` | `boolean` | 是否已有可用密钥 |
| `maskedSecret` | `string` | 脱敏密钥，未配置时为空字符串 |
| `baseUrl` | `string` | Provider Base URL |
| `secretSource` | `string` | `secure_store`、`env` 或 `none` |
| `supportsTextGeneration` | `boolean` | 当前阶段是否已接入文本生成 |

当前密钥写入与同步健康检查已支持 Provider ID：

- `openai`
- `openai_compatible`
- `anthropic`
- `gemini`

当前 Provider 注册表已暴露的 Provider 类型：

- 商业文本与多模态 Provider：OpenAI、Anthropic、Google Gemini、DeepSeek、通义千问/Qwen、月之暗面/Kimi、智谱 GLM、MiniMax、火山/豆包、百度千帆/ERNIE、腾讯混元、xAI、Mistral、Cohere。
- 聚合与兼容 Provider：OpenRouter、OpenAI-compatible、自建兼容网关。
- 本地模型 Provider：Ollama、LM Studio、vLLM、LocalAI。
- 专用媒体 Provider：TTS、字幕对齐、视频生成、资产分析等能力 Provider。

新增 Provider 必须通过 Runtime Provider 注册表和模型目录暴露给前端，不得由页面硬编码。

`AIProviderHealth`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `provider` | `string` | Provider ID |
| `status` | `string` | `ready`、`missing_secret`、`misconfigured` 或 `unsupported` |
| `message` | `string` | 中文可见状态说明 |

`AIProviderSecretInput`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `apiKey` | `string` | 是 | Provider API Key，只写入 SecretStore，不在响应中返回 |
| `baseUrl` | `string | null` | 否 | OpenAI-compatible 等 Provider 的 Base URL |

### 8.2 后端接口与前端调用

| 状态 | 方法 | 路径 | 后端入口 | 前端调用 | 消费方 | 测试 |
| --- | --- | --- | --- | --- | --- | --- |
| 当前 | `GET` | `/api/settings/health` | `api/routes/settings.py:get_runtime_health` | `fetchRuntimeHealth()` | `config-bus` store、Shell 状态、AI 与系统设置页 | `tests/contracts/test_runtime_health_contract.py`、`tests/runtime/test_settings_health.py`、`apps/desktop/tests/ai-system-settings.spec.ts` |
| 当前 | `GET` | `/api/settings/config` | `api/routes/settings.py:get_runtime_config` | `fetchRuntimeConfig()` | `config-bus` store、AI 与系统设置页 | `tests/contracts/test_settings_config_contract.py`、`tests/runtime/test_settings_config.py`、`apps/desktop/tests/ai-system-settings.spec.ts` |
| 当前 | `PUT` | `/api/settings/config` | `api/routes/settings.py:update_runtime_config` | `updateRuntimeConfig(input)` | `config-bus` store、AI 与系统设置页 | `tests/contracts/test_settings_config_contract.py`、`tests/runtime/test_settings_config.py`、`apps/desktop/tests/ai-system-settings.spec.ts` |
| 当前 | `GET` | `/api/settings/diagnostics` | `api/routes/settings.py:get_runtime_diagnostics` | `fetchRuntimeDiagnostics()` | `config-bus` store、Detail Panel、AI 与系统设置页 | `tests/contracts/test_settings_config_contract.py`、`tests/runtime/test_settings_config.py`、`apps/desktop/tests/ai-system-settings.spec.ts` |
| 当前 | `GET` | `/api/settings/ai-capabilities` | `api/routes/ai_capabilities.py:get_ai_capability_settings` | `fetchAICapabilitySettings()` | `ai-capability` store、AI 与系统设置页 | `tests/contracts/test_ai_capabilities_contract.py`、`tests/runtime/test_ai_capabilities.py`、`apps/desktop/tests/ai-system-settings.spec.ts` |
| 当前 | `PUT` | `/api/settings/ai-capabilities` | `api/routes/ai_capabilities.py:update_ai_capability_settings` | `updateAICapabilitySettings(capabilities)` | `ai-capability` store、AI 与系统设置页 | `tests/contracts/test_ai_capabilities_contract.py`、`tests/runtime/test_ai_capabilities.py`、`apps/desktop/tests/ai-system-settings.spec.ts` |
| 当前 | `PUT` | `/api/settings/ai-capabilities/providers/{provider_id}/secret` | `api/routes/ai_capabilities.py:set_provider_secret` | `updateAIProviderSecret(providerId, input)` | Runtime client 已提供；页面 Provider Secret UI 待接入 | `tests/contracts/test_ai_capabilities_contract.py`、`tests/runtime/test_ai_capabilities.py` |
| 当前 | `POST` | `/api/settings/ai-capabilities/providers/{provider_id}/health-check` | `api/routes/ai_capabilities.py:check_provider_health` | `checkAIProviderHealth(providerId, input)` | `ai-capability` store、AI 与系统设置页、右侧诊断抽屉 | `tests/contracts/test_ai_capabilities_contract.py`、`tests/runtime/test_ai_capabilities.py`、`apps/desktop/tests/ai-system-settings.spec.ts` |

### 8.3 `GET /api/settings/config`

成功响应：

```json
{
  "ok": true,
  "data": {
    "revision": 1,
    "runtime": {
      "mode": "test",
      "workspaceRoot": "D:/TK-OPS/workspace"
    },
    "paths": {
      "cacheDir": "D:/TK-OPS/cache",
      "exportDir": "D:/TK-OPS/exports",
      "logDir": "D:/TK-OPS/logs"
    },
    "logging": {
      "level": "INFO"
    },
    "ai": {
      "provider": "openai",
      "model": "gpt-5.4",
      "voice": "alloy",
      "subtitleMode": "balanced"
    }
  }
}
```

### 8.4 `PUT /api/settings/config`

请求：

```json
{
  "runtime": {
    "mode": "production",
    "workspaceRoot": "D:/TK-OPS/workspace"
  },
  "paths": {
    "cacheDir": "D:/TK-OPS/cache",
    "exportDir": "D:/TK-OPS/exports",
    "logDir": "D:/TK-OPS/logs"
  },
  "logging": {
    "level": "DEBUG"
  },
  "ai": {
    "provider": "openai",
    "model": "gpt-5.4-mini",
    "voice": "nova",
    "subtitleMode": "precise"
  }
}
```

成功响应：

```json
{
  "ok": true,
  "data": {
    "revision": 2,
    "runtime": {
      "mode": "production",
      "workspaceRoot": "D:/TK-OPS/workspace"
    },
    "paths": {
      "cacheDir": "D:/TK-OPS/cache",
      "exportDir": "D:/TK-OPS/exports",
      "logDir": "D:/TK-OPS/logs"
    },
    "logging": {
      "level": "DEBUG"
    },
    "ai": {
      "provider": "openai",
      "model": "gpt-5.4-mini",
      "voice": "nova",
      "subtitleMode": "precise"
    }
  }
}
```

约束：

- 后端会确保 `workspaceRoot`、`cacheDir`、`exportDir`、`logDir` 对应目录存在。
- 成功更新会写入 `settings.updated` audit log。
- 页面保存失败时必须保留用户草稿并提供重试。

### 8.5 `GET /api/settings/diagnostics`

成功响应：

```json
{
  "ok": true,
  "data": {
    "databasePath": "D:/TK-OPS/runtime.db",
    "logDir": "D:/TK-OPS/logs",
    "revision": 2,
    "mode": "production",
    "healthStatus": "online"
  }
}
```

约束：

- 诊断接口只返回非敏感字段。
- 不返回 API Key、环境变量明文或 traceback。

### 8.6 `GET /api/settings/ai-capabilities`

成功响应：

```json
{
  "ok": true,
  "data": {
    "capabilities": [
      {
        "capabilityId": "script_generation",
        "enabled": true,
        "provider": "openai",
        "model": "gpt-5",
        "agentRole": "资深短视频脚本策划",
        "systemPrompt": "围绕用户主题生成高留存、可拍摄的短视频脚本。",
        "userPromptTemplate": "主题：{{topic}}"
      }
    ],
    "providers": [
      {
        "provider": "openai",
        "label": "OpenAI",
        "configured": false,
        "maskedSecret": "",
        "baseUrl": "https://api.openai.com/v1/responses",
        "secretSource": "none",
        "supportsTextGeneration": true
      }
    ]
  }
}
```

约束：

- 首次读取时后端会创建 7 个默认能力配置。
- Provider 列表来自 Runtime 注册表，当前已覆盖商业、聚合、本地和媒体预留 Provider。
- 响应不得包含 `apiKey` 明文字段。

### 8.7 `PUT /api/settings/ai-capabilities`

请求：

```json
{
  "capabilities": [
    {
      "capabilityId": "script_generation",
      "enabled": true,
      "provider": "openai",
      "model": "gpt-5.4",
      "agentRole": "资深短视频脚本策划",
      "systemPrompt": "围绕用户主题生成高留存、可拍摄的短视频脚本。",
      "userPromptTemplate": "主题：{{topic}}"
    },
    {
      "capabilityId": "script_rewrite",
      "enabled": true,
      "provider": "openai",
      "model": "gpt-5-mini",
      "agentRole": "短视频脚本改写编辑",
      "systemPrompt": "在保持原意的前提下提升脚本节奏、开场和转化效率。",
      "userPromptTemplate": "原脚本：\n{{script}}\n\n改写要求：{{instructions}}"
    },
    {
      "capabilityId": "storyboard_generation",
      "enabled": true,
      "provider": "openai",
      "model": "gpt-5-mini",
      "agentRole": "分镜规划导演",
      "systemPrompt": "把脚本文本拆解为清晰的镜头与视觉提示。",
      "userPromptTemplate": "脚本内容：\n{{script}}"
    },
    {
      "capabilityId": "tts_generation",
      "enabled": false,
      "provider": "openai",
      "model": "gpt-5-mini",
      "agentRole": "配音导演",
      "systemPrompt": "为脚本生成适合配音的语气和节奏说明。",
      "userPromptTemplate": "脚本内容：\n{{script}}"
    },
    {
      "capabilityId": "subtitle_alignment",
      "enabled": false,
      "provider": "openai",
      "model": "gpt-5-mini",
      "agentRole": "字幕对齐编辑",
      "systemPrompt": "让字幕语言和节奏更适合短视频表达。",
      "userPromptTemplate": "脚本内容：\n{{script}}"
    },
    {
      "capabilityId": "video_generation",
      "enabled": false,
      "provider": "openai_compatible",
      "model": "custom-video",
      "agentRole": "视频生成导演",
      "systemPrompt": "把分镜转成可执行的视频生成提示。",
      "userPromptTemplate": "分镜内容：\n{{storyboard}}"
    },
    {
      "capabilityId": "asset_analysis",
      "enabled": false,
      "provider": "gemini",
      "model": "gemini-2.5-pro",
      "agentRole": "素材分析师",
      "systemPrompt": "总结素材内容、价值点和可复用结构。",
      "userPromptTemplate": "素材内容：\n{{assets}}"
    }
  ]
}
```

成功响应：

```json
{
  "ok": true,
  "data": {
    "capabilities": [
      {
        "capabilityId": "script_generation",
        "enabled": true,
        "provider": "openai",
        "model": "gpt-5.4",
        "agentRole": "资深短视频脚本策划",
        "systemPrompt": "围绕用户主题生成高留存、可拍摄的短视频脚本。",
        "userPromptTemplate": "主题：{{topic}}"
      }
    ],
    "providers": [
      {
        "provider": "openai",
        "label": "OpenAI",
        "configured": false,
        "maskedSecret": "",
        "baseUrl": "https://api.openai.com/v1/responses",
        "secretSource": "none",
        "supportsTextGeneration": true
      }
    ]
  }
}
```

约束：

- 当前后端要求提交完整 7 项能力配置；缺任一能力会返回 400。
- 页面保存时不能只提交被编辑的一行。
- `capabilityId` 不允许脱离固定能力集合。

能力配置不完整失败响应：

```json
{
  "ok": false,
  "error": "AI 能力配置不完整。"
}
```

### 8.8 `PUT /api/settings/ai-capabilities/providers/{provider_id}/secret`

请求：

```json
{
  "apiKey": "sk-live-example",
  "baseUrl": "https://api.openai.com/v1/responses"
}
```

成功响应：

```json
{
  "ok": true,
  "data": {
    "provider": "openai",
    "label": "OpenAI",
    "configured": true,
    "maskedSecret": "sk-l****mple",
    "baseUrl": "https://api.openai.com/v1/responses",
    "secretSource": "secure_store",
    "supportsTextGeneration": true
  }
}
```

约束：

- `apiKey` 必须写入 SecretStore。
- 响应只返回 `maskedSecret`，不得返回明文。
- `openai_compatible` 必须有可用 Base URL，否则 health-check 会返回 `misconfigured`。

### 8.9 `POST /api/settings/ai-capabilities/providers/{provider_id}/health-check`

请求：

```json
{
  "model": "gpt-5.4"
}
```

成功响应：

```json
{
  "ok": true,
  "data": {
    "provider": "openai",
    "status": "ready",
    "message": "OpenAI / gpt-5.4 真实连通性测试通过。",
    "model": "gpt-5.4",
    "checkedAt": "2026-04-17T01:20:00Z",
    "latencyMs": 420
  }
}
```

其他状态：

| `status` | 说明 |
| --- | --- |
| `ready` | Provider 已配置，且当前阶段支持文本生成 |
| `missing_secret` | 未配置 API Key |
| `misconfigured` | 配置不完整，如 OpenAI-compatible 缺少 Base URL |
| `offline` | 远端不可达、本地服务未启动或网络异常 |
| `unsupported` | Provider 已注册，但当前阶段尚未接入文本生成 |

约束：

- 请求中的 `model` 可选；未传时 Runtime 自动回退到该 Provider 的默认可测模型。
- 健康检查会发起真实 HTTP 探测，不再只做本地配置判断。
- 返回 `checkedAt`、`latencyMs` 供右侧诊断抽屉和状态提示消费。
- 错误信息必须保持中文可见，可直接映射到 UI 提示。

### 8.10 当前已知差距

- AI 与系统设置页面已接入 Provider 注册表、模型目录、能力支持矩阵、密钥写入和同步健康检查入口；后续仍需把能力级默认模型保存逻辑接入配置总线。
- 当前文本模型 Provider 已支持真实连通性探测；媒体 Provider 的专用探测策略仍需按 `tts`、`video_generation`、`asset_analysis` 能力继续扩展。
- 模型目录当前来自 Runtime 内置注册表，不执行真实远端模型发现；远端刷新接入后必须记录来源、耗时、失败原因和缓存时间。
- `PUT /api/settings/config` 的 422 validation failure 当前由全局处理返回 `Request validation failed`；最终用户可见文案应在后续实现中收口为中文提示。
- 本模块当前没有 TaskBus 长任务和 WebSocket 事件。

### 8.11 Provider 注册表与模型目录

本节为当前已实现的同步契约。模型目录为 Runtime 内置初始目录，远端模型发现尚未接入；如果后续刷新访问远端且耗时较长，应升级为 TaskBus 长任务。

接口：

| 状态 | 方法 | 路径 | 用途 |
| --- | --- | --- | --- |
| 当前 | `GET` | `/api/settings/ai-providers/catalog` | 返回 Runtime 支持的 Provider 注册表 |
| 当前 | `GET` | `/api/settings/ai-providers/{provider_id}/models` | 返回指定 Provider 的模型目录 |
| 当前 | `GET` | `/api/settings/ai-capabilities/support-matrix` | 返回每个 AI 能力可选 Provider 与模型范围 |
| 当前 | `POST` | `/api/settings/ai-providers/{provider_id}/models/refresh` | 返回内置目录刷新结果；真实远端刷新后应升级为 TaskBus |

`AIProviderCatalogItem`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `provider` | `string` | Provider ID |
| `label` | `string` | 中文或官方展示名 |
| `kind` | `string` | `commercial`、`openai_compatible`、`aggregator`、`local`、`media` |
| `configured` | `boolean` | 是否已配置凭据或本地连接 |
| `baseUrl` | `string` | 当前 Base URL |
| `secretSource` | `string` | `secure_store`、`env` 或 `none` |
| `capabilities` | `string[]` | 支持的能力类型，如 `text_generation`、`vision`、`tts`、`video_generation`、`asset_analysis` |
| `requiresBaseUrl` | `boolean` | 是否必须配置 Base URL |
| `supportsModelDiscovery` | `boolean` | 是否支持拉取模型目录 |
| `status` | `string` | `ready`、`missing_secret`、`misconfigured`、`unsupported`、`offline` |

`AIModelCatalogItem`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `modelId` | `string` | Provider 侧模型 ID |
| `displayName` | `string` | UI 展示名称 |
| `provider` | `string` | 所属 Provider |
| `capabilityTypes` | `string[]` | 支持的能力类型 |
| `inputModalities` | `string[]` | `text`、`image`、`audio`、`video` |
| `outputModalities` | `string[]` | `text`、`image`、`audio`、`video` |
| `contextWindow` | `number | null` | 上下文长度，未知时为 `null` |
| `defaultFor` | `string[]` | 推荐默认使用的 TK-OPS 能力 |
| `enabled` | `boolean` | 当前是否允许被能力配置选择 |

约束：

- 前端模型选择器必须消费 Runtime 模型目录，不得在页面写死模型列表。
- Runtime 可以内置首批 Provider 元数据，但必须通过注册表服务暴露，并允许后续扩展。
- 未知 Provider、不可用 Base URL、缺少密钥、远端目录刷新失败都必须返回中文错误信封，不能 500。
- OpenAI-compatible、OpenRouter、本地模型服务必须允许用户配置 Base URL。
- 视频生成、TTS、字幕对齐和资产分析 Provider 不能混同为普通文本 Provider，必须按能力类型过滤。
- 刷新远端模型目录如果超过同步请求可接受时间，应进入 TaskBus，并支持状态查询、失败原因和重试。

## 9. 前端调用登记表

| 函数 | 文件 | Runtime 路径 | 返回类型 | 主要消费方 | 更新要求 |
| --- | --- | --- | --- | --- | --- |
| `fetchRuntimeHealth()` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/settings/health` | `RuntimeHealthSnapshot` | `config-bus` store、Shell 状态、AI 与系统设置页 | Runtime 健康字段变化时必须同步类型、store、状态栏和测试 |
| `fetchRuntimeConfig()` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/settings/config` | `AppSettings` | `config-bus` store、AI 与系统设置页 | 配置字段变化必须同步 `AppSettings`、设置页表单和 contract tests |
| `updateRuntimeConfig(input)` | `apps/desktop/src/app/runtime-client.ts` | `PUT /api/settings/config` | `AppSettings` | `config-bus` store、AI 与系统设置页 | 保存失败必须保留草稿并展示中文错误 |
| `fetchRuntimeDiagnostics()` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/settings/diagnostics` | `RuntimeDiagnostics` | `config-bus` store、Detail Panel、AI 与系统设置页 | 不得向前端暴露敏感字段 |
| `fetchAICapabilitySettings()` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/settings/ai-capabilities` | `AICapabilitySettings` | `ai-capability` store、AI 与系统设置页 | 能力集合、Provider 状态字段变化必须同步类型、store 和测试 |
| `updateAICapabilitySettings(capabilities)` | `apps/desktop/src/app/runtime-client.ts` | `PUT /api/settings/ai-capabilities` | `AICapabilitySettings` | `ai-capability` store、AI 与系统设置页 | 当前必须提交完整 7 项能力配置，不允许只提交单行 |
| `updateAIProviderSecret(providerId, input)` | `apps/desktop/src/app/runtime-client.ts` | `PUT /api/settings/ai-capabilities/providers/{provider_id}/secret` | `AIProviderSecretStatus` | Runtime client 已提供；Provider Secret UI 待接入 | 不得展示 API Key 明文，成功后只展示 maskedSecret |
| `checkAIProviderHealth(providerId, input)` | `apps/desktop/src/app/runtime-client.ts` | `POST /api/settings/ai-capabilities/providers/{provider_id}/health-check` | `AIProviderHealth` | `ai-capability` store、AI 与系统设置页、右侧诊断抽屉 | 必须支持可选 `model` 请求体，并把 `checkedAt`、`latencyMs`、状态映射为中文反馈 |
| `fetchAIProviderCatalog()` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/settings/ai-providers/catalog` | `AIProviderCatalogItem[]` | `ai-capability` store、Provider 管理 UI | 用于支持主流 Provider 注册表，页面不得硬编码 Provider 列表 |
| `fetchAIProviderModels(providerId)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/settings/ai-providers/{provider_id}/models` | `AIModelCatalogItem[]` | `ai-capability` store、模型目录面板 | 页面不得硬编码模型列表；未知 Provider 必须显示中文错误 |
| `fetchAICapabilitySupportMatrix()` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/settings/ai-capabilities/support-matrix` | `AICapabilitySupportMatrix` | `ai-capability` store、能力级模型选择 | 用于限制每个能力可选模型 |
| `refreshAIProviderModels(providerId)` | `apps/desktop/src/app/runtime-client.ts` | `POST /api/settings/ai-providers/{provider_id}/models/refresh` | `AIModelCatalogRefreshResult` | `ai-capability` store、模型目录面板 | 当前返回内置目录刷新结果；接入真实远端刷新后必须同步 TaskBus 文档 |
| `fetchAssets(type?, q?)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/assets` | `AssetDto[]` | `asset-library` store | 如新增筛选参数，必须同步本文件、类型和测试 |
| `fetchAssetReferences(id)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/assets/{id}/references` | `AssetReferenceDto[]` | `asset-library` store | 删除确认依赖该调用 |
| `deleteAsset(id)` | `apps/desktop/src/app/runtime-client.ts` | `DELETE /api/assets/{id}` | `AssetDeleteResult` | `asset-library` store | 删除前必须先检查引用；后端仍会阻断有引用资产 |
| `importAsset(input)` | `apps/desktop/src/app/runtime-client.ts` | `POST /api/assets/import` | `AssetDto` | `asset-library` store、资产中心页面 | 点击导入必须使用桌面文件选择器多选；只能注册真实本地文件路径，不生成假资产数据 |
| `fetchAsset(id)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/assets/{id}` | `AssetDto` | Runtime client、后续资产检查器编辑能力 | 如页面直接消费，必须补页面状态测试 |
| `updateAsset(id, input)` | `apps/desktop/src/app/runtime-client.ts` | `PATCH /api/assets/{id}` | `AssetDto` | Runtime client、后续资产检查器编辑能力 | 编辑能力开放时必须补 store/page 测试 |
| `fetchWorkspaceTimeline(projectId)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/workspace/projects/{project_id}/timeline` | `WorkspaceTimelineResultDto` | `editing-workspace` store、AI 剪辑工作台页面 | 空态不得生成假轨道；必须显示创建草稿入口 |
| `createWorkspaceTimeline(projectId, input)` | `apps/desktop/src/app/runtime-client.ts` | `POST /api/workspace/projects/{project_id}/timeline` | `WorkspaceTimelineResultDto` | `editing-workspace` store、空态创建入口 | 创建真实空草稿，不自动填充示例轨道 |
| `updateWorkspaceTimeline(timelineId, input)` | `apps/desktop/src/app/runtime-client.ts` | `PATCH /api/workspace/timelines/{timeline_id}` | `WorkspaceTimelineResultDto` | `editing-workspace` store、保存时间线动作 | 保存失败必须保留前端草稿并显示中文错误 |
| `runWorkspaceAICommand(projectId, input)` | `apps/desktop/src/app/runtime-client.ts` | `POST /api/workspace/projects/{project_id}/ai-commands` | `WorkspaceAICommandResultDto` | `editing-workspace` store、AI 魔法剪入口 | 本批返回 `blocked`，不得显示假任务进度 |
| `fetchVoiceProfiles()` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/voice/profiles` | `VoiceProfileDto[]` | `voice-studio` store、音色选择组件 | 不得在页面内写死 Provider 音色 |
| `fetchVoiceTracks(projectId)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/voice/projects/{project_id}/tracks` | `VoiceTrackDto[]` | `voice-studio` store、配音版本列表 | 列表必须来自真实 Runtime 记录 |
| `generateVoiceTrack(projectId, input)` | `apps/desktop/src/app/runtime-client.ts` | `POST /api/voice/projects/{project_id}/tracks/generate` | `VoiceTrackGenerateResultDto` | `voice-studio` store、配音中心页面 | 无 TTS Provider 时必须展示 `blocked`，不得假成功 |
| `fetchVoiceTrack(trackId)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/voice/tracks/{track_id}` | `VoiceTrackDto` | `voice-studio` store、版本详情 | 返回段落映射，后续字幕/时间线消费依赖该结构 |
| `deleteVoiceTrack(trackId)` | `apps/desktop/src/app/runtime-client.ts` | `DELETE /api/voice/tracks/{track_id}` | `void` | `voice-studio` store、配音版本列表 | 删除失败必须展示中文错误 |

前端本地预览调用登记：

| 调用 | 文件 | 用途 | 更新要求 |
| --- | --- | --- | --- |
| `convertFileSrc(filePath)` | `apps/desktop/src/components/assets/AssetPreview.vue` | 将真实本地视频、图片、文档路径转换为 WebView 可渲染地址；文本类文档读取后按 UTF-8 渲染 | 依赖 Tauri 桌面环境和 `app.security.assetProtocol`；不得用假缩略图替代真实文件预览 |

## 10. 待补文档接口清单(🚧 已实现未文档化)

> 以下 11 个模块的 Runtime 路由已落地，但本文件尚未补齐契约描述。每个模块需要补齐的最小骨架:数据对象 → 接口定义 → 错误码 → 前端调用登记 → schema_version。文档化优先级以 `BACKEND-REQUIREMENTS-2026-04-17.md` §0.1.2 为准。

| 模块 | 路由文件 | 实现接口数 | 文档化优先级 | 主要依赖 |
| --- | --- | --- | --- | --- |
| M01 仪表盘 | `apps/py-runtime/src/api/routes/dashboard.py` | 4 | P1 | 项目、任务、AI 用量聚合 |
| M02 项目空间 | `apps/py-runtime/src/api/routes/projects.py` | 8 | P1 | 项目主模型、最近编辑 |
| M03 脚本中心 | `apps/py-runtime/src/api/routes/scripts.py` | 9 | P1 | Script 实体、AI 文本流 |
| M04 分镜中心 | `apps/py-runtime/src/api/routes/storyboards.py` | 7 | P1 | Storyboard 实体、镜头排程 |
| M06 视频拆解中心 | `apps/py-runtime/src/api/routes/decomposition.py` | 6 | P2 | 媒体抽帧、AI 解析 |
| M10 任务队列 | `apps/py-runtime/src/api/routes/tasks.py` | 7 | P1 | TaskBus、WebSocket |
| M11 渲染管线 | `apps/py-runtime/src/api/routes/render.py` | 5 | P2 | RenderTask、媒体输出 |
| M12 发布管理 | `apps/py-runtime/src/api/routes/publishing.py` | 6 | P2 | 平台账号、发布计划 |
| M13 复盘中心 | `apps/py-runtime/src/api/routes/review.py` | 5 | P3 | 数据回流、AI 摘要 |
| M14 工作区设置 | `apps/py-runtime/src/api/routes/workspace_settings.py` | 4 | P2 | 工作区目录、个人化 |
| M15 项目操作 | `apps/py-runtime/src/api/routes/project_actions.py` | 3 | P2 | 项目级动作、备份 |

补齐策略:
1. 每模块独占一节(`## 11. M01 仪表盘`、`## 12. M02 项目空间` …),沿用 §4-8 的章节结构。
2. 与 `BACKEND-REQUIREMENTS-2026-04-17.md` §2.x 表格里的 ✅/🚧/📋 状态保持一致;若文档化与实现存在 gap,优先标注 🚧 而非 ✅。
3. 文档化每完成一节,更新 §0.2 模块覆盖度总览的"文档化"列与百分比。

## 11. 验证命令

接口或调用文档变化后，至少运行：

```powershell
npm --prefix apps/desktop run test
venv\Scripts\python.exe -m pytest tests\contracts -q
```

如涉及页面、样式或 Runtime 服务层，还必须运行：

```powershell
npm --prefix apps/desktop run build
venv\Scripts\python.exe -m pytest tests\runtime -q
```

提交前检查：

```powershell
git diff --check --cached
```
