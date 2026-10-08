# Changelog

## Unreleased

### P0-H 真实 AI 执行（0.5.0 候选开发中）

- 新增 `0023_p0h_real_ai_execution`、不可变 AI 依赖快照、Provider 真实小调用验证、版本化 Route / Template / Recipe 生命周期和账号隔离约束。
- 新增 Tauri `rootRef` 受控文件注册、Runtime 账号 Asset 与知识 v2 文本块链；页面不能直传任意绝对路径。
- 新增统一 AI Execution Gateway 与账号级 Desktop 真实调用工作面，覆盖预检、执行、取消、同快照重试、输出、用量、费用、超时、fallback、恢复与脱敏证据。
- 新增 H5 严格 allowlist 证据生成、四制品 SHA-256 绑定、两阶段证据附加与 Production 发布门禁；受控 Provider 明确禁止冒充外部真实 Provider。
- 修复 P0-H Playwright WebServer 结束后可能残留 Runtime、Provider、Vite、状态文件和临时凭据目录的问题；`globalTeardown` 现在通过显式关闭请求等待完整回收，清理失败会使 E2E 失败。
- 当前自动化结果：Runtime `977 passed, 1 skipped`；Desktop 36 个文件、162 项；Rust/Tauri 24 项；TypeScript、P0-H Playwright 1 项和 H5 发布证据 10 项通过。
- 源码版本暂保持 `0.4.11`；目标机器真实 OpenAI-compatible Provider 证据、真实 TikTok 证据、干净 Production 构建及 P0-I 完成前，不发布或宣称 `0.5.0` Production。

### 0.4.11 P0-G 验收补齐与冷启动加固

- 新增两条独立真实 Runtime Playwright 场景：执行环境首次创建失败后保留原对象和任务上下文重试；监督登录 `preparing` 阶段取消后，会话与后台任务真实进入取消终态。
- 登录导航移入可取消的后台执行边界，取消后不再继续推进为等待用户登录；界面保留“登录已取消”和“重新开始登录”的可恢复状态。
- E2E Runtime 增加仅测试入口可用的一次性浏览器启动失败与登录导航阻塞控制，生产 Runtime 不暴露故障注入 API。
- Windows GUI smoke 改为从本次 portable ZIP 全新解压目录冷启动，并连续确认同一有效窗口句柄后再测试标准窗口控制；9 项证据同时绑定 Desktop 与 portable SHA-256。
- 版本按已外发测试包的补丁规则从 `0.4.10` 升为 `0.4.11`；八个 pending Route 未伪开放，继续归入 P0-H / P0-I。

### 0.4.10 Production 加固与真实发布门禁

- 加固机器身份、许可证、执行环境失败重试、监督登录取消、Runtime 启停日志与发布 manifest v2；错误与制品身份均进入可追踪证据。
- 修复 PyInstaller 混入不兼容 `MSVCP140.dll` 的 Runtime 崩溃，打包 Sidecar 排除 `greenlet` 并通过真实启动检查。
- 首启 E2E 增加受控真实进程与端口所有权测试，避免依赖测试机浏览器多进程实现；生产浏览器链保持严格所有权验证。
- 修复安装包 smoke 的时序抖动、阶段诊断与 Windows PowerShell UTF-8 输出；GUI 8 项和安装包连续门禁通过。
- 修复打包许可证 smoke 漏传 Runtime `artifactBuildId`，现已校验 manifest 与二进制哈希，并完成真实签发、激活与复核。
- 全量结果：Runtime `932 passed, 1 skipped`；Desktop 33 个文件、149 项；TypeScript、Rust 21 项、首启 E2E 3 项、账号兼容 E2E 7 项全部通过。
- 0.4.10 test-channel manifest 已绑定 10 份测试证据与 4 个制品；免安装 ZIP SHA-256 `A7D369B24790486079E5F60A30DBBC961480AC7D7526BEA5B94236491CA3A3D9`，NSIS SHA-256 `FCB79C4863F87D0E312584C95BE795CEDA6CB3C4653FE6B20437ADBB89FCDC9F`。
- 当前工作树为 dirty，仅交付测试候选；Production 仍需目标机器真实 TikTok 可见监督登录证据与干净提交重建。

### 0.4.9 Windows 单入口免安装包修复

- 免安装 ZIP 根目录只保留 `tk-ops-desktop.exe` 一个用户入口，Python Runtime 收进 `resources/runtime/` 内部资源目录并继续由 Desktop 自动启动。
- Runtime Supervisor 改为启动经过 manifest 与 SHA-256 校验的资源绝对路径；安装包与免安装包使用同一内部 Runtime 布局。
- Windows GUI smoke 新增根目录单 EXE 门禁，防止后续构建再次把内部 sidecar 暴露为第二个入口。
- 按已外发测试包的补丁规则将版本从 `0.4.8` 升级为 `0.4.9`；新制品已重新生成 Runtime manifest、release manifest 和 SHA-256。
- `0.4.9` Desktop 33 个测试文件、147 项测试、类型检查、首启 E2E 3 项、Rust 21 项、GUI smoke 8 项及安装包 smoke 通过；免安装 ZIP SHA-256 为 `8C04D57CF8AF756BDCF0ECFBE5C41A6004DD7104D203C2A2D43E7D8503757F2F`。

### 版本治理

- 将下一次缺陷修复交付的项目版本从 `0.4.7` 提升为 `0.4.8`，并新增统一的主版本、次版本、补丁版本判定与发布门禁。
- 根 `package.json` 作为正式版本唯一真源；Tauri、Cargo 和 Python Runtime 源版本同步更新，Runtime manifest 与 EXE 继续由真实构建生成，禁止手工伪改构建信息。

### 0.4.8 未保存决策与定位版本体验修复

- 修复未保存内容弹窗的控制器上下文丢失问题；“取消”“放弃并继续”“保存并继续”现在只接受一次决策，并在账号切换期间保留页面守卫。
- 新增账号定位历史版本详情接口、加载与错误恢复状态；版本列表改为目标受众、内容支柱和表达风格的语义摘要，并支持查看完整详情、复制哈希和基于历史版本生成新草稿。
- 当前定位卡片同步显示真实受众、内容支柱和风格标签；历史泛化摘要保持只读兼容，不伪造旧数据。
- 修复账号目录后台刷新期间菜单残留与 E2E 导航竞态，系统设置和账号管理继续通过真实壳层入口切换。
- 修复 Windows Runtime 仅持有外部浏览器 PID 时过早判定停止失败的问题；终止后进行有界退出等待，并用 Windows 进程退出码确认真实状态。
- Runtime 源版本改由统一版本同步脚本维护，sidecar `--version` 不再读取虚拟环境中的陈旧安装元数据；0.4.8 构建前后均执行版本一致性门禁。
- 完整兼容 E2E 7 项通过，覆盖账号隔离、定位 v1→v2、三种未保存决策、执行环境、AI 配置、归档恢复、十三容器和双主题 PC 布局。
- 0.4.8 测试通道制品已通过 GUI 与安装包 smoke：免安装 ZIP SHA-256 `79A567D585E0DB06EA5F859F7AB6542D93727534DFE22E11D64D112CC5692445`；NSIS SHA-256 `84E4F19B963269A7C9E38C4A1C4BDCC322E2C259547EB0C1FCF7D12CA4160E4F`。

### P0-F 正式路由与 Windows 桌面交付

- 正式 Route Manifest 已切换为十三个页面容器和十个账号级入口；旧 Project、Timeline、剪辑、独立配音 / 字幕 / 渲染 / 自动化 URL 只做一次性迁移重定向，不再进入旧业务页面。
- 落地 Windows Runtime sidecar、Tauri Supervisor、单实例、动态 loopback 端口、内存会话令牌、生产数据目录、启动超时、有限重启、优雅退出和 Windows Job Object 进程树清理。
- 强化迁移启动恢复：迁移实际变更且 durable journal 尚未开放写门时才允许恢复；写门开放后禁止覆盖当前数据库，失败证据只暴露稳定错误码、revision 与 SQLite 错误类别。
- 修复 Windows 受限 `PATH` 下机器码采集与 `\\?\\` 规范路径传入 Python 导致的 SQLite `SQLITE_CANTOPEN`；正式应用无需系统 Python 即可离线启动 Runtime。
- 修复 Desktop 冷启动时早于 Supervisor ready 获取连接的竞态：启动页现在保持加载并以 250ms 间隔有界等待最多 90 秒，Runtime ready 后自动继续，永久错误仍立即进入可恢复错误态。
- 修正首启授权交互：完整机器码由 Runtime 根据当前 PC 稳定硬件信息自动生成并只读展示，支持一键复制；Desktop 激活时只提交许可证密钥，由 Runtime 强制绑定本机机器码。
- 恢复 Windows 原生标题栏，免安装应用提供标准最小化、最大化与关闭按钮。
- 修复许可证签发私钥与 Runtime 内嵌公钥失配：统一正式公钥，签发前增加密钥对一致性门禁，密钥初始化拒绝覆盖，测试不再改写真实签发私钥。
- 本轮修正复验通过：Runtime 定向 28 项、Desktop 111 项、全局前端类型检查、239 模块生产构建和真实 Sidecar smoke 均通过。
- 完成 P0 全量验收：Desktop 107 项、全局 `vue-tsc`、239 模块生产构建、7 条真实 Runtime E2E、Rust 17 项、Sidecar smoke、NSIS 安装包 smoke，以及 Light / Dark 与两档 PC 窗口视觉检查均通过。
- NSIS 制品：`TK-OPS_0.4.7_x64-setup.exe`，大小 `30,984,341` 字节，SHA-256 `E75501CA8BBA51A610ED411CEFD1B09844FF3A9EACCA8824AEA09F41EF688F75`。
- 本地文件知识源桥接未在 P0-F 内伪实现；当前继续失败封闭并保留重试，转入 P1 单独设计与验收。

### P0-E AI 配置纵向链

- 新增 Alembic `0020_p0e_ai_vertical_chain`，补齐 Prompt 聚合修订与账号 AI Recipe 内容摘要，并在任何 SQLite DDL 前完成 legacy Recipe JSON 预校验。
- 落地 Provider、Model、Capability、Capability Route、Prompt Profile、Composition Template 与 Account AI Recipe 的 v1 Runtime 服务、35 个 HTTP 接口和领域级 Desktop Client / Store。
- Provider 凭据正文只进入系统安全存储；读取仅返回 `credentialSummary`。任务快照、事件、日志和普通写幂等记录继续拒绝凭据、Prompt 正文与本地路径。
- 落地 Provider 健康检查、模型发现、模型能力验证三类持久任务，以及 Provider 健康、能力契约、Prompt / Template 版本和 AI 配置修订共同约束的路由与 Recipe 激活门。
- 落地低噪音 AI 与系统设置、五步 Provider 向导、Prompt / 合成模板版本工作面及账号 AI Recipe 编辑入口，覆盖加载、首次使用、空、依赖阻断、长任务、错误、重试和未保存守卫。
- P0-E 阶段范围 Runtime 71 项、Desktop 41 项均取得通过证据；DTO 收口后额外 14 项 Desktop 回归通过。`build:p0` 处理 530 个模块并通过，P0-E 新路径类型错误为 0，113 个相关文件通过 UTF-8、无 BOM 与 500 行门禁。

### P0-D Desktop 账号上下文

- 拆分 Desktop Runtime Client / Types，Bootstrap、账号、定位知识、系统配置、任务和事件统一进入领域客户端，新页面不直接请求 Runtime。
- 新增工作区激活和同账号真实连接候选接口，`AccountDto` 补齐定位摘要与最近使用时间；当前 v1 库存为 46 个 HTTP + 1 个 WebSocket。
- 落地 Account Context、最近账号与页面恢复、未保存守卫、迟到响应隔离、可逆切换事务、账号事件重订阅和当前账号归档清理。
- 落地受控 P0 Route Manifest、首启门、新账号壳、账号切换器、状态反馈和宽屏 / 紧凑 PC 布局；该受控清单已在 P0-F 切换为正式路由真源。
- 落地账号管理、六步向导、真实连接、复制、归档恢复，以及定位、知识规则、来源、索引、快照和 BrandKit 的真实 Runtime 页面。
- P0-D 阶段验收通过：Runtime 38 项、Desktop 50 项均取得通过证据；P0-D 新路径类型错误为 0，`build:p0` 处理 468 个模块并通过，真实 Runtime 完成授权、双账号隔离、页面恢复、归档清理和两档 PC 窗口 E2E。
- 真实 E2E 修复开发编排器未传递预期 Host 的启动缺口；浏览器验收结束时 Console 为 0 错误、0 警告。当时登记的 79 个 legacy 类型错误已在 P0-F 正式切换时清零。

### P0-C 账号纵向链

- 新增 Alembic `0019_p0_account_vertical_chain`，以加法迁移接管账号五状态、知识快照标签和普通写幂等记录；只保守补齐缺失的空知识库与保守发布默认值，不伪造来源、快照、连接或 ready。
- 落地账号创建、详情、工作区上下文、六步向导、白名单配置复制、归档、恢复健康复检与 readiness 服务，并强制账号聚合修订和全层账号作用域。
- 落地真实 `DeviceWorkspace -> BrowserInstance -> ExecutionBinding` 连接、绑定与诊断链路，拒绝跨账号对象、假绑定和不一致执行证据。
- 落地定位版本、知识规则、六类知识来源、正文/公共 HTTPS 真实索引、不可变快照、BrandKit 和发布默认值；file 来源可创建，但在受控文件桥实现前明确失败并保留重试路径，该桥已转入 P1。
- 新增 `account.health_check`、`account.restore_health_check`、`account.connection_check` 和 `knowledge.index` 四个可取消持久任务类型，覆盖超时、失败、重启策略、日志和账号 Topic 状态反馈。
- 配置总线新增账号分页、普通写幂等 TTL 和三个知识索引策略键；知识索引任务冻结创建时配置修订与策略，避免在途任务配置漂移。
- 新增 31 个账号范围 `/api/v1` HTTP 接口，当前静态库存达到 44 个 HTTP + 1 个 WebSocket；同步账号、知识、任务事件、错误、配置和 legacy 退出关系文档。
- P0-C 阶段范围 175 项均已取得通过证据：最后一次完整运行 `169 passed, 6 failed in 123.31s`，剩余 6 项修正测试断言后定向复验 `6 passed in 23.52s`；接口库存、编译、差异和 UTF-8 门禁同步通过。

### P0-B Runtime v1 内核

- 新增 13 个 `/api/v1` HTTP 接口和 1 个 WebSocket 入口，统一 Runtime Session、Host / Origin、许可证门、成功/失败信封、错误码与 `log_id`。
- 将任务切换为 SQLite 持久化真源，覆盖快照 v2、处理器版本、幂等、超时、取消、重试、重启恢复和有界停机。
- 新增账号范围 Topic、sequence、outbox、断线重放、HTTP 最终状态补拉，以及 Bootstrap、系统设置和任务 legacy 薄适配器。
- 强化结构化日志与诊断安全，脱敏 Token、Prompt、Provider body 和本地路径，并对动态 Validation 键失败封闭。
- 新增 Alembic `0018_p0_runtime_kernel`，收紧任务与事件约束，并保护 SQLite 跨 revision 有数据降级的失败原子性。
- P0-B 最终阶段验收通过：41 个定向测试文件 `239 passed, 1 skipped in 171.75s`；391 个 Python 文件编译、接口库存、差异和 UTF-8 门禁通过。

### P0-A 账号基础与数据库接管

- 统一 Runtime 与 Alembic 数据库路径、迁移配置、启动与迁移结构化日志和启动生命周期。
- 新增已知 legacy 匿名结构指纹、跨进程迁移锁、DB / WAL / SHM 备份恢复与目标 Schema 契约校验。
- 新增 Alembic `0015–0017`，以加法方式预建账号基础、AI 配置、持久任务和事件对象，并保守迁移旧数据。
- 生产 Runtime 在创建 Engine、Repository 和 Service 前执行正式迁移；未知 Schema 只读失败，不再由正常启动隐式 repair。
- 产品、架构、项目状态、兼容矩阵和 legacy API 索引同步到账号工作区 P0 主线。
- P0-A 唯一一次阶段测试通过：14 个定向测试文件共 `94 passed`；Python `compileall`、差异和 UTF-8 门禁通过。

### M05 AI 剪辑工作台体验收敛

- 预览舞台画幅切换从局部组件状态提升为工作台状态，9:16 / 16:9 选择可由页面与 Store 统一承接。
- 真实视频 / 音频素材预览接入播放事件同步，媒体 `currentTime` 与时间线播放头双向换算，拖动时间线后播放器会跟随定位。
- 删除时间线片段前新增桌面确认，删除成功后保存状态明确提示可通过时间线工具栏撤销。
- 更新 M05 工作台体验收敛计划、项目状态文档、预览舞台测试、工作台页面测试、Store 回归测试与 graphify 图谱。

## 0.4.7 - 2026-05-17

### M05 真实编辑交互

- M05 时间线拖拽交互拆分为几何、磁吸和拖拽状态模块，片段移动、边缘裁剪、分割与删除均通过 Runtime 保存并可回滚错误。
- Runtime 新增资产入轨能力，支持从资产中心把视频/音频素材加入匹配轨道，并拒绝锁定轨道、源文件缺失、类型不匹配和同轨重叠。
- 资产来源视图补齐“加入时间线”和“替换片段”闭环，前端仅通过 Runtime Client 和 Pinia store 发起修改，不在组件中直接请求。
- 播放器、属性面板与本地预检联动到当前播放头和选中片段，预检问题可定位到相关片段或轨道，无法定位时显示中文提示。
- 更新 Runtime API 文档、M05 实施记录、前后端契约测试、页面测试、布局测试和版本镜像。

## 0.4.6 - 2026-05-15

### M05 基础剪辑工作台 UI 定稿

- M05 时间线二阶段补齐播放头分割、步进移动、基础磁吸和边缘裁剪，Runtime 统一校验重叠、锁定轨道、负起点和裁剪最小时长。
- M05 AI 剪辑工作台 UI 定稿落地：增加资产中心素材入口、缩略图时间线、音频波形、字幕块、播放头、基础工具栏和属性面板结构。
- M05 时间线基础工具补齐真实 `分割` 与 `删除` 动作：新增 Runtime 服务、HTTP 契约、前端 Runtime Client、Pinia Store 与工具栏事件联动。
- 首启启动检查页补齐共享样式与 Runtime 异常诊断面板，避免离线时退化为无样式裸页面。
- 素材池新增 `分镜 / 配音 / 字幕 / 资产` 来源视图，资产来源通过 Runtime Client 读取 `GET /api/assets` 后按当前项目过滤。
- 时间线布局收敛为宽屏三栏加底部多轨工作区，紧凑窗口按容器查询折叠，避免旧布局左右大空白与面板挤压。
- 右侧基础属性面板按片段信息、时间参数、素材来源、预检提醒与默认折叠的 AI 粗剪建议组织。
- 更新 M05 Runtime 调用说明、布局契约测试、页面回归测试和版本镜像。

## 0.4.5 - 2026-05-14

### M05 AI 剪辑工作台与全局布局分型

- 新增 M05 创作链路汇入能力，支持把脚本、分镜、配音与字幕聚合为受管时间线轨道，并保留手动轨道边界。
- Runtime 新增 `workspace.timeline.assemble` 契约、服务层与测试，前端通过统一 Runtime Client 和 Pinia store 消费，不在组件中直连接口。
- AI 剪辑工作台参考基础剪辑软件布局重排为素材池、9:16 播放器、基础属性、基础工具和时间线区域，补齐空态、预检、汇入状态和保存反馈。
- 建立全局页面布局分型：`editor / workspace / queue / management` 全宽铺开，`dashboard / settings` 放宽到 1680px。
- 账号管理和设备与工作区管理改为 `management` 页面类型，左侧对象列表控制在 320-420px，右侧详情区自适应，紧凑窗口自动单列。
- 更新 PRD、UI 设计真源、Runtime API 文档、项目状态和 Superpowers 计划 / 规格记录，并补齐前后端契约、布局契约与浏览器宽屏 / 紧凑抽查。

## 0.4.4 - 2026-05-12

### 字幕对齐中心收口

- 字幕生成默认绑定当前项目最新可用配音轨，生成结果会记录 `sourceVoice` 快照，并在配音段已有时间码时沿用对应字幕时间码。
- 字幕对齐中心新增脚本文案表格，将结构化脚本段落转换为段号、时间、目标、字幕文案和时间码状态，便于生成前核对。
- 字幕对齐页移除重复的脚本文案摘要卡，字幕校对台收敛为纯预览画面窗口，并补齐右侧时间码与样式控件的可编辑回归。
- 字幕预览窗口改为 9:16 手机画幅，样式面板新增行距和字幕框宽度，预览字幕支持拖动微调位置。
- 字幕生成和旧轨道加载会清理 `S01 0-5s` 类段号时间前缀，按脚本文案表格行生成，避免 5 行脚本变成 7 段字幕。
- 分镜与脚本结构化表格增加横向阅读宽度，避免英文长句或拍摄说明被压成过窄竖排。
- 脚本生成 Prompt 明确“观众文案按目标语言、制作说明保持中文”，分镜生成和展示链路清理“延续上句 / 同上”占位文案。
- 前端字幕 store 统一读取脚本文档、字幕轨和配音轨，生成字幕时通过 Runtime 契约传入 `sourceVoiceTrackId`，不在组件内直接请求。
- 更新 Runtime API 契约、Superpowers 计划 / 规格记录和相关 Pytest / Vitest 覆盖。

## 0.4.3 - 2026-05-11

### 火山豆包 TTS2 与配音中心收口

- 接入火山豆包语音合成模型 2.0，固定使用 `seed-tts-2.0`，移除 1.0 模型入口，并通过官方 OpenAPI 同步 2.0 音色列表。
- AI 与系统设置新增火山豆包语音的 Access Token、App ID、Access Key ID、Secret Access Key 与 Region 配置入口，统一写入配置总线和 SecretStore。
- 配音中心支持真实音频流播放、整段预览与当前段落预览；生成中状态、任务进度、错误提示和音色列表滚动交互已补齐。
- Runtime 新增配音音频资源接口，修复火山 SSE 空音频解析、中文文本与非中文音色误配提示，并补齐对应契约测试、单元测试和前端回归测试。
- 更新 Runtime API、项目状态、README 与 Superpowers 计划 / 规格记录，版本真源提升到本轮发布号并同步桌面壳与 Python Runtime 镜像版本。

## 0.4.2 - 2026-04-22

### V2 前后端联调收口

- 同步 V2 后端模块主线 `3.1 -> 3.16` 与工程化尾项，补齐 `config.changed`、`ai-capability.changed`、Provider 模型远端刷新、FastAPI lifespan 启动链路。
- 同步前端 Runtime 事件消费层、`config-bus` / `ai-capability` store 回流与设置页 Provider 管理联动，打通模型刷新、健康刷新与配置状态回流主线。
- 更新 `docs/PROJECT-STATUS.md`、`docs/RUNTIME-API-CALLS.md` 与实施计划文档，收口当前分支的 V2 落地口径。

## 0.4.1 - 2026-04-20

### V2 文档治理

- 新增 V2 产品 / 前端 / 后端三件套：`docs/V2-PRODUCT-REQUIREMENTS-2026-04-20.md`、`docs/V2-FRONTEND-REQUIREMENTS-2026-04-20.md`、`docs/V2-BACKEND-REQUIREMENTS-2026-04-20.md`，作为下一阶段需求收口入口。
- 将本轮 8 条真实用户体验反馈按前后端切分，登记为 `F-01 ~ F-08`（前端）与 `B-01 ~ B-06`（后端），两侧建立交叉索引。
- 回写 V2 入口到 `docs/PRD.md`（第 17-19 节）与 `docs/UI-DESIGN-PRD.md`（第 16 节）；将 `docs/BACKEND-REQUIREMENTS-2026-04-17.md` 标注为历史快照。
- 刷新 `docs/PROJECT-STATUS.md`：扩展真源关系表、新增 16 页状态表的 V2 列、在 V2 章节补齐回流闭环与退役规则。
- 归档旧 Superpowers 计划与规格（20 份 plan + 15 份 spec）到历史位置，仓库内统一收敛到 V2 流程。
- 新增 `docs/superpowers/plans/2026-04-20-v2-product-doc-pack.md` 与配套 spec，作为本轮文档治理的实施记录。

### 分支治理

- 合并完成的 codex/* 本地与远端分支统一清理，仓库仅保留 `main`。

## 0.4.0 - 2026-04-19

### 全站 UI 深度精修 (Precision Sculpting)

- 完成了全站 16 个核心页面的像素级视觉对齐与物理动效补齐。
- 引入全站 `:active` 缩放反馈与弹性滑动动效 (`<transition-group>`)，大幅提升桌面端操控质感。
- 实现了统一的 AI 任务反馈系统 (`ai-flow-bar`)，全站 AI 任务处理状态可视化。
- 修复了资产中心与视频拆解中心的视频预览黑屏问题，引入强制首帧抓取机制。
- 深度精修了 M05 AI 剪辑工作台，实现了多轨时间线弹性流转、AI 魔法剪流光反馈及工业级布局加固。

### 模块改进

- **M02 创作总览**：优化了极光背景混合模式，补齐了最近项目删除动效与原生确认弹窗。
- **M09 资产中心**：重构了预览引擎，支持动态路径解析与原生文件选择器异步加载，杜绝了非 Tauri 环境下的启动崩溃。
- **M10-M15 执行层**：统一替换了所有原生 Input 组件，并补齐了任务队列的平滑补位动效。
- **系统设置**：接通了原生文件夹选择与日志目录唤起功能。

### 技术债清理

- 彻底清理了误用的 CSS 占位符，加固了剪辑台等复杂页面的布局稳定性。
- 规范了全站滚动条样式，采用超细隐形设计，保持界面极客感。

## 0.3.4 - 2026-04-19

### Runtime 契约与设置收口

- 补齐 `review / workspace / subtitles / video-deconstruction / voice` 的后端契约差口，并同步更新前端运行时调用类型。
- 新增 AI Provider 文本适配层与 OpenAI TTS 适配实现，补上能力配置、健康检查、错误信封与相关契约测试。
- 修正授权激活、Runtime 自检、视频拆解阶段阻塞、配音波形摘要和字幕本地生成的真实返回路径。

### 文档同步

- 更新 `docs/RUNTIME-API-CALLS.md`，使接口地址、错误码、返回示例和当前代码保持一致。
- 根真源版本提升到 `0.3.4`，桌面壳与 Python Runtime 镜像版本继续通过同步脚本维护。

## 0.3.3 - 2026-04-17

### Main 分支收口

- 将 `codex/m05-ai-editing-workspace-runtime-ui` 合并到 `main`，结束本地主干之外的 M05 工作台并行实现。
- 提交桌面开发启动链路修正、项目状态文档和 Stitch CLI 辅助脚本，清理 `main` 上的脏工作树。

### M05 AI 剪辑工作台

- 新增 `/api/workspace` 时间线草稿读取、创建、保存和 AI 命令阻断态的 Runtime 契约。
- 将 AI 剪辑工作台拆分为页面壳、workspace 模块、Pinia store 和样式文件，移除页面内静态假轨道和假 AI 结果。

### 文档与版本统一

- 将根 `README.md`、`apps/desktop/README.md`、`docs/PROJECT-STATUS.md`、`docs/RUNTIME-API-CALLS.md` 统一到合并后的最新状态口径。
- 根真源已提升到当轮发布号，镜像清单继续通过同步脚本维护。

## 0.3.2 - 2026-04-16

### 开发态启动链路

- 统一根 `desktop:tauri:dev` 与 Tauri `beforeDevCommand` 的调用方式，避免开发态命令口径分裂。
- `npm run app:dev` 新增现有 Runtime / 前端开发服务器复用逻辑，减少 8000 与 1420 端口被占用时的误报。

### 文档状态收口

- 新增 `docs/PROJECT-STATUS.md`，按 16 页结构记录当前实现、Runtime 接线、验收记录和待收口问题。
- 更新根 `README.md` 当前边界，明确 TaskBus、视频导入、配音中心、资产中心和 M09-M15 Runtime 页面接线已进入阶段性基线。
- 更新 `apps/desktop/README.md` 当前职责与页面边界，使桌面端说明和项目状态文档保持一致。
- 标记 Provider Secret UI、真实 OpenAI 调用链路、真实 TTS Provider、字幕对齐、时间线、渲染与发布执行层仍需后续计划推进。

### 验证

- 文档级 UTF-8 读取检查
- 文档关键术语一致性检查

## 0.3.1 - 2026-04-15

### 基础问题收口

- 视频导入后台处理接入统一 TaskBus，前端通过中心化任务状态消费进度与终态。
- 补齐 M09-M15 Runtime client、Pinia store 与后端 API 契约测试，覆盖资产、账号、设备工作区、自动化、发布、渲染与复盘基础链路。
- 修复设备工作区、自动化任务、发布计划和渲染任务删除接口的空响应问题，统一返回 Runtime JSON 信封。
- 资产中心与账号管理 store 增加可断言错误态，为页面展示中文错误反馈打基础。

### 验证

- `npm --prefix apps/desktop run test`
- `npm --prefix apps/desktop run build`
- `venv\Scripts\python.exe -m pytest tests/runtime -q`
- `venv\Scripts\python.exe -m pytest tests/contracts -q`

## 0.2.0 - 2026-04-12

### 合并基线

- 本地 `main` 已包含 `codex/version-source-sync`、`codex/foundation-config-logging`、`codex/license-wizard-foundation` 与 `codex/creative-chain-foundation` 的提交链。
- 本轮将 `codex/offline-license-foundation` 的未提交改动整理为新的可追溯基线，后续从 `main` 继续推进。

### 新增能力

- 新增离线一机一码授权链路，支持机器码生成、授权码签名校验、授权状态持久化与中文错误反馈。
- 新增授权机工具与 Windows BAT 入口，可输入客户机器码并生成授权码。
- 新增开发态一键启动入口，根命令可自动启动 Runtime、等待健康检查并启动 Tauri 桌面应用。
- 新增首启 BootstrapGate，启动时先展示加载、授权和初始化前置页，避免用户面对空白界面等待。
- 新增 Stitch CLI UI 流程文档与设计稿目录，首页和全局壳层已按本地 AI 视频创作指挥舱方向重做。

### 改进

- 创作总览、全局壳层、Detail Panel、Status Bar 与 16 页占位入口统一中文文案和状态表达。
- Runtime 授权错误、启动脚本、版本脚本与文档输出修正为可读中文。
- 根版本真源继续由 `package.json` 维护，桌面 Tauri、Rust 与 Python manifest 版本由同步脚本镜像。
- 桌面测试目录迁移到 `apps/desktop/tests`，前端测试配置同步更新。

### 清理

- 删除仓库根 `package-lock.json`，桌面端依赖锁定迁移到 `apps/desktop/package-lock.json`。
- 删除已不再作为项目内置插件维护的 `plugins/superpowers` 与旧 `tests/desktop` 路径。
- 本地代理配置目录 `.claude/` 与 `.codex/` 不纳入提交。
