# TK-OPS 项目状态总览

> 更新日期：2026-08-09
> 当前阶段：P0-H 规格已批准，实施待开始；P0-G 0.4.11 仍为自动化测试候选

> 2026-08-02 复核结论：以下 P0-A 至 P0-F 记录保留为当时阶段证据，不再证明当前工作树或当前制品可交付。当前真实首启 E2E 与门禁外 Tauri 权限测试曾失败，且账号执行环境、监督登录、AI 真执行和八个 pending 页面尚未形成完整生产闭环。当前状态以 P0-G 阶段证据和 release manifest 为准。
> 2026-08-09 更新：0.4.11 补齐环境失败恢复与登录准备取消 E2E，并改为从 portable ZIP 全新解压目录执行 GUI 冷启动门禁；P0-H 实现级规格已批准、实施待开始，真实 TikTok 目标机器证据与 P0-I 创作生产链仍未完成。
> 本文记录当前实现与目标架构的差异，不替代产品、UI、架构或工程真源。

## 1. 文档真源

| 事项 | 唯一真源 |
| --- | --- |
| 产品范围、页面容器、能力边界 | `docs/PRD.md` |
| 视觉、壳层、布局和交互 | `docs/UI-DESIGN-PRD.md` |
| 目录、路由、服务和模型落点 | `docs/ARCHITECTURE-BOOTSTRAP.md` |
| 工程约束与协作流程 | `AGENTS.md` |
| P0 实施范围与顺序 | `docs/superpowers/plans/2026-07-19-prototype-to-production-p0-account-foundation.md` |
| P0 数据、接口、状态和验收契约 | `docs/superpowers/specs/2026-07-19-prototype-to-production-p0-account-foundation-design.md` |
| 当前生产闭环路线 | `docs/superpowers/plans/2026-08-08-production-ai-creation-real-validation.md` |
| P0-G Production 加固规格 | `docs/superpowers/specs/2026-08-08-p0-g-production-hardening-design.md` |
| P0-H 真实 AI 执行规格 | `docs/superpowers/specs/2026-08-09-p0-h-real-ai-execution-design.md`，已批准、实施待开始 |
| legacy 接口索引 | `docs/RUNTIME-API-CALLS.md` |
| 目标 `/api/v1` 接口文档 | `docs/api/v1/`，由 P0-B 开始逐资源建立 |

发生冲突时按 `PRD -> UI-DESIGN-PRD -> ARCHITECTURE-BOOTSTRAP -> AGENTS` 裁决。旧 V2、M05–M15、Stitch、Graphify 和原型文档只能作为迁移或视觉参考。

## 2. 产品目标

TK-OPS 的目标形态是 Windows 10/11、本地优先、一机一码授权、TikTok 优先的“账号定位驱动的 AI 短视频策划、批量生产与媒体工作台”。

账号是工作区与数据隔离边界，目标主链为：

```text
Account
→ ContentPlan
→ ContentItem
→ Script
→ Storyboard
→ ProductionBatch
→ ContentVariant
→ CompositionSpec
→ RenderTask
→ PublishTask
```

正常账号工作区只有十个主入口：

1. 工作台
2. 定位与知识
3. 脚本与选题
4. 分镜规划
5. 视频拆解
6. 批量生产
7. 内容库
8. 媒体工具箱
9. 发布
10. 复盘

账号管理和 AI 与系统设置是系统级页面。产品不提供 AI 剪辑工作台、手动多轨时间线、团队后台、经营系统、高风险设备伪装或平台保护绕过。

## 3. 当前实现事实

### 3.1 已完成

- Tauri 2 + Vue 3 桌面壳、FastAPI Runtime、离线许可证、配置总线、SQLite 和现有业务适配器可作为迁移基础。
- 本地账号工作区交互原型已经验证十入口、左下账号切换、账号管理、AI 配置、创作链、拆解表格、批次流水线、内容库、媒体工具和中性空态。
- P0 计划与详细规格已经批准。
- P0-A 数据库接管生产实现已经落地：
  - 统一数据库路径与迁移配置。
  - 已知 legacy 匿名结构指纹与未知结构只读拒绝。
  - 跨进程迁移锁。
  - SQLite DB / WAL / SHM 备份、校验与失败恢复。
  - Alembic `0015_p0_expand -> 0016_p0_backfill -> 0017_p0_enforce_and_cutover`。
  - 列、索引、唯一约束、外键、CHECK 与触发器目标契约。
  - Runtime 在创建 Engine、Repository 和 Service 前完成迁移。
- P0-B Runtime v1 内核已经通过阶段验收：
  - 13 个 `/api/v1` HTTP 接口与 1 个账号范围 WebSocket。
  - Runtime Session、Host / Origin 和许可证统一门禁。
  - 统一信封、大写错误码、`log_id`、请求上下文与脱敏结构化日志。
  - SQLite 持久任务、快照 v2、幂等、超时、取消、重试、重启恢复和有界停机。
  - 账号 Topic、sequence、outbox、断线重放和 HTTP 最终状态补拉。
  - Bootstrap、系统设置和任务 legacy 薄适配器。
  - Alembic `0018_p0_runtime_kernel` 与跨 revision 降级失败原子性保护。
- P0-C 账号纵向链已经通过阶段验收：
  - Alembic `0019_p0_account_vertical_chain` 接管五状态、账号配置、知识快照标签和普通写幂等表；迁移只保守补齐空知识库与发布默认值，不伪造来源、快照、连接或 ready。
  - 账号创建、详情、工作区上下文、六步向导、白名单配置复制、归档、恢复和真实健康检查服务。
  - `Account -> DeviceWorkspace -> BrowserInstance -> ExecutionBinding` 同账号真实连接约束。
  - 定位版本、知识规则与六类来源、真实 text / 公共 HTTPS 索引任务、不可变快照、BrandKit 和发布默认值；file 来源在受控文件桥前明确失败封闭，该桥转入 P1。
  - 普通账号写操作持久幂等、账号聚合修订、分页配置、账号 Topic、outbox、缓存失效与安全日志。
  - 新增 31 个账号范围 v1 HTTP；P0-C 验收时总库存为 44 个 HTTP + 1 个 WebSocket。
  - 新增 `account.health_check`、`account.restore_health_check`、`account.connection_check` 与 `knowledge.index` 四个账号任务类型。
  - `docs/api/v1/` 已按真实路由同步接口、错误、任务、事件与配置键；P0-C 的 44 个 HTTP + 1 个 WebSocket 库存和 UTF-8 静态门禁已通过。
- P0-D Desktop 账号上下文已经通过阶段验收：
  - Runtime Client / Types 已按 Bootstrap、账号、定位知识、系统配置、任务和事件拆分；P0-D 新模块不再导入旧单文件客户端，组件不直接请求 Runtime。
  - 账号 DTO 新增定位摘要与最近使用时间；新增工作区激活和真实连接候选 2 个 HTTP，账号范围现为 33 个 HTTP，当前总库存为 46 个 HTTP + 1 个 WebSocket。
  - Account Context 已覆盖最近账号恢复、prepare / commit 切换、迟到响应隔离、可逆资源、未保存守卫、配置总线页面记忆和账号事件重订阅。
  - 受控 P0 Route Manifest、新 Bootstrap Gate、十入口账号壳、左下账号切换器、状态栏、宽屏与紧凑 PC 布局已经落地；小于 960px 明确提示仅支持 PC 工作区。
  - 账号管理、六步向导、复制、归档恢复、真实连接候选与健康任务，以及定位、知识规则、来源、索引、快照和 BrandKit 页面均接入 v1 真实数据。
  - 无账号、加载、空、筛选空、依赖阻断、离线、失败与重试状态已经覆盖；当前账号归档会原子清空账号上下文，不保留旧账号快照。
- P0-E AI 配置纵向链已经通过阶段验收：
  - Alembic `0020_p0e_ai_vertical_chain` 补齐 Prompt 聚合修订与账号 AI Recipe 内容摘要，并在 SQLite DDL 前预校验 legacy Recipe JSON。
  - Provider、Model、Capability、Capability Route、Prompt Profile、Composition Template 与 Account AI Recipe 已进入统一 v1 服务、仓储、配置修订、幂等和事件边界。
  - Provider 凭据只进入系统安全存储，读取只返回 `credentialSummary`；Prompt 正文、凭据、本地路径和任务快照均有负向安全契约。
  - `provider.health_check`、`provider.model_discovery` 与 `model.capability_check` 三类持久任务覆盖超时、取消、失败、日志和最终补拉。
  - Provider 就绪、模型能力契约、Prompt / Template 不可变版本与系统 AI 修订共同约束 Capability Route 和账号 Recipe 的验证与激活。
  - Desktop AI 与系统设置、Provider 五步向导、模型与路由、Prompt / 合成模板版本及账号 AI Recipe 已接入真实 Runtime，覆盖首次使用、依赖阻断、长任务、错误、重试和未保存状态。
  - AI v1 新增 35 个 HTTP；当前总库存为 81 个 HTTP + 1 个 WebSocket。
- P0-F 路由切换与 Windows 桌面交付已经通过最终验收：
  - 正式 Route Manifest 固定十三个页面容器与十个账号级入口；旧 Project / Timeline 和独立流程 URL 只做单次重定向，旧业务页面不可达。
  - Runtime sidecar、Tauri Supervisor、单实例、动态 loopback 端口、内存会话、生产数据目录、90 秒冷启动、有限重启、优雅退出与进程树清理已落地。
  - 迁移写门、durable cutover journal、写门前恢复、写门后禁止覆盖当前数据库和前向兼容回退 Runtime 制品已形成可验证证据。
  - 正式全局 `vue-tsc --noEmit` 已通过，P0-D / P0-E 登记的 79 个 legacy 类型错误已随正式路由收口清零。
  - Windows NSIS 安装包无需系统 Python 即可离线启动，安装、单实例、生产数据落点、Supervisor ready 与卸载后进程树清理 smoke 已通过。
- P0-G 账号工作区与 Production 加固已形成 0.4.11 测试候选：
  - 真实受控工作目录、执行环境、进程所有权、账号绑定、监督登录、任务恢复、归档清理和 Runtime generation 恢复已经闭环。
  - 机器身份、许可证、Sidecar ABI、原生窗口、单实例、优雅退出、安装包与发布证据链已加固。
  - Runtime、Desktop、Rust、账号兼容 E2E、安装包与许可证实包 smoke 继续进入全量门禁；首启证据扩为 5 项，GUI 冷启动门禁扩为 9 项。
  - release manifest v2 为 `channel=test`、`dirty=true`，包含 10 份证据与 4 个当前制品；未提升 production 指针。

### 3.2 尚未完成

- 本地 file 知识来源的 Tauri 受控选择、复制、校验与索引桥尚未实现；当前继续失败封闭并保留重试，属于 P1。
- ContentItem、单条生产、完整批量生产、拆解回流、内容库和分级媒体工具属于 P1。
- 真实发布、回执、恢复与复盘证据回流属于 P2。
- P0-H 详细规格已覆盖 H1-H5、模型/API/状态/文件地图/验收/rollback，并已批准；生产代码实施待开始。P0-I 创作生产链仍未实施，八个业务页面不得以 pending 壳冒充完成。

## 4. 阶段状态

| 批次 | 当前状态 | 已有成果 | 退出条件 |
| --- | --- | --- | --- |
| P0-A 安全基线与数据库接管 | 阶段验收通过 | 生产实现、兼容矩阵、文档和阶段验证已完成 | 已退出 |
| P0-B Runtime v1 内核 | 阶段验收通过 | `/api/v1`、安全门、信封、日志、持久任务、账号事件与 legacy 薄转发已完成 | 已退出 |
| P0-C 账号纵向链 | 阶段验收通过 | 0019、账号服务、31 个 HTTP、四个账号任务、定位知识品牌对象、v1 文档与隔离验证均已完成 | 已退出 |
| P0-D Desktop 账号上下文 | 阶段验收通过 | 领域 Runtime Client、Account Context、受控新壳、账号管理、定位知识、真实状态矩阵和真实 Runtime E2E 已通过 | 已退出 |
| P0-E AI 配置纵向链 | 阶段验收通过 | 0020、35 个 HTTP、系统 AI 对象、安全凭据、三类任务、版本、路由、账号 Recipe 与 Desktop 工作面均已完成 | 已退出 |
| P0-F 路由切换与桌面交付 | 历史阶段已退出 | 旧证据保留；当前可交付性改由 P0-G 0.4.11 manifest 证明 | 已退出 |
| P0-G 账号执行与 Production 加固 | 测试候选通过 | 真实账号/工作区/执行环境、监督登录、恢复、GUI、安装包与许可证实包证据已通过 | 目标机器 TikTok 证据与干净提交后提升 Production |
| P0-H AI 真执行 | 规格已批准，实施待开始 | H1-H5 实现级规格、精确文件地图、两层证据与 rollback 已形成 | 按 H1 → H5 实施；真实 Provider 调用、受控知识文件、任务/日志/成本与失败恢复通过 |
| P0-I 创作与批量生产 | 未开始 | 产品与交互规格已确认 | 单条创作、拆解、批量、内容库和分级媒体工具逐阶段通过 |
| P2 发布与复盘 | 未开始 | 旧实现仅作为迁移参考 | 真实绑定、预检、回执、恢复和证据回流通过 |

## 5. 阶段验证证据

P0-A 阶段验收记录（2026-07-26）：

- 严格遵守单次阶段测试节奏，没有重复运行 pytest。
- 命令：`venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <isolated> --tb=short -q <P0-A 14 个定向测试文件>`；固定文件清单见兼容矩阵第 8 节。
- 结果：`94 passed in 52.95s`，退出码 0。
- 覆盖：数据库路径、迁移配置、legacy 指纹、迁移锁、DB/WAL/SHM 备份恢复、`0015–0017`、目标 Schema 契约、启动顺序、日志与 UTF-8 主链。
- 环境：独立临时 Runtime 数据目录、数据库、pytest basetemp 和 pycache；未把开发数据库或种子数据作为通过证据。
- 静态证据：Runtime 与 Alembic `compileall` 退出码 0；`git diff --check`、UTF-8 无 BOM 和真源术语检查通过。

P0-B 阶段验收记录（2026-07-26）：

- 最终命令：`venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <isolated> --tb=short -q <P0-B 41 个定向测试文件>`。
- 最终结果：`239 passed, 1 skipped in 171.75s`，退出码 0。
- 覆盖：v1 Bootstrap / 配置 / 诊断 / 任务 / WS、Runtime 安全、日志脱敏、持久任务与事件、legacy 薄适配、0018 迁移、数据库接管与许可证主链。
- 验收前收口运行结果为 `235 passed, 1 skipped, 4 failed`；失败仅集中在迁移降级夹具与跨 revision 失败原子性，修复并完成独立静态审查后才执行最终验收。
- 静态证据：391 个 Python 文件编译、16 个核心模块导入、18 个 Alembic revision、13 个 HTTP + 1 个 WebSocket 文档库存、`git diff --check` 和 UTF-8 无 BOM 门禁通过。
- 环境：最终运行使用独立 pytest basetemp，不读取或覆盖开发数据库。

P0-C 阶段验收记录（2026-07-26）：

- 阶段范围覆盖 23 个定向测试文件，共 175 个契约、迁移、账号生命周期、连接、知识、任务、隔离与 P0-B 主链回归用例。
- 最后一次完整阶段运行结果为 `169 passed, 6 failed in 123.31s`；6 项均为同一个幂等重放测试断言错误，生产响应已经正确返回 `idempotentReplay=true`。
- 修正断言后只复验该参数化用例，结果为 `6 passed in 23.52s`。修正未改生产代码，因此阶段范围内 175 项均已取得通过证据。
- 验收过程中真实发现并修复 SQLite batch 重建表时的跨表触发器顺序、Windows IANA `tzdata` 依赖、测试 Runtime Session、工作区与浏览器落库顺序，以及同步 yield 依赖的 ContextVar 跨上下文复位问题。
- 静态证据：Runtime / Alembic / 测试 Python 编译、关键模块导入、44 个 HTTP + 1 个 WebSocket 文档库存、`git diff --check`、494 个 Python / Markdown 文件 UTF-8 无 BOM 门禁通过。
- 所有运行均使用独立 pytest basetemp、Runtime 数据目录和数据库，未读取或覆盖开发数据库。

P0-D 阶段验收记录（2026-07-26）：

- Runtime 阶段范围为 6 个定向文件、38 项。首次运行 `37 passed, 1 failed in 36.33s`，唯一失败是测试误读不存在的 `RuntimeEvent.id`；更正为真实字段 `event_id` 后只复验该项，结果 `1 passed in 4.25s`。生产代码未因该断言修改，38 项均已取得通过证据。
- Desktop 阶段范围为 14 个 P0 Vitest 文件、50 项。首次运行 `49 passed, 1 failed in 13.44s`，失败真实暴露知识 Store 异步写入原始缓存对象后页面停留加载态；修复生产 Pinia 响应性后只复验该文件，结果 `7 passed`，50 项均已取得通过证据。
- `vue-tsc --noEmit` 的 P0-D 新路径过滤结果为 0 个错误；全仓仍报告 79 个冻结 legacy 路径错误，已登记为 P0-F 切换前债务，不表述为全量类型检查通过。
- 受控 P0 构建 `npm --prefix apps/desktop run build:p0` 通过，处理 468 个模块，耗时 `5.14s`。
- 真实 Runtime E2E 使用独立临时数据库与工作区，完成许可证激活、目录初始化、无账号空态、双账号创建与切换、各账号最近工作面恢复、账号 A 定位与知识对账号 B 不可见、归档当前账号后原子清空上下文；1180×760 无页面级横向溢出，900px 宽度显示 PC 窗口下限提示，浏览器 Console 为 0 错误、0 警告。
- E2E 首次启动发现开发编排器未向 Runtime 安全中间件传递预期 Host；已改为从受控 Runtime URL 注入 `TK_OPS_RUNTIME_EXPECTED_HOST`，随后真实启动链通过。
- 静态证据：当前库存为 46 个 HTTP + 1 个 WebSocket，`git diff --check` 与 P0-D UTF-8 无 BOM 门禁通过。

P0-E 阶段验收记录（2026-07-26）：

- Runtime 阶段范围为 6 个定向文件、71 项。首次运行 `65 passed, 6 failed in 225.35s`；失败集中在 Provider 摘要字段、能力路由错误优先级与安全幂等快照、以及 SQLite 迁移失败原子性。修复后只复验 6 个失败点并全部通过；迁移正常回填另补 1 项回归证据。
- Desktop 阶段范围为 6 个 P0 Vitest 文件、41 项。首次运行 `38 passed, 3 failed`；修复本地 JSON 错误映射和测试隔离后只复验 2 个失败文件，结果 `17 passed`，因此 41 项均取得通过证据。
- Provider 响应统一改为 `credentialSummary`，Capability Route 补齐稳定 `id` 后，额外执行相关 2 个 Desktop 文件 `14 passed`；两项 Provider 敏感数据 / DTO Runtime 定向用例 `2 passed in 10.95s`。
- `vue-tsc --noEmit` 的 P0-E 新路径过滤结果为 0 个错误；全仓仍报告原有 79 个冻结 legacy 路径错误，继续登记为 P0-F 切换债务，不表述为全量类型检查通过。
- 受控 P0 构建通过，处理 530 个模块，耗时 `12.86s`。当前 v1 库存为 81 个 HTTP + 1 个 WebSocket。
- 静态证据：`git diff --check` 通过；113 个 P0-E 相关 Python、TypeScript、Vue、CSS、Markdown 文件通过 UTF-8、无 BOM 与单文件不超过 500 行门禁。

P0-F 最终验收记录（2026-08-01）：

> 历史证据说明：本节数字和哈希在 2026-08-01 对应构建中当时有效；2026-08-02 当前源码、测试与制品已发生漂移，不得作为当前发布证据，也不会被覆盖或改写。

- Runtime / Contract 按 P0 阶段矩阵完成全量收口；最终发现的 21 项 legacy 契约不一致已修正并仅定向复验受影响范围。收口后机器码、迁移启动与写门恢复定向测试 `11 passed in 11.20s`。
- Desktop P0 测试覆盖 23 个文件、`107 passed`；全局 `vue-tsc --noEmit` 通过，Vite 生产构建处理 239 个模块并通过。
- 真实 Runtime 浏览器 E2E `7 passed`：覆盖许可证、目录、两账号隔离、设备 / 工作区 / 执行绑定、Provider / 模型 / 路由 / Prompt / Recipe、WebSocket、归档恢复、十三 Route 和三组视觉基线。
- Rust `cargo fmt --check`、`cargo check` 通过，单元测试 `17 passed`；新增重启顺序契约保证旧进程完成清理后才进入退避和新世代。
- 受限 `PATH` Sidecar smoke 通过，build ID 为 `0.4.7-x86_64-pc-windows-msvc-d7538489342f`；证明生产链不依赖系统 Python 或 `PATH` 中的 PowerShell。
- NSIS 安装包 smoke 通过 Supervisor ready、生产数据落点、离线启动、单实例和进程树清理。制品 `TK-OPS_0.4.7_x64-setup.exe` 为 `30,984,341` 字节，SHA-256 为 `E75501CA8BBA51A610ED411CEFD1B09844FF3A9EACCA8824AEA09F41EF688F75`。
- Light `1440×900`、Dark `1440×900`、Dark `1180×760` 视觉验收通过；账号切换器、状态栏和工作面在两档 PC 窗口无手机化或页面级错位。

## 6. 已知过渡项

| 过渡项 | 当前状态 | 退出阶段 |
| --- | --- | --- |
| `accounts.status='active'` | 0019 与新写入已切换五状态；迁移、约束和 legacy 兼容证据已通过 P0-C 验收 | 已退出 |
| 工作区、浏览器实例和执行绑定的部分账号外键可空 | 旧数据无法可靠推断时不伪造；v1 只接受真实完整绑定，物理收紧须另立数据库迁移计划 | 后续独立计划 |
| legacy 账号读取与 AI API | 正式 Desktop 已退出 legacy 调用；非生产兼容读取冻结保留，不再承载新增能力 | 正式路径已退出 |
| 新 AI 配置表为禁用或未验证回填 | P0-E 始终按 unknown / incomplete 读取，并强制健康、能力与版本验证；未伪装为 ready | 已退出 |
| 旧 Project/Timeline 和独立页面仍在代码中 | 正式路由已解除，只允许作为迁移源；物理删除须另立计划 | 正式路径已退出 |
| 生产写门与回退 Runtime 制品 | P0-G 0.4.11 test manifest 继续受目标机器证据与干净提交门禁约束 | Production 提升 |
| 本地 file 知识来源桥 | 当前失败封闭，不读取任意本地路径；rootRef 授权、账号 Asset 与索引链已写入 P0-H 规格 | P0-H |

## 7. 当前下一步

1. 在目标测试机器上使用当前 0.4.11 制品完成一次真实 TikTok 可见浏览器监督登录，生成绑定 Desktop、Runtime 与安装包哈希的证据。
2. 整理当前脏工作树为干净提交后重新构建 production 通道；在两项门禁满足前不提升 `current.json`。
3. 审批 P0-H 详细规格；批准前不修改生产实现，批准后严格按 H1→H5 接通 AI 配置、受控知识文件与真实 AI Execution Gateway，并以真实 Provider 调用验收。
4. P0-H 通过后进入 P0-I，按账号内容主链逐步开放八个 pending 页面，不一次性伪开放。

## 8. 交付纪律

- 不把未提交原型、演示数据或旧页面测试当作生产完成证据。
- 每个阶段同步 plan/spec、项目状态、接口文档、错误码和调用说明。
- 每个阶段保持独立文件边界、代码审查和回退点。
- 没有真实 Runtime 数据时只显示中性空态或受限状态。
- 所有长任务必须有超时、取消、失败、重试、日志和最终状态补拉。
