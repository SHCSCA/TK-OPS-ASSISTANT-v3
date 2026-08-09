# TK-OPS 生产链闭环总路线图

> 日期：2026-08-02
> 状态：P0-G 计划与规格已批准并进入 G0；P0-H / P0-I 已补齐路线契约，仍待各自实施批准
> 依据：`docs/audits/2026-08-02-production-chain-closure-audit.md`
> 目标：交付账号定位驱动、AI 深度接入、可批量生产且可由真实 Windows 制品验收的 TikTok 桌面工作台

## 1. 当前真实位置

项目不是“只差几个 UI 细节”，也不是需要推倒重来。已经可复用的是 Tauri + Vue + Runtime 骨架、许可证基础、账号基础、AI 配置对象和十三 Route 页面树。尚未闭合的是三个连续层级：

```text
验收可信度
  ↓
P0-G 账号执行基础（G0-G7）
  ↓
P0-H AI 配置到真实执行
  ↓
P0-I 账号级创作、批量生产、资产、发布与复盘
```

任何上层阶段都不得用 seed、假数据或 legacy 路由绕过下层。P0-I 可以先用确定性 fake provider 做契约测试，但最终验收必须至少有一个受支持 Provider 的真实调用证据。

## 2. 最终目标与用户主链

最终用户在一个免安装 Windows 应用内完成：

```text
安装/免安装启动与激活
→ 新建 TikTok 账号工作区
→ 配置定位、品牌和账号知识库
→ 选择受控工作目录并建立浏览器执行环境
→ 用户监督登录 TikTok
→ 配置并验证 AI Provider / Model / Route / Prompt / Recipe
→ 新建选题 → 生成/编辑脚本 → 分镜 → 资产/视频拆解
→ 形成批次与多个 ContentVariant
→ 配音/字幕/CompositionSpec/渲染
→ 内容库沉淀 → 用户确认发布 → 复盘
```

切换左下账号后，定位、知识、内容计划、脚本、分镜、批次、资产、任务、发布配置和复盘全部随账号切换；跨账号复用必须显式复制。

## 3. 阶段依赖和批准方式

| 阶段 | 依赖 | 核心结果 | 是否需要独立规格批准 |
| --- | --- | --- | --- |
| G0 验收真源 | 无 | 测试、E2E、制品证据可信 | 纳入 P0-G 规格 |
| G1 壳层 | G0 基线 | 账号切换器与紧凑窗口可用 | 纳入 P0-G 规格 |
| G2 受控目录 | G0 | 账号工作区 rootRef 真实可用 | 纳入 P0-G 规格 |
| G3 执行环境 | G2 | UI 从零创建并安全管理真实三对象 | 纳入 P0-G 规格 |
| G4 连接与登录 | G1、G3 | 账号连接、监督登录、深链闭环 | 纳入 P0-G 规格 |
| G5 Runtime 韧性 | G0，可与 G2/G3 部分并行设计 | Sidecar 重启恢复、启动前诊断 | 纳入 P0-G 规格 |
| G6 任务与一致性 | G3、G4、G5 | 长任务、事务、事件和归档完整 | 纳入 P0-G 规格 |
| G7 制品验收 | G0-G6 | 当前 EXE/ZIP 可复现并完成真实 GUI 主链 | 纳入 P0-G 规格 |
| P0-H AI 真执行 | G2、G4、G6 | AI 配置和知识引用驱动真实任务 | 独立 plan/spec |
| P0-I 创作生产链 | P0-H | 八个 pending 页面逐段替换为生产能力 | 独立 plan/spec，按纵切片阶段批准 |

同一问题只允许一个主整改阶段；其他阶段只能消费已完成契约，不能复制修复逻辑。

## 4. P0-G：账号执行基础

P0-G 的详细执行真源是：

`docs/superpowers/plans/2026-08-02-account-workspace-execution-environment-closure.md`

### G0 验收真源

**阶段成果**：

- 首启 E2E 使用匹配的 Issuer 私钥 / Runtime 公钥，并遵循机器码只读交互。
- 生产 E2E 不再调用 `seedExecutionBinding`。
- 94 个 Desktop 测试文件被明确分为 active / compatibility / retired；默认门禁覆盖 active 集，意外路由 warning 失败。
- 当前制品 manifest 自动绑定版本、Git 状态、测试、配置摘要、大小和 SHA256。
- 历史 P0-F 证据保留但标记 stale snapshot。

**验收命令草案**（规格阶段锁定脚本名；当前未宣称执行）：

```powershell
npm --prefix apps/desktop run test:active
npm --prefix apps/desktop run typecheck
Push-Location apps/desktop; npx playwright test -g "真实首启链完成授权且不注入执行环境"; Pop-Location
```

### G1 壳层和账号切换器

**阶段成果**：

- 无页面级横向滚动；账号菜单视口内完整呈现。
- 切换、搜索、空态、添加和管理入口使用统一反馈。
- Light / Dark 和两档 PC 窗口有截图与几何断言。

**验收证据**：组件交互测试、`scrollWidth/clientWidth`、菜单 bounding box、1440×900 与 1180×760 截图。

### G2 受控账号工作目录

**阶段成果**：

- 原生目录选择器 → Rust 注册 → `rootRef` → Runtime resolver 纵向可用。
- DeviceWorkspace 目录和 Runtime 全局数据根在 UI、API、文档、生命周期上分开。
- 目录取消、无权限、危险根、重解析点、失效和重授权可恢复。
- 最小 asset scope，不退回开放整个用户目录。

**验收证据**：Rust 单元、Runtime resolver、Desktop bridge、重启恢复和受限路径集成测试。

### G3 执行环境、资格和进程所有权

**阶段成果**：

- 新 v1 provisioning 服务从 UI/API 创建同账号 `DeviceWorkspace`、`BrowserInstance`、`ExecutionBinding`。
- 候选查询和绑定命令共享资格服务，绑定事务内重验。
- 浏览器进程具有跨 Runtime 重启可验证的所有权；PID 复用不误杀。
- 并发幂等、超时、取消、回滚和外部副作用补偿可观察。
- legacy `/api/devices/*` 停止写入，字段错位数据只做可审计迁移。

**验收证据**：新鲜 DB、无 seed、跨账号拒绝、并发、故障注入、Runtime 重启和 PID 复用测试。

### G4 账号连接、监督登录和动作路由

**阶段成果**：

- 向导从空候选直接创建、选择、绑定、登录、探测到 valid。
- 用户在可见浏览器中监督登录；系统不保存明文凭据、不绕过验证码。
- `unknown/login_required/login_in_progress/probing/valid/expired/revoked` 会话状态明确。
- typed action 携带 accountId、route、wizardStep、taskId、logId、returnTo；错误账号和未知动作可见失败。
- 账号身份可编辑，修订冲突可恢复。

**验收证据**：正常、取消、登录超时、会话过期、登出、跨账号深链和 returnTo E2E。

### G5 Runtime 韧性和启动前诊断

**阶段成果**：

- supervisor generation 变化驱动 Desktop 连接、缓存和请求失效并重新握手。
- Runtime 未启动时仍可复制日志摘要和导出脱敏诊断包。
- 机器码分项采集、稳定降级、算法版本化并兼容既有许可证。
- 重启、退避、超时来自全局配置总线且有真实 consumer。

**验收证据**：Sidecar 强制崩溃/新端口/token 恢复，受限 Windows 机器码矩阵，旧许可证回归。

### G6 长任务、事务和事件

**阶段成果**：

- provisioning、检查、登录 probe、启动/停止、删除和归档统一任务终态、进度、取消、超时、重试、日志。
- WebSocket 实时更新并有轮询 fallback；应用重启后恢复任务投影。
- DB 事务、outbox 和外部补偿一致；账号归档不会遗留受控进程、会话和任务。
- 失败任务在工作台和详情页提供真正可执行的 retry/view log/cancel 动作。

**验收证据**：全部终态、断网、重启、重复事件、故障注入、补偿失败和归档清理测试。

### G7 Windows 制品验收

**阶段成果**：

- Runtime sidecar、NSIS 和免安装运行包由仓库脚本可复现。
- manifest 和 SHA256 对应当前代码及测试；失败构建不覆盖 current。
- 可见 GUI smoke 验证 WebView、激活、Runtime ready、标准窗口按钮、单实例聚焦、优雅关闭和重启恢复。
- 干净 Windows 数据目录走完账号执行主链。
- 明确“免安装运行包”是否包含数据便携；当前未实现前不得宣传为完全 portable data。

**验收证据**：干净机运行日志、截图、manifest、哈希、测试报告与回退制品。

## 5. P0-H：AI 配置、知识引用到真实执行

P0-H 在 P0-G 稳定后另立详细 plan/spec。它不扩展页面树，负责让现有“定位与知识”和“AI 与系统设置”从管理对象变为真实能力入口。

### H1 Provider Profile 完整管理

- 新增/编辑 base URL、credential_ref、超时、额外参数、启停、发现、验证和轮换凭据。
- 凭据由安全存储管理，UI 只显示掩码/引用；日志统一脱敏。
- Provider 验证分成网络可达、鉴权有效、模型发现、能力实测，不用静态声明代替。

### H2 Model / Route / Prompt / Recipe 依赖图

- 定义能力路由解析顺序、fallback、超时、重试和成本/并发边界。
- Prompt 有版本、用途、输入输出 schema 和回滚；账号 Recipe 激活不可变快照。
- dependency issue 提供结构化 repair action，复用 G4 typed router，修复后 returnTo 重新验证。

### H3 受控知识文件引用

- 复用 G2 原生选择和 rootRef 基础，支持视频、图片、文档的账号级引用。
- 导入生成 Asset/KnowledgeSource 和索引任务，不复制或覆盖源文件，失败可重试/取消。
- 只允许自有、公共领域或已获授权素材；下载/去水印不绕过登录、DRM、付费墙或访问控制。

### H4 统一 AI Execution Gateway

- v1 Provider / Model / Route / Prompt / Recipe 成为唯一配置真源。
- legacy `AITextGenerationService` 等通过适配层消费激活快照，逐步移除双配置装配。
- 每次 AIJob 固化 `account_id`、capability、provider/model route、prompt version、recipe version、knowledge snapshot、输入哈希、耗时、token/成本、错误和重试。
- 所有 AI 长任务接入 G6 生命周期。

### H5 配置总线消费矩阵

- 每个配置键必须有 owner、validator、consumer、热更新策略、日志和测试。
- 无 consumer 的键不得继续以“已支持”显示；requiredCapabilities 在保存时验证并规范化。

### P0-H 验收

```text
系统配置 Provider + 凭据
→ 发现并验证真实模型
→ 建立 Script Route + Prompt
→ 当前账号激活 Recipe
→ 导入一个受控知识文件
→ 发起真实 AIJob
→ 可查看采用快照、进度、日志与结果
→ 修改配置不改变历史任务快照
```

至少一个受支持 Provider 跑通真实纵向调用；其余 Provider 可用契约测试，不得声称全部实测。

### P0-H 完整依赖与接口边界

前置依赖：G2 受控文件引用、G4 typed action 与账号会话、G6 任务/事件/补偿全部通过；Provider Secret Store、账号 Recipe 和 v1 配置修订保持可用。P0-H 不依赖 P0-I 页面，可先通过独立执行 API 验收。

新增或收口的接口：

```text
PATCH /api/v1/ai-system/providers/{provider_id}
PUT   /api/v1/ai-system/providers/{provider_id}/credential
POST  /api/v1/ai-system/providers/{provider_id}/checks
POST  /api/v1/accounts/{account_id}/knowledge/sources/file-refs
POST  /api/v1/accounts/{account_id}/ai-executions
GET   /api/v1/accounts/{account_id}/ai-executions/{execution_id}
POST  /api/v1/accounts/{account_id}/ai-recipes/{version_id}/validate
POST  /api/v1/accounts/{account_id}/ai-recipes/{version_id}/activate
```

`POST ai-executions` 必须提交 capability、输入引用和 `If-Match` Recipe 修订；Runtime 固化 provider/model route、Prompt/Recipe/知识快照、配置修订与输入哈希后返回 `202 + taskId + executionId`。执行状态复用 G6 `RuntimeTask`，不得增加页面直连 Provider。

### P0-H 验证命令、失败恢复与回退

```powershell
python -m pytest tests/runtime/test_p0_h_ai_execution_gateway.py tests/runtime/test_p0_h_controlled_knowledge_file.py tests/contracts/test_p0_h_ai_execution_api.py -q
npm --prefix apps/desktop run test -- p0-h-provider-editor p0-h-recipe-repair p0-h-knowledge-file
Push-Location apps/desktop
npx playwright test -g "AI 配置与知识快照驱动真实执行"
Pop-Location
```

- Provider/凭据更新失败保留旧 credential_ref 与已激活路由；不覆盖可用配置。
- 文件摄取失败保留源文件和失败 KnowledgeSource，不静默写入快照。
- AI 执行失败保留不可变快照、taskId、logId 和可重试输入；配置变化不重写历史。
- 回退时关闭 execution gateway 写入口并恢复旧只读配置视图；数据库加法对象保留，明文凭据永不回流。

## 6. P0-I：账号级创作、批量生产与运营闭环

P0-I 以固定主链为模型真源：

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

每个账号级实体显式含 `account_id`；脚本/分镜/知识/Recipe 采用不可变版本快照；不重新引入手动多轨剪辑工作台。

### I1 脚本与选题

- 新建 ContentPlan / ContentItem，复用账号定位、BrandKit、知识快照和 Recipe。
- 支持人工新建、AI 候选、批量选择、编辑、版本、审核与退回。
- 清楚区分“选题池”和“单视频制作链”，不把批量生产提前到拆解页。

**阶段成果**：用户可在当前账号真实新建选题，并生成/编辑一个版本化脚本。

### I2 分镜规划

- Script version 明确派生 Storyboard version；镜头包含目的、画面、台词/字幕、素材需求、时长和生成策略。
- 从分镜继续创建 ProductionBatch 或单条 ContentVariant，不在分镜后形成死路。
- 支持镜头级重生成与版本选择，不实现手动多轨时间线。

**阶段成果**：选题 → 脚本 → 分镜 → 创建生产项连续可达。

### I3 视频拆解

- 真实 VideoAnalysisJob 输出轻松阅读的表格：时间段、脚本文案、关键词、关键帧、内容结构。
- 内容结构总结 Hook/展开/证据/CTA、节奏、镜头、语言和画面特点，并生成可编辑 tags。
- 用户明确选择“生成脚本新版本”“生成分镜新版本”或“写入账号知识库”，不得静默覆盖。

**阶段成果**：拆解成为创作输入工具，不是批量生产的隐式前置。

### I4 批量生产与自动合成

- 从 ContentItem/Storyboard 选择多个 variant 策略，形成 ProductionBatch。
- Image/Video/TTS/Subtitle Provider 通过 P0-H gateway 调用。
- `CompositionSpec` 表达自动合成；支持成片预览、镜头级重生成、版本选择、渲染失败恢复。
- 队列提供进度、并发、取消、重试、日志和账号隔离。

**阶段成果**：一个账号可从多个选题批量生成可审阅的视频版本。

### I5 内容库与媒体工具

- 内容库按视频、图片、音频、文档等真实资产分类，显示来源、版权/授权、版本、关联内容项和任务。
- 下载、转码、抽帧、去水印等轻量工具只产生新资产，不覆盖源文件。
- 下载/去水印先要求权利确认，不绕过 DRM、登录和访问控制。

**阶段成果**：生产输出和外部授权素材成为当前账号可追溯资产。

### I6 发布与复盘

- V1 优先用户确认发布；自动化必须基于真实连接、会话、执行环境和平台限制。
- PublishTask 记录目标账号、内容版本、时间、结果、平台响应和失败恢复。
- 复盘只展示真实采集数据；无数据使用中性空态，不制造播放量或增长数字。
- 复盘洞察可显式生成新 ContentPlan/知识版本，保持来源链。

**阶段成果**：内容从创作到发布结果和下一轮选题形成可审计闭环。

### P0-I 完整依赖与接口边界

前置依赖：P0-H 至少一个真实 Provider 纵向执行通过；G4 账号上下文、G6 任务事件、G7 当前制品验收可复用。I1→I6 按纵切片依赖，后一片不能用假对象绕过前一片。

正式资源接口：

```text
GET/POST /api/v1/accounts/{account_id}/content-plans
GET/POST /api/v1/accounts/{account_id}/content-items
GET/POST /api/v1/accounts/{account_id}/content-items/{item_id}/scripts
GET/POST /api/v1/accounts/{account_id}/content-items/{item_id}/storyboards
POST     /api/v1/accounts/{account_id}/video-analyses
POST     /api/v1/accounts/{account_id}/video-analyses/{analysis_id}/applications
GET/POST /api/v1/accounts/{account_id}/production-batches
GET/POST /api/v1/accounts/{account_id}/content-variants
GET/POST /api/v1/accounts/{account_id}/assets
POST     /api/v1/accounts/{account_id}/media-tool-tasks
GET/POST /api/v1/accounts/{account_id}/publish-tasks
GET      /api/v1/accounts/{account_id}/review-metrics
```

所有写请求使用幂等键和资源修订；Script/Storyboard/CompositionSpec 版本不可覆盖。拆解应用 Body 明确指定 `createScriptVersion`、`createStoryboardVersion`、`createKnowledgeVersion`，默认全部 false，禁止静默回流。ProductionBatch 固化采用版本和 Recipe/知识快照。

### P0-I 验证命令、失败恢复与回退

```powershell
python -m pytest tests/runtime/test_p0_i_content_chain.py tests/runtime/test_p0_i_batch_render.py tests/runtime/test_p0_i_publish_review.py tests/contracts/test_p0_i_account_isolation.py -q
npm --prefix apps/desktop run test -- p0-i-script-topic p0-i-storyboard p0-i-video-analysis p0-i-production-library
Push-Location apps/desktop
npx playwright test -g "当前账号从新建选题到生成可发布内容"
Pop-Location
```

- AI/渲染局部失败保留成功 variant 和镜头，按失败节点重试，不重建整个批次。
- 媒体工具不覆盖源资产；删除任务只撤销新输出引用。
- 发布失败保留待发布版本、平台响应摘要和 retry gate；不得伪造发布成功。
- 复盘采集失败显示空态和日志，不回填演示数字。
- 每个 I 阶段保留对应 pending 页面为 feature flag 回退；旧 Timeline 和旧壳不恢复，新增表/版本不物理删除。

## 7. 十三个 Route 的最终启用标准

| Route | 当前 | 何时可标记生产可用 |
| --- | --- | --- |
| 首启与许可证 | 有页面，证据漂移 | G0 + G5 + G7 主链通过 |
| 工作台 | 基础可用 | G4 action + G6 task projection 完成 |
| 定位与知识 | 基础可用，文件禁用 | P0-H 受控导入与真实检索通过 |
| 脚本与选题 | pending | I1 纵向 E2E 通过 |
| 分镜规划 | pending | I2 纵向 E2E 通过 |
| 视频拆解 | pending | I3 真分析和三类显式应用动作通过 |
| 批量生产 | pending | I4 批次到 RenderTask 通过 |
| 内容库 | pending | I5 真实资产与版本链通过 |
| 媒体工具箱 | pending | I5 权利确认、任务和新资产通过 |
| 发布 | pending | I6 真实 PublishTask 通过 |
| 复盘 | pending | I6 真实数据和空态通过 |
| 账号管理 | 页面可用，连接缺失 | G1-G6 通过 |
| AI 与系统设置 | 页面可用，执行孤岛 | P0-H 全链通过 |

“Route 可导航”“页面有内容”“单元测试通过”均不能单独作为生产可用证据。

## 8. 审计问题到阶段的唯一映射

| 阶段 | S0/S1 问题 | 不重复原则 |
| --- | --- | --- |
| G0 | S0-01、S0-02、S0-07 | 只修验收真源；不实现业务能力 |
| G1 | S1-15 | 只修壳层和切换器 |
| G2 | S1-10 | 只交付受控目录契约 |
| G3 | S0-03、S1-08、S1-09 | provisioning、eligibility、process proof 在一个领域内 |
| G4 | S0-04、S1-13 | 登录会话和 typed action 共同闭合账号修复路径 |
| G5 | S1-11、S1-12 | Runtime 起前/重启韧性 |
| G6 | S1-14、S1-20 | 任务、事务、事件与补偿 |
| G7 | S1-19 | 只提升通过真实 GUI 验收的制品 |
| P0-H | S0-05、S1-16、S1-17、S1-18、S1-21 | AI、知识与配置统一到 execution gateway |
| P0-I | S0-06 | 固定账号创作主链和八个 pending Route |

辅助项：S2-22 随 G4；S2-23 随 G0；S2-24 随 P0-I。任何实现 PR 必须标记主阶段和问题 ID；不得同时声称修复另一个阶段的问题。

## 9. 阶段性成果和决策门

| 决策门 | 用户可看到的阶段成果 | 放行条件 |
| --- | --- | --- |
| 批准 P0-G plan | 完整执行基础方案 | 本路线图与 P0-G 边界认可 |
| 批准 P0-G spec | 状态机、API、migration、UI 流、测试矩阵 | 无未裁决的账号/目录/登录安全边界 |
| G0-G4 完成 | 新账号可建立真实环境并登录 | 无 seed 新鲜库 E2E |
| G5-G7 完成 | 可恢复、可诊断、可复现的免安装 EXE | 干净 Windows GUI 主链与 manifest |
| 批准 P0-H plan/spec | AI/知识真实执行设计 | Provider 范围、凭据、安全和成本边界认可 |
| P0-H 完成 | 配置能产生可追溯真实 AIJob | 至少一个真实 Provider 纵向证据 |
| 批准 P0-I plan/spec | 八页面按纵切片实施 | 主模型、版本和发布边界认可 |
| P0-I 完成 | 从选题到发布复盘的账号级生产闭环 | 每 Route 真数据主链 + 全量制品验收 |

## 10. 最终 Definition of Done

- 十三个正式 Route 都有明确真实数据路径或合法中性空态，八个 pending 标识全部按纵向证据移除。
- 任意账号切换都不会串定位、知识、内容、任务、环境、凭据或发布数据。
- AI 调用均能追溯 Provider/模型路由、Prompt/Recipe/知识快照、输入、耗时、成本和错误。
- 所有长任务都有超时、失败、取消、重试、日志、刷新和重启恢复。
- 用户可从干净 Windows 制品完成激活、账号、工作区、登录、创作、批量生产、资产、发布与复盘。
- 构建 manifest、测试、API 文档、配置消费矩阵和当前制品一致；历史证据不被冒充为当前证据。
- 不出现单文件数千行、UI 直连后端、散落配置、英文占位、假业务数字或旧壳回流。

## 11. 当前建议

先批准修订版 P0-G 计划，不直接编码 P0-H/P0-I。P0-G 规格批准后按 G0 到 G7 实施；G0 首先恢复可信门禁，G7 才交付新的免安装 EXE。这样每个阶段都有用户可验证成果，也能在问题出现时退回最近的稳定制品，而不是继续在假绿基础上叠功能。
