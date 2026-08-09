# TK-OPS Production、真实 AI 与创作生产链闭环计划

> 日期：2026-08-08  
> 状态：已批准；用户已明确同意先完成 Production 收口，并要求真实验证 P0-H 与 P0-I  
> 上游真源：`docs/PRD.md`、`docs/UI-DESIGN-PRD.md`、`docs/ARCHITECTURE-BOOTSTRAP.md`、`AGENTS.md`  
> 继承路线：`docs/superpowers/plans/2026-08-02-production-chain-closure-roadmap.md`

## 1. 目标与版本边界

本计划分三个不可跳级的发布列车：

| 版本 | 阶段 | 目标 | 对外口径 |
| --- | --- | --- | --- |
| `0.4.10` | P0-G Production Hardening | 修复机器身份、执行环境恢复、发布证据与状态漂移 | 通过全部门禁后才可称 P0-G Production |
| `0.5.0` | P0-H Real AI Execution | 配置、知识、Prompt、Recipe 驱动真实 Provider 调用 | 至少一个受支持 Provider 真实纵向通过 |
| `0.6.0` | P0-I Creation Production Chain | 八个 pending 页面接入账号级真实创作、生产、资产、发布、复盘链 | 八页面逐片通过后才整体发布 |

`0.4.9` 保留为 P0-G 测试候选，不提升 Production，不覆盖其制品与证据。

## 2. 当前实测基线

- Runtime：`921 passed, 1 skipped`。
- Desktop：33 个测试文件、147 项通过；TypeScript 通过。
- Rust/Tauri：21 项通过。
- 首启 E2E：3/3；账号完整链路 E2E：7/7。
- GUI smoke：8 项；安装包 smoke 与许可证发行器打包 Runtime 激活通过。
- 免安装包根目录只有一个 Desktop EXE。
- 当前 `git status --short` 为 330 条，禁止据此生成 Production manifest。
- 八个账号级页面仍为 `p1_pending` / `p2_pending`。
- Provider 检查层当前主要完成连接、模型发现和静态声明，未形成统一 AI Execution Gateway。
- 目标 `ContentPlan -> ContentItem -> Script -> Storyboard -> ProductionBatch -> ContentVariant -> CompositionSpec -> RenderTask -> PublishTask` 尚未完整落库。

## 3. 阶段 A：0.4.10 P0-G Production 收口

### A1 稳定机器身份

- 机器因子改为带名称的采集结果，不再把可变长度值列表直接拼接。
- 首次可信采集建立受系统安全存储保护的机器身份基线，只保存因子摘要，不保存原始硬件值。
- 已建立基线后，单个 CIM、注册表或系统盘采集源临时失败不得改变公开机器码。
- 只有足够的已观测因子明确冲突时才能进入 `machine_mismatch`；采集不足进入可恢复的 `identity_unavailable` / `degraded`，不得伪装成换机。
- 兼容已签发 v1 许可证；迁移无法证明一致时失败封闭并提示重试，不自动覆盖基线或要求重新购买。
- 测试覆盖三因子到两因子、超时、空值、因子变化、基线损坏、旧许可证迁移和测试 override 隔离。

### A2 执行环境与监督登录恢复

- 账号向导分别读取“全部执行环境”和“可绑定候选”；失败环境不得显示为“没有执行环境”。
- 失败卡显示环境、工作目录、原任务、错误码、日志和恢复动作。
- 创建失败重试复用原 `environmentId`，新任务写入 `retryOfTaskId`，不得生成失联环境。
- 登录创建响应一返回就保存 `sessionId + prepareTaskId`；准备、等待、探测任一阶段取消都调用 Runtime 取消会话和对应任务。
- Runtime 取消处理负责终止任务、关闭本次受控浏览器、写终态、事件与补偿证据；前端 AbortController 只负责停止等待。
- 重启应用后可从 Runtime 任务与登录会话恢复 UI，不依赖组件内存。

### A3 可信发布门禁

- release manifest 升级为 v2，绑定 commit、tracked diff、untracked 文件内容摘要、构建输入、测试证据与制品哈希。
- Production 强制干净工作树；test 通道也必须能发现同名状态下源码内容变化。
- Production 必需证据至少包括 Runtime 全量、Desktop active、TypeScript、Rust、首启 E2E、账号链路 E2E、GUI smoke、安装包 smoke、sidecar smoke、许可证发行器对打包 Runtime 激活。
- 目标机器 TikTok 可见浏览器监督登录作为独立人工证据门；证据脱敏，不记录用户名、Cookie、Token、机器码明文或截图中的私人信息。
- 所有证据必须来自同一次编排或被显式绑定到同一 Desktop/Runtime/installer SHA-256。
- 失败构建不得覆盖 `current.json`，dirty test manifest 永远不能提升 Production。

### A4 状态真源和交付

- 对齐 `PROGRESS.md`、`BLOCKED.md`、`docs/PROJECT-STATUS.md`、相关 plan/spec 和 Changelog。
- 清理 330 条工作树状态并按职责形成可审查提交，禁止把临时缓存、测试数据、密钥或制品提交进 Git。
- 生成 `0.4.10` test 候选，完成目标机器人工证据后再生成干净 Production manifest 和回退包。

## 4. 阶段 B：0.5.0 P0-H 真实 AI 执行

### B1 Provider 与模型实测

- Provider Profile 支持完整编辑、凭据轮换、超时、额外参数、启停和健康状态。
- 验证拆分为网络、鉴权、模型发现和小型真实能力调用；静态 capability 声明不能标记“已验证”。
- 第一条正式纵向链优先采用 OpenAI-compatible 文本模型；其他适配器通过契约测试，未实测者明确标注。

### B2 配置依赖图

- Model、Capability Route、Prompt Profile、Composition Template、Account Recipe 使用显式修订和不可变激活快照。
- Route 解析包含优先级、fallback、超时、重试、并发和成本上限。
- 保存与激活前生成结构化 dependency issues 和 repair actions。

### B3 受控知识文件

- 复用 Tauri rootRef，只接受用户授权的本地视频、图片、音频和文档引用。
- 导入创建账号级 Asset / KnowledgeSource 和持久索引任务；不覆盖或偷偷复制源文件。
- 失败保留对象、taskId、logId 和可恢复动作。

### B4 AI Execution Gateway

- 新增账号级 AIExecution / AIJob 聚合与统一 Provider 端口。
- 每次执行冻结账号、capability、Provider/model route、Prompt/Recipe/知识快照、输入哈希、配置修订、耗时、usage、成本摘要、输出与错误。
- 所有调用通过 Runtime 任务生命周期、结构化日志和统一配置总线；Desktop 不直连 Provider。
- 旧 `AITextGenerationService` 只能作为兼容适配器消费新 Gateway，禁止维护第二套配置真源。

### B5 真实验收

真实链路必须完成：

```text
配置 Provider 与凭据
→ 真实发现模型
→ 真实小型能力验证
→ 配置 Script Route + Prompt
→ 当前账号激活 Recipe
→ 导入一个受控知识文件
→ 发起真实 AIExecution
→ 返回真实模型结果、usage/耗时、快照、taskId、logId
→ 修改配置后历史执行保持不变
```

验收记录只保存脱敏 Provider、模型、响应 ID 摘要、usage、耗时和输出哈希。API Key、Prompt 私密正文、本地绝对路径和用户资料不得进入普通日志或 manifest。

## 5. 阶段 C：0.6.0 P0-I 创作生产链

P0-I 只能消费已通过的 P0-H Gateway，按 I1→I6 纵切片实施：

1. I1 脚本与选题：ContentPlan、ContentItem、手动/AI/拆解来源、版本化 Script。
2. I2 分镜规划：Script 版本派生 Storyboard，镜头级生成/重生成，继续创建单条或批次。
3. I3 视频拆解：真实分析任务输出脚本文案、关键词、关键帧、结构与 tags，显式选择性回流。
4. I4 批量生产：ProductionBatch、ContentVariant、Provider 子任务、CompositionSpec、真实 FFmpeg RenderTask。
5. I5 内容库与工具：账号级真实 Asset 分类、来源/授权/版本；工具只创建新资产。
6. I6 发布与复盘：用户确认发布、真实执行环境、PublishTask/回执/失败恢复和真实指标空态。

每完成一个纵切片才将对应 Route 从 pending 切为 ready。旧页面、旧项目模型和 Timeline 只可迁移数据或抽取算法，不能回到运行路由。

## 6. P0-I 真实验收场景

至少跑通一条真实账号链：

```text
账号定位 + 知识快照 + AI Recipe
→ 新建真实 ContentItem
→ Provider 生成并保存 Script v1
→ 生成 Storyboard v1
→ 创建 ProductionBatch 与至少两个 ContentVariant
→ 至少一个真实媒体生成/TTS/字幕能力调用
→ FFmpeg 生成可播放视频文件
→ 内容库显示来源、版本、任务和授权
→ 用户确认后在目标 TikTok 可见浏览器完成真实发布或保存草稿
→ PublishTask 保存真实平台结果
→ 复盘只读取真实可用数据；没有数据时保持空态
```

真实外部发布属于有外部影响的人工确认门，执行时必须再次取得用户明确确认；自动化测试不得发布内容。

## 7. 文件地图

### 0.4.10

- Runtime：`services/machine_code.py`、`services/bootstrap_v1/license.py`、`services/execution_environments/`、`services/accounts/login_sessions.py`。
- 数据：新 Alembic 加法迁移、`device_workspace.py`、`account_login_session.py`、相关仓储和 DTO。
- Desktop：账号向导、执行环境 Creator/列表、登录组件、Runtime clients/types。
- 发布：`scripts/build-windows-release.mjs`、manifest create/verify、packaging tests。
- 文档：版本、状态、Runtime API、打包与验收说明。

### 0.5.0

- Runtime：`services/ai_execution_v1/`、`repositories/ai_execution_v1/`、Provider adapters、知识文件摄取、v1 routes/schemas。
- Desktop：AI 系统设置、账号 Recipe、知识来源、Execution Detail Panel、tasks/events。
- 数据：AIExecution、快照、usage/cost、受控文件引用的加法迁移。
- 文档：唯一 Runtime API 和 Desktop 调用文档。

### 0.6.0

- Runtime：内容主链领域模型、仓储、服务、任务处理器、媒体/渲染/发布适配器。
- Desktop：八个正式页面按 page/composable/helpers/types/styles 拆分。
- 数据：ContentPlan 到 PublishTask 的加法迁移和 legacy 显式导入工具。
- 测试：每个纵切片的契约、账号隔离、恢复、E2E 和 GUI 证据。

## 8. 全局门禁

- 不使用 seed、假结果或静态 capability 声明冒充真实验收。
- 每个写操作有账号范围、幂等键、修订、日志、错误码、重试/取消和缓存失效。
- Provider、渲染、发布长任务有超时、并发、成本/资源限制和补偿。
- 所有新增配置进入统一配置总线；所有请求通过 Runtime adapter。
- 每阶段完成“阶段相关测试 + 一条主链回归”；最终执行全量 Runtime/Desktop/Rust/E2E/打包/视觉/目标机器验收。
- 未取得真实外部依赖证据时只标记 blocked/test，不得降格验收标准。

## 9. 回退边界

- 每个阶段只做加法迁移；回退关闭写入口和 Route feature flag，不物理删除新表。
- 机器身份基线写入失败不覆盖旧许可证；执行环境重试失败保留原对象和用户文件。
- AI 执行失败保留快照和输出证据；Provider 配置回退不改写历史任务。
- P0-I 单片失败只关闭该 Route，已通过的前置页面与账号基础继续可用。

## 10. 退出标准

- `0.4.10`：全部 Production 阻断关闭，干净提交、可信 manifest、目标机器 TikTok 监督登录通过。
- `0.5.0`：至少一个真实 Provider 完成知识/Prompt/Recipe 驱动的可追溯 AIExecution。
- `0.6.0`：八个 pending 页面全部由真实账号主链驱动，生成真实视频资产并完成用户确认发布/草稿及真实复盘空态。

