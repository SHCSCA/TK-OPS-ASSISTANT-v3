# TK-OPS 原型转生产：P0 账号工作区与 AI 配置底座实施计划

> 日期：2026-07-19  
> 状态：已批准（2026-07-20）  
> 实施进度：P0-A 至 P0-F 已于 2026-08-01 全部完成并通过最终验收  
> 执行授权：用户已于 2026-07-26 要求按本计划连续开发并同步文档  
> 测试节奏：P0-A 至 P0-E 各完成后执行一次阶段测试；P0-F 已执行一次 P0 全量测试、构建、E2E、Tauri / 安装包与视觉验收  
> 类型：生产主链迁移、多文件架构调整、前后端契约升级  
> 目标终端：Windows PC 桌面应用，不考虑手机端适配  
> 前置真源：`docs/PRD.md`、`docs/UI-DESIGN-PRD.md`、`docs/ARCHITECTURE-BOOTSTRAP.md`  
> 交互基线：`docs/prototypes/tk-ops-account-workspace/`  
> 原型验收：账号级工作区、低噪音 PC 界面、脚本到分镜再到批量生产、视频拆解表格、AI 配置闭环和业务空态暂时通过

## 1. 背景与现状判断

交互原型已基本确认，但当前生产目录仍保留旧产品结构，不能直接逐页照抄原型：

1. `apps/desktop/src/app/router/route-manifest.ts` 仍使用旧 16 页导航，包含已经明确砍掉的 AI 剪辑工作台、独立配音、字幕、渲染和自动化入口。
2. 前端已有许可证、Runtime 配置、账号、设备、脚本、分镜、拆解、发布等实现，可以迁移复用；但当前主要依赖项目上下文，尚未形成统一 `AccountContextStore` 和账号切换事务。
3. Runtime 已有账号、Provider、模型、Prompt、脚本、分镜和拆解模型，但接口主要仍为 `/api/...`，领域对象与 `/api/v1/accounts/{account_id}/...` 账号范围契约不完整。
4. AI 设置当前以 `AICapabilityConfig`、`AIProviderSetting` 和 `PromptTemplate` 为主，尚未完整区分 `ProviderProfile`、`ModelProfile`、`ModelCapability`、`CapabilityRoute`、`PromptProfile` 与 `AccountAIRecipe`。
5. `apps/desktop/src/app/runtime-client.ts` 与 `apps/desktop/src/types/runtime.ts` 已经成为跨领域集中入口，继续叠加会违反模块边界和大文件约束。
6. `docs/api/v1/` 尚不存在，缺少生产接口唯一真源。
7. 当前工作区含已确认原型和真源文档改动。本计划实施时必须保留这些改动，禁止覆盖或回退用户已有成果。

因此，本阶段采用“迁移式 P0”：先建立真实账号范围、版本化契约、配置总线、错误日志与 AI 配置底座，再迁移 P1 创作页面。禁止直接把演示数据接入生产壳，也不以重建仓库替代迁移。

## 2. 目标与成功定义

本阶段交付一条可真实运行的 P0 纵向主链：

```text
许可证与目录初始化
→ Runtime 健康检查
→ 创建或选择真实账号
→ 连接 / 工作区 / 执行环境诊断
→ 切换账号并隔离缓存、任务和订阅
→ 配置 Provider、模型、能力路由和 Prompt
→ 保存账号 AI 创作档案
→ 进入该账号独立工作区空态
```

成功标准：

1. 新壳不再展示已砍掉的剪辑工作台和旧独立工具入口。
2. 账号切换是可取消、可失败、可重试的事务；切换失败保留原账号，旧请求和旧订阅不能污染新账号。
3. 所有新增账号级接口由路径或强类型上下文确定 `account_id`，请求体不能覆盖作用域。
4. Provider 凭据只保存安全存储引用；UI、日志、账号 Recipe 和任务快照不保存明文密钥。
5. AI 功能可追溯到 Provider、模型、能力路由、Prompt 版本、账号覆盖和配置修订。
6. 生产 UI 至少覆盖加载、空、正常、错误、受限、取消、重试和成功反馈，不以演示数据伪装正常态。
7. 新接口使用 `/api/v1`、统一信封、稳定错误码和 `log_id`，并在 `docs/api/v1/` 提供唯一接口文档。
8. 相关前端、Runtime、契约和主链回归测试通过，Light / Dark 与宽屏 / 紧凑 PC 可用。

## 3. 范围

### 3.1 本阶段纳入

- 许可证、目录初始化、Runtime 与媒体依赖健康的生产入口复核和 `/api/v1/bootstrap` 迁移。
- 新账号工作区壳、左下账号切换器、账号选择态和 `AccountContextStore`。
- 账号创建草稿、状态机、真实连接诊断、配置复制白名单、归档与恢复健康复检。
- 账号定位与知识库的 P0 基础对象、状态摘要和空态；本阶段不实现完整知识检索体验。
- 系统 Provider、模型、模型能力、能力路由、Prompt Profile 与账号 AI Recipe 的真实配置闭环。
- 配置总线、结构化日志、错误码、任务作用域、缓存修订和 WebSocket 账号主题。
- Runtime 客户端与类型按领域拆分，保留必要兼容适配层。
- 新 13 Route ID 壳层落地，以及旧 URL 的一次性迁移重定向。
- Alembic 数据迁移、API 文档、测试和回退验证。

### 3.2 本阶段不纳入

- 不实现 P1 的完整选题、脚本、分镜、视频拆解、批量生产、内容库和媒体工具业务页。
- 不实现 P2 的发布执行和复盘数据回流。
- 不恢复 AI 剪辑工作台、手动多轨时间线或专业剪辑功能。
- 不接入订单、商品、退款、团队协作、重 CRM 或经营看板。
- 不做手机端适配。
- 不在本阶段物理删除旧 Timeline、配音、字幕、渲染和自动化数据；仅从新主导航解除引用，并保留受控迁移与回退路径。
- 不用开发种子数据冒充真实账号、连接、Provider 健康或生成结果。

## 4. 架构决策

### 4.1 迁移而非重写

复用已有许可证、Runtime 启动、账号、设备工作区、Provider 健康和设置服务，逐项迁入新接口与模型。旧接口只在明确兼容窗口内调用新服务层，不再新增业务逻辑。

### 4.2 账号范围是 Runtime 强约束

- 新账号级路由统一放在 `/api/v1/accounts/{account_id}/...`。
- API dependency 解析账号、状态和权限范围，服务与仓储显式接收 `account_id`。
- 文件目录、缓存键、任务、日志和 WebSocket 主题使用相同账号 ID。
- 前端 `accountRevision` 与 AbortController 共同阻止旧响应回写。

### 4.3 配置只走统一总线

优先级固定为：

```text
系统默认 → CapabilityRoute → AccountAIRecipe → 单次批次策略
```

P0 只实现前三层。所有写操作经 Runtime 校验、持久化并广播 `aiConfigRevision` 或 `accountRevision`；页面不维护可独立生效的配置副本。

### 4.4 AI 对象分层

| 对象 | 本阶段职责 |
| --- | --- |
| `ProviderProfile` | Provider 类型、连接地址、凭据引用、并发、超时与健康 |
| `ModelProfile` | Provider 下真实模型 ID、启停、限制与发现来源 |
| `ModelCapability` | 声明能力、适配器能力、契约来源、验证状态与参数边界 |
| `PromptProfile` | 能力、系统提示、任务模板、变量、输出 Schema 与不可变版本 |
| `CapabilityRoute` | 产品能力到主模型、回退模型和 Prompt 版本的系统映射 |
| `AccountAIRecipe` | 账号风格、音色、成本与允许字段的账号级覆盖 |

可用能力只取“供应商声明能力 ∩ 适配器已接入能力”，且必须通过契约验证。

### 4.5 旧能力只解除引用，不静默删数据

- 新主导航切换到 13 Route ID。
- 旧 URL 只做一次性重定向或明确的迁移提示。
- 旧工作台、Timeline 和独立媒体中心文件保持不可达，待后续专门删除计划处理。
- 任何旧数据转换都必须可审计、可重复执行并可回滚。

## 5. 前后端契约门

规格阶段必须为下列资源定义地址、方法、参数、成功信封、错误码、示例、缓存失效和事件：

- `/api/v1/bootstrap/*`
- `/api/v1/accounts`
- `/api/v1/accounts/{account_id}`
- `/api/v1/accounts/{account_id}/connection`
- `/api/v1/accounts/{account_id}/positioning`
- `/api/v1/accounts/{account_id}/knowledge`
- `/api/v1/accounts/{account_id}/ai-recipe`
- `/api/v1/system/providers`
- `/api/v1/system/models`
- `/api/v1/system/model-capabilities`
- `/api/v1/system/capability-routes`
- `/api/v1/system/prompt-profiles`
- `/api/v1/system/config`
- `/api/v1/system/diagnostics`
- `/api/v1/ws`

统一失败信封：

```json
{
  "ok": false,
  "error": "可直接展示的中文错误",
  "error_code": "ACCOUNT_SWITCH_FAILED",
  "log_id": "log_xxx"
}
```

兼容旧 `/api/...` 的期限、转发关系和移除条件必须写入规格，禁止长期双轨。

## 6. 预计文件地图

以下是职责边界，不要求把所有修改堆进同一提交；具体文件名可在规格中微调，但不得越过这些模块边界。

### 6.1 文档与契约

- 新增 `docs/superpowers/specs/2026-07-19-prototype-to-production-p0-account-foundation-design.md`
- 新增 `docs/api/v1/README.md`
- 新增 `docs/api/v1/bootstrap.md`
- 新增 `docs/api/v1/accounts.md`
- 新增 `docs/api/v1/account-knowledge.md`
- 新增 `docs/api/v1/ai-system.md`
- 新增 `docs/api/v1/tasks-and-events.md`
- 新增 `docs/api/v1/errors.md`
- 新增 `docs/P0-ACCOUNT-FOUNDATION-COMPATIBILITY-MATRIX.md`，记录旧路由、旧接口、旧模型和目标落点

### 6.2 Desktop

- 修改 `apps/desktop/src/app/router/route-ids.ts`
- 修改 `apps/desktop/src/app/router/route-manifest.ts`
- 修改 `apps/desktop/src/app/router/index.ts`
- 新增 `apps/desktop/src/app/account-context/`
- 将 `apps/desktop/src/app/runtime-client.ts` 拆为 `apps/desktop/src/app/runtime-client/` 下的核心、账号、Bootstrap 与 AI 系统客户端
- 将 `apps/desktop/src/types/runtime.ts` 按通用信封、账号、Bootstrap 和 AI 系统契约拆分
- 新增 `apps/desktop/src/layouts/account-workspace/`
- 新增 `apps/desktop/src/pages/workspace-home/`
- 迁移 `apps/desktop/src/pages/accounts/` 到 `apps/desktop/src/pages/settings/` 下的新账号管理边界
- 重构 `apps/desktop/src/pages/settings/` 的 AI 设置实现
- 新增或重构 `apps/desktop/src/modules/accounts/`、`ai-recipes/`、`system/`
- 修改 `apps/desktop/src/layouts/shell/` 与全局令牌，落地低噪音账号级壳
- 新增相关 Vitest；旧页面测试保留到兼容入口解除后再删除

### 6.3 Runtime

- 新增 `apps/py-runtime/src/api/dependencies/account_scope.py`
- 新增或迁移 `apps/py-runtime/src/api/routes/v1/` 下的 Bootstrap、账号与系统 AI 路由
- 重构 `apps/py-runtime/src/domain/models/account.py`
- 新增账号定位、知识库基础、Provider、模型、能力、Prompt、路由和 Recipe 模型文件
- 将账号、AI 和配置服务迁入 `apps/py-runtime/src/services/accounts/`、`provider-profiles/`、`model-profiles/`、`capability-routes/`、`prompt-profiles/`、`ai-recipes/` 与 `knowledge/`
- 新增对应仓储与 Schema，所有账号级仓储方法显式接收 `account_id`
- 新增 `apps/py-runtime/src/config/`、`logging/`、`errors/` 统一入口
- 修改 WebSocket 管理器与任务上下文，支持账号主题和修订号
- 新增 Alembic migration，迁移旧账号状态和 AI 配置；禁止在启动时靠隐式 Schema 修补替代正式迁移

### 6.4 测试

- 扩展 `tests/runtime/`：账号状态机、配置复制、归档恢复、AI 配置和迁移
- 扩展 `tests/contracts/`：`/api/v1` 信封、错误码、账号范围和兼容转发
- 新增 Desktop 测试：账号切换事务、旧请求取消、路由守卫、配置未保存守卫和页面状态
- 新增至少一条端到端主链：首启 → 账号 → AI 就绪 → 账号工作区空态

## 7. 分阶段实施

### Gate：计划与规格

- [x] 用户批准本计划。
- [x] 生成详细规格，明确迁移矩阵、数据表、状态机、接口、错误码、事件、页面状态和验收用例。
- [x] 用户已于 2026-07-20 批准规格，可按 P0-A 至 P0-F 分批修改 `apps/desktop`、`apps/py-runtime` 和数据库迁移。
- [x] 用户已于 2026-07-26 授权按本计划连续开发，并要求阶段测试与文档同步。

回退点：规格批准前仅新增计划与规格；批准后的每个 P0 批次保持独立文件边界和回退点。

### P0-A：安全基线与数据库接管

- [x] 生成旧 Route ID / URL、旧 API、旧表和旧字段兼容矩阵。
- [x] 盘点旧 Schema、种子数据、真实开发库和未知结构风险。
- [x] 固化数据库迁移、配置、启动顺序和目标契约基线测试。
- [x] 统一 Runtime 与 Alembic 数据库路径和迁移配置入口。
- [x] 建立已知 legacy 匿名结构指纹，未知结构只读失败。
- [x] 建立迁移锁、DB / WAL / SHM 备份恢复和目标契约校验。
- [x] 实现 `0015–0017` 的空库、已知 revision、已知 legacy、未知指纹和有损 downgrade 保护。
- [x] 将生产启动切换为“配置与日志 → 迁移 → Engine / Repository / Service”。
- [x] 同步 P0-A 文档并执行唯一一次阶段测试：14 个定向测试文件 `94 passed in 52.95s`，Python 编译、差异和 UTF-8 门禁通过。

回退点：业务写门尚未开放时，失败才允许恢复迁移前备份；写门开放后禁止覆盖当前数据库。

### P0-B：Runtime v1 内核

- [x] B1：建立 `/api/v1` 路由装配、Runtime 会话、Host / Origin 防护和许可证门。
- [x] B2：建立统一信封、大写错误码、`log_id`、请求上下文、脱敏日志和配置入口。
- [x] B3：接入持久任务、超时、取消、重试、重启恢复和幂等。
- [x] B4：建立账号 Topic、sequence、断线重放、HTTP 最终对账和 legacy 薄转发。
- [x] 同步 `docs/api/v1/`、错误码、事件和调用说明。
- [x] 完成 P0-B 阶段验收：41 个定向测试文件 `239 passed, 1 skipped in 171.75s`；391 个 Python 文件编译、16 个核心模块导入、18 个迁移 revision、13 个 HTTP + 1 个 WebSocket 文档库存、差异和 UTF-8 门禁通过。

验收前收口运行曾发现 4 个迁移契约问题（`235 passed, 1 skipped, 4 failed`）；修复快照降级断言顺序、0018 严格约束夹具和 SQLite 跨 revision 降级预检后，最终阶段验收通过。该失败记录保留为真实验收证据，不计为阶段完成。

回退点：v1 尚未被正式 Desktop 使用；可恢复上一 Runtime 构建，新表保持加法状态。

### P0-C：账号纵向链

- [x] C0：已收口知识来源 DTO、普通写幂等、分页配置、HTTP / WebSocket 修订边界、AI 接缝和真实执行对象边界。
- [x] 迁移账号状态为 `draft / unbound / ready / attention / archived`，移除新写入的 `active` 兼容。
- [x] 实现创建草稿、真实连接诊断、配置复制白名单、归档和恢复健康复检。
- [x] 落地定位、知识库、BrandKit 和发布默认值基础对象。
- [x] 强制服务、仓储、缓存、文件、任务、日志和事件的账号范围。
- [x] 账号与知识接口文档、静态门禁与 P0-C 阶段验收已完成：最后一次完整运行 `169 passed, 6 failed in 123.31s`，剩余 6 项为幂等重放断言错误，修正后定向复验 `6 passed in 23.52s`；175 项阶段范围均取得通过证据。

验收收口过程中修复了 SQLite 跨表触发器重建顺序、Windows IANA 时区依赖、测试 Runtime Session、真实工作区落库顺序和账号作用域 ContextVar 生命周期。最后 169 项通过后只修改测试断言并复验剩余 6 项，没有再次运行已通过范围。

回退点：新账号对象保持加法；P0-F 正式发布前不开放新写门。非生产旧 Desktop 只保留账号读取过渡，旧账号写入明确返回 410；若必须恢复旧写入，只能整体恢复上一兼容 Runtime 构建，不能双写两套状态机。

### P0-D：Desktop 账号上下文

- [x] D0：已对齐 `docs/ARCHITECTURE-BOOTSTRAP.md` 的 P0-D 目录与页面落点，冻结受控新壳构建边界。
- [x] 拆分 Runtime Client / Types，迁移 Bootstrap、账号、定位知识、配置、任务和事件调用。
- [x] 实现 `AccountContextStore`、未保存守卫、迟到响应隔离、账号切换器和最近页面恢复。
- [x] 落地账号管理、六步向导、定位知识 P0 页面和宽屏 / 紧凑 PC 壳层。
- [x] 新 Route Manifest 只在测试与受控构建启用，不向用户提供双壳开关。
- [x] 开发完成后执行一次 P0-D 阶段测试：Runtime 38 项、Desktop 50 项均取得通过证据；P0-D 路径类型错误为 0，受控构建与真实 Runtime E2E 通过。全仓 79 个冻结 legacy 类型错误保留至 P0-F 收口。

回退点：发布前恢复上一 Desktop 构建；Runtime 和数据库保持兼容。

### P0-E：AI 配置纵向链

- [x] 实现 Provider、Model、Capability、Prompt、Composition Template、Capability Route 与 Account Recipe。
- [x] 实现安全凭据引用、能力契约验证、配置修订、继承、版本和未保存守卫。
- [x] 迁移 AI 系统页面和客户端；旧 AI 配置只保留只读映射。
- [x] 同步 AI 接口文档和安全边界，并完成一次 P0-E 阶段门禁：Runtime 71 项、Desktop 41 项均取得通过证据；Provider / Route DTO 修正后额外 14 项 Desktop 回归通过，`build:p0` 处理 530 个模块并通过，P0-E 新路径类型错误为 0。

阶段门禁首次暴露 6 个 Runtime 边界和 3 个 Desktop 状态映射问题；修复后只定向复验失败范围。全仓仍有 79 个已冻结 legacy 类型错误，继续由 P0-F 正式切换收口，不表述为全量类型检查通过。113 个 P0-E 文件通过 UTF-8、无 BOM 与单文件不超过 500 行门禁。

回退点：未验证的新 AI 对象不得成为默认路由；恢复旧只读配置视图时不得复制明文密钥。

### P0-F：路由切换、桌面打包与 P0 验收

- [x] 打包 Runtime sidecar，增加 Supervisor、单实例、动态端口、生产数据目录和退出清理。
- [x] 正式切换 13 Route ID 与十个账号级入口。
- [x] 从主导航解除旧剪辑、独立配音、字幕、渲染和自动化入口；旧 URL 只做一次性重定向。
- [x] 验证无账号、切换中、账号失效、Runtime 离线、AI 未就绪和数据库维护状态。
- [x] 完成写门、回退 Runtime 制品兼容、旧库升级和失败恢复证据。
  - [x] 写门前启动恢复由独立协调器接管：仅迁移实际变更且 durable journal 未记录 `write_gate_opened` 时自动恢复；恢复前先停止后台并释放 Engine，恢复后核对迁移前指纹。
- [x] 执行一次 P0-F 阶段测试、浏览器 E2E、Tauri / Rust、安装包与视觉验收。

完成证据：Desktop `107 passed`、全局类型检查、239 模块生产构建、真实 Runtime E2E `7 passed`、Rust `17 passed`、受限 `PATH` Sidecar smoke、NSIS 安装包 smoke 和三组 PC 视觉基线均通过。Sidecar build ID 为 `0.4.7-x86_64-pc-windows-msvc-d7538489342f`；本地 file 知识来源桥未伪实现，已明确转入 P1。

回退点：写门开放后只能恢复兼容当前 Schema 的 Desktop / Runtime 制品；强制恢复必须先生成增量恢复与核对报告。

### P0 最终验收

- [x] P0-A 至 P0-F 全部完成后，执行一次 P0 全量自动化测试、构建、E2E、Tauri / 安装包和视觉验收。
- [x] 执行 `git diff --check`、编码、接口库存和文本级真源一致性检查。
- [x] 保存真实验收证据，不把开发种子数据或交互原型当作生产通过证据。

## 8. 必须验证的主链与异常链

1. 首次启动 → 许可证无效 → 激活 → 初始化目录 → Runtime 自检 → 进入账号选择。
2. 无账号 → 创建草稿 → 真实连接未完成 → 进入 `unbound` → 完成连接诊断 → 进入 `ready`。
3. 账号 A 打开未保存 AI Recipe → 切换账号 B → 保存 / 放弃 / 取消三条路径均正确。
4. 切换账号时账号 A 请求延迟返回 → 不得写入账号 B 页面、缓存和任务视图。
5. 切换失败 → 保留账号 A → 展示中文错误、`log_id`、重试和日志入口。
6. 添加 Provider → 凭据引用 → 连接测试失败 / 成功 → 模型发现或手动录入 → 保存。
7. 模型宣称能力但适配器未接入或契约未验证 → 不得成为默认 Capability Route。
8. 新建 Prompt Profile → 变量 / Schema 校验 → 保存新版本 → 绑定能力路由 → 查看引用。
9. 账号 Recipe 继承系统路由 → 允许字段覆盖 → 配置修订广播 → 账号就绪摘要刷新。
10. Runtime 离线、Provider 超时、WebSocket 断开、迁移失败和安全存储不可用时，均有可见恢复路径。
11. 归档当前账号 → 工作区退出到账号选择；恢复后重新执行连接、工作区、知识库和 Provider 健康检查。
12. 旧剪辑工作台 URL → 不进入旧业务页面；按兼容规则重定向或显示迁移说明。

## 9. 风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 旧代码已经覆盖较多业务，直接换壳导致回归范围过大 | 高 | 先建立差异矩阵和基线测试，按 Runtime、账号、AI、路由四个可回退阶段迁移 |
| 旧接口与 `/api/v1` 长期双轨 | 高 | 旧接口只允许薄转发，规格记录截止条件，新增能力只进入 v1 |
| 账号字段补齐不彻底造成跨账号泄漏 | 高 | API dependency、服务、仓储、缓存、任务、日志、文件和 WS 同时强制 account scope |
| AI 凭据和 Prompt 被日志或前端状态泄漏 | 高 | 安全存储引用、脱敏日志、契约测试和负向测试共同约束 |
| 删除旧剪辑模型导致历史项目不可恢复 | 高 | 本阶段只解除主导航引用，不物理删除；后续另立数据迁移与删除计划 |
| 大文件继续膨胀 | 中 | Runtime 客户端、类型、服务和页面按领域拆分，设置文件大小和职责审查门槛 |
| 开发种子数据掩盖空态或连接问题 | 中 | 生产默认中性空态；种子数据仅在显式开发开关和测试数据库使用 |
| Tauri 与浏览器模式行为不同 | 中 | 浏览器验证交互，Tauri 验证子进程、目录、安全存储和断网恢复 |

## 10. 回退与数据安全原则

1. 每个 Alembic migration 必须具备可验证的 `upgrade` / `downgrade` 或明确不可逆理由与备份步骤。
2. 首轮迁移优先新增表和字段，稳定后再进入删除计划。
3. 旧接口兼容层不得写第二份业务数据，只调用新服务。
4. 账号切换失败、AI 配置保存失败或健康检查失败均不得提交半成品事务。
5. 归档不删除内容、知识来源、任务日志和发布记录。
6. 所有实现提交按阶段保持可回退，不与当前未提交原型和文档成果混合覆盖。

## 11. 验收清单

- [x] 原型已冻结为交互基线，生产页面不复制演示数据。
- [x] 新 13 Route ID 和账号级工作区壳生效。
- [x] 已砍掉的剪辑工作台与旧独立工具不再进入主导航。
- [x] 许可证、目录和 Runtime 健康走真实链路。
- [x] 账号状态机、切换事务、连接诊断、复制、归档和恢复可用。
- [x] 定位与知识库基础对象按账号隔离。
- [x] Provider、模型、能力、Prompt、路由和账号 Recipe 可真实配置并可追溯。
- [x] `/api/v1`、统一信封、错误码、日志 ID 和账号 WebSocket 主题生效。
- [x] `docs/api/v1/` 成为唯一接口文档，包含地址、方法、参数、返回、错误码和示例。
- [x] Desktop 与 Runtime 大文件按领域拆分，没有继续形成单文件集中实现。
- [x] 加载、空、正常、错误、取消、重试和受限状态有可见反馈。
- [x] Light / Dark、宽屏 / 紧凑 PC、浏览器 / Tauri 主链验证通过。
- [x] 相关测试、主链回归、迁移验证、构建和 `git diff --check` 通过。

## 12. 后续阶段

P0 验收通过后，下一份独立计划再进入 P1 第一条创作纵向链：

```text
新建 ContentItem 选题
→ 生成并采用 ScriptVersion
→ 生成并确认 StoryboardVersion
→ 创建单条 ProductionBatch
→ 生成内容归档到账号内容库
```

视频拆解回流、固定脚本 / 已有素材输入、完整批量生产、媒体工具和发布复盘在此基础上分批接入，避免同时迁移全部旧业务造成不可控回归。
