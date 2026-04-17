# Runtime API 与前端调用真源

**当前状态（2026-04-17）**: Runtime 已覆盖 `search / license / dashboard / scripts / storyboards / workspace / video-deconstruction / voice / subtitles / assets / accounts / devices / automation / publishing / renders / review / settings / tasks / ws / ai-capabilities / ai-providers`。
**接口版本**: V1（统一 JSON 信封，无独立版本号前缀）
**唯一真源约束**: 后端路由、服务、前端 `runtime-client.ts`、Pinia store、契约测试发生变化时，必须在同一次改动中更新本文件。
**编码约束**: 本文档必须使用 UTF-8 无 BOM 保存，所有读取、生成、校验脚本都按 UTF-8 处理，避免中文出现乱码。

---

## 1. 全局约定

### 1.1 基础规则

- Runtime 基础地址：桌面端默认本地 `http://127.0.0.1:8000`
- 成功信封：

```json
{
  "ok": true,
  "data": {}
}
```

- 失败信封：

```json
{
  "ok": false,
  "error": "中文可见错误",
  "error_code": "task.conflict"
}
```

- 时间字段统一使用 ISO 8601 / UTC。
- 文档中的“当前前端调用点”优先写 `runtime-client.ts` 函数名；若当前页面或 store 尚未直接消费，会明确写“当前前端未直接调用”。

### 1.2 通用错误码

| HTTP 状态码 | 含义 | 说明 |
| --- | --- | --- |
| `404` | 资源不存在 | 项目、账号、工作区、视频、任务等目标不存在 |
| `409` | 状态冲突 | 当前状态不允许执行，例如重复运行、删除被引用对象、未就绪对象应用到项目 |
| `422` | 参数校验失败 | 请求体缺字段、字段类型错误、枚举值非法 |
| `500` | Runtime 内部错误 | 服务层异常；前端只显示中文错误，不暴露 traceback |

| `error_code` | 场景 | 说明 |
| --- | --- | --- |
| `request.validation_failed` | 请求体验证失败 | 统一由 `error_response(..., error_code=...)` 返回 |
| `runtime.not-ready` | Runtime 自检未通过 | 适用于版本、依赖、数据库等启动前检查 |
| `runtime.port-occupied` | Runtime 端口被占用 | 适用于 `/api/bootstrap/runtime-selfcheck` 的端口检查 |
| `project.not_found` | 项目不存在 | 适用于 dashboard / script / storyboard 等项目主链 |
| `task.not_found` | 长任务不存在 | 适用于 `/api/tasks/{task_id}` |
| `task.conflict` | 长任务不可取消或状态冲突 | 适用于 `/api/tasks/{task_id}/cancel` |
| `search.query.invalid` | 搜索参数非法 | 预留给 `/api/search` 的查询校验扩展 |

### 1.3 模块索引

| 模块 | 路由前缀 | 当前前端入口 |
| --- | --- | --- |
| 许可证 | `/api/license` | `license.ts`、`BootstrapGate.vue`、`SetupLicenseWizardPage.vue` |
| 首启初始化 | `/api/bootstrap` | `runtime-client.ts`（`initializeDirectories`、`runtimeSelfCheck`） |
| 创作总览 | `/api/dashboard` | `fetchDashboardSummary`、`creator-dashboard` 页面 |
| 脚本与选题中心 | `/api/scripts` | `script-studio.ts`、`ScriptTopicCenterPage.vue` |
| 分镜规划中心 | `/api/storyboards` | `storyboard.ts`、`StoryboardPlanningCenterPage.vue` |
| AI 剪辑工作台 | `/api/workspace` | `editing-workspace.ts`、`AIEditingWorkspacePage.vue` |
| 视频拆解中心 | `/api/video-deconstruction` | `video-import.ts`、`VideoDeconstructionCenterPage.vue` |
| 配音中心 | `/api/voice` | `voice-studio.ts`、`VoiceStudioPage.vue` |
| 字幕对齐中心 | `/api/subtitles` | `subtitle-alignment.ts`、`SubtitleAlignmentCenterPage.vue` |
| 资产中心 | `/api/assets` | `asset-library.ts`、`AssetLibraryPage.vue` |
| 账号管理 | `/api/accounts` | `account-management.ts`、`AccountManagementPage.vue` |
| 设备与工作区管理 | `/api/devices` | `device-workspaces.ts`、`DeviceWorkspaceManagementPage.vue` |
| 自动化执行中心 | `/api/automation` | `automation.ts`、`AutomationConsolePage.vue` |
| 发布中心 | `/api/publishing/plans` | `publishing.ts`、`PublishingCenterPage.vue` |
| 渲染与导出中心 | `/api/renders` | `renders.ts`、`RenderExportCenterPage.vue` |
| 复盘与优化中心 | `/api/review` | `review.ts`、`ReviewOptimizationCenterPage.vue` |
| AI 与系统设置 | `/api/settings`、`/api/settings/ai-capabilities`、`/api/settings/ai-providers` | `config-bus.ts`、`ai-capability.ts`、`AIAndSystemSettingsPage.vue` |
| 全局搜索 | `/api/search` | `searchGlobal` |
| 长任务状态 | `/api/tasks` | `task-bus.ts` |
| WebSocket | `/api/ws` | `task-bus.ts` WebSocket 订阅 |

### 1.4 全局搜索

**核心返回 DTO**: `GlobalSearchResultDto`
关键字段：`projects[]`、`scripts[]`、`tasks[]`、`assets[]`、`accounts[]`、`workspaces[]`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/search` | 查询参数：`q`、`types?`、`limit?` | `GlobalSearchResultDto` | `422`、`500` | `searchGlobal` |

**示例**

```json
{
  "ok": true,
  "data": {
    "projects": [
      {
        "id": "project-1",
        "name": "Alpha 项目",
        "subtitle": "Alpha 描述",
        "updatedAt": "2026-04-17T12:00:00Z"
      }
    ],
    "scripts": [
      {
        "id": "project-1:1",
        "projectId": "project-1",
        "title": "Alpha Hook",
        "snippet": "Alpha Hook 第二行文案",
        "updatedAt": "2026-04-17T12:00:00Z"
      }
    ],
    "tasks": [],
    "assets": [],
    "accounts": [],
    "workspaces": []
  }
}
```

### 2.1 首启运行时初始化

**核心返回 DTO**: `BootstrapDirectoryReportDto`、`RuntimeSelfCheckReportDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `POST /api/bootstrap/initialize-directories` | 无；按当前 settings/config 与 runtime data root 创建并校验目录 | `BootstrapDirectoryReportDto`：`rootDir`、`databasePath`、`status`、`directories[]`、`checkedAt` | `500` | `initializeDirectories` |
| `POST /api/bootstrap/runtime-selfcheck` | 无；执行端口、版本、依赖、数据库聚合自检 | `RuntimeSelfCheckReportDto`：`status`、`runtimeVersion`、`checkedAt`、`items[]` | `500`；单项失败时结果内返回 `runtime.not-ready` / `runtime.port-occupied` | `runtimeSelfCheck` |

**目录初始化示例**

```json
{
  "ok": true,
  "data": {
    "rootDir": "C:/TKOPS/.runtime-data",
    "databasePath": "C:/TKOPS/.runtime-data/runtime.db",
    "status": "ok",
    "directories": [
      {
        "key": "projects",
        "label": "项目目录",
        "path": "C:/TKOPS/.runtime-data/projects",
        "exists": true,
        "writable": true,
        "status": "ok",
        "message": "目录已就绪"
      }
    ],
    "checkedAt": "2026-04-17T12:00:00Z"
  }
}
```

**自检示例**

```json
{
  "ok": true,
  "data": {
    "status": "ok",
    "runtimeVersion": "0.3.3",
    "checkedAt": "2026-04-17T12:00:00Z",
    "items": [
      {
        "key": "port",
        "label": "端口检查",
        "status": "ok",
        "detail": "端口 8000 可用。",
        "errorCode": null,
        "checkedAt": "2026-04-17T12:00:00Z"
      }
    ]
  }
}
```

---

## 2. 许可证

**核心返回 DTO**: `LicenseStatusDto` / `LicenseActivateResultDto`
关键字段：`active`、`restrictedMode`、`machineCode`、`machineBound`、`licenseType`、`maskedCode`、`activatedAt`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/license/status` | 无 | `LicenseStatusDto` | `500` | `fetchLicenseStatus` |
| `POST /api/license/activate` | `LicenseActivateInput`：`activationCode` | `LicenseActivateResultDto` | `422`、`500` | `activateLicense` |

**示例**

```json
{
  "ok": true,
  "data": {
    "active": true,
    "restrictedMode": false,
    "machineCode": "TKOPS-LOCAL-001",
    "machineBound": true,
    "licenseType": "offline",
    "maskedCode": "TKOP-****-001",
    "activatedAt": "2026-04-17T09:30:00Z"
  }
}
```

---

## 3. 创作总览

**核心返回 DTO**: `DashboardSummaryDto`、`ProjectSummaryDto`、`CurrentProjectContextDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/dashboard/summary` | 无 | `DashboardSummaryDto`：`greeting`、`heroContext`、`recentProjects[]`、`todos[]`、`exceptions[]`、`health`、`generatedAt`、`currentProject` | `500` | `fetchDashboardSummary` |
| `POST /api/dashboard/projects` | `CreateProjectInput`：`name`、`description` | `ProjectSummaryDto` | `422`、`500` | `createDashboardProject` |
| `GET /api/dashboard/context` | 无 | `CurrentProjectContextDto \| null` | `500` | `fetchCurrentProjectContext` |
| `PUT /api/dashboard/context` | `SetCurrentProjectInput`：`projectId`，支持 `null` 清空当前项目 | `CurrentProjectContextDto \| null` | `404`、`422` | `updateCurrentProjectContext` |

**示例**

```json
{
  "ok": true,
  "data": {
    "greeting": {
      "title": "上午进度",
      "subtitle": "聚焦当前项目与核心任务。"
    },
    "heroContext": {
      "currentProject": {
        "id": "project-1",
        "name": "TikTok 选题 A",
        "status": "active",
        "lastEditedAt": "2026-04-17T08:30:00Z"
      },
      "primaryAction": {
        "label": "继续项目",
        "action": "resume-project",
        "targetProjectId": "project-1"
      },
      "pendingTasks": 0,
      "blockingIssues": 0
    },
    "recentProjects": [
      {
        "id": "project-1",
        "name": "TikTok 选题 A",
        "description": "创作总览演示项目",
        "status": "active",
        "currentScriptVersion": 2,
        "currentStoryboardVersion": 1,
        "createdAt": "2026-04-17T08:00:00Z",
        "updatedAt": "2026-04-17T08:30:00Z",
        "lastAccessedAt": "2026-04-17T08:30:00Z"
      }
    ],
    "currentProject": {
      "projectId": "project-1",
      "projectName": "TikTok 选题 A",
      "status": "active"
    },
    "todos": [],
    "exceptions": [],
    "health": {
      "runtimeStatus": "online",
      "aiProviderStatus": "ready",
      "taskBusStatus": "idle"
    },
    "generatedAt": "2026-04-17T08:30:00Z"
  }
}
```

---

## 4. 脚本与选题中心

**核心返回 DTO**: `ScriptDocumentDto`
关键字段：`projectId`、`currentVersion`、`versions[]`、`recentJobs[]`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/scripts/projects/{project_id}/document` | 路径参数：`project_id` | `ScriptDocumentDto` | `404`、`500` | `fetchScriptDocument` |
| `PUT /api/scripts/projects/{project_id}/document` | `ScriptSaveInput`：`content` | `ScriptDocumentDto` | `404`、`422` | `saveScriptDocument` |
| `POST /api/scripts/projects/{project_id}/generate` | `ScriptGenerateInput`：`topic` | `ScriptDocumentDto` | `404`、`409`、`500` | `generateScriptDocument` |
| `POST /api/scripts/projects/{project_id}/rewrite` | `ScriptRewriteInput`：`instructions` | `ScriptDocumentDto` | `404`、`409`、`500` | `rewriteScriptDocument` |

**示例**

```json
{
  "ok": true,
  "data": {
    "projectId": "project-1",
    "currentVersion": {
      "revision": 3,
      "source": "video_extraction",
      "content": "第一幕：钩子开场……",
      "provider": null,
      "model": null,
      "aiJobId": null,
      "createdAt": "2026-04-17T10:00:00Z"
    },
    "versions": [],
    "recentJobs": []
  }
}
```

---

## 5. 分镜规划中心

**核心返回 DTO**: `StoryboardDocumentDto`
关键字段：`projectId`、`basedOnScriptRevision`、`currentVersion`、`versions[]`、`recentJobs[]`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/storyboards/projects/{project_id}/document` | 路径参数：`project_id` | `StoryboardDocumentDto` | `404`、`500` | `fetchStoryboardDocument` |
| `PUT /api/storyboards/projects/{project_id}/document` | `StoryboardSaveInput`：`basedOnScriptRevision`、`scenes[]` | `StoryboardDocumentDto` | `404`、`422` | `saveStoryboardDocument` |
| `POST /api/storyboards/projects/{project_id}/generate` | 路径参数：`project_id` | `StoryboardDocumentDto` | `404`、`409`、`500` | `generateStoryboardDocument` |

**示例**

```json
{
  "ok": true,
  "data": {
    "projectId": "project-1",
    "basedOnScriptRevision": 3,
    "currentVersion": {
      "revision": 1,
      "basedOnScriptRevision": 3,
      "source": "manual",
      "scenes": [
        {
          "sceneId": "scene-1",
          "title": "开场镜头",
          "summary": "主播展示成品",
          "visualPrompt": "竖屏近景，明亮布光"
        }
      ],
      "provider": null,
      "model": null,
      "aiJobId": null,
      "createdAt": "2026-04-17T10:05:00Z"
    },
    "versions": [],
    "recentJobs": []
  }
}
```

---

## 6. AI 剪辑工作台

**核心返回 DTO**: `WorkspaceTimelineResultDto`、`TimelineDto`、`WorkspaceAICommandResultDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/workspace/projects/{project_id}/timeline` | 路径参数：`project_id` | `WorkspaceTimelineResultDto`：`timeline`、`message` | `404`、`500` | `fetchWorkspaceTimeline` |
| `POST /api/workspace/projects/{project_id}/timeline` | `TimelineCreateInput`：`name` | `TimelineDto` | `404`、`422` | `createWorkspaceTimeline` |
| `PATCH /api/workspace/timelines/{timeline_id}` | `TimelineUpdateInput`：`name?`、`durationSeconds?`、`tracks[]` | `TimelineDto` | `404`、`422` | `updateWorkspaceTimeline` |
| `POST /api/workspace/projects/{project_id}/ai-commands` | `WorkspaceAICommandInput`：`timelineId?`、`capabilityId`、`parameters` | `WorkspaceAICommandResultDto`，当前固定 `status=blocked` | `404`、`422` | `runWorkspaceAICommand` |

**示例**

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

---

## 7. 视频拆解中心

**核心返回 DTO**: `ImportedVideoDto`、`VideoTranscriptDto`、`VideoSegmentDto`、`VideoStructureExtractionDto`、`ApplyVideoExtractionResultDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `POST /api/video-deconstruction/projects/{project_id}/import` | `ImportVideoInput`：`filePath` | `ImportedVideoDto` | `404`、`422` | `importVideo` |
| `GET /api/video-deconstruction/projects/{project_id}/videos` | 路径参数：`project_id` | `ImportedVideoDto[]` | `404` | `fetchImportedVideos` |
| `DELETE /api/video-deconstruction/videos/{video_id}` | 路径参数：`video_id` | `null` | `404` | `deleteImportedVideo` |
| `POST /api/video-deconstruction/videos/{video_id}/transcribe` | 无 | `VideoTranscriptDto`；无 Provider 时 `status=pending_provider` 且 `text=null` | `404` | `startVideoTranscription` |
| `GET /api/video-deconstruction/videos/{video_id}/transcript` | 无 | `VideoTranscriptDto` | `404` | `fetchVideoTranscript` |
| `POST /api/video-deconstruction/videos/{video_id}/segment` | 无 | `VideoSegmentDto[]` | `404`、`409` | `runVideoSegmentation` |
| `GET /api/video-deconstruction/videos/{video_id}/segments` | 无 | `VideoSegmentDto[]` | `404` | `fetchVideoSegments` |
| `POST /api/video-deconstruction/videos/{video_id}/extract-structure` | 无 | `VideoStructureExtractionDto`；依赖 transcript | `404`、`409` | `extractVideoStructure` |
| `GET /api/video-deconstruction/videos/{video_id}/structure` | 无 | `VideoStructureExtractionDto` | `404` | `fetchVideoStructure` |
| `POST /api/video-deconstruction/extractions/{extraction_id}/apply-to-project` | 无 | `ApplyVideoExtractionResultDto`：`projectId`、`extractionId`、`scriptRevision`、`status`、`message` | `404`、`409` | `applyVideoExtractionToProject` |

**示例**

```json
{
  "ok": true,
  "data": {
    "id": "transcript-1",
    "videoId": "video-1",
    "language": "zh-CN",
    "text": null,
    "status": "pending_provider",
    "createdAt": "2026-04-17T10:10:00Z",
    "updatedAt": "2026-04-17T10:10:00Z"
  }
}
```

---

## 8. 配音中心

**核心返回 DTO**: `VoiceProfileDto`、`VoiceTrackDto`、`VoiceTrackGenerateResultDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/voice/profiles` | 无 | `VoiceProfileDto[]` | `500` | `fetchVoiceProfiles` |
| `GET /api/voice/projects/{project_id}/tracks` | 路径参数：`project_id` | `VoiceTrackDto[]` | `404` | `fetchVoiceTracks` |
| `POST /api/voice/projects/{project_id}/tracks/generate` | `VoiceTrackGenerateInput`：`profileId`、`sourceText`、`speed`、`pitch`、`emotion` | `VoiceTrackGenerateResultDto`：`track`、`task`、`message` | `404`、`422`、`409` | `generateVoiceTrack` |
| `GET /api/voice/tracks/{track_id}` | 路径参数：`track_id` | `VoiceTrackDto` | `404` | `fetchVoiceTrack` |
| `DELETE /api/voice/tracks/{track_id}` | 路径参数：`track_id` | 删除结果对象 | `404` | `deleteVoiceTrack` |

**示例**

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
      "voiceName": "标准女声",
      "filePath": null,
      "segments": [],
      "status": "blocked",
      "createdAt": "2026-04-17T10:15:00Z"
    },
    "task": null,
    "message": "当前未配置可用 TTS Provider，已保留配音轨草稿。"
  }
}
```

---

## 9. 字幕对齐中心

**核心返回 DTO**: `SubtitleTrackDto`、`SubtitleTrackGenerateResultDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/subtitles/projects/{project_id}/tracks` | 路径参数：`project_id` | `SubtitleTrackDto[]` | `404` | `fetchSubtitleTracks` |
| `POST /api/subtitles/projects/{project_id}/tracks/generate` | `SubtitleTrackGenerateInput`：`sourceText`、`language`、`stylePreset` | `SubtitleTrackGenerateResultDto`：`track`、`task`、`message` | `404`、`422`、`409` | `generateSubtitleTrack` |
| `GET /api/subtitles/tracks/{track_id}` | 路径参数：`track_id` | `SubtitleTrackDto` | `404` | `fetchSubtitleTrack` |
| `PATCH /api/subtitles/tracks/{track_id}` | `SubtitleTrackUpdateInput`：`segments[]`、`style` | `SubtitleTrackDto` | `404`、`422` | `updateSubtitleTrack` |
| `DELETE /api/subtitles/tracks/{track_id}` | 路径参数：`track_id` | 删除结果对象 | `404` | `deleteSubtitleTrack` |

**示例**

```json
{
  "ok": true,
  "data": {
    "id": "subtitle-1",
    "projectId": "project-1",
    "timelineId": null,
    "source": "ai_generated",
    "language": "zh-CN",
    "style": {
      "preset": "clean",
      "fontSize": 40,
      "position": "bottom",
      "textColor": "#FFFFFF",
      "background": "rgba(0,0,0,0.35)"
    },
    "segments": [],
    "status": "ready",
    "createdAt": "2026-04-17T10:18:00Z"
  }
}
```

---

## 10. 资产中心

**核心返回 DTO**: `AssetDto`、`AssetReferenceDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/assets` | 查询参数：`type?`、`source?`、`project_id?`、`q?` | `AssetDto[]` | `500` | `fetchAssets` |
| `POST /api/assets` | `AssetCreateInput`：`name`、`type`、`source`、`filePath?`、`projectId?` 等 | `AssetDto` | `422` | 当前前端未直接调用 |
| `POST /api/assets/import` | `AssetImportInput`：`filePath`、`type`、`source`、`projectId?` 等 | `AssetDto` | `422`、`500` | `importAsset` |
| `GET /api/assets/{asset_id}` | 路径参数：`asset_id` | `AssetDto` | `404` | `fetchAsset` |
| `PATCH /api/assets/{asset_id}` | `AssetUpdateInput`：`name?`、`tags?`、`metadataJson?` | `AssetDto` | `404`、`422` | `updateAsset` |
| `DELETE /api/assets/{asset_id}` | 路径参数：`asset_id` | 删除结果对象 | `404` | `deleteAsset` |
| `GET /api/assets/{asset_id}/references` | 路径参数：`asset_id` | `AssetReferenceDto[]` | `404` | `fetchAssetReferences` |
| `POST /api/assets/{asset_id}/references` | `AssetReferenceCreateInput`：`referenceType`、`referenceId` | `AssetReferenceDto` | `404`、`422` | 当前前端未直接调用 |
| `GET /api/assets/references/{ref_id}` | 路径参数：`ref_id` | `AssetReferenceDto` | `404` | 当前前端未直接调用 |
| `DELETE /api/assets/references/{ref_id}` | 路径参数：`ref_id` | 删除结果对象 | `404` | 当前前端未直接调用 |

**示例**

```json
{
  "ok": true,
  "data": {
    "id": "asset-1",
    "name": "成片封面",
    "type": "image",
    "source": "imported",
    "filePath": "C:/workspace/assets/cover.png",
    "fileSizeBytes": 204800,
    "durationMs": null,
    "thumbnailPath": null,
    "tags": "[\"封面\",\"竖屏\"]",
    "projectId": "project-1",
    "metadataJson": "{\"width\":1080,\"height\":1920}",
    "createdAt": "2026-04-17T10:20:00Z",
    "updatedAt": "2026-04-17T10:20:00Z"
  }
}
```

---

## 11. 账号管理

**核心返回 DTO**: `AccountDto`、`AccountGroupDto`、`AccountRefreshStatsDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/accounts` | 查询参数：`status?`、`platform?`、`group_id?`、`q?` | `AccountDto[]` | `500` | `fetchAccounts` |
| `POST /api/accounts` | `AccountCreateInput`：`name`、`platform`、`status` 等 | `AccountDto` | `422` | `createAccount` |
| `GET /api/accounts/{account_id}` | 路径参数：`account_id` | `AccountDto` | `404` | 当前前端未直接调用 |
| `PATCH /api/accounts/{account_id}` | `AccountUpdateInput` | `AccountDto` | `404`、`422` | 当前前端未直接调用 |
| `DELETE /api/accounts/{account_id}` | 路径参数：`account_id` | 删除结果对象 | `404` | `deleteAccount` |
| `POST /api/accounts/{account_id}/refresh-stats` | 路径参数：`account_id` | `AccountRefreshStatsDto` | `404` | `refreshAccountStats` |
| `POST /api/accounts/{account_id}/status-check` | 与 `refresh-stats` 相同；历史兼容别名 | `AccountRefreshStatsDto` | `404` | `runAccountStatusCheck` |
| `GET /api/accounts/groups` | 无 | `AccountGroupDto[]` | `500` | `fetchAccountGroups` |
| `POST /api/accounts/groups` | `AccountGroupCreateInput`：`name`、`description?`、`color?` | `AccountGroupDto` | `422` | 当前前端未直接调用 |
| `PATCH /api/accounts/groups/{group_id}` | `AccountGroupUpdateInput` | `AccountGroupDto` | `404`、`422` | 当前前端未直接调用 |
| `DELETE /api/accounts/groups/{group_id}` | 路径参数：`group_id` | 删除结果对象 | `404` | 当前前端未直接调用 |
| `GET /api/accounts/groups/{group_id}/members` | 路径参数：`group_id` | `AccountDto[]` | `404` | 当前前端未直接调用 |
| `POST /api/accounts/groups/{group_id}/members` | `AccountGroupMemberCreateInput`：`accountId` | 成功结果对象 | `404`、`422` | 当前前端未直接调用 |
| `DELETE /api/accounts/groups/{group_id}/members/{account_id}` | 路径参数：`group_id`、`account_id` | 成功结果对象 | `404` | 当前前端未直接调用 |

**示例**

```json
{
  "ok": true,
  "data": {
    "id": "account-1",
    "status": "active",
    "updatedAt": "2026-04-17T10:22:00Z",
    "providerStatus": "pending_provider"
  }
}
```

---

## 12. 设备与工作区管理

**核心返回 DTO**: `DeviceWorkspaceDto`、`HealthCheckResultDto`、`BrowserInstanceDto`、`ExecutionBindingDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/devices/workspaces` | 无 | `DeviceWorkspaceDto[]` | `500` | `fetchDeviceWorkspaces` |
| `POST /api/devices/workspaces` | `DeviceWorkspaceCreateInput`：`name`、`root_path` | `DeviceWorkspaceDto` | `422` | `createDeviceWorkspace` |
| `GET /api/devices/workspaces/{ws_id}` | 路径参数：`ws_id` | `DeviceWorkspaceDto` | `404` | `fetchDeviceWorkspace` |
| `PATCH /api/devices/workspaces/{ws_id}` | `DeviceWorkspaceUpdateInput`：`name?`、`root_path?`、`status?` | `DeviceWorkspaceDto` | `404`、`422` | `updateDeviceWorkspace` |
| `DELETE /api/devices/workspaces/{ws_id}` | 路径参数：`ws_id`；删除时会级联清理 browser instances 与 bindings | 删除结果对象 | `404` | `deleteDeviceWorkspace` |
| `POST /api/devices/workspaces/{ws_id}/health-check` | 无 | `HealthCheckResultDto` | `404` | `checkDeviceWorkspaceHealth` |
| `GET /api/devices/browser-instances` | 查询参数：`workspace_id?` | `BrowserInstanceDto[]` | `500` | `fetchBrowserInstances` |
| `POST /api/devices/browser-instances` | `BrowserInstanceCreateInput`：`workspace_id`、`name`、`profile_path`、`browser_type` | `BrowserInstanceDto` | `404`、`422` | `createBrowserInstance` |
| `DELETE /api/devices/browser-instances/{instance_id}` | 路径参数：`instance_id` | 删除结果对象 | `404`、`409` | `removeBrowserInstance` |
| `GET /api/devices/bindings` | 查询参数：`workspace_id?`、`account_id?` | `ExecutionBindingDto[]` | `500` | `fetchExecutionBindings` |
| `POST /api/devices/bindings` | `ExecutionBindingCreateInput`：`account_id`、`device_workspace_id`、`browser_instance_id?`、`source?`、`metadata_json?` | `ExecutionBindingDto` | `404`、`422`、`409` | `createExecutionBinding` |
| `DELETE /api/devices/bindings/{binding_id}` | 路径参数：`binding_id` | 删除结果对象 | `404` | `removeExecutionBinding` |

**示例**

```json
{
  "ok": false,
  "error": "当前浏览器实例已被执行绑定引用，无法直接删除。"
}
```

---

## 13. 自动化执行中心

**核心返回 DTO**: `AutomationTaskDto`、`AutomationTaskRunDto`、`AutomationTaskRunLogsDto`、`TriggerTaskResultDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/automation/tasks` | 无 | `AutomationTaskDto[]` | `500` | `fetchAutomationTasks` |
| `POST /api/automation/tasks` | `AutomationTaskCreateInput`：`name`、`type`、`cron_expr?`、`config_json?` | `AutomationTaskDto` | `422` | `createAutomationTask` |
| `GET /api/automation/tasks/{task_id}` | 路径参数：`task_id` | `AutomationTaskDto` | `404` | `fetchAutomationTask` |
| `PATCH /api/automation/tasks/{task_id}` | `AutomationTaskUpdateInput` | `AutomationTaskDto` | `404`、`422` | `updateAutomationTask` |
| `DELETE /api/automation/tasks/{task_id}` | 路径参数：`task_id` | 删除结果对象 | `404` | `deleteAutomationTask` |
| `POST /api/automation/tasks/{task_id}/trigger` | 无 | `TriggerTaskResultDto`：`task_id`、`run_id`、`status`、`message` | `404`、`409` | `triggerAutomationTask` |
| `GET /api/automation/tasks/{task_id}/runs` | 路径参数：`task_id` | `AutomationTaskRunDto[]` | `404` | `fetchAutomationTaskRuns` |
| `GET /api/automation/runs/{run_id}` | 路径参数：`run_id` | `AutomationTaskRunDto` | `404` | `fetchAutomationRun` |
| `POST /api/automation/runs/{run_id}/cancel` | 路径参数：`run_id`；仅允许 `queued/running` | `AutomationTaskRunDto` | `404`、`409` | `cancelAutomationRun` |
| `GET /api/automation/runs/{run_id}/logs` | 路径参数：`run_id` | `AutomationTaskRunLogsDto`：`run_id`、`log_text`、`lines[]` | `404` | `fetchAutomationRunLogs` |

**示例**

```json
{
  "ok": true,
  "data": {
    "run_id": "run-1",
    "log_text": "任务开始\n正在执行采集",
    "lines": [
      "任务开始",
      "正在执行采集"
    ]
  }
}
```

---

## 14. 发布中心

**核心返回 DTO**: `PublishPlanDto`、`PrecheckResultDto`、`SubmitPlanResultDto`、`PublishReceiptDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/publishing/plans` | 无 | `PublishPlanDto[]` | `500` | `fetchPublishPlans` |
| `POST /api/publishing/plans` | `PublishPlanCreateInput`：`title`、`account_id?`、`account_name?`、`project_id?`、`video_asset_id?`、`scheduled_at?` | `PublishPlanDto` | `422` | `createPublishPlan` |
| `GET /api/publishing/plans/{plan_id}` | 路径参数：`plan_id` | `PublishPlanDto` | `404` | `fetchPublishPlan` |
| `PATCH /api/publishing/plans/{plan_id}` | `PublishPlanUpdateInput`：`title?`、`account_name?`、`status?`、`scheduled_at?` | `PublishPlanDto` | `404`、`422` | `updatePublishPlan` |
| `DELETE /api/publishing/plans/{plan_id}` | 路径参数：`plan_id` | 删除结果对象 | `404` | `deletePublishPlan` |
| `POST /api/publishing/plans/{plan_id}/precheck` | 无 | `PrecheckResultDto`：`items[]`、`has_errors`、`checked_at`；当前复用 `precheck_result_json` 存储 | `404` | `runPublishingPrecheck` |
| `POST /api/publishing/plans/{plan_id}/submit` | 无；要求预检无 `error` | `SubmitPlanResultDto`：`plan_id`、`status`、`submitted_at`、`message` | `404`、`409` | `submitPublishPlan` |
| `POST /api/publishing/plans/{plan_id}/cancel` | 无 | `PublishPlanDto` | `404` | `cancelPublishPlan` |
| `GET /api/publishing/plans/{plan_id}/receipt` | 路径参数：`plan_id` | `PublishReceiptDto`：`id`、`plan_id`、`status`、`external_url`、`error_message`、`completed_at` | `404` | `fetchPublishReceipt` |

**示例**

```json
{
  "ok": true,
  "data": {
    "id": "receipt-1",
    "plan_id": "plan-1",
    "status": "manual_required",
    "external_url": null,
    "error_message": null,
    "completed_at": null,
    "created_at": "2026-04-17T10:25:00Z"
  }
}
```

---

## 15. 渲染与导出中心

**核心返回 DTO**: `RenderTaskDto`、`CancelRenderResultDto`、`ExportProfileDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/renders/profiles` | 无；首次访问会补齐默认配置 | `ExportProfileDto[]` | `500` | `fetchExportProfiles` |
| `POST /api/renders/profiles` | `ExportProfileCreateInput`：`name`、`format`、`resolution`、`fps`、`video_bitrate`、`audio_policy`、`subtitle_policy`、`config_json?` | `ExportProfileDto` | `422` | `createExportProfile` |
| `GET /api/renders/tasks` | 无 | `RenderTaskDto[]` | `500` | `fetchRenderTasks` |
| `POST /api/renders/tasks` | `RenderTaskCreateInput`：`project_id?`、`project_name?`、`preset`、`format` | `RenderTaskDto` | `422` | `createRenderTask` |
| `GET /api/renders/tasks/{task_id}` | 路径参数：`task_id` | `RenderTaskDto` | `404` | `fetchRenderTask` |
| `PATCH /api/renders/tasks/{task_id}` | `RenderTaskUpdateInput`：`preset?`、`format?`、`status?`、`progress?`、`output_path?`、`error_message?` | `RenderTaskDto` | `404`、`422` | `updateRenderTask` |
| `DELETE /api/renders/tasks/{task_id}` | 路径参数：`task_id` | 删除结果对象 | `404` | `deleteRenderTask` |
| `POST /api/renders/tasks/{task_id}/cancel` | 路径参数：`task_id` | `CancelRenderResultDto` | `404`、`409` | `cancelRenderTask` |
| `POST /api/renders/tasks/{task_id}/retry` | 路径参数：`task_id`；仅允许 `failed/cancelled`，复用原 task 重置状态 | `RenderTaskDto` | `404`、`409` | `retryRenderTask` |

**示例**

```json
{
  "ok": true,
  "data": {
    "id": "profile-default",
    "name": "默认竖屏导出",
    "format": "mp4",
    "resolution": "1080x1920",
    "fps": 30,
    "video_bitrate": "8000k",
    "audio_policy": "merge_all",
    "subtitle_policy": "burn_in",
    "config_json": null,
    "is_default": true,
    "created_at": "2026-04-17T10:26:00Z",
    "updated_at": "2026-04-17T10:26:00Z"
  }
}
```

---

## 16. 复盘与优化中心

**核心返回 DTO**: `ReviewSummaryDto`、`GenerateReviewSuggestionsResultDto`、`ApplyReviewSuggestionResultDto`
`ReviewSuggestion` 关键字段：`id`、`code`、`category`、`title`、`description`、`priority`、`status`、`actionLabel`、`sourceType`、`sourceId`、`createdAt`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/review/projects/{project_id}/summary` | 路径参数：`project_id` | `ReviewSummaryDto` | `404` | `fetchReviewSummary` |
| `POST /api/review/projects/{project_id}/analyze` | 路径参数：`project_id` | `AnalyzeProjectResultDto`：`project_id`、`status`、`message`、`analyzed_at` | `404`、`409` | `analyzeReviewProject` |
| `PATCH /api/review/projects/{project_id}/summary` | `ReviewSummaryUpdateInput`：核心指标字段 | `ReviewSummaryDto` | `404`、`422` | `updateReviewSummary` |
| `GET /api/review/projects/{project_id}/suggestions` | 路径参数：`project_id` | `ReviewSuggestion[]` | `404` | `fetchReviewSuggestions` |
| `POST /api/review/projects/{project_id}/suggestions/generate` | 路径参数：`project_id`；当前复用规则生成 | `GenerateReviewSuggestionsResultDto`：`project_id`、`status`、`message`、`generated_count`、`generated_at` | `404`、`409` | `generateReviewSuggestions` |
| `PATCH /api/review/suggestions/{suggestion_id}` | `ReviewSuggestionUpdateInput`：`status`，仅允许 `pending/applied/dismissed` | `ReviewSuggestion` | `404`、`409`、`422` | `updateReviewSuggestion` |
| `POST /api/review/suggestions/{suggestion_id}/apply-to-script` | 无；应用后通过 script service 生成新草稿版本 | `ApplyReviewSuggestionResultDto`：`project_id`、`suggestion_id`、`script_revision`、`status`、`message` | `404`、`409` | `applyReviewSuggestionToScript` |

**示例**

```json
{
  "ok": true,
  "data": {
    "project_id": "project-1",
    "status": "ready",
    "message": "已生成 3 条优化建议。",
    "generated_count": 3,
    "generated_at": "2026-04-17T10:28:00Z"
  }
}
```

---

## 17. AI 与系统设置

### 17.1 Runtime 基础设置

**核心返回 DTO**: `RuntimeHealthSnapshotDto`、`AppSettingsDto`、`RuntimeDiagnosticsDto`、`RuntimeLogPageDto`、`DiagnosticsBundleDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/settings/health` | 无 | `RuntimeHealthSnapshotDto`：`runtime`、`aiProvider`、`renderQueue`、`publishingQueue`、`taskBus`、`license`、`lastSyncAt` | `500` | `fetchRuntimeHealth` |
| `GET /api/settings/config` | 无 | `AppSettingsDto`：`runtime`、`paths`、`logging`、`ai`、`revision` | `500` | `fetchRuntimeConfig` |
| `PUT /api/settings/config` | `AppSettingsUpdateInput`：`runtime.mode/workspaceRoot`、`paths.cacheDir/exportDir/logDir`、`logging.level`、`ai.provider/model/voice/subtitleMode`；成功后广播 `config.changed` | `AppSettingsDto` | `422`、`500` | `updateRuntimeConfig` |
| `GET /api/settings/diagnostics` | 无 | `RuntimeDiagnosticsDto`：`databasePath`、`logDir`、`revision`、`mode`、`healthStatus` | `500` | `fetchRuntimeDiagnostics` |
| `GET /api/settings/logs` | 查询参数：`kind?`、`since?`、`level?`、`limit?`；当前从 `runtime.jsonl` 读取结构化日志 | `RuntimeLogPageDto`：`items[]`、`nextCursor` | `422`、`500` | `fetchRuntimeLogs` |
| `POST /api/settings/diagnostics/export` | 无；生成当前 settings / health / diagnostics / runtime.jsonl 的诊断包 | `DiagnosticsBundleDto`：`bundlePath`、`createdAt`、`entries[]` | `500` | `exportDiagnosticsBundle` |

### 17.2 AI 能力配置

**核心返回 DTO**: `AICapabilitySettingsDto`、`AICapabilitySupportMatrixDto`、`AIProviderHealthDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/settings/ai-capabilities` | 无 | `AICapabilitySettingsDto`：`capabilities[]`、`providers[]` | `500` | `fetchAICapabilitySettings` |
| `PUT /api/settings/ai-capabilities` | `AICapabilityConfigListInput`：`capabilities[]`；成功后广播 `ai-capability.changed` | `AICapabilitySettingsDto` | `422`、`500` | `updateAICapabilitySettings` |
| `GET /api/settings/ai-capabilities/support-matrix` | 无 | `AICapabilitySupportMatrixDto` | `500` | `fetchAICapabilitySupportMatrix` |
| `PUT /api/settings/ai-capabilities/providers/{provider_id}/secret` | `AIProviderSecretInput`：`apiKey`、`baseUrl?` | `AIProviderSecretStatusDto` | `404`、`422` | `updateAIProviderSecret` |
| `POST /api/settings/ai-capabilities/providers/{provider_id}/health-check` | `AIProviderHealthCheckInput`：`model?` | `AIProviderHealthDto` | `404`、`422` | `checkAIProviderHealth` |

### 17.3 AI Provider 目录

**核心返回 DTO**: `AIProviderCatalogItemDto`、`AIModelCatalogItemDto`、`AIModelCatalogRefreshResultDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/settings/ai-providers/catalog` | 无 | `AIProviderCatalogItemDto[]` | `500` | `fetchAIProviderCatalog` |
| `GET /api/settings/ai-providers/{provider_id}/models` | 路径参数：`provider_id` | `AIModelCatalogItemDto[]` | `404` | `fetchAIProviderModels` |
| `POST /api/settings/ai-providers/{provider_id}/models/refresh` | 路径参数：`provider_id` | `AIModelCatalogRefreshResultDto` | `404`、`409` | `refreshAIProviderModels` |

**健康示例**

```json
{
  "ok": true,
  "data": {
    "runtime": {
      "status": "online",
      "port": 8000,
      "uptimeMs": 1200,
      "version": "0.3.3"
    },
    "aiProvider": {
      "status": "configured",
      "latencyMs": null,
      "providerId": "openai",
      "providerName": "OpenAI",
      "lastChecked": null
    },
    "renderQueue": {
      "running": 0,
      "queued": 0,
      "avgWaitMs": null
    },
    "publishingQueue": {
      "pendingToday": 0,
      "failedToday": 0
    },
    "taskBus": {
      "running": 0,
      "queued": 0,
      "blocked": 0,
      "failed24h": 0
    },
    "license": {
      "status": "missing",
      "expiresAt": null
    },
    "lastSyncAt": "2026-04-17T12:00:00Z",
    "service": "online",
    "version": "0.3.3",
    "now": "2026-04-17T12:00:00Z",
    "mode": "development"
  }
}
```

**配置示例**

```json
{
  "ok": true,
  "data": {
    "runtime": {
      "mode": "desktop",
      "workspaceRoot": "C:/TKOPS/workspaces"
    },
    "paths": {
      "cacheDir": "C:/TKOPS/cache",
      "exportDir": "C:/TKOPS/exports",
      "logDir": "C:/TKOPS/logs"
    },
    "logging": {
      "level": "INFO"
    },
    "ai": {
      "provider": "openai",
      "model": "gpt-5.4-mini",
      "voice": "alloy",
      "subtitleMode": "auto"
    },
    "revision": 3
  }
}
```

---

## 18. 长任务状态

**核心返回结构**: `TaskDto`
关键字段：`id`、`kind`、`label`、`status`、`progressPct`、`startedAt`、`finishedAt`、`etaMs`、`projectId`、`ownerRef`、`errorCode`、`errorMessage`、`retryable`、`createdAt`、`updatedAt`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/tasks` | 查询参数：`type?`、`status?`（逗号分隔） | `TaskDto[]` | `500` | `fetchActiveTasks` |
| `GET /api/tasks/{task_id}` | 路径参数：`task_id` | `TaskDto` | `404` | `fetchTaskStatus` |
| `POST /api/tasks/{task_id}/cancel` | 路径参数：`task_id` | `{ task_id, status, message }` | `404`、`409`（`task.conflict`） | `cancelTask` |

**示例**

```json
{
  "ok": true,
  "data": {
    "id": "task-1",
    "kind": "video-import",
    "label": "导入视频",
    "status": "running",
    "progressPct": 45,
    "startedAt": "2026-04-17T10:30:00Z",
    "finishedAt": null,
    "etaMs": 120000,
    "projectId": "project-1",
    "ownerRef": {
      "kind": "imported-video",
      "id": "video-1"
    },
    "errorCode": null,
    "errorMessage": null,
    "retryable": false,
    "createdAt": "2026-04-17T10:30:00Z",
    "updatedAt": "2026-04-17T10:30:10Z"
  }
}
```

---

## 19. WebSocket

**连接地址**: `WS /api/ws`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `WS /api/ws` | 无；连接建立后用于任务广播与心跳保持 | 服务端主动推送任务事件 | 连接断开时由前端重连 | `task-bus.ts` |

**当前事件格式（任务类）**

```json
{
  "schema_version": 1,
  "type": "task.progress",
  "taskId": "task-1",
  "taskType": "tts_generation",
  "projectId": "project-1",
  "status": "running",
  "progress": 45,
  "message": "正在生成第 3/8 段..."
}
```

**当前已落地事件类型**

- `task.started`
- `task.progress`
- `task.completed`
- `task.failed`
- `config.changed`
- `ai-capability.changed`
- `context.project.changed`

**非任务事件示例**

```json
{
  "schema_version": 1,
  "type": "config.changed",
  "payload": {
    "changedKeys": ["logging.level"],
    "revision": 2
  }
}
```

**日志分页示例**

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "timestamp": "2026-04-17T12:05:00Z",
        "level": "INFO",
        "kind": "audit",
        "requestId": "req-123",
        "message": "settings.updated",
        "context": {
          "revision": 2
        }
      }
    ],
    "nextCursor": null
  }
}
```

**诊断包示例**

```json
{
  "ok": true,
  "data": {
    "bundlePath": "C:/TKOPS/exports/diagnostics/tk-ops-diagnostics-20260417-120500.zip",
    "createdAt": "2026-04-17T12:05:00Z",
    "entries": [
      {
        "name": "settings.json",
        "path": "settings.json",
        "sizeBytes": 420
      },
      {
        "name": "runtime.jsonl",
        "path": "runtime.jsonl",
        "sizeBytes": 1024
      }
    ]
  }
}
```

---

## 20. 文档维护检查清单

当你修改 Runtime 接口时，至少同步核对以下内容：

1. `apps/py-runtime/src/api/routes/`
2. `apps/py-runtime/src/services/`
3. `apps/py-runtime/src/repositories/`
4. `apps/py-runtime/src/schemas/`
5. `apps/desktop/src/types/runtime.ts`
6. `apps/desktop/src/app/runtime-client.ts`
7. 对应 Pinia store / 页面消费点
8. `tests/contracts/` 与 `apps/desktop/tests/`
9. 本文件 `docs/RUNTIME-API-CALLS.md`

当前文档与代码对齐批次：**2026-04-17 Runtime 接口补齐与 M06/M11/M12/M13/M14/M15 收口**
