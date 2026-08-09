# TK-OPS 原型转生产：P0 账号工作区与 AI 配置底座详细设计规格

> 创建日期：2026-07-20  
> 状态：已批准（2026-07-20）  
> 实施进度：P0-A 至 P0-F 已于 2026-08-01 全部完成并通过最终验收  
> 兼容矩阵：`docs/P0-ACCOUNT-FOUNDATION-COMPATIBILITY-MATRIX.md`  
> 测试节奏：P0-A 至 P0-E 各完成后执行一次阶段测试；P0-F 已执行一次 P0 全量测试、构建、E2E、Tauri / 安装包与视觉验收  
> 对应计划：`docs/superpowers/plans/2026-07-19-prototype-to-production-p0-account-foundation.md`  
> 产品真源：`docs/PRD.md`  
> UI 真源：`docs/UI-DESIGN-PRD.md`  
> 架构真源：`docs/ARCHITECTURE-BOOTSTRAP.md`  
> 目标终端：Windows PC 桌面应用，不考虑手机端适配  
> 实施门：本规格经用户批准后，才允许修改 `apps/desktop`、`apps/py-runtime`、`tests` 和生产数据库迁移

## 1. 规格目标

本规格将已验收交互原型转换为第一段真实生产主链，解决四个基础问题：

1. 将旧项目级 16 页壳迁移为十三个页面容器、十个账号级导航入口和两个系统级管理入口。
2. 将“账号切换”从页面筛选提升为 Runtime、缓存、任务、文件、日志和 WebSocket 共同执行的工作区事务。
3. 将现有 AI Provider、模型、能力与 Prompt 配置升级为系统配置、账号配方和后续批次覆盖可追溯的配置继承链。
4. 将旧 `/api/...`、集中式客户端 / 类型、大型服务和启动时隐式 Schema 修补迁移到版本化、可回退、可测试的生产结构。

本阶段最终可完成：

```text
许可证与目录初始化
→ Runtime 自检
→ 创建 / 选择账号
→ 真实连接与工作区诊断
→ 定位、知识库和 AI 配方基础配置
→ 原子切换账号工作区
→ 进入该账号的真实空态或就绪工作区
```

本阶段不实现完整 P1 创作业务，不以旧页面或演示数据冒充已迁移功能。

## 2. 现状基线与约束

### 2.1 可复用基线

- Desktop 已有 Tauri 2、Vue 3、Pinia、Vue Router、Vite、Vitest、Bootstrap Gate、许可证 Store、配置总线、任务总线和设计令牌。
- Runtime 已有 FastAPI、SQLAlchemy、Alembic、统一成功信封、请求 ID、日志入口、安全存储、账号 / 工作区 / 执行绑定、Provider 健康和 AI 模型基础数据。
- 已有账号、Bootstrap、设置、Provider、Prompt、WebSocket、契约与 Runtime 测试，可作为迁移回归基线。
- 原型已确认账号级信息架构、低噪音视觉语言、账号管理、AI 设置和业务空态。

### 2.2 必须修复的基线偏差

下表是 2026-07-20 设计审计基线。P0-A 已将“数据迁移”一项切换为正式 Alembic 接管；其余偏差仍按 P0-B 至 P0-F 处理。

| 偏差 | 当前状态 | P0 目标 |
| --- | --- | --- |
| 页面树 | 旧 16 页，仍含 AI 剪辑工作台、独立配音 / 字幕 / 渲染 / 自动化 | 十个账号入口、两个系统页、一个首启页 |
| 工作区范围 | `requiresProjectContext` 和 `ProjectStore` | `requiresAccountContext` 和 `AccountContextStore` |
| Runtime API | 主要使用 `/api/...` | 新能力只使用 `/api/v1/...`，旧入口薄转发 |
| WebSocket | 全局广播，前端单连接收全部事件 | 系统事件 + 当前账号主题，服务端隔离 |
| Tauri / Runtime | 开发脚本在外部启动 Uvicorn；安装包没有 Runtime sidecar | Tauri 真实拥有 Runtime 子进程与生命周期 |
| 账号状态 | `active` 等旧状态可由输入直接写入 | 服务层计算固定五状态，禁止请求体直接覆盖 |
| AI 配置 | 能力、Provider、模型和 Prompt 边界混合 | 六类系统对象 + 账号 Recipe |
| 数据迁移 | P0-A 前由启动时 `create_all` 与千行 Schema repair 维护 | P0-A 已切换为 legacy baseline + Alembic 正式迁移 |
| API 文档 | `docs/api/v1/` 尚未建立 | `docs/api/v1/` 唯一真源 |
| 异常反馈 | 部分后台刷新只写 `console.warn` | Runtime 日志 + 稳定错误容器 + 重试入口 |

旧 Runtime、Contract、Desktop 与原型测试可作为迁移基线而非 P0 完成证据；其中大量断言锁定旧 `/api/...` 和旧产品页面。P0-A 已新增迁移、恢复、锁、指纹和启动顺序测试；P0-B 以后仍必须新增真实 v1 与新主链测试，不能仅依靠旧测试继续全绿。

### 2.3 强制拆分对象

以下文件不得继续承载新增 P0 业务：

| 当前文件 | 约行数 | 处理方式 |
| --- | ---: | --- |
| `apps/desktop/src/app/runtime-client.ts` | 约 1600 | 拆为通用核心、Bootstrap、账号、AI 系统和任务客户端 |
| `apps/desktop/src/types/runtime.ts` | 约 1950 | 拆为通用、Bootstrap、账号、AI、任务 DTO |
| `apps/desktop/src/layouts/AppShell.vue` | 约 1120 | 拆为账号壳、Sidebar、Top Bar、Detail Panel 和状态反馈 |
| `apps/desktop/src/modules/settings/components/ProviderCatalogPanel.vue` | 约 1110 | Provider 表、向导、详情与状态 composable 分离 |
| `apps/desktop/src/pages/settings/AISystemSettingsPage.vue` | 约 760 | 页面编排、composable 和三个设置面分离 |
| `apps/desktop/src/pages/setup/SetupLicenseWizardPage.vue` | 约 630 | 页面步骤、状态、表单和样式分离 |
| `apps/py-runtime/src/services/ai_capability_service.py` | 2392 | 按 Provider、模型能力、路由、Prompt 和健康检查拆分 |
| `apps/py-runtime/src/persistence/engine.py` | 1007 | 引擎、legacy preflight、迁移运行器和测试辅助分离 |
| `apps/py-runtime/src/app/factory.py` | 489 | 容器装配、路由装配、异常处理和 lifespan 分离 |

拆分必须保持现有对外行为有测试保护；不得以“重构”为理由同时修改无关业务规则。

现有 `ProjectStore` 继续作为旧代码迁移参考，不允许改名后冒充 Account Context；否则项目级缓存与账号租户边界会被混入同一状态机。

## 3. P0 交付边界

### 3.1 P0 可用页面

| Route ID | URL | 范围 | P0 状态 |
| --- | --- | --- | --- |
| `setup_license_wizard` | `/setup/license` | 系统 | 真实可用 |
| `account_workspace_home` | `/workspace` | 账号 | 真实壳、就绪摘要、业务空态 |
| `account_strategy_knowledge` | `/strategy-knowledge` | 账号 | 定位与知识 P0 基础配置 |
| `account_script_topic` | `/scripts` | 账号 | 显示真实前置状态与 P1 迁移说明，不读取旧项目数据 |
| `account_storyboard_planning` | `/storyboards` | 账号 | 显示真实前置状态与 P1 迁移说明 |
| `account_video_deconstruction` | `/video-deconstruction` | 账号 | 显示真实前置状态与 P1 迁移说明 |
| `account_batch_production` | `/production/batches` | 账号 | 显示真实账号与 AI 就绪状态，P1 前不创建假批次 |
| `account_content_library` | `/content-library` | 账号 | 真实空态，不读取未迁移旧资产 |
| `account_media_toolbox` | `/media-tools` | 账号 | 真实依赖状态，P1 前不执行新增工具 |
| `account_publishing` | `/publishing` | 账号 | 真实连接 / 执行绑定预检，P2 前不伪造任务 |
| `account_review` | `/review` | 账号 | 等待真实回执的中性状态 |
| `account_management` | `/settings/accounts` | 系统 | 真实可用 |
| `ai_system_settings` | `/settings/ai-system` | 系统 | 真实 Provider、模型、路由、Prompt、Runtime 与诊断 |

P1 页面容器可以在 P0 出现，但必须明确呈现 `dependency_blocked` 或真实空态；禁止把旧项目级页面原样挂回新路由。

### 3.2 P0 领域对象

- 账号身份、状态、连接摘要与配置复制审计。
- `PositioningProfile`、`AccountKnowledgeBase`、`KnowledgeSource`、`BrandKit` 和 `AccountPublishDefaults` 基础对象。
- `ProviderProfile`、`ModelProfile`、`ModelCapability`、`PromptProfile`、`CapabilityRoute` 和 `AccountAIRecipe`。
- 系统配置修订、账号修订、任务、日志和 WebSocket 事件。

### 3.3 P0 非目标

- 不迁移完整 `ContentItem`、脚本、分镜、拆解、批次、内容变体和成片执行。
- 不物理删除旧 Timeline、配音、字幕、渲染、自动化或旧页面文件。
- 不提供跨账号引用；P0 只提供显式配置复制。
- 不实现 Provider 计费后台、Prompt 市场、团队共享配置和云同步。
- 不直接运行 ComfyUI 工作流 JSON 或向普通页面暴露供应商私有参数。

## 4. 目标架构与数据流

```text
Tauri / Vue UI
  ├─ BootstrapStore ──────────────── /api/v1/bootstrap
  ├─ AccountContextStore ─────────── /api/v1/accounts/{account_id}
  ├─ ConfigBusStore ──────────────── /api/v1/system/config
  ├─ AISystem stores ─────────────── /api/v1/system/*
  └─ TaskBusStore ────────────────── /api/v1/ws?account_id=...
                           │
                           ▼
FastAPI v1 routes
  ├─ request / error / log middleware
  ├─ account scope dependency
  ├─ service transaction boundary
  ├─ repository account boundary
  └─ config + task + event buses
                           │
                           ▼
SQLite + local workspace + secure secret store
```

核心原则：

1. UI 只提交用户意图，不计算账号生命周期、AI 能力可用性和复制白名单。
2. 所有账号级 URL 显式包含 `account_id`；账号级请求体中出现不同账号 ID 时直接拒绝。
3. Provider 密钥写入安全存储，数据库只保存 `credential_ref`。
4. 配置写操作在同一事务中更新数据和修订号，事务提交后才广播事件。
5. 长操作创建任务；HTTP 返回任务受理结果，进度经账号范围事件更新。

## 5. Desktop 路由与壳层规格

### 5.0 Bootstrap 单一入口

当前 `BootstrapGate.vue` 与 `SetupLicenseWizardPage.vue` 同时承载许可证 / 初始化 UI，形成双真源。P0 固定为：

- `/setup/license` 的 `SetupLicenseWizardPage.vue` 承载许可证、目录初始化、Runtime 自检和可恢复错误步骤。
- `BootstrapGate` 只负责首次状态加载、应用级不可恢复错误遮罩和把用户送到路由页，不再自行渲染第二套许可证 / 初始化表单。
- `BootstrapStore` 是状态真源，页面只通过 Store 触发 Runtime 适配层；首启步骤不得各自维护副本。
- 已授权且初始化完成时，路由页按 `redirect` 返回原目标；默认目标为 `/workspace`，不再是 `/dashboard`。

### 5.1 新路由元数据

`RouteManifestItem` 改为至少包含：

```ts
type RouteManifestItem = {
  id: RouteId;
  path: string;
  title: string;
  icon: string;
  navOrder: number | null;
  navSection: "strategy" | "creation" | "delivery" | "system" | "hidden";
  scope: "system" | "account";
  requiresLicense: boolean;
  requiresRuntimeReady: boolean;
  migrationState: "ready" | "p0_foundation" | "p1_pending" | "p2_pending";
  detailPanelMode: "hidden" | "contextual" | "overlay";
  loadComponent: () => Promise<unknown>;
};
```

删除 `requiresProjectContext` 的业务含义。兼容期可以保留字段解析，但新 Route Manifest 不再写入该字段。

### 5.2 路由守卫顺序

1. 加载许可证与 Bootstrap 状态。
2. 未授权或 Runtime 未初始化时进入 `/setup/license?redirect=...`。
3. `scope=system` 的页面允许在无当前账号时进入。
4. `scope=account` 且无有效账号时保留目标 URL，展示账号选择状态；不得自动选择任意账号。
5. 当前账号已归档、被删除或修订失效时清空账号上下文并展示选择状态。
6. 账号切换或路由离开前调用统一未保存守卫。
7. P1 / P2 未迁移页面进入真实受限状态，不回退到旧业务页面。

### 5.3 旧路由兼容映射

| 旧 Route / URL | 新目标 | 兼容行为 |
| --- | --- | --- |
| `creator_dashboard` `/dashboard` | `/workspace` | `replace` 重定向 |
| `script_topic_center` `/scripts/topics` | `/scripts` | `replace` 重定向 |
| `storyboard_planning_center` `/storyboards/planning` | `/storyboards` | `replace` 重定向 |
| `video_deconstruction_center` `/video/deconstruction` | `/video-deconstruction` | `replace` 重定向 |
| `asset_library` `/assets/library` | `/content-library` | 进入 P1 迁移说明，不读取旧资产 |
| `publishing_center` `/publishing/center` | `/publishing` | 进入真实连接预检状态 |
| `review_optimization_center` `/review/optimization` | `/review` | 进入等待真实回执状态 |
| `account_management` `/accounts` | `/settings/accounts` | `replace` 重定向 |
| `device_workspace_management` `/devices/workspaces` | `/settings/ai-system?section=runtime` | 打开 Runtime 与工作区分区 |
| `ai_editing_workspace` `/workspace/editing` | `/production/batches?legacySource=editing-workspace` | 显示一次性迁移说明，禁止打开旧工作台 |
| `voice_studio` `/voice/studio` | `/production/batches?legacyStage=voice` | 显示流程已合并提示 |
| `subtitle_alignment_center` `/subtitles/alignment` | `/production/batches?legacyStage=subtitle` | 显示流程已合并提示 |
| `render_export_center` `/renders/export` | `/production/batches?legacyStage=render` | 显示流程已合并提示 |
| `automation_console` `/automation/console` | `/workspace?legacyRoute=automation-console` | 在工作台显示流程已合并提示 |

兼容重定向只存在一个发布窗口。新代码、新文档和新链接禁止生成旧 URL。

### 5.4 账号工作区壳

`AccountWorkspaceLayout` 只负责布局：

- `AccountSidebar`：十个账号入口、系统设置、账号切换器。
- `AccountTopBar`：页面标题、当前账号副文本、Runtime / 工作区健康和唯一主动作插槽。
- `ContentHost`：页面内容与页面状态。
- `ShellDetailPanel`：按选中对象打开；紧凑窗口为覆盖抽屉。
- `ShellStatusFeedback`：持续任务、连接中断和稳定错误入口。

壳层不得直接调用 Runtime 或拼接业务规则。账号、配置和任务状态由 Store 注入。

### 5.5 PC 尺寸行为

| 条件 | Sidebar | Top Bar | Detail Panel | 页面主体 |
| --- | --- | --- | --- | --- |
| `>= 1280px` | 248px 展开 | 当前账号 + 页面 | 360px 推入或覆盖，按页面决定 | 28–32px 边距 |
| `960–1279px` | 76px 图标栏 | 隐藏重复账号副文本 | 右侧覆盖抽屉 | 20px 边距 |
| `< 960px` | 不支持 | 显示“窗口过窄”稳定提示 | 不渲染新布局 | 不切换手机导航 |

必须覆盖 Light / Dark、键盘焦点、Reduced Motion 和局部滚动。账号切换器、设置入口和页面主动作始终可达。

## 6. AccountContext 前端规格

### 6.1 Store 状态

```ts
type AccountSwitchStatus =
  | "idle"
  | "guarding"
  | "preparing"
  | "committing"
  | "refreshing"
  | "failed";

type AccountContextState = {
  currentAccountId: string | null;
  currentAccount: AccountWorkspaceContextDto | null;
  switchStatus: AccountSwitchStatus;
  switchIntentId: string | null;
  targetAccountId: string | null;
  accountRevision: number;
  subscriptionRevision: number;
  lastRouteByAccount: Record<string, string>;
  pendingUnsavedGuard: boolean;
  error: RuntimeError | null;
};
```

`lastRouteByAccount` 通过配置总线持久化；禁止页面自行写 `localStorage`。

这里的 `accountRevision` 是前端账号上下文世代，用于丢弃迟到响应；Runtime 账号实体自己的 revision 在 DTO 中使用 `revision`，工作区快照使用 `workspaceRevision`，三者不得混用。

### 6.2 未保存守卫注册表

页面通过统一注册表提供：

```ts
type UnsavedGuard = {
  id: string;
  label: string;
  isDirty: () => boolean;
  save: () => Promise<void>;
  discard: () => Promise<void> | void;
};
```

账号切换、路由离开、关闭设置编辑器和归档当前账号均调用同一注册表。Modal 只给出“保存并继续 / 放弃并继续 / 取消”，保存失败时停止切换并保留编辑状态。

### 6.3 切换事务

```text
记录旧账号、路由、缓存与订阅快照
→ 检查同账号与重复点击
→ 执行未保存守卫
→ 创建 switchIntentId、AbortController 并递增切换修订
→ 取消旧账号可见 HTTP 请求，但不取消后台任务或旧事件订阅
→ prepare 目标账号并暂存壳数据、就绪摘要和可见任务
→ 临时订阅目标账号 Topics，携带逐 Topic 游标映射并缓冲事件
→ 原子提交 currentAccount、缓存命名空间、可见任务、路由与 accountRevision
→ 清空 Detail Panel、页面选择和账号 AI 会话
→ 提升目标订阅并退订旧账号可见 topic
→ 恢复目标账号最近有效页面，否则进入 /workspace
→ 调用 workspace-activation 记录最近使用时间与服务端账号修订
→ 按修订补拉最终摘要
→ 完成
```

关键规则：

- `prepare` 与目标临时订阅完成前不得修改 `currentAccountId`，旧账号壳、缓存和订阅保持可见。
- 每个账号级请求捕获发出时的 `accountRevision`；响应到达时修订不一致则丢弃，不显示为错误。
- Runtime 客户端用 `AbortController` 按 `scopeKey=account:{id}` 取消旧请求。
- 旧账号后台任务继续在 Runtime 运行，只停止当前 UI 的可见订阅。
- 目标临时订阅失败时回滚切换；提交完成后的后续断线不回滚账号，只显示稳定离线条并通过 HTTP 对账恢复。
- `workspace-activation` 或提交后的摘要补拉失败不回滚已经可见的目标账号；状态进入 `failed`，重试类型为刷新，只重新对账当前目标账号。
- HTTP 结果必须同时匹配目标账号、`switchIntentId` 和切换修订，任意异步步骤只有最新 Intent 可以提交。
- Runtime Client 对账号级响应执行范围校验；返回对象包含其他账号 ID 时转换为 `ACCOUNT_SCOPE_MISMATCH`，记录日志并禁止进入 Store。
- A→B 与 A→C 并发采用 latest-intent-wins；过期 Intent 取消目标请求、退订临时 topic 并丢弃缓冲。

### 6.4 账号切换器状态

- `idle`：正常显示当前账号。
- `guarding`：显示未保存确认，不显示加载遮罩。
- `preparing / committing / refreshing`：切换器禁用重复点击，Content Host 使用局部 Skeleton。
- `failed`：提交前失败保留原账号并提供“重试切换”；提交后激活或补拉失败保留目标账号并提供“重试刷新”。两者都显示中文错误和可用的 `log_id`。
- 目标账号 `archived`：不可切换，只提供“前往管理并恢复”。

### 6.5 缓存命名空间

所有账号 Store 缓存键固定为：

```text
account:{account_id}:{resource}:{query_hash}
```

写操作成功后根据 Runtime 返回的 `invalidations` 精确失效。账号切换只切换可见命名空间，不清除上一账号已缓存的只读数据；涉及未保存编辑草稿的缓存必须在守卫完成后处理。

## 7. P0 页面与交互规格

### 7.1 无当前账号状态

进入账号级 URL 但没有当前账号时，不重定向到任意账号，也不显示空白页面。Content Host 显示：

- 标题：“选择一个账号工作区”。
- 一句影响说明：“定位、知识、内容与任务按 TikTok 账号独立保存。”
- 主动作：“选择账号”。
- 次级文字入口：“添加账号”。

账号选择弹层关闭后仍停留在原 URL；选择成功后继续进入该 URL。系统设置与账号管理始终可访问。

### 7.2 账号管理列表

列表列固定为：

| 列 | 内容 |
| --- | --- |
| 身份 | 头像、显示名、TikTok handle |
| 定位 | 激活定位版本的短摘要；没有时显示“待设置” |
| 就绪状态 | 连接、知识、AI 三个短状态 |
| 生命周期 | 草稿、未绑定、可用、需处理、已归档 |
| 最近使用 | 真实 `last_used_at`；没有时显示“尚未使用” |
| 动作 | 当前推荐动作一个，其余进入更多菜单 |

页面顶部只显示状态筛选、搜索和“添加账号”。禁止显示粉丝数、视频数、增长率等无来源统计卡。

P0 创建入口平台固定为 TikTok，不显示现有 YouTube 选项；用户不能手工选择生命周期状态。现有“同步健康 100%”等假指标全部移除，改为 Runtime 返回的连接 / 知识 / AI 三项真实就绪度。

### 7.3 六步添加账号向导

| 步骤 | 字段 / 动作 | 允许结果 |
| --- | --- | --- |
| 1. 基础身份 | 显示名、TikTok handle、头像文件可选 | 保存 `draft` |
| 2. 真实连接 | 选择真实 DeviceWorkspace、BrowserInstance、ExecutionBinding，运行诊断 | 可保存连接草稿；六步向导未完成时账号生命周期仍为 `draft` |
| 3. 定位 | 受众、内容支柱、表达风格、禁用边界、发布约束 | 创建定位草稿版本 |
| 4. 知识库 | 创建独立知识库，可添加真实来源并发起索引 | 空库可继续，但显示“待补充” |
| 5. AI 配方 | 继承系统路由，选择视觉风格、音色、模板、成本和允许覆盖 | 校验后创建 Recipe v1 |
| 6. 健康检查 | 连接、知识、AI 三项检查和修复入口 | 由服务层计算最终状态 |

向导关闭前触发未保存守卫。所有连接、索引和 AI 检查有超时、取消、失败、重试和日志入口。

### 7.4 账号详情

同一系统页内使用低高度标签：

```text
概览 | 身份与定位 | 连接与工作区 | 知识库 | AI 创作档案 | 发布默认值 | 数据与归档
```

详情只在选中一个账号后出现。归档账号默认只读，允许恢复、导出诊断摘要和查看审计记录。

### 7.5 配置复制

复制 Modal 必须逐项勾选允许范围：

- 定位模板。
- 知识规则结构，不含来源、索引和引用。
- BrandKit。
- AI 配方引用和允许覆盖，不含 Provider 凭据。
- 发布默认值。

目标始终是新账号草稿。结果页展示 `copiedSections`、`skippedSections` 和跳过原因。禁止复制平台授权、工作区 / 浏览器绑定、内容、资产、任务、知识来源、索引、日志和发布历史。

### 7.6 归档与恢复

- 归档确认列出影响：停止进入新生产 / 发布、当前工作区退出、历史保留。
- 当前账号归档成功后，Account Context 原子清空并进入账号选择状态。
- 恢复不直接设为 `ready`；先进入 `unbound` 或 `attention`，运行连接、工作区、知识和 AI 健康复检后再由服务层计算。
- 检查失败展示具体依赖和恢复动作，不以绿色状态表示未验证对象。

### 7.7 定位与知识 P0 页面

P0 页面提供：

- 当前激活定位版本摘要、草稿与“新建版本”。
- 知识库状态、来源列表、索引任务和规则冲突。
- BrandKit 基础字段与版本。
- 来源详情的状态、哈希、更新时间、错误和日志引用。

P0 不提供生成引用浏览、语义检索调试器或完整案例分析。没有来源时显示“添加知识来源”，不渲染假文档。

### 7.8 AI 与系统设置

一级分区：

```text
AI 能力 | Runtime 与工作区 | 日志与诊断
```

AI 能力二级标签：

```text
Provider | 模型与能力 | Prompt 模板
```

#### Provider

- Provider 表只展示名称、适配方式、健康、能力类型、模型数和一个主动作。
- 适配方式明确包含 Direct API、OpenAI-compatible、ComfyUI 和 RunningHub；不得因旧页面缺少选项而隐藏已批准能力。
- “添加 Provider”五步：连接类型 → 地址与凭据引用 → 网络与并发 → 模型发现 / 手动录入 → 测试并保存。
- 连接测试是可取消任务。测试失败不得保存为“健康”，但可保存禁用配置供后续修复。
- 凭据输入离开前写入安全存储；页面只接收 `credentialRef` 与掩码摘要。

#### 模型与能力

- 模型表：模型 ID、Provider、启用、已接入能力、契约验证、限制。
- 能力路由表：产品能力、主模型、回退模型、Prompt、状态、一个修复动作。
- 能力矩阵详情区分 `declared`、`adapterSupported`、`contractVerified`。
- 未验证的能力不可出现在路由选择器可选项中。
- 已退出产品主线的 `magic_cut` 不进入 P0 能力键、设置页或默认路由；旧配置只在迁移报告中记录。

#### Prompt 模板

- 左侧列表按能力筛选，右侧编辑器显示名称、系统提示、任务模板、变量 Schema、输出 Schema、视觉前缀、安全约束和引用。
- 已激活版本不可原地修改；“保存”创建新版本。
- 切换模板、关闭详情、离开页面和切换账号均触发未保存守卫。
- 页面和日志默认不显示完整 Prompt；编辑器仅在用户主动打开时加载正文。

### 7.9 页面状态矩阵

| 状态 | 页面表达 | 允许动作 |
| --- | --- | --- |
| `loading` | 局部 Skeleton，保留壳层 | 取消长操作 |
| `first_use` | 标题、影响、一项主动作 | 创建 / 配置 |
| `empty` | 中性空态 | 添加真实对象 |
| `filtered_empty` | 无匹配结果 | 清除筛选 |
| `dependency_blocked` | 缺失依赖和修复入口 | 前往依赖页 |
| `waiting_external` | 任务 / Provider / 索引等待 | 取消、查看进度 |
| `restricted` | 账号归档、权限或未授权 | 恢复或诊断 |
| `error` | 中文摘要、影响、重试、日志 | 重试、打开日志 |
| `ready` | 真实数据 | 页面主动作 |

任何静默后台刷新失败都必须写入统一日志，并在影响当前操作时显示稳定反馈；不得只输出浏览器控制台。

## 8. Runtime 模块结构规格

### 8.1 应用装配拆分

目标结构：

```text
apps/py-runtime/src/app/
├── factory.py                 # 只创建 FastAPI 与调用装配器
├── container.py               # Repository / Service 容器
├── lifecycle.py               # 数据迁移、健康刷新、关闭清理
├── route_registry.py          # v1 与兼容路由装配
└── exception_handlers.py      # 统一异常转换
```

`factory.py` 不再逐项构建数十个对象。`RuntimeContainer` 以强类型属性保存服务；测试可注入替身。应用启动失败必须记录日志并让 Bootstrap 获得可展示错误，禁止带半初始化服务继续运行。

### 8.2 v1 路由结构

```text
apps/py-runtime/src/api/
├── dependencies/
│   ├── account_scope.py
│   ├── license_guard.py
│   ├── runtime_session_guard.py
│   ├── request_origin_guard.py
│   └── request_context.py
├── routes/
│   ├── v1/
│   │   ├── bootstrap.py
│   │   ├── accounts.py
│   │   ├── account_connection.py
│   │   ├── account_positioning.py
│   │   ├── account_knowledge.py
│   │   ├── account_ai_recipe.py
│   │   ├── account_publish_defaults.py
│   │   ├── system_providers.py
│   │   ├── system_models.py
│   │   ├── system_model_capabilities.py
│   │   ├── system_capability_routes.py
│   │   ├── system_prompt_profiles.py
│   │   ├── system_composition_templates.py
│   │   ├── system_config.py
│   │   └── tasks.py
│   └── legacy/                # 仅薄转发，不含新业务规则
└── websocket/
    ├── manager.py
    ├── protocol.py
    └── routes.py
```

每个路由文件只做参数解析、dependency 调用、服务调用和信封封装。业务状态转换和复制范围必须在服务层。

### 8.3 服务拆分

```text
services/
├── accounts/
│   ├── account_service.py
│   ├── account_health_service.py
│   ├── account_copy_service.py
│   └── account_context_service.py
├── provider_profiles/
├── model_profiles/
├── capability_routes/
├── prompt_profiles/
├── composition_templates/
├── ai_recipes/
├── knowledge/
├── config/
└── tasks/
```

所有服务方法捕获可预期依赖异常并转换为领域错误；未知异常使用 `log.exception(...)` 记录后向上交给统一异常处理器。事务写操作必须显式提交 / 回滚，事件仅在提交成功后发布。

服务与仓储不得依赖 FastAPI `HTTPException`；HTTP 映射只存在于统一异常处理层。GET / 列表 / 健康读取禁止创建默认配置、执行迁移或写数据库；默认值初始化必须使用显式命令或 migration。跨 Provider、数据库和 outbox 的写入必须采用明确 Unit of Work 与补偿动作，禁止主记录已保存但副作用失败后留下半配置。

### 8.4 账号范围 dependency

`resolve_account_scope(account_id, request)` 执行：

1. 校验 ID 格式。
2. 查询账号；不存在返回 `ACCOUNT_NOT_FOUND`。
3. 默认拒绝归档账号进入账号工作区；恢复和审计路由可显式允许。
4. 建立 `AccountScope(account_id, account_revision, status, request_id)`。
5. 将范围写入日志 ContextVar。

账号级 Schema 禁止暴露可写 `accountId`；确实需要返回时只作为只读响应字段。服务与仓储签名的第一个业务参数固定为 `account_id`。

所有 v1 HTTP / WebSocket 先通过 `require_runtime_session` 与 Host / Origin 防护。通过调用方认证后，只有 `GET /bootstrap/status`、`GET /bootstrap/license`、`POST /bootstrap/license/activate` 豁免 `require_active_license`；安装迁移失败在 HTTP 监听前通过 Supervisor 生命周期信封报告，不扩大匿名或许可证豁免路由。前端路由守卫只是体验优化，不能替代服务端门禁。许可证失效时已经运行的任务按任务快照进入可审计终态，禁止继续创建新业务任务。

### 8.5 请求上下文、信封和日志

每个请求生成：

- `request_id`：HTTP 请求关联 ID，写入 `X-Request-ID`。
- `operation_id`：一次跨请求业务操作 ID，可由客户端 `X-Operation-ID` 传入。
- `log_id`：只有产生可见错误或诊断记录时生成，返回 UI。

成功：

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "revision": 12,
    "invalidations": []
  }
}
```

失败：

```json
{
  "ok": false,
  "error": "账号切换准备失败，请检查账号连接状态。",
  "error_code": "ACCOUNT_SWITCH_PREPARE_FAILED",
  "log_id": "log_01J..."
}
```

`meta` 可省略。新 v1 禁止在响应中暴露 traceback、完整路径、密钥、令牌、完整 Prompt、Provider 原始正文和内部 SQL。

结构化日志必须在数据库 preflight / migration 之前初始化。日志处理器挂到所有 Runtime 模块可传播到的统一根，而不是只配置 `tk_ops.runtime` 命名空间；需用测试证明任意模块的 `logging.getLogger(__name__).exception(...)` 能进入 JSONL 并关联 `log_id`。未知异常处理器必须调用 `log.exception(...)`，不能只返回 500。

Pydantic / FastAPI 校验错误只返回安全的字段位置、规则代码和中文摘要；禁止把 `exc.errors()` 中的原始 `input`、API Key、Token、Prompt 或路径直接放进响应与日志。深层映射键和额外字段位置可能来自用户输入，必须统一中性化为 `field`。

### 8.6 配置总线

配置优先级固定：

```text
系统默认 → CapabilityRoute → AccountAIRecipe → 后续 ProductionBatch 覆盖
```

P0 配置总线至少管理：

- Runtime 路径、日志级别、代理、连接和任务超时。
- HTTP 重试策略、WebSocket 重连策略和迁移备份策略。
- Provider 网络默认值和并发上限。
- 账号就绪所需能力清单。
- API 列表默认分页 `api.paginationDefaultLimit=50` 与最大分页 `api.paginationMaxLimit=200`。
- UI 主题、最近账号、每账号最近页面和紧凑窗口偏好。

配置更新使用修订号和 `If-Match`，冲突返回 `CONFIG_REVISION_CONFLICT`。页面不得自行持久化同名配置。

### 8.7 任务与取消

连接检查、知识索引、Provider 测试、模型发现、模型契约验证和账号恢复复检均使用统一任务模型：

```json
{
  "taskId": "task_01J...",
  "scope": "account",
  "accountId": "acc_01J...",
  "taskType": "account.health_check",
  "status": "queued",
  "cancellable": true,
  "createdAt": "2026-07-20T10:00:00Z"
}
```

状态固定为真源规定的 `queued / running / cancelling / failed / completed`。终态细节由独立字段表达：`completed` 必须携带 `completionKind: succeeded | cancelled`；`failed` 必须携带 `failureKind: error | timed_out | restart_interrupted`。取消是幂等操作；取消成功进入 `completed + cancelled`，超时进入 `failed + timed_out`，已经结束的任务返回当前终态，不返回假成功。事件只使用 `task.completed` 或 `task.failed` 表达终态，并携带相同 kind，禁止再创造与数据库状态并列的 `succeeded / cancelled / timed_out` 状态。Runtime 重启后从持久化任务恢复：可安全续跑的任务按幂等快照恢复，其余非终态任务转为 `failed + restart_interrupted` 并提供重试。

### 8.8 Tauri Runtime Supervisor 与 sidecar

当前 `src-tauri/src/main.rs` 只注册 Dialog / Shell 插件，安装包资源只有 FFprobe；`npm run app:dev` 启动的 Uvicorn 只是开发期外部脚本，不能作为生产 Runtime 证据。P0 必须补齐：

```text
Tauri 启动
→ 获取单实例锁
→ 解析应用数据目录与 Bootstrap 配置
→ 选择受控 loopback 端口并生成会话令牌
→ 启动已打包 Runtime sidecar
→ 轮询 /api/v1/bootstrap/status
→ 就绪后把连接信息交给 Runtime client
→ 监控退出、受控重启和状态事件
→ 应用退出时终止子进程树
```

Rust 模块边界：

```text
apps/desktop/src-tauri/src/
├── main.rs
├── runtime_supervisor/
│   ├── mod.rs
│   ├── config.rs
│   ├── process.rs
│   ├── health.rs
│   └── commands.rs
└── app_paths.rs
```

约束：

- 生产只绑定 `127.0.0.1`，使用动态受控端口，禁止监听公网网卡。
- 会话令牌由 Tauri 内存生成，通过环境变量传给 sidecar；不得出现在命令行、磁盘配置或日志。
- Frontend 通过受控 Tauri command 获取短期连接信息；浏览器开发模式继续使用 `VITE_RUNTIME_BASE_URL`，两种模式共用同一 Runtime Client 接口。
- 所有 `/api/v1/*` HTTP 请求均携带 `Authorization: Bearer <runtime_session_token>`；Runtime 使用常量时间比较验证令牌。Frontend Runtime Client 统一注入该 Header，业务组件不得读取、拼接或持久化令牌。
- 许可证门的豁免不等于调用方认证豁免：`GET /bootstrap/status`、`GET /bootstrap/license`、`POST /bootstrap/license/activate` 仅豁免许可证检查，仍必须通过 Runtime 会话认证。生产模式不存在匿名 Bootstrap API。
- Supervisor 的就绪轮询同样携带会话令牌。若另设进程存活探针，只能是未挂入 FastAPI 业务路由的进程内 IPC，不能暴露匿名 HTTP 健康端点。
- HTTP 必须校验 `Host` 为启动时确定的 `127.0.0.1:{port}`；CORS 只允许编译期 Tauri Origin 与开发配置白名单，禁止 `*`、任意 `localhost` 或请求反射 Origin。带 Origin 的请求和 WebSocket 握手必须通过同一白名单校验。
- WebSocket 使用受控子协议携带同一短期会话令牌，并在日志中整体脱敏；禁止把令牌放入 URL、Query、普通访问日志或持久化重连数据。
- 启动超时、最大重启次数和退避策略来自 Bootstrap 配置层；Runtime 就绪后由统一配置总线接管可变配置。
- Bootstrap 配置层只包含启动 Runtime 所必需的不可变默认值，并与统一配置 Schema 同源；不得形成第二套用户可编辑配置或页面私有副本。
- 第二个桌面实例只激活第一个窗口，不得再启动一个写同一数据库的 Runtime。
- sidecar 崩溃后 UI 显示稳定离线状态、日志入口和“重新启动 Runtime”，不得在后台无限重启。
- Runtime 在 HTTP 监听前因迁移 / 配置失败时，通过受控 stdout 生命周期信封输出脱敏 `error_code`、`log_id` 和阶段后退出；Supervisor 捕获并转换为 Bootstrap 可见错误，禁止把原始 stderr 或 traceback直接展示给 UI。
- 生产数据目录使用系统应用数据目录；仓库 `.runtime-data` 只用于开发，不进入安装包。

打包边界：

- 在 `apps/py-runtime/packaging/` 维护可重复的 Runtime sidecar 构建配置。
- `scripts/prepare-runtime-sidecar.mjs` 只负责调用固定构建入口、校验版本 / 哈希并放入 Tauri `externalBin` 目标目录。
- Tauri `beforeBuildCommand` 先准备 Runtime sidecar 和媒体工具，再构建前端。
- Runtime、Desktop 与 Tauri 版本必须由现有版本同步 / 检查脚本共同验证。
- 未生成 sidecar 时生产构建必须失败，禁止静默回退到系统 Python。

## 9. 数据模型规格

数据库字段使用 `snake_case`，API DTO 使用 `camelCase`。所有时间使用带时区 UTC ISO 8601；SQLite 保存规范化 UTC 文本。所有可更新聚合根包含整数 `revision`，每次成功写入递增。

### 9.1 `accounts` 扩展

保留现有主键和历史字段，新增或规范：

| 字段 | 类型 | 约束 / 说明 |
| --- | --- | --- |
| `id` | text | 主键，不复用 |
| `name` | text | 显示名，必填 |
| `platform` | text | P0 固定 `tiktok` |
| `username` | text nullable | TikTok handle |
| `platform_account_id` | text nullable | 平台稳定账号 ID，验证获得前不伪造 |
| `avatar_url` | text nullable | 只允许受控本地资源或安全 URL |
| `status` | text | 五状态 CheckConstraint |
| `wizard_completed_at` | text nullable | 六步向导完成时间 |
| `status_reason_code` | text nullable | 当前阻断原因 |
| `last_used_at` | text nullable | 成功切换后更新 |
| `last_health_checked_at` | text nullable | 最近完整健康检查 |
| `archived_at` | text nullable | 归档时间 |
| `revision` | integer | 默认 1 |
| `created_at` / `updated_at` | text | 必填 |

旧粉丝、关注、视频统计字段暂时保留但不进入 P0 UI，也不参与状态计算。`AccountCreateInput` 和 `AccountUpdateInput` 删除可写 `status`、统计数字和授权到期字段；状态只由服务动作和健康计算改变。

#### `account_connections`

每账号最多一个当前连接聚合：

- `id`, `account_id`，`account_id` 唯一。
- `credential_ref`, `session_ref`：只保存安全存储引用。
- `auth_status`：`unknown / required / valid / expired / failed`。
- `health_status`：`unknown / checking / ready / attention / failed`。
- `active_execution_binding_id`：当前真实执行绑定，可空。
- `last_checked_at`, `error_code`, `error_log_id`, `revision`, `created_at`, `updated_at`。

`DeviceWorkspace`、`BrowserInstance` 和 `ExecutionBinding` 必须分别显式保存 `account_id` 并由服务 / 仓储双重校验。活动绑定同时引用真实 `device_workspace_id` 和 `browser_instance_id`；两者不得复用同一字段或只靠 DTO 名称推断。

### 9.2 定位、知识、品牌与发布默认值

#### `positioning_profiles`

| 字段 | 说明 |
| --- | --- |
| `id`, `account_id` | 主键与账号外键 |
| `version` | 账号内单调递增，唯一 `(account_id, version)` |
| `status` | `draft / active / archived`，每账号最多一个 active |
| `audience_json` | 受众结构 |
| `content_pillars_json` | 内容支柱数组 |
| `voice_style_json` | 表达风格 |
| `prohibited_terms_json` | 禁用词与风险边界 |
| `publishing_constraints_json` | 发布约束 |
| `summary` | UI 短摘要，不存 AI 伪结果 |
| `revision`, `created_at`, `activated_at` | 版本与审计 |

激活新版本不会覆盖旧版本。P1 生成任务引用明确定位版本。

#### `account_knowledge_bases`

| 字段 | 说明 |
| --- | --- |
| `id`, `account_id` | 一账号一个，`account_id` 唯一 |
| `status` | `empty / indexing / ready / stale / attention` |
| `rules_json` | 规则结构，不包含来源正文 |
| `rules_version` | 规则版本 |
| `index_revision` | 索引修订 |
| `last_indexed_at` | 最近成功索引 |
| `error_code`, `error_log_id` | 可见错误关联 |
| `revision`, `created_at`, `updated_at` | 审计 |

#### `knowledge_sources`

| 字段 | 说明 |
| --- | --- |
| `id`, `account_id`, `knowledge_base_id` | 账号与知识库强范围 |
| `kind` | `document / image / video / audio / text / reference` |
| `name` | 来源名称 |
| `source_ref` | 受控文件 / 资产引用，不存未脱敏路径到日志 |
| `status` | `pending / indexing / ready / failed / stale` |
| `content_hash` | 去重与变更检测 |
| `metadata_json` | 安全元数据 |
| `error_code`, `error_log_id` | 失败证据 |
| `revision`, `created_at`, `updated_at`, `deleted_at` | 审计与软删除墓碑 |

P0 只建立来源、状态和索引任务，不实现完整检索 API。

#### `knowledge_snapshots`

- `id`, `account_id`, `knowledge_base_id`, `snapshot_version`。
- `positioning_profile_id`, `rules_version`, `index_revision`。
- `label`, `source_manifest_json`, `content_hash`, `created_at`；`label` 由 P0-C 的 0019 加法迁移补齐。
- 快照不可修改；P0 提供基础创建与审计能力，P1 生成任务必须引用明确快照。

#### `brand_kits`

- `id`, `account_id`, `version`, `status`。
- `visual_style_json`、`colors_json`、`fonts_json`、`logo_asset_refs_json`、`voice_rules_json`。
- 每账号最多一个激活版本；跨账号复制生成新 ID 和来源审计。

#### `account_publish_defaults`

- `account_id` 唯一。
- `timezone`、`privacy_level`、`allow_comments`、`allow_duet`、`allow_stitch`、`caption_rules_json`。
- P0 只保存默认值，不执行发布。

### 9.3 账号配置复制审计

`account_config_copy_runs`：

- `id`, `source_account_id`, `target_account_id`。
- `requested_sections_json`, `copied_sections_json`, `skipped_sections_json`。
- `status`：`running / succeeded / failed / rolled_back`。
- `operation_id`, `error_code`, `error_log_id`, `created_at`, `completed_at`。

复制在一个数据库事务内完成。任一已选择分区失败则全部回滚，目标账号草稿保留但不包含半复制数据；响应明确说明结果。

### 9.4 普通写操作幂等

P0-C 新增 `runtime_mutation_idempotency`，不得借用任务表冒充同步写幂等：

- `scope`、`account_id`、`operation_name`、`idempotency_key_hash`。
- `request_hash`、`response_json`、`resource_type`、`resource_id`。
- `created_at`、`expires_at`。
- 同一作用域、操作和键的同请求返回已保存结果；同键异参返回 `409 REQUEST_CONFLICT`。
- 账号 A 的键不得占用账号 B；响应不得保存凭据、Prompt 正文、本地路径或知识来源正文。

### 9.5 `provider_profiles`

| 字段 | 说明 |
| --- | --- |
| `id`, `name` | 主键与显示名 |
| `adapter_type` | `direct_api / openai_compatible / comfyui / runninghub` |
| `base_url` | 经校验的连接地址 |
| `credential_ref` | 安全存储引用，数据库不存密钥 |
| `region`, `proxy_ref` | 区域与安全代理引用，可空 |
| `timeout_ms`, `max_concurrency` | 通过配置总线边界校验 |
| `enabled` | 是否允许路由使用 |
| `health_status` | `unknown / checking / ready / degraded / failed` |
| `last_checked_at`, `last_error_code`, `last_error_log_id` | 健康证据 |
| `revision`, `created_at`, `updated_at` | 审计 |

Provider 保存成功不等于健康成功。未测试或失败的 Provider 可以作为禁用配置保存，不能成为默认路由。

### 9.6 `model_profiles` 与 `model_capabilities`

`model_profiles`：

- `id`, `provider_profile_id`, `model_id`, `display_name`。
- `enabled`, `discovery_source`：`discovered / manual / migrated`。
- `context_window`, `base_limits_json`。
- 唯一 `(provider_profile_id, model_id)`。
- `revision`, `created_at`, `updated_at`。

`model_capabilities`：

- `id`, `model_profile_id`, `capability_key`。
- `declared_supported`, `adapter_supported`, `contract_verified`。
- `input_modalities_json`, `output_modalities_json`, `parameter_schema_json`。
- `source_urls_json`, `known_limits_json`, `verified_at`, `contract_revision`。
- 唯一 `(model_profile_id, capability_key)`。

产品可用条件固定为：

```text
model.enabled
AND provider.enabled
AND provider.health_status IN (ready, degraded)
AND declared_supported
AND adapter_supported
AND contract_verified
```

`degraded` Provider 是否允许使用由系统配置总线控制，默认只允许已有任务重试，不允许成为新默认路由。

### 9.7 `prompt_profiles`

| 字段 | 说明 |
| --- | --- |
| `id` | 具体版本 ID |
| `profile_key` | 同一逻辑模板的稳定键 |
| `name`, `capability_key` | 名称与产品能力 |
| `version` | `profile_key` 内递增 |
| `status` | `draft / active / archived` |
| `system_prompt`, `task_template` | 正文，只在主动编辑时返回 |
| `variables_schema_json`, `output_schema_json` | 变量与结构化输出契约 |
| `visual_style_prefix`, `safety_constraints_json` | 视觉和安全约束 |
| `content_hash` | 完整性与审计，不写完整正文到日志 |
| `created_from_id`, `created_at`, `activated_at` | 版本来源 |

激活版本不可更新正文。修改操作创建新版本，并由引用更新事务显式切换。

### 9.8 `capability_routes`

- `id`, `capability_key`，P0 系统范围每个能力唯一。
- `primary_model_profile_id`、`fallback_model_profile_id` 可空。
- `prompt_profile_id` 可空但由能力规则决定是否必需。
- `enabled`, `validation_status`：`valid / incomplete / invalid`。
- `validation_issues_json`, `revision`, `created_at`, `updated_at`。

能力键至少包括：

```text
topic_generation, script_generation, script_rewrite,
storyboard_generation, video_deconstruction, speech_to_text,
image_generation, text_to_video, image_to_video,
tts, subtitle_alignment, asset_analysis, embedding
```

### 9.9 `composition_template_profiles`

该系统级模型承接 Pixelle 风格的“模板驱动自动合成”，但不引入手动时间线或任意工作流执行：

| 字段 | 说明 |
| --- | --- |
| `id`, `template_key`, `name` | 版本主键、稳定逻辑键与中文名称 |
| `version`, `status` | 逻辑键内递增版本；`draft / active / archived` |
| `template_type` | `slideshow / talking_head / product_showcase / mixed_media` |
| `aspect_ratios_json` | 允许画幅，例如 `9:16`；不得由页面私自扩展 |
| `parameter_schema_json` | 可配置参数及边界的 JSON Schema |
| `composition_spec_template_json` | 只含受控 `CompositionSpec` 骨架和占位引用，不含可执行脚本 |
| `compatible_capabilities_json` | 所需能力键和最低契约版本 |
| `preview_asset_ref` | 当前工作区可读取的受控预览资产引用，可空 |
| `content_hash`, `revision`, `created_from_id` | 完整性、并发与版本来源 |
| `created_at`, `activated_at` | 审计时间 |

激活版本不可原地改写；新版本必须重新校验参数 Schema、能力依赖和预览引用。P0 只负责模板配置、预览元数据和 Recipe 引用，不执行 P1 批量渲染。

### 9.10 `account_ai_recipes`

| 字段 | 说明 |
| --- | --- |
| `id`, `account_id`, `name` | 主键与账号范围 |
| `version` | 账号内递增 |
| `status` | `draft / active / archived` |
| `route_overrides_json` | 允许的模型 / 路由覆盖引用 |
| `visual_style_json`, `voice_profile_ref` | 风格与音色引用 |
| `composition_template_ref` | 受控模板引用，可空 |
| `cost_policy_json`, `fallback_policy_json` | 成本和回退策略 |
| `source_ai_config_revision` | 创建时系统 AI 修订 |
| `validation_status`, `validation_issues_json` | 可用性 |
| `revision`, `created_from_id`, `created_at`, `activated_at` | 审计 |

Recipe 不保存 Provider 密钥、Base URL、工作流原文或完整系统 Prompt。激活时生成安全的解析摘要；后续生成任务再形成不可变完整配置快照。

### 9.11 `runtime_tasks` 与 `runtime_events`

`runtime_tasks` 必须持久化，至少包含：

- `id`, `scope`, `account_id`, `task_type`, `status`, `completion_kind`, `failure_kind`, `progress`。
- `cancellable`, `timeout_at`, `attempt`, `retry_of_task_id`。
- `config_snapshot_json`：只含安全引用与不可变版本，不含密钥 / 完整 Prompt。
- `result_ref`, `error_code`, `error_log_id`。
- `revision`, `created_at`, `started_at`, `completed_at`, `updated_at`。

`runtime_events` 作为事务 outbox 与有界重放来源：

- `event_id`, `topic`, `sequence`, `event_type`, `account_id`。
- `aggregate_type`, `aggregate_id`, `task_id`, `log_id`, `revision`。
- `payload_json`, `occurred_at`, `published_at`。
- 唯一 `(topic, sequence)`；账号事件必须有 `account_id`。

业务写入、修订递增和 outbox 事件在同一数据库事务提交。发布器只发送已提交事件；Runtime 重启后继续投递未发布事件并恢复非终态任务。

### 9.12 索引与外键

所有账号级表建立 `(account_id, updated_at)` 索引。外键删除策略：

- 账号禁止物理级联删除，P0 只归档。
- Provider 被 Route 或 Recipe 引用时禁止删除，只允许禁用或归档。
- Model 被 Route 引用时禁止删除。
- Prompt 激活版本被 Route 引用时禁止删除。
- KnowledgeSource 可以软删除，索引与快照保留来源墓碑。

## 10. 状态机与业务规则

### 10.1 账号生命周期

允许转换：

```text
draft -> unbound
unbound -> ready
unbound <-> attention
ready <-> attention
draft | unbound | ready | attention -> archived
archived -> draft | unbound | ready | attention
```

状态计算优先级：

1. 显式归档 → `archived`。
2. 六步向导未完成 → `draft`。
3. 缺少真实 ExecutionBinding 或连接从未验证 → `unbound`。
4. 连接失效、知识索引错误 / 规则冲突、必要 AI 能力无有效路由 → `attention`。
5. 连接健康、知识库已创建且无阻断错误、必要 AI Recipe 验证通过 → `ready`。

空知识库允许账号进入 `ready`，但 `knowledgeReadiness` 显示“待补充”；索引失败、过期或规则冲突才阻断为 `attention`。必要 AI 能力清单来自配置总线，禁止硬编码在页面。

`unbound` 只表示“已完成向导，但尚未建立首个有效真实绑定”，不能用于保存中途向导。已经进入 `ready` 或 `attention` 的账号若绑定丢失、解除或失效，统一进入 `attention` 并给出修复动作，不允许 `ready -> unbound`。恢复归档账号时，未完成六步向导的账号回到 `draft`；已完成向导的账号按复检结果进入 `unbound / ready / attention`。

### 10.2 账号就绪摘要

```ts
type SuggestedActionDto = {
  actionKey: "open_connection" | "open_knowledge" | "open_ai_recipe" | "run_health_check" | "view_log";
  label: string;
  routeId: string;
  section: string | null;
  taskId: string | null;
};

type ReadinessItemDto = {
  status: "ready" | "attention" | "blocked" | "missing" | "empty" | "checking";
  label: string;
  errorCode: string | null;
  logId: string | null;
  checkedAt: string | null;
  suggestedAction: SuggestedActionDto | null;
};

type AccountReadinessDto = {
  connection: ReadinessItemDto;
  knowledge: ReadinessItemDto;
  ai: ReadinessItemDto;
  overall: "ready" | "attention" | "blocked";
  checkedAt: string | null;
  suggestedAction: SuggestedActionDto | null;
};
```

每项包含 `status`、中文 `label`、`errorCode`、`logId`、最近验证时间和一个修复动作。UI 不根据字段自行推导总状态。

### 10.3 Provider 健康

```text
unknown -> checking -> ready | degraded | failed
ready | degraded | failed -> checking
```

取消检查回到检查前状态并记录取消；超时进入 `failed`，错误码为 `PROVIDER_CHECK_TIMED_OUT`。

### 10.4 Prompt 版本

```text
draft -> active -> archived
draft -> archived
```

同一 `profile_key` 只允许一个 active。激活新版本和更新 Capability Route 引用可以在一个事务中完成；失败保持原 active 版本和引用。

### 10.5 Recipe 版本

Recipe 采用与 Prompt 相同的不可变激活规则。系统 `aiConfigRevision` 更新后，已激活 Recipe 不被静默改写，只重新计算 `validation_status`；用户确认后创建新 Recipe 版本。

## 11. Runtime API v1 契约

### 11.1 通用约定

- 基础前缀：`/api/v1`。
- JSON 字段：DTO 使用 `camelCase`；成功信封固定为 `ok / data / meta?`，失败信封固定为 `ok / error / error_code / log_id? / fieldErrors? / meta?`。
- 写请求：`Content-Type: application/json; charset=utf-8`。
- 调用方认证：所有 HTTP 请求必须携带 `Authorization: Bearer <runtime_session_token>`。缺失返回 `401 RUNTIME_SESSION_REQUIRED`，无效返回 `401 RUNTIME_SESSION_INVALID`；该 Header 不得进入访问日志、错误信封或前端持久化状态。
- 来源保护：生产请求的 `Host` 必须精确匹配 Supervisor 分配的 `127.0.0.1:{port}`；带 `Origin` 的 HTTP / WebSocket 请求必须匹配受控 Tauri Origin。开发 Origin 只能来自 Bootstrap 白名单，禁止通配和请求反射。
- 资源并发：更新请求使用 `If-Match: "{revision}"`；缺失时允许普通更新的接口必须在文档明确说明。
- 幂等：创建、复制、归档、恢复和任务创建接受 `Idempotency-Key`。
- 请求关联：客户端可传 `X-Operation-ID`；服务端总返回 `X-Request-ID`。
- 许可证：`GET /bootstrap/status`、`GET /bootstrap/license`、`POST /bootstrap/license/activate` 是唯一许可证豁免端点；它们仍要求 Runtime 会话认证。其他 HTTP 与 WebSocket 均同时要求有效 Runtime 会话和有效许可证。
- 列表分页：`cursor`、`limit`；默认值读取 `api.paginationDefaultLimit=50`，最大值读取 `api.paginationMaxLimit=200`。
- 删除：P0 只删除未引用草稿；账号、Provider、激活模型和激活 Prompt 使用归档 / 禁用。

### 11.2 Bootstrap

| 方法 | 地址 | 请求 | 返回 | 关键错误码 |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/bootstrap/status` | 无 | `BootstrapStatusDto` | `RUNTIME_NOT_READY` |
| GET | `/api/v1/bootstrap/license` | 无 | `LicenseStatusDto` | `LICENSE_STORE_UNAVAILABLE` |
| POST | `/api/v1/bootstrap/license/activate` | `LicenseActivationInput` | `LicenseStatusDto` | `LICENSE_INVALID`, `LICENSE_MACHINE_MISMATCH` |
| POST | `/api/v1/bootstrap/directories/initialize` | `DirectoryInitializationInput` | `DirectoryReportDto` | `DIRECTORY_CREATE_FAILED` |
| POST | `/api/v1/bootstrap/self-checks` | `SelfCheckInput` | `TaskAcceptedDto`，HTTP 202 | `SELF_CHECK_ALREADY_RUNNING` |

`BootstrapStatusDto`：

```json
{
  "license": { "status": "active", "machineCode": "full-local-code", "machineCodeMasked": "masked" },
  "directories": { "status": "ready", "issues": [] },
  "runtime": { "status": "ready", "version": "<runtime-version>" },
  "mediaTools": { "status": "attention", "issues": ["FFMPEG_NOT_FOUND"] },
  "canContinue": true,
  "blockingIssues": [],
  "revision": 8
}
```

许可证、目录和 Runtime 是进入壳层的硬门。P0 不要求所有可选媒体工具健康才能进入，但必须显示真实缺口。

### 11.3 账号与工作区上下文

| 方法 | 地址 | 职责 |
| --- | --- | --- |
| GET | `/api/v1/accounts` | 筛选、搜索和分页列出账号 |
| POST | `/api/v1/accounts` | 创建账号草稿 |
| GET | `/api/v1/accounts/{account_id}` | 获取账号详情 |
| PATCH | `/api/v1/accounts/{account_id}` | 更新允许的身份字段 |
| GET | `/api/v1/accounts/{account_id}/workspace-context` | 账号切换 prepare，返回壳数据与就绪摘要 |
| POST | `/api/v1/accounts/{account_id}/workspace-activation` | 账号切换界面提交后记录最近使用时间和账号修订 |
| POST | `/api/v1/accounts/{account_id}/complete-wizard` | 标记向导完成并计算状态 |
| POST | `/api/v1/accounts/{account_id}/copy-config` | 从来源账号复制白名单配置 |
| POST | `/api/v1/accounts/{account_id}/archive` | 归档账号 |
| POST | `/api/v1/accounts/{account_id}/restore` | 恢复并受理健康复检 |
| GET | `/api/v1/accounts/{account_id}/health` | 获取三项就绪和整体状态 |
| POST | `/api/v1/accounts/{account_id}/health-checks` | 受理完整健康检查 |

创建请求：

```json
{
  "name": "北美家居灵感号",
  "username": "homeideas",
  "platform": "tiktok"
}
```

创建响应数据：

```json
{
  "id": "acc_01J...",
  "name": "北美家居灵感号",
  "username": "homeideas",
  "platform": "tiktok",
  "status": "draft",
  "readiness": {
    "connection": {
      "status": "missing",
      "label": "未连接",
      "errorCode": null,
      "logId": null,
      "checkedAt": null,
      "suggestedAction": {
        "actionKey": "open_connection",
        "label": "配置真实连接",
        "routeId": "account_management",
        "section": "connection",
        "taskId": null
      }
    },
    "knowledge": {
      "status": "empty",
      "label": "待补充",
      "errorCode": null,
      "logId": null,
      "checkedAt": null,
      "suggestedAction": {
        "actionKey": "open_knowledge",
        "label": "添加知识来源",
        "routeId": "account_strategy_knowledge",
        "section": "knowledge",
        "taskId": null
      }
    },
    "ai": {
      "status": "missing",
      "label": "AI 配方待配置",
      "errorCode": "AI_RECIPE_REQUIRED",
      "logId": null,
      "checkedAt": null,
      "suggestedAction": {
        "actionKey": "open_ai_recipe",
        "label": "配置 AI 创作档案",
        "routeId": "ai_system_settings",
        "section": "account-recipe",
        "taskId": null
      }
    },
    "overall": "blocked",
    "checkedAt": null,
    "suggestedAction": {
      "actionKey": "open_connection",
      "label": "配置真实连接",
      "routeId": "account_management",
      "section": "connection",
      "taskId": null
    }
  },
  "positioningSummary": null,
  "lastUsedAt": null,
  "wizardCompletedAt": null,
  "revision": 1
}
```

`GET workspace-context` 返回：

```json
{
  "account": {},
  "readiness": {},
  "navigation": {
    "lastRoute": "/workspace",
    "availableRoutes": [
      "account_workspace_home",
      "account_strategy_knowledge",
      "account_script_topic",
      "account_storyboard_planning",
      "account_video_deconstruction",
      "account_batch_production",
      "account_content_library",
      "account_media_toolbox",
      "account_publishing",
      "account_review"
    ]
  },
  "taskSummary": {
    "running": 0,
    "failed": 0
  },
  "workspaceRevision": 12
}
```

`taskSummary` 必须来自真实任务；没有任务返回零是事实性计数，不添加演示数据。`subscriptionRevision` 是 Desktop 管理的 WebSocket 订阅世代，不属于 HTTP 工作区 DTO。

复制请求：

```json
{
  "sourceAccountId": "acc_source",
  "sections": ["positioning", "knowledgeRules", "brandKit", "aiRecipe"]
}
```

目标账号 ID 来自路径。若 `sourceAccountId` 与目标相同返回 `ACCOUNT_COPY_SOURCE_EQUALS_TARGET`。

### 11.4 真实连接与执行绑定

| 方法 | 地址 | 职责 |
| --- | --- | --- |
| GET | `/api/v1/accounts/{account_id}/connection` | 返回账号连接、工作区、浏览器和绑定摘要 |
| GET | `/api/v1/accounts/{account_id}/connection/candidates` | 列出同账号下真实完整的执行绑定候选 |
| PUT | `/api/v1/accounts/{account_id}/connection/binding` | 绑定真实 BrowserInstance / DeviceWorkspace |
| DELETE | `/api/v1/accounts/{account_id}/connection/binding` | 解除绑定，保留审计 |
| POST | `/api/v1/accounts/{account_id}/connection/checks` | 受理真实诊断任务 |

绑定请求只允许引用数据库中存在且可验证的真实对象：

```json
{
  "deviceWorkspaceId": "workspace_01J...",
  "browserInstanceId": "browser_01J..."
}
```

Runtime 服务层只选择数据库中已经存在且账号、DeviceWorkspace、BrowserInstance 三者一致的 `ExecutionBinding`，不得创建或改写环境对象；同一工作区与浏览器组合存在历史绑定时，候选列表和绑定写入都只解析按更新时间与稳定 ID 排序后的最新绑定，避免选择与提交漂移。无候选时返回 `WORKSPACE_UNAVAILABLE`。UI 不提交 `status` 和私有 metadata JSON。

现有旧 DTO 的 `browserInstanceId` 实际可能承载 `device_workspace_id`。迁移时禁止直接写入新 `browser_instance_id`：legacy bridge 必须分别查询 `device_workspaces` 与 `browser_instances`，只在真实外键证据成立时建立引用；无法判定的旧绑定迁为 `unbound` 并生成诊断问题，不猜测映射。

### 11.5 定位、知识、品牌与发布默认值

| 方法 | 地址 | 职责 |
| --- | --- | --- |
| GET | `/api/v1/accounts/{account_id}/positioning` | 列出版本和当前激活版本 |
| POST | `/api/v1/accounts/{account_id}/positioning/versions` | 创建草稿版本 |
| POST | `/api/v1/accounts/{account_id}/positioning/versions/{version}/activate` | 激活版本 |
| GET | `/api/v1/accounts/{account_id}/knowledge` | 获取知识库摘要与规则 |
| PATCH | `/api/v1/accounts/{account_id}/knowledge` | 更新知识规则并递增版本 |
| GET | `/api/v1/accounts/{account_id}/knowledge/sources` | 来源列表 |
| POST | `/api/v1/accounts/{account_id}/knowledge/sources` | 添加真实来源 |
| POST | `/api/v1/accounts/{account_id}/knowledge/index-jobs` | 受理索引任务 |
| DELETE | `/api/v1/accounts/{account_id}/knowledge/sources/{source_id}` | 软删除来源 |
| GET / POST | `/api/v1/accounts/{account_id}/knowledge/snapshots` | 列出 / 创建不可变知识快照 |
| GET | `/api/v1/accounts/{account_id}/knowledge/snapshots/{snapshot_id}` | 查看快照清单与来源证据 |
| GET / PUT | `/api/v1/accounts/{account_id}/brand-kit` | 获取 / 创建新 BrandKit 版本 |
| GET / PUT | `/api/v1/accounts/{account_id}/publish-defaults` | 获取 / 更新发布默认值 |

来源上传、文件选择与 Tauri 文件访问必须使用受控文件引用；API 不接受任意客户端绝对路径字符串。

### 11.6 账号 AI Recipe

| 方法 | 地址 | 职责 |
| --- | --- | --- |
| GET | `/api/v1/accounts/{account_id}/ai-recipe` | 当前激活版本、解析摘要和验证问题 |
| GET | `/api/v1/accounts/{account_id}/ai-recipe/versions` | 版本列表 |
| POST | `/api/v1/accounts/{account_id}/ai-recipe/versions` | 创建新版本 |
| POST | `/api/v1/accounts/{account_id}/ai-recipe/versions/{version}/validate` | 校验系统继承与覆盖 |
| POST | `/api/v1/accounts/{account_id}/ai-recipe/versions/{version}/activate` | 激活已验证版本 |

创建 Recipe 不接受 Provider 密钥、Base URL 或完整 Prompt。引用不存在、模型未验证或覆盖越界返回 `AI_RECIPE_INVALID` 和字段级问题。

### 11.7 Provider 与模型

| 方法 | 地址 | 职责 |
| --- | --- | --- |
| GET / POST | `/api/v1/system/providers` | 列表 / 新建 Provider |
| GET / PATCH | `/api/v1/system/providers/{provider_id}` | 详情 / 更新非敏感字段 |
| PUT | `/api/v1/system/providers/{provider_id}/credential` | 写入安全存储并返回引用摘要 |
| POST | `/api/v1/system/providers/{provider_id}/checks` | 受理连接检查 |
| POST | `/api/v1/system/providers/{provider_id}/model-discovery` | 受理模型发现 |
| GET / POST | `/api/v1/system/models` | 列表 / 手动添加模型 |
| GET / PATCH | `/api/v1/system/models/{model_profile_id}` | 详情 / 启停与显示字段 |
| GET | `/api/v1/system/model-capabilities` | 跨模型筛选能力、来源和契约验证状态 |
| GET | `/api/v1/system/models/{model_profile_id}/capabilities` | 能力与契约来源 |
| POST | `/api/v1/system/models/{model_profile_id}/capability-checks` | 受理契约验证 |

写入凭据请求正文只在内存中存在，日志仅记录 Provider ID、字段名、长度和安全摘要。响应：

```json
{
  "credentialRef": "secret://providers/prov_01J...",
  "maskedValue": "sk-••••••••4f2a",
  "updatedAt": "2026-07-20T10:00:00Z"
}
```

### 11.8 Capability Route 与 Prompt Profile

| 方法 | 地址 | 职责 |
| --- | --- | --- |
| GET | `/api/v1/system/capability-routes` | 路由列表与验证状态 |
| PUT | `/api/v1/system/capability-routes/{capability_key}` | 原子更新主模型、回退模型与 Prompt |
| POST | `/api/v1/system/capability-routes/{capability_key}/validate` | 重新验证 |
| GET / POST | `/api/v1/system/prompt-profiles` | 列表 / 创建逻辑模板首版本 |
| GET | `/api/v1/system/prompt-profiles/{profile_key}` | 版本摘要与引用 |
| GET | `/api/v1/system/prompt-profiles/{profile_key}/versions/{version}` | 主动加载具体正文 |
| POST | `/api/v1/system/prompt-profiles/{profile_key}/versions` | 创建新版本 |
| POST | `/api/v1/system/prompt-profiles/{profile_key}/versions/{version}/activate` | 激活版本 |

更新 Capability Route 使用一个请求完成全部引用更新，禁止页面按字段连续保存形成半配置。

#### 11.8.1 Composition Template Profile

| 方法 | 地址 | 职责 |
| --- | --- | --- |
| GET / POST | `/api/v1/system/composition-templates` | 列表 / 创建逻辑模板首版本 |
| GET | `/api/v1/system/composition-templates/{template_key}` | 版本摘要、兼容能力与引用数量 |
| GET | `/api/v1/system/composition-templates/{template_key}/versions/{version}` | 加载具体受控模板与参数 Schema |
| POST | `/api/v1/system/composition-templates/{template_key}/versions` | 从已知版本创建新草稿版本 |
| POST | `/api/v1/system/composition-templates/{template_key}/versions/{version}/validate` | 校验 Schema、能力和预览引用 |
| POST | `/api/v1/system/composition-templates/{template_key}/versions/{version}/activate` | 激活已验证版本 |

模板 API 只保存声明式 `CompositionSpec` 骨架；拒绝任意可执行代码、Shell、绝对路径和未注册节点。创建 / 激活分别发送 `composition.template.updated` / `composition.template.activated`，并失效模板列表、引用该模板的 Recipe 验证摘要。

### 11.9 系统配置、诊断与任务

| 方法 | 地址 | 职责 |
| --- | --- | --- |
| GET / PATCH | `/api/v1/system/config` | 读取 / 更新统一配置总线 |
| GET | `/api/v1/system/diagnostics` | Runtime、数据库、工作区、日志和依赖摘要 |
| GET | `/api/v1/system/logs/{log_id}` | 返回已脱敏错误摘要和建议动作 |
| GET | `/api/v1/system/tasks/{task_id}` | 系统任务状态 |
| POST | `/api/v1/system/tasks/{task_id}/cancel` | 取消系统任务 |
| GET | `/api/v1/accounts/{account_id}/tasks/{task_id}` | 账号任务状态 |
| POST | `/api/v1/accounts/{account_id}/tasks/{task_id}/cancel` | 取消账号任务 |

日志详情 API 不返回完整日志文件，只返回当前用户可安全查看的结构化片段；打开原始日志目录由 Tauri 受控命令完成。

### 11.10 WebSocket 协议

连接地址固定为 `/api/v1/ws`。令牌通过受控 `Sec-WebSocket-Protocol` 传递并整体脱敏，禁止放在 URL Query。连接建立后，客户端发送逐 Topic 订阅帧：

```json
{
  "type": "subscribe",
  "subscriptionRevision": 8,
  "accountId": "acc_01J...",
  "topics": [
    {
      "topic": "system:health",
      "lastEventId": "evt_system_41",
      "afterSequence": 41
    },
    {
      "topic": "account:acc_01J...:tasks",
      "lastEventId": "evt_account_19",
      "afterSequence": 19
    }
  ]
}
```

`accountId` 可空；为空时只允许订阅 `system:*`。非空时只允许该账号的 `account:{accountId}:*` 与授权的系统 Topic，不允许一个连接混订多个账号。服务端逐项验证 `(topic, lastEventId, afterSequence)` 后返回 `subscribed` 确认及每个 Topic 的当前 sequence；任一账号范围不匹配时整帧拒绝并记录 `ACCOUNT_SCOPE_MISMATCH`。

事件信封：

```json
{
  "schemaVersion": 1,
  "eventId": "evt_01J...",
  "eventType": "account.health.updated",
  "topic": "account:acc_01J...:workspace",
  "sequence": 42,
  "occurredAt": "2026-07-20T10:00:00Z",
  "accountId": "acc_01J...",
  "resourceType": "account",
  "resourceId": "acc_01J...",
  "taskId": null,
  "revision": 13,
  "payload": {}
}
```

P0 事件：

- `bootstrap.license.changed / bootstrap.directories.changed`
- `runtime.health.updated`
- `config.changed`
- `account.created / account.updated / account.workspace.activated / account.config.copied`
- `account.health.updated`
- `account.archived`
- `account.connection.updated`
- `positioning.version.created / positioning.version.activated`
- `knowledge.rules.updated / knowledge.source.created / knowledge.source.removed / knowledge.snapshot.created / knowledge.index.updated`
- `brand-kit.updated / publish.defaults.updated`
- `provider.updated / provider.credential.updated / provider.health.updated`
- `model.updated / model.capability.updated`
- `prompt.profile.updated / prompt.profile.activated`
- `composition.template.updated / composition.template.activated`
- `ai.config.changed`
- `ai.recipe.updated`
- `task.queued / task.started / task.progress / task.cancelling / task.completed / task.failed`；`task.completed` 携带 `completionKind`，`task.failed` 携带 `failureKind`

服务端只向订阅该账号的连接发送账号事件；不得先全局广播再依赖 UI 过滤。

每个 Topic 独立使用单调 `sequence` 和有界重放缓冲区，大小由配置总线管理。不存在跨 Topic 的单一游标。重连时对订阅帧中的每一项分别处理：

- `lastEventId`、`afterSequence` 均属于该 Topic 且仍在缓冲区：从 `afterSequence + 1` 顺序重放。
- 两个游标互相矛盾：只拒绝该订阅帧，返回 `WS_CURSOR_MISMATCH`，不猜测位置。
- 某 Topic 游标已过期：只针对该 Topic 发送 `sync.required`，前端通过对应 HTTP 资源补拉最终状态，然后以确认帧给出的当前 sequence 重新订阅。
- 游标属于其他账号或 Topic：整帧拒绝并记录 `ACCOUNT_SCOPE_MISMATCH`，不泄露目标 Topic 是否存在。
- 前端按 `eventId` 去重，并以 HTTP 最终对象为真源；事件不能替代数据库状态。

### 11.11 规范性 DTO 与逐端点契约

本节与 11.2–11.10 共同构成 P0 实施前已经冻结的接口契约，不得把参数、返回、错误、失效或事件留待编码时临时决定。`docs/api/v1/` 只按本节拆分成便于前后端阅读的文件，并由 OpenAPI / 路由注册表测试校验，不产生第二套语义。

#### 11.11.1 信封、分页与公共参数

所有成功响应使用：

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "revision": 3,
    "invalidations": ["account:acc_01J...:workspace"],
    "nextCursor": null
  }
}
```

所有失败响应使用：

```json
{
  "ok": false,
  "error": "数据已被其他操作更新，请重新加载后再试。",
  "error_code": "REVISION_CONFLICT",
  "log_id": "log_01J...",
  "fieldErrors": []
}
```

约束：

- 请求关联以 `X-Request-ID` Header 为准；`meta` 只在需要返回修订、失效项或游标时出现。`revision` 只在资源或聚合有修订时存在；读请求一旦返回 `meta.invalidations`，其值固定为空数组。
- `log_id` 只在用户可见错误或诊断记录已经实际生成时返回；不得为普通校验错误伪造空日志引用。
- 列表 Query 统一为 `cursor?: string`、`limit?: 1..configuredMax`；默认值读取 `api.paginationDefaultLimit=50`，最大值读取 `api.paginationMaxLimit=200`，两者只允许由配置总线管理。账号列表另有 `q?: string`、`status?: draft|unbound|ready|attention|archived`。
- 所有行隐含公共 Header `Authorization`；写入行中标记 `rev` 的必须携带 `If-Match`，标记 `idem` 的必须携带 `Idempotency-Key`。
- 所有行都可能返回公共错误 `RUNTIME_SESSION_REQUIRED`、`RUNTIME_SESSION_INVALID`、`RUNTIME_HOST_INVALID`、`RUNTIME_ORIGIN_FORBIDDEN`、`REQUEST_VALIDATION_FAILED`、`REQUEST_TIMEOUT`、`INTERNAL_ERROR`；除三条许可证豁免端点外还可能返回 `LICENSE_INVALID`。表内只重复该端点额外领域错误。
- `account_id`、`source_id`、`snapshot_id`、`task_id`、`provider_id`、`model_profile_id`、`profile_key`、`template_key` 是非空、最大 128 字符的稳定 ID；非法格式返回 `REQUEST_VALIDATION_FAILED`，不存在返回对应 `*_NOT_FOUND`。

规范性输入 DTO：

```ts
type LicenseActivationInput = { licenseKey: string };
type DirectoryInitializationInput = { workspaceRootRef: string | null };
type SelfCheckInput = { checks: Array<"database" | "directories" | "media_tools" | "runtime"> };

type AccountCreateInput = { name: string; username?: string | null; platform: "tiktok" };
type AccountPatchInput = { name?: string; username?: string | null; avatarAssetRef?: string | null };
type CompleteWizardInput = { completedSteps: Array<"identity" | "connection" | "positioning" | "knowledge" | "ai_recipe" | "health"> };
type AccountCopyInput = { sourceAccountId: string; sections: Array<"positioning" | "knowledgeRules" | "brandKit" | "aiRecipe" | "publishDefaults"> };
type ArchiveInput = { reason?: string | null };
type HealthCheckInput = { checks?: Array<"connection" | "knowledge" | "ai"> };

type ConnectionBindingInput = { deviceWorkspaceId: string; browserInstanceId: string };
type PositioningVersionInput = { audience: object; contentPillars: string[]; tone: object; prohibitedTopics: string[]; publishingConstraints: object };
type KnowledgeRulesPatchInput = { inclusionRules: object; exclusionRules: object; citationPolicy: object };
type KnowledgeSourceInput = { kind: "document" | "image" | "video" | "audio" | "text" | "reference"; sourceMode: "file" | "url" | "text"; controlledFileRef?: string; url?: string; title: string; text?: string };
type KnowledgeSnapshotInput = { sourceIds: string[]; label?: string | null };
type BrandKitVersionInput = { colors: string[]; fonts: string[]; logoAssetRefs: string[]; visualRules: object; voiceRules: object };
type PublishDefaultsInput = { timezone: string; privacyLevel: string; allowComments: boolean; allowDuet: boolean; allowStitch: boolean; captionRules: object };

type AccountAIRecipeVersionInput = { name: string; routeOverrides: object; visualStyle: object; voiceProfileRef?: string | null; compositionTemplateRef?: string | null; costPolicy: object; fallbackPolicy: object };
type ProviderCreateInput = { name: string; adapterType: "direct_api" | "openai_compatible" | "comfyui" | "runninghub"; baseUrl: string; region?: string | null; timeoutMs: number; maxConcurrency: number; enabled: boolean };
type ProviderPatchInput = Partial<Omit<ProviderCreateInput, "adapterType">>;
type ProviderCredentialInput = { credential: string };
type ModelCreateInput = { providerProfileId: string; modelId: string; displayName: string; enabled: boolean; baseLimits?: object };
type ModelPatchInput = { displayName?: string; enabled?: boolean; baseLimits?: object };
type CapabilityCheckInput = { capabilityKeys?: string[]; force?: boolean };
type CapabilityRouteInput = { primaryModelProfileId: string | null; fallbackModelProfileId: string | null; promptProfileId: string | null; enabled: boolean };
type PromptProfileInput = { profileKey: string; name: string; capabilityKey: string; systemPrompt: string; taskTemplate: string; variablesSchema: object; outputSchema: object; visualStylePrefix?: string; safetyConstraints: object };
type PromptVersionInput = Omit<PromptProfileInput, "profileKey" | "capabilityKey"> & { createdFromVersion: number };
type CompositionTemplateInput = { templateKey: string; name: string; templateType: "slideshow" | "talking_head" | "product_showcase" | "mixed_media"; aspectRatios: string[]; parameterSchema: object; compositionSpecTemplate: object; compatibleCapabilities: object; previewAssetRef?: string | null };
type CompositionTemplateVersionInput = Omit<CompositionTemplateInput, "templateKey" | "templateType"> & { createdFromVersion: number };
type SystemConfigPatchInput = { values: Record<string, unknown> };
```

规范性输出 DTO 至少包含下列字段；服务端可以增加向后兼容的只读字段，但不得改变字段含义：

```ts
type TaskAcceptedDto = { taskId: string; scope: "system" | "account"; accountId: string | null; taskType: string; status: "queued"; cancellable: boolean; createdAt: string };
type TaskDto = Omit<TaskAcceptedDto, "status" | "cancellable"> & { status: "queued" | "running" | "cancelling" | "failed" | "completed"; cancellable: boolean; completionKind: "succeeded" | "cancelled" | null; failureKind: "error" | "timed_out" | "restart_interrupted" | null; progress: number; resultRef: string | null; errorCode: string | null; logId: string | null; revision: number };
type LicenseStatusDto = { status: "missing" | "active" | "expired" | "invalid" | "machine_mismatch"; machineCode: string; machineCodeMasked: string; expiresAt: string | null; activatedAt: string | null; blockingIssue: { code: string; message: string } | null; revision: number };
type DirectoryReportDto = { status: "ready" | "attention" | "failed"; workspaceRootDisplay: string; directories: Array<{ key: string; status: "ready" | "created" | "failed"; writable: boolean }>; issues: Array<{ code: string; message: string; logId: string | null }>; revision: number };
type BootstrapStatusDto = { license: LicenseStatusDto; directories: DirectoryReportDto; runtime: { status: "starting" | "ready" | "failed"; version: string }; mediaTools: { status: "ready" | "attention" | "failed"; issues: string[] }; canContinue: boolean; blockingIssues: Array<{ code: string; message: string; logId: string | null }>; revision: number };
type AccountDto = { id: string; name: string; username: string | null; platform: "tiktok"; status: "draft" | "unbound" | "ready" | "attention" | "archived"; readiness: AccountReadinessDto; positioningSummary: string | null; lastUsedAt: string | null; wizardCompletedAt: string | null; revision: number };
type AccountListDto = { items: AccountDto[]; totalKnown: number | null };
type AccountWorkspaceRouteId = "account_workspace_home" | "account_strategy_knowledge" | "account_script_topic" | "account_storyboard_planning" | "account_video_deconstruction" | "account_batch_production" | "account_content_library" | "account_media_toolbox" | "account_publishing" | "account_review";
type AccountWorkspaceContextDto = { account: AccountDto; readiness: AccountReadinessDto; navigation: { lastRoute: string; availableRoutes: AccountWorkspaceRouteId[] }; taskSummary: { running: number; failed: number }; workspaceRevision: number };
type AccountConfigCopyResultDto = { runId: string; sourceAccountId: string; targetAccountId: string; requestedSections: string[]; copiedSections: string[]; skippedSections: Array<{ section: string; reasonCode: string }>; status: "succeeded"; targetRevision: number; completedAt: string };
type DeviceWorkspaceSummaryDto = { id: string; name: string; status: string };
type BrowserInstanceSummaryDto = { id: string; name: string; status: string; lastCheckedAt: string | null };
type ExecutionBindingSummaryDto = { id: string; status: string; deviceWorkspaceId: string; browserInstanceId: string };
type ConnectionCandidateDto = { deviceWorkspace: DeviceWorkspaceSummaryDto; browserInstance: BrowserInstanceSummaryDto; executionBinding: ExecutionBindingSummaryDto };
type ConnectionCandidatesDto = { items: ConnectionCandidateDto[] };
type ConnectionDto = { accountId: string; deviceWorkspace: DeviceWorkspaceSummaryDto | null; browserInstance: BrowserInstanceSummaryDto | null; executionBinding: ExecutionBindingSummaryDto | null; lastCheck: object | null; revision: number };
type PositioningDto = { accountId: string; activeVersion: number | null; versions: Array<{ version: number; status: string; summary: string; createdAt: string }>; revision: number };
type PositioningVersionDto = { id: string; accountId: string; version: number; status: "draft" | "active" | "archived"; audience: object; contentPillars: string[]; tone: object; prohibitedTopics: string[]; publishingConstraints: object; contentHash: string; createdAt: string; activatedAt: string | null; revision: number };
type KnowledgeDto = { accountId: string; rulesVersion: number; sourceCounts: Record<string, number>; latestSnapshotId: string | null; readiness: object; revision: number };
type KnowledgeSourceDto = { id: string; accountId: string; kind: "document" | "image" | "video" | "audio" | "text" | "reference"; sourceMode: "file" | "url" | "text"; title: string; status: "pending" | "indexing" | "ready" | "failed" | "stale" | "removed"; controlledRef: string | null; sourceUrl: string | null; contentHash: string | null; indexedAt: string | null; removedAt: string | null; errorCode: string | null; logId: string | null; revision: number };
type KnowledgeSourcePageDto = { items: KnowledgeSourceDto[]; totalKnown: number | null };
type KnowledgeSnapshotDto = { id: string; accountId: string; label: string | null; sourceIds: string[]; sourceEvidence: Array<{ sourceId: string; contentHash: string; indexedRevision: number }>; rulesVersion: number; contentHash: string; createdAt: string };
type KnowledgeSnapshotPageDto = { items: KnowledgeSnapshotDto[]; totalKnown: number | null };
type BrandKitDto = { accountId: string; activeVersion: number | null; versions: Array<{ version: number; status: "draft" | "active" | "archived"; contentHash: string; createdAt: string }>; active: { colors: string[]; fonts: string[]; logoAssetRefs: string[]; visualRules: object; voiceRules: object } | null; revision: number };
type PublishDefaultsDto = { accountId: string; timezone: string; privacyLevel: string; allowComments: boolean; allowDuet: boolean; allowStitch: boolean; captionRules: object; revision: number };
type AIRecipeDto = { accountId: string; activeVersion: number | null; versions: Array<{ version: number; status: string; validationStatus: string }>; resolvedSummary: object | null; revision: number };
type AIRecipeVersionDto = { id: string; accountId: string; version: number; status: "draft" | "active" | "archived"; name: string; routeOverrides: object; visualStyle: object; voiceProfileRef: string | null; compositionTemplateRef: string | null; costPolicy: object; fallbackPolicy: object; sourceAiConfigRevision: number; validationStatus: "unvalidated" | "valid" | "invalid"; validationIssues: Array<{ code: string; field: string | null; message: string }>; contentHash: string; createdAt: string; activatedAt: string | null; revision: number };
type AIRecipeVersionPageDto = { items: AIRecipeVersionDto[]; totalKnown: number | null };
type AIRecipeValidationDto = { accountId: string; version: number; validationStatus: "valid" | "invalid"; validationIssues: Array<{ code: string; field: string | null; message: string; suggestedAction: string | null }>; resolvedRouteSummary: Record<string, { modelProfileId: string; promptProfileId: string | null; source: "system" | "account_override" }>; sourceAiConfigRevision: number };
type ProviderDto = { id: string; name: string; adapterType: string; baseUrl: string; credential: { configured: boolean; maskedValue: string | null }; enabled: boolean; healthStatus: string; revision: number };
type ProviderPageDto = { items: ProviderDto[]; totalKnown: number | null };
type CredentialSummaryDto = { credentialRef: string; configured: true; maskedValue: string; updatedAt: string; providerRevision: number };
type ModelProfileDto = { id: string; providerProfileId: string; modelId: string; displayName: string; enabled: boolean; discoverySource: string; capabilities: ModelCapabilityDto[]; revision: number };
type ModelCapabilityDto = { capabilityKey: string; declaredSupported: boolean; adapterSupported: boolean; contractVerified: boolean; availability: "available" | "unverified" | "unavailable"; verifiedAt: string | null; contractRevision: number };
type ModelPageDto = { items: ModelProfileDto[]; totalKnown: number | null };
type ModelCapabilityPageDto = { items: Array<ModelCapabilityDto & { modelProfileId: string; providerProfileId: string }>; totalKnown: number | null };
type CapabilityRouteDto = { capabilityKey: string; primaryModelProfileId: string | null; fallbackModelProfileId: string | null; promptProfileId: string | null; enabled: boolean; validationStatus: "valid" | "incomplete" | "invalid"; validationIssues: object[]; revision: number };
type CapabilityRoutePageDto = { items: CapabilityRouteDto[]; totalKnown: number | null };
type PromptProfileDto = { profileKey: string; name: string; capabilityKey: string; activeVersion: number | null; activeVersionId: string | null; versions: Array<{ version: number; status: string; contentHash: string }>; referenceCount: number; revision: number };
type PromptProfilePageDto = { items: PromptProfileDto[]; totalKnown: number | null };
type PromptVersionDto = { id: string; profileKey: string; name: string; capabilityKey: string; version: number; status: "draft" | "active" | "archived"; systemPrompt: string; taskTemplate: string; variablesSchema: object; outputSchema: object; visualStylePrefix: string; safetyConstraints: object; contentHash: string; createdFromId: string | null; createdAt: string; activatedAt: string | null; revision: number };
type CompositionTemplateDto = { templateKey: string; name: string; templateType: string; activeVersion: number | null; activeVersionId: string | null; versions: Array<{ version: number; status: string; contentHash: string }>; compatibleCapabilities: object; referenceCount: number; revision: number };
type CompositionTemplatePageDto = { items: CompositionTemplateDto[]; totalKnown: number | null };
type CompositionTemplateVersionDto = { id: string; templateKey: string; name: string; templateType: "slideshow" | "talking_head" | "product_showcase" | "mixed_media"; version: number; status: "draft" | "active" | "archived"; aspectRatios: string[]; parameterSchema: object; compositionSpecTemplate: object; compatibleCapabilities: object; previewAssetRef: string | null; contentHash: string; createdFromId: string | null; createdAt: string; activatedAt: string | null; revision: number };
type CompositionTemplateValidationDto = { templateKey: string; version: number; validationStatus: "valid" | "invalid"; validationIssues: Array<{ code: string; field: string | null; message: string }>; verifiedCapabilities: string[]; checkedAt: string };
type SystemConfigDto = { values: Record<string, unknown>; writableKeys: string[]; restartRequiredKeys: string[]; revision: number };
type DiagnosticsDto = { runtime: object; database: object; directories: object; mediaTools: object; sidecar: object; checkedAt: string };
type SafeLogExcerptDto = { logId: string; severity: "info" | "warning" | "error"; summary: string; errorCode: string | null; stage: string | null; occurredAt: string; suggestedActions: string[]; requestId: string | null; operationId: string | null };
type RuntimeEventDto = { schemaVersion: 1; eventId: string; eventType: string; topic: string; sequence: number; occurredAt: string; accountId: string | null; resourceType: string | null; resourceId: string | null; taskId: string | null; revision: number | null; payload: object };
type SubscribeFrame = { type: "subscribe"; subscriptionRevision: number; accountId: string | null; topics: Array<{ topic: string; lastEventId: string | null; afterSequence: number | null }> };
type SubscribedFrame = { type: "subscribed"; subscriptionRevision: number; topics: Array<{ topic: string; currentSequence: number; replayedCount: number }> };
```

#### 11.11.2 Bootstrap 与账号契约矩阵

| 方法与地址 | Path / Query / Header / Body | 成功 | 额外错误 | 失效与事件 |
| --- | --- | --- | --- | --- |
| `GET /bootstrap/status` | 无额外参数；许可证豁免 | 200 `BootstrapStatusDto` | `RUNTIME_NOT_READY` | 无 |
| `GET /bootstrap/license` | 无额外参数；许可证豁免 | 200 `LicenseStatusDto` | `LICENSE_STORE_UNAVAILABLE` | 无 |
| `POST /bootstrap/license/activate` | `idem`; `LicenseActivationInput`；许可证豁免 | 200 `LicenseStatusDto` | `LICENSE_INVALID`, `LICENSE_MACHINE_MISMATCH` | `bootstrap`, `bootstrap.license.changed` |
| `POST /bootstrap/directories/initialize` | `idem`; `DirectoryInitializationInput` | 200 `DirectoryReportDto` | `DIRECTORY_CREATE_FAILED` | `bootstrap`, `bootstrap.directories.changed` |
| `POST /bootstrap/self-checks` | `idem`; `SelfCheckInput` | 202 `TaskAcceptedDto` | `SELF_CHECK_ALREADY_RUNNING` | `system:tasks`, `task.queued` |
| `GET /accounts` | Query `q,status,cursor,limit` | 200 `AccountListDto`; `meta.nextCursor` | 无 | 无 |
| `POST /accounts` | `idem`; `AccountCreateInput` | 201 `AccountDto` | `ACCOUNT_PLATFORM_UNSUPPORTED`, `ACCOUNT_USERNAME_INVALID` | `accounts:list`, `account.created` |
| `GET /accounts/{account_id}` | Path `account_id` | 200 `AccountDto` | `ACCOUNT_NOT_FOUND` | 无 |
| `PATCH /accounts/{account_id}` | Path；`rev`; `AccountPatchInput` | 200 `AccountDto` | `ACCOUNT_NOT_FOUND`, `ACCOUNT_ARCHIVED`, `REVISION_CONFLICT` | `account:{id}:detail,workspace`, `account.updated` |
| `GET /accounts/{account_id}/workspace-context` | Path；Query `include=readiness,taskSummary,navigation` 可重复 | 200 `AccountWorkspaceContextDto` | `ACCOUNT_NOT_FOUND`, `ACCOUNT_ARCHIVED` | 无 |
| `POST /accounts/{account_id}/workspace-activation` | Path；`rev,idem`; 无 Body | 200 `AccountDto` | `ACCOUNT_NOT_FOUND`, `ACCOUNT_ARCHIVED`, `REVISION_CONFLICT`, `REQUEST_CONFLICT` | `accounts:list,current-context,detail,workspace`，`account.workspace.activated` |
| `POST /accounts/{account_id}/complete-wizard` | Path；`rev,idem`; `CompleteWizardInput` | 200 `AccountDto` | `ACCOUNT_STATE_TRANSITION_INVALID`, `ACCOUNT_WIZARD_INCOMPLETE`, `REVISION_CONFLICT` | `detail,workspace,accounts:list`, `account.updated` |
| `POST /accounts/{account_id}/copy-config` | Path；`rev,idem`; `AccountCopyInput` | 200 `AccountConfigCopyResultDto` | `ACCOUNT_COPY_SECTION_INVALID`, `ACCOUNT_COPY_SOURCE_EQUALS_TARGET`, `REVISION_CONFLICT` | 目标账号 `detail,workspace,readiness`，`account.config.copied` |
| `POST /accounts/{account_id}/archive` | Path；`rev,idem`; `ArchiveInput` | 200 `AccountDto` | `ACCOUNT_STATE_TRANSITION_INVALID`, `REVISION_CONFLICT` | `accounts:list,current-context`，`account.archived` |
| `POST /accounts/{account_id}/restore` | Path；`rev,idem`; `HealthCheckInput` | 202 `TaskAcceptedDto` | `ACCOUNT_STATE_TRANSITION_INVALID`, `TASK_ALREADY_RUNNING` | `accounts:list,account:tasks`，`task.queued` |
| `GET /accounts/{account_id}/health` | Path | 200 `AccountReadinessDto` | `ACCOUNT_NOT_FOUND` | 无 |
| `POST /accounts/{account_id}/health-checks` | Path；`idem`; `HealthCheckInput` | 202 `TaskAcceptedDto` | `TASK_ALREADY_RUNNING` | `account:tasks,readiness`，`task.queued` |

#### 11.11.3 连接、定位、知识与默认值契约矩阵

| 方法与地址 | 参数 | 成功 | 额外错误 | 失效与事件 |
| --- | --- | --- | --- | --- |
| `GET /accounts/{account_id}/connection` | Path | 200 `ConnectionDto` | `ACCOUNT_NOT_FOUND` | 无 |
| `GET /accounts/{account_id}/connection/candidates` | Path | 200 `ConnectionCandidatesDto` | `ACCOUNT_NOT_FOUND`, `ACCOUNT_ARCHIVED` | 无 |
| `PUT /accounts/{account_id}/connection/binding` | Path；`rev,idem`; `ConnectionBindingInput` | 200 `ConnectionDto` | `WORKSPACE_UNAVAILABLE`, `BROWSER_INSTANCE_NOT_FOUND`, `EXECUTION_BINDING_INVALID`, `REVISION_CONFLICT` | `connection,readiness,workspace`，`account.connection.updated` |
| `DELETE /accounts/{account_id}/connection/binding` | Path；`rev,idem`; 无 Body | 200 `ConnectionDto` | `ACCOUNT_CONNECTION_REQUIRED`, `REVISION_CONFLICT` | 同上；`account.connection.updated` |
| `POST /accounts/{account_id}/connection/checks` | Path；`idem`; `HealthCheckInput` | 202 `TaskAcceptedDto` | `TASK_ALREADY_RUNNING`, `WORKSPACE_UNAVAILABLE` | `account:tasks,connection`，`task.queued` |
| `GET /accounts/{account_id}/positioning` | Path | 200 `PositioningDto` | `ACCOUNT_NOT_FOUND` | 无 |
| `POST /accounts/{account_id}/positioning/versions` | Path；`rev,idem`; `PositioningVersionInput` | 201 `PositioningVersionDto` | `POSITIONING_INVALID`, `REVISION_CONFLICT` | `positioning,workspace`，`positioning.version.created` |
| `POST /accounts/{account_id}/positioning/versions/{version}/activate` | Path；`rev,idem`; 无 Body | 200 `PositioningDto` | `POSITIONING_VERSION_NOT_FOUND`, `POSITIONING_INVALID`, `REVISION_CONFLICT` | `positioning,workspace,readiness`，`positioning.version.activated` |
| `GET /accounts/{account_id}/knowledge` | Path | 200 `KnowledgeDto` | `ACCOUNT_NOT_FOUND` | 无 |
| `PATCH /accounts/{account_id}/knowledge` | Path；`rev`; `KnowledgeRulesPatchInput` | 200 `KnowledgeDto` | `KNOWLEDGE_RULES_INVALID`, `REVISION_CONFLICT` | `knowledge,workspace,readiness`，`knowledge.rules.updated` |
| `GET /accounts/{account_id}/knowledge/sources` | Path；Query `kind,status,cursor,limit` | 200 `KnowledgeSourcePageDto` | 无 | 无 |
| `POST /accounts/{account_id}/knowledge/sources` | Path；`idem`; `KnowledgeSourceInput` | 201 `KnowledgeSourceDto` | `KNOWLEDGE_SOURCE_INVALID`, `CONTROLLED_FILE_REF_INVALID` | `knowledge,sources`，`knowledge.source.created` |
| `DELETE /accounts/{account_id}/knowledge/sources/{source_id}` | Path；`rev,idem` | 200 `KnowledgeSourceDto` 墓碑 | `KNOWLEDGE_SOURCE_NOT_FOUND`, `REVISION_CONFLICT` | `knowledge,sources,readiness`，`knowledge.source.removed` |
| `POST /accounts/{account_id}/knowledge/index-jobs` | Path；`idem`; `{ sourceIds?: string[] }` | 202 `TaskAcceptedDto` | `KNOWLEDGE_SOURCE_INVALID`, `TASK_ALREADY_RUNNING` | `account:tasks,knowledge`，`task.queued` |
| `GET /accounts/{account_id}/knowledge/snapshots` | Path；Query `cursor,limit` | 200 `KnowledgeSnapshotPageDto` | 无 | 无 |
| `POST /accounts/{account_id}/knowledge/snapshots` | Path；`idem`; `KnowledgeSnapshotInput` | 201 `KnowledgeSnapshotDto` | `KNOWLEDGE_SNAPSHOT_INVALID` | `knowledge,snapshots`，`knowledge.snapshot.created` |
| `GET /accounts/{account_id}/knowledge/snapshots/{snapshot_id}` | Path | 200 `KnowledgeSnapshotDto` | `KNOWLEDGE_SNAPSHOT_NOT_FOUND` | 无 |
| `GET /accounts/{account_id}/brand-kit` | Path | 200 `BrandKitDto` | `ACCOUNT_NOT_FOUND` | 无 |
| `PUT /accounts/{account_id}/brand-kit` | Path；`rev,idem`; `BrandKitVersionInput` | 200 `BrandKitDto` | `BRAND_KIT_INVALID`, `REVISION_CONFLICT` | `brand-kit,workspace`，`brand-kit.updated` |
| `GET /accounts/{account_id}/publish-defaults` | Path | 200 `PublishDefaultsDto` | `ACCOUNT_NOT_FOUND` | 无 |
| `PUT /accounts/{account_id}/publish-defaults` | Path；`rev`; `PublishDefaultsInput` | 200 `PublishDefaultsDto` | `PUBLISH_DEFAULTS_INVALID`, `REVISION_CONFLICT` | `publish-defaults,workspace`，`publish.defaults.updated` |

#### 11.11.4 AI Recipe 与系统 AI 契约矩阵

P0-E 实现勘误：`prompt_profiles` 必须持久化 `revision`，
`account_ai_recipes` 必须持久化 `content_hash`；由
`0020_p0e_ai_vertical_chain` 对迁移对象做确定性回填并收紧约束。
`PromptProfileDto` 与 `CompositionTemplateDto` 增加
`activeVersionId: string | null`，供 Route 与 Recipe 按真实不可变版本外键
引用；`activeVersion` 继续用于展示，禁止把 `profileKey/templateKey` 伪装成
版本行 ID。
Recipe 在数据库中的初始校验态继续使用 `incomplete`，API 统一映射为
`unvalidated`。三类持久任务类型冻结为
`provider.health_check`、`provider.model_discovery`、
`model.capability_check`。`direct_api` 在 P0-E 仅作为受控通用 HTTP
连接类型，不猜测协议；需要特定 SDK 协议的 Provider 使用
`openai_compatible`、`comfyui` 或 `runninghub` 显式适配器。

| 方法与地址 | 参数 | 成功 | 额外错误 | 失效与事件 |
| --- | --- | --- | --- | --- |
| `GET /accounts/{account_id}/ai-recipe` | Path | 200 `AIRecipeDto` | `ACCOUNT_NOT_FOUND` | 无 |
| `GET /accounts/{account_id}/ai-recipe/versions` | Path；Query `cursor,limit` | 200 `AIRecipeVersionPageDto` | 无 | 无 |
| `POST /accounts/{account_id}/ai-recipe/versions` | Path；`rev,idem`; `AccountAIRecipeVersionInput` | 201 `AIRecipeVersionDto` | `AI_RECIPE_INVALID`, `COMPOSITION_TEMPLATE_NOT_FOUND`, `REVISION_CONFLICT` | `ai-recipe,readiness`，`ai.recipe.updated` |
| `POST /accounts/{account_id}/ai-recipe/versions/{version}/validate` | Path；`idem`; 无 Body | 200 `AIRecipeValidationDto` | `AI_RECIPE_INVALID`, `MODEL_CAPABILITY_UNVERIFIED` | `ai-recipe,readiness`，`ai.recipe.updated` |
| `POST /accounts/{account_id}/ai-recipe/versions/{version}/activate` | Path；`rev,idem`; 无 Body | 200 `AIRecipeDto` | `AI_RECIPE_INVALID`, `REVISION_CONFLICT` | `ai-recipe,readiness,workspace`，`ai.recipe.updated` |
| `GET /system/providers` | Query `enabled,healthStatus,cursor,limit` | 200 `ProviderPageDto` | 无 | 无 |
| `POST /system/providers` | `idem`; `ProviderCreateInput` | 201 `ProviderDto` | `PROVIDER_ADAPTER_UNSUPPORTED`, `PROVIDER_BASE_URL_INVALID` | `providers,ai-summary`，`provider.updated` |
| `GET /system/providers/{provider_id}` | Path | 200 `ProviderDto` | `PROVIDER_NOT_FOUND` | 无 |
| `PATCH /system/providers/{provider_id}` | Path；`rev`; `ProviderPatchInput` | 200 `ProviderDto` | `PROVIDER_NOT_FOUND`, `PROVIDER_BASE_URL_INVALID`, `REVISION_CONFLICT` | `providers,models,routes,recipes`，`provider.updated`, `ai.config.changed` |
| `PUT /system/providers/{provider_id}/credential` | Path；`rev`; `ProviderCredentialInput` | 200 `CredentialSummaryDto` | `PROVIDER_NOT_FOUND`, `PROVIDER_SECRET_UNAVAILABLE`, `REVISION_CONFLICT` | `provider,ai-summary`，`provider.credential.updated` |
| `POST /system/providers/{provider_id}/checks` | Path；`idem`; `{ force?: boolean }` | 202 `TaskAcceptedDto` | `PROVIDER_SECRET_UNAVAILABLE`, `TASK_ALREADY_RUNNING` | `system:tasks,provider`，`task.queued` |
| `POST /system/providers/{provider_id}/model-discovery` | Path；`idem`; `{ replaceMissing?: false }` | 202 `TaskAcceptedDto` | `PROVIDER_CONNECTION_FAILED`, `TASK_ALREADY_RUNNING` | `system:tasks,models`，`task.queued` |
| `GET /system/models` | Query `providerId,enabled,capabilityKey,cursor,limit` | 200 `ModelPageDto` | `PROVIDER_NOT_FOUND` | 无 |
| `POST /system/models` | `idem`; `ModelCreateInput` | 201 `ModelProfileDto` | `PROVIDER_NOT_FOUND`, `MODEL_ALREADY_EXISTS` | `models,routes,recipes`，`model.updated`, `ai.config.changed` |
| `GET /system/models/{model_profile_id}` | Path | 200 `ModelProfileDto` | `MODEL_NOT_FOUND` | 无 |
| `PATCH /system/models/{model_profile_id}` | Path；`rev`; `ModelPatchInput` | 200 `ModelProfileDto` | `MODEL_NOT_FOUND`, `MODEL_IN_USE`, `REVISION_CONFLICT` | `models,routes,recipes`，`model.updated`, `ai.config.changed` |
| `GET /system/model-capabilities` | Query `providerId,modelProfileId,capabilityKey,availability,cursor,limit` | 200 `ModelCapabilityPageDto` | `PROVIDER_NOT_FOUND`, `MODEL_NOT_FOUND` | 无 |
| `GET /system/models/{model_profile_id}/capabilities` | Path | 200 `ModelCapabilityDto[]` | `MODEL_NOT_FOUND` | 无 |
| `POST /system/models/{model_profile_id}/capability-checks` | Path；`idem`; `CapabilityCheckInput` | 202 `TaskAcceptedDto` | `MODEL_NOT_FOUND`, `TASK_ALREADY_RUNNING` | `system:tasks,model-capabilities`，`task.queued` |
| `GET /system/capability-routes` | Query `capabilityKey,validationStatus,cursor,limit` | 200 `CapabilityRoutePageDto` | 无 | 无 |
| `PUT /system/capability-routes/{capability_key}` | Path；`rev,idem`; `CapabilityRouteInput` | 200 `CapabilityRouteDto` | `CAPABILITY_ROUTE_INVALID`, `MODEL_CAPABILITY_UNVERIFIED`, `REVISION_CONFLICT` | `routes,ai-summary,recipes`，`ai.config.changed` |
| `POST /system/capability-routes/{capability_key}/validate` | Path；`idem`; 无 Body | 200 `CapabilityRouteDto` | `CAPABILITY_ROUTE_INVALID` | `routes,recipes`，`ai.config.changed` |
| `GET /system/prompt-profiles` | Query `capabilityKey,status,cursor,limit` | 200 `PromptProfilePageDto` | 无 | 无 |
| `POST /system/prompt-profiles` | `idem`; `PromptProfileInput` | 201 `PromptProfileDto` | `PROMPT_PROFILE_INVALID` | `prompts,ai-summary`，`prompt.profile.updated` |
| `GET /system/prompt-profiles/{profile_key}` | Path | 200 `PromptProfileDto` | `PROMPT_PROFILE_NOT_FOUND` | 无 |
| `GET /system/prompt-profiles/{profile_key}/versions/{version}` | Path | 200 `PromptVersionDto` | `PROMPT_VERSION_NOT_FOUND` | 无 |
| `POST /system/prompt-profiles/{profile_key}/versions` | Path；`rev,idem`; `PromptVersionInput` | 201 `PromptVersionDto` | `PROMPT_PROFILE_INVALID`, `PROMPT_VERSION_IMMUTABLE`, `REVISION_CONFLICT` | `prompts`，`prompt.profile.updated` |
| `POST /system/prompt-profiles/{profile_key}/versions/{version}/activate` | Path；`rev,idem`; 无 Body | 200 `PromptProfileDto` | `PROMPT_VERSION_NOT_FOUND`, `PROMPT_PROFILE_INVALID`, `REVISION_CONFLICT` | `prompts,routes,recipes`，`prompt.profile.activated`, `ai.config.changed` |
| `GET /system/composition-templates` | Query `templateType,status,cursor,limit` | 200 `CompositionTemplatePageDto` | 无 | 无 |
| `POST /system/composition-templates` | `idem`; `CompositionTemplateInput` | 201 `CompositionTemplateDto` | `COMPOSITION_TEMPLATE_INVALID` | `composition-templates`，`composition.template.updated` |
| `GET /system/composition-templates/{template_key}` | Path | 200 `CompositionTemplateDto` | `COMPOSITION_TEMPLATE_NOT_FOUND` | 无 |
| `GET /system/composition-templates/{template_key}/versions/{version}` | Path | 200 `CompositionTemplateVersionDto` | `COMPOSITION_TEMPLATE_VERSION_NOT_FOUND` | 无 |
| `POST /system/composition-templates/{template_key}/versions` | Path；`rev,idem`; `CompositionTemplateVersionInput` | 201 `CompositionTemplateVersionDto` | `COMPOSITION_TEMPLATE_INVALID`, `REVISION_CONFLICT` | `composition-templates`，`composition.template.updated` |
| `POST /system/composition-templates/{template_key}/versions/{version}/validate` | Path；`idem`; 无 Body | 200 `CompositionTemplateValidationDto` | `COMPOSITION_TEMPLATE_INVALID`, `MODEL_CAPABILITY_UNVERIFIED` | `composition-templates,recipes`，`composition.template.updated` |
| `POST /system/composition-templates/{template_key}/versions/{version}/activate` | Path；`rev,idem`; 无 Body | 200 `CompositionTemplateDto` | `COMPOSITION_TEMPLATE_INVALID`, `REVISION_CONFLICT` | `composition-templates,recipes`，`composition.template.activated`, `ai.config.changed` |

#### 11.11.5 配置、诊断、任务与事件契约矩阵

| 方法与地址 | 参数 | 成功 | 额外错误 | 失效与事件 |
| --- | --- | --- | --- | --- |
| `GET /system/config` | Query `prefix?` | 200 `SystemConfigDto` | 无 | 无 |
| `PATCH /system/config` | `rev`; `SystemConfigPatchInput` | 200 `SystemConfigDto` | `CONFIG_KEY_NOT_WRITABLE`, `CONFIG_REVISION_CONFLICT` | `system-config` 及键对应域，`config.changed` |
| `GET /system/diagnostics` | Query `sections?` 为 `runtime,database,directories,mediaTools,sidecar` 逗号列表 | 200 `DiagnosticsDto` | `DIAGNOSTICS_UNAVAILABLE` | 无 |
| `GET /system/logs/{log_id}` | Path | 200 `SafeLogExcerptDto` | `LOG_NOT_FOUND` | 无 |
| `GET /system/tasks/{task_id}` | Path | 200 `TaskDto` | `TASK_NOT_FOUND`, `ACCOUNT_SCOPE_MISMATCH` | 无 |
| `POST /system/tasks/{task_id}/cancel` | Path；`idem`; 无 Body | 200 `TaskDto` | `TASK_NOT_FOUND`, `TASK_NOT_CANCELLABLE` | `system:tasks`，`task.cancelling` 或当前终态 |
| `GET /accounts/{account_id}/tasks/{task_id}` | Path | 200 `TaskDto` | `TASK_NOT_FOUND`, `ACCOUNT_SCOPE_MISMATCH` | 无 |
| `POST /accounts/{account_id}/tasks/{task_id}/cancel` | Path；`idem`; 无 Body | 200 `TaskDto` | `TASK_NOT_FOUND`, `TASK_NOT_CANCELLABLE`, `ACCOUNT_SCOPE_MISMATCH` | `account:{id}:tasks`，`task.cancelling` 或当前终态 |
| `WS /ws` | 会话子协议；首帧 `SubscribeFrame`，每 Topic 一组游标 | 101 后返回 `SubscribedFrame` 并发送 `RuntimeEventDto` | `RUNTIME_SESSION_INVALID`, `ACCOUNT_SCOPE_MISMATCH`, `WS_CURSOR_MISMATCH`, `WS_EVENT_GAP` | 不适用；协议本身承载事件 |

#### 11.11.6 资源示例与缓存语义

以下示例是 `data` 字段的规范形状；均放入 11.11.1 的成功信封。字符串正文仅为结构示意，不作为产品假数据写入数据库。

连接更新：

```json
{
  "accountId": "acc_01J...",
  "deviceWorkspace": { "id": "workspace_01J...", "status": "available" },
  "browserInstance": { "id": "browser_01J...", "status": "stopped" },
  "executionBinding": { "id": "binding_01J...", "verifiedAt": null },
  "lastCheck": null,
  "revision": 4
}
```

定位与知识：

```json
{
  "positioning": { "accountId": "acc_01J...", "activeVersion": 2, "versions": [{ "version": 2, "status": "active", "summary": "面向明确受众的短视频内容定位", "createdAt": "2026-07-20T10:00:00Z" }], "revision": 5 },
  "knowledge": { "accountId": "acc_01J...", "rulesVersion": 2, "sourceCounts": { "ready": 0, "indexing": 0, "failed": 0 }, "latestSnapshotId": null, "readiness": { "status": "empty" }, "revision": 3 }
}
```

账号 AI Recipe：

```json
{
  "accountId": "acc_01J...",
  "activeVersion": 1,
  "versions": [{ "version": 1, "status": "active", "validationStatus": "valid" }],
  "resolvedSummary": { "inheritedCapabilities": ["script_generation"], "overriddenCapabilities": [], "compositionTemplateRef": "tpl_vertical_story@1" },
  "revision": 2
}
```

系统 AI 配置：

```json
{
  "provider": { "id": "prov_01J...", "name": "兼容接口", "adapterType": "openai_compatible", "baseUrl": "https://api.example.invalid/v1", "credentialSummary": { "configured": true, "maskedValue": "••••4f2a" }, "enabled": true, "healthStatus": "unknown", "revision": 1 },
  "model": { "id": "model_01J...", "providerProfileId": "prov_01J...", "modelId": "model-id", "displayName": "文本模型", "enabled": true, "discoverySource": "manual", "capabilities": [], "revision": 1 },
  "route": { "id": "route_01J...", "capabilityKey": "script_generation", "primaryModelProfileId": "model_01J...", "fallbackModelProfileId": null, "promptProfileId": "prompt_script_v1", "enabled": true, "validationStatus": "incomplete", "validationIssues": [{ "code": "MODEL_CAPABILITY_UNVERIFIED" }], "revision": 1 }
}
```

Prompt 与合成模板：

```json
{
  "prompt": { "profileKey": "script_default", "name": "默认脚本提示", "capabilityKey": "script_generation", "activeVersion": 1, "versions": [{ "version": 1, "status": "active", "contentHash": "sha256:..." }], "referenceCount": 1, "revision": 2 },
  "compositionTemplate": { "templateKey": "vertical_story", "name": "竖屏叙事模板", "templateType": "mixed_media", "activeVersion": 1, "versions": [{ "version": 1, "status": "active", "contentHash": "sha256:..." }], "compatibleCapabilities": { "required": ["image_generation", "tts"] }, "referenceCount": 1, "revision": 2 }
}
```

任务与诊断：

```json
{
  "task": { "taskId": "task_01J...", "scope": "account", "accountId": "acc_01J...", "taskType": "account.health_check", "status": "completed", "cancellable": false, "createdAt": "2026-07-20T10:00:00Z", "completionKind": "succeeded", "failureKind": null, "progress": 1, "resultRef": "result://task_01J...", "errorCode": null, "logId": null, "revision": 4 },
  "diagnostics": { "runtime": { "status": "ready" }, "database": { "status": "ready" }, "directories": { "status": "ready" }, "mediaTools": { "status": "attention" }, "sidecar": { "status": "running" }, "checkedAt": "2026-07-20T10:00:00Z" }
}
```

缓存键只使用矩阵“失效”列的稳定标识；HTTP 成功提交与 outbox 事件处于同一事务边界。Desktop 收到写响应后立即失效本地键，不等待 WebSocket；随后收到同 revision 事件只用于确认，收到更高 revision 才再次补拉。

## 12. 错误码、HTTP 状态与恢复动作

v1 错误码统一使用大写下划线式。现有旧 API 的小写点分式错误码只在兼容响应中保留；`docs/api/v1/errors.md` 必须维护完整一对一映射，并把旧 `requestId` 与 v1 `log_id` / `X-Request-ID` 的关联写清楚。同一个 v1 路由、事件或日志禁止混用两种命名。

| 错误码 | HTTP | 中文默认摘要 | 推荐恢复动作 |
| --- | ---: | --- | --- |
| `REQUEST_VALIDATION_FAILED` | 422 | 请求参数校验失败 | 定位字段并修正 |
| `REQUEST_TIMEOUT` | 504 | 操作超时 | 重试或检查依赖 |
| `RUNTIME_SESSION_REQUIRED` | 401 | 缺少本机 Runtime 会话凭据 | 由桌面壳重新获取连接信息 |
| `RUNTIME_SESSION_INVALID` | 401 | 本机 Runtime 会话已失效 | 重启 Runtime 连接，不复用旧令牌 |
| `RUNTIME_HOST_INVALID` | 400 | Runtime 请求目标不合法 | 检查受控本机端口 |
| `RUNTIME_ORIGIN_FORBIDDEN` | 403 | 请求来源不受信任 | 使用正式桌面壳或受控开发 Origin |
| `REVISION_CONFLICT` | 412 | 数据已被更新 | 重新加载后合并 |
| `CONFIG_REVISION_CONFLICT` | 412 | 配置已被其他操作更新 | 重新加载后合并 |
| `LICENSE_INVALID` | 403 | 许可证无效 | 返回许可证向导 |
| `LICENSE_MACHINE_MISMATCH` | 403 | 许可证与本机不匹配 | 查看机器码并重新授权 |
| `LICENSE_STORE_UNAVAILABLE` | 503 | 许可证安全存储不可用 | 检查系统安全存储后重试 |
| `DIRECTORY_CREATE_FAILED` | 500 | 工作目录初始化失败 | 检查路径与权限后重试 |
| `RUNTIME_NOT_READY` | 503 | Runtime 尚未就绪 | 重新自检 |
| `SELF_CHECK_ALREADY_RUNNING` | 409 | 系统自检正在运行 | 打开已有任务 |
| `ACCOUNT_NOT_FOUND` | 404 | 账号不存在或已移除 | 返回账号选择 |
| `ACCOUNT_ARCHIVED` | 409 | 账号已归档 | 前往账号管理恢复 |
| `ACCOUNT_SCOPE_MISMATCH` | 403 | 请求不属于当前账号 | 刷新账号工作区 |
| `ACCOUNT_SWITCH_PREPARE_FAILED` | 409 | 账号工作区准备失败 | 查看依赖并重试 |
| `ACCOUNT_STATE_TRANSITION_INVALID` | 409 | 当前账号状态不允许此操作 | 查看账号健康 |
| `ACCOUNT_CONNECTION_REQUIRED` | 409 | 账号尚未完成真实连接 | 打开连接与工作区 |
| `ACCOUNT_PLATFORM_UNSUPPORTED` | 422 | 当前平台不受支持 | P0 仅选择 TikTok |
| `ACCOUNT_USERNAME_INVALID` | 422 | TikTok handle 格式无效 | 修正账号标识 |
| `ACCOUNT_WIZARD_INCOMPLETE` | 409 | 添加账号向导尚未完成 | 补齐必要步骤 |
| `WORKSPACE_UNAVAILABLE` | 409 | 账号工作区不可用 | 检查真实工作区与绑定 |
| `BROWSER_INSTANCE_NOT_FOUND` | 404 | 浏览器实例不存在 | 重新选择真实实例 |
| `EXECUTION_BINDING_INVALID` | 422 | 执行绑定无效 | 检查工作区与浏览器归属 |
| `ACCOUNT_COPY_SECTION_INVALID` | 422 | 包含不可复制配置 | 取消非法分区 |
| `ACCOUNT_COPY_SOURCE_EQUALS_TARGET` | 409 | 不能复制到同一账号 | 选择其他来源 |
| `POSITIONING_INVALID` | 422 | 定位配置无效 | 修正受众、支柱或边界 |
| `POSITIONING_VERSION_NOT_FOUND` | 404 | 定位版本不存在 | 重新选择版本 |
| `KNOWLEDGE_RULES_INVALID` | 422 | 知识规则无效 | 修正规则或引用策略 |
| `KNOWLEDGE_SOURCE_INVALID` | 422 | 知识来源不可用 | 重新选择来源 |
| `KNOWLEDGE_SOURCE_NOT_FOUND` | 404 | 知识来源不存在 | 刷新来源列表 |
| `CONTROLLED_FILE_REF_INVALID` | 422 | 文件引用不受当前工作区控制 | 通过受控文件选择器重新导入 |
| `KNOWLEDGE_SNAPSHOT_INVALID` | 422 | 知识快照无法创建 | 修正来源集合 |
| `KNOWLEDGE_SNAPSHOT_NOT_FOUND` | 404 | 知识快照不存在 | 刷新快照列表 |
| `KNOWLEDGE_INDEX_FAILED` | 500 | 知识索引失败 | 查看日志并重试 |
| `BRAND_KIT_INVALID` | 422 | 品牌规范无效 | 修正颜色、字体或资产引用 |
| `PUBLISH_DEFAULTS_INVALID` | 422 | 发布默认值无效 | 修正时区或平台约束 |
| `PROVIDER_NOT_FOUND` | 404 | Provider 不存在 | 返回 Provider 列表 |
| `PROVIDER_ADAPTER_UNSUPPORTED` | 422 | Provider 适配器不受支持 | 选择已接入适配器 |
| `PROVIDER_BASE_URL_INVALID` | 422 | Provider 地址无效或不安全 | 修正受控连接地址 |
| `PROVIDER_SECRET_UNAVAILABLE` | 503 | Provider 凭据不可用 | 重新设置凭据 |
| `PROVIDER_CONNECTION_FAILED` | 502 | Provider 连接失败 | 检查地址、凭据和网络 |
| `PROVIDER_CHECK_TIMED_OUT` | 504 | Provider 检查超时 | 重试或增加受控超时 |
| `MODEL_NOT_FOUND` | 404 | 模型不存在 | 重新发现或手动添加 |
| `MODEL_ALREADY_EXISTS` | 409 | 同一 Provider 已存在该模型 | 使用现有模型 |
| `MODEL_IN_USE` | 409 | 模型仍被路由引用 | 先调整能力路由 |
| `MODEL_CAPABILITY_UNVERIFIED` | 409 | 模型能力尚未验证 | 运行能力检查 |
| `CAPABILITY_ROUTE_INVALID` | 422 | AI 能力路由无效 | 修正模型与 Prompt |
| `CAPABILITY_ROUTE_UNAVAILABLE` | 409 | AI 能力当前不可用 | 切换已验证模型 |
| `PROMPT_PROFILE_INVALID` | 422 | Prompt 模板校验失败 | 修正变量或输出 Schema |
| `PROMPT_PROFILE_NOT_FOUND` | 404 | Prompt Profile 不存在 | 刷新模板列表 |
| `PROMPT_VERSION_NOT_FOUND` | 404 | Prompt 版本不存在 | 重新选择版本 |
| `PROMPT_VERSION_IMMUTABLE` | 409 | 已激活版本不可直接修改 | 创建新版本 |
| `COMPOSITION_TEMPLATE_INVALID` | 422 | 合成模板无效 | 修正 Schema、能力或资产引用 |
| `COMPOSITION_TEMPLATE_NOT_FOUND` | 404 | 合成模板不存在 | 刷新模板列表 |
| `COMPOSITION_TEMPLATE_VERSION_NOT_FOUND` | 404 | 合成模板版本不存在 | 重新选择版本 |
| `AI_RECIPE_INVALID` | 422 | 账号 AI 配方不可用 | 修正覆盖或系统路由 |
| `CONFIG_KEY_NOT_WRITABLE` | 422 | 配置项不可由用户修改 | 仅修改配置总线允许字段 |
| `DIAGNOSTICS_UNAVAILABLE` | 503 | 诊断信息暂不可用 | 稍后重试并查看日志 |
| `LOG_NOT_FOUND` | 404 | 日志引用不存在或已过期 | 重新执行诊断 |
| `TASK_NOT_FOUND` | 404 | 任务不存在 | 刷新任务列表 |
| `TASK_NOT_CANCELLABLE` | 409 | 当前任务不能取消 | 等待终态 |
| `TASK_ALREADY_RUNNING` | 409 | 相同操作正在运行 | 打开已有任务 |
| `TASK_TIMEOUT` | 504 | 任务执行超时 | 查看日志并重试 |
| `WS_EVENT_GAP` | 409 | 事件游标已断档 | 通过 HTTP 重新同步 |
| `WS_CURSOR_MISMATCH` | 409 | 事件游标与 Topic 不一致 | 通过 HTTP 对账后重新订阅 |
| `LEGACY_WRITE_UNSUPPORTED` | 410 | 旧写入方式已停用 | 使用归档或版本化新接口 |
| `DATABASE_SCHEMA_UNSUPPORTED` | 503 | 数据库结构无法安全识别 | 保留原库并查看迁移诊断 |
| `MIGRATION_FAILED` | 503 | 数据迁移失败，已停止启动 | 恢复备份或查看日志 |
| `INTERNAL_ERROR` | 500 | 系统内部错误，请稍后重试 | 查看 `log_id` 并重试 |

领域服务抛出强类型错误，异常处理器统一映射。不得在路由层到处硬编码中文错误。字段级验证问题放入安全 `fieldErrors`，不得包含敏感原值。

## 13. 数据库迁移规格

### 13.1 启动迁移流程

正常启动不得继续直接执行 `Base.metadata.create_all()` 和多段隐式表重建。新流程：

```text
解析数据库路径
→ 获取单实例迁移锁
→ 检查数据库完整性和可写性
→ 检查 Alembic 版本
→ 无版本旧库完整命中冻结 cohort 时直接安全 stamp 0014
→ 对需要升级的已有非空数据库创建带时间戳的同目录备份
→ Alembic upgrade head
→ 执行迁移后契约验证
→ 释放迁移锁
→ 创建 Runtime 容器
```

- 空数据库从 Alembic base 升级。
- 已有 `alembic_version` 从当前版本升级。
- 没有 `alembic_version` 但完整命中冻结 legacy cohort 的数据库直接安全 stamp 到 `0014`，再由 `0015–0017` 完成扩展、回填与约束；启动流程不得运行旧 repair 或 normalizer。
- 空库不创建迁移前备份；失败时只清理未完成的新数据库单元。只有需要升级的已有非空数据库才创建 DB / WAL / SHM 迁移备份。
- 未知 Schema 禁止猜测修复，返回 `DATABASE_SCHEMA_UNSUPPORTED` 并保留原文件。
- 迁移失败立即停止 Runtime 就绪，恢复备份并返回可见错误；不得在半迁移数据库上继续服务。

2026-07-20 设计审计快照中，仓库开发库 `.runtime-data/runtime.db` 有 39 张表、`schema_meta=3`，但没有 `alembic_version`。该快照仅用于冻结 legacy cohort，不代表后续运行时事实。实现禁止直接对无版本旧库执行 `alembic upgrade head`：legacy baseline 必须先校验完整表、列、约束和持久 Schema 对象指纹，只有已知 cohort 才允许安全 stamp；未知或部分匹配指纹只读失败，绝不猜测修补。

### 13.2 新迁移序列

#### `0015_p0_expand`

- 以加法方式扩展 `accounts` 的向导、归档、健康和 revision 字段，首轮允许必要 nullable。
- 新增 AccountConnection、定位、知识库 / 来源 / 快照、BrandKit、发布默认值和复制审计表。
- 新增 Provider、模型、能力、Prompt、Capability Route、Account AI Recipe、持久化任务和事件 outbox 表。
- 新增系统 `ai_config_revision`，但不切换生产读取路径。

#### `0016_p0_backfill`

- 保守回填旧账号：明确 archived → `archived`；缺少真实绑定 → `unbound`；有绑定但知识 / AI 未验证或有旧错误 → `attention`；未知状态 → `attention`。绝不自动迁为 `ready`。
- 旧绑定必须基于真实外键证据拆分 workspace / browser；无法判定时解除活动绑定并记录诊断。
- `AIProviderSetting` 映射到待检查的 `ProviderProfile`，只保留有效安全存储引用。
- `AIProviderModel` 映射为 `ModelProfile(discovery_source=migrated)`。
- 旧能力只形成 `declared_supported`；`adapter_supported` 由适配器注册表重新计算，`contract_verified=false`。
- 旧 Prompt 和 `AICapabilityConfig` 映射为禁用 / incomplete 的版本与 Route 草稿；`magic_cut` 等退出主线能力不自动路由。
- 保留来源 ID、内容哈希、行数、引用校验和迁移报告。

#### `0017_p0_enforce_and_cutover`

- 使用 SQLite batch migration 增加 CheckConstraint、NotNull、外键、唯一约束和账号范围索引。
- 增加配置复制、健康检查、版本激活、任务与事件审计约束。
- 验证不存在跨账号外键、孤儿引用、重复活动版本和无 topic 事件。
- 将生产 factory 切换到 Alembic migration runner，并停止正常启动路径的 `create_all` 与 schema repair。
- 过渡修复逻辑只留在显式 legacy bridge，后续 GET 和普通启动不再触发。

### 13.3 事务与备份

- 迁移锁、备份目录、保留份数和超时由配置总线管理。
- Alembic 与 Runtime 当前使用的数据库环境变量必须统一为配置总线解析结果；旧 `TK_OPS_DATABASE_PATH` 与 `TK_OPS_RUNTIME_DB_PATH` 只能由一个兼容解析器读取，并在冲突时拒绝启动，禁止迁移到另一份数据库。
- SQLite DDL 可能无法完整事务回滚，因此生产回退以数据库文件备份为真源。
- 备份文件名只包含安全时间戳和数据库 ID，不在 UI 或普通日志展示完整路径。
- 备份前停止业务写入并处理 SQLite WAL；数据库文件及存在的 `-wal` / `-shm` 必须作为同一恢复单元记录大小和校验值。
- 迁移前后执行 `PRAGMA integrity_check`、外键检查和目标表契约验证。
- 迁移报告记录版本、耗时、表数量、成功 / 失败、`log_id`，不记录业务正文。

### 13.4 回退策略

- P0 迁移为加法优先，旧表在本阶段不删除。
- 实现阶段每个迁移必须提供开发 / 测试用 `downgrade`；若会丢失 P0 新写数据，必须显式报错并要求恢复迁移前备份。
- 迁移和切换使用明确的无写窗口：关闭 API 写门、排空正在提交的事务、记录 `cutover_event_id`、完成 WAL checkpoint 与备份，再执行迁移和验证。验证完成前 Desktop 只能显示维护态，不能创建任何 P0 写入。
- 若迁移或启动验证在写门重新开放前失败，可以恢复迁移前备份；恢复后必须核对数据库、WAL / SHM 校验和与 `cutover_event_id`，因为该窗口内不存在合法新写入。
- 写门重新开放后，迁移前备份仅作为取证备份，禁止自动恢复。代码回退必须使用“上一 Desktop + 前向兼容回退 Runtime”读取当前已迁移数据库；回退 Runtime 与 0015–0017 Schema 的契约在发布前纳入测试和制品清单。
- 若缺陷导致当前 Schema 也不可继续使用，先重新关闭写门并完整备份当前数据库，再按 `runtime_events` 中 `cutover_event_id` 之后的事务事件导出增量包；恢复目标库后通过专用、幂等的恢复工具重放可表示记录，逐表核对数量、主键、revision、内容哈希和审计事件。不能无损表示的 P0 新对象必须保留在只读恢复库并阻止完成回退，禁止以“回退成功”掩盖数据损失。
- 已投入使用的生产数据库不通过自动 downgrade 回退；任何强制恢复都必须生成回退报告、源 / 目标校验和、未映射对象清单和 `log_id`。
- 路由切换前保留旧构建可运行；路由切换后禁止在同一构建中提供两个可选壳。

## 14. 旧 API 与代码兼容策略

### 14.1 旧 API 薄转发

兼容入口只允许：

1. 将旧请求转换为新服务层输入。
2. 调用与 v1 相同服务。
3. 将新 DTO 转为旧响应形状。
4. 记录 `legacy_api.used` 诊断事件。

禁止在兼容路由中复制事务、状态计算、仓储写入和缓存失效。新增功能不提供旧 API 入口。

兼容层直接调用相同 Service / Unit of Work，禁止通过 HTTP 回环调用 v1。旧 `/api/ws` 在兼容期只发送不含账号业务数据的系统事件；账号事件只存在于带账号范围的 v1 WebSocket。

旧 `DELETE /api/accounts/{id}`、旧 AI 聚合 PUT 和会原地覆盖 Prompt 的危险写接口不得偷偷映射为新语义，统一返回 HTTP 410 `LEGACY_WRITE_UNSUPPORTED`，并给出归档 / 版本化新接口；绝不继续物理删除、双写或静默覆盖。

### 14.2 兼容退出条件

- 新 Desktop 不再调用旧 `/api/...`。
- v1 相关契约和主链测试连续通过。
- 诊断日志在一个内部发布窗口内不再发现旧 Desktop 调用。
- 用户确认 P0 主链后，另立删除计划移除旧路由、旧页面引用和旧表。

兼容层只保留一个受控迁移窗口；旧调用计数、旧 Desktop URL 和兼容契约依赖归零后，必须经独立删除计划批准才可移除。具体发布批次随发布计划调整，但退出条件不得放宽。

### 14.3 前端客户端过渡

现有 `runtime-client.ts` 先改为只重导出新领域客户端，避免一次性修改所有未迁移旧页面。新 P0 页面必须直接引用：

```text
app/runtime-client/core
app/runtime-client/bootstrap
app/runtime-client/accounts
app/runtime-client/ai-system
app/runtime-client/tasks
```

旧页面只在不可达兼容期间继续使用重导出；不得向集中入口新增函数。

## 15. 安全、隐私与审计

### 15.1 凭据

- Provider 密钥、Token 和敏感代理凭据只写系统安全存储。
- 数据库、配置总线、账号 Recipe、日志和任务快照只保存引用。
- 读取 API 永不返回原始凭据；重新编辑时要求用户重新输入或保留现有引用。
- 更新凭据先创建新安全引用，再在数据库事务中切换引用；数据库失败删除新引用，数据库提交后才清理旧引用。安全存储失败时不得写数据库。DPAPI 损坏或用户变化必须返回可见错误，禁止降级为明文。

### 15.2 Provider 网络边界

- 只允许 `http` / `https`；拒绝 `file`、`ftp`、`gopher` 等协议。
- 本机和局域网地址用于本地 Provider 时必须明确标注连接范围，不静默上报外网。
- 重定向次数、响应体大小、连接 / 读取超时和并发通过配置总线限制。
- Provider 原始错误经过安全归一化后展示；响应正文不直接写日志。

### 15.3 本地文件

- UI 文件选择通过 Tauri 受控命令生成文件引用。
- Runtime 校验引用位于允许工作区或已授权导入范围。
- Tauri 当前 `$HOME/**`、Desktop、Documents 等宽泛 assetProtocol scope 必须收窄到应用数据和账号工作区；外部选择文件先显式导入 / 复制后再预览，禁止长期开放整个用户目录。
- 校验必须解析规范化真实路径，并阻止 `..`、符号链接、Windows Junction 或重解析点逃逸当前账号工作区。
- 日志只保存文件 ID、扩展名、大小和脱敏摘要。

账号文件根固定为配置总线解析后的 `accounts/{account_id}/`，P0 子目录至少包括 `knowledge/`、`imports/`、`tasks/` 和 `temp/`。服务按 AccountScope 生成路径，页面与请求体不得自行拼接账号目录。

### 15.4 Prompt 与知识

- Prompt 编辑 API 只有主动打开具体版本时返回正文。
- 日志记录 Prompt ID、版本、哈希和长度，不记录全文。
- 知识来源正文不进入普通任务事件；事件只包含来源 ID 和状态。

### 15.5 结构化日志字段

至少包含：

```text
timestamp, level, module, operation, request_id, operation_id, log_id,
account_id, resource_type, resource_id, task_id, stage, duration_ms,
provider_profile_id, model_profile_id, capability_key,
prompt_profile_id, prompt_version, config_revision,
error_code, retry_of
```

所有字段允许为空但键名统一。新增注释必须使用中文；日志消息优先中文，技术标识保留英文键。

## 16. 缓存、修订与事件一致性

### 16.1 修订号

- `systemConfigRevision`：Runtime 与系统配置。
- `aiConfigRevision`：Provider、模型、能力、Prompt 和 Capability Route。
- `accountRevision`：账号聚合、定位、知识、Recipe、连接和默认值。
- `subscriptionRevision`：当前账号事件订阅世代，由前端每次重连递增。

写操作响应 `meta.revision` 和 `meta.invalidations`。运行中的后续生成任务使用创建时快照，不跟随修订变化。

### 16.2 失效规则

| 写操作 | 必须失效 / 更新 |
| --- | --- |
| 账号身份、连接、定位、知识、Recipe | 当前账号详情、就绪摘要、工作区首页 |
| Provider / 模型 / 能力 | 系统 AI 摘要、Capability Route 验证、受影响账号 Recipe 验证 |
| Prompt 新版本 / 激活 | Prompt 列表、引用 Route、受影响 Recipe 验证 |
| 配置总线更新 | Bootstrap / 诊断 / 网络策略 / UI 偏好对应缓存 |
| 归档账号 | 账号列表、当前账号上下文、账号事件订阅 |

前端收到事件后先比较修订；旧事件忽略，新事件按 invalidation 补拉，不直接把不完整事件 payload 当最终对象。

## 17. API 文档唯一真源

P0-A 只建立兼容矩阵，不虚构尚未实现的 v1 接口。P0-B 开始后，按本规格随实际路由逐资源物化以下文档目录；接口语义已经由第 11 节冻结，实施只允许补充与代码一一对应的字段说明，不得临时改变参数、状态、错误、失效或事件：

```text
docs/api/v1/
├── README.md
├── bootstrap.md
├── accounts.md
├── account-knowledge.md
├── ai-system.md
├── tasks-and-events.md
└── errors.md
```

每个接口条目必须包含：

1. 用途、范围和稳定级别。
2. 地址与方法。
3. Path / Query / Header / Body 参数。
4. 成功 HTTP 状态、信封和完整示例。
5. 错误 HTTP 状态、错误码、中文默认摘要和恢复动作。
6. `If-Match`、`Idempotency-Key` 和超时要求。
7. 缓存失效、修订号和 WebSocket 事件。
8. 账号隔离与敏感信息说明。
9. 旧接口兼容关系和退出条件。

前端调用文档以相同 API 文件为真源，不另写一份可能漂移的契约。Desktop 领域客户端函数在文档中补充 TypeScript 映射名称。

现有大型 `docs/RUNTIME-API-CALLS.md` 在 P0 实施时冻结为 legacy 索引，顶部明确指向 `docs/api/v1/`，禁止继续追加 v1 内容；否则会形成两个接口真源。

## 18. 测试与验证规格

### 18.1 Runtime 单元测试

#### 账号

- 创建账号只产生 `draft`，输入不能设置状态。
- 五状态允许 / 禁止转换矩阵。
- 健康计算对连接、知识和必要 AI 能力的组合。
- 配置复制白名单、全事务回滚和禁止复制对象。
- 归档保留数据；恢复先复检，不直接假设 ready。
- 所有账号仓储查询必须包含 `account_id`。

#### AI

- 凭据只写安全存储引用，DTO / 日志不泄漏原值。
- 模型可用性严格使用三项能力交集。
- Capability Route 原子验证主模型、回退和 Prompt。
- Prompt active 版本不可变，新版本哈希和引用正确。
- Recipe 继承优先级、覆盖白名单、系统修订失效和激活事务。

#### 配置、错误与任务

- 配置 `If-Match` 冲突。
- 领域异常到 HTTP / 错误码 / `log_id` 的稳定映射。
- 长任务超时、取消、幂等、失败和重试来源。
- 日志脱敏完整路径、密钥、Token、Prompt 和 Provider 正文。
- DPAPI / 安全存储不可用、密文损坏和 Windows 用户变化时可见失败，禁止回退到明文文件。

### 18.2 数据库迁移测试

- 空数据库 `base -> head`。
- 当前 0014 Alembic 数据库升级。
- 无 `alembic_version` 的已知 legacy 指纹安全 stamp 后升级。
- 仓库开发库结构的匿名快照升级，不使用原业务内容。
- 未知指纹停止并保持文件哈希不变。
- 任一 migration 中断后自动恢复备份。
- 0015–0017 开发数据库 downgrade / re-upgrade；存在无法无损映射的新版本数据时必须拒绝 downgrade 并要求备份恢复。
- 外键检查、唯一索引和跨账号孤儿检查。
- 迁移旧 AI 配置后全部为 unknown / incomplete，绝不假 ready。

### 18.3 Runtime 契约测试

- 所有 v1 成功 / 失败信封、状态码和 `X-Request-ID`。
- 账号级 URL 缺失、无效、归档和 scope mismatch。
- 请求体不能覆盖路径账号。
- `If-Match`、幂等键、分页和最大 limit。
- 旧 API 只调用新服务且记录兼容事件。
- API 文档中的地址、方法、错误码和路由注册表一致。
- Prompt / Provider / 日志响应不包含敏感字段。

### 18.4 WebSocket 隔离测试

- 系统连接只收到系统事件。
- 账号 A 连接不收到账号 B 事件。
- 账号切换后旧订阅关闭，新订阅使用更高 `subscriptionRevision`。
- 旧修订事件被 UI 忽略。
- 断线重连、心跳、取消和任务终态补拉。
- 每个 Topic 独立重放；多 Topic 断点互不覆盖，单一过期 Topic 只触发该 Topic 的 `sync.required`。
- 使用账号 A 的 Topic 游标订阅账号 B 时整帧拒绝，且不泄露账号 A Topic 是否存在。
- 缺失 / 无效 Runtime 会话令牌、错误 Host、非白名单 Origin 的 HTTP 与 WebSocket 均被拒绝且日志脱敏。
- 服务端发送失败会清理连接并记录异常，不影响其他订阅。

### 18.5 Desktop Vitest

- 路由清单只有十三个页面容器；主导航只有十个账号入口。
- 旧 URL 映射正确，旧剪辑工作台组件不可达。
- 无账号进入账号选择状态，不自动选择。
- 账号切换保存 / 放弃 / 取消三条守卫路径。
- prepare 失败保留原账号。
- 旧 HTTP 响应、旧事件和过期 `switchIntentId` 不能写入新账号。
- WebSocket 失败显示稳定离线反馈，不只写 console。
- 添加账号六步向导字段、状态、取消、重试和错误。
- Provider 向导、模型验证、Route、Prompt 版本和 Recipe 继承。
- 加载、空、正常、错误、受限和筛选为空。
- Light / Dark 和宽屏 / 紧凑布局 class / 可见行为。
- 键盘焦点、Esc、未保存 Modal 和 Reduced Motion。

### 18.6 浏览器端到端主链

使用临时真实 Runtime 测试库，不使用生产 `.runtime-data`：

```text
激活测试许可证
→ 初始化临时目录
→ 创建账号 A / B
→ 为账号 A 建立真实测试绑定
→ 配置测试 Provider 适配器、模型、路由与 Prompt
→ 激活账号 A Recipe
→ 切换 A / B 并验证内容和事件隔离
→ 归档 A 并恢复复检
```

测试 Provider 必须明确是本地测试适配器，不在生产 UI 伪装为真实第三方成功。

E2E 禁止 mock `fetch` 或直接向页面注入业务对象；页面必须经过真实 Runtime、服务、仓储和临时 SQLite。外部第三方网络只允许在 Provider 适配器边界替换为确定性测试适配器。

### 18.7 Tauri 与 sidecar 验证

- Rust 单元测试 Runtime Supervisor 状态机、超时、有限重启和退出清理。
- 构建脚本在 sidecar 缺失、版本不匹配或哈希错误时失败。
- 安装包离线启动，不依赖系统 Python 或仓库路径。
- 第二实例只激活第一实例，不启动第二 Runtime。
- 动态端口被占用时重新选择；sidecar 只能监听 loopback。
- sidecar 崩溃时 UI 显示错误；手动重启后恢复。
- 应用退出后子进程树消失，数据库锁释放。
- 生产应用数据目录、许可证、日志和数据库路径正确。

### 18.8 主链回归与质量门

P0-A 至 P0-E 每个阶段只集中运行一次：

1. 当前阶段相关单元 / 契约 / UI 测试。
2. 一条与当前阶段相关的主链回归。
3. `git diff --check`。
4. 中文编码与真源术语检查。

开发过程中只做静态检查和代码审查，不反复运行测试。P0-F 执行一次 P0 全量 Runtime / Desktop 自动化测试、类型检查、Desktop 构建、浏览器 E2E、Tauri sidecar smoke、安装包 smoke、Light / Dark 与两档 PC 尺寸人工验收。

根 `package.json` 必须新增统一但可分层执行的 `test`、`typecheck`、`test:e2e` 和 Tauri smoke 入口；Vite build 不能替代 TypeScript 类型检查。新增 Playwright E2E 配置使用临时数据库和临时工作区。`tests/runtime/README.md`、`tests/contracts/README.md` 同步更新，不再保留“本轮不创建测试代码”等过时说明。

当前约 76 个测试文件直接锁定旧 `/api/...`。迁移策略是：先保留其 legacy 回归价值，再为 v1 新增独立契约；新 Desktop 完成迁移后才批量改写或退役旧断言，禁止一开始删除旧测试制造虚假全绿。

### 18.9 模块边界质量门

- 新增 P0 生产源文件以约 350 行为目标，接近 500 行必须拆分或在审查中给出职责不可再分的证据；测试与独立 CSS 以约 500 行为审查线。
- 本阶段列出的七个集中大文件必须显著缩小或退化为兼容重导出 / 装配入口。
- 增加静态检查：新 P0 页面不得直接 `fetch`，服务不得读取页面状态，账号仓储方法不得省略账号范围。
- 旧大文件允许在兼容窗口保留不可达代码，但禁止继续增长；后续删除计划再移除。

## 19. 实施文件地图

### 19.1 Desktop 与 Tauri

```text
apps/desktop/src/app/
├── account-context/
│   ├── account-context-store.ts
│   ├── account-switch-transaction.ts
│   ├── account-request-registry.ts
│   ├── account-request-scope.ts
│   ├── unsaved-guard-registry.ts
│   └── useAccountUnsavedGuard.ts
├── router/
│   ├── route-ids.ts
│   ├── route-manifest.ts
│   ├── legacy-redirects.ts
│   └── guards.ts
└── runtime-client/
    ├── core.ts
    ├── bootstrap.ts
    ├── accounts.ts
    ├── system-config.ts
    ├── ai-system.ts
    ├── tasks.ts
    └── index.ts

apps/desktop/src/layouts/account-workspace/
apps/desktop/src/pages/workspace-home/
apps/desktop/src/pages/strategy-knowledge/
apps/desktop/src/pages/settings/accounts/
apps/desktop/src/pages/settings/ai-system/
apps/desktop/src/modules/accounts/
apps/desktop/src/modules/knowledge/
apps/desktop/src/modules/ai-recipes/
apps/desktop/src/modules/system/
apps/desktop/src/types/runtime/
apps/desktop/src-tauri/src/runtime_supervisor/
apps/py-runtime/packaging/
scripts/prepare-runtime-sidecar.mjs
```

现有 `runtime-client.ts` 和 `types/runtime.ts` 最终只允许作为兼容重导出，之后另立删除任务。

### 19.2 Runtime

P0-A 实际落点：

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
    ├── types.py
    ├── legacy_baseline.py
    ├── fingerprint.py
    ├── lock.py
    ├── backup.py
    ├── runner.py
    ├── target_columns.py
    ├── target_checks.py
    ├── target_relations.py
    └── target_contract.py
```

P0-B 至 P0-E 仍按以下目标边界展开：

```text
apps/py-runtime/src/
├── api/dependencies/
├── api/routes/v1/
├── api/routes/legacy/
├── api/websocket/
├── app/container.py
├── app/route_registry.py
├── app/exception_handlers.py
├── errors/
├── logging/
├── services/accounts/
├── services/provider_profiles/
├── services/model_profiles/
├── services/capability_routes/
├── services/prompt_profiles/
├── services/ai_recipes/
├── services/knowledge/
├── services/tasks/
└── domain/models/（按对象拆分）
```

### 19.3 文档与测试

- `docs/api/v1/` 接口唯一真源。
- `tests/runtime/` 服务、迁移、任务和安全测试。
- `tests/contracts/` v1、隔离、文档与兼容契约。
- `apps/desktop/tests/` Store、路由、页面状态与组件测试。
- `tests/e2e/` 临时 Runtime 主链。
- Tauri Rust 单元与 sidecar 打包 smoke。

## 20. 分批实施顺序与回退点

### P0-A：安全基线与数据库接管

- 固化数据库迁移、配置、启动顺序和目标契约基线测试。
- 生成旧路由 / API / 表 / 字段兼容矩阵。
- 建立真实开发库匿名结构指纹，不复制业务正文。
- 拆分 legacy baseline、迁移锁、备份恢复与数据库配置入口。
- 实现 0015–0017 的空库、0014、已知 legacy 和未知指纹测试。

2026-07-26 收口状态：

| 交付项 | 状态 | 证据 |
| --- | --- | --- |
| 数据库迁移、配置、启动顺序和目标契约基线 | 已完成 | P0-A 固定测试文件清单与阶段验证记录 |
| 旧路由 / API / 表 / 字段兼容矩阵 | 已完成 | `docs/P0-ACCOUNT-FOUNDATION-COMPATIBILITY-MATRIX.md` |
| 匿名 Schema 指纹与未知结构拒绝 | 已完成 | `persistence/migration/fingerprint.py`、`legacy_baseline.py` |
| 数据库路径、迁移配置、锁与备份恢复 | 已完成 | `config/database.py`、`config/migration.py`、`persistence/migration/` |
| `0015–0017` 与目标契约 | 已完成 | `alembic/versions/0015_p0_expand.py` 至 `0017_p0_enforce_and_cutover.py` |
| 生产启动接管 | 已完成 | `app/lifecycle.py`、`app/factory.py` |
| 文档同步与阶段验证 | 已完成 | 14 个定向测试文件 `94 passed in 52.95s`；Python 编译、差异和 UTF-8 门禁通过 |

持久任务、账号 Topic 与受控 legacy Bootstrap / 系统 / 任务薄适配已经由 P0-B 退出过渡状态。`accounts.status='active'`、部分 nullable 账号外键、legacy 账号 / AI API 和旧 AI 读取链仍是已登记过渡项，分别由 P0-C、P0-E 退出。写门、回退 Runtime 制品兼容、`cutover_event_id` 和增量灾难恢复证据属于 P0-F 发布阻断门，不得把 P0-A 启动期恢复表述为完整生产灾难恢复。

验证：2026-07-26 唯一一次 P0-A 阶段测试通过，14 个定向测试文件 `94 passed in 52.95s`；隔离 Runtime 数据目录、数据库、pytest basetemp 和 pycache；Runtime / Alembic `compileall`、`git diff --check` 与 UTF-8 无 BOM 门禁通过。  
回退：写门开放前失败才恢复迁移前数据库备份；写门开放后使用兼容当前 Schema 的上一 Desktop + 回退 Runtime，不覆盖已迁移数据库。

### P0-B：Runtime v1 内核

- 拆分 app container、异常、结构化日志和配置入口。
- 建立 v1 路由装配、Runtime 许可证门、统一信封、错误码、`log_id` 和请求上下文。
- 建立任务模型、账号范围 WebSocket topic、sequence、重放与最终状态补拉。
- 旧 API 只做薄转发，并建立完整错误码 / 字段映射。

2026-07-26 收口状态：

| 交付项 | 状态 | 证据 |
| --- | --- | --- |
| `/api/v1`、Runtime 会话、安全门与许可证门 | 已完成 | 13 个 HTTP + 1 个 WebSocket 路由与文档库存一致 |
| 信封、错误码、`log_id`、请求上下文与脱敏日志 | 已完成 | Validation 动态键失败封闭，Token、Prompt、Provider body 与本地路径不泄漏 |
| 持久任务、幂等、超时、取消、重试与恢复 | 已完成 | `runtime_tasks`、快照 v2、处理器版本与任务 Runner |
| 账号 Topic、sequence、重放、HTTP 对账与 outbox | 已完成 | `runtime_events`、账号订阅门与最终状态补拉 |
| legacy 薄转发与接口文档 | 已完成 | Bootstrap、系统设置和任务兼容适配器；`docs/api/v1/` 为 v1 唯一真源 |
| 阶段验证 | 已完成 | 41 个定向测试文件 `239 passed, 1 skipped in 171.75s`；391 个 Python 文件编译、差异与 UTF-8 门禁通过 |

验收前收口运行暴露 4 个迁移契约问题，修复后才执行最终阶段验收；不得把失败运行表述为通过证据。

验证：v1 信封 / 许可证 / 错误 / 任务 / WS 契约、旧接口不双写、迁移 round-trip 与降级失败原子性。  
回退：v1 尚未被 Desktop 使用；恢复上一 Runtime 构建，新表保持加法状态。

#### P0-C C0 契约收口（2026-07-26）

P0-C 写生产代码前固定以下决策：

1. 配置复制继续使用已批准白名单 `positioning / knowledgeRules / brandKit / aiRecipe / publishDefaults`。PRD 只定义“配置复制”能力，没有列出更窄白名单，因此不存在删除 BrandKit 的产品真源冲突；其中 `aiRecipe` 在 P0-C 只通过 `AIRecipeCopyPort` 调用，P0-E 未接入时明确进入 `skippedSections`，不得伪复制。
2. `KnowledgeSource.kind` 统一为持久媒体语义 `document / image / video / audio / text / reference`；`sourceMode` 单独表达 `file / url / text` 输入方式。`deleted_at` 映射输出状态 `removed`，不覆盖原索引证据。
3. 0019 加法迁移补齐 `knowledge_snapshots.label` 和普通写幂等表；BrandKit 输入与输出补齐现有 `voice_rules_json` 对应的 `voiceRules`。
4. 创建账号、复制、归档、恢复、版本创建和来源写入统一使用 `runtime_mutation_idempotency`；同键异参返回 `409 REQUEST_CONFLICT`，不在路由内各自保存幂等状态。
5. 列表默认值和上限只读取配置总线的 `api.paginationDefaultLimit` 与 `api.paginationMaxLimit`，cursor 编解码由公共 dependency 提供。
6. `subscriptionRevision` 只属于 Desktop / WebSocket 订阅帧，不进入 `AccountWorkspaceContextDto`；HTTP 使用资源 `workspaceRevision`，事件最终一致性继续按 Topic `sequence` 补拉。
7. P0-C 定义 `AccountAIReadinessPort` 与 `AIRecipeCopyPort`，不提前实现 Provider、模型、Prompt、Route 或 Recipe；P0-E 在同一事务边界接入真实实现。
8. 连接绑定只允许引用数据库中真实存在且账号一致的 DeviceWorkspace、BrowserInstance 与 ExecutionBinding。P0-C 不伪造环境对象；没有候选对象时返回 `WORKSPACE_UNAVAILABLE`，真实环境创建与 Supervisor 所有权留在 P0-F。

### P0-C：账号纵向链

- 先完成 C0 契约收口，解决知识 DTO、普通写幂等、分页配置、修订来源、AI 端口和真实执行对象边界。
- 落地账号五状态、健康、真实连接修正、复制、归档 / 恢复。
- 落地定位、知识库、BrandKit 和发布默认值基础对象。
- 强制服务、仓储、缓存、文件、任务、日志和事件的账号范围。
- 完成账号相关 v1 文档与跨账号负向测试。

验证：账号 Unit / Contract、跨账号隔离、复制事务、归档恢复和迁移回归。2026-07-26 阶段范围共 175 项；最后一次完整运行 `169 passed, 6 failed in 123.31s`，6 项仅为幂等重放断言与正确生产响应不一致，修正后定向复验 `6 passed in 23.52s`，阶段验收通过。静态编译、模块导入、44 个 HTTP + 1 个 WebSocket 文档库存、差异与 UTF-8 门禁同时通过。  
回退：新账号对象为加法；P0-F 正式发布前不开放新写门。非生产旧 Desktop 只保留账号读取过渡，旧账号写入明确返回 410；确需恢复旧写入时整体恢复上一兼容 Runtime 构建，禁止双写两套状态机。

### P0-D：Desktop 账号上下文

- [x] 拆分 Runtime client / types，迁移 Bootstrap、账号、定位知识、配置、任务和事件调用。
- [x] 落地 Account Context、未保存守卫、迟到响应隔离、账号切换器和真实工作区空态。
- [x] 落地账号管理、六步向导、定位知识 P0 页面和两档 PC 壳层。
- [x] 新 Route Manifest 只在测试 / 受控 P0 构建启用，不向用户提供双壳切换控件。
- [x] 执行 P0-D 单次阶段门禁并记录证据：Runtime 38 项、Desktop 50 项均取得通过证据；P0-D 新路径 `vue-tsc` 错误为 0，受控构建处理 468 个模块并通过；真实 Runtime 完成授权、目录、双账号隔离、页面恢复、归档清理和两档 PC 窗口 E2E，Console 为 0 错误、0 警告。全仓 79 个冻结 legacy 类型错误明确留待 P0-F 正式切换前清零，不表述为全量类型检查通过。

验证：Runtime 首次 `37 passed, 1 failed`，更正测试字段后定向 `1 passed`；Desktop 首次 `49 passed, 1 failed`，修复真实 Pinia 响应性缺陷后定向文件 `7 passed`，因此阶段范围 38 + 50 项均有通过证据。`build:p0` 用时 `5.14s`；E2E 使用独立临时数据库与工作区。  
回退：发布前恢复上一 Desktop 构建；数据库和 Runtime 仍兼容旧客户端。

### P0-E：AI 配置纵向链

- [x] 落地 Provider、Model、Capability、Prompt、Composition Template、Capability Route 与 Account Recipe。
- [x] 完成安全存储引用、能力契约验证、配置修订、继承和未保存守卫。
- [x] 迁移 AI 系统页面和客户端；旧 AI 配置保持只读映射。
- [x] 完成 `docs/api/v1/ai-system.md` 与安全负向测试。

2026-07-26 收口状态：

| 交付项 | 状态 | 证据 |
| --- | --- | --- |
| 系统 AI 对象与账号 Recipe | 已完成 | 35 个 AI HTTP、`0020_p0e_ai_vertical_chain`、版本与账号聚合服务 |
| 安全凭据、脱敏与幂等 | 已完成 | Provider 摘要仅返回 `credentialSummary`；明文不进入数据库、响应、任务、事件或日志 |
| Provider / 模型 / 能力 / Route | 已完成 | 健康检查、模型发现、能力验证三类持久任务；Provider 未就绪与能力未验证均阻断路由 |
| Prompt / Composition / Recipe 版本 | 已完成 | 不可变版本 ID、单调聚合修订、验证后激活与 AI 配置漂移阻断 |
| Desktop 系统 AI 与账号 Recipe | 已完成 | 领域客户端、配置 Store、五步 Provider 向导、空态 / 错误 / 重试 / 未保存守卫 |
| 文档与阶段门禁 | 已完成 | Runtime 71 项、Desktop 41 项均取得通过证据；额外 14 项 DTO 回归通过；受控构建和静态门禁通过 |

验证：Runtime 首次 `65 passed, 6 failed`，修复 Provider 摘要、路由错误优先级、幂等安全引用和 SQLite DDL 前预校验后，仅定向复验 6 个失败点并全部通过。Desktop 首次 `38 passed, 3 failed`，修复本地校验错误映射与测试隔离后定向文件 `17 passed`；Provider / Route DTO 收口后额外 `14 passed`。`build:p0` 处理 530 个模块并通过；P0-E 新路径类型错误为 0，79 个冻结 legacy 类型错误留待 P0-F；113 个相关文件通过 UTF-8、无 BOM 与 500 行门禁。  
回退：未验证的新 AI 对象不成为默认路由；恢复旧只读配置视图，不复制明文密钥。

### P0-F：路由切换、Tauri 打包与最终验收

- [x] 打包 Runtime sidecar，增加 Supervisor、单实例、动态端口、生产数据目录和退出清理。
- [x] 首启页展示 Runtime 自动生成的只读完整机器码并允许复制；激活请求只提交许可证密钥，窗口使用 Windows 原生标题栏和标准窗口控制。
- [x] 签发工具在签发前强制校验私钥与 Runtime 内嵌公钥一致，密钥对初始化拒绝静默覆盖；测试不得写入或轮换真实签发密钥。
- [x] 启用新十三 Route，旧 URL 只做一次性重定向。
- [x] 确认旧剪辑工作台和独立流程入口不可达。
- 迁移实际变更后到 durable 写门开放前，Secret Store、容器、兼容证据、Runtime 事件或后台启动任一步失败，统一由独立启动恢复协调器先停止后台、释放 Engine，再依据 cutover journal 恢复迁移前状态并校验指纹。`MigrationReport` 只在进程内保留受控备份句柄，日志和生命周期事件仅暴露 `backup_database_id`、稳定错误码与 `log_id`，不暴露路径。
- journal 已记录 `write_gate_opened` 时禁止自动恢复；迁移未产生变更时同样不触碰数据库。恢复本身失败必须保留当前数据库、备份和 durable 证据并停止启动。
- [x] 执行全量测试、浏览器 E2E、安装包 smoke、Tauri / Rust 测试与视觉验收。

验证：Desktop `107 passed`、全局类型检查、239 模块生产构建、真实 Runtime E2E `7 passed`、Rust `17 passed`、受限 `PATH` Sidecar smoke、NSIS 安装包 smoke、Light / Dark 与两档 PC 视觉验收均通过。安装包无需系统 Python并覆盖 Supervisor ready、生产数据落点、单实例和进程树清理；机器码和迁移恢复收口定向测试 `11 passed`。本地 file 知识来源桥继续失败封闭并转入 P1，不计入 P0 完成范围。  
回退：写门开放后恢复“上一 Desktop + 前向兼容回退 Runtime”并继续使用当前数据库；只有验证阶段尚未开放写门时才允许恢复迁移前备份。制品不混用，强制数据恢复必须执行增量导出 / 重放与核对流程。

P0-C、P0-D 和 P0-E 必须保持独立提交 / 审核边界，不合并为一个无法回退的大改。

## 21. 最终验收标准

1. 安装后的 Windows 桌面应用无需系统 Python即可启动真实 Runtime。
2. 许可证、目录、数据库迁移和 Runtime 健康失败都有中文反馈、`log_id` 与恢复动作。
3. 主导航只有十个账号入口；剪辑工作台和独立配音 / 字幕 / 渲染 / 自动化不可达。
4. 账号管理从左下切换器进入，创建、真实连接、复制、归档和恢复完整可用。
5. 切换账号后 UI、缓存、请求、任务、日志上下文、文件范围和 WebSocket 不混入上一账号。
6. 定位、知识库、BrandKit、发布默认值和 AI Recipe 独立绑定账号。
7. Provider、模型、能力、Route、Prompt 和 Composition Template 有真实配置、验证、版本和安全凭据引用。
8. 无真实数据时只显示中性空态；P1 / P2 未迁移功能不展示伪结果。
9. `/api/v1`、统一信封、错误码、修订、幂等、任务和事件契约稳定。
10. `docs/api/v1/` 与实际路由、DTO、错误码和事件一致。
11. 已识别大文件完成职责拆分，P0 新代码不形成新的集中大文件。
12. Light / Dark、`1440×900` 与约 `1180×760` 完成主链，`960px` 最小宽度无错位或手机化。
13. 相关单元、契约、迁移、UI、E2E、Tauri、构建和差异检查全部通过。

## 22. 实施批准边界

本规格批准后只实施 P0。若实施中出现以下任一情况，必须停止并先更新计划 / 规格：

- 需要迁移完整 ContentItem、脚本、分镜、批次或内容库业务。
- 需要物理删除旧 Timeline 或旧业务表。
- 需要新增导航页面或改变账号作为工作区边界。
- 需要接入新的高风险自动化、平台绕过、DRM / 付费墙处理能力。
- 需要把生产 Runtime 改回外部系统 Python、未版本化 API 或页面直连 Provider。

本规格批准前不修改生产代码。
