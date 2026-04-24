> 更新日期：2026-04-24；对应应用版本以根 `package.json#version` 为准。本文以当前 `main` 代码为接口真源，记录已落地 Runtime 接口与前端调用关系。V2 前端已接通 `deleteDashboardProject`、浏览器实例 CRUD、FFprobe 诊断消费链路。

# Runtime API 与前端调用真源

**当前状态（2026-04-24）**: Runtime 已覆盖 `search / prompt-templates / license / dashboard / scripts / storyboards / workspace / video-deconstruction / voice / subtitles / assets / accounts / devices / automation / publishing / renders / review / settings / tasks / ws / ai-capabilities / ai-providers`。`test_runtime_contract_inventory.py` 已校验 HTTP 文档路由与 FastAPI 注册路由一致（181 / 181）；`bootstrap.readiness / dashboard.delete / settings.diagnostics.media / devices.browser-instances / ai-providers runtime / dashboard summary` 已回流到本文。§21-24 的 AI Provider 调用层架构定义与分阶段路线图继续保留为后续实现真源。
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
| `runtime.port-not-listening` | Runtime 端口未监听 | 适用于 `/api/bootstrap/runtime-selfcheck` 的端口检查；监听中返回 `ok`，未监听返回 `warning` |
| `license.not_activated` | 许可证未激活 | 适用于 `GET /api/bootstrap/readiness` 的阻断项 |
| `project.not_found` | 项目不存在 | 适用于 dashboard / script / storyboard 等项目主链 |
| `task.not_found` | 长任务不存在 | 适用于 `/api/tasks/{task_id}` |
| `task.conflict` | 长任务不可取消或状态冲突 | 适用于 `/api/tasks/{task_id}/cancel` |
| `project.delete_blocked` | 项目删除被阻断 | 项目仍存在未完成任务，禁止软删除 |
| `provider.health.refresh_failed` | AI Provider 聚合健康刷新失败 | 适用于 `/api/ai-providers/health/refresh` 的单 Provider 刷新失败场景 |
| `provider.model.capability_required` | AI Provider 模型能力声明缺失 | 适用于 `PUT /api/ai-providers/{provider_id}/models/{model_id}` |
| `media.ffprobe_unavailable` | ffprobe 不可用 | 适用于 `/api/settings/diagnostics/media` 与视频拆解链路 |
| `media.ffprobe_incompatible` | ffprobe 版本或输出不兼容 | 适用于 `/api/settings/diagnostics/media` 与视频拆解链路 |
| `account.status_inactive` | 账号当前未启用 | 适用于账号发布校验 |
| `account.username_missing` | 账号缺少用户名 | 适用于账号发布校验 |
| `account.authorization_expired` | 账号授权已过期 | 适用于账号发布校验 |
| `account.binding_required` | 账号缺少可用执行环境绑定 | 适用于账号发布校验 |
| `workspace.root_path_missing` | 工作区根目录不存在 | 适用于工作区环境校验与健康检查 |
| `workspace.root_path_invalid` | 工作区根路径不是目录 | 适用于工作区环境校验与健康检查 |
| `workspace.browser_instance_error` | 工作区下存在异常浏览器实例 | 适用于工作区环境校验与健康检查 |

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
| 提示词模板中心 | `/api/prompt-templates` | `runtime-client.ts`（`listPromptTemplates`、`createPromptTemplate`、`updatePromptTemplate`、`deletePromptTemplate`） |
| AI 与系统设置 | `/api/settings`、`/api/settings/ai-capabilities`、`/api/settings/ai-providers` | `config-bus.ts`、`ai-capability.ts`、`AISystemSettingsPage.vue` |
| 全局搜索 | `/api/search` | `searchGlobal` |
| 长任务状态 | `/api/tasks` | `task-bus.ts` |
| WebSocket | `/api/ws` | `task-bus.ts` WebSocket 订阅 |

## 1.5 文档-代码差异矩阵（V1）

- HTTP 文档路由数（提取）：181
- HTTP 代码路由数（去重）：181
- HTTP 文档与代码一致：181
- HTTP 代码未写入文档（需补充）：0
- HTTP 文档有但代码未见（需补齐）：0

### 接口状态表（2026-04-24）

| 状态 | 数量 | 说明 |
| --- | --- | --- |
| 已实现并已文档化 | 181 | 当前所有 HTTP 接口明细均已在 `apps/py-runtime` 与本文档对齐 |
| 已实现但未文档化 | 0 | 本轮已补齐 `bootstrap / dashboard / settings / devices / ai-providers` 新增运行时接口登记 |
| 文档已写但未实现 | 0 | 本轮已补齐 `/api/video-deconstruction` 文档要求的 7 个接口，并完成剩余接口登记 |
| 字段仍可继续细化 | 若干 | 主要是高级接口的错误码、更多响应示例和边界说明 |

### 本轮收口

- 已按文档补齐 `/api/video-deconstruction/videos/{video_id}/transcribe`
- 已按文档补齐 `/api/video-deconstruction/videos/{video_id}/transcript`
- 已按文档补齐 `/api/video-deconstruction/videos/{video_id}/segment`
- 已按文档补齐 `/api/video-deconstruction/videos/{video_id}/segments`
- 已按文档补齐 `/api/video-deconstruction/videos/{video_id}/extract-structure`
- 已按文档补齐 `/api/video-deconstruction/videos/{video_id}/structure`
- 已按文档补齐 `/api/video-deconstruction/extractions/{extraction_id}/apply-to-project`
- 已补登记 `/api/video-deconstruction/videos/{video_id}/stages`
- 已补登记 `/api/video-deconstruction/videos/{video_id}/stages/{stage_id}/rerun`
- 已补登记 `GET /api/bootstrap/readiness`
- 已补登记 `DELETE /api/dashboard/projects/{project_id}`
- 已补登记 `GET /api/settings/diagnostics/media`
- 已补登记 `/api/devices/workspaces/{ws_id}/browser-instances*`
- 已补登记 `GET /api/ai-providers/health`、`POST /api/ai-providers/health/refresh`、`PUT /api/ai-providers/{provider_id}/models/{model_id}`

### 仍待细化的高优先模块

- 脚本 / 分镜：可继续补充 `versions / restore / shots* / sync-from-script` 的失败路径示例。
- 工作台：可继续补充 `clip move/trim/replace`、`preview`、`precheck` 的更多返回示例。
- 配音 / 字幕 / 资产：可继续补充 `waveform / export / group batch` 的异常路径与响应样例。

### 字段层面结论

- `search / bootstrap / settings.health / prompt-templates / video-deconstruction` 当前已完成文档字段闭环。
- 其余高级接口主要缺更多异常样例、边界说明与前端类型收口，不再是路由条目未登记问题。

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
        "snippet": "Alpha Hook 第二行文本。",
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

---

## 2.1 首启运行时初始化

**核心返回 DTO**: `BootstrapDirectoryReportDto`、`RuntimeSelfCheckReportDto`、`BootstrapReadinessDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `POST /api/bootstrap/initialize-directories` | 无；按当前 settings/config 与 runtime data root 创建并校验目录 | `BootstrapDirectoryReportDto`：`rootDir`、`databasePath`、`status`、`directories[]`、`checkedAt` | `500` | `initializeDirectories` |
| `POST /api/bootstrap/runtime-selfcheck` | 无；执行端口、版本、依赖、数据库聚合自检 | `RuntimeSelfCheckReportDto`：`status`、`runtimeVersion`、`checkedAt`、`items[]` | `500`；端口项未监听时返回 `runtime.port-not-listening` | `runtimeSelfCheck` |
| `GET /api/bootstrap/readiness` | 无；聚合许可证、目录初始化、Runtime 自检、媒体依赖，返回首启可继续状态与阻断项 | `BootstrapReadinessDto`：`status`、`canContinue`、`items[]`、`blockers[]` | `500`；许可证未激活时返回阻断项并标记 `license.not_activated` | 当前前端未直接调用 |

**端口检查语义**

- 监听中返回 `ok`。
- 未监听返回 `warning`，`errorCode` 为 `runtime.port-not-listening`。

```json
{
  "ok": true,
  "data": {
    "status": "ok",
    "runtimeVersion": "0.3.4",
    "checkedAt": "2026-04-17T12:00:00Z",
    "items": [
      {
        "key": "port",
        "label": "端口检查",
        "status": "ok",
        "detail": "端口 8000 已处于监听状态",
        "errorCode": null,
        "checkedAt": "2026-04-17T12:00:00Z"
      }
    ]
  }
}
```

## 2. 许可证

**核心返回 DTO**: `LicenseStatusDto` / `LicenseActivateResultDto`
关键字段：`active`、`restrictedMode`、`machineCode`、`machineBound`、`licenseType`、`maskedCode`、`activatedAt`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/license/status` | 无 | `LicenseStatusDto` | `500` | `fetchLicenseStatus` |
| `POST /api/license/activate` | `LicenseActivateInput`：`activationCode` | `LicenseActivateResultDto` | `422`、`500`、`503` | `activateLicense` |

**当前差异**

- 缺少 `cryptography` 依赖时，`GET /api/license/status` 仍可用，但 `POST /api/license/activate` 会返回 `503`，错误信息为“许可证激活依赖未就绪，请检查运行时依赖与授权配置”。

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

**核心返回 DTO**: `DashboardSummaryDto`、`ProjectSummaryDto`、`CurrentProjectContextDto`、`DashboardTaskDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/dashboard/summary` | 无 | `DashboardSummaryDto`：`recentProjects[]`、`currentProject`、`recentTasks[]`、`pendingItems[]`、`riskSummary`、`currentAction`、`generatedAt` | `500` | `fetchDashboardSummary` |
| `POST /api/dashboard/projects` | `CreateProjectInput`：`name`、`description` | `ProjectSummaryDto` | `422`、`500` | `createDashboardProject` |
| `DELETE /api/dashboard/projects/{project_id}` | 路径参数：`project_id`；软删除项目，若被未完成任务占用则阻断 | `DeleteProjectResultDto`：`deleted`、`projectId`、`clearedCurrentProject`、`deletedAt` | `404`、`409`；阻断时返回 `project.delete_blocked` | `deleteDashboardProject` → `stores/project.ts:deleteProject` |
| `GET /api/dashboard/context` | 无 | `CurrentProjectContextDto \| null` | `500` | `fetchCurrentProjectContext` |
| `PUT /api/dashboard/context` | `SetCurrentProjectInput`：`projectId`，支持 `null` 清空当前项目 | `CurrentProjectContextDto \| null` | `404`、`422` | `updateCurrentProjectContext` |

**示例**

```json
{
  "ok": true,
  "data": {
    "recentProjects": [
      {
        "id": "project-1",
        "name": "TikTok 选题 A",
        "description": "创作总览演示项目",
        "status": "active",
        "currentScriptVersion": 1,
        "currentStoryboardVersion": 0,
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
    "recentTasks": [
      {
        "taskId": "task-1",
        "taskType": "video_import",
        "projectId": "project-1",
        "status": "running",
        "progress": 42,
        "message": "正在解析视频元数据",
        "createdAt": "2026-04-17T08:20:00Z",
        "updatedAt": "2026-04-17T08:25:00Z"
      }
    ],
    "pendingItems": [
      {
        "id": "task-task-1",
        "kind": "active_task",
        "title": "当前项目有正在处理的任务",
        "detail": "video_import 正处于 running，先处理当前任务再继续下一步。",
        "action": "open-task",
        "targetProjectId": "project-1",
        "targetTaskId": "task-1"
      }
    ],
    "riskSummary": {
      "total": 1,
      "blocking": 0,
      "items": [
        {
          "id": "delete-guard-task-1",
          "level": "warning",
          "title": "当前项目暂不支持删除",
          "detail": "项目仍有未完成任务，删除操作会被后端阻断。",
          "targetProjectId": "project-1",
          "targetTaskId": "task-1"
        }
      ]
    },
    "currentAction": {
      "label": "继续当前任务",
      "action": "open-task",
      "targetProjectId": "project-1",
      "targetTaskId": "task-1"
    },
    "generatedAt": "2026-04-17T08:30:00Z"
  }
}
```

---

## 4. 脚本与选题中心

**核心返回 DTO**: `ScriptDocumentDto`、`ScriptLastOperationDto`
关键字段：`projectId`、`currentVersion`、`versions[]`、`recentJobs[]`、`isSaved`、`latestRevision`、`saveSource`、`latestAiJob`、`lastOperation`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/scripts/projects/{project_id}/document` | 路径参数：`project_id` | `ScriptDocumentDto`：`currentVersion`、`versions[]`、`recentJobs[]`、`isSaved`、`latestRevision`、`saveSource`、`latestAiJob`、`lastOperation` | `404`、`500` | `fetchScriptDocument` |
| `GET /api/scripts/projects/{project_id}/versions` | 路径参数：`project_id` | `ScriptVersionDto[]` | `404` | 当前前端未直接调用 |
| `PUT /api/scripts/projects/{project_id}/document` | `ScriptSaveInput`：`content` | `ScriptDocumentDto`；保存结果通过 `isSaved/latestRevision/saveSource/lastOperation` 返回 | `404`、`422` | `saveScriptDocument` |
| `POST /api/scripts/projects/{project_id}/generate` | `ScriptGenerateInput`：`topic` | `ScriptDocumentDto`；生成作业状态通过 `latestAiJob/recentJobs[]/lastOperation` 返回 | `404`、`409`、`500` | `generateScriptDocument` |
| `POST /api/scripts/projects/{project_id}/title-variants` | `ScriptTitleVariantsInput`：`topic`、`count` | `ScriptTitleVariantDto[]` | `404`、`422`、`502` | `generateScriptTitleVariants` |
| `POST /api/scripts/projects/{project_id}/rewrite` | `ScriptRewriteInput`：`instructions` | `ScriptDocumentDto`；改写结果通过 `latestAiJob/recentJobs[]/lastOperation` 返回 | `400`、`404`、`409`、`500`；无脚本版本时返回中文阻断信息 | `rewriteScriptDocument` |
| `POST /api/scripts/projects/{project_id}/restore/{version_id}` | 路径参数：`project_id`、`version_id` | `ScriptDocumentDto` | `404` | `restoreScriptVersion` |
| `POST /api/scripts/projects/{project_id}/segments/{segment_id}/rewrite` | 路径参数：`project_id`、`segment_id`；`ScriptSegmentRewriteInput`：`instructions`、`promptTemplateId?` | `ScriptDocumentDto` | `400`、`404`、`422` | `rewriteScriptSegment` |

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
    "recentJobs": [],
    "isSaved": true,
    "latestRevision": 3,
    "saveSource": "video_extraction",
    "latestAiJob": {
      "id": "job-1",
      "capabilityId": "script_generation",
      "provider": "openai",
      "model": "gpt-5",
      "status": "succeeded",
      "error": null,
      "durationMs": 21,
      "createdAt": "2026-04-17T10:00:00Z",
      "completedAt": "2026-04-17T10:00:21Z"
    },
    "lastOperation": {
      "revision": 3,
      "source": "video_extraction",
      "createdAt": "2026-04-17T10:00:00Z",
      "aiJobId": null,
      "aiJobStatus": null
    }
  }
}
```

---

## 4.1 提示词模板中心

**核心返回 DTO**: `PromptTemplateDto`
关键字段：`id`、`kind`、`name`、`description`、`content`、`createdAt`、`updatedAt`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/prompt-templates` | 查询参数：`kind?` | `PromptTemplateDto[]` | `422`、`500` | `listPromptTemplates` |
| `POST /api/prompt-templates` | `PromptTemplateInput`：`kind`、`name`、`description`、`content` | `PromptTemplateDto` | `422`、`500` | `createPromptTemplate` |
| `PUT /api/prompt-templates/{template_id}` | 路径参数：`template_id`；`PromptTemplateUpdateInput`：`kind`、`name`、`description`、`content` | `PromptTemplateDto` | `404`、`422`、`500` | `updatePromptTemplate` |
| `DELETE /api/prompt-templates/{template_id}` | 路径参数：`template_id` | `{"deleted": true}` | `404` | `deletePromptTemplate` |

**当前差异**

- 已修复：前端 `runtime-client.ts` 使用 `PUT /api/prompt-templates/{template_id}`，输入字段与后端 `kind/name/description/content` 保持一致。

**示例**

```json
{
  "ok": true,
  "data": [
    {
      "id": "pt-1",
      "kind": "script_hook",
      "name": "开场钩子",
      "description": "用于短视频脚本开场",
      "content": "请输出 3 个高冲击开场句。",
      "createdAt": "2026-04-17T12:10:00Z",
      "updatedAt": "2026-04-17T12:10:00Z"
    }
  ]
}
```

---

## 5. 分镜规划中心

**核心返回 DTO**: `StoryboardDocumentDto`、`StoryboardConflictSummaryDto`、`StoryboardLastOperationDto`
关键字段：`projectId`、`basedOnScriptRevision`、`currentScriptRevision`、`currentVersion`、`versions[]`、`recentJobs[]`、`syncStatus`、`conflictSummary`、`latestAiJob`、`lastOperation`

**最小字段约束**

- `StoryboardDocumentDto` 外层固定返回：`projectId`、`basedOnScriptRevision`、`currentVersion`、`versions[]`、`recentJobs[]`
- `StoryboardVersionDto` 固定返回：`revision`、`basedOnScriptRevision`、`source`、`scenes[]`、`provider`、`model`、`aiJobId`、`createdAt`
- `StoryboardSceneDto` / `StoryboardShotDto` 固定返回：`sceneId`、`title`、`summary`、`visualPrompt`
- `StoryboardTemplateDto` 固定返回：`id`、`name`、`description`、`shots[]`
- `source` 当前已落地值包含：`manual`、`ai_generate`、`sync_from_script`、`shot_create`、`shot_update`、`shot_delete`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/storyboards/projects/{project_id}/document` | 路径参数：`project_id` | `StoryboardDocumentDto`：`basedOnScriptRevision`、`currentScriptRevision`、`syncStatus`、`conflictSummary`、`latestAiJob`、`lastOperation` | `404`、`500` | `fetchStoryboardDocument` |
| `GET /api/storyboards/templates` | 无 | `StoryboardTemplateDto[]` | `500` | `fetchStoryboardTemplates` |
| `PUT /api/storyboards/projects/{project_id}/document` | `StoryboardSaveInput`：`basedOnScriptRevision`、`scenes[]` | `StoryboardDocumentDto`；保存结果通过 `lastOperation` 返回 | `404`、`422` | `saveStoryboardDocument` |
| `POST /api/storyboards/projects/{project_id}/generate` | 路径参数：`project_id` | `StoryboardDocumentDto`；生成状态通过 `latestAiJob/recentJobs[]/lastOperation` 返回 | `400`、`404`、`409`、`500` | `generateStoryboardDocument` |
| `POST /api/storyboards/projects/{project_id}/sync-from-script` | 路径参数：`project_id` | `StoryboardDocumentDto`；同步结果通过 `syncStatus/conflictSummary/lastOperation` 返回 | `400`、`404` | `syncStoryboardFromScript` |
| `POST /api/storyboards/projects/{project_id}/shots` | 路径参数：`project_id`；`StoryboardShotInput`：`title`、`summary`、`visualPrompt` | `StoryboardDocumentDto` | `400`、`404`、`422` | `createStoryboardShot` |
| `PATCH /api/storyboards/projects/{project_id}/shots/{shot_id}` | 路径参数：`project_id`、`shot_id`；`StoryboardShotUpdateInput` | `StoryboardDocumentDto` | `404`、`422` | `updateStoryboardShot` |
| `DELETE /api/storyboards/projects/{project_id}/shots/{shot_id}` | 路径参数：`project_id`、`shot_id` | `StoryboardDocumentDto` | `404` | `deleteStoryboardShot` |

**示例**

```json
{
  "ok": true,
  "data": {
    "projectId": "project-1",
    "basedOnScriptRevision": 3,
    "currentScriptRevision": 4,
    "currentVersion": {
      "revision": 1,
      "basedOnScriptRevision": 3,
      "source": "sync_from_script",
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
    "recentJobs": [],
    "syncStatus": "outdated",
    "conflictSummary": {
      "hasConflict": true,
      "reason": "当前分镜基于旧脚本版本，建议先重新同步再继续编辑。",
      "currentScriptRevision": 4,
      "basedOnScriptRevision": 3,
      "storyboardRevision": 1
    },
    "latestAiJob": {
      "id": "job-2",
      "capabilityId": "storyboard_generation",
      "provider": "openai",
      "model": "gpt-5-mini",
      "status": "succeeded",
      "error": null,
      "durationMs": 18,
      "createdAt": "2026-04-17T10:05:00Z",
      "completedAt": "2026-04-17T10:05:18Z"
    },
    "lastOperation": {
      "revision": 1,
      "source": "manual",
      "createdAt": "2026-04-17T10:05:00Z",
      "aiJobId": null,
      "aiJobStatus": null
    }
  }
}
```

**模板示例**

```json
{
  "ok": true,
  "data": [
    {
      "id": "hook-problem-solution",
      "name": "钩子-问题-解决",
      "description": "适合短视频创作的基础三段式分镜模板。",
      "shots": [
        {
          "sceneId": "shot-1",
          "title": "开场钩子",
          "summary": "快速抛出冲突或吸引点。",
          "visualPrompt": "强节奏开场，镜头推进。"
        }
      ]
    }
  ]
}
```

---

## 6. AI 剪辑工作台

**核心返回 DTO**: `WorkspaceTimelineResultDto`、`TimelineDto`、`WorkspaceAICommandResultDto`

- `TimelineDto` 新增：
  - `version`：`versionToken`、`updatedAt`、`trackCount`、`clipCount`
  - `assetReferenceStatus`：`totalClips`、`readyClips`、`processingClips`、`failedClips`、`missingReferenceClips`、`manualClips`、`referencedClips`
- `WorkspaceTimelineResultDto` 新增：
  - `activeTask`：当前时间线的活跃任务快照；当前无活跃任务时返回 `null`
  - `saveState`：`saved`、`updatedAt`、`source`、`message`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/workspace/projects/{project_id}/timeline` | 路径参数：`project_id` | `WorkspaceTimelineResultDto`：`timeline`、`activeTask?`、`saveState?`、`message` | `404`、`500` | `fetchWorkspaceTimeline` |
| `POST /api/workspace/projects/{project_id}/timeline` | `TimelineCreateInput`：`name` | `WorkspaceTimelineResultDto`：`timeline`、`activeTask?`、`saveState`、`message` | `404`、`422` | `createWorkspaceTimeline` |
| `PATCH /api/workspace/timelines/{timeline_id}` | `TimelineUpdateInput`：`name?`、`durationSeconds?`、`tracks[]` | `WorkspaceTimelineResultDto`：`timeline`、`activeTask?`、`saveState`、`message` | `404`、`422` | `updateWorkspaceTimeline` |
| `GET /api/workspace/clips/{clip_id}` | 路径参数：`clip_id` | `WorkspaceClipDetailDto` | `404` | `fetchWorkspaceClip` |
| `POST /api/workspace/clips/{clip_id}/move` | 路径参数：`clip_id`；`ClipMoveInput`：`targetTrackId`、`startMs` | `WorkspaceTimelineResultDto`：`timeline`、`activeTask?`、`saveState`、`message` | `404`、`422` | `moveWorkspaceClip` |
| `POST /api/workspace/clips/{clip_id}/trim` | 路径参数：`clip_id`；`ClipTrimInput`：`startMs?`、`durationMs?`、`inPointMs?`、`outPointMs?` | `WorkspaceTimelineResultDto`：`timeline`、`activeTask?`、`saveState`、`message` | `404`、`422` | `trimWorkspaceClip` |
| `POST /api/workspace/clips/{clip_id}/replace` | 路径参数：`clip_id`；`ClipReplaceInput`：`sourceType`、`sourceId?`、`label`、`prompt?`、`resolution?`、`editableFields[]` | `WorkspaceTimelineResultDto`：`timeline`、`activeTask?`、`saveState`、`message` | `404`、`422` | `replaceWorkspaceClip` |
| `GET /api/workspace/timelines/{timeline_id}/preview` | 路径参数：`timeline_id` | `TimelinePreviewDto`：`status=ready`，`previewUrl` 为本地 `data:application/json` manifest | `404`、`500` | `fetchTimelinePreview` |
| `POST /api/workspace/timelines/{timeline_id}/precheck` | 路径参数：`timeline_id` | `TimelinePrecheckDto`：`status=ready/warning`、`issues[]` | `404`、`500` | `precheckTimeline` |
| `POST /api/workspace/projects/{project_id}/ai-commands` | `WorkspaceAICommandInput`：`timelineId?`、`capabilityId`、`parameters` | `WorkspaceAICommandResultDto`；当前最小实现返回 `status=queued` 并创建真实 TaskBus 任务 | `404`、`422` | `runWorkspaceAICommand` |

**当前实现说明**

- `GET /preview` 不伪造渲染画面，返回基于真实轨道、片段与时长统计生成的本地 manifest。
- `POST /precheck` 校验轨道类型、片段时长、起始时间与片段数据格式；空轨道会返回可见问题列表。
- `TimelineDto.version` 不伪造整数版号，使用真实 `timeline.id + updatedAt + trackCount + clipCount` 生成 `versionToken` 作为当前时间线版本信号。
- `TimelineDto.assetReferenceStatus` 基于真实片段 `sourceType/sourceId/status` 聚合，不编造素材可用性。
- `WorkspaceTimelineResultDto.activeTask` 只返回当前 Runtime 进程内、且 `ownerRef` 绑定到该时间线的活跃任务，优先 `ai-workspace-command`。
- `WorkspaceTimelineResultDto.saveState.source` 当前取值：`load`、`create`、`save`、`clip_move`、`clip_trim`、`clip_replace`。

**示例**

```json
{
  "ok": true,
  "data": {
    "timeline": {
      "id": "timeline-1",
      "projectId": "project-1",
      "version": {
        "versionToken": "timeline-1:2026-04-21T10:00:00Z:2:3",
        "updatedAt": "2026-04-21T10:00:00Z",
        "trackCount": 2,
        "clipCount": 3
      },
      "assetReferenceStatus": {
        "totalClips": 3,
        "readyClips": 2,
        "processingClips": 1,
        "failedClips": 0,
        "missingReferenceClips": 0,
        "manualClips": 1,
        "referencedClips": 2
      }
    },
    "activeTask": null,
    "saveState": {
      "saved": true,
      "updatedAt": "2026-04-21T10:00:00Z",
      "source": "save",
      "message": "已确认保存时间线草稿。"
    },
    "message": "已保存时间线草稿。"
  }
}
```

---

## 7. M06 视频拆解中心

**核心返回 DTO**: `ImportedVideoDto`、`VideoStageDto`、`VideoTranscriptDto`、`VideoSegmentDto`、`VideoStructureExtractionDto`、`ApplyVideoExtractionResultDto`

**当前契约要点**

- `GET /api/video-deconstruction/videos/{video_id}/stages` 返回完整阶段编排状态，覆盖：
  - `import`
  - `transcribe`
  - `segment`
  - `extract_structure`
- `VideoStageDto` 当前用于表达阶段状态与长任务上下文，关键字段包括：
  - `stageId`
  - `label`
  - `status`
  - `progressPct`
  - `resultSummary`
  - `errorMessage`
  - `errorCode`
  - `nextAction`
  - `blockedByStageId`
  - `updatedAt`
  - `isCurrent`
  - `activeTaskId`
  - `activeTaskStatus`
  - `activeTaskProgress`
  - `activeTaskMessage`
  - `canCancel`
  - `canRetry`
  - `canRerun`
- 阶段长任务状态统一通过 HTTP 返回，不要求页面自行拼装；若存在 `activeTaskId`，前端可继续通过 `POST /api/tasks/{task_id}/cancel` 或 `GET /api/tasks` 协同控制
- `POST /api/video-deconstruction/projects/{project_id}/import` 只返回初始 `ImportedVideoDto`；真正的视频元数据解析在后台导入任务中完成，导入阶段状态应以 `GET /stages` 和视频状态为准
- 当前视频拆解链路会广播：
  - `video.import.stage.started`
  - `video.import.stage.completed`
  - `video.import.stage.failed`
  - `video_status_changed`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `POST /api/video-deconstruction/projects/{project_id}/import` | `ImportVideoInput`：`filePath` | `ImportedVideoDto` | `400`、`409` | `importVideo` |
| `GET /api/video-deconstruction/projects/{project_id}/videos` | 路径参数：`project_id` | `ImportedVideoDto[]` | `500` | `fetchImportedVideos` |
| `DELETE /api/video-deconstruction/videos/{video_id}` | 路径参数：`video_id` | `null` | `404` | `deleteImportedVideo` |
| `POST /api/video-deconstruction/videos/{video_id}/transcribe` | 无 | `VideoTranscriptDto`；未接入 Provider 时返回 `status=provider_required` 且 `text=null` | `404`、`500` | `startVideoTranscription` |
| `GET /api/video-deconstruction/videos/{video_id}/transcript` | 路径参数：`video_id` | `VideoTranscriptDto` | `404`、`500` | `fetchVideoTranscript` |
| `POST /api/video-deconstruction/videos/{video_id}/segment` | 无 | `VideoSegmentDto[]` | `404`、`409 task.conflict`、`500` | `runVideoSegmentation` |
| `GET /api/video-deconstruction/videos/{video_id}/segments` | 路径参数：`video_id` | `VideoSegmentDto[]` | `404` | `fetchVideoSegments` |
| `POST /api/video-deconstruction/videos/{video_id}/extract-structure` | 无 | `VideoStructureExtractionDto`；要求分段阶段已成功 | `404`、`409 task.conflict`、`500` | `extractVideoStructure` |
| `GET /api/video-deconstruction/videos/{video_id}/structure` | 路径参数：`video_id` | `VideoStructureExtractionDto` | `404` | `fetchVideoStructure` |
| `POST /api/video-deconstruction/extractions/{extraction_id}/apply-to-project` | 无 | `ApplyVideoExtractionResultDto`：`projectId`、`extractionId`、`scriptRevision`、`status`、`message` | `404`、`409 task.conflict`、`500` | `applyVideoExtractionToProject` |
| `GET /api/video-deconstruction/videos/{video_id}/stages` | 路径参数：`video_id` | `VideoStageDto[]`；返回 `import / transcribe / segment / extract_structure` 全链路状态、阻塞关系和活动任务摘要 | `404` | `fetchVideoStages` |
| `POST /api/video-deconstruction/videos/{video_id}/stages/{stage_id}/rerun` | 路径参数：`stage_id` 仅支持 `transcribe / segment / extract_structure` | `TaskInfo`：`id`、`taskType`、`projectId`、`status`、`progress`、`message`、`createdAt`、`updatedAt` | `400`、`404`、`409` | `rerunVideoStage` |

**当前错误语义**

- `POST /transcribe` 当前不会真实调用转录 Provider；若未接入 Provider，会返回 `status=provider_required`
- `POST /segment` 在转录未成功时返回 `409`，并把 `segment` 阶段写成 `blocked`，同时给出 `errorCode=task.conflict`、`blockedByStageId=transcribe`
- `POST /extract-structure` 在分段未成功时返回 `409`，并把 `extract_structure` 阶段写成 `blocked`，同时给出 `errorCode=task.conflict`、`blockedByStageId=segment`
- `POST /apply-to-project` 要求 `extract_structure.status=succeeded`，否则返回 `409`
- `POST /stages/{stage_id}/rerun` 会复用阶段阻塞语义；其中 `transcribe` 重跑在未接入 Provider 时仍会回到 `provider_required`
- 导入阶段如果 FFprobe 不可用，会写入 `status=failed_degraded`，并通过 WebSocket 广播 `video.import.stage.failed`、`errorCode=media.ffprobe_unavailable`、`nextAction=请先修复 FFprobe 或媒体诊断配置后，再重新导入视频。`

**当前状态语义**

- 当前阶段由 `isCurrent=true` 标记；优先级以活动任务为先，其次是首个未成功阶段，因此它可能出现在 `running / queued / provider_required / blocked / failed / failed_degraded`
- 典型状态包括：
  - `import.status=failed_degraded`：导入记录仍存在，但 FFprobe 不可用，元数据解析降级失败
  - `transcribe.status=provider_required`：当前未接入可用转录 Provider
  - `segment.status=blocked`：转录未成功，分段被前置阶段阻塞
  - `extract_structure.status=blocked`：分段未成功，结构提取被前置阶段阻塞

**当前差异**

- `apps/desktop/src/types/video.ts` 中的 `ImportedVideoStatus` 仍只声明 `imported | ready`，但后端当前还会返回 `failed_degraded` 与 `error`

**示例**

```json
{
  "ok": true,
  "data": [
    {
      "stageId": "import",
      "label": "导入",
      "status": "failed_degraded",
      "progressPct": 80,
      "resultSummary": "FFprobe 不可用，导入解析失败，暂缺时长与分辨率等元数据。",
      "errorMessage": "FFprobe 不可用，视频元数据解析已降级失败，请先修复媒体诊断后重试。",
      "errorCode": "media.ffprobe_unavailable",
      "nextAction": "请先修复 FFprobe 或媒体诊断配置后，再重新导入视频。",
      "blockedByStageId": null,
      "updatedAt": "2026-04-21T10:10:00Z",
      "isCurrent": true,
      "activeTaskId": null,
      "activeTaskStatus": null,
      "activeTaskProgress": null,
      "activeTaskMessage": null,
      "canCancel": false,
      "canRetry": false,
      "canRerun": false
    },
    {
      "stageId": "segment",
      "label": "分段",
      "status": "blocked",
      "progressPct": 0,
      "resultSummary": "视频转录尚未成功，分段已阻塞；请先完成转录后重试。",
      "errorMessage": "视频转录尚未成功，分段已阻塞；请先完成转录后重试。",
      "errorCode": "task.conflict",
      "nextAction": "请先完成转录阶段后重试。",
      "blockedByStageId": "transcribe",
      "updatedAt": "2026-04-21T10:12:00Z",
      "isCurrent": false,
      "activeTaskId": null,
      "activeTaskStatus": null,
      "activeTaskProgress": null,
      "activeTaskMessage": null,
      "canCancel": false,
      "canRetry": true,
      "canRerun": true
    }
  ]
}
```

```json
{
  "ok": false,
  "error": "视频转录尚未成功，分段已阻塞；请先完成转录后重试。",
  "error_code": "task.conflict"
}
```

---
## 8. 配音中心

**核心返回 DTO**: `VoiceProfileDto`、`VoiceTrackDto`、`VoiceTrackGenerateResultDto`、`VoiceTrackRegenerateResultDto`

**当前契约重点**

- `VoiceTrackDto` 返回真实轨道快照：`id`、`projectId`、`timelineId`、`source`、`provider`、`voiceName`、`filePath`、`segments[]`、`status`、`version`、`config`、`preview`、`activeTask`、`createdAt`、`updatedAt`
- `version` 是对象：`revision`、`updatedAt`，用于前端判断配音版本与最近落库时间
- `config` 返回参数来源和最近一次操作：`parameterSource`、`profileId`、`provider`、`voiceId`、`voiceName`、`locale`、`model`、`speed`、`pitch`、`emotion`、`sourceText`、`sourceLineCount`、`lastOperation`
- `preview` 返回试听资源状态：`status`、`resourceId`、`filePath`、`message`
- `activeTask` 返回当前活跃的 `ai-voice` 任务，无任务时为 `null`
- `VoiceTrackGenerateResultDto` 和 `VoiceTrackRegenerateResultDto` 统一返回 `track`、`task`、`message`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/voice/profiles` | 无 | `VoiceProfileDto[]` | `500` | `fetchVoiceProfiles` |
| `POST /api/voice/profiles` | `VoiceProfileCreateInput`：`provider`、`voiceId`、`displayName`、`locale`、`tags[]`、`enabled` | `VoiceProfileDto` | `422`、`500`、`503` | `createVoiceProfile` |
| `GET /api/voice/projects/{project_id}/tracks` | 路径参数 `project_id` | `VoiceTrackDto[]` | `404` | `fetchVoiceTracks` |
| `POST /api/voice/projects/{project_id}/tracks/generate` | `VoiceTrackGenerateInput`：`profileId`、`sourceText`、`speed`、`pitch`、`emotion` | `VoiceTrackGenerateResultDto` | `404`、`422`、`500` | `generateVoiceTrack` |
| `POST /api/voice/tracks/{track_id}/segments/{segment_id}/regenerate` | 路径参数 `track_id`、`segment_id`；`VoiceSegmentRegenerateInput`：可选 `profileId`、`speed`、`pitch`、`emotion` | `VoiceTrackRegenerateResultDto` | `404`、`422`、`500` | `regenerateVoiceSegment` |
| `GET /api/voice/tracks/{track_id}/waveform` | 路径参数 `track_id` | `VoiceWaveformDto` | `404`、`500` | `fetchVoiceWaveform` |
| `GET /api/voice/tracks/{track_id}` | 路径参数 `track_id` | `VoiceTrackDto` | `404` | `fetchVoiceTrack` |
| `DELETE /api/voice/tracks/{track_id}` | 路径参数 `track_id` | `null` | `404` | `deleteVoiceTrack` |

**当前实现说明**

- `POST /api/voice/projects/{project_id}/tracks/generate` 会走真实 Provider 能力判断。无可用 TTS 配置时，返回 `track.status="blocked"` 和 `task=null`，同时保留草稿轨道。
- 存在可用 TTS Runtime 时，返回 `track.status="processing"`，创建 `kind="ai-voice"` 任务，任务成功后写入真实音频文件并切换到 `ready`，失败时切到 `failed`。
- `POST /api/voice/tracks/{track_id}/segments/{segment_id}/regenerate` 会更新真实 `segments[].regeneration`。无 Provider 时返回 `blocked` 且 `retryable=true`；有 Provider 时返回真实任务状态，成功后更新片段音频资源和配音版本。
- `GET /api/voice/tracks/{track_id}/waveform` 只基于本地真实音频文件生成波形摘要，缺少音频文件时明确返回 `missing_audio`。
- `config.parameterSource` 当前可能为 `seed`、`profile`、`manual`、`runtime`，分别表示旧数据种子、按音色生成、手动片段重生和运行时回填。

**示例**

blocked：
```json
{
  "ok": true,
  "data": {
    "track": {
      "id": "voice-1",
      "projectId": "project-1",
      "timelineId": null,
      "source": "tts",
      "provider": "openai",
      "voiceName": "标准女声",
      "filePath": null,
      "segments": [],
      "status": "blocked",
      "version": {
        "revision": 1,
        "updatedAt": "2026-04-21T10:15:00Z"
      },
      "config": {
        "parameterSource": "profile",
        "voiceId": "alloy",
        "voiceName": "标准女声",
        "speed": 1.0,
        "pitch": 0,
        "emotion": "calm"
      },
      "preview": {
        "status": "blocked",
        "resourceId": null,
        "filePath": null,
        "message": "当前未配置可用 TTS Provider，已保留配音轨草稿。"
      },
      "activeTask": null,
      "createdAt": "2026-04-21T10:15:00Z",
      "updatedAt": "2026-04-21T10:15:00Z"
    },
    "task": null,
    "message": "当前未配置可用 TTS Provider，已保留配音轨草稿。"
  }
}
```

processing：
```json
{
  "ok": true,
  "data": {
    "track": {
      "id": "voice-2",
      "projectId": "project-1",
      "timelineId": null,
      "source": "tts",
      "provider": "openai",
      "voiceName": "标准女声",
      "filePath": null,
      "segments": [],
      "status": "processing",
      "version": {
        "revision": 2,
        "updatedAt": "2026-04-21T10:18:00Z"
      },
      "config": {
        "parameterSource": "profile",
        "voiceId": "alloy",
        "voiceName": "标准女声",
        "speed": 1.0,
        "pitch": 0,
        "emotion": "calm"
      },
      "preview": {
        "status": "processing",
        "resourceId": null,
        "filePath": null,
        "message": "配音生成任务已提交。"
      },
      "activeTask": {
        "id": "task-voice-1",
        "kind": "ai-voice",
        "taskType": "ai-voice",
        "projectId": "project-1",
        "ownerRef": {
          "kind": "voice-track",
          "id": "voice-2"
        },
        "status": "queued",
        "progress": 0,
        "label": "配音生成：标准女声",
        "message": "配音生成任务已提交。",
        "createdAt": "2026-04-21T10:18:00Z",
        "updatedAt": "2026-04-21T10:18:00Z"
      },
      "createdAt": "2026-04-21T10:18:00Z",
      "updatedAt": "2026-04-21T10:18:00Z"
    },
    "task": {
      "id": "task-voice-1",
      "kind": "ai-voice",
      "taskType": "ai-voice",
      "projectId": "project-1",
      "ownerRef": {
        "kind": "voice-track",
        "id": "voice-2"
      },
      "status": "queued",
      "progress": 0,
      "label": "配音生成：标准女声",
      "message": "配音生成任务已提交。",
      "createdAt": "2026-04-21T10:18:00Z",
      "updatedAt": "2026-04-21T10:18:00Z"
    },
    "message": "配音生成任务已提交。"
  }
}
```

waveform 缺少音频：
```json
{
  "ok": true,
  "data": {
    "status": "missing_audio",
    "message": "未找到音频文件，无法生成波形摘要。",
    "durationMs": null,
    "sampleRate": null,
    "channels": null,
    "points": []
  }
}
```

## 9. M08 字幕对齐中心

**核心返回 DTO**: `SubtitleTrackDto`、`SubtitleTrackGenerateResultDto`、`SubtitleStyleTemplateDto`、`SubtitleExportDto`

**当前契约要点**

- `SubtitleTrackDto` 当前会附带 `sourceVoice`、`alignment` 和 `updatedAt`，用于表达字幕与配音轨的绑定关系、对齐状态以及最近更新时间
- `sourceVoice` 当前包含：
  - `trackId`
  - `revision`
  - `updatedAt`
- `alignment` 当前包含：
  - `status`
  - `diffSummary`
  - `errorCode`
  - `errorMessage`
  - `nextAction`
  - `updatedAt`
- `diffSummary` 当前包含：
  - `segmentCountChanged`
  - `timingChangedSegments`
  - `textChangedSegments`
  - `lockedSegments`
- `SubtitleTrackGenerateInput` 当前支持 `sourceVoiceTrackId`，用于在生成阶段直接挂接来源音轨

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/subtitles/projects/{project_id}/tracks` | 路径参数：`project_id` | `SubtitleTrackDto[]` | `500` | `fetchSubtitleTracks` |
| `POST /api/subtitles/projects/{project_id}/tracks/generate` | `SubtitleTrackGenerateInput`：`sourceText`、`language`、`stylePreset`、`sourceVoiceTrackId?` | `SubtitleTrackGenerateResultDto`：`track`、`task`、`message` | `400`、`404`、`500` | `generateSubtitleTrack` |
| `GET /api/subtitles/style-templates` | 无 | `SubtitleStyleTemplateDto[]` | `500` | `listSubtitleStyleTemplates` |
| `POST /api/subtitles/tracks/{track_id}/align` | 路径参数：`track_id`；`SubtitleTrackAlignInput`：`segments[]` | `SubtitleTrackDto` | `400`、`404`、`422`、`500` | `alignSubtitleTrack` |
| `POST /api/subtitles/tracks/{track_id}/export` | 路径参数：`track_id`；`SubtitleExportInput`：`format` | `SubtitleExportDto` | `400`、`404`、`422` | `exportSubtitleTrack` |
| `GET /api/subtitles/tracks/{track_id}` | 路径参数：`track_id` | `SubtitleTrackDto` | `404`、`500` | `fetchSubtitleTrack` |
| `PATCH /api/subtitles/tracks/{track_id}` | `SubtitleTrackUpdateInput`：`segments[]`、`style` | `SubtitleTrackDto` | `404`、`422`、`500` | `updateSubtitleTrack` |
| `DELETE /api/subtitles/tracks/{track_id}` | 路径参数：`track_id` | `null` | `404`、`500` | `deleteSubtitleTrack` |

**当前错误语义**

- `POST /generate` 当前是 deterministic local 规则生成，不依赖 AI Provider
- 若未传 `sourceVoiceTrackId`，生成结果会写成 `alignment.status="draft"`，提示先绑定来源音轨
- 若传入 `sourceVoiceTrackId` 且音轨存在，会回填 `sourceVoice`，并将 `alignment.status` 置为 `pending_alignment`
- `POST /align` 要求所有 segments 都具备有效时间码；成功后会生成 `diffSummary`，并将 `alignment.status` 置为 `aligned`
- `PATCH /tracks/{track_id}` 会重新计算 `diffSummary`；若片段缺少完整时间码，会把 `alignment.status` 置为 `needs_alignment`，并返回 `errorCode=subtitle.timecode_incomplete`
- `POST /export` 返回的是内联导出结果：`fileName`、`content`、`lineCount`、`status`、`message`，不是文件路径

**当前差异**

- 已修复：`apps/desktop/src/types/runtime.ts` 中的 `SubtitleTrackDto` 已补齐 `updatedAt / sourceVoice / alignment`
- 已修复：`SubtitleTrackGenerateInput` 已声明 `sourceVoiceTrackId`
- 已修复：`SubtitleStyleTemplateDto` 已补齐 `description / style`
- 已修复：`SubtitleExportDto` 已切换为后端当前返回的 `fileName / content / lineCount / status / message` 内联导出口径

**示例**

生成结果：
```json
{
  "ok": true,
  "data": {
    "track": {
      "id": "subtitle-2",
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
          "text": "欢迎来到今天的视频。",
          "startMs": 0,
          "endMs": 1260,
          "confidence": null,
          "locked": false
        }
      ],
      "sourceVoice": {
        "trackId": "voice-track-1",
        "revision": 3,
        "updatedAt": "2026-04-21T10:08:00Z"
      },
      "alignment": {
        "status": "pending_alignment",
        "diffSummary": null,
        "errorCode": null,
        "errorMessage": null,
        "nextAction": "运行字幕对齐，确认字幕时间码与音轨保持一致。",
        "updatedAt": "2026-04-21T10:18:00Z"
      },
      "status": "ready",
      "createdAt": "2026-04-21T10:18:00Z",
      "updatedAt": "2026-04-21T10:18:00Z"
    },
    "task": {
      "kind": "local-subtitle-generate",
      "mode": "deterministic-local",
      "language": "zh-CN",
      "stylePreset": "creator-default",
      "segmentCount": 1,
      "sourceCharacters": 11,
      "generatedAt": "2026-04-21T10:18:00Z",
      "sourceVoiceTrackId": "voice-track-1"
    },
    "message": "字幕轨道已基于本地文本规则生成。"
  }
}
```

对齐结果：
```json
{
  "ok": true,
  "data": {
    "id": "subtitle-2",
    "projectId": "project-1",
    "alignment": {
      "status": "aligned",
      "diffSummary": {
        "segmentCountChanged": false,
        "timingChangedSegments": 2,
        "textChangedSegments": 1,
        "lockedSegments": 1
      },
      "errorCode": null,
      "errorMessage": null,
      "nextAction": "可继续导出字幕，或回到字幕编辑中微调文案。",
      "updatedAt": "2026-04-21T10:22:00Z"
    },
    "updatedAt": "2026-04-21T10:22:00Z"
  }
}
```

---

## 10. 资产中心

**核心返回 DTO**: `AssetDto`、`AssetReferenceDto`

**当前契约要点**

- `AssetDto` 现在除了基础字段，还会返回 4 组运行时摘要：
  - `sourceInfo`：来源与归属
  - `availability`：文件可用性与下一步动作
  - `referenceSummary`：引用关系与删除阻断状态
  - `thumbnailStatus`：缩略图生成状态
- `sourceInfo` 关键字段：`source`、`projectId`、`groupId`、`filePath`、`metadataSummary`
- `availability` 关键字段：`status`、`errorCode`、`errorMessage`、`nextAction`
- `referenceSummary` 关键字段：`total`、`referenceTypes[]`、`blockingDelete`
- `thumbnailStatus` 关键字段：`status`、`path`、`generatedAt`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/assets` | 查询参数：`type?`、`source?`、`project_id?`、`q?` | `AssetDto[]` | `500` | `fetchAssets` |
| `GET /api/assets/groups` | 无 | `AssetGroupDto[]` | `500` | 当前前端未直接调用 |
| `POST /api/assets/groups` | `AssetGroupCreateInput`：`name`、`parentId?` | `AssetGroupDto` | `422`、`500` | 当前前端未直接调用 |
| `PATCH /api/assets/groups/{group_id}` | 路径参数：`group_id`；`AssetGroupUpdateInput`：`name?`、`parentId?` | `AssetGroupDto` | `400`、`404`、`422`、`500` | 当前前端未直接调用 |
| `DELETE /api/assets/groups/{group_id}` | 路径参数：`group_id` | `{"deleted": true}` | `404`、`500` | 当前前端未直接调用 |
| `POST /api/assets` | `AssetCreateInput`：`name`、`type`、`source`、`filePath?`、`projectId?` 等 | `AssetDto` | `400`、`422`、`500` | 当前前端未直接调用 |
| `POST /api/assets/import` | `AssetImportInput`：`filePath`、`type`、`source`、`projectId?` 等 | `AssetDto` | `400`、`422`、`500` | `importAsset` |
| `POST /api/assets/batch-delete` | `BatchDeleteAssetsInput`：`assetIds[]` | `{"deletedCount": number}` | `422`、`500` | 当前前端未直接调用 |
| `POST /api/assets/batch-move-group` | `BatchMoveGroupInput`：`assetIds[]`、`groupId?` | `{"movedCount": number, "groupId": string \| null}` | `404`、`422`、`500` | 当前前端未直接调用 |
| `GET /api/assets/{asset_id}` | 路径参数：`asset_id` | `AssetDto` | `404` | `fetchAsset` |
| `PATCH /api/assets/{asset_id}` | `AssetUpdateInput`：`name?`、`tags?`、`metadataJson?` | `AssetDto` | `400`、`404`、`422`、`500` | `updateAsset` |
| `DELETE /api/assets/{asset_id}` | 路径参数：`asset_id` | 删除结果对象 | `404`、`409`、`500` | `deleteAsset` |
| `GET /api/assets/{asset_id}/references` | 路径参数：`asset_id` | `AssetReferenceDto[]` | `404` | `fetchAssetReferences` |
| `POST /api/assets/{asset_id}/references` | `AssetReferenceCreateInput`：`referenceType`、`referenceId` | `AssetReferenceDto` | `404`、`422` | 当前前端未直接调用 |
| `GET /api/assets/references/{ref_id}` | 路径参数：`ref_id` | `AssetReferenceDto` | `404` | 当前前端未直接调用 |
| `DELETE /api/assets/references/{ref_id}` | 路径参数：`ref_id` | 删除结果对象 | `404` | 当前前端未直接调用 |

**状态语义**

- `sourceInfo` 会把 `source / projectId / groupId / filePath / metadataJson` 中可稳定消费的信息整理为结构化摘要。
- `availability.status` 用来表达资产当前是否可继续使用：
  - `missing_source`：没有文件路径
  - `missing_file`：有路径但本地文件不存在
  - `ready`：源文件存在且可访问
- `referenceSummary` 会汇总引用数量和引用类型；当 `blockingDelete=true` 时，删除接口会被阻断。
- `thumbnailStatus.status` 用于表达缩略图链路状态：
  - `none`：当前没有缩略图，也没有进行中的缩略图任务
  - `queued` / `running`：存在进行中的缩略图任务
  - `ready`：缩略图文件已生成
  - `failed`：记录存在但缩略图文件缺失
  - `missing_source`：源文件不可用，因此无法生成缩略图

**示例**

导入成功：
```json
{
  "ok": true,
  "data": {
    "id": "asset-1",
    "name": "opening.mp4",
    "type": "video",
    "source": "local",
    "filePath": "C:/workspace/assets/opening.mp4",
    "fileSizeBytes": 204800,
    "durationMs": null,
    "thumbnailPath": null,
    "tags": "[\"开场\"]",
    "projectId": "project-1",
    "metadataJson": "{\"width\":1080,\"height\":1920}",
    "sourceInfo": {
      "source": "local",
      "projectId": "project-1",
      "groupId": null,
      "filePath": "C:/workspace/assets/opening.mp4",
      "metadataSummary": {
        "width": 1080,
        "height": 1920
      }
    },
    "availability": {
      "status": "ready",
      "errorCode": null,
      "errorMessage": null,
      "nextAction": null
    },
    "referenceSummary": {
      "total": 0,
      "referenceTypes": [],
      "blockingDelete": false
    },
    "thumbnailStatus": {
      "status": "none",
      "path": null,
      "generatedAt": null
    },
    "createdAt": "2026-04-21T10:20:00Z",
    "updatedAt": "2026-04-21T10:20:00Z"
  }
}
```

删除阻断：
- 当 `referenceSummary.total > 0` 且 `blockingDelete=true` 时，`DELETE /api/assets/{asset_id}` 会返回 `409`。
- UI 应优先引导用户查看引用详情，再决定解除引用或更换素材。

---

## 11. M10 账号管理

**核心返回 DTO**: `AccountDto`、`AccountGroupDto`、`AccountRefreshStatsDto`、`AccountBindingDto`、`AccountPublishReadinessDto`

**当前契约要点**

- `AccountDto` 现在会附带 `publishReadiness`，用于直接表达账号是否可发布。
- `publishReadiness` 关键字段：
  - `canPublish`
  - `status`
  - `lastValidatedAt`
  - `errorCode`
  - `errorMessage`
  - `suggestedAction`
  - `binding`
- 发布校验基于真实已存数据，不再只返回笼统状态：
  - `account.status`
  - `username`
  - `authExpiresAt`
  - `execution binding` 是否存在且为 `active`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/accounts` | 查询参数：`status?`、`platform?`、`group_id?`、`q?` | `AccountDto[]`；每项包含 `publishReadiness` | `500` | `fetchAccounts` |
| `POST /api/accounts` | `AccountCreateInput`：`name`、`platform`、`username?`、`status?` 等 | `AccountDto` | `422` | `createAccount` |
| `GET /api/accounts/{account_id}` | 路径参数：`account_id` | `AccountDto`；包含 `publishReadiness` | `404` | 当前前端未直接调用 |
| `PATCH /api/accounts/{account_id}` | `AccountUpdateInput` | `AccountDto`；包含最新 `publishReadiness` | `404`、`422` | 当前前端未直接调用 |
| `DELETE /api/accounts/{account_id}` | 路径参数：`account_id` | 删除结果对象 | `404` | `deleteAccount` |
| `POST /api/accounts/{account_id}/refresh-stats` | 路径参数：`account_id`；执行一次真实账号发布校验并更新时间戳 | `AccountRefreshStatsDto`：`id`、`status`、`updatedAt`、`providerStatus`、`publishReadiness` | `404` | `refreshAccountStats` |
| `PUT /api/accounts/{account_id}/binding` | `AccountBindingUpsertInput`：`browserInstanceId`、`status?`、`source?`、`metadataJson?` | `AccountBindingDto` | `404`、`422` | `setAccountBinding` |
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
    "id": "binding-1",
    "accountId": "account-1",
    "browserInstanceId": "workspace-1",
    "status": "active",
    "source": "manual",
    "maskedMetadataJson": "{\"token\":\"***\",\"profile\":\"main\"}",
    "createdAt": "2026-04-17T10:22:00Z",
    "updatedAt": "2026-04-17T10:22:00Z"
  }
}
```

```json
{
  "ok": true,
  "data": {
    "id": "account-1",
    "name": "TikTok 主账号",
    "platform": "tiktok",
    "username": "creator_main",
    "avatarUrl": null,
    "status": "active",
    "authExpiresAt": "2099-01-01T00:00:00Z",
    "followerCount": null,
    "followingCount": null,
    "videoCount": null,
    "tags": null,
    "notes": null,
    "publishReadiness": {
      "canPublish": true,
      "status": "ready",
      "lastValidatedAt": "2026-04-21T08:30:00Z",
      "errorCode": null,
      "errorMessage": null,
      "suggestedAction": null,
      "binding": {
        "bindingId": "binding-1",
        "browserInstanceId": "workspace-1",
        "status": "active",
        "source": "manual",
        "updatedAt": "2026-04-21T08:28:00Z"
      }
    },
    "createdAt": "2026-04-21T08:20:00Z",
    "updatedAt": "2026-04-21T08:30:00Z"
  }
}
```

**状态语义**

- `publishReadiness.status` 当前包含：
  - `ready`
  - `blocked`
  - `action_required`
  - `expired`
  - `binding_required`
- `suggestedAction` 用于给前端直接呈现下一步动作，不需要页面自行猜测。
- `lastValidatedAt` 仅在执行过 `refresh-stats` 后更新，表示最近一次真实校验时间。

---

## 12. M11 设备与工作区管理

**核心返回 DTO**: `DeviceWorkspaceDto`、`HealthCheckResultDto`、`DeviceWorkspaceLogDto`、`AccountBindingDto`、`DeviceWorkspaceEnvironmentStatusDto`、`DeviceWorkspaceBindingSummaryDto`、`DeviceWorkspaceHealthSummaryDto`

**当前契约要点**

- `DeviceWorkspaceDto` 现在会附带 3 组真实运行时摘要：
  - `environmentStatus`
  - `bindingSummary`
  - `healthSummary`
- `environmentStatus` 基于真实文件系统和实例状态派生：
  - `root_path` 是否存在
  - `root_path` 是否为目录
  - `browserInstances` 数量与运行数量
  - 是否存在异常浏览器实例
- `bindingSummary` 基于真实 `execution_bindings` 聚合：
  - `totalBindings`
  - `activeBindings`
  - `accountIds`
- `healthSummary` 基于最近一次 `health-check` 结果日志聚合；没有历史记录时返回 `unknown`。

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/devices/workspaces` | 无 | `DeviceWorkspaceDto[]`；每项包含 `environmentStatus / bindingSummary / healthSummary` | `500` | `fetchDeviceWorkspaces` |
| `POST /api/devices/workspaces` | `DeviceWorkspaceCreateInput`：`name`、`root_path` | `DeviceWorkspaceDto` | `422` | `createDeviceWorkspace` |
| `GET /api/devices/workspaces/{ws_id}` | 路径参数：`ws_id` | `DeviceWorkspaceDto`；包含 `environmentStatus / bindingSummary / healthSummary` | `404` | `fetchDeviceWorkspace` |
| `PATCH /api/devices/workspaces/{ws_id}` | `DeviceWorkspaceUpdateInput`：`name?`、`root_path?`、`status?` | `DeviceWorkspaceDto`；包含最新摘要 | `404`、`422` | `updateDeviceWorkspace` |
| `DELETE /api/devices/workspaces/{ws_id}` | 路径参数：`ws_id` | 删除结果对象 | `404` | `deleteDeviceWorkspace` |
| `POST /api/devices/workspaces/{ws_id}/health-check` | 无；执行一次真实工作区环境校验并记录最新结果 | `HealthCheckResultDto`：`workspace_id`、`status`、`checked_at`、`errorCode`、`errorMessage`、`nextAction`、`environmentStatus`、`bindingSummary` | `404` | `checkDeviceWorkspaceHealth` |
| `GET /api/devices/workspaces/{ws_id}/logs` | 查询参数：`since?` | `DeviceWorkspaceLogDto[]` | `404` | `fetchWorkspaceLogs` |
| `GET /api/devices/workspaces/{ws_id}/browser-instances` | 路径参数：`ws_id`；列出工作区下的真实浏览器实例 | `BrowserInstanceDto[]` | `404` | `fetchBrowserInstances` |
| `POST /api/devices/workspaces/{ws_id}/browser-instances` | 路径参数：`ws_id`；`BrowserInstanceCreateInput`：`name`、`profilePath` | `BrowserInstanceDto` | `404`、`422` | `createBrowserInstance` |
| `GET /api/devices/workspaces/{ws_id}/browser-instances/{instance_id}` | 路径参数：`ws_id`、`instance_id` | `BrowserInstanceDto` | `404` | 当前前端未直接调用 |
| `POST /api/devices/workspaces/{ws_id}/browser-instances/{instance_id}/start` | 路径参数：`ws_id`、`instance_id`；启动浏览器实例并广播状态变更 | `BrowserInstanceWriteResultDto`：`saved`、`updatedAt`、`versionOrRevision`、`objectSummary`、`browserInstance` | `404` | `startBrowserInstance` |
| `POST /api/devices/workspaces/{ws_id}/browser-instances/{instance_id}/stop` | 路径参数：`ws_id`、`instance_id`；停止浏览器实例并广播状态变更 | `BrowserInstanceWriteResultDto`：`saved`、`updatedAt`、`versionOrRevision`、`objectSummary`、`browserInstance` | `404` | `stopBrowserInstance` |
| `POST /api/devices/workspaces/{ws_id}/browser-instances/{instance_id}/health-check` | 路径参数：`ws_id`、`instance_id`；检查 profile 目录与实例状态 | `BrowserInstanceWriteResultDto`：`saved`、`updatedAt`、`versionOrRevision`、`objectSummary`、`browserInstance` | `404` | `checkBrowserInstanceHealth` |
| `GET /api/devices/browser-instances` | 无；当前是 `workspaces` 列表兼容别名 | `DeviceWorkspaceDto[]` | `500` | 当前前端未直接调用 |
| `POST /api/devices/browser-instances` | `DeviceWorkspaceCreateInput`；当前是创建工作区兼容别名 | `DeviceWorkspaceDto` | `422` | `createLegacyDeviceWorkspaceViaBrowserAlias` |
| `GET /api/devices/browser-instances/{ws_id}` | 路径参数：`ws_id`；当前是工作区详情兼容别名 | `DeviceWorkspaceDto` | `404` | 当前前端未直接调用 |
| `PATCH /api/devices/browser-instances/{ws_id}` | `DeviceWorkspaceUpdateInput`；当前是工作区更新兼容别名 | `DeviceWorkspaceDto` | `404`、`422` | 当前前端未直接调用 |
| `DELETE /api/devices/browser-instances/{ws_id}` | 路径参数：`ws_id`；当前是工作区删除兼容别名 | 删除结果对象 | `404` | `removeBrowserInstance` |
| `POST /api/devices/browser-instances/{ws_id}/health-check` | 无；当前是工作区健康检查兼容别名 | `HealthCheckResultDto` | `404` | 当前前端未直接调用 |
| `GET /api/devices/browser-instances/{ws_id}/logs` | 查询参数：`since?`；当前是工作区日志兼容别名 | `DeviceWorkspaceLogDto[]` | `404` | 当前前端未直接调用 |
| `GET /api/devices/bindings` | 无 | `AccountBindingDto[]` | `500` | `fetchExecutionBindings` |
| `PUT /api/devices/bindings/{account_id}` | `AccountBindingUpsertInput` | `AccountBindingDto` | `404`、`422` | 当前前端未直接调用 |
| `GET /api/devices/bindings/{binding_id}` | 路径参数：`binding_id` | `AccountBindingDto` | `404` | 当前前端未直接调用 |
| `DELETE /api/devices/bindings/{binding_id}` | 路径参数：`binding_id` | 删除结果对象 | `404` | `removeExecutionBinding` |

**当前差异**

- 已修复：前端 `BrowserInstanceDto` / `AccountBindingDto` 已对齐当前 M11 后端 schema，浏览器实例列表、创建、启动、停止与实例健康检查均走工作区嵌套路由。
- 已修复：`fetchWorkspaceLogs` 使用后端实际支持的 `since?` 查询参数，`fetchExecutionBindings` 不再附带无效查询参数。
- 已修复：旧 `device_workspaces` / `execution_bindings` 表会在 Runtime 启动时重建到当前 schema，补齐 `last_used_at / updated_at`，并移除会阻断插入的旧 NOT NULL 列。
- `health-check` 现在会直接返回中文可读的错误原因与下一步动作，前端不需要再自行猜测“根目录不存在”或“环境异常”的文案。

**示例**

```json
{
  "ok": true,
  "data": [
    {
      "id": "log-1",
      "workspaceId": "workspace-1",
      "kind": "health_check",
      "level": "INFO",
      "message": "工作区健康检查通过。",
      "contextJson": null,
      "createdAt": "2026-04-17T10:23:00Z"
    }
  ]
}
```

```json
{
  "ok": true,
  "data": {
    "workspace_id": "workspace-1",
    "status": "ready",
    "checked_at": "2026-04-21T08:40:00Z",
    "errorCode": null,
    "errorMessage": null,
    "nextAction": "如需执行发布或自动化，请先创建浏览器实例。",
    "environmentStatus": {
      "status": "ready_without_browser",
      "rootPathExists": true,
      "isDirectory": true,
      "browserInstanceCount": 0,
      "runningBrowserInstanceCount": 0,
      "errorCode": null,
      "errorMessage": "工作区已就绪，但还没有浏览器实例。",
      "nextAction": "如需执行发布或自动化，请先创建浏览器实例。"
    },
    "bindingSummary": {
      "totalBindings": 1,
      "activeBindings": 1,
      "accountIds": ["account-1"]
    }
  }
}
```

**状态语义**

- `environmentStatus.status` 当前包含：
  - `ready`
  - `ready_without_browser`
  - `degraded`
  - `missing_root`
  - `invalid_root`
- 当根目录不存在或路径非法时，`health-check` 会返回结构化错误：
  - `workspace.root_path_missing`
  - `workspace.root_path_invalid`
- 当工作区下存在异常浏览器实例时，`environmentStatus` 会返回 `workspace.browser_instance_error`。

---

## 13. M12 自动化执行中心

**核心返回 DTO**: `AutomationTaskDto`、`AutomationTaskRunDto`、`TriggerTaskResultDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/automation/tasks` | 查询参数：`status?`、`type?` | `AutomationTaskDto[]`：补充 `source`、`queue`、`latestResult`、`retry` | `500` | `fetchAutomationTasks` |
| `POST /api/automation/tasks` | `AutomationTaskCreateInput`：`name`、`type`、`rule?`、`cron_expr?`、`config_json?` | `AutomationTaskDto` | `422` | `createAutomationTask` |
| `GET /api/automation/tasks/{task_id}` | 路径参数：`task_id` | `AutomationTaskDto`：详情结构与列表一致，包含当前来源、队列状态、最近结果、可重试语义 | `404` | `fetchAutomationTask` |
| `PATCH /api/automation/tasks/{task_id}` | `AutomationTaskUpdateInput` | `AutomationTaskDto` | `404`、`422` | `updateAutomationTask` |
| `POST /api/automation/tasks/{task_id}/pause` | 无 | `AutomationTaskDto`，`enabled=false` | `404` | `pauseAutomationTask` |
| `POST /api/automation/tasks/{task_id}/resume` | 无 | `AutomationTaskDto`，`enabled=true` | `404` | `resumeAutomationTask` |
| `DELETE /api/automation/tasks/{task_id}` | 路径参数：`task_id` | 删除结果对象 | `404` | `deleteAutomationTask` |
| `POST /api/automation/tasks/{task_id}/trigger` | 无 | `TriggerTaskResultDto`：`task_id`、`run_id`、`status`、`queueStatus`、`queuePosition`、`activeRunId`、`nextAction`、`message` | `404`、`409 automation.task_disabled`、`409 automation.task_already_running`、`409 automation.binding_required`、`409 automation.config_missing` | `triggerAutomationTask` |
| `GET /api/automation/tasks/{task_id}/runs` | 路径参数：`task_id`；查询参数：`limit?` | `AutomationTaskRunDto[]`：补充 `resultSummary`、`errorCode`、`errorMessage`、`retryable`、`nextAction` | `404` | `fetchAutomationTaskRuns` |

**关键字段约束**

- `AutomationTaskDto.source`
  - `kind`：任务来源类型，默认优先取 `rule.kind` 或配置里的 `sourceKind`
  - `projectId / accountId / workspaceId`：从 `config_json` 或 `rule.config` 解析出的真实来源上下文
  - `label`：前端可直接展示的来源摘要
- `AutomationTaskDto.queue`
  - `status`：`idle | queued | running`
  - `position`：只有真实处于 `queued` 时返回序号，否则返回 `null`
  - `activeRunId`：当前活跃运行实例 ID
- `AutomationTaskDto.latestResult`
  - `status`：`idle | queued | running | succeeded | failed | cancelled`
  - `summary`：最近一次运行摘要，默认取最近日志的最后一行
  - `errorCode / errorMessage`：仅在失败或取消时返回
- `AutomationTaskDto.retry`
  - `canRetry`：是否允许当前任务直接重试
  - `errorCode`：重试阻断原因，当前覆盖 `automation.task_disabled`、`automation.binding_required`、`automation.config_missing`、`automation.task_already_running`
  - `nextAction`：中文下一步动作，前端可直接展示
- `AutomationTaskRunDto`
  - `resultSummary`：单次运行摘要
  - `retryable`：该次失败是否允许重试
  - `nextAction`：失败或取消后的恢复动作

**说明**

- 当前自动化中心保留原有路由，不新增新路由；本轮主要补齐的是任务实例生命周期契约。
- `409` 不再是空泛冲突：必须伴随明确 `error_code` 返回，供前端直接区分“任务停用 / 正在运行 / 缺少绑定 / 缺少配置”。

**示例**

```json
{
  "ok": true,
  "data": {
    "task_id": "auto-1",
    "run_id": "run-1",
    "status": "queued",
    "queueStatus": "queued",
    "queuePosition": 1,
    "activeRunId": "run-1",
    "nextAction": "可在运行历史中查看最新状态与执行日志。",
    "message": "自动化任务已进入执行队列。"
  }
}
```

---

## 14. M13 发布中心

**核心返回 DTO**: `PublishPlanDto`、`PublishCalendarDto`、`PrecheckResultDto`、`SubmitPlanResultDto`、`PublishReceiptDto`

**当前契约要点**

- `PublishPlanDto` 现在会附带 4 组发布执行语义：
  - `precheck_summary`：最近一次发布预检摘要
  - `latest_receipt`：最近一次平台回执摘要
  - `publish_readiness`：当前是否允许提交发布，以及阻断原因与下一步动作
  - `recovery`：是否允许重试 / 取消，以及建议恢复动作
- `PrecheckResultDto.items[]` 当前固定覆盖 5 类检查项：
  - `account_readiness`
  - `device_binding`
  - `publish_config`
  - `video_asset`
  - `schedule`
- `PublishReceiptDto` 当前用于表达平台回执阶段化状态，前端可直接消费：
  - `stage`
  - `summary`
  - `error_code`
  - `error_message`
  - `next_action`
  - `is_final`
- 当前发布链路会广播 3 类事件：
  - `publishing.precheck.completed`
  - `publishing.submit.completed`
  - `publishing.receipt.updated`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/publishing/plans` | 查询参数：`status?` | `PublishPlanDto[]`；每项包含 `precheck_summary / latest_receipt / publish_readiness / recovery` | `500` | `fetchPublishPlans` |
| `POST /api/publishing/plans` | `PublishPlanCreateInput`：`title`、`account_id?`、`account_name?`、`project_id?`、`video_asset_id?`、`scheduled_at?` | `PublishPlanDto` | `422` | `createPublishPlan` |
| `GET /api/publishing/calendar` | 无；当前后端返回完整日历 DTO，不消费 `from / to` 查询参数 | `PublishCalendarDto`：`items[]`、`generated_at` | `500` | `fetchPublishingCalendar` |
| `GET /api/publishing/plans/{plan_id}` | 路径参数：`plan_id` | `PublishPlanDto` | `404` | `fetchPublishPlan` |
| `PATCH /api/publishing/plans/{plan_id}` | `PublishPlanUpdateInput`：`title?`、`account_name?`、`status?`、`scheduled_at?` | `PublishPlanDto` | `404`、`422` | `updatePublishPlan` |
| `DELETE /api/publishing/plans/{plan_id}` | 路径参数：`plan_id` | 删除结果对象 | `404` | `deletePublishPlan` |
| `POST /api/publishing/plans/{plan_id}/precheck` | 无；执行一次真实发布预检并广播结果 | `PrecheckResultDto`：`plan_id`、`items[]`、`conflicts[]`、`has_errors`、`blocking_count`、`readiness`、`checked_at` | `404` | `runPublishingPrecheck` |
| `POST /api/publishing/plans/{plan_id}/submit` | 无；提交发布并写入最新回执摘要 | `SubmitPlanResultDto`：`plan_id`、`status`、`submitted_at`、`message`、`receipt_status`、`error_code`、`error_message`、`next_action`、`receipt` | `404`、`409 publishing.precheck_failed` | `submitPublishPlan` |
| `POST /api/publishing/plans/{plan_id}/cancel` | 无 | `PublishPlanDto` | `404` | `cancelPublishPlan` |
| `GET /api/publishing/plans/{plan_id}/receipts` | 路径参数：`plan_id` | `PublishReceiptDto[]` | `404` | `fetchPublishReceipts` |
| `GET /api/publishing/plans/{plan_id}/receipt` | 路径参数：`plan_id` | `PublishReceiptDto` | `404 publishing.receipt_not_found` | `fetchPublishReceipt` |

**当前差异**

- 已修复：`apps/desktop/src/types/runtime.ts` 中的 `PublishPlanDto / PrecheckResultDto / SubmitPlanResultDto / PublishReceiptDto / PublishCalendarDto` 已对齐当前后端真实返回。
- 已修复：`fetchPublishingCalendar()` 不再附带 `from / to` 查询参数，直接消费后端 `PublishCalendarDto` 聚合对象。

**当前错误码**

| `error_code` | 含义 | 触发条件 |
| --- | --- | --- |
| `publishing.precheck_failed` | 发布预检未通过 | `/submit` 时存在阻断项，返回 `409` |
| `publishing.account_required` | 发布计划缺少账号 | `account_id` 为空 |
| `publishing.account_not_ready` | 发布账号不可用 | 账号不存在、未启用、缺少用户名或授权已过期 |
| `publishing.device_binding_required` | 缺少可用工作区绑定 | 账号未绑定工作区，或绑定工作区无效 / 根目录异常 |
| `publishing.config_missing` | 发布配置不完整 | 缺少发布时间 |
| `publishing.video_asset_required` | 缺少视频资产 | `video_asset_id` 为空 |
| `publishing.schedule_conflict` | 发布排期冲突 | 同账号同时间存在冲突排期 |
| `publishing.receipt_not_found` | 发布回执不存在 | `/receipt` 查询不到最新回执 |

**示例**

```json
{
  "ok": true,
  "data": {
    "id": "plan-1",
    "title": "晚间发布排期",
    "status": "submitted",
    "precheck_summary": {
      "status": "ready",
      "checked_at": "2026-04-21T10:20:00Z",
      "blocking_count": 0
    },
    "publish_readiness": {
      "can_submit": true,
      "status": "ready",
      "error_code": null,
      "error_message": null,
      "next_action": null,
      "binding": {
        "binding_id": "binding-1",
        "workspace_id": "workspace-1",
        "workspace_name": "主发布工作区",
        "workspace_status": "ready",
        "root_path": "D:/tkops/workspaces/publish",
        "updated_at": "2026-04-21T10:18:00Z"
      }
    },
    "latest_receipt": {
      "id": "receipt-1",
      "status": "receipt_pending",
      "stage": "receipt",
      "summary": "已提交平台，等待平台回执。",
      "error_code": null,
      "error_message": null,
      "next_action": {
        "key": "refresh-receipt",
        "label": "刷新回执"
      },
      "received_at": "2026-04-21T10:20:00Z",
      "is_final": false
    }
  }
}
```

---

## 15. M14 渲染与导出中心

**核心返回 DTO**: `RenderTaskDto`、`CancelRenderResultDto`、`ExportProfileDto`、`RenderResourceUsageDto`

**当前契约要点**

- `RenderTaskDto` 现在会附带 3 组运行时语义：
  - `stage`：阶段摘要，当前覆盖 `queued / rendering / exporting / completed / failed / cancelled`
  - `output`：输出文件探测结果，包含 `path / exists / size_bytes / last_checked_at / can_open`
  - `failure`：失败或异常输出语义，包含 `error_code / error_message / next_action / retryable`
- 当前渲染链路会广播 2 类事件：
  - `render.progress`：进度更新事件
  - `render.status.changed`：状态、阶段、输出与失败信息变更事件

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/renders/profiles` | 无 | `ExportProfileDto[]` | `500` | `fetchExportProfiles` |
| `POST /api/renders/profiles` | `ExportProfileCreateInput`：`name`、`format?`、`resolution?`、`fps?`、`video_bitrate?`、`audio_policy?`、`subtitle_policy?`、`config_json?` | `ExportProfileDto` | `400`、`422` | `createExportProfile` |
| `GET /api/renders/templates` | 无；当前后端直接复用 profile 列表作为模板来源 | `ExportProfileDto[]` | `500` | `listRenderTemplates` |
| `GET /api/renders/resource-usage` | 无 | `RenderResourceUsageDto`：`cpu`、`gpu`、`disk`、`collectedAt` | `500` | `fetchRenderResourceUsage` |
| `GET /api/renders/tasks` | 查询参数：`status?` | `RenderTaskDto[]`；每项包含 `stage / output / failure` | `500` | `fetchRenderTasks` |
| `POST /api/renders/tasks` | `RenderTaskCreateInput`：`project_id?`、`project_name?`、`preset?`、`format?` | `RenderTaskDto` | `422` | `createRenderTask` |
| `GET /api/renders/tasks/{task_id}` | 路径参数：`task_id` | `RenderTaskDto` | `404` | `fetchRenderTask` |
| `PATCH /api/renders/tasks/{task_id}` | `RenderTaskUpdateInput`：`preset?`、`format?`、`status?`、`progress?`、`output_path?`、`error_message?` | `RenderTaskDto` | `404`、`422` | `updateRenderTask` |
| `DELETE /api/renders/tasks/{task_id}` | 路径参数：`task_id` | 删除结果对象 | `404` | `deleteRenderTask` |
| `POST /api/renders/tasks/{task_id}/cancel` | 路径参数：`task_id` | `CancelRenderResultDto`：`task_id`、`status`、`message` | `404`、`409 render.task_not_cancellable` | `cancelRenderTask` |
| `POST /api/renders/tasks/{task_id}/retry` | 路径参数：`task_id`；仅允许 `failed / cancelled` 任务重试 | `RenderTaskDto` | `404`、`409 render.task_not_retryable` | `retryRenderTask` |

**当前差异**

- 已修复：`apps/desktop/src/types/runtime.ts` 中的 `RenderTaskDto / RenderResourceUsageDto` 已对齐 `stage / output / failure` 与嵌套 `cpu / gpu / disk` 结构。
- 已修复：`listRenderTemplates()` 返回 `ExportProfileDto[]`，与后端 `GET /api/renders/templates` 实际返回保持一致。

**当前错误码**

| `error_code` | 含义 | 触发条件 |
| --- | --- | --- |
| `render.task_not_cancellable` | 当前任务不可取消 | 只有 `queued / rendering` 状态允许取消 |
| `render.task_not_retryable` | 当前任务不可重试 | 只有 `failed / cancelled` 状态允许重试 |
| `render.task_failed` | 渲染任务执行失败 | `status=failed` 时出现在 `failure` |
| `render.task_cancelled` | 渲染任务已取消 | `status=cancelled` 时出现在 `failure` |
| `render.output_not_found` | 输出文件不存在 | `status=completed` 但 `output.path` 对应文件不存在 |

**示例**

```json
{
  "ok": true,
  "data": {
    "id": "render-task-1",
    "project_id": "project-1",
    "project_name": "夏季穿搭合集",
    "preset": "1080p",
    "format": "mp4",
    "status": "completed",
    "progress": 100,
    "output_path": "D:/tkops/output/project-1/final.mp4",
    "error_message": null,
    "stage": {
      "code": "completed",
      "label": "已完成"
    },
    "output": {
      "path": "D:/tkops/output/project-1/final.mp4",
      "exists": true,
      "size_bytes": 10485760,
      "last_checked_at": "2026-04-21T10:40:00Z",
      "can_open": true
    },
    "failure": {
      "error_code": null,
      "error_message": null,
      "next_action": null,
      "retryable": false
    },
    "started_at": "2026-04-21T10:31:00Z",
    "finished_at": "2026-04-21T10:39:00Z",
    "created_at": "2026-04-21T10:30:00Z",
    "updated_at": "2026-04-21T10:40:00Z"
  }
}
```

---

## 16. M15 复盘与优化中心

**核心返回 DTO**: `ReviewSummaryDto`、`AnalyzeProjectResultDto`、`ProjectSummaryDto`、`ApplySuggestionToScriptResultDto`
`ReviewSummaryDto.suggestions[]` 当前由 summary 聚合返回；`adopt` 会创建新的项目草稿，`apply-to-script` 会在原项目内生成新的脚本版本并回写建议状态。

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/review/projects/{project_id}/summary` | 路径参数：`project_id` | `ReviewSummaryDto` | `404` | `fetchReviewSummary` |
| `POST /api/review/projects/{project_id}/analyze` | 路径参数：`project_id` | `AnalyzeProjectResultDto`：`project_id`、`status`、`message`、`analyzed_at` | `404`、`409` | `analyzeReviewProject` |
| `PATCH /api/review/projects/{project_id}/summary` | `ReviewSummaryUpdateInput`：核心指标字段 | `ReviewSummaryDto` | `404`、`422` | `updateReviewSummary` |
| `POST /api/review/projects/{project_id}/suggestions/{suggestion_id}/adopt` | 路径参数：`project_id`、`suggestion_id` | `ProjectSummaryDto`：采纳建议后生成的新项目 | `404`、`409` | `adoptReviewSuggestion` |
| `POST /api/review/suggestions/{suggestion_id}/adopt` | 路径参数：`suggestion_id`；使用当前上下文项目 | `ProjectSummaryDto` | `404`、`409` | 当前前端未直接调用 |
| `POST /api/review/suggestions/{suggestion_id}/apply-to-script` | 路径参数：`suggestion_id`；在原项目内生成新的脚本版本并回写建议状态 | `ApplySuggestionToScriptResultDto`：`projectId`、`suggestionId`、`status`、`message`、`currentScriptVersion`、`scriptVersion` | `404`、`409`、`500` | `applyReviewSuggestionToScript` |

**示例**

```json
{
  "ok": true,
  "data": {
    "project_id": "project-1",
    "status": "done",
    "message": "复盘分析已完成。",
    "analyzed_at": "2026-04-17T10:28:00Z"
  }
}
```

```json
{
  "ok": true,
  "data": {
    "projectId": "project-1",
    "suggestionId": "project-1:hook_first_3s",
    "status": "已应用",
    "message": "已将复盘建议应用到原项目脚本，并生成新的脚本版本",
    "currentScriptVersion": 3,
    "scriptVersion": {
      "revision": 3,
      "source": "review_apply",
      "content": "原脚本内容\n\n【复盘建议】\n提高前 3 秒钩子",
      "provider": null,
      "model": null,
      "aiJobId": null,
      "createdAt": "2026-04-19T11:28:00Z"
    }
  }
}
```

---

## 17. AI 与系统设置

### 17.1 Runtime 基础设置

**核心返回 DTO**: `RuntimeHealthSnapshotDto`、`AppSettingsDto`、`RuntimeDiagnosticsDto`、`RuntimeMediaDiagnosticsDto`、`RuntimeLogPageDto`、`DiagnosticsBundleDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/settings/health` | 无 | `RuntimeHealthSnapshotDto`：`runtime`、`aiProvider`、`renderQueue`、`publishingQueue`、`taskBus`、`license`、`lastSyncAt` | `500` | `fetchRuntimeHealth` |
| `GET /api/settings/config` | 无 | `AppSettingsDto`：`runtime`、`paths`、`logging`、`ai`、`revision` | `500` | `fetchRuntimeConfig` |
| `PUT /api/settings/config` | `AppSettingsUpdateInput`：`runtime.mode/workspaceRoot`、`paths.cacheDir/exportDir/logDir`、`logging.level`、`ai.provider/model/voice/subtitleMode`；成功后广播 `config.changed` | `AppSettingsDto` | `422`、`500` | `updateRuntimeConfig` |
| `GET /api/settings/diagnostics` | 无 | `RuntimeDiagnosticsDto`：`databasePath`、`logDir`、`revision`、`mode`、`healthStatus` | `500` | `fetchRuntimeDiagnostics` |
| `GET /api/settings/diagnostics/media` | 无；读取 ffprobe 可用性、路径、版本与最近检查时间 | `RuntimeMediaDiagnosticsDto`：`ffprobe.status`、`ffprobe.path`、`ffprobe.version`、`ffprobe.errorCode`、`ffprobe.errorMessage`、`checkedAt` | `500`；ffprobe 异常时返回 `media.ffprobe_unavailable` 或 `media.ffprobe_incompatible` | 当前前端未直接调用 |
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
| `POST /api/settings/ai-providers/{provider_id}/models/refresh` | 路径参数：`provider_id`；OpenAI 兼容类读取 `{baseUrl}/models`，Ollama / OpenRouter 使用专用目录接口 | `AIModelCatalogRefreshResultDto` | `400`、`404`、`502`；缺密钥 `provider.model.refresh_missing_secret`，缺 Base URL `provider.model.refresh_missing_base_url` | `refreshAIProviderModels` |

`AIProviderCatalogItemDto` 字段：

| 字段 | 含义 |
| --- | --- |
| `provider`、`label`、`kind` | Provider ID、展示名称和基础类型。 |
| `region` | `domestic`、`global`、`local`、`custom`，用于 Provider Hub 模板分组。 |
| `category` | `model_hub`、`text`、`video`、`tts`、`aggregator`、`local`、`custom` 等工作台分类。 |
| `protocol` | Runtime 协议族，如 `openai_responses`、`openai_chat`、`anthropic_messages`、`gemini_generate`、`cohere_chat`、`manual_catalog`。 |
| `modelSyncMode` | `remote`、`static`、`manual`，标识模型目录来自远端同步、内置目录或手动维护。 |
| `tags` | 中文模板标签，用于前端展示和检索，不参与连通性判断。 |
| `configured`、`status` | 由密钥、Base URL 和 Runtime 健康快照计算，不代表远端模型一定可用。 |
| `baseUrl`、`secretSource` | 当前 Runtime 解析出的 Base URL 与密钥来源；不会返回明文 API Key。 |
| `capabilities` | Provider 声明能力，模型级最终能力仍以 `AIModelCatalogItemDto.capabilityTypes` 为准。 |
| `requiresBaseUrl`、`supportsModelDiscovery` | 配置要求和是否允许通过 Runtime 执行模型目录刷新。 |

首批 Provider Hub 模板覆盖国际、本地、国内文本/多模态、国内视频、国内 TTS 和自定义 Provider。模板只作为接入入口，真实可用模型仍以配置后的模型目录接口为准。

### 17.4 AI Provider 运行时聚合

**核心返回 DTO**: `AIProviderHealthOverviewDto`、`AIProviderModelWriteReceiptDto`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/ai-providers/health` | 无；读取最近一次聚合健康快照 | `AIProviderHealthOverviewDto`：`providers[]`、`refreshedAt` | `500` | `config-bus.ts`（`fetchProviderReadinessSilently` -> `fetchProviderHealth`） |
| `POST /api/ai-providers/health/refresh` | 无；逐个 Provider 触发静默刷新，失败不会阻断 Runtime 启动 | `AIProviderHealthOverviewDto`：`providers[]`、`refreshedAt` | `500`；单 Provider 失败时记录 `provider.health.refresh_failed` | 当前前端未直接调用 |
| `PUT /api/ai-providers/{provider_id}/models/{model_id}` | 路径参数：`provider_id`、`model_id`；`AIProviderModelUpsertInput`：`displayName`、`capabilityKinds`、`inputModalities[]`、`outputModalities[]`、`contextWindow?`、`defaultFor[]`、`enabled` | `AIProviderModelWriteReceiptDto`：`saved`、`wasUpsert`、`updatedAt`、`versionOrRevision`、`objectSummary`、`model` | `400`、`404`；能力缺失时返回 `provider.model.capability_required` | 当前前端未直接调用 |

**健康示例**

```json
{
  "ok": true,
  "data": {
    "runtime": {
      "status": "online",
      "port": 8000,
      "uptimeMs": 1200,
      "version": "0.3.4"
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
    "version": "0.3.4",
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

**核心返回结构**: `TaskInfo`
当前后端 `TaskManager` 是内存态任务管理器，`/api/tasks` 只返回 `queued/running` 活跃任务。前端 `task-bus.ts` 会把 WebSocket 事件补齐成兼容 `TaskInfo` / 旧 `TaskDto` 的混合字段。

后端字段：`id`、`task_type`、`project_id`、`status`、`progress`、`message`、`created_at`、`updated_at`
前端兼容字段：`kind`、`label`、`progressPct`、`projectId`、`errorCode`、`errorMessage`、`retryable`、`createdAt`、`updatedAt`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `GET /api/tasks` | 当前无后端查询参数；前端 wrapper 不传筛选参数 | `TaskInfo[]` | `500` | `fetchActiveTasks` |
| `GET /api/tasks/{task_id}` | 路径参数：`task_id` | `TaskInfo` | `404` | `fetchTaskStatus` |
| `POST /api/tasks/{task_id}/cancel` | 路径参数：`task_id` | `{ task_id, status, message }` | `404`、`409`（`task.conflict`） | `cancelTask` |

**示例**

```json
{
  "ok": true,
  "data": {
    "id": "task-1",
    "task_type": "video_import",
    "project_id": "project-1",
    "status": "running",
    "progress": 45,
    "message": "正在解析视频元信息",
    "created_at": "2026-04-17T10:30:00Z",
    "updated_at": "2026-04-17T10:30:10Z"
  }
}
```

---

## 19. WebSocket

**连接地址**: `WS /api/ws`

| 接口 | 请求参数 | 返回结果 | 错误码 | 当前前端调用点 |
| --- | --- | --- | --- | --- |
| `WS /api/ws` | 客户端可发送 `ping` 维持连接；服务端当前只读取并记录文本消息 | 服务端主动推送任务、视频导入阶段、配置和状态类事件 | 连接断开时前端 3 秒后自动重连 | `task-bus.ts` |

**前端 TaskBus 行为**

- WebSocket 地址由 `VITE_RUNTIME_BASE_URL` 推导，默认连接 `ws://127.0.0.1:8000/api/ws`。
- 心跳间隔为 25 秒，发送文本 `ping`。
- 可订阅 key 包括 `taskId`、`videoId`、`jobId`、`trackId`、`accountId`、`workspaceId`、`planId`、`projectId`。
- 接收到带 `taskId` 的事件时，`task-bus.ts` 会同步更新 `tasks` Map；所有事件都会按 key 写入 `lastEvents`。

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

**当前已登记事件类型**

- `task.started`
- `task.progress`
- `task.log`
- `task.completed`
- `task.failed`
- `script.ai.stream.chunk`
- `script.ai.stream.completed`
- `script.ai.stream.failed`
- `video.import.stage.started`
- `video.import.stage.progress`
- `video.import.stage.completed`
- `video.import.stage.failed`
- `render.progress`
- `account.status.changed`
- `device.status.changed`
- `publish.receipt.updated`
- `config.changed`
- `ai-capability.changed`
- `context.project.changed`

**视频导入阶段事件示例**

视频导入 TaskBus pilot 中，`taskId` 等于 `ImportedVideo.id`。通用任务进度通过 `task.progress` 广播，阶段状态通过 `video.import.stage.*` 广播。

```json
{
  "schema_version": 1,
  "type": "video.import.stage.progress",
  "videoId": "video-1",
  "stage": "import",
  "progressPct": 45,
  "message": "正在解析视频元信息"
}
```

**渲染进度事件示例**

```json
{
  "schema_version": 1,
  "type": "render.progress",
  "taskId": "render-1",
  "projectId": "project-1",
  "status": "running",
  "progressPct": 62,
  "bitrateKbps": 3800,
  "outputSec": 9.2,
  "message": "正在渲染"
}
```

**当前差异**

- 前端 `task-bus.ts` 已兼容缺少 `schema_version` 的历史事件，并在解析时补齐 `schema_version: 1`。
- `process_video_import_task` 仍可能额外广播历史 `video_status_changed` 事件；新页面应以 TaskBus 标准事件为准，旧事件仅作兼容观察。

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

### 20.1 当前代码一致性异常

以下项目用于记录当前代码中已经存在或刚完成收口的 wrapper / 类型 / 路由差异；后续修复时必须同时改后端、前端、测试和本文档。

| 模块 | 差异 | 当前处理 |
| --- | --- | --- |
| Prompt 模板 | 已修复：前端 `runtime-client.ts` 使用 `PUT`，请求字段对齐 `kind/name/description/content` | 已有 `runtime-client-b-s3.spec.ts` 覆盖 |
| M08 字幕对齐 | 已修复：前端 `SubtitleTrackDto`、`SubtitleTrackGenerateInput`、`SubtitleStyleTemplateDto`、`SubtitleExportDto` 与后端 sourceVoice / alignment / 内联导出 schema 对齐 | 已有 `runtime-client-b-s4.spec.ts`、`runtime-client-subtitles.spec.ts` 与 `subtitle-alignment-store.spec.ts` 覆盖 |
| M11 设备与工作区 | 已修复：前端新增嵌套 browser instance routes、`BrowserInstanceWriteResultDto`，binding 入参与后端 `AccountBindingDto` 对齐 | 已有 `runtime-client-b-s5.spec.ts` 覆盖；legacy alias 继续保留为后端兼容能力 |
| M13 发布中心 | 已修复：前端 `PublishReceiptDto`、`PublishCalendarDto` 与后端聚合 schema 对齐，publishing store 增加 calendar / receipt 消费 | 已有 `runtime-client-b-s5.spec.ts` 与 `runtime-stores-m09-m15.spec.ts` 覆盖 |
| M14 渲染导出 | 已修复：前端 `RenderResourceUsageDto`、templates/profile 类型与后端 schema 对齐，renders store 增加 profiles/templates/resource-usage/retry 消费 | 已有 `runtime-client-b-s5.spec.ts` 与 `runtime-stores-m09-m15.spec.ts` 覆盖 |
| TaskBus | 已修复：前端兼容缺少 `schema_version` 的历史事件并补齐为 `1`；`video_status_changed` 仍作为 legacy event type 保留 | 已有 `task-bus.spec.ts` 覆盖 |

当前文档与代码对齐批次：**2026-04-24 Runtime HTTP 路由库存复核 + V2 类型漂移收尾，181 条 HTTP 接口明细已与当前后端代码全量对齐；后续主要补更多异常样例与端到端联调说明**

---

## 21. AI Provider 多模型调用层架构

> **本节定位**：为 Codex（后端）和 Gemini（前端）提供完整的多 AI Provider 调用层实现规格。Codex 读本节写代码，Gemini 读本节对齐前端状态。

### 21.1 现状与缺口总览

| 层级 | 现状 | 缺口 |
| --- | --- | --- |
| Provider 目录层 | `_provider_catalog_metadata()` 已定义 30+ Provider，包含国内厂商模板和自定义 Provider 模板 | **已完成** |
| 健康探针层 | `openai` / `openai_compatible` / `anthropic` / `gemini` / `cohere` 均有 `_post_*_probe` | **已完成** |
| 文本生成 dispatch | `generate_text()` 已使用 `dispatch_text_generation(runtime_config, request)`，按 `ProviderRuntimeConfig.protocol_family` 走统一 registry | **已完成** |
| TTS 生成 dispatch | `voice_service.py` 的 `generate_track()` 已支持 `blocked / processing` 双路径；当前仅 OpenAI TTS 可真实执行 | **已完成最小真实接入** |
| Provider 适配器目录 | `apps/py-runtime/src/ai/providers/` 已落地文本 adapter 与 `tts_openai.py`；其他 TTS adapter 仍为预留规格 | **已部分完成** |

### 21.2 Provider 协议族分类

所有 Provider 按 HTTP 协议归为少量协议族，dispatch 只需实现稳定路径：

| 协议族 ID | 协议特征 | 覆盖 Provider |
| --- | --- | --- |
| `openai_responses` | POST `/responses`，Bearer auth，`{model, instructions, input}` | `openai`（仅 Responses API） |
| `openai_chat` | POST `/chat/completions`，Bearer auth，`{model, messages}`；模型目录刷新默认读取 `/models` | `openai_compatible`, `custom_openai_compatible`, `deepseek`, `qwen`, `kimi`, `zhipu`, `volcengine`, `baidu_qianfan`, `tencent_hunyuan`, `xunfei_spark`, `minimax`, `baichuan`, `lingyi`, `stepfun`, `sensecore`, `openrouter`, `ollama` |
| `anthropic_messages` | POST `/messages`，`x-api-key` header + `anthropic-version`，`{model, messages, max_tokens}` | `anthropic` |
| `gemini_generate` | POST `/models/{model}:generateContent?key=`，无 auth header，`{contents}` | `gemini` |
| `cohere_chat` | POST `/chat`，Bearer auth，`{model, message}` | `cohere` |

> **规则**：目录中标记为 `manual_catalog` 或 TTS/视频/分析专用的 Provider（如 `azure_speech`、`elevenlabs`、`kling`、`custom_video_provider` 等）不走文本生成 dispatch。

### 21.3 Provider 适配器接口契约（Codex 实现规格）

#### 21.3.1 文件结构

```
apps/py-runtime/src/ai/providers/
├── __init__.py              # 导出 dispatch_text_generation / dispatch_tts / has_tts_adapter
├── _http.py                 # Provider HTTP 公共层
├── base.py                  # TextGenerationAdapter / TTSAdapter 抽象基类
├── errors.py                # ProviderHTTPException
├── openai_responses.py      # OpenAI Responses API 适配
├── openai_chat.py           # OpenAI-compatible Chat Completions 适配
├── anthropic_messages.py    # Anthropic Messages API 适配
├── gemini_generate.py       # Google Gemini GenerateContent 适配
├── cohere_chat.py           # Cohere Chat 适配
└── tts_openai.py            # OpenAI TTS 适配
```

> 当前状态（2026-04-18）：其他 TTS adapter 仍属预留规格，尚未在 `apps/py-runtime/src/ai/providers/` 目录落地。

#### 21.3.2 TextGenerationAdapter 基类

```python
# apps/py-runtime/src/ai/providers/base.py

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextGenerationRequest:
    """统一的文本生成请求"""
    model: str
    system_prompt: str       # agentRole + systemPrompt 拼接
    user_prompt: str         # 模板渲染后的用户 prompt
    max_tokens: int = 4096
    temperature: float = 0.7
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class TextGenerationResponse:
    """统一的文本生成响应"""
    text: str
    usage_input_tokens: int | None = None
    usage_output_tokens: int | None = None
    raw_response: dict | None = None  # 调试用，不暴露给前端


class TextGenerationAdapter(ABC):
    """文本生成适配器抽象基类"""

    @abstractmethod
    def generate(
        self,
        *,
        base_url: str,
        api_key: str,
        request: TextGenerationRequest,
    ) -> TextGenerationResponse:
        """调用 Provider API 生成文本，失败时抛 ProviderError"""
        ...
```

#### 21.3.3 Anthropic Messages 适配器（`_call_anthropic_messages`）

**文件**：`apps/py-runtime/src/ai/providers/anthropic_messages.py`

**HTTP 请求规格**：

| 项目 | 值 |
| --- | --- |
| Method | `POST` |
| Endpoint | `{base_url}`（默认 `https://api.anthropic.com/v1/messages`） |
| Auth Header | `x-api-key: {api_key}`（**不是** Bearer） |
| 必传 Header | `anthropic-version: 2023-06-01`，`content-type: application/json` |
| Timeout | 60s |

**请求体**：

```json
{
  "model": "{model}",
  "max_tokens": 4096,
  "system": "{system_prompt}",
  "messages": [
    { "role": "user", "content": "{user_prompt}" }
  ]
}
```

**响应解析**：

```python
# 成功响应结构
{
  "id": "msg_...",
  "type": "message",
  "content": [
    { "type": "text", "text": "生成的文本..." }
  ],
  "usage": {
    "input_tokens": 100,
    "output_tokens": 200
  }
}

# 解析逻辑
texts = [block["text"] for block in response["content"] if block["type"] == "text"]
text = "\n".join(texts).strip()
if not text:
    raise ProviderError(502, "Anthropic 返回了空文本。")
```

**错误映射**：

| HTTP Status | error.type | 中文提示 | error_code |
| --- | --- | --- | --- |
| 401 | `authentication_error` | API Key 无效或已过期 | `ai_provider_auth_failed` |
| 429 | `rate_limit_error` | 请求频率超限，请稍后重试 | `ai_provider_rate_limited` |
| 529 | `overloaded_error` | Anthropic 服务过载，请稍后重试 | `ai_provider_overloaded` |
| 5xx | — | AI Provider 服务异常 | `ai_provider_server_error` |

#### 21.3.4 Gemini GenerateContent 适配器（`_call_gemini_generate`）

**文件**：`apps/py-runtime/src/ai/providers/gemini_generate.py`

**HTTP 请求规格**：

| 项目 | 值 |
| --- | --- |
| Method | `POST` |
| Endpoint | `{base_url}/{model}:generateContent?key={api_key}`（默认 base `https://generativelanguage.googleapis.com/v1beta/models`） |
| Auth | **Query param** `key=`（不用 header） |
| Header | `content-type: application/json` |
| Timeout | 60s |

**请求体**：

```json
{
  "contents": [
    {
      "parts": [
        { "text": "{user_prompt}" }
      ]
    }
  ],
  "systemInstruction": {
    "parts": [
      { "text": "{system_prompt}" }
    ]
  },
  "generationConfig": {
    "maxOutputTokens": 4096,
    "temperature": 0.7
  }
}
```

**响应解析**：

```python
# 成功响应结构
{
  "candidates": [
    {
      "content": {
        "parts": [
          { "text": "生成的文本..." }
        ]
      },
      "finishReason": "STOP"
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 100,
    "candidatesTokenCount": 200
  }
}

# 解析逻辑
candidates = response.get("candidates", [])
if not candidates:
    raise ProviderError(502, "Gemini 未返回候选结果。")
parts = candidates[0].get("content", {}).get("parts", [])
text = "\n".join(p["text"] for p in parts if "text" in p).strip()
if not text:
    raise ProviderError(502, "Gemini 返回了空文本。")
```

**Endpoint 构造注意**：`model` 必须 URL-encode（`urllib.parse.quote(model, safe="")`），与现有 `_post_gemini_probe` 逻辑一致。

#### 21.3.5 Cohere Chat 适配器（`_call_cohere_chat`）

**文件**：`apps/py-runtime/src/ai/providers/cohere_chat.py`

**HTTP 请求规格**：

| 项目 | 值 |
| --- | --- |
| Method | `POST` |
| Endpoint | `{base_url}/chat`（默认 `https://api.cohere.com/v2/chat`） |
| Auth | `Authorization: Bearer {api_key}` |
| Header | `content-type: application/json` |
| Timeout | 60s |

**请求体**：

```json
{
  "model": "{model}",
  "messages": [
    { "role": "system", "content": "{system_prompt}" },
    { "role": "user", "content": "{user_prompt}" }
  ]
}
```

**响应解析**：

```python
# Cohere V2 Chat API 响应结构
{
  "id": "...",
  "message": {
    "role": "assistant",
    "content": [
      { "type": "text", "text": "生成的文本..." }
    ]
  },
  "usage": {
    "tokens": { "input_tokens": 100, "output_tokens": 200 }
  }
}

# 解析逻辑
content = response.get("message", {}).get("content", [])
if isinstance(content, list):
    text = "\n".join(c["text"] for c in content if c.get("type") == "text").strip()
elif isinstance(content, str):
    text = content.strip()
if not text:
    raise ProviderError(502, "Cohere 返回了空文本。")
```

### 21.4 generate_text dispatch（当前实现）

**目标文件**：`apps/py-runtime/src/services/ai_text_generation_service.py`

**当前状态（2026-04-18）**：

- `AITextGenerationService.generate_text()` 已不再维护 `_PROTOCOL_MAP`，也不再按 `provider == 'openai' / 'openai_compatible'` 做硬编码分支。
- `AICapabilityService.get_provider_runtime_config()` 已返回 `ProviderRuntimeConfig.protocol_family`，由 `ai.providers.dispatch_text_generation(runtime_config, request)` 统一分发。
- runtime 当前已注册的文本协议族为：`openai_responses`、`openai_chat`、`anthropic_messages`、`gemini_generate`、`cohere_chat`。

```python
provider_runtime = self._capability_service.get_provider_runtime_config(capability.provider)

output = ai_providers.dispatch_text_generation(
    provider_runtime,
    TextGenerationRequest(
        model=capability.model,
        system_prompt=instructions,
        user_prompt=prompt,
        request_id=request_id,
    ),
)
output_text = output.text
```

**当前约束**：
- `dispatch_text_generation(runtime_config, request)` 只依赖 `runtime_config.protocol_family`，不再接收额外 `protocol_family` 参数。
- 未注册的协议族统一抛 `ai_provider_unsupported`。
- `GeneratedTextResult`、Prompt 模板渲染以及 `AIJobRepository.create_running / mark_succeeded / mark_failed` 生命周期保持不变。

### 21.5 TTS 调用层规格（Codex 实现规格）

#### 21.5.1 TTS 适配器基类

```python
# apps/py-runtime/src/ai/providers/base.py（追加）

@dataclass(frozen=True, slots=True)
class TTSRequest:
    """统一的 TTS 请求"""
    text: str
    voice_id: str
    model: str | None = None
    speed: float = 1.0
    output_format: str = "mp3"  # mp3 / wav / pcm
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class TTSResponse:
    """统一的 TTS 响应"""
    audio_bytes: bytes
    content_type: str          # audio/mpeg, audio/wav, etc.
    duration_ms: int | None = None


class TTSAdapter(ABC):
    @abstractmethod
    def synthesize(
        self,
        *,
        base_url: str,
        api_key: str,
        request: TTSRequest,
    ) -> TTSResponse:
        ...
```

#### 21.5.2 各 TTS Provider 调用规格

| Provider | Endpoint | Auth | 请求体核心字段 | 响应 |
| --- | --- | --- | --- | --- |
| `openai`（当前已落地） | `POST {base_url}/audio/speech` | Bearer | `{model, input, voice, speed, response_format}` | 二进制音频流 |

> 当前状态（2026-04-18）：仅 `tts_openai.py` 已落地。Azure Speech、ElevenLabs、火山语音、MiniMax Speech 等其他 TTS adapter 仍属预留规格，尚未接入 runtime。

#### 21.5.3 voice_service.py 改造要点

**当前状态（2026-04-18）**：

1. `VoiceService.generate_track()` 已支持双路径：
   - 有可用 OpenAI TTS 配置且 provider 已注册 TTS adapter → 创建 `status="processing"` 的轨道并返回 `kind="ai-voice"` 任务对象。
   - 无可用 TTS adapter、无配置、缺少必需 secret 或 base_url → 保持兼容 `status="blocked"` + `task=null`。
2. `ai-voice` 后台任务会调用 `dispatch_tts()`，并将音频落盘到 `{workspace}/voice/{track_id}.{format}`。
3. 后台任务成功后更新 `file_path`、`provider` 和 `status="ready"`；失败时更新 `status="failed"`。
4. `regenerate_segment()` 仍走 TaskBus 兼容任务对象，不做真实分段音频拼接或音频回写。

#### 21.5.4 TTS Provider 到 voice_id 映射

`VoiceProfile.provider` 已使用真实 provider ID；当前内建音色均为 `openai`。

| VoiceProfile.provider | voice_id 含义 | 示例 |
| --- | --- | --- |
| `openai` | OpenAI voice name | `alloy`、`nova`、`echo`、`shimmer` |
| 其他 provider | 各家 TTS voice 标识 | 仍属预留规格，待对应 TTS adapter 落地后启用 |

### 21.6 Provider 能力适配矩阵

> Codex 实现时以此表为 dispatch 依据。前端以此表控制 Provider 下拉选项。

> 当前状态（2026-04-18）：`dispatch_tts` 当前仅注册 `openai`。其余虽然在能力元数据中声明了 `tts` capability，但运行时若无已注册 TTS adapter，会在 `VoiceService.generate_track()` 侧回退为 `blocked`。

| Provider ID | text_generation | vision | tts | video_generation | asset_analysis | 协议族 |
| --- | --- | --- | --- | --- | --- | --- |
| `openai` | ✅ | ✅ | ✅ | — | — | `openai_responses` |
| `openai_compatible` | ✅ | ✅ | — | — | — | `openai_chat` |
| `anthropic` | ✅ | ✅ | — | — | — | `anthropic_messages` |
| `gemini` | ✅ | ✅ | — | — | ✅ | `gemini_generate` |
| `deepseek` | ✅ | — | — | — | — | `openai_chat` |
| `qwen` | ✅ | ✅ | — | — | — | `openai_chat` |
| `kimi` | ✅ | — | — | — | — | `openai_chat` |
| `zhipu` | ✅ | ✅ | — | — | — | `openai_chat` |
| `minimax` | ✅ | — | ✅ | — | — | `openai_chat` |
| `doubao` | ✅ | ✅ | ✅ | — | — | `openai_chat` |
| `baidu_qianfan` | ✅ | ✅ | — | — | — | `openai_chat` |
| `hunyuan` | ✅ | ✅ | — | — | — | `openai_chat` |
| `xai` | ✅ | — | — | — | — | `openai_chat` |
| `mistral` | ✅ | — | — | — | — | `openai_chat` |
| `cohere` | ✅ | — | — | — | — | `cohere_chat` |
| `openrouter` | ✅ | ✅ | — | — | — | `openai_chat` |
| `ollama` | ✅ | ✅ | — | — | — | `openai_chat` |
| `lm_studio` | ✅ | ✅ | — | — | — | `openai_chat` |
| `vllm` | ✅ | — | — | — | — | `openai_chat` |
| `localai` | ✅ | — | ✅ | — | — | `openai_chat` |
| `azure_speech` | — | — | ✅ | — | — | 专用 TTS |
| `elevenlabs` | — | — | ✅ | — | — | 专用 TTS |
| `volcengine_speech` | — | — | ✅ | — | — | 专用 TTS |
| `minimax_speech` | — | — | ✅ | — | — | 专用 TTS |

### 21.7 统一错误码扩展

AI 调用层新增以下 `error_code`，Codex 在服务层抛出，Gemini 在前端映射中文提示：

| error_code | HTTP Status | 中文提示 | 触发场景 |
| --- | --- | --- | --- |
| `ai_capability_disabled` | 400 | 当前 AI 能力已停用，请在设置中启用 | `capability.enabled == false` |
| `ai_provider_not_configured` | 400 | Provider API Key 尚未配置 | 当前 Provider `requires_secret=true` 且 `api_key` 为空 |
| `ai_provider_base_url_missing` | 400 | Provider Base URL 尚未配置 | `openai_compatible` 等需 base_url 的 provider |
| `ai_provider_unsupported` | 400 | 当前 Provider 不支持该能力类型 | Provider 不支持文本生成，或 `protocol_family` 未注册到文本 adapter registry |
| `ai_provider_auth_failed` | 502 | AI Provider 认证失败，请检查 API Key | 远端返回 401/403 |
| `ai_provider_rate_limited` | 502 | 请求频率超限，请稍后重试 | 远端返回 429 |
| `ai_provider_overloaded` | 502 | AI Provider 服务过载，请稍后重试 | 远端返回 529（Anthropic）/ 503 |
| `ai_provider_server_error` | 502 | AI Provider 服务异常 | 远端返回 5xx |
| `ai_provider_empty_response` | 502 | AI Provider 返回了空内容 | 解析结果为空 |
| `ai_provider_timeout` | 504 | AI Provider 响应超时 | 60s 超时 |
| `ai_provider_unreachable` | 502 | 无法连接 AI Provider，请检查网络 | `URLError` |
| `tts_provider_not_available` | 503 | TTS Provider 尚未接入 | 调用 `dispatch_tts()` 时当前 Provider 未注册 TTS adapter |

---

## 22. 前后端接口漂移修复清单（2026-04-24 已收口）

> 本节记录本轮已完成的前端代码与后端真实接口对齐项。后续若再次出现漂移，应继续在本节追加并同步测试。

### 22.1 Prompt 模板接口（已修复）

| 项 | 当前前端 | 后端真实接口 | 修复动作 |
| --- | --- | --- | --- |
| 更新方法 | `runtime-client.ts` 使用 `PUT` | 后端路由为 `PUT /api/prompt-templates/{template_id}` | 已对齐 |
| 请求字段 | `{ kind, name, description, content }` | `{ kind, name, description, content }` | 已对齐 |

### 22.2 M11 设备与工作区类型（已修复）

| 项 | 当前前端 | 后端真实接口 | 修复动作 |
| --- | --- | --- | --- |
| DTO 命名 | `DeviceWorkspaceDto`、`BrowserInstanceDto`、`BrowserInstanceWriteResultDto`、`AccountBindingDto` | 后端当前 schema | 已对齐 |
| Store / client 路径 | `workspaces/{ws_id}/browser-instances*` 嵌套路由 | 后端 canonical routes | 已对齐，legacy alias 仅作为后端兼容能力保留 |

### 22.3 M13 发布中心类型（已修复）

| 项 | 当前前端 | 后端真实接口 | 修复动作 |
| --- | --- | --- | --- |
| 发布回执 | `PublishReceiptDto` 阶段化结构 | 后端返回 `platform_response_json` + `received_at` | 已对齐 |
| 日历视图 | `PublishCalendarDto` 聚合对象 | 后端返回 `PublishCalendarDto` | 已对齐 |

### 22.4 M14 渲染导出（已修复）

| 项 | 当前前端 | 后端真实接口 | 修复动作 |
| --- | --- | --- | --- |
| 资源用量 | `RenderResourceUsageDto` 结构化对象 | 后端返回 `cpu/gpu/disk/collectedAt` | 已对齐 |
| 模板/Profile | `listRenderTemplates()` 返回 `ExportProfileDto[]` | 后端 `GET /api/renders/templates` 复用 `ExportProfileDto[]` | 已对齐 |

### 22.5 TaskBus WebSocket（前端兼容已修复）

| 项 | 当前前端 | 后端真实接口 | 修复动作 |
| --- | --- | --- | --- |
| `schema_version` | 前端对缺失字段的历史事件补齐 `schema_version: 1` | 全局约定所有 WS 消息必须带 `schema_version` | 前端兼容已补齐；后端仍建议持续发送显式版本 |
| `video_status_changed` | legacy event type 保留 | 历史事件，后端可能不再发送 | 保留兼容解析，不作为新事件类型扩展入口 |

### 22.6 AI 能力配置页面对齐

前端 AI 设置页面需要与 21.6 能力矩阵联动：

| 需求 | 说明 | Gemini 动作 |
| --- | --- | --- |
| Provider 选择器过滤 | 用户选择 `capability_id` 后，Provider 下拉只显示支持该能力的 Provider | 读取 `GET /api/settings/ai-providers/catalog` 返回的 `capabilities` 字段做过滤 |
| 模型选择器联动 | Provider 变更后，模型列表跟随切换 | 调用 `GET /api/settings/ai-providers/{provider_id}/models` 获取可用模型 |
| 健康状态展示 | 每个已配置 Provider 显示连通状态 | 调用 `POST /api/settings/ai-capabilities/providers/{provider_id}/health-check` |
| TTS Provider 区分 | TTS 能力配置时只展示 TTS Provider | 前端按 `capabilities` 包含 `"tts"` 过滤 |

---

## 23. 分阶段实施路线图

### Phase 0：Provider 适配器骨架（Codex · 优先级最高）

- [x] 创建 `apps/py-runtime/src/ai/providers/__init__.py` + `base.py`
- [x] 将现有 `_call_openai_responses` 迁移到 `openai_responses.py`
- [x] 将现有 `_call_openai_compatible_chat` 迁移到 `openai_chat.py`
- [x] 改造 `generate_text()` dispatch，改为使用 `ProviderRuntimeConfig.protocol_family` + `dispatch_text_generation(...)`
- [x] 确保现有 `openai` + `openai_compatible` 行为不变（回归测试）

### Phase 1：补齐三大商业 Provider（Codex）

- [x] 实现 `anthropic_messages.py`（按 21.3.3 规格）
- [x] 实现 `gemini_generate.py`（按 21.3.4 规格）
- [x] 实现 `cohere_chat.py`（按 21.3.5 规格）
- [x] 统一错误码（按 21.7 表）
- [x] 补齐 `tests/runtime/test_ai_providers.py` 单元测试

### Phase 2：TTS 调用层（Codex）

- [x] 实现 `TTSAdapter` 基类 + `tts_openai.py`（当前只落地 OpenAI TTS）
- [x] 改造 `voice_service.py`（按 21.5.3 要点）
- [x] `VoiceProfile.provider` 从占位 provider 改为真实 provider ID
- [ ] 后续逐个接入 Azure Speech / ElevenLabs / 火山 / MiniMax

### Phase 3：前端对齐（Gemini）

- [ ] 修复 22.1-22.5 所有接口漂移项
- [ ] AI 设置页面 Provider 选择器联动（按 22.6）
- [ ] TTS 页面接入真实音频播放（依赖 Phase 2 完成）

---

## 24. ProviderRuntimeConfig 完整字段参考

当前 `ProviderRuntimeConfig` dataclass（`ai_capability_service.py:38`）：

```python
@dataclass(frozen=True, slots=True)
class ProviderRuntimeConfig:
    provider: str                    # Provider ID，如 'anthropic'
    label: str                       # 展示名，如 'Anthropic'
    api_key: str | None              # API Key（已从 SecretStore 解密）
    base_url: str                    # 当前生效的 Base URL
    secret_source: str               # 'secure_store' | 'env' | 'none'
    requires_secret: bool            # 当前 Provider 是否必须配置 secret
    supports_text_generation: bool   # 是否支持文本生成
    supports_tts: bool               # 是否支持 TTS
    protocol_family: str             # 文本协议族 ID，供 dispatch 使用
```

> `requires_secret`、`supports_tts`、`protocol_family` 当前属于 runtime 内部元数据，用于服务层和 adapter dispatch，不直接外泄到现有 HTTP DTO。

---

> **文档版本**：2026-04-19 · review / workspace / subtitles / video-deconstruction / voice 契约对齐 · AI Provider 调用层架构定义首版 · 接口漂移清单 · 分阶段路线图
