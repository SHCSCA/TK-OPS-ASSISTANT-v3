# TK-OPS 实现骨架引导文档

## 1. 文档定位

本文是 TK-OPS 当前阶段的实现骨架真源，只定义目标目录、路由、模块职责、Runtime 资源边界和核心模型落点。产品范围以 `docs/PRD.md` 为准，视觉与布局以 `docs/UI-DESIGN-PRD.md` 为准，工程约束以 `AGENTS.md` 为准。

本文取代旧的 16 页路由与 `Timeline` 中枢架构。脚本与选题、分镜规划和视频拆解允许按当前账号工作区边界迁移回新路由；AI 剪辑工作台、手动多轨时间线和其余旧页面树不得重新接入。

## 2. 技术主线

- 桌面壳：Tauri 2 + Vue 3 + TypeScript + Vite。
- 前端状态与路由：Pinia + Vue Router。
- 业务 Runtime：Python + FastAPI + SQLAlchemy + Alembic。
- 本地数据：SQLite + 账号范围的本地工作区目录。
- 通信：HTTP 获取当前状态，WebSocket 推送任务与状态变化。
- 媒体流水线：独立生成、转码、字幕烧录、封面与自动合成服务。
- AI：多 Provider 能力适配层。

## 3. 目录边界

新生产实现只允许落在：

- `apps/desktop`
- `apps/py-runtime`
- `tests`
- `docs`

`desktop_app/` 只可作为迁移和历史模型参考，不得重新进入运行、联调、打包或发布链路。

### 3.1 Desktop 目标结构

```text
apps/desktop/src/
├── app/
│   ├── router/
│   ├── runtime-client/
│   └── account-context/
├── layouts/
│   └── account-workspace/
├── pages/
│   ├── setup/
│   ├── workspace-home/
│   ├── strategy-knowledge/
│   ├── script-topic/
│   ├── storyboard-planning/
│   ├── video-deconstruction/
│   ├── batch-production/
│   ├── content-library/
│   ├── media-toolbox/
│   ├── publishing/
│   ├── review/
│   └── settings/
├── modules/
│   ├── accounts/
│   ├── ai-recipes/
│   ├── knowledge/
│   ├── planning/
│   ├── scripts/
│   ├── storyboards/
│   ├── video-deconstruction/
│   ├── media-tools/
│   ├── production/
│   ├── composition/
│   ├── publishing/
│   ├── review/
│   └── system/
├── components/
├── composables/
├── stores/
├── styles/
└── types/
```

页面状态、服务调用、helpers、types 和 styles 必须按职责拆分。组件不得直接 `fetch`，所有请求统一通过 Runtime 适配层。

### 3.2 Runtime 目标结构

```text
apps/py-runtime/src/
├── api/
│   ├── routes/
│   ├── dependencies/
│   └── websocket/
├── app/
├── domain/
│   └── models/
├── services/
│   ├── accounts/
│   ├── ai-recipes/
│   ├── provider-profiles/
│   ├── model-profiles/
│   ├── prompt-profiles/
│   ├── capability-routes/
│   ├── composition-templates/
│   ├── knowledge/
│   ├── planning/
│   ├── scripts/
│   ├── storyboards/
│   ├── video-deconstruction/
│   ├── media-tools/
│   ├── assets/
│   ├── production/
│   ├── composition/
│   ├── publishing/
│   └── review/
├── repositories/
├── schemas/
├── tasks/
├── media/
├── ai/
│   └── providers/
├── persistence/
├── config/
├── logging/
└── errors/
```

UI 只表达状态和意图。账号隔离、业务规则、事务、缓存失效、任务编排和错误转换必须在 Runtime 服务层完成。

P0-A 已落地的数据库启动骨架：

```text
apps/py-runtime/src/
├── app/
│   ├── config.py
│   ├── factory.py
│   ├── lifecycle.py
│   └── logging.py
├── config/
│   ├── database.py
│   └── migration.py
└── persistence/migration/
    ├── legacy_baseline.py
    ├── fingerprint.py
    ├── lock.py
    ├── backup.py
    ├── runner.py
    └── target_*.py
```

该骨架是正式生产启动路径，不得重新合并回 `persistence/engine.py` 或启动时隐式 repair。

## 4. 路由真源

### 4.1 Route IDs

```ts
export const routeIds = {
  setupLicenseWizard: "setup_license_wizard",
  accountWorkspaceHome: "account_workspace_home",
  accountStrategyKnowledge: "account_strategy_knowledge",
  accountScriptTopic: "account_script_topic",
  accountStoryboardPlanning: "account_storyboard_planning",
  accountVideoDeconstruction: "account_video_deconstruction",
  accountBatchProduction: "account_batch_production",
  accountContentLibrary: "account_content_library",
  accountMediaToolbox: "account_media_toolbox",
  accountPublishing: "account_publishing",
  accountReview: "account_review",
  accountManagement: "account_management",
  aiSystemSettings: "ai_system_settings"
} as const;
```

### 4.2 路由表

| Route ID | URL | 页面组件 | 账号要求 |
| --- | --- | --- | --- |
| `setup_license_wizard` | `/setup/license` | `pages/setup/SetupLicenseWizardPage.vue` | 否 |
| `account_workspace_home` | `/workspace` | `pages/workspace-home/AccountWorkspaceHomePage.vue` | 是 |
| `account_strategy_knowledge` | `/strategy-knowledge` | `pages/strategy-knowledge/AccountStrategyKnowledgePage.vue` | 是 |
| `account_script_topic` | `/scripts` | `pages/script-topic/AccountScriptTopicPage.vue` | 是 |
| `account_storyboard_planning` | `/storyboards` | `pages/storyboard-planning/AccountStoryboardPlanningPage.vue` | 是 |
| `account_video_deconstruction` | `/video-deconstruction` | `pages/video-deconstruction/AccountVideoDeconstructionPage.vue` | 是 |
| `account_batch_production` | `/production/batches` | `pages/batch-production/AccountBatchProductionPage.vue` | 是 |
| `account_content_library` | `/content-library` | `pages/content-library/AccountContentLibraryPage.vue` | 是 |
| `account_media_toolbox` | `/media-tools` | `pages/media-toolbox/AccountMediaToolboxPage.vue` | 是 |
| `account_publishing` | `/publishing` | `pages/publishing/AccountPublishingPage.vue` | 是 |
| `account_review` | `/review` | `pages/review/AccountReviewPage.vue` | 是 |
| `account_management` | `/settings/accounts` | `pages/settings/accounts/AccountManagementPage.vue` | 否 |
| `ai_system_settings` | `/settings/ai-system` | `pages/settings/AISystemSettingsPage.vue` | 否 |

### 4.3 路由守卫

路由进入顺序：

1. 检查许可证与 Runtime 初始化。
2. 系统页可在无当前账号时打开。
3. 账号工作区页面要求有效 `current_account_id`。
4. 当前账号失效时进入账号选择状态，不自动使用任意其他账号。
5. 账号切换后恢复该账号最近页面；无记录时进入 `/workspace`。

旧 Route IDs 和 URL 只能提供一次性迁移重定向，不得继续承载业务页面。

## 5. Account Context

### 5.1 前端上下文

统一 `AccountContextStore` 至少持有：

- `currentAccountId`
- `switchStatus`
- `lastRouteByAccount`
- `accountRevision`
- `pendingUnsavedGuard`
- `subscriptionRevision`

账号切换事务：

```text
检查未保存状态
→ 保存 / 放弃 / 取消
→ 进入 switching
→ 取消旧账号可见请求
→ 清理页面级选中与 AI 上下文
→ 切换 Runtime account scope
→ 重建缓存键与 WebSocket 订阅
→ 拉取目标账号壳层数据
→ 恢复目标账号最近页面
→ 退出 switching
```

切换失败时保留原账号工作区，并显示中文错误、日志入口和重试。

### 5.2 Runtime 范围

所有账号级 API 必须从路径或强类型请求上下文获得 `account_id`。禁止由页面在请求体中随意覆盖授权范围。

仓储方法必须显式接收 `account_id`，例如：

```python
async def list_batches(account_id: UUID, filters: BatchFilters) -> list[ProductionBatch]:
    ...
```

缓存键、任务关联、日志字段、文件目录和 WebSocket 主题必须包含同一账号范围。

### 5.3 账号状态机

账号状态只允许以下转换：

```text
draft -> unbound -> ready
unbound <-> attention
ready <-> attention
draft | unbound | ready | attention -> archived
archived -> unbound | ready | attention
```

归档只改变账号可用状态，不删除内容、知识来源、任务日志或发布记录。恢复时必须重新执行授权、工作区、知识库和 Provider 健康检查，再决定目标状态。账号配置复制由服务层生成新账号草稿，只复制白名单字段，禁止复制授权、凭据、绑定和历史实体。

## 6. Runtime API 资源边界

所有接口使用 `/api/v1` 版本前缀。

| 前缀 | 职责 |
| --- | --- |
| `/api/v1/bootstrap` | 许可证、目录初始化、Runtime 与媒体工具健康 |
| `/api/v1/accounts` | 真实账号列表、创建草稿、状态、切换准备与账号级摘要 |
| `/api/v1/accounts/{account_id}/connection` | 真实账号授权、工作区、浏览器实例与执行绑定健康 |
| `/api/v1/accounts/{account_id}/ai-recipe` | 账号 AI 创作档案、继承来源、校验与版本 |
| `/api/v1/accounts/{account_id}/publish-defaults` | 账号发布默认值与约束 |
| `/api/v1/accounts/{account_id}/positioning` | 定位版本与发布约束 |
| `/api/v1/accounts/{account_id}/knowledge` | 来源、索引、规则、快照与引用 |
| `/api/v1/accounts/{account_id}/plans` | 内容计划、栏目、选题与节奏 |
| `/api/v1/accounts/{account_id}/content-items` | 创作前内容对象、选题来源、采用状态与版本摘要 |
| `/api/v1/accounts/{account_id}/scripts` | 策划简报、脚本版本、AI 作业、采用与恢复 |
| `/api/v1/accounts/{account_id}/storyboards` | 脚本版本引用、分镜版本、镜头重生成、采用与同步 |
| `/api/v1/accounts/{account_id}/video-deconstructions` | 视频来源、阶段任务、脚本 / 关键词 / 关键帧 / 结构结果与选择性回流 |
| `/api/v1/accounts/{account_id}/batches` | 批次创建、队列项、阶段、取消、重试、单条生产与确认 |
| `/api/v1/accounts/{account_id}/contents` | 内容变体、视频 / 图片 / 音频 / 文档资产、用途、来源和版本 |
| `/api/v1/accounts/{account_id}/media-tool-tasks` | 媒体工具任务、权利确认、进度、取消、重试与输出 |
| `/api/v1/accounts/{account_id}/publishing` | 预检、排期、执行、回执与重试 |
| `/api/v1/accounts/{account_id}/review` | 真实表现、建议、证据与回流动作 |
| `/api/v1/system/providers` | Provider Profile、凭据引用、连接健康与系统默认 |
| `/api/v1/system/models` | Provider 下的真实模型、启停、发现、手动录入与基础限制 |
| `/api/v1/system/model-capabilities` | 供应商声明能力、适配器已接入能力、契约验证、来源、模式、参数边界与可用性 |
| `/api/v1/system/capability-routes` | 产品 AI 能力到主模型、回退模型和 Prompt 的系统映射 |
| `/api/v1/system/prompt-profiles` | 版本化系统提示、任务模板、变量、输出 Schema、视觉风格前缀与引用 |
| `/api/v1/system/composition-templates` | 受控合成模板、类型、画幅、参数 Schema、预览与兼容能力 |
| `/api/v1/system/media-tools` | 工具能力注册、依赖健康、支持输入输出与风险边界 |
| `/api/v1/system` | 配置总线、工作区、执行环境、日志与诊断 |

生产实现时必须在 `docs/api/v1/` 维护唯一接口文档，包含地址、方法、参数、返回、错误码和示例。

## 7. WebSocket 与任务

WebSocket 使用账号范围主题：

- `account:{account_id}:tasks`
- `account:{account_id}:creative`
- `account:{account_id}:video-deconstructions`
- `account:{account_id}:media-tools`
- `account:{account_id}:batches`
- `account:{account_id}:publishing`
- `system:health`
- `system:providers`
- `system:ai-config`

账号切换时取消旧账号可见订阅并建立新订阅。旧账号任务不取消，只从当前可见视图移除。重连后必须按 `last_event_id` 补拉，随后通过 HTTP 获取最终状态快照。

统一任务状态：

- `queued`
- `running`
- `cancelling`
- `failed`
- `completed`

每个长任务包含超时、取消、阶段、进度、关联对象、日志引用、最小重试范围和最终结果。

AI 生成进度事件至少包含 `event_type`、`progress`、`item_current`、`item_total`、`step`、`action` 和 `extra_info`。批次聚合器负责把镜头级进度换算为任务级进度；并发结果必须按镜头索引归并，单镜头失败不得覆盖其他镜头产物。

## 8. 领域模型落点

| 模型 | 主要职责 |
| --- | --- |
| `Account` | 真实 TikTok 账号与账号级工作区根对象 |
| `AccountConnection` | 授权、工作区、浏览器实例、执行环境与健康状态 |
| `PositioningProfile` | 受众、内容支柱、表达风格与版本 |
| `AccountKnowledgeBase` | 账号独立知识空间与索引配置 |
| `KnowledgeSource` | 来源、状态、版本、校验与引用 |
| `KnowledgeSnapshot` | 生成任务使用的不可变知识快照 |
| `BrandKit` | 品牌事实、视觉资产、CTA 和发布约束 |
| `AccountAIRecipe` | 账号默认模型、风格、音色、模板、成本与回退策略 |
| `AccountPublishDefaults` | 账号语言、时区、节奏和发布约束默认值 |
| `ProviderProfile` | 系统级 Provider 连接、凭据引用与默认策略 |
| `ModelProfile` | Provider 下的真实模型 ID、显示名、启用状态与基础限制 |
| `ModelCapability` | 供应商声明能力、适配器已接入能力、契约验证、来源、参数边界和已知限制 |
| `PromptProfile` | 版本化系统提示、任务模板、变量、输出 Schema、视觉风格前缀与引用 |
| `CapabilityRoute` | 产品 AI 能力到主模型、回退模型和 Prompt 的系统映射 |
| `CompositionTemplateProfile` | 合成模板类型、画幅、参数 Schema、预览、兼容能力和版本 |
| `GenerationRun` | 单个批次的 AI 执行记录、配方版本与总用量 |
| `GenerationStep` | 脚本、分镜、媒体、TTS、字幕和合成节点记录 |
| `AIUsageRecord` | Provider、模型、耗时、成本、结果和错误关联 |
| `ContentPlan` | 栏目、选题矩阵、节奏与批次入口 |
| `ContentItem` | 单条内容的创作前对象，关联选题简报、脚本版本、分镜版本、来源和生产引用 |
| `TopicBrief` | 选题标题、内容支柱、受众、角度、目标时长、来源和标签 |
| `Script` | 策划简报、正文、结构、修订和采用记录 |
| `Storyboard` | 已采用脚本引用、镜头计划、修订和采用记录 |
| `VideoDeconstruction` | 账号级视频来源、阶段状态、Provider、日志与回流状态 |
| `DeconstructionResult` | 带时间码的脚本、分组关键词、关键帧、结构段和来源证据 |
| `MediaToolDefinition` | 系统级工具能力、输入输出、依赖、风险和可用性声明 |
| `MediaToolTask` | 账号级工具任务、权利确认、配置快照、状态、输出和错误 |
| `ProductionBatch` | 批量任务聚合、阶段、策略和日志 |
| `BatchEntry` | 批次内单条执行队列项、就绪状态、阻断原因和输出引用 |
| `ContentVariant` | 单条可发布内容的聚合根 |
| `ContentItemReference` | 批次内容使用的脚本、分镜和知识快照不可变引用 |
| `Asset` | 视频、图片、音频或文档资产，以及用途、来源、状态、版本和业务引用 |
| `CompositionSpec` | Runtime 内部自动合成规则，不对应手动时间线 UI |
| `VoiceTrack` | 配音文件、音色、版本与段落映射 |
| `SubtitleTrack` | 字幕内容、样式、对齐结果与版本 |
| `RenderTask` | 自动合成、字幕烧录、封面、转码与输出 |
| `PublishTask` | 预检、排期、执行、回执与重试 |
| `DeviceWorkspace` | 真实 PC 工作区与文件边界 |
| `ExecutionBinding` | 账号、工作区、浏览器实例和执行环境绑定 |
| `PerformanceSnapshot` | 真实发布表现和来源时间 |

所有账号级模型必须有 `account_id`、创建与更新时间、版本或修订号。生成结果还必须包含定位版本、知识快照、Provider 和策略版本。

## 9. 服务边界

- `AccountLifecycleService`：创建草稿、真实连接、状态转换、配置复制、归档与恢复。
- `AccountContextService`：切换准备、账号摘要和隔离验证。
- `PositioningService`：定位版本、校验和回退。
- `KnowledgeService`：来源导入、索引、冲突检测、快照和引用。
- `ContentPlanningService`：栏目、选题矩阵、节奏和计划状态。
- `ContentItemService`：单条创作对象、选题来源、阶段、版本摘要和生产引用。
- `ScriptWorkflowService`：策划简报、脚本生成 / 改写、版本、采用、比较和恢复。
- `StoryboardWorkflowService`：脚本引用、分镜生成、镜头级重生成、版本、同步和采用。
- `VideoDeconstructionService`：视频来源、解析 / 转录、关键词、分段、结构提取、标准结果和选择性回流。
- `MediaToolRegistry`：工具定义、依赖健康、输入输出与风险边界。
- `MediaToolTaskService`：权利确认、任务创建、超时、取消、重试、输出资产和日志。
- `AssetService`：账号资产类型、用途、来源、版本、缩略图、可用性、引用和工具输出入库。
- `BatchProductionService`：建批、队列项、单条生产、阶段编排、取消、重试和确认。
- `AIRecipeService`：系统默认、账号配方、批次覆盖、校验和版本。
- `ProviderProfileService`：系统 Provider、凭据引用、连接测试和健康状态。
- `ModelProfileService`：模型发现、手动录入、启停、基础限制和 Provider 归属。
- `ModelCapabilityRegistry`：供应商声明与适配器能力归一、契约来源、验证状态、刷新、查询和参数边界校验。
- `PromptProfileService`：Prompt 版本、变量、Schema、预览、引用关系和未保存冲突校验。
- `CapabilityRouteService`：产品能力主模型、回退模型、Prompt、就绪状态和受影响页面解析。
- `CompositionTemplateService`：模板清单、类型、画幅、参数 Schema、预览、兼容性和版本。
- `ContentVariantService`：脚本、分镜、版本和审核状态。
- `CompositionService`：镜头、配音、字幕、封面和自动合成。
- `PublishingService`：真实绑定、预检、执行、回执和恢复。
- `ReviewService`：表现证据、建议和显式回流。
- `ConfigurationBus`：系统配置与账号覆盖项。
- `TaskBus`：长任务、状态广播、日志和重试。

事务边界由服务层显式控制。失败必须回滚并使用 `log.exception(...)` 记录，同时转换为安全的中文错误。

## 10. Provider 接口

- `ScriptProvider`
- `ImageGenerationProvider`
- `VideoGenerationProvider`
- `TTSProvider`
- `SubtitleAlignmentProvider`
- `AssetAnalysisProvider`
- `VideoAnalysisProvider`
- `SpeechToTextProvider`
- `EmbeddingProvider`

Provider 由配置总线和 `ModelCapabilityRegistry` 选择与校验，页面不能直接知道供应商实现，也不能展示模型未声明支持的参数。调用记录账号、能力、模型、Provider、版本、知识快照、AI 配方版本、批次覆盖、耗时、成本、状态与失败原因。

直接 API、OpenAI-compatible、ComfyUI 和 RunningHub 都通过适配层实现同一能力接口。适配方式不得泄漏到页面业务规则；页面只读取标准化能力、健康与任务状态。

能力契约至少包含：

- `declared_abilities`：供应商或工作流元数据声明的能力。
- `adapter_abilities`：当前适配器真实实现并经过测试的能力。
- `input_modalities` 与 `adapter_input_modalities`。
- `parameter_schema`：时长、比例、分辨率、负向提示、原生音频、水印和并发等边界。
- `contract_verified`、`verified_at`、`source_urls` 与 `contract_issues`。

产品可用能力固定取 `declared_abilities ∩ adapter_abilities`，并要求 `contract_verified=true`。未验证模型只能在诊断详情中展示，不得成为默认 `CapabilityRoute`。Provider 拒绝或内容审核失败可以返回安全改写建议，但 Runtime 不得在无用户确认时静默重写 Prompt。

## 11. 配置、日志与错误

### 11.1 配置总线

配置优先级：

`系统默认 -> CapabilityRoute -> 账号覆盖 -> 单次批次策略`

账号覆盖必须经过配置总线校验和持久化。页面、脚本、服务不得各自保存独立配置副本。

Provider 原始密钥只能由系统级 `ProviderProfile` 引用安全存储；`AccountAIRecipe` 和 `ProductionBatch` 只能保存 `provider_profile_id`、模型 ID、配方版本与覆盖字段。

固定脚本拆分方式、Prompt Profile 版本、视觉风格前缀、合成模板版本、TTS、BGM、能力参数和能力契约修订必须进入不可变任务配置快照。页面不得在运行中修改既有 `GenerationRun`；需要变更时创建新运行或重试修订。

媒体工具依赖、可执行文件路径、支持来源和全局限制只允许进入系统配置与 `MediaToolRegistry`。账号只保存任务和输出，不保存独立工具路径；单次任务配置必须通过配置总线和工具定义校验。

### 11.2 日志字段

统一结构至少包含：

- 时间、级别、模块、操作。
- `account_id`、对象类型、对象 ID、任务 ID。
- 阶段、耗时、Provider / Runtime 版本。
- 模型、能力路由、Prompt / 模板版本、契约修订和重试来源。
- 安全错误码、失败原因和关联日志 ID。
- 媒体工具任务还需记录工具 id、输入来源类型、权利确认时间、输出资产和依赖版本；日志不得保存完整私密链接或未脱敏本地路径。

日志不得记录密钥、令牌、完整凭据、完整 Prompt、供应商原始请求正文或未脱敏敏感路径。调试模式也只能记录字段名、长度、安全摘要和引用 ID。

### 11.3 Runtime 信封

- 成功：`{ "ok": true, "data": ..., "meta": ...? }`
- 失败：`{ "ok": false, "error": "...", "error_code": "...", "log_id": "...?", "fieldErrors": ...?, "meta": ...? }`
- 请求关联由响应 Header `X-Request-ID` 提供；`log_id` 只在用户可见错误或诊断记录已实际生成时返回，不伪造空日志引用。

### 11.4 数据库配置与启动迁移

数据库路径、迁移锁、备份目录、保留份数和超时必须通过统一配置入口解析。`TK_OPS_RUNTIME_DB_PATH` 与 legacy `TK_OPS_DATABASE_PATH` 指向不同文件时拒绝启动；相对路径固定锚定 Runtime 数据目录，不得依赖进程当前工作目录。

生产启动顺序固定为：

```text
加载 Bootstrap 配置
→ 配置结构化日志
→ 加载完整配置
→ 获取迁移锁
→ 识别 Alembic revision 或已知 legacy 指纹
→ 必要时备份 DB / WAL / SHM
→ Alembic upgrade head
→ 验证目标 Schema 契约
→ 创建 Engine、Repository 和 Service
→ Runtime 就绪
```

- 未知或部分匹配 Schema 只读失败，禁止 stamp、repair 或猜测补列。
- 正常生产启动不得调用 `Base.metadata.create_all()`、`initialize_domain_schema()` 或隐式 Schema repair。
- legacy normalizer 只允许存在于显式迁移 bridge 和测试辅助路径。
- Runtime 容器尚未创建、业务写门尚未开放时，迁移失败才可恢复迁移前备份。
- 写门开放后禁止自动覆盖当前数据库；P0-F 已完成回退 Runtime 制品兼容、维护态、`cutover_event_id` 和启动恢复证据，强制数据恢复仍必须经过单独的增量导出、重放与核对流程。

## 12. 缓存与状态更新

- 所有账号级缓存键以 `account_id` 开头。
- 写操作成功后失效当前对象、依赖对象、页面摘要和任务列表。
- 任务完成后由 WebSocket 推送修订号，前端补拉最终对象。
- 账号切换增加 `accountRevision`，旧请求结果不得写入新账号状态。
- 取消、失败和重试必须同步更新批次、内容变体、任务队列和壳层反馈。
- 脚本采用或恢复后失效分镜就绪摘要；已存在分镜不得被静默覆盖，必须记录所基于的脚本修订。
- 视频拆解回流后失效脚本、分镜、知识来源与创作摘要；媒体工具完成后失效当前账号内容库和工具任务列表。
- Provider、模型、能力、Prompt 或模板更新后增加 `aiConfigRevision`，失效系统 AI 就绪摘要和受影响账号配方校验结果；运行中的任务继续使用创建时快照。

## 13. 测试边界

生产实现至少覆盖：

1. 仓储与服务层账号隔离。
2. 账号切换时旧请求和旧订阅不能污染新账号状态。
3. 知识快照与生成记录可追溯。
4. 批次取消、局部重试和幂等。
5. 发布预检与真实回执状态转换。
6. Runtime 信封、错误码和中文错误转换。
7. Light / Dark、宽屏 / 紧凑窗口和页面状态。
8. 账号状态转换、配置复制白名单、归档与恢复健康复检。
9. Provider Profile、模型、Prompt 与账号 AI 配方不泄漏密钥或完整 Prompt，继承优先级确定。
10. 模型声明能力与适配器能力交集、契约验证、参数 Schema、已确认内容 / 主题 / 固定脚本 / 已有素材输入、节点级取消、重试与回退幂等。
11. 脚本版本采用、恢复、未保存守卫和分镜脚本修订一致性。
12. 视频拆解阶段幂等、Provider / FFprobe 缺失、标准结果和选择性回流。
13. 媒体工具权利确认、工具能力阻断、任务超时 / 取消 / 重试和输出账号隔离。
14. 十入口导航、脚本 / 分镜 / 拆解 / 工具箱的宽屏、紧凑窗口与 Light / Dark。
15. Provider 向导、模型发现 / 手动录入、能力路由、Prompt 版本与模板预览的加载、空、正常、错误和未保存状态。
16. 固定脚本三种拆分方式、资产分析匹配、任务 / 镜头两级进度、并发归并和局部失败保留。

## 14. 迁移与删除边界

- P0-A 兼容边界以 `docs/P0-ACCOUNT-FOUNDATION-COMPATIBILITY-MATRIX.md` 为准。
- 旧 `ai_editing_workspace`、配音、字幕、渲染、自动化等独立路由不得继续出现在主导航。
- 旧 `script_topic_center`、`storyboard_planning_center`、`video_deconstruction_center` 可迁移到新的账号级路由，但必须补齐 `account_id` 范围、账号缓存键、任务主题和未保存守卫；不得原样接回旧壳。
- 旧 `account_content_plan` 重定向到 `account_script_topic`，原栏目、选题与节奏数据迁移为 `ContentPlan` 和 `ContentItem`。
- 链接下载和去水印属于新增生产能力，正式接入前必须单独完成依赖、平台条款、许可证、安全、接口与测试规格。
- 旧 `Timeline` 数据若需保留，只能迁移或转换为内部 `CompositionSpec`，不能直接作为新 UI 编辑模型。
- 删除旧路由和模型前必须另立实现计划，包含数据迁移、兼容期、回退点和测试。
- 当前交互原型不修改生产目录、Runtime、数据库或真实接口。
