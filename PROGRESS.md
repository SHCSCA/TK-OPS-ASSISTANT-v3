# 生产闭环审计进度

> 日期：2026-08-02
> 范围：P0-G 账号工作区与执行环境生产闭环，按 G0 → G7 实施

1. 目标：识别“页面存在、测试通过、文档完成，但真实用户无法完成操作”的生产断点。
2. 顺序：基线核验 → 十三 Route / 八条链审计 → 问题去重 → P0-G 修订 → 总路线 → 交叉验收。
3. 最大风险：现有测试通过但绕过真实创建、登录、GUI 与制品链，形成假完成证据。
4. 工作树基线：`main...origin/main`，283 条既有未提交状态，必须完整保留。
5. 路由基线：13 个正式 Route，8 个 P1/P2 pending，14 个 legacy redirect。
6. Desktop 基线：24 个 P0 测试文件、111 tests passed；`vue-tsc --noEmit` 通过。
7. 测试噪音：账号壳测试持续输出 10 个路由未匹配警告，但不影响退出码。
8. Runtime 静态基线：132 个 Runtime/Contract Python 文件、769 个 test 函数；未宣称全量通过。
9. 真实首启 E2E：退出 1，许可证签发私钥与 Runtime 验签公钥不匹配，页面未启动。
10. 门禁外复核：`tests/tauri-capabilities.spec.ts` 为 3 tests / 1 failed，确认默认测试集之外存在安全契约漂移。
11. 十三个 Route、八条生产链和 24 个去重问题已写入 `docs/audits/2026-08-02-production-chain-closure-audit.md`。
12. S0/S1 已唯一映射到 G0-G7、P0-H、P0-I；不存在跨阶段重复主责。
13. P0-G 已补齐验收真源、受控目录、真实 provisioning、候选资格、进程所有权、监督登录、任务和 GUI 制品验收。
14. 总路线已拆为 P0-G 账号执行基础、P0-H AI 真执行、P0-I 创作生产链，并明确十三 Route 启用门槛。
15. 交叉校验：24 个问题 ID 唯一；21 个 S0/S1 在审计映射表中各出现且只出现一次；Route 13 行、生产链 8 行。
16. 文件校验：5 个允许修改的文档均为 UTF-8 无 BOM；最长 343 行，无大文件实现；`BLOCKED.md` 无待裁决项。
17. 最终差异检查：`git diff --check -- docs/audits docs/superpowers/plans PROGRESS.md BLOCKED.md` 退出 0。
18. 当前状态：审计、P0-G 修订计划和生产链总路线均已完成，等待用户批准 P0-G 后进入规格阶段。

> 上述 1–18 条是实施前审计快照。用户已批准规格并要求进入真实生产实施；其中“只读”“等待批准”不再代表当前状态。

## P0-G 规格阶段

1. 用户于 2026-08-02 回复“同意执行”，P0-G 计划已批准。
2. 已复核 PRD、UI PRD、架构真源、现有 P0-G 计划、生产链审计和当前脏工作树；未清理既有改动。
3. 已确认复用现有 DeviceWorkspace、BrowserInstance、ExecutionBinding、AccountConnection、RuntimeTask 和 RuntimeEvent。
4. 规格不新建第二套任务状态；UI 终态映射到现有 status + completionKind / failureKind。
5. TikTok 登录固定为可见浏览器内用户监督登录，准备与探测分开，不输入凭据、不回传 Cookie。
6. 已生成 `docs/superpowers/specs/2026-08-02-account-workspace-execution-environment-closure-design.md`。
7. 规格覆盖模型、状态机、API、Tauri 桥、UI、错误、配置、迁移、任务事件、测试、恢复和回退。
8. 一致性检查：规格包含 8 个 G 阶段、5 组 API、模型/状态机/错误/配置/迁移/回退，无缺失章节。
9. 编码与格式：6 份相关文档均为 UTF-8 无 BOM、无行尾空白；文档差异检查退出 0。
10. 当前状态：规格已完成并等待用户批准；获批前不修改生产源码、测试、配置或制品。
11. G0 只读预检：当前为 94 个 Vitest 文件（24 个 P0 默认门禁、70 个门禁外）与 1 个 Playwright E2E 文件。
12. G0 首启根因已精确到 E2E 未传 `--runtime-public-key`，同时仍写入已删除的“完整机器码”输入框。
13. G0 假绿路径已确认：active 主链 helper 调用 `seedExecutionBinding`，再调用 `seed-execution-binding.py` 直写数据库。
14. G0 制品证据预检：仓库当前不存在 release/build artifact manifest，现有安装 smoke 只做隐藏进程与日志检查。
15. 待审批规格已补充 G0-A 至 G0-D 的精确文件地图、测试库存 Schema、manifest Schema 和提升规则。
16. 规格审批门已连续等待三个目标回合；当前没有可在不修改生产范围的前提下继续推进的只读工作。
17. 已将唯一阻塞项登记到 `BLOCKED.md`；收到“批准规格”后从 G0-A 恢复执行。

> 上述“等待规格批准”是历史过程记录。用户于 2026-08-02 明确要求纠正批准状态并按 G0 → G7 实施，`BLOCKED.md` 已清空。

## P0-G G0 验收真源修复

1. 规格状态已更正为“已批准”；P0-H / P0-I 已补齐依赖、接口、验证命令和回退方案。
2. 真实首启 E2E 已拆为独立激活用例，不再创建账号、不再写入机器码、不再注入执行环境或直接写数据库。
3. E2E 许可证签发与 Runtime 验签显式使用同一临时公钥；机器码由 Runtime 自动生成并只读展示。
4. 已建立 `test-inventory.v1.json`，当前完整登记 95 个 Vitest 文件：26 个 active、69 个 compatibility、0 个 retired；另登记 1 个 active Playwright 与 1 个 compatibility Playwright。
5. 默认 Desktop 门禁只运行 active 库存；未登记测试、重复分类、active 引用 seed 或直接写执行对象数据库时立即失败。
6. Tauri 文件系统权限测试已纳入默认门禁，并锁定 `$APPLOCALDATA/runtime/accounts/**/*` 最小范围，禁止扩大至用户主目录、文档、图片或视频全目录。
7. 已建立 release manifest schema v1、生成器、复验器和 Windows 构建编排器；脏工作树仅允许 test 通道，production 提升必须是干净提交且具有完整测试与 GUI smoke 证据。
8. `npm test`：退出 0，26 个测试文件、115 项测试通过，无 Vue Router warning 和预期异常日志污染。
9. `npm run typecheck`：退出 0，`vue-tsc --noEmit` 通过。
10. `npx playwright test -g "真实首启链完成授权且不注入执行环境"`：退出 0，1 项真实首启 E2E 通过；覆盖许可证激活、目录初始化、Runtime HTTP 链路和无账号空工作区。
11. E2E 收尾已区分主动进程树回收与 Runtime 异常退出，复验不再出现错误误报。
12. 当前状态：G0 完成，只证明验收真源恢复；账号切换布局、工作目录、执行环境、登录恢复和新 EXE 仍需按 G1 → G7 实施，不得宣称已交付。

## P0-G G1 账号切换布局闭环

1. 全局 `shell.css` 已接入统一样式入口；Desktop 根节点、工作区壳和窄窗提示统一使用宿主窗口 `100%` 尺寸，不再用 `100vw/100vh` 制造横向滚动。
2. 账号菜单已 Teleport 到 body 覆盖层，宽度固定按 320px/视口安全区取小值；宽屏从触发器对齐，紧凑窗口从侧栏右边缘留出 12px。
3. 菜单支持搜索、Escape、点击外部关闭、关闭后焦点恢复和 resize/scroll 动态重定位。
4. 定向组件/契约测试：2 个文件、7 项通过；TypeScript 类型检查通过。
5. 两档 PC 窗口 E2E 首次发现紧凑侧栏边界重叠 1px，未放宽断言；修正后复验退出 0，1440×900 与 1024×768 的菜单四边均在安全区内且页面无水平溢出。

## P0-G G2 受控工作目录桥

1. 新增 Tauri `workspace_roots` 模块，按命令、注册表、路径校验、类型和结构化日志分层，未把实现堆入 `main.rs`。
2. 已注册选择、描述、重新授权和撤销四个命令；用户取消选择返回 `null`，不是异常。
3. 注册表固定为应用本地数据目录的 `workspace-roots.v1.json`，使用不可猜测 `rootRef`、账号共同校验、修订号、临时文件和 `.bak` 快照。
4. 目录选择拒绝磁盘根、Home、Windows、Program Files、AppData、仓库根、Runtime 数据根、跨账号重复目录和不可写目录。
5. Runtime supervisor 通过只由宿主设置的 `TK_OPS_WORKSPACE_ROOT_REGISTRY_PATH` 传递注册表；页面和 HTTP 不提交绝对路径。
6. Runtime 新增只读 resolver，支持 mtime 缓存、主动失效、账号隔离、撤销/过期检测、损坏主文件回退已验证快照或 `.bak`、重启恢复。
7. Rust：`cargo test workspace_roots` 退出 0，3 项通过；Python：G2 Runtime/Contract 6 项通过；Desktop：3 项通过；类型检查通过。
8. Python 测试环境仍报告既有 `asyncio_default_fixture_loop_scope` 未识别警告；测试本身通过，该环境依赖警告将在 G7 工具链验收中单独核对。
9. 当前状态：G2 基础能力完成，工作目录将在 G3 的“新建执行环境”流程中成为必选输入；尚未宣称执行环境可用。

## P0-G G3 真实执行环境闭环

1. `0021_p0g_execution_environment_closure` 已增加受控目录引用、所有权、修订、错误证据和账号登录会话结构，并通过新鲜库、历史库和最新 head 迁移验证。
2. Runtime 已实现账号级执行环境创建、读取、资格评估和持久 provisioning 任务；HTTP 只接收 `rootRef`，目录路径由宿主注册表只读解析。
3. provisioning 会创建受控目录结构、启动本机 Chrome/Edge、校验 PID、可执行文件、Profile 命令行、owner marker 与调试端口所有权；证据不足时失败封闭并保留日志引用。
4. Desktop 账号向导已增加真实工作目录选择、新建环境、任务轮询/取消、状态和错误反馈；创建完成后只能按 Runtime 返回的合格候选继续绑定。
5. 绑定契约已收紧为 `{environmentId,eligibilityRevision}`；旧的“工作区 ID + 浏览器 ID”拼接入口已移除，跨账号、过期证据和不合格环境均被拒绝。
6. G3 Runtime 组合测试 34 项、相关 Desktop 测试 6 项和 TypeScript 类型检查已通过；旧 P0-C/P0-D 真实连接回归已迁移到新资格契约并通过。

## P0-G G4 监督登录与安全动作路由

1. Runtime 已实现 `account_login_sessions` 持久状态机、登录准备、公开身份探测、取消和安全登出任务；每账号只允许一个活动登录尝试。
2. 登录只在可见受控浏览器内由用户操作，服务端不接收密码、Cookie 或验证码；完成后只把账号、绑定、浏览器、公开身份和探测时间的最小证明写入 Secret Store。
3. 公开身份不匹配、未登录、页面不可识别、会话过期和跨账号读取均使用稳定错误码；清理 TikTok origin 失败时不会伪装已登出。
4. Desktop 账号向导已提供“打开浏览器登录”“我已完成登录”“取消登录”和目标/探测身份反馈，只有连接达到 `authStatus=valid`、`healthStatus=ready` 才进入下一步。
5. 新增 typed action router，按版本、当前账号、动作与路由白名单、参数和 returnTo 逐项校验；越权或解析失败 fail-closed，并在页面显示可见反馈。
6. API 真源已新增执行环境 3 个接口和监督登录 5 个接口，v1 静态库存为 89 个 HTTP；接口文档与实际注册路由一致性测试通过。
7. G4 Runtime/Contract 8 项、Desktop active 31 文件/131 项和 TypeScript 类型检查通过。
8. Playwright“新账号建立环境并完成监督登录”退出 0：覆盖真实账号、真实数据库、Tauri 格式目录注册表、真实浏览器进程与绑定；仅用户凭据输入/公开身份结果使用显式 E2E 适配器，生产入口仍使用真实 TikTok 公开页面探测。
9. 当前状态：G4 自动化阶段完成；真实 TikTok 凭据由用户监督输入的人工证据和可交付 EXE 仍属于 G7，尚未宣称最终交付。

## P0-G G5 Runtime 恢复、脱机诊断与机器码韧性

1. Supervisor 状态与连接 DTO 已携带 `generation`；Desktop 在挂载应用前先订阅 `runtime-supervisor://status`，不再永久缓存首次端口和会话令牌。
2. generation 变化会统一取消全部在途 HTTP、暂停非 GET 写操作、清空连接 Promise，并把失败转换为 `RUNTIME_CONNECTION_CHANGED`；用户草稿状态不被清空。
3. 账号 WebSocket 在连接变化时进入可见离线态，Runtime 新 generation 就绪后使用新 subscription revision 重建；Bootstrap 与当前账号聚合随后重新加载。
4. 宿主配置已统一为 `restart.maxAttempts=3`、`restart.initialDelayMs=500`、`restart.maxDelayMs=5000` 与 `diagnostics.tailLines=200`，由 Rust owner/validator/consumer 使用，页面不读取配置文件。
5. 新增 `get_runtime_supervisor_diagnostics` 与 `export_runtime_supervisor_diagnostics`；Runtime HTTP 不可用时仍能读取/导出版本、generation、阶段、退出码、重试次数、制品哈希和脱敏日志尾部。
6. 启动错误页已增加复制诊断摘要和导出诊断动作；诊断 payload 不含 session token、许可证密钥、环境变量值或完整路径。
7. 机器码既有三因子摘要格式保持为 v1；注册表、CIM、系统盘因子独立捕获并记录，至少两个稳定因子时可降级生成，不足时通过许可证服务返回 `LICENSE_STORE_UNAVAILABLE` 与 logId。
8. `cargo test runtime_supervisor`：18 项通过；机器码与诊断 Contract：10 项通过；旧许可证/签发器回归：16 项通过、1 项环境相关跳过。
9. Desktop active 回归：32 个文件、133 项通过；TypeScript 类型检查与相关差异检查通过。
10. 当前状态：G5 完成，进入 G6 任务终态、补偿、重启恢复和账号归档清理；尚未构建或交付最终 EXE。

## P0-G G6 任务生命周期、补偿与归档清理

1. Runtime 已增加系统级与账号级持久任务列表接口；Desktop 任务投影从 HTTP 最终真源重建，WebSocket 只负责触发刷新，Runtime generation 切换后自动补拉。
2. 任务轮询遇到 `RUNTIME_CONNECTION_CHANGED` 或 `RUNTIME_NOT_READY` 时会在原截止时间内继续等待，不再把 Runtime 重启误报为业务任务失败。
3. 当前账号详情面板显示最近五条真实持久任务，并覆盖加载、空、正常和错误状态；账号切换按 `account_id` 隔离任务投影。
4. 账号归档改为不可取消的 `account.archive_cleanup` 持久任务：先取消同账号其他任务、撤销 TikTok 会话、证明并停止受控浏览器，最后才提交归档状态与稳定 `account.archived` 事件。
5. 归档清理无法证明进程归属或停止进程时，账号保持 `attention + ARCHIVE_CLEANUP_FAILED`，环境进入 `cleanup_failed/orphaned`；工作目录、用户文件和未证明归属的进程均不会删除或误杀。
6. Desktop 账号管理在归档任务真正成功后才刷新账号目录并显示成功；提交、等待、失败和恢复后的最终状态均可见。
7. 执行环境已增加启动、停止、检查与软删除四类持久动作；全部要求修订锁和幂等键，删除固定保留用户文件。停止/删除前重新验证进程所有权，恢复中的停止任务可在已停止状态幂等收敛。
8. 代码审查修复了两处同类风险：过期停止任务不能控制仍运行的浏览器；停止环境不能被健康检查误标为正常。真实健康失败会清理进程引用并进入可重新启动的 stopped/offline 状态。
9. API 真源已登记 6 个任务 HTTP 与 7 个执行环境 HTTP，v1 静态库存更新为 95 个 HTTP；归档 202 语义、错误恢复、任务类型、缓存失效和 Desktop 调用映射已同步。
10. G6 Runtime 定向测试 11 项、Runtime/Contract 接口测试 10 项、Desktop 任务恢复 2 项和 active 全量 136 项已分别通过；TypeScript 类型检查与 Python compileall 通过。
11. 当前状态：G6 功能与阶段证据完成，进入 G7 全量测试、真实首启/账号执行主链、可见 Tauri GUI 与免安装 EXE/ZIP 制品验收。

## P0-G G7 测试通道制品交付

1. Runtime 全量测试通过：932 项通过、1 项环境相关跳过；Desktop 当前 active 门禁为 33 个文件、149 项通过；TypeScript 类型检查通过。
2. Rust/Tauri 单元测试 21 项通过；原生窗口会在 Windows 上强制恢复 `WS_OVERLAPPEDWINDOW`，清除 `WS_POPUP`，并重新应用标准窗口边框。
3. 真实首启 Playwright E2E 3 项通过：自动机器码与许可证、两档 PC 账号切换布局、新账号到工作目录、执行环境、绑定和监督登录链。
4. Windows 可见 GUI smoke 8 项通过：单入口、主窗口、标准窗口控制、最小化/最大化/恢复、Runtime ready、单实例、`WM_CLOSE` 优雅退出和重启恢复。
5. NSIS 安装包 smoke 通过：临时目录静默安装、隐藏 Python `PATH` 后启动、production SQLite/日志落点、Runtime ready、单实例、进程树清理和静默卸载。
6. 发布编排已生成测试通道 Runtime sidecar、NSIS 安装包与免安装 ZIP；manifest 包含 Git 状态、输入哈希、测试证据、制品大小和 SHA256，并已复验通过。
7. 免安装包不是数据随身版；应用数据继续保存到 Windows 本地应用数据目录，压缩包只负责完整携带 Desktop、Runtime 和资源。
8. 当前工作树为 `dirty=true`，因此只生成 `test` 通道 manifest，没有覆盖或提升 `dist/releases/current.json`，上一生产指针不受影响。
9. 当前候选仍需用户在目标机器上完成一次不保存凭据的真实 TikTok 可见浏览器监督登录；在该人工证据和干净提交具备前，不宣称 production 提升完成。
10. 当前状态：P0-G 生产实现和自动化测试通道制品已可交付测试；P0-H / P0-I 已获路线授权但尚未实现，不冒充 AI 真执行或完整创作生产链已完成。

## 0.4.8 未保存决策与定位版本体验补丁

1. 用户已批准 `docs/superpowers/plans/2026-08-02-unsaved-dialog-positioning-version-ux-fix.md`。
2. 项目源版本已由 `0.4.7` 升级为 `0.4.8`，根 `package.json` 为唯一真源；Tauri、Cargo、Cargo.lock 和 Python Runtime 镜像已同步。
3. 新增 `docs/VERSIONING.md`，锁定 PATCH / MINOR / MAJOR 判定、外发测试包版本升级和真实构建产物门禁。
4. `npm run version:sync` 与 `npm run version:check` 已通过；旧 Runtime manifest 继续绑定旧二进制，等待补丁完成后真实重建。
5. 已生成 `docs/superpowers/specs/2026-08-02-unsaved-dialog-positioning-version-ux-fix-design.md`，覆盖未保存决策接线、定位版本详情 API、语义摘要、基于版本修改、账号隔离、测试与制品。
6. 用户已批准规格，Desktop 与 Runtime 生产实现、接口文档和相关测试均已更新。
7. 未保存决策已修复控制器 `this` 接线、重复决策锁和切换期间页面保留；三种真实按钮路径均由 E2E 覆盖。
8. 定位版本已新增单版本详情 API、语义摘要、详情抽屉、错误重试、哈希复制和“基于此版本修改并保存为新版本”闭环。
9. 完整兼容 E2E 7 项通过；同时发现并修复 Windows 外部浏览器 PID 终止后的退出判定竞态，归档恢复按“历史环境保留、活动绑定清空、恢复后重新复检”验收。
10. Runtime 全量 922 项完成：`921 passed, 1 skipped`；Desktop active 33 个文件、147 项通过；TypeScript、Rust 21 项、首启 E2E 3 项和兼容 E2E 7 项全部通过。
11. `playwright-cli` 视觉验收覆盖 1440×900 Light、1024×768 Dark 的定位详情抽屉与未保存弹窗；无溢出、遮挡或控制台错误。
12. 首次构建被 Runtime 陈旧安装元数据的 0.4.7 版本阻断；已将 Runtime 源版本纳入统一同步/检查总线，相关测试 19 项通过，sidecar 重新构建后报告 0.4.8。
13. Windows GUI smoke 7 项与独立安装包 smoke 通过；release manifest 复验通过，通道为 `test`、工作树为 dirty，未提升 production 指针。
14. 免安装 ZIP 大小 `32,360,914` 字节，SHA-256 `79A567D585E0DB06EA5F859F7AB6542D93727534DFE22E11D64D112CC5692445`；直接运行 EXE 大小 `12,946,432` 字节，SHA-256 `6DECF520A2CCDDCADE94D297E0544B9E9F67ABB01628EB23FF38BAF96D174B10`。
15. 当前状态：0.4.8 补丁实现与测试通道 Windows 制品验收完成，可交付用户测试。

## 0.4.9 Windows 单入口免安装包补丁

1. 用户验收发现 `0.4.8` 免安装 ZIP 根目录同时出现 Desktop 与 Runtime 两个 EXE；根因是发布脚本直接把 Tauri external sidecar 复制到用户入口目录。
2. 本次验收修复保持 Runtime 架构不变：根目录只允许一个 Desktop EXE，Runtime 移入 `resources/runtime/` 并由 Supervisor 自动校验、启动和关闭。
3. 根据 `docs/VERSIONING.md` 的外发测试包规则，源版本已升级并同步为 `0.4.9`，`npm run version:check` 通过。
4. Desktop 33 个测试文件、147 项测试、类型检查、首启 E2E 3 项、Rust 21 项全部通过。
5. Windows GUI smoke 8 项通过，新增 `single-root-executable` 结构门禁，并验证内部 Runtime ready、单实例、优雅退出与重启恢复。
6. NSIS 安装包 smoke 通过，验证 Supervisor ready、production 数据落点、离线启动、单实例与进程树清理。
7. 免安装 ZIP 根目录实测只有 `tk-ops-desktop.exe` 一个 EXE；Runtime 与 FFprobe 位于内部 `resources/` 目录，不需要用户启动。
8. 新 ZIP 大小 `32,360,847` 字节，SHA-256 `8C04D57CF8AF756BDCF0ECFBE5C41A6004DD7104D203C2A2D43E7D8503757F2F`；当前为 dirty 工作树生成的 `test` 通道制品，未提升 production 指针。

## 0.4.10 Production 加固与测试候选

1. 机器码已进入稳定身份版本与许可证兼容链；执行环境失败重试保留原环境、任务和错误上下文，监督登录取消会真实停止后台准备任务。
2. Runtime 打包排除了 `greenlet` 与不匹配的 `MSVCP140.dll`，Sidecar 使用同一套 ABI 运行；当前 SHA-256 为 `0394A51821A2F9488E3D168630707751C9DEA63315B451285C9100A7296FC481`。
3. 首启 E2E 使用仅限测试的受控浏览器进程，仍真实校验 PID、可执行文件、Profile 命令行、owner marker 与调试端口所有权，不再依赖测试机 Chrome/Edge 的多进程行为。
4. Runtime 全量 `932 passed, 1 skipped`；Desktop 33 个文件、149 项；TypeScript 类型检查、Rust/Tauri 21 项、首启 E2E 3 项、账号兼容 E2E 7 项全部通过。
5. Windows GUI smoke 8 项通过；NSIS 安装包连续验证 Supervisor ready、production 数据落点、离线启动、单实例、优雅退出与进程树清理。
6. 打包许可证 smoke 已校验 Runtime manifest 与二进制 SHA-256，注入真实 `artifactBuildId`，完成机器码读取、发行器签发、激活与 active 复核。
7. release manifest schema v2 已生成并复验：10 份测试证据、4 个制品，`channel=test`、`dirty=true`，未提升 production 指针。
8. 免安装 ZIP 根目录仍只有 `tk-ops-desktop.exe` 一个 EXE；ZIP SHA-256 为 `A7D369B24790486079E5F60A30DBBC961480AC7D7526BEA5B94236491CA3A3D9`，NSIS SHA-256 为 `FCB79C4863F87D0E312584C95BE795CEDA6CB3C4653FE6B20437ADBB89FCDC9F`。
9. 当前状态：0.4.10 可作为测试候选交付；Production 提升仍需目标机器真实 TikTok 可见监督登录证据与干净工作树。

## 0.4.11 P0-G 验收补齐与测试候选

1. 外部验收指出 0.4.10 缺少执行环境失败恢复、监督登录准备取消的独立 Runtime E2E，且 ZIP 全新解压冷启动出现一次窗口控制探测波动；本补丁只收口既定 P0-G 规格，不扩展八个 pending 页面。
2. Playwright 首启证据由 3 项扩为 5 项；新增环境失败注入、同对象重试、`retryOfTaskId`、同工作目录/浏览器证据，以及登录准备取消后会话和任务终态验证。
3. 登录导航不再同步阻塞 Runtime 任务协程；取消会真实终止准备任务，UI 显示“登录已取消”并提供“重新开始登录”。
4. GUI smoke 现从本次 portable ZIP 全新解压目录启动，要求窗口句柄与标准样式连续稳定后才测试最小化/最大化；共 9 项，证据同时绑定 Desktop 与 portable 哈希。
5. 根据版本治理规则升级为 `0.4.11`；0.5.0 仍保留给 P0-H AI 真执行和 P0-I 创作生产链。
6. 自动发布门禁仍为 test channel：Production 提升继续需要目标机器真实 TikTok 可见监督登录证据和干净提交重建。

## 0.5.0 P0-H 真实 AI 执行规格开工回执

1. 目标：仅交付 P0-H H1-H5 实现级详细规格，并同步项目状态；本轮不修改生产代码、测试、配置、迁移或制品。
2. 基线：版本 `0.4.11`、正式 pending 路由 8 个、P0-H 规格 0 份，`services/ai_execution_v1` 与 `repositories/ai_execution_v1` 均不存在，全部符合任务书预期。
3. 顺序：核对 B1-B5 与文档真源 → 冻结模型/API/文件地图/验收回退 → 同步状态 → 执行红灯到绿灯及白名单审计。
4. 最大风险：真实凭据和真实 Provider 验收只能在后续目标机器实施；本规格必须保证证据脱敏，并禁止自动假 Provider 冒充真实验收。
5. 写入边界：仅限本规格、`docs/PROJECT-STATUS.md`、`PROGRESS.md`、`BLOCKED.md` 四个文档。

## 0.5.0 P0-H 规格执行进度

1. 真源核对完成：B1-B5、PRD、UI、架构、AI v1 API、Provider 适配器、任务内核、知识索引与 Tauri `rootRef` 实现均已读取。
2. 已确认 P0-H 必须新增 0023 加法迁移与统一 AI Execution Gateway；现有 `AITextGenerationService`、`ai_job_records` 和不可用受控文件解析器只能作为迁移边界，不能继续形成第二条生产链。
3. 必填项报警器已先用 `P0H_MISSING_MARKER` 执行，因规格文件不存在按预期退出 1，红灯有效。
4. 已生成 `docs/superpowers/specs/2026-08-09-p0-h-real-ai-execution-design.md`：冻结 H1-H5、AIExecution/AIJob、状态机、API/错误码、rootRef 文件链、Desktop 状态、0023 与精确文件地图、两层证据和 rollback。
5. `docs/PROJECT-STATUS.md` 与 `BLOCKED.md` 已统一为“P0-H 规格待批准，尚未实施”；八个正式路由继续 pending，未修改生产代码、测试、配置、迁移或制品。
6. 同一必填项报警器对真实词表执行成功，H1、H2、H3、H4、H5、AIExecution、AIJob、account_id、idempotency、timeout、retry、cancel、usage、cost、redaction、rollback 全部命中，退出码 0。
7. 第一轮规格结构审计通过：776 行、19 组结构化表格，模型、状态机、API、错误码、文件地图、验收与 rollback 章节齐全，占位词扫描为 0；四文档均为 UTF-8 无 BOM。
8. 第一轮 `git diff --check` 退出 0。仓库原始 `git diff --name-only` 仍显示开工前既存白名单外差异；同粒度状态对比为开工 `337=白名单3+外部334`、结束 `338=白名单4+外部334`，白名单外增量 0，生产源码、测试、配置和制品的本任务改动数为 0。

## 0.5.0 P0-H 规格第二轮完成性审计

1. 消除创建期循环外键：Snapshot 不再反向保存 execution ID，一对一关系只由 Execution 的非空唯一外键建立，execution/snapshot/task ID 在同一事务前预生成。
2. 修正 OutputStore 崩溃一致性：临时文件 fsync 后先原子进入最终 content-addressed 路径，再提交数据库引用；改名失败不提交，数据库失败留下的孤儿文件由启动对账清理。
3. 补齐 Provider、credential、Model 与 CapabilityRoute 不可变 revision、活动指针、Route draft/validate/activate API，以及旧 Route 端点的单服务兼容边界。
4. 补齐受控文件注册表的 Supervisor 启动配置、Runtime 路径校验和 Desktop 现有页面/状态文件地图；没有新增主导航 Route。
5. 新增 post-send 终态未知与计费不确定边界：此类执行禁止自动 retry/fallback，只有用户看见风险后才能新建 same_snapshot retry。
6. 第二轮必填词、敏感占位词、UTF-8 无 BOM、统一状态和结构门禁通过：规格 869 行、19 个二级章节、19 组结构化表格；最终差异与白名单门禁在本轮末执行。
7. 最终 `git diff --check` 退出 0；原始 `git diff --name-only` 已执行，仍包含开工前既存的白名单外 tracked 差异。
8. 同粒度状态门禁为 `338=白名单4+外部334`，相对开工 `337=白名单3+外部334` 的白名单外增量仍为 0；本任务新增状态只有白名单内规格文件。

## 0.5.0 P0-H 规格第三轮最终审计

1. 按 B1-B5 和任务书逐项建立当前文件证据，范围边界、H1-H5、模型、状态机、隔离、API、事件、Desktop、0023 文件地图、两层证据、阶段命令和回退共 16 类要求全部通过。
2. 必填项真实词表检查退出 0；缺失标记检查以 `P0H_MISSING_MARKER` 按预期退出 1；禁用占位词 0、四文档 UTF-8 无 BOM、开工回执 8 行、正式 pending Route 仍为 8 个。
3. `git diff --check` 退出 0；规格保持 869 行、19 组结构化表格，状态文档仍统一为“P0-H 规格待批准，尚未实施”。
4. 仓库状态第三次仍为 `338=白名单4+外部334`，相对开工的白名单外增量为 0；原始 `git diff --name-only` 仍越过白名单。
5. 任务禁止修改或回滚开工前 334 条外部差异，因此无法使原始仓库级白名单转绿；同一阻断已连续三轮成立，且授权范围内没有剩余可执行修复。

## 0.5.0 P0-H 用户授权后的安全隔离

1. 用户已明确授权谨慎处理既存工作树差异；全程不删除、不覆盖、不推送，并保留不可变 stash 哈希作为恢复点。
2. 预检为 `main@f329401bfea40b91da08075f03f40af839b57489`、既有 stash 0 个、tracked 状态 105 条、untracked 状态 233 组共 1283 个文件约 153 MB，G 盘可用约 2.33 GB。
3. 原始完整可见状态保存在 `2a1079de64d62e00fbbed95862a34dd895e43ae0`；`.gitignore` 还原后显现的 668 个历史忽略产物保存在 `6b1dcad7b8fa0603c6ce43a16b5663e68475c75c`。两者均为含三个父提交的本地 stash，白名单文件命中数为 0。
4. 仅将第一份快照应用到新建本地分支 `codex/p0h-baseline-snapshot`，恢复真实 `0.4.11` 源码；四份 P0-H 文档在应用前后 SHA-256 完全一致。
5. `.codex-tmp` 与原型 `.npm-cache` 另存为 `b5ea8a0de0a2d1fc786b8f77e743d18f849b9c2d`，未把截图临时文件或约 150 MB npm 缓存写入 Git 历史。
6. 基线候选共 990 个路径、约 11 MB，最大文件约 1.04 MB；没有超过 10 MB 的文件、私钥、环境变量文件、可执行文件或缓存目录，许可证 PEM 已核验为公钥。
7. 本地基线提交为 `bec7844452bce4e6a1559debc1903e30ba4bb03a`，提交信息 `chore: snapshot pre-p0h 0.4.11 baseline`；990 个既有路径已固化，四份 P0-H 文档命中数为 0。
8. 当前分支没有上游且未推送；三个 stash 均保留，未执行 pop 或 drop。基线提交保留历史内容原样，提交前诊断出的旧尾随空白未做跨范围格式化。
9. 当前工作区只剩四份 P0-H 白名单文档；在当前分支不要重复应用原始完整快照，如需恢复缓存或历史忽略产物，只按用途使用对应不可变 stash 哈希。

## 0.5.0 P0-H 用户授权后最终门禁

1. `npm run version:check` 退出 0，主版本保持 `0.4.11`；正式 pending Route 仍为 8 个。
2. 同一必填项检查以 `P0H_MISSING_MARKER` 退出 1，再以真实 H1-H5 与模型、隔离、执行控制、证据词表退出 0，红灯到绿灯符合预期。
3. 禁用内容命中 0；四份文档均为 UTF-8 无 BOM；开工回执 5 项；规格保持 869 行、19 组结构化表格。
4. `git diff --check` 退出 0；`git diff --name-only` 仅列四份白名单文档；工作区状态数 4、白名单外状态 0。
5. 安全基线 `bec7844452bce4e6a1559debc1903e30ba4bb03a`、本地分支与三个 stash 对象均完成完整性校验；没有上游、没有推送。

## 0.5.0 P0-H 规格批准

1. 用户于 2026-08-09 明确批准 P0-H 真实 AI 执行详细规格。
2. 规格状态统一更新为“已批准，实施待开始”；P0-I 创作生产链仍不在本阶段范围内。
3. 下一步严格按 H1 → H2 → H3 → H4 → H5 顺序实施，并在每个阶段完成后集中执行阶段测试与一条主链回归。

## 0.5.0 P0-H H1-H4 实施与 H5 门禁工具

1. H1 已完成：新增 `0023_p0h_real_ai_execution`、AIExecution / AIJob / Usage / Output / Snapshot / Dependency Snapshot 模型、仓储、目标 Schema 契约和加法迁移。
2. H2 已完成：Provider 真实小调用验证、不可变依赖快照、Route / Template / Recipe draft→validate→activate 生命周期、修订漂移阻断和配置总线执行策略已接通。
3. H3 已完成：Tauri `rootRef` 受控文件注册、Runtime 账号 Asset、知识 v2 文本块、索引与快照链落地；任意路径、越权账号、篡改哈希和超限文件均失败封闭。
4. H4 已完成：统一 AI Execution Gateway 与 Desktop 账号级真实调用工作面覆盖预检、创建、查询、取消、same-snapshot retry、输出、用量、费用、超时、fallback、重启恢复、事件与脱敏日志。
5. H5 工具已完成：最终 evidence 严格 allowlist、四制品 SHA-256 绑定、reported usage / 成本门禁、两阶段附加和 Production manifest 验证已通过；真实外部 Provider 证据仍待目标机器人工执行。
6. 修复 Playwright WebServer 强制结束后可能残留 Runtime、Provider、Vite、状态文件与临时凭据目录的问题；新增 `globalTeardown → shutdown.request → 环境优雅回收` 握手，最终复验残留进程 0、状态文件和临时目录均清理。
7. 最终自动化证据：Runtime `977 passed, 1 skipped`；Desktop 36 个文件、`162 passed`；Rust/Tauri `24 passed`；TypeScript typecheck 通过；P0-H Playwright `1 passed`；H5 发布证据 `10 passed`。
8. `npm run version:check` 与 `git diff --check` 均退出 0；新增 H5 脚本和 E2E 支持文件均小于 500 行。
9. 版本继续保持 `0.4.11`，H5 真实外部 Provider、真实 TikTok 目标机证据与干净 Production 构建完成前不宣称 `0.5.0`；P0-I 仍未开始，八个正式业务路由继续 pending。
