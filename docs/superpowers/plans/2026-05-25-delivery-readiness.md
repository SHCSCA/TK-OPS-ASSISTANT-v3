# 2026-05-25 TK-OPS 交付可用性总推进计划

## 1. 目标与状态

目标：按 `docs/PRD.md`、`docs/UI-DESIGN-PRD.md`、`docs/ARCHITECTURE-BOOTSTRAP.md` 和 `AGENTS.md`，把 TK-OPS 推进到用户可安装、可启动、可完成核心创作链路、可获得真实反馈的交付状态。

当前结论：项目已有 16 页路由、桌面壳、Runtime API、测试基础和部分 AI / 视频拆解 / 时间线能力，但尚不能判定为可交付。主要差距集中在真实执行闭环、首启可用性、信息架构一致性、真实媒体输出、任务恢复、发布边界和证据化验证。

本计划是总推进计划。进入实现前，还需按仓库规则补齐对应设计规格 `docs/superpowers/specs/2026-05-25-delivery-readiness-design.md`，并按阶段拆分小步交付。

## 2. 文档真源

- 产品范围：`docs/PRD.md`
- UI 和交互：`docs/UI-DESIGN-PRD.md`
- 架构与目录：`docs/ARCHITECTURE-BOOTSTRAP.md`
- 工程约束：`AGENTS.md`
- 既有计划与规格：`docs/superpowers/plans/`、`docs/superpowers/specs/`

冲突处理原则：产品范围以 PRD 为准，视觉与壳层以 UI PRD 为准，目录与模型以架构文档为准，工程约束以 AGENTS.md 为准。若实现需要突破当前边界，先更新文档，再进入代码改动。

## 3. 子代理配置

每次开发前从 `.codex/agents` 选择合适 agent，并由主代理负责架构、审核和方向把控。

已用于本轮只读审计的 agent：

- 产品可交付审计：`.codex/agents/product-manager.toml`
- 体验与交互审计：`.codex/agents/design-ux-architect.toml`
- Runtime 架构审计：`.codex/agents/engineering-backend-architect.toml`
- 交付证据审计：`.codex/agents/testing-reality-checker.toml`

后续开发推荐 agent：

- 前端体验实现：`.codex/agents/engineering-frontend-developer.toml`
- 后端能力实现：`.codex/agents/engineering-backend-architect.toml`
- 最小变更落地：`.codex/agents/engineering-minimal-change-engineer.toml`
- 代码审核：`.codex/agents/engineering-code-reviewer.toml`
- 可用性验证：`.codex/agents/testing-reality-checker.toml`
- API 契约验证：`.codex/agents/testing-api-tester.toml`
- 证据收集：`.codex/agents/testing-evidence-collector.toml`

## 4. P0 验收门槛

达到可交付前，至少满足以下门槛：

1. 首启、许可证、目录初始化、Runtime 健康检查能走真实链路，并给出中文可恢复反馈。
2. 16 页路由、侧边栏分组和壳层结构与 UI PRD 保持一致。
3. 核心链路 `Project -> Script -> Storyboard -> Timeline -> VoiceTrack -> SubtitleTrack -> RenderTask` 至少有一条可验证主路径。
4. 视频拆解结果能回流到同一 Project，而不是形成孤立数据。
5. AI 能力调用必须经过统一 Provider / 能力接口，禁用、失败、超时和配置缺失都有可见反馈。
6. 渲染导出至少具备真实最小输出链路，不能只创建数据库任务。
7. 发布中心必须清楚区分“真实提交能力”和“发布前检查 / 待人工执行”边界，禁止把半闭环伪装成真实发布。
8. 长任务具备超时、取消、失败提示、重试和日志追踪；关键任务状态可恢复或明确提示不可恢复边界。
9. 桌面宽屏和紧凑窗口布局可用，不能被 Tauri 窗口配置直接阻断。
10. 前端、Runtime、契约、构建、启动和关键 UI 截图均有验证记录。

## 5. 已识别阻断项

### 5.1 产品和体验阻断

- M05 AI 剪辑工作台缺少真实视频 / 音频预览信心链路；当前 `/api/workspace/timelines/{timeline_id}/preview` 只返回 Runtime manifest，真实媒体预览必须等显式媒体契约落地，前端不得从片段 metadata 猜测媒体 URL。
- M05 紧凑窗口体验仍需收口，960 x 720 下必须保证大预览舞台、基础时间线和状态反馈可见，侧边栏抽屉不能长期遮挡主工作区。
- 部分 AI 行动入口处于禁用或半可用状态，缺少明确原因、恢复路径和任务反馈。
- 侧边栏分组仍偏旧结构，未完全遵循 UI PRD 的五组信息架构。
- 状态栏存在模拟延迟文案风险，违反真实状态原则。
- 原生确认框仍存在，和统一桌面体验不一致。
- 需要用 Playwright 或等价浏览器工具补齐桌面宽屏、紧凑窗口和关键页面截图证据。

### 5.2 Runtime 阻断

- 发布服务只生成 `receipt_pending`，缺少真实 TikTok / 浏览器执行器、回执拉取和失败恢复。
- 渲染服务主要落库，缺少 FFmpeg 最小输出链路。
- 自动化执行只生成摘要，缺少真实采集、回复、同步或校验执行器。
- 浏览器实例只改状态，缺少真实进程、端口、PID、健康探测和关闭恢复。
- 全局任务总线为内存态，重启后任务丢失。
- 视频转录 Provider 未完整落地，部分路径仍提示真实协议未接入。
- 账号刷新不是平台校验，只是本地 readiness 更新。
- 多个服务文件超过 1000 行，需要在功能推进中逐步拆分。

### 5.3 验证阻断

- 当前工作区存在大量已修改和未跟踪文件，需在每阶段开始前确认改动归属。
- Runtime 依赖环境和测试命令需要重新验证，不能只沿用旧结论。
- Tauri 打包、桌面启动和端到端主链路尚未形成完整证据。

## 6. 阶段计划

### 阶段 0：证据基线与环境收口

目标：先建立“当前能跑到哪里”的真实证据，避免在不确定环境上继续叠加改动。

范围：

- 记录工作区改动归属和未跟踪文件。
- 验证 Node、Python、Rust / Tauri、FFmpeg / ffprobe 是否可用。
- 跑前端测试、Runtime 相关测试、契约测试、构建命令和启动命令。
- 输出失败清单，不把失败伪装为通过。

推荐 agent：

- `.codex/agents/testing-reality-checker.toml`
- `.codex/agents/testing-evidence-collector.toml`

验证命令候选：

```powershell
git status --short
npm --prefix apps/desktop test
npm --prefix apps/desktop run build
python -m pytest tests/runtime tests/contracts
npm run app:dev
```

### 阶段 1：信息架构与 UI 真实反馈

目标：用较低后端依赖的改动，先修复用户第一眼可感知的“不可信”和“不一致”问题。

范围：

- 路由和侧边栏分组对齐 UI PRD 五组结构。
- 桌面窗口配置支持紧凑窗口验证，不让最小宽度阻断 960-1199 区间。
- 状态栏移除模拟延迟，改为 Runtime 真实状态、未知态或诊断态。
- M05 预览区明确 Runtime manifest、结构预览与真实媒体预览边界：当前 manifest 只驱动结构预览；真实媒体必须来自 Runtime 显式媒体契约；无真实媒体时显示中性结构预览、中文错误态或下一步引导。
- M05 时间线将 AI managed 分镜、配音、字幕轨道按同一目标时长判定同步状态，后端组装阶段尽量按 reference timing 对齐，无法对齐时通过预检或同步标记暴露。
- M05 紧凑窗口下保留大预览舞台、9:16 / 16:9 切换和基础时间线可见性，素材池 / 属性区可折叠或顺序下移。
- M05 AI 行动入口补齐禁用原因、任务状态、失败反馈和重试入口。
- 将关键原生确认框替换为统一 UI 反馈组件或已有确认模式。

推荐 agent：

- `.codex/agents/design-ux-architect.toml`
- `.codex/agents/engineering-frontend-developer.toml`
- `.codex/agents/engineering-minimal-change-engineer.toml`
- `.codex/agents/testing-reality-checker.toml`

主要文件地图：

- `apps/desktop/src/app/route-manifest.ts`
- `apps/desktop/src/layouts/AppShell.vue`
- `apps/desktop/src/components/shell/ShellSidebar.vue`
- `apps/desktop/src/components/shell/ShellStatusBar.vue`
- `apps/desktop/src/pages/AIEditingWorkspacePage.vue`
- `apps/desktop/src/modules/workspace/*`
- `apps/desktop/src-tauri/tauri.conf.json`
- `tests/desktop/*`

验收：

- 前端测试通过。
- 宽屏和紧凑窗口关键截图无重叠、无假状态、无英文占位。
- 侧边栏五组结构与 UI PRD 一致。
- M05 没有把结构预览伪装成真实视频预览。

### 阶段 2：首启、配置总线和 Runtime 就绪

目标：用户首次打开能完成许可证、目录、Runtime 健康检查和 AI 配置诊断。

范围：

- 首启向导使用真实 Runtime readiness。
- 目录初始化、许可证校验、Runtime 自检、AI 能力检查统一反馈。
- 设置页能力状态与配置总线一致，不出现页面内散落配置。
- AI 能力禁用时，任务发起前给出明确中文错误，不进入后台后才失败。

推荐 agent：

- `.codex/agents/engineering-backend-architect.toml`
- `.codex/agents/engineering-frontend-developer.toml`
- `.codex/agents/testing-api-tester.toml`

主要文件地图：

- `apps/desktop/src/modules/settings/*`
- `apps/desktop/src/app/runtime-client.ts`
- `apps/desktop/src/types/runtime.ts`
- `apps/py-runtime/src/services/settings_service.py`
- `apps/py-runtime/src/services/ai_capability_service.py`
- `apps/py-runtime/src/services/ai_text_generation_service.py`
- `tests/runtime/*`
- `tests/contracts/*`

验收：

- 无配置绕过统一入口。
- 禁用 AI 能力时前端可见、后端有日志、任务不误入队列。
- Runtime 健康状态能在状态栏和设置页同步体现。

### 阶段 3：核心创作主链路可用

目标：用户至少能从项目进入脚本、分镜、时间线、配音 / 字幕和任务状态，形成可验证主路径。

范围：

- 验证并补齐项目主链数据一致性。
- 视频拆解结果能应用到当前 Project。
- M05 时间线编辑、选择、移动、裁剪、吸附、撤销 / 重做和保存状态可用。
- 任务完成后刷新项目、时间线和相关缓存。

推荐 agent：

- `.codex/agents/product-manager.toml`
- `.codex/agents/engineering-frontend-developer.toml`
- `.codex/agents/engineering-backend-architect.toml`
- `.codex/agents/testing-reality-checker.toml`

主要文件地图：

- `apps/desktop/src/pages/*`
- `apps/desktop/src/modules/workspace/*`
- `apps/desktop/src/modules/video-deconstruction/*`
- `apps/py-runtime/src/services/workspace_service.py`
- `apps/py-runtime/src/services/video_deconstruction_service.py`
- `tests/desktop/*`
- `tests/runtime/*`

验收：

- 主链路测试覆盖正常、空态、失败和重试。
- UI 不展示假业务数字。
- 数据变化后缓存、队列和状态刷新一致。

### 阶段 4：真实渲染最小闭环

目标：至少提供一个真实可验证的本地输出文件能力。

范围：

- 接入 FFmpeg / ffprobe 诊断。
- 从 Project / Timeline / Asset 生成最小输出文件。
- 任务具备进度、取消、失败、重试和输出文件校验。
- Runtime 返回统一信封和中文错误。

推荐 agent：

- `.codex/agents/engineering-backend-architect.toml`
- `.codex/agents/engineering-ai-engineer.toml`
- `.codex/agents/testing-api-tester.toml`
- `.codex/agents/testing-reality-checker.toml`

主要文件地图：

- `apps/py-runtime/src/services/render_service.py`
- `apps/py-runtime/src/media/*`
- `apps/py-runtime/src/repositories/*render*`
- `apps/py-runtime/src/schemas/renders.py`
- `apps/desktop/src/pages/RenderExportPage.vue`
- `tests/runtime/test_render_service.py`
- `tests/contracts/*render*`

验收：

- 成功任务产生真实输出文件。
- 失败任务有错误码、日志和 UI 提示。
- 重试不制造重复脏状态。

### 阶段 5：发布、浏览器实例与自动化真实边界

目标：发布中心和自动化中心不再把占位状态伪装为真实完成；真实执行能力分层落地。

范围：

- 浏览器实例具备真实进程、profile、PID、端口、健康检查和停止恢复。
- 发布中心至少完成真实发布前检查；若暂不自动提交 TikTok，必须明确标注人工执行边界。
- 自动化中心把可执行动作、待接入动作和诊断状态分清。
- 执行日志、回执、失败原因和重试路径可追踪。

推荐 agent：

- `.codex/agents/automation-governance-architect.toml`
- `.codex/agents/engineering-backend-architect.toml`
- `.codex/agents/engineering-pc-host-engineer.toml`
- `.codex/agents/testing-reality-checker.toml`

主要文件地图：

- `apps/py-runtime/src/services/device_workspace_service.py`
- `apps/py-runtime/src/services/publishing_service.py`
- `apps/py-runtime/src/services/automation_service.py`
- `apps/desktop/src/pages/PublishingCenterPage.vue`
- `apps/desktop/src/pages/AutomationCenterPage.vue`
- `tests/runtime/*publishing*`
- `tests/runtime/*device*`
- `tests/contracts/*`

验收：

- 浏览器实例不是纯状态翻转。
- 发布状态不再以 `receipt_pending` 代表真实完成。
- 用户能明确知道哪些动作已经执行、哪些需要人工介入。

### 阶段 6：任务总线、迁移治理和大文件拆分

目标：把可交付能力背后的工程风险收口。

范围：

- 持久化任务总线，支持重启恢复、超时、取消、重试和广播一致。
- Alembic 迁移治理替代隐式 `create_all` / repair 作为升级主路径。
- 拆分超大服务文件，优先处理 `ai_capability_service.py`、`voice_service.py`、`video_deconstruction_service.py`、`workspace_service.py`。
- API 文档更新，补齐地址、方法、参数、返回、错误码和示例。

推荐 agent：

- `.codex/agents/engineering-software-architect.toml`
- `.codex/agents/engineering-backend-architect.toml`
- `.codex/agents/engineering-database-optimizer.toml`
- `.codex/agents/engineering-technical-writer.toml`
- `.codex/agents/engineering-code-reviewer.toml`

验收：

- 服务拆分后现有契约不降级。
- 迁移测试覆盖旧库升级。
- 文档和代码契约同步。

## 7. 第一批建议执行切片

建议第一批只做“阶段 1：信息架构与 UI 真实反馈”。原因：

- 用户第一眼能感知到交付质量。
- 后端依赖较低，适合在当前工作区存在大量改动时先小步收口。
- 能快速消除旧导航、假延迟、结构预览伪装和紧凑窗口不可测等明显体验问题。
- 可通过前端测试、构建和截图形成明确证据。

第一批完成后，再进入阶段 2 和阶段 3，避免同时打开渲染、发布、任务总线等高耦合后端大改。

## 8. 回退点

- 每阶段只改阶段内文件，不做无关重构。
- 每阶段开始前记录 `git status --short`，避免覆盖用户或其他代理改动。
- 若测试环境缺依赖，先记录失败原因并补环境说明，不伪称通过。
- 若发现实现范围超过计划，先更新计划 / 规格，再继续。

## 9. 审批门

本计划通过后，下一步创建设计规格：

`docs/superpowers/specs/2026-05-25-delivery-readiness-design.md`

设计规格通过后，优先进入第一批执行切片：

`阶段 1：信息架构与 UI 真实反馈`
