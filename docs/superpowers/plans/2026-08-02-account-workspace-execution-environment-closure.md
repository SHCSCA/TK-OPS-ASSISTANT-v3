# P0-G 账号工作区与执行环境生产闭环计划

> 日期：2026-08-02
> 状态：计划与规格均已批准，G0-G2 已完成，G3 实施中
> 类型：多文件、跨 Desktop / Tauri / Runtime / 测试 / 制品的生产闭环
> 审计真源：`docs/audits/2026-08-02-production-chain-closure-audit.md`
> 产品边界：Windows PC、本地优先、账号级工作区、用户监督的 TikTok 登录

## 1. 本计划解决什么

P0-G 只负责建立可信的“账号执行基础”，使全新用户不依赖测试 seed、手工写库或旧设备接口即可完成：

```text
可复现首启
→ 账号创建
→ 选择受控工作目录
→ 创建真实 DeviceWorkspace / BrowserInstance / ExecutionBinding
→ 启动受控浏览器
→ 用户监督登录 TikTok
→ Runtime 验证会话与连接健康
→ 切换账号、重启应用后仍保持正确隔离与恢复
```

本计划不实现 AI 真实生成、知识文件消费、选题/脚本/分镜/拆解、批量生产、内容库、媒体工具、发布和复盘。这些分别归属 P0-H 与 P0-I，禁止借 P0-G 扩页或写假业务结果。

## 2. 成功定义

1. 全新数据目录、正式 production mode、无 seed 的当前制品可以走完上述链路。
2. 所有账号级执行对象显式携带同一 `account_id`，候选和绑定均在事务内重验资格。
3. 工作目录由原生选择器生成受控引用；页面和 API 不直接持有任意绝对路径。
4. 浏览器进程具有可持久验证的所有权证据；Runtime 重启后不能误杀无关进程。
5. TikTok 登录只由用户在可见浏览器内完成；系统只探测会话，不绕过验证码、DRM、风控或访问控制。
6. Sidecar 重启、目录失效、会话过期、任务失败均有中文反馈、日志、重试/取消和恢复路径。
7. 1440×900 与 1180×760 两档 PC 窗口中，账号切换器和向导无裁切、闪烁或页面级横向滚动。
8. 当前 installer / 免安装包由仓库内脚本可复现，manifest 绑定 Git、配置、测试结果和 SHA256。

## 3. 范围边界

### 纳入

- G0 验收真源和无 seed E2E。
- G1 账号壳、切换器、紧凑窗口。
- G2 账号 DeviceWorkspace 的受控目录引用。
- G3 执行环境 provisioning、候选资格、进程所有权。
- G4 账号连接、监督登录、会话状态和跨页 action。
- G5 Runtime Supervisor 恢复、启动前诊断、机器码稳定性。
- G6 长任务、事务、事件、归档清理和兼容收口。
- G7 可复现制品和真实可见 GUI 验收。

### 不纳入

- 不把 Runtime 全局数据根与账号工作目录合并。全局数据根迁移只允许启动前工具处理。
- 不实现云手机、群控、指纹伪装、验证码绕过、批量养号或规避 TikTok 风控。
- 不复活旧设备管理页，不扩展 legacy `/api/devices/*` 写能力。
- 不让 Vue 组件直接 fetch、直接写数据库、直接启动进程或保存绝对路径。
- 不把测试 helper、静态地址、假候选、假登录状态当验收证据。
- 不处理 P0-H / P0-I 的 AI 与创作能力。

## 4. 先锁定的核心契约

规格文件固定为：

`docs/superpowers/specs/2026-08-02-account-workspace-execution-environment-closure-design.md`

规格获批前不修改生产代码。规格至少锁定以下契约。

### 4.1 对象和不变量

```text
Account
  └─ DeviceWorkspace(account_id, root_ref, state)
       └─ BrowserInstance(account_id, workspace_id, profile_ref, state)
            └─ ExecutionBinding(account_id, workspace_id, browser_instance_id, state)
                 └─ AccountConnection(auth_state, session_ref, health_state)
```

- 三个执行对象和连接必须属于同一账号。
- 跨账号复用只能显式复制，不能认领或静默重写所有权。
- `session_ref` / `credential_ref` 只能指向安全存储，不返回 cookie、token 或明文凭据。
- 绑定 eligibility 是服务层唯一规则；候选查询和绑定命令都调用它，绑定事务内必须重验。

### 4.2 状态机

执行环境：

```text
draft → provisioning → stopped → starting → ready
                   ↘ failed       ↘ unhealthy
ready → stopping → stopped
任意状态 → deleting → deleted / cleanup_failed
```

TikTok 会话：

```text
unknown → login_required → login_in_progress → probing → valid
                                  ↘ cancelled   ↘ invalid
valid → expiring / expired / revoked → login_required
```

任何长动作返回 `task_id`，必须具备 queued/running/succeeded/failed/cancelled/timed_out 终态、`log_id`、进度、可取消性和重试策略。

### 4.3 受控目录引用

- Tauri 打开 Windows 原生目录选择器并在 Rust 层规范化。
- Rust 通过统一配置总线注册引用，只向 UI 返回 `rootRef` 与脱敏 `displayPath`。
- Runtime resolver 校验存在性、可写性、危险根目录、重解析点、账号所有权和引用失效。
- 默认 Profile 和任务输出置于账号工作区；不开放 `$HOME/**`、`$DOCUMENT/**` 等宽泛 asset scope。
- portable 包迁移、目录丢失和重新授权必须有明确状态，不猜测新路径。

### 4.4 进程所有权

浏览器启动记录至少包含：实例 ID、可执行文件规范路径、Profile 规范路径、PID、进程创建时间、启动 nonce、调试端口、Runtime generation。停止前逐项核验；证据不足标记 orphaned，只提示人工处理，不执行 `os.kill`。

### 4.5 生产 API 草案

最终字段、错误码和示例由规格及唯一 API 文档确定，资源边界预期为：

- `GET /api/v1/accounts/{account_id}/execution-environments`
- `POST /api/v1/accounts/{account_id}/execution-environments`
- `GET /api/v1/accounts/{account_id}/execution-environments/{environment_id}`
- `POST /api/v1/accounts/{account_id}/execution-environments/{environment_id}/start`
- `POST /api/v1/accounts/{account_id}/execution-environments/{environment_id}/stop`
- `POST /api/v1/accounts/{account_id}/execution-environments/{environment_id}/checks`
- `DELETE /api/v1/accounts/{account_id}/execution-environments/{environment_id}`
- `POST /api/v1/accounts/{account_id}/connection/login-sessions`
- `GET /api/v1/accounts/{account_id}/connection/login-sessions/{session_id}`
- `POST /api/v1/accounts/{account_id}/connection/login-sessions/{session_id}/probe`
- `DELETE /api/v1/accounts/{account_id}/connection/session`
- 继续保留 `GET /connection/candidates`、`PUT /connection/binding`、`DELETE /connection/binding`

所有响应使用 `{ "ok": true, "data": ... }` / `{ "ok": false, "error": ... }`，错误带稳定 `error_code`、中文 `error`、可选 `log_id`、`retryable` 和结构化 `recovery_action`。

## 5. 分阶段实施

### G0：恢复验收真源

**目标**：先阻止假绿，再改功能。

**改动**：

- 修正首启 E2E 的只读机器码交互和测试密钥对装配；Issuer 与 Runtime 公钥必须同源。
- 将生产 E2E 中 `seedExecutionBinding` 标为禁止前置；仓储测试可继续使用专用夹具。
- 建立 active / compatibility / retired 测试清单，默认门禁执行 active 测试并禁止意外 Vue Router warning。
- 校准 `tauri-capabilities.spec.ts` 到当前最小权限契约，不扩大文件协议 scope。
- 生成 build manifest：Git commit/worktree 状态、版本、配置摘要、测试证据、sidecar/installer/portable SHA256。
- 历史 P0-F 记录保留并标记 stale snapshot，不篡改历史数字。

**主要文件**：Desktop test scripts/E2E support、license issuer test setup、测试清单、构建 manifest 脚本、项目状态文档。

**阶段验收**：全新目录运行首启 E2E 到“无候选”真实空态；无数据库 seed；默认门禁包含所有 active 测试；当前 manifest 可追溯。

**回退点**：只回退门禁编排和证据生成，不回退当前许可证安全契约。

### G1：账号壳和切换器

**目标**：解决用户已复现的裁切和页面溢出。

**改动**：

- 统一 reset、`box-sizing`、壳层高度和滚动容器，消除 `100vw` 引发的横向滚动。
- 账号菜单使用受控宽度、视口碰撞检测和明确层级；必要时 Teleport 到 overlay root。
- 统一打开、搜索、空态、切换、添加、管理、关闭和失败反馈。
- Desktop 宽屏与紧凑窗口同时覆盖 Light / Dark。

**主要文件**：`layouts/account-workspace/`、全局 styles、AccountSwitcher 组件与相关 P0/E2E 测试。

**阶段验收**：两档窗口打开菜单后 `scrollWidth === clientWidth`，菜单四边在视口内，触发器不被覆盖；截图人工复核。

**回退点**：样式和 overlay 可独立回退，不触碰数据。

### G2：受控账号工作目录

**目标**：让用户选择真实账号工作目录，同时明确它不是 Runtime 全局数据根。

**改动**：

- 新增 Tauri workspace-root 模块，拆分 picker、规范化、注册、撤销和错误映射。
- Runtime 通过统一配置总线装配 resolver；UI 只提交 `rootRef`。
- 实现可写、危险根、重解析点、引用过期、目录缺失、账号冲突和重授权处理。
- 系统设置只读展示 Runtime 全局数据根；账号详情/向导管理 DeviceWorkspace 目录。
- 不在 Runtime 已启动后“热迁移” DB/data_dir；全局数据根迁移另立启动前工具。

**主要文件**：Tauri `workspace_roots/`、capability 最小权限、Desktop bridge/client、Runtime config/resolver、bootstrap/API 文档。

**阶段验收**：原生选择成功/取消/无权限/越界/重解析点/失效/重启恢复测试通过；日志不泄露完整敏感路径。

**回退点**：关闭新建动作，既有 rootRef 保持只读可诊断；不移动或删除用户文件。

### G3：执行环境 provisioning、资格与进程所有权

**目标**：正式 API 从零创建真实三对象，并安全管理受控浏览器。

**改动**：

- 新增账号作用域 execution-environments schema、route、service、repository 和 migration。
- 单一事务创建三对象，目录/Profile/进程副作用使用 outbox 或补偿；支持幂等键、超时和取消。
- 建立唯一 eligibility service；候选列表和绑定事务内重检 workspace、browser、binding、进程和账号关系。
- 浏览器发现只支持本机明确安装的 Chrome/Edge；记录持久 process ownership proof。
- 修复或隔离 legacy 字段错位；不猜测历史关系，不继续开放旧写接口。

**主要文件**：Runtime v1 execution environment 模块、browser runtime、account connection query/service、Alembic、领域客户端和 API 文档。

**阶段验收**：无 seed 的 UI/API 创建；跨账号拒绝；并发幂等；失败注入回滚；Runtime 重启后所有权验证；PID 复用不误杀。

**回退点**：feature flag 关闭新写路由，保留 migration 与只读数据；未知进程只标 orphaned。

### G4：向导、监督登录和 typed action router

**目标**：用户在正式 UI 走完连接链，并保证跨页动作落到正确账号。

**改动**：

- 向导连接步骤加入“新建执行环境”，成功后刷新、自动选择并绑定；失败保留草稿。
- 在可见受控浏览器中启动监督登录；Runtime 探测 TikTok 会话，保存安全 `session_ref`，处理过期/撤销/重登/登出。
- 禁止自动输入用户凭据、绕过验证码或把 cookies 返回 UI。
- 建立 typed action contract：`action`、`accountId`、`route`、`wizardStep`、`taskId`、`logId`、`returnTo`。
- 工作台、账号管理、知识页和健康问题统一解析；切换目标账号失败必须可见。
- 补齐账号可编辑身份字段，统一 optimistic revision 与错误反馈。

**主要文件**：账号向导/详情、workspace home action builder、router/composable、Runtime login session service、连接健康、API 文档。

**阶段验收**：新账号从空态到 valid；取消登录、会话过期、跨账号深链、修复后返回、重启恢复和登出 E2E；无敏感信息泄漏。

**回退点**：登录失败降为 `login_required`，保留执行环境和账号草稿；typed router 对未知动作 fail-closed。

### G5：Runtime Supervisor、启动前诊断和机器码韧性

**目标**：Runtime 起不来或重启时，用户仍可诊断并自动恢复连接。

**改动**：

- Desktop 订阅 supervisor generation/status；端口/token 变化时失效单例连接、缓存和在途请求，按退避重连。
- BootstrapErrorScreen 可读取 supervisor 日志摘要、复制诊断、导出脱敏诊断包。
- 机器码采集对注册表/CIM/卷序列做分项异常记录和稳定降级；算法版本化并兼容已有许可证。
- 通过配置总线管理重启次数、退避和超时，杜绝硬编码旁路。

**主要文件**：Tauri runtime supervisor、Desktop connection/bootstrap error、Runtime machine code、配置 schema/consumer、诊断文档与测试。

**阶段验收**：Sidecar 崩溃后新端口/token 自动恢复；断开期间操作可见失败并可重试；受限 Windows 矩阵机器码稳定；旧许可证不失效。

**回退点**：关闭自动恢复则回到显式“重启 Runtime”，但保留诊断导出；机器码始终兼容旧版本。

### G6：任务生命周期、事务、事件和归档清理

**目标**：所有执行环境长动作可追踪、可取消、可恢复，数据库与外部副作用一致。

**改动**：

- 统一 task projection、WebSocket topic、轮询 fallback、取消、超时、重试和 `log_id`。
- Desktop 全局任务状态与账号缓存同步失效；离开/重启页面后可恢复在途任务。
- provisioning、检查、登录 probe、停止、删除和归档使用明确事务/outbox/补偿。
- 账号归档前停止受控进程、撤销会话、取消环境任务；失败返回可恢复状态。
- legacy 接口仅兼容读取，写请求返回稳定迁移提示。

**主要文件**：Runtime task/event/transaction 模块、account commands、Desktop task store/feedback、WebSocket adapter、兼容矩阵。

**阶段验收**：每类任务覆盖 queued 到全部终态；断网/重启恢复；故障注入无半对象；归档后无活跃受控进程/会话/任务。

**回退点**：WebSocket 可降级轮询；补偿失败保留 cleanup_failed 和审计记录，绝不静默删除。

### G7：可复现制品与真实桌面验收

**目标**：交付的 EXE/ZIP 与通过验收的代码和证据一一对应。

**改动**：

- 仓库脚本统一构建 Runtime sidecar、Tauri installer 和免安装运行包；说明后者是否数据便携。
- manifest 写入版本、Git 状态、构建参数、签名/公钥指纹、所有制品大小和 SHA256。
- Windows smoke 以可见窗口验证：WebView 渲染、许可证激活、Runtime ready、标准最小化/最大化/关闭、单实例聚焦、优雅 WM_CLOSE、重启恢复。
- 干净数据目录完成“许可证 → 新账号 → 新工作区 → 浏览器 → 登录 → valid”。
- 失败制品不覆盖 current；上一版保留为回退。

**主要文件**：packaging scripts、Tauri config、Windows GUI smoke、发布清单和状态文档。

**阶段验收**：在至少一台干净 Windows 测试机复现构建和全链；人工截图/日志/manifest/哈希齐全；强制 kill 不算正常关闭通过。

**回退点**：current 指针回退上一版；数据 migration 必须有 backup/downgrade 方案，不用破坏性覆盖。

## 6. 文件地图与拆分边界

### Desktop

- `src/layouts/account-workspace/`：壳层和切换器，不放业务服务。
- `src/modules/execution-environments/`：types、client adapter、store/composable、components、styles 分拆。
- `src/modules/accounts/`：向导、账号详情和登录状态展示。
- `src/app/runtime-client/`：唯一 HTTP/WebSocket 入口。
- `src/app/actions/`：typed action schema、parser、router、return context。
- `src/app/runtime-supervisor/`：连接 generation 和恢复，不散落到页面。

### Tauri

- `src/workspace_roots/`：目录选择/引用。
- `src/runtime_supervisor/`：sidecar 生命周期和诊断。
- `main.rs` 只装配命令；禁止形成新大文件。

### Runtime

- `api/routes/v1/execution_environments.py` 与 `schemas/v1/execution_environments.py`。
- `services/execution_environments/`：provisioning、eligibility、process ownership、cleanup。
- `services/accounts/`：connection/login session/readiness/commands。
- 仓储、任务、事件、配置分别保持现有统一边界。

### 文档与测试

- 唯一 API 文档必须包含地址、方法、参数、响应、错误码和示例。
- Runtime 纵向集成、Desktop 状态、Tauri 单元、Playwright 主链、Windows GUI smoke 各自负责一层，不互相伪造。

## 7. 每阶段通用完成条件

1. 只修改该阶段已批准规格内的文件；超范围先更新 plan/spec。
2. 新增注释仅用简洁中文；所有异常记录统一日志并转中文 UI 反馈。
3. UI 覆盖 loading / empty / normal / error / cancelling / retrying；长任务还覆盖超时和恢复。
4. 数据请求只走 Runtime 适配层；配置只走全局配置总线。
5. Light / Dark、1440×900、1180×760 全覆盖。
6. 阶段相关测试 + 一条账号主链回归通过；G7 再跑 P0 全量、构建、E2E、Tauri、制品与视觉验收。
7. API 文档与调用文档同步更新，不以测试 helper 代替生产契约。

## 8. 批准门

- **计划批准记录**：用户于 2026-08-02 明确回复“同意执行”，P0-G 计划获批。
- **规格批准记录**：用户在 2026-08-02 的验收退回结论中明确要求纠正规格批准状态并按 G0 → G7 实施。
- **当前阶段**：规格已批准，从 G0 验收真源开始实施；每阶段集中验收并设置回退点。
- P0-H 和 P0-I 必须另行计划/规格批准，不随 P0-G 自动获得开发授权。
