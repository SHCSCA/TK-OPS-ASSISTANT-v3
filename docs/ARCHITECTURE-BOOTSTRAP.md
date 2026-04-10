# TK-OPS 实现骨架引导文档

| 字段 | 内容 |
| --- | --- |
| 文档版本 | 0.1.1 |
| 当前工程版本 | 0.1.1 |

## 1. 文档定位与优先级

### 1.1 文档定位

本文档是 TK-OPS 当前阶段的实现骨架真源，用于补齐 [docs/PRD.md](/Users/wz/Desktop/py/TK-OPS-ASSISTANT-v3/docs/PRD.md) 与 [docs/UI-DESIGN-PRD.md](/Users/wz/Desktop/py/TK-OPS-ASSISTANT-v3/docs/UI-DESIGN-PRD.md) 之间尚未固定的目录树、路由清单、模块边界和模型落点。

本文档不负责重新定义产品范围，也不负责替代 UI 视觉规范。它只回答四类问题：

- 新目录应该落在哪里。
- 16 个页面路由应该如何命名和归属。
- Runtime 的入口分组应该如何稳定切分。
- 核心持久化模型应该归属到哪里，并主要服务哪些页面与服务。

### 1.2 冲突处理顺序

当文档之间出现冲突时，按以下顺序处理：

1. 产品范围、页面目标、能力边界以 [docs/PRD.md](/Users/wz/Desktop/py/TK-OPS-ASSISTANT-v3/docs/PRD.md) 为准。
2. 视觉语言、壳层结构、页面布局、设计令牌以 [docs/UI-DESIGN-PRD.md](/Users/wz/Desktop/py/TK-OPS-ASSISTANT-v3/docs/UI-DESIGN-PRD.md) 为准。
3. 目录树、路由归属、模块责任、模型落点以本文档为准。
4. 协作流程、工程硬约束、交付规则以 [AGENTS.md](/Users/wz/Desktop/py/TK-OPS-ASSISTANT-v3/AGENTS.md) 为准。

### 1.3 文档边界

- 本轮只定义稳定命名、落点和边界，不定义数据库字段级 schema。
- 本轮只定义资源归属和路由分组，不扩展具体 endpoint 粒度。
- 本轮只定义目标目录骨架，不代表这些目录已经在仓库中落地。

## 2. 当前仓库现状与目标状态

### 2.1 当前仓库现状

当前仓库仍以文档、插件和本地虚拟环境为主，已经存在产品真源、UI 真源和协作手册，但尚未落地以下实现目录：

- `apps/desktop`
- `apps/py-runtime`
- `tests/desktop`
- `tests/runtime`
- `tests/contracts`

### 2.2 目标状态

后续实现必须统一落在新的实现骨架下，不回退到旧壳路径，也不在仓库根目录散落页面、脚本或业务模型。

重要说明：

- 下述目录树是未来目标结构，不代表当前仓库已经存在对应实现。
- 如果某条路径尚未创建，应在后续获批实现任务中按本文档创建。
- 不得因为目标目录尚未存在，就把新实现塞回旧目录、单文件脚本或历史壳层目录。

## 3. 目标目录树

### 3.1 顶层结构

```text
apps/
  desktop/
    src/
      app/
        router/
      layouts/
      pages/
      modules/
      components/
      stores/
      styles/
      types/
  py-runtime/
    src/
      api/
        routes/
      app/
      domain/
        models/
      services/
      repositories/
      schemas/
      tasks/
      media/
      ai/
        providers/
      persistence/
tests/
  desktop/
  runtime/
  contracts/
```

### 3.2 `apps/desktop` 目录责任

| 目录 | 责任 |
| --- | --- |
| `apps/desktop/src/app/router/` | 路由真源、路由清单、路由守卫、导航分组和路由级元信息。 |
| `apps/desktop/src/layouts/` | Tauri 桌面壳、页面模板、Title Bar、Sidebar、Detail Panel、Status Bar 等布局层。 |
| `apps/desktop/src/pages/` | 16 个正式页面的页面根组件，只承载页面装配，不堆积复杂业务逻辑。 |
| `apps/desktop/src/modules/` | 按业务域拆分的页面内模块、面板、可复用业务视图与 composables。 |
| `apps/desktop/src/components/` | 跨域共享的通用 UI 组件和基础交互组件。 |
| `apps/desktop/src/stores/` | Pinia 状态管理、全局上下文、任务广播、配置状态和项目上下文状态。 |
| `apps/desktop/src/styles/` | 全局样式入口、设计令牌、主题变量、排版和基础工具类。 |
| `apps/desktop/src/types/` | UI 类型、DTO 类型、路由类型和前端消费的协议类型，不重建持久化业务模型。 |

### 3.3 `apps/py-runtime` 目录责任

| 目录 | 责任 |
| --- | --- |
| `apps/py-runtime/src/api/routes/` | FastAPI 路由入口，按资源前缀分组注册，不在此处堆积业务流程。 |
| `apps/py-runtime/src/app/` | Runtime 启动、配置、依赖注入、日志初始化、应用级上下文。 |
| `apps/py-runtime/src/domain/models/` | SQLAlchemy 持久化实体和领域模型定义。 |
| `apps/py-runtime/src/services/` | 领域编排与应用服务，承接页面请求、任务调度和跨模型流程。 |
| `apps/py-runtime/src/repositories/` | 数据访问层，封装查询、写入和持久化细节。 |
| `apps/py-runtime/src/schemas/` | 请求响应 schema、DTO、序列化与反序列化对象。 |
| `apps/py-runtime/src/tasks/` | 长任务、队列任务、后台执行任务与重试流程。 |
| `apps/py-runtime/src/media/` | 渲染、转码、拼接、封面导出、字幕烧录等媒体流水线。 |
| `apps/py-runtime/src/ai/providers/` | AI Provider 适配层，按能力接口接入脚本、视频、TTS、字幕和资产分析能力。 |
| `apps/py-runtime/src/persistence/` | 数据库引擎、会话、迁移入口、存储初始化和持久化基础设施。 |

### 3.4 `tests` 目录责任

| 目录 | 责任 |
| --- | --- |
| `tests/desktop/` | 路由、页面装配、状态管理、交互契约和前端关键链路测试。 |
| `tests/runtime/` | Runtime 路由、服务、模型、任务和媒体链路测试。 |
| `tests/contracts/` | 前后端协议契约测试，覆盖 JSON 信封、路由映射、资源前缀和关键 DTO 对齐。 |

## 4. 前端路由清单与路由契约

### 4.1 路由真源位置

前端路由真源建议统一放在：

- `apps/desktop/src/app/router/route-manifest.ts`
- `apps/desktop/src/app/router/route-ids.ts`
- `apps/desktop/src/app/router/guards/`

### 4.2 `RouteManifestItem` 契约

`RouteManifestItem` 是前端路由的稳定契约，后续页面实现和导航系统必须基于这组字段，不在页面内另起一套命名。

```ts
type RouteManifestItem = {
  id: string
  path: string
  title: string
  navGroup: string
  icon: string
  pageType: string
  requiresLicense: boolean
  requiresProjectContext: boolean
  detailPanelMode: string
  statusBarMode: string
  componentImport: string
}
```

字段说明：

| 字段 | 含义 |
| --- | --- |
| `id` | 稳定路由标识，供导航、权限、状态恢复和日志使用。 |
| `path` | 路由 URL，后续不应随意变更。 |
| `title` | 页面中文名称。 |
| `navGroup` | Sidebar 顶层分组，必须与 UI 真源一致。 |
| `icon` | 图标系统中的稳定图标标识。 |
| `pageType` | 页面类型，如 `wizard`、`dashboard`、`editor`、`workspace`、`queue`、`settings`。 |
| `requiresLicense` | 是否要求通过授权校验后才能进入。 |
| `requiresProjectContext` | 是否要求已有当前项目上下文。 |
| `detailPanelMode` | Detail Panel 默认模式，如 `hidden`、`contextual`、`asset`、`binding`、`logs`、`settings`。 |
| `statusBarMode` | Status Bar 默认模式，如 `setup`、`overview`、`editing`、`tasks`、`publishing`、`rendering`、`review`、`system`。 |
| `componentImport` | 页面组件建议导入路径，供路由懒加载和实现命名参考。 |

### 4.3 16 个正式路由清单

导航分组必须与 [docs/UI-DESIGN-PRD.md](/Users/wz/Desktop/py/TK-OPS-ASSISTANT-v3/docs/UI-DESIGN-PRD.md) 当前口径保持一致：

- 启动与总览
- 创作前置
- 创作与媒体
- 执行与治理
- 系统与 AI

| Route ID | Path | 页面名称 | 导航分组 | 页面组件命名规范 | `componentImport` |
| --- | --- | --- | --- | --- | --- |
| `setup_license_wizard` | `/setup/license` | 首启与许可证向导 | 启动与总览 | `SetupLicenseWizardPage.vue` | `@/pages/setup/SetupLicenseWizardPage.vue` |
| `creator_dashboard` | `/dashboard` | 创作总览 | 启动与总览 | `CreatorDashboardPage.vue` | `@/pages/dashboard/CreatorDashboardPage.vue` |
| `script_topic_center` | `/scripts/topics` | 脚本与选题中心 | 创作前置 | `ScriptTopicCenterPage.vue` | `@/pages/scripts/ScriptTopicCenterPage.vue` |
| `storyboard_planning_center` | `/storyboards/planning` | 分镜规划中心 | 创作前置 | `StoryboardPlanningCenterPage.vue` | `@/pages/storyboards/StoryboardPlanningCenterPage.vue` |
| `ai_editing_workspace` | `/workspace/editing` | AI 剪辑工作台 | 创作与媒体 | `AIEditingWorkspacePage.vue` | `@/pages/workspace/AIEditingWorkspacePage.vue` |
| `video_deconstruction_center` | `/video/deconstruction` | 视频拆解中心 | 创作前置 | `VideoDeconstructionCenterPage.vue` | `@/pages/video/VideoDeconstructionCenterPage.vue` |
| `voice_studio` | `/voice/studio` | 配音中心 | 创作与媒体 | `VoiceStudioPage.vue` | `@/pages/voice/VoiceStudioPage.vue` |
| `subtitle_alignment_center` | `/subtitles/alignment` | 字幕对齐中心 | 创作与媒体 | `SubtitleAlignmentCenterPage.vue` | `@/pages/subtitles/SubtitleAlignmentCenterPage.vue` |
| `asset_library` | `/assets/library` | 资产中心 | 创作与媒体 | `AssetLibraryPage.vue` | `@/pages/assets/AssetLibraryPage.vue` |
| `account_management` | `/accounts` | 账号管理 | 执行与治理 | `AccountManagementPage.vue` | `@/pages/accounts/AccountManagementPage.vue` |
| `device_workspace_management` | `/devices/workspaces` | 设备与工作区管理 | 执行与治理 | `DeviceWorkspaceManagementPage.vue` | `@/pages/devices/DeviceWorkspaceManagementPage.vue` |
| `automation_console` | `/automation/console` | 自动化执行中心 | 执行与治理 | `AutomationConsolePage.vue` | `@/pages/automation/AutomationConsolePage.vue` |
| `publishing_center` | `/publishing/center` | 发布中心 | 执行与治理 | `PublishingCenterPage.vue` | `@/pages/publishing/PublishingCenterPage.vue` |
| `render_export_center` | `/renders/export` | 渲染与导出中心 | 创作与媒体 | `RenderExportCenterPage.vue` | `@/pages/renders/RenderExportCenterPage.vue` |
| `review_optimization_center` | `/review/optimization` | 复盘与优化中心 | 执行与治理 | `ReviewOptimizationCenterPage.vue` | `@/pages/review/ReviewOptimizationCenterPage.vue` |
| `ai_system_settings` | `/settings/ai-system` | AI 与系统设置 | 系统与 AI | `AISystemSettingsPage.vue` | `@/pages/settings/AISystemSettingsPage.vue` |

### 4.4 路由实现约束

- 所有正式页面都必须出现在统一路由清单中。
- 页面组件命名统一采用 `PascalCase + Page.vue`。
- `apps/desktop/src/pages/` 下只放页面根组件，不在页面根组件内重建完整业务域。
- 页面级复杂逻辑优先下沉到 `apps/desktop/src/modules/`、`apps/desktop/src/stores/` 和 Runtime 服务层。
- 未经文档更新，不得新增第 17 个正式页面，也不得随意拆出平级主路由。

## 5. Runtime 模块边界与 API 前缀

### 5.1 统一协议约束

Runtime 返回协议继续沿用 [docs/PRD.md](/Users/wz/Desktop/py/TK-OPS-ASSISTANT-v3/docs/PRD.md) 已确定的统一 JSON 信封：

- 成功：`{ "ok": true, "data": ... }`
- 失败：`{ "ok": false, "error": "..." }`

本文档不发明第二套返回协议。

### 5.2 API 前缀分组

下列前缀只定义资源归属和路由边界，不在本轮展开字段级 schema 或 endpoint 细节。

| API 前缀 | 资源归属 | 主要服务页面或能力 |
| --- | --- | --- |
| `/api/license` | 授权激活、校验、受限模式、机器绑定 | `setup_license_wizard` |
| `/api/dashboard` | 仪表总览、最近项目、待办、健康摘要 | `creator_dashboard` |
| `/api/scripts` | 选题、标题、脚本、文案、版本 | `script_topic_center` |
| `/api/storyboards` | 分镜、镜头规划、节奏、脚本映射 | `storyboard_planning_center` |
| `/api/workspace` | 时间线、片段编排、工作台状态 | `ai_editing_workspace` |
| `/api/video-deconstruction` | 导入视频、转写、切段、结构拆解 | `video_deconstruction_center` |
| `/api/voice` | TTS、音色、试音、音轨版本 | `voice_studio` |
| `/api/subtitles` | 字幕生成、对齐、样式、时间码校正 | `subtitle_alignment_center` |
| `/api/assets` | 资产检索、引用、版本、预览 | `asset_library` |
| `/api/accounts` | 账号对象、分组、状态、绑定关系 | `account_management` |
| `/api/devices` | 工作区、浏览器实例、健康检查、执行环境 | `device_workspace_management` |
| `/api/automation` | 采集、回复、同步、校验和队列任务 | `automation_console` |
| `/api/publishing` | 发布计划、预检、执行、回执 | `publishing_center` |
| `/api/renders` | 渲染任务、导出配置、转码与恢复 | `render_export_center` |
| `/api/review` | 复盘摘要、异常回看、优化建议 | `review_optimization_center` |
| `/api/settings` | Provider、模型、目录、日志、系统配置 | `ai_system_settings` |

### 5.3 Runtime 模块边界

为避免把 FastAPI 路由层写成巨型业务文件，后续实现必须遵守以下分层：

1. `api/routes/` 只做入参接收、出参返回、错误转换和服务调用。
2. `services/` 负责业务流程、任务编排和跨模型协同。
3. `repositories/` 负责数据库读写和查询封装。
4. `tasks/` 负责长任务执行、重试、队列与恢复。
5. `media/` 负责渲染、转码和文件导出能力。
6. `ai/providers/` 负责多 Provider 适配和能力路由。

## 6. 核心模型清单与归属

### 6.1 核心原则

- 持久化业务模型统一放在 `apps/py-runtime/src/domain/models/`。
- 前端只维护对应 UI 类型和 DTO 类型，统一放在 `apps/desktop/src/types/`，不在页面层重建另一套持久化模型。
- 页面消费 Runtime 返回的结构化对象，不直接拼接底层实体字段。

### 6.2 核心模型表

| 模型 | 归属目录 | 主要职责 | 主要被哪些页面或服务消费 |
| --- | --- | --- | --- |
| `Project` | `apps/py-runtime/src/domain/models/` | 作为项目根对象聚合创作上下文、任务、版本和资产引用。 | `creator_dashboard`、`script_topic_center`、`storyboard_planning_center`、`ai_editing_workspace`、`review_optimization_center`、`ProjectService` |
| `Script` | `apps/py-runtime/src/domain/models/` | 保存脚本正文、标题、文案、版本和来源信息。 | `script_topic_center`、`storyboard_planning_center`、`ScriptService`、`AI ScriptProvider` |
| `Storyboard` | `apps/py-runtime/src/domain/models/` | 保存分镜结构、镜头节奏、视觉提示和脚本映射。 | `storyboard_planning_center`、`ai_editing_workspace`、`StoryboardService` |
| `Timeline` | `apps/py-runtime/src/domain/models/` | 管理时间线工程、轨道关系、片段编排和导出上下文。 | `ai_editing_workspace`、`render_export_center`、`TimelineService` |
| `VoiceTrack` | `apps/py-runtime/src/domain/models/` | 管理 TTS 或导入音轨、音色版本和时间线音频引用。 | `voice_studio`、`ai_editing_workspace`、`VoiceService` |
| `SubtitleTrack` | `apps/py-runtime/src/domain/models/` | 管理字幕段、时间码、样式、版本和对齐状态。 | `subtitle_alignment_center`、`ai_editing_workspace`、`SubtitleService` |
| `Asset` | `apps/py-runtime/src/domain/models/` | 管理视频、图片、音频、封面和模板等资产对象。 | `asset_library`、`ai_editing_workspace`、`video_deconstruction_center`、`AssetService` |
| `Account` | `apps/py-runtime/src/domain/models/` | 表示 TikTok 账号对象、分组、状态和发布目标。 | `account_management`、`publishing_center`、`automation_console`、`AccountService` |
| `DeviceWorkspace` | `apps/py-runtime/src/domain/models/` | 表示真实 PC 工作区、浏览器实例和执行环境。 | `device_workspace_management`、`publishing_center`、`automation_console`、`DeviceWorkspaceService` |
| `ExecutionBinding` | `apps/py-runtime/src/domain/models/` | 连接账号、设备工作区与执行任务的稳定绑定关系。 | `account_management`、`device_workspace_management`、`publishing_center`、`automation_console`、`ExecutionBindingService` |
| `AutomationTask` | `apps/py-runtime/src/domain/models/` | 表示采集、回复、同步、校验等自动化任务。 | `automation_console`、`review_optimization_center`、`AutomationService`、`AutomationTaskRunner` |
| `PublishPlan` | `apps/py-runtime/src/domain/models/` | 表示发布计划、发布时间、预检结果和目标账号。 | `publishing_center`、`account_management`、`PublishingService` |
| `RenderTask` | `apps/py-runtime/src/domain/models/` | 表示渲染、转码、导出任务与其状态流转。 | `render_export_center`、`ai_editing_workspace`、`RenderService`、`MediaPipelineService` |
| `LicenseGrant` | `apps/py-runtime/src/domain/models/` | 表示许可证授权状态、机器绑定和校验记录。 | `setup_license_wizard`、`AISystemSettings` 诊断区、`LicenseService` |
| `AIJobRecord` | `apps/py-runtime/src/domain/models/` | 记录 AI 调用能力、模型、耗时、结果状态和失败原因。 | `script_topic_center`、`voice_studio`、`subtitle_alignment_center`、`review_optimization_center`、`AIOrchestrationService` |

### 6.3 前端类型约束

前端只允许维护以下类型层：

- 路由类型：放在 `apps/desktop/src/types/router/`
- UI 视图模型：放在 `apps/desktop/src/types/view-models/`
- Runtime DTO：放在 `apps/desktop/src/types/dto/`
- 共享状态类型：放在 `apps/desktop/src/types/state/`

前端不应做的事：

- 不在 `pages/` 内定义持久化业务模型。
- 不在多个页面里重复定义 `Project`、`Timeline`、`Account` 等核心对象。
- 不让页面自己推断实体归属关系，而应统一复用 DTO 和 store。

## 7. V1 必做与预留

### 7.1 V1 必做

以下内容属于 V1 首期必须固定的实施骨架：

- 16 个正式页面路由与稳定 `Route ID`
- `apps/desktop` 与 `apps/py-runtime` 的基础目录树
- `RouteManifestItem` 这组稳定路由字段
- Runtime 16 组资源前缀
- 15 个核心持久化模型及其落点归属
- 前端只维护 UI/DTO 类型、Runtime 持有持久化模型的边界

### 7.2 预留但本轮不落地

以下内容只保留扩展位，不作为本轮必须交付项：

- 更重的媒体内核升级位
- TikTok 之外的多平台扩展位
- 更多 AI Provider 和模型适配位
- 更细的 schema 字段和 endpoint 粒度
- 更复杂的任务调度策略和分布式执行能力

### 7.3 执行约束

- 预留位不能被误当成 V1 首期交付承诺。
- 新增目录、路由、模型前，先检查是否已被本文档固定。
- 如果后续实现需要扩展正式页面、资源前缀或核心模型，应先更新本文档，再进入实现。

## 8. 文档验收检查表

在后续实现或继续扩展本文档前，应至少检查：

1. `docs/ARCHITECTURE-BOOTSTRAP.md` 是否作为实现骨架真源被引用。
2. 正式路由数量是否仍为 16。
3. 路由 ID 是否与 [docs/PRD.md](/Users/wz/Desktop/py/TK-OPS-ASSISTANT-v3/docs/PRD.md) 完全一致。
4. 导航分组是否与 [docs/UI-DESIGN-PRD.md](/Users/wz/Desktop/py/TK-OPS-ASSISTANT-v3/docs/UI-DESIGN-PRD.md) 当前分组一致。
5. 文档是否明确说明“目标目录树是未来结构，不代表当前仓库已落地”。
6. 是否坚持沿用 [docs/PRD.md](/Users/wz/Desktop/py/TK-OPS-ASSISTANT-v3/docs/PRD.md) 中既有 JSON 信封，而没有发明第二套返回协议。
7. 每个核心模型是否都能在本文档里找到明确归属目录和主要消费者。
