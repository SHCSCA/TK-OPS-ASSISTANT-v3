# TK-OPS 生产链闭环审计

> 日期：2026-08-02
> 状态：审计完成，P0-G 计划已批准并进入规格审批
> 审计方式：只读代码、测试、文档和制品证据核验；审计阶段未修改生产代码、测试、配置或制品
> 审计范围：十三个正式 Route、八条生产链、Windows 免安装桌面应用

## 1. 结论

当前项目已经具备可运行的 P0 桌面壳、许可证、账号、AI 配置和部分 Runtime 基础，但还不能认定为“生产链闭环”。关键原因不是页面数量不足，而是存在三类断层：

1. 用户从 UI 不能创建真实执行环境、完成 TikTok 登录并形成可验证的账号连接；现有 E2E 通过直接写数据库绕过该断点。
2. v1 Provider / Model / Route / Prompt / Recipe 配置与真实 AI 生成服务仍是两套系统，八个创作和生产页面仍明确处于 pending。
3. 默认测试门禁、首启 E2E 和当前发布制品证据已经漂移，历史 P0-F 结论只能视为当时快照，不能继续证明当前提交可交付。

本次确认 24 个去重问题：S0 7 项、S1 14 项、S2 3 项。每个 S0/S1 只归属一个整改阶段，避免多阶段重复修补。整改顺序固定为：先恢复验收可信度，再闭合账号执行基础，之后接通 AI 配置与真实执行，最后实现八个账号级创作/生产页面。

## 2. 本次实际基线

| 检查 | 实际结果 | 判断 |
| --- | --- | --- |
| `git status --short --branch` | `main...origin/main`，283 条既有状态 | 工作树很脏；本审计不得归并或清理用户改动 |
| Route 静态统计 | 13 个正式 Route；8 个 pending；14 个 legacy redirect | 页面树存在不等于能力可用 |
| Runtime 测试静态统计 | 132 个 Python 测试文件；769 个 `test_` 函数 | 本轮未执行 Runtime 全量测试，不宣称通过 |
| `npm --prefix apps/desktop run test` | 24 files / 111 tests passed | 默认门禁只覆盖 `tests/p0`，并持续输出未匹配路由警告 |
| `npm --prefix apps/desktop run typecheck` | 通过 | 仅证明类型检查通过 |
| 真实首启 E2E | 退出 1，webServer 启动前因许可证签发密钥与 Runtime 验签公钥不匹配而失败 | 当前无法证明首启主链 |
| `npx vitest run tests/tauri-capabilities.spec.ts` | 3 tests：2 passed / 1 failed | 默认门禁外已有安全契约测试漂移 |

## 3. 严重度与“生产可达”定义

- **S0**：阻断首次使用、核心生产链或发布可信度；普通用户必然或高概率遇到。
- **S1**：关键恢复、安全、隔离或一致性缺陷；会导致错误绑定、不可恢复、错误杀进程或静默失效。
- **S2**：不立即阻断主链，但造成管理死角、假绿或产品边界不清。
- **S3**：轻微体验或文案问题；本次未单列。
- **生产可达**：正式 Route、正式 Runtime 路由和当前桌面制品可触达；仅测试 helper、直接写库、旧路由或手工调试可达不算闭环。

## 4. 十三个正式 Route 核验

Route 真源为 `apps/desktop/src/app/router/p0-route-manifest.ts`。`ready` 只表示路由已有正式页面，不代表下游链路全部可用。

| # | Route | 当前状态 | 生产边界与主要断点 | 后续阶段 |
| --- | --- | --- | --- | --- |
| 1 | 首启与许可证向导 | ready 但当前 E2E 失败 | 机器码只读设计正确；签发环境未与 Runtime 公钥对齐 | G0、G5、G7 |
| 2 | 工作台 | P0 foundation | 建议动作缺少统一上下文；失败任务不可恢复 | G4、G6 |
| 3 | 定位与知识 | P0 foundation | 本地文件桥明确禁用，知识源不能真正导入 | P0-H |
| 4 | 脚本与选题 | P1 pending | `AccountCapabilityPendingPage`，无生产 Runtime 链 | P0-I |
| 5 | 分镜规划 | P1 pending | 同上 | P0-I |
| 6 | 视频拆解 | P1 pending | 同上 | P0-I |
| 7 | 批量生产 | P1 pending | 同上 | P0-I |
| 8 | 内容库 | P1 pending | 同上 | P0-I |
| 9 | 媒体工具箱 | P1 pending | 同上 | P0-I |
| 10 | 发布 | P2 pending | 同上 | P0-I |
| 11 | 复盘 | P2 pending | 同上 | P0-I |
| 12 | 账号管理 | ready 但连接闭环缺失 | 不能从 UI 创建环境、登录 TikTok；身份只读 | G1-G4 |
| 13 | AI 与系统设置 | ready 但配置孤岛 | Provider 不能完整编辑；v1 路由未进入真实生成 | P0-H |

八个 pending 页面由 `AccountCapabilityPendingPage.vue:46-49` 明确提示尚未连接生产 Runtime；`p0-router-bootstrap.spec.ts:132-135` 和 `account-capability-pending.spec.ts:12-13` 还把该状态固定为测试预期。因此它们是已知阶段边界，不应被历史“页面已完成”表述掩盖。

## 5. 八条生产链核验

| 生产链 | 用户期望 | 当前真实状态 | 结论 |
| --- | --- | --- | --- |
| 许可证 / 机器码 / Issuer | 打开应用自动生成稳定机器码，合法密钥可激活 | UI 已只读显示机器码，但 E2E 仍填写旧字段；临时私钥未配套 Runtime 公钥 | 阻断，G0 |
| Runtime 启动 / 目录 | Sidecar 自动启动、可恢复；全局数据根和账号目录清晰 | `workspaceRootRef` 无 resolver；重启后连接缓存可能持有旧端口/token | 未闭环，G2/G5 |
| 账号创建 / 切换 / 深链 | 创建、切换、恢复动作始终落在目标账号 | 普通切换有反馈，深链选择失败只记日志；action 参数不完整 | 未闭环，G1/G4 |
| 工作区 / 浏览器 / Binding / TikTok 授权 | UI 创建真实对象、启动受控浏览器、登录并验证会话 | 正式 API 只有候选与绑定；无 provisioning、无登录会话状态机 | 核心阻断，G2-G4 |
| 知识文件引用 | 选择视频/文档/图片并形成受控引用 | UI 明确禁用，本地文件桥 fail-closed | 未实现，P0-H |
| AI 配置到真实执行 | 配置 Provider/模型/路由/提示词后，生产任务按快照调用 | v1 配置与 legacy `AICapabilityService` 两套装配，暂无真实闭环 | 核心阻断，P0-H |
| 长任务生命周期 | 可查看进度、取消、重试、日志和恢复 | 多处仅保存 taskId 或要求手动刷新，失败动作缺 log/retry 上下文 | 未闭环，G6 |
| Tauri / 窗口 / portable | 当前制品可复现构建并完成可见 GUI 首启、重启与关闭 | 当前哈希与历史文档不符；smoke 不验证可见 WebView/标准按钮/激活主链 | 证据不足，G7 |

## 6. 已确认问题

### S0-01 许可证首启 E2E 已与当前机器码和验签契约脱节

- **用户路径 / 预期**：启动免安装 EXE → 自动读取机器码 → 输入由匹配 Issuer 签发的密钥 → 激活。
- **实际 / 根因**：`apps/desktop/tests/e2e/account-workspace.e2e.ts:35` 仍填写“完整机器码”，而 `P0SetupLicenseWizardPage.vue:58-85` 已改为只读复制；`tests/e2e/support/e2e-environment.mjs:61-75` 生成临时私钥时未传对应 Runtime 公钥，`apps/py-runtime/tools/license-issuer/issue_license.py:85-100,177-188` 会拒绝不匹配密钥。
- **生产可达**：是。当前首启验收在页面启动前失败，不能证明现有制品可激活。
- **假绿原因**：默认 Desktop 单测不运行真实 Issuer + Sidecar + WebView 首启。
- **整改归属 / 依赖 / 回退**：**G0**。先锁定测试密钥对与只读机器码契约；失败即回退到最近一次可复现的验收基线，不改许可证安全规则。

### S0-02 E2E 直接写数据库伪造执行环境

- **用户路径 / 预期**：新账号在向导中创建工作区、浏览器实例和执行绑定。
- **实际 / 根因**：`apps/desktop/tests/e2e/support/p0-main-chain.ts:63` 调用 `seedExecutionBinding`；`seed-execution-binding.py:53-144` 直接插入三类对象，绕过正式 UI、API、目录、进程和健康检查。
- **生产可达**：普通用户不可达；测试专用后门可达，正是生产断点。
- **假绿原因**：测试预先构造了用户无法创建的候选；`account-management-ui.spec.ts:67-87` 还把“没有可绑定环境”的死路固定为正确空态。
- **整改归属 / 依赖 / 回退**：**G0**。生产验收禁止 seed；测试 helper 可保留为仓储单测夹具，但不得作为 E2E 前置。

### S0-03 正式 Runtime 没有执行环境 provisioning 能力

- **用户路径 / 预期**：账号向导“连接”步骤点击新建，真实创建 `DeviceWorkspace → BrowserInstance → ExecutionBinding`。
- **实际 / 根因**：`api/routes/v1/account_connection.py:29-81` 只有读取、候选、绑定、解绑和检查；`WizardConnectionStep.vue:32` 只显示“没有可绑定的执行环境”。旧 `/api/devices/*` 在生产模式不加载（`app/route_registry.py:81-142`），且旧路由已重定向到只读 Runtime 设置（`legacy-redirects.ts:24-27`）。
- **生产可达**：是，任何新账号都会进入死路。
- **假绿原因**：S0-02 的直接写库掩盖缺失 API。
- **整改归属 / 依赖 / 回退**：**G3**，依赖 G2 受控目录引用。写路由可用 feature flag 关闭，保留只读候选与既有数据。

### S0-04 TikTok 登录和会话验证不存在生产状态机

- **用户路径 / 预期**：启动受控浏览器 → 用户监督登录 TikTok → Runtime 探测会话 → 显示已登录、过期、需重登或登出。
- **实际 / 根因**：`services/accounts/connection.py:203-217` 新连接固定 `auth_status="unknown"`；`health_execution.py:138-164` 只消费已有状态，没有生产服务将其变为 `valid`。测试在 `test_p0_c_account_health_consistency.py:669-686` 直接把数据库改成 running/valid。
- **生产可达**：是。用户无法完成向导后续健康验收。
- **假绿原因**：测试用数据库突变代替真实浏览器会话探测。
- **整改归属 / 依赖 / 回退**：**G4**，依赖 G3 真实进程。回退时保留环境对象，连接状态降为需重新登录，不伪装有效。

### S0-05 v1 AI 配置没有驱动真实 AI 执行

- **用户路径 / 预期**：在系统设置配置 Provider、模型、路由、提示词和账号 Recipe，随后真实任务使用该激活快照。
- **实际 / 根因**：`app/container.py:27,105,224,311` 同时装配 legacy `AICapabilityService` 与 v1 配置服务；`ai_text_generation_service.py:14,50` 仍依赖 legacy 服务。v1 测试 `test_p0_e_ai_provider_model_route_chain.py:25-133` 只验证 CRUD/激活，生成测试则用 fake service（`test_ai_text_generation_service.py:48-67,131-150`）。
- **生产可达**：是。用户配置成功不等于任何生产生成会采用它。
- **假绿原因**：配置链和执行链分别测试，没有纵向真实调用。
- **整改归属 / 依赖 / 回退**：**P0-H**。以能力路由快照适配 legacy 消费端，按 provider feature flag 回退，不允许页面直连供应商。

### S0-06 创作主模型缺少账号隔离且八个生产页面仍为占位

- **用户路径 / 预期**：当前账号的选题、脚本、分镜、拆解、批次、内容、发布和复盘全链隔离。
- **实际 / 根因**：`domain/models/project.py:9-21`、`script.py:9-28`、`storyboard.py:9-27`、`ai_job.py:9-26` 未体现固定主链所需 `account_id`；八个正式页面仍为 pending，生产路由也未加载旧创作接口。
- **生产可达**：是。用户只能看到边界提示，不能完成内容生产。
- **假绿原因**：路由存在与 pending UI 测试被误解为功能完成。
- **整改归属 / 依赖 / 回退**：**P0-I**，依赖 P0-H 真实 AI 执行。按单条主链逐页启用，pending 页面作为安全回退。

### S0-07 当前制品与历史 P0-F 发布证据不一致

- **用户路径 / 预期**：拿到文档声明的当前免安装包，可按相同输入复现哈希并完成测试。
- **实际 / 根因**：当前 sidecar SHA256 为 `6838F6E8261532DD85B7AE562C37F0EB27E3DC871B5A9A3FE985AC4153BFEB72`，NSIS 为 `2C32C905F298A8D680850CA0EF837F7809249C35ACFC4A3DD712F73ECFF0E499`，portable ZIP 为 `C9E4F84A4017993CFCF48482B25F9E1D9446FABDC0174776A144EE554CA4321A`；`docs/PROJECT-STATUS.md:180-184` 仍记录旧测试数、旧 sidecar 和旧 NSIS 哈希/大小。
- **生产可达**：是。用户无法确认自己测试的是哪一构建。
- **假绿原因**：发布状态是手工历史快照，没有构建清单与当前 Git/配置/测试证据绑定。
- **整改归属 / 依赖 / 回退**：**G0**。历史记录保留但标注 stale；当前状态只引用机器生成 manifest，不覆盖旧制品。

### S1-08 候选资格和绑定存在 TOCTOU

- **用户路径 / 预期**：只出现属于当前账号、工作区健康、浏览器真实运行且未冲突的候选；绑定时再次验证。
- **实际 / 根因**：`account_connection_v1_queries.py:92-120` 只关联身份，没有过滤工作区/浏览器/进程健康；`services/accounts/connection.py:149-196` 验证 ID 关系但未做最终资格重检。
- **生产可达**：是。陈旧或失效候选可能被绑定。
- **假绿原因**：集成测试 `p0c_account_integration_support.py:61-110` 直接构造完美对象。
- **整改归属 / 依赖 / 回退**：**G3**。统一 eligibility service，绑定事务内重检；失败仅拒绝新绑定，不破坏原绑定。

### S1-09 浏览器进程所有权不足，可能误杀复用 PID

- **用户路径 / 预期**：应用只停止自己为该账号启动、且可证明所有权的浏览器进程。
- **实际 / 根因**：`services/browser_runtime.py:76-127` 所有权只保存在内存；重启后 stop 在 `:180-203` 退化为 `os.kill(process_id, SIGTERM)`，健康检查 `:135-175` 只看 PID/端口，没有核对 exe、Profile、启动令牌和进程创建时间。
- **生产可达**：是，Runtime 重启或 PID 复用后可触发。
- **假绿原因**：单进程短生命周期测试不覆盖 Runtime 重启和 PID 复用。
- **整改归属 / 依赖 / 回退**：**G3**。持久化 process ownership proof；证据不足只标记 orphaned 并提示人工关闭，绝不强杀。

### S1-10 `workspaceRootRef` 是未装配的伪能力，且混淆两类目录

- **用户路径 / 预期**：首启可选 Runtime 全局数据根；账号可另选 DeviceWorkspace 目录，二者生命周期清楚。
- **实际 / 根因**：`schemas/v1/bootstrap.py:92` 接受非空引用，`services/bootstrap_v1/directories.py:90-112` 依赖 resolver，但 container 未注入；`docs/api/v1/bootstrap.md:303-307` 已承认当前只有 null 可用。即使解析成功，启动时 DB/data_dir 已确定，初始化也不会安全搬迁现有数据。
- **生产可达**：是，非空选择会失败或产生误导。
- **假绿原因**：测试只覆盖默认 data dir，没有 prelaunch relocation 与账号目录分层。
- **整改归属 / 依赖 / 回退**：**G2**。G2 只实现账号工作区受控引用；全局数据根若需迁移必须走启动前迁移工具，不能在页面热改。

### S1-11 Sidecar 自动重启后 Desktop 可能继续使用旧连接

- **用户路径 / 预期**：Runtime 崩溃并自动重启后，Desktop 自动获取新端口/token，缓存失效并恢复。
- **实际 / 根因**：`app/runtime-client/connection.ts:32,66-72` 缓存单例 Promise，只在显式操作 `:40-41,56-58` 失效；Rust 在 `runtime_supervisor/mod.rs:36` 发状态事件，但 Desktop 未发现对应订阅。
- **生产可达**：是，任何自动重启后均可能发生。
- **假绿原因**：测试固定连接信息，不模拟监督器重启与 token 轮换。
- **整改归属 / 依赖 / 回退**：**G5**。事件驱动失效并限制重连退避；失败回到可诊断的 Runtime 不可用页。

### S1-12 Runtime 启动前诊断不足，机器码对单项系统能力过度脆弱

- **用户路径 / 预期**：Runtime 起不来时仍能导出 supervisor 日志；注册表/CIM/卷序列某项不可用时机器码采用稳定降级策略。
- **实际 / 根因**：`BootstrapErrorScreen.vue:16,38,46` 只有重启/重检；机器码 `machine_code.py:16-25` 顺序调用注册表、CIM、卷序列，单个 helper 抛错可中断整体（`:36-40,58,82-100`）。
- **生产可达**：是，受限 Windows、CIM 服务异常或 Sidecar 启动失败时发生。
- **假绿原因**：测试验证命令形状/override，没有受限权限、CIM 禁用和跨重启稳定性实机矩阵。
- **整改归属 / 依赖 / 回退**：**G5**。先增加 pre-runtime 诊断导出；机器码算法变化必须带版本兼容，不能使已发许可证失效。

### S1-13 跨页面 action/deep link 缺少统一账号上下文

- **用户路径 / 预期**：从工作台或健康问题跳转修复，目标页选中正确账号、步骤和日志，完成后返回原处。
- **实际 / 根因**：`workspace-home-view.ts:63-79` 只生成 section/taskId；`use-account-management-page.ts:60-83,149-198` 只识别少量 action。知识页 `AccountStrategyKnowledgePage.vue:186-196` 忽略 query account，返回 `:272-283` 又依赖当前 active account；深链账号选择失败在 `use-account-workspace-shell.ts:284-297` 只写日志。
- **生产可达**：是，工作台建议动作和跨账号修复均可触达。
- **假绿原因**：测试只验证单页点击，不验证目标账号、返回路径和失败反馈。
- **整改归属 / 依赖 / 回退**：**G4**。建立 typed action router；未知 action 拒绝执行并提供中文反馈，保留原路由。

### S1-14 长任务只有 taskId，没有完整生命周期

- **用户路径 / 预期**：健康检查、修复、AI、渲染和发布任务可查看进度、取消、重试、日志与恢复。
- **实际 / 根因**：`account-management-store.ts:158-178,206-224` 只保存 pendingTaskIds；`WizardHealthStep.vue:13-33` 要求手动刷新；`use-account-workspace-shell.ts:186-190` 的失败摘要没有 retry/log 上下文。
- **生产可达**：是，当前账号检查任务已触达；后续长任务会放大问题。
- **假绿原因**：`account-management-store.spec.ts:65-93` 只断言请求 accepted，不等待终态。
- **整改归属 / 依赖 / 回退**：**G6**。统一 task projection 与 WebSocket/poll fallback；回退保留任务记录，UI 可降级轮询。

### S1-15 账号切换器存在横向溢出与裁切

- **用户路径 / 预期**：1440×900 和紧凑 PC 窗口中，左下菜单完整可见且不被页面滚动条覆盖。
- **实际 / 根因**：`account-workspace.css:15-16` 使用 `100vw/100vh`，全局 `styles/index.css` 未引入含 reset 的 `shell.css:7-9`；菜单基础宽度位于 `account-switcher.css:92-99`，仅紧凑 override 到 320px（`account-workspace.css:445-449`）。现有截图已显示裁切。
- **生产可达**：是，用户截图已复现。
- **假绿原因**：E2E `account-workspace.e2e.ts:354-386` 只检查 viewport/sidebar，未打开菜单断言 bounding box 与页面 scrollWidth。
- **整改归属 / 依赖 / 回退**：**G1**。仅回退壳层样式即可，不影响数据。

### S1-16 Provider Profile 不能完整编辑或轮换凭据

- **用户路径 / 预期**：新增后能编辑 base URL、凭据引用、超时等并测试生效。
- **实际 / 根因**：`ProviderWorkspace.vue:119-185` 主要是只读、启停、发现和测试；客户端已有 `patchProviderProfile` / `updateProviderCredential`（`runtime-client/ai-system.ts:107-126`），但凭据更新只在新建向导 `use-provider-wizard.ts:102-119` 使用。
- **生产可达**：是，设置页点击管理后无法完成配置维护。
- **假绿原因**：`ai-provider-model-route-store.spec.ts:120-130` 只覆盖 enabled patch。
- **整改归属 / 依赖 / 回退**：**P0-H**。凭据只显示引用/掩码，轮换失败保留旧 credential_ref。

### S1-17 AI Recipe 依赖阻断没有修复导航

- **用户路径 / 预期**：Recipe 校验失败可一键跳到缺失模型/路由/提示词，修复后返回并重新验证。
- **实际 / 根因**：`AccountAIRecipePanel.vue:73-79,126-158` 只列问题、验证和激活；`account-ai-recipe-store.ts:120-130` 标记 `dependency_blocked`，没有结构化 repair action/returnTo。
- **生产可达**：是，配置稍有缺失即进入死路。
- **假绿原因**：测试只验证状态，不覆盖跨页修复闭环。
- **整改归属 / 依赖 / 回退**：**P0-H**。复用 G4 typed action router；未知依赖保持阻断，不允许强行激活。

### S1-18 知识库本地文件导入被永久禁用

- **用户路径 / 预期**：当前账号选择视频、文档、图片并生成受控文件引用和索引任务。
- **实际 / 根因**：`KnowledgeSourcesPanel.vue:33-57` 明示未来 bridge 且按钮 disabled；`account-knowledge-operations.ts:71,125` 主动抛出不可用；`docs/api/v1/account-knowledge.md:20,155,240` 也声明 fail-closed。
- **生产可达**：是，定位与知识页正式可达。
- **假绿原因**：`strategy-knowledge-ui.spec.ts:66` 把禁用状态固定为正确结果。
- **整改归属 / 依赖 / 回退**：**P0-H**，复用 G2 受控引用，不开放 `$HOME/**`；失败保留源文件不写入知识库。

### S1-19 打包 smoke 没有验证用户真正看到的桌面应用

- **用户路径 / 预期**：干净机器双击 EXE，看到 WebView、标准最小化/最大化/关闭按钮，完成激活，重启恢复，并能正常关闭。
- **实际 / 根因**：`tests/packaging/windows-installer-smoke.ps1:356-415` 隐藏启动，只检查日志、DB、进程和第二实例；`:424` 强制 stop。`tauri.conf.json:30` 虽启用 decorations，但没有可见 GUI/焦点/WM_CLOSE 验收；portable ZIP 也无仓库内可复现装配脚本。
- **生产可达**：是，用户已报告标准按钮和整程序启动问题。
- **假绿原因**：进程存活被当成 GUI 可用；未经过许可证、Runtime 重连与优雅关闭。
- **整改归属 / 依赖 / 回退**：**G7**。保留上一版制品；新制品只有通过可见 GUI smoke 才提升为 current。

### S1-20 多对象写入、事件和账号归档缺少一致事务/补偿

- **用户路径 / 预期**：创建环境或归档账号要么完整成功，要么可恢复；进程、任务、会话、事件一致。
- **实际 / 根因**：`device_workspace_repository.py:21-80,163-193,216-243` 分步 commit；`device_workspace_service.py:111-149,582-587` 状态、日志、事件分离；`services/accounts/commands.py:339-415` 归档未统一停止浏览器、撤销会话和取消环境任务。
- **生产可达**：是，任一中途异常或归档操作可触发。
- **假绿原因**：happy-path 测试不注入跨 DB/文件/进程故障。
- **整改归属 / 依赖 / 回退**：**G6**。DB 使用明确事务，外部副作用使用 outbox/补偿；迁移可回退但审计记录不可删除。

### S1-21 全局配置总线存在“可保存但无人消费”和延迟报错

- **用户路径 / 预期**：保存重试、WebSocket、Provider 默认值和账号必需能力后，运行时立即按统一配置生效并在保存时校验。
- **实际 / 根因**：`services/config/schema.py:84-103,160-181` 定义多个键，但代码检索未发现 HTTP retry/WebSocket max delay 的消费端；`accounts.requiredCapabilities` 可保存重复或任意值，`runtime_policy.py:36-73` 到使用时才以 INTERNAL_ERROR 拒绝。
- **生产可达**：是，AI 与系统设置正式可达。
- **假绿原因**：`test_v1_config_and_diagnostics.py:31-68,165-170` 只验证持久化。
- **整改归属 / 依赖 / 回退**：**P0-H**。建立 config owner/consumer 矩阵与保存期校验；未接入的键只读或移除，保留旧值兼容读取。

### S2-22 账号身份仍是只读占位

- **用户路径 / 预期**：账号管理可修改名称、handle、定位摘要等可编辑身份字段。
- **实际 / 根因**：`AccountDetailPanel.vue:50-63` 显示“后续开放”，而客户端已有 patch（`runtime-client/accounts.ts:71-81`）。
- **生产可达**：是，但不阻断首次连接。
- **假绿原因**：账号创建测试未覆盖后续编辑。
- **整改归属**：G4，与连接向导共用账号修订和反馈机制。

### S2-23 默认 Desktop 门禁排除了 70 个 Vitest 文件且容忍路由警告

- **用户路径 / 预期**：默认 `npm test` 代表当前 Desktop 有效测试集。
- **实际 / 根因**：仓库有 94 个 Vitest 文件和 1 个 Playwright E2E 文件，默认 `package.json` 只运行 24 个 `tests/p0` Vitest 文件；本轮单独运行 `tests/tauri-capabilities.spec.ts` 已出现 1/3 失败。P0 测试还持续输出 10 个未匹配路由警告但退出 0。
- **生产可达**：间接影响所有发布判断。
- **假绿原因**：没有 active/compat/retired 测试清单和零意外 warning 规则。
- **整改归属**：G0。先分类和校准契约，不以放宽 asset scope 让旧测试变绿。

### S2-24 八个 pending 页面是已知范围，不应继续计入“已完成页面”

- **用户路径 / 预期**：导航项可完成对应业务任务。
- **实际 / 根因**：Route 存在，但正式页面明确提示尚未接入生产 Runtime。
- **生产可达**：是，属于透明但未完成的阶段边界。
- **假绿原因**：项目状态按路由/视觉计数，而非按真实任务完成率计数。
- **整改归属**：P0-I。G0 先修正文档口径，I 再按主链逐页启用。

## 7. S0 / S1 唯一整改归属

| 阶段 | 唯一归属问题 | 验收证据 |
| --- | --- | --- |
| G0 验收真源 | S0-01、S0-02、S0-07 | 无 seed 的首启 E2E；密钥/公钥一致；当前 manifest 绑定 Git、配置、测试和 SHA256 |
| G1 壳层 | S1-15 | 两档 PC 窗口打开菜单后的 bounding box、scrollWidth 和截图证据 |
| G2 受控目录 | S1-10 | 原生选择、rootRef resolver、权限/越界/失效/重启恢复测试；两类目录明确分离 |
| G3 执行环境 | S0-03、S1-08、S1-09 | UI/API 从零创建三对象；资格事务重检；进程所有权重启证明 |
| G4 连接与登录 | S0-04、S1-13 | 监督登录状态机、会话探测、typed action/deep link/returnTo 纵向 E2E |
| G5 Runtime 韧性 | S1-11、S1-12 | Sidecar 新端口/token 自动恢复；Runtime 启动前诊断；机器码稳定性矩阵 |
| G6 任务与一致性 | S1-14、S1-20 | 任务终态/取消/重试/日志；故障注入事务与补偿；归档清理证据 |
| G7 制品验收 | S1-19 | 当前 portable/installer 可复现；可见 WebView、激活、标准按钮、重启、优雅关闭 smoke |
| P0-H AI 真执行 | S0-05、S1-16、S1-17、S1-18、S1-21 | 配置到真实调用纵向测试；凭据轮换；依赖修复；受控文件；配置消费矩阵 |
| P0-I 创作生产链 | S0-06 | 账号级主模型与八页面逐段纵向 E2E，pending 按证据移除 |

S2-22 随 G4 处理，S2-23 随 G0 处理，S2-24 随 P0-I 处理；它们不占用 S0/S1 的唯一归属关系。

## 8. 仍需在实现阶段验证、但本次不冒充已确认的线索

1. 尚未在多台受限 Windows 实机复现机器码失败，因此 S1-12 的“脆弱性”由代码路径确认，具体失败率未知。
2. 本轮未执行 132 个 Runtime 测试文件、Rust 全量测试、完整构建和安装包 smoke，因此不得从静态数量推导它们通过。
3. 尚未对真实 TikTok 页面做自动登录；方案只允许用户监督登录和会话探测，不承诺规避验证码、风控或平台访问控制。
4. 当前 portable ZIP 是“免安装运行包”，数据仍落在系统本地应用目录；除非后续明确实现数据随包迁移，否则不得宣传为完全便携数据包。

## 9. 审计判定

- 历史 P0-F 文档和制品记录保留作为历史证据，但自 2026-08-02 起标记为 **stale snapshot**。
- 当前产品状态应表述为：**P0 桌面与账号基础可运行，生产验收证据已漂移；账号执行环境、TikTok 登录、AI 真执行和八个生产页面尚未闭环。**
- 下一步不是直接大改源码，而是先批准修订后的 P0-G 计划，再生成 G0-G7 详细规格；P0-H、P0-I 分别单独走计划与规格批准。
