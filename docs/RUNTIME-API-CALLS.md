# Runtime API 与前端调用唯一文档

> 本文件是 TK-OPS 前后端 Runtime 接口与前端调用关系的唯一真源。
> 任何新增、删除、重命名、字段调整、状态语义调整或调用入口调整，都必须在同一次变更中更新本文件。
> 编码约定：本文档和相关中文产品文档统一使用 UTF-8 无 BOM 保存；读取、生成、校验脚本必须显式按 UTF-8 处理，避免中文文案在 PowerShell、测试输出或 IDE 中出现乱码。

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

## 4. M07 配音中心

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

### 6.2 后端接口与前端调用

| 状态 | 方法 | 路径 | 后端入口 | 前端调用 | 消费方 | 测试 |
| --- | --- | --- | --- | --- | --- | --- |
| 当前 | `GET` | `/api/voice/profiles` | `api/routes/voice.py:list_profiles` | `fetchVoiceProfiles()` | `voice-studio` store、`VoiceProfileRail.vue` | `tests/contracts/test_voice_runtime_contract.py`、`apps/desktop/tests/runtime-client-voice.spec.ts` |
| 当前 | `GET` | `/api/voice/projects/{project_id}/tracks` | `api/routes/voice.py:list_project_tracks` | `fetchVoiceTracks(projectId)` | `voice-studio` store、`VoiceVersionPanel.vue` | `tests/contracts/test_voice_runtime_contract.py`、`apps/desktop/tests/runtime-client-voice.spec.ts` |
| 当前 | `POST` | `/api/voice/projects/{project_id}/tracks/generate` | `api/routes/voice.py:generate_track` | `generateVoiceTrack(projectId, input)` | `voice-studio` store、`VoicePreviewStage.vue` | `tests/contracts/test_voice_runtime_contract.py`、`tests/runtime/test_voice_service.py`、`apps/desktop/tests/voice-studio-store.spec.ts` |
| 当前 | `GET` | `/api/voice/tracks/{track_id}` | `api/routes/voice.py:get_track` | `fetchVoiceTrack(trackId)` | `voice-studio` store、版本详情 | `tests/contracts/test_voice_runtime_contract.py`、`apps/desktop/tests/runtime-client-voice.spec.ts` |
| 当前 | `DELETE` | `/api/voice/tracks/{track_id}` | `api/routes/voice.py:delete_track` | `deleteVoiceTrack(trackId)` | `voice-studio` store、`VoiceVersionPanel.vue` | `tests/contracts/test_voice_runtime_contract.py`、`apps/desktop/tests/voice-studio-store.spec.ts` |

### 4.3 `POST /api/voice/projects/{project_id}/tracks/generate`

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

## 5. M08 字幕对齐中心

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

### 5.2 后端接口与前端调用

| 状态 | 方法 | 路径 | 后端入口 | 前端调用 | 消费方 | 测试 |
| --- | --- | --- | --- | --- | --- | --- |
| 当前 | `GET` | `/api/subtitles/projects/{project_id}/tracks` | `api/routes/subtitles.py:list_project_tracks` | `fetchSubtitleTracks(projectId)` | `subtitle-alignment` store、`SubtitleVersionPanel.vue` | `tests/contracts/test_subtitle_runtime_contract.py`、`apps/desktop/tests/runtime-client-subtitles.spec.ts` |
| 当前 | `POST` | `/api/subtitles/projects/{project_id}/tracks/generate` | `api/routes/subtitles.py:generate_track` | `generateSubtitleTrack(projectId, input)` | `subtitle-alignment` store、字幕对齐中心页面 | `tests/contracts/test_subtitle_runtime_contract.py`、`tests/runtime/test_subtitle_service.py`、`apps/desktop/tests/subtitle-alignment-store.spec.ts` |
| 当前 | `GET` | `/api/subtitles/tracks/{track_id}` | `api/routes/subtitles.py:get_track` | `fetchSubtitleTrack(trackId)` | `subtitle-alignment` store、版本详情 | `tests/contracts/test_subtitle_runtime_contract.py`、`apps/desktop/tests/runtime-client-subtitles.spec.ts` |
| 当前 | `PATCH` | `/api/subtitles/tracks/{track_id}` | `api/routes/subtitles.py:update_track` | `updateSubtitleTrack(trackId, input)` | `subtitle-alignment` store、`SubtitleSegmentList.vue`、`SubtitleTimingPanel.vue`、`SubtitleStylePanel.vue` | `tests/contracts/test_subtitle_runtime_contract.py`、`tests/runtime/test_subtitle_service.py`、`apps/desktop/tests/subtitle-alignment-store.spec.ts` |
| 当前 | `DELETE` | `/api/subtitles/tracks/{track_id}` | `api/routes/subtitles.py:delete_track` | `deleteSubtitleTrack(trackId)` | `subtitle-alignment` store、`SubtitleVersionPanel.vue` | `tests/contracts/test_subtitle_runtime_contract.py`、`apps/desktop/tests/subtitle-alignment-store.spec.ts` |

### 5.3 `POST /api/subtitles/projects/{project_id}/tracks/generate`

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

### 5.4 前端调用登记

| 函数 | 文件 | Runtime 路径 | 返回类型 | 主要消费方 | 更新要求 |
| --- | --- | --- | --- | --- | --- |
| `fetchSubtitleTracks(projectId)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/subtitles/projects/{project_id}/tracks` | `SubtitleTrackDto[]` | `subtitle-alignment` store、`SubtitleVersionPanel.vue` | 列表必须来自真实 Runtime 记录 |
| `generateSubtitleTrack(projectId, input)` | `apps/desktop/src/app/runtime-client.ts` | `POST /api/subtitles/projects/{project_id}/tracks/generate` | `SubtitleTrackGenerateResultDto` | `subtitle-alignment` store、字幕对齐中心页面 | 无 Provider 时必须展示 `blocked`，不得假成功 |
| `fetchSubtitleTrack(trackId)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/subtitles/tracks/{track_id}` | `SubtitleTrackDto` | `subtitle-alignment` store、版本详情 | 返回段落和样式映射 |
| `updateSubtitleTrack(trackId, input)` | `apps/desktop/src/app/runtime-client.ts` | `PATCH /api/subtitles/tracks/{track_id}` | `SubtitleTrackDto` | `subtitle-alignment` store、字幕段落、时间码、样式面板 | 保存失败必须显示中文错误 |
| `deleteSubtitleTrack(trackId)` | `apps/desktop/src/app/runtime-client.ts` | `DELETE /api/subtitles/tracks/{track_id}` | `void` | `subtitle-alignment` store、版本面板 | 删除后必须刷新列表并清空失效选中态 |

## 6. M09 资产中心

> 2026-04-16 修订：Runtime 启动时会兼容修复旧版 `assets` 表，避免旧本地库缺少 `name`、`type`、`updated_at` 等列导致 `GET /api/assets` 直接 500，也避免旧版 `kind` / `file_name` 非空约束阻断新图片导入。点击“导入资产”必须弹出桌面文件选择器并支持多选；每个被选中的真实本地路径逐个通过 `importAsset(input)` 进入 Runtime。Tauri 主窗口 capability 必须包含 `dialog:allow-open`，否则文件选择器会被运行时权限拒绝；`tauri.conf.json` 必须启用 `app.security.assetProtocol` 并允许用户素材目录，否则 `convertFileSrc(filePath)` 生成的真实预览地址无法在 WebView 中读取。资产中心前端已采用素材墙、批量导入状态、真实本地预览、UTF-8 文档预览和全局右侧抽屉联动；页面不得回退到手动路径输入或图标占位预览。

### 6.1 数据对象

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

### 6.2 后端接口与前端调用

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

### 6.3 `POST /api/assets/import`

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

### 6.4 删除与引用影响范围

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

### 6.5 旧版本地库兼容

历史本地库可能已经存在旧版 `assets` 表，字段为 `kind`、`file_name` 等旧命名，缺少当前 `AssetDto` 依赖的 `name`、`type`、`duration_ms`、`thumbnail_path`、`tags`、`updated_at` 等列。Runtime 初始化必须在 `initialize_domain_schema(engine)` 中执行兼容修复：

- 只补齐当前模型查询必需的缺失列。
- `file_name` 回填到 `name`，`kind` 回填到 `type`。
- `updated_at` 为空时回填为 `created_at`。
- 如旧列 `kind`、`file_name`、`mime_type` 带有非空约束并会阻断新 ORM 插入，允许原地重建 `assets` 表；重建必须保留旧数据和旧列值，不清空用户本地资产。
- 兼容修复必须由 `tests/runtime/test_asset_schema_migration.py` 覆盖。

### 6.6 TaskBus WebSocket 依赖

前端任务总线连接 `ws://127.0.0.1:8000/api/ws`。Runtime 运行环境必须安装 `websockets` 或 `wsproto` 之一；当前项目依赖固定为 `websockets>=14.0,<16.0`。如果缺少该依赖，Uvicorn 会记录 `No supported WebSocket library detected`，升级请求会退化成普通 `GET /api/ws` 并持续返回 404。

## 7. 前端调用登记表

| 函数 | 文件 | Runtime 路径 | 返回类型 | 主要消费方 | 更新要求 |
| --- | --- | --- | --- | --- | --- |
| `fetchAssets(type?, q?)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/assets` | `AssetDto[]` | `asset-library` store | 如新增筛选参数，必须同步本文件、类型和测试 |
| `fetchAssetReferences(id)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/assets/{id}/references` | `AssetReferenceDto[]` | `asset-library` store | 删除确认依赖该调用 |
| `deleteAsset(id)` | `apps/desktop/src/app/runtime-client.ts` | `DELETE /api/assets/{id}` | `AssetDeleteResult` | `asset-library` store | 删除前必须先检查引用；后端仍会阻断有引用资产 |
| `importAsset(input)` | `apps/desktop/src/app/runtime-client.ts` | `POST /api/assets/import` | `AssetDto` | `asset-library` store、资产中心页面 | 点击导入必须使用桌面文件选择器多选；只能注册真实本地文件路径，不生成假资产数据 |
| `fetchAsset(id)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/assets/{id}` | `AssetDto` | Runtime client、后续资产检查器编辑能力 | 如页面直接消费，必须补页面状态测试 |
| `updateAsset(id, input)` | `apps/desktop/src/app/runtime-client.ts` | `PATCH /api/assets/{id}` | `AssetDto` | Runtime client、后续资产检查器编辑能力 | 编辑能力开放时必须补 store/page 测试 |
| `fetchVoiceProfiles()` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/voice/profiles` | `VoiceProfileDto[]` | `voice-studio` store、音色选择组件 | 不得在页面内写死 Provider 音色 |
| `fetchVoiceTracks(projectId)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/voice/projects/{project_id}/tracks` | `VoiceTrackDto[]` | `voice-studio` store、配音版本列表 | 列表必须来自真实 Runtime 记录 |
| `generateVoiceTrack(projectId, input)` | `apps/desktop/src/app/runtime-client.ts` | `POST /api/voice/projects/{project_id}/tracks/generate` | `VoiceTrackGenerateResultDto` | `voice-studio` store、配音中心页面 | 无 TTS Provider 时必须展示 `blocked`，不得假成功 |
| `fetchVoiceTrack(trackId)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/voice/tracks/{track_id}` | `VoiceTrackDto` | `voice-studio` store、版本详情 | 返回段落映射，后续字幕/时间线消费依赖该结构 |
| `deleteVoiceTrack(trackId)` | `apps/desktop/src/app/runtime-client.ts` | `DELETE /api/voice/tracks/{track_id}` | `void` | `voice-studio` store、配音版本列表 | 删除失败必须展示中文错误 |

前端本地预览调用登记：

| 调用 | 文件 | 用途 | 更新要求 |
| --- | --- | --- | --- |
| `convertFileSrc(filePath)` | `apps/desktop/src/components/assets/AssetPreview.vue` | 将真实本地视频、图片、文档路径转换为 WebView 可渲染地址；文本类文档读取后按 UTF-8 渲染 | 依赖 Tauri 桌面环境和 `app.security.assetProtocol`；不得用假缩略图替代真实文件预览 |

## 8. 验证命令

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