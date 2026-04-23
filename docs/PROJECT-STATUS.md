# TK-OPS 项目状态总览

> 更新日期：2026-04-22（当前应用版本以根 `package.json#version` 为准；V2 前后端落地：F-01~F-08 + B-01~B-06 + Modules A-H 运行时事件层全部合入，测试 315 passed/1 skipped）
> 状态来源：根 `README.md`、`CHANGELOG.md`、`docs/` 真源文档、`docs/superpowers/` 实施记录、`docs/BACKEND-REQUIREMENTS-2026-04-17.md` 进度表、`graphify-out/GRAPH_REPORT.md`，以及当前仓库代码与测试结构。
> 本文只记录当前实现与文档对齐状态，不替代产品真源、UI 真源、架构真源或 Runtime API 真源。

## 1. 真源关系

| 事项 | 真源 |
| --- | --- |
| 产品范围、页面树、能力边界 | `docs/PRD.md` |
| UI 视觉语言、壳层结构、布局规则 | `docs/UI-DESIGN-PRD.md` |
| 目录、路由、模块、模型落点 | `docs/ARCHITECTURE-BOOTSTRAP.md` |
| 工程协作、实现硬约束 | `AGENTS.md`、`CLAUDE.md` |
| Runtime 接口与前端调用关系 | `docs/RUNTIME-API-CALLS.md` |
| 后端缺口与补齐顺序 | `docs/BACKEND-REQUIREMENTS-2026-04-17.md` |
| 已审批实施计划与设计 | `docs/superpowers/plans/`、`docs/superpowers/specs/` |
| 代码结构导航 | `graphify-out/GRAPH_REPORT.md` + `graphify-out/wiki/` |
| V2 过渡性需求收口入口 | `docs/V2-PRODUCT-REQUIREMENTS-2026-04-20.md`、`docs/V2-FRONTEND-REQUIREMENTS-2026-04-20.md`、`docs/V2-BACKEND-REQUIREMENTS-2026-04-20.md`（验收后回流到 PRD / UI-DESIGN-PRD / RUNTIME-API-CALLS，再转入归档，不与上述主真源并列替代） |

`.claude/plan/` 目录下的 M05-M15 文档保留为历史模块蓝图，不单独代表当前实现状态。后续判断状态时，以代码、测试、`docs/superpowers/`、`CHANGELOG.md` 和本文为准。

## 2. 当前阶段

当前工程版本以根 `package.json#version` 为准，桌面壳与 Python Runtime 镜像版本通过 `npm run version:sync` 脚本维护；发布节奏见 `CHANGELOG.md`。

当前阶段可概括为：

- **UI 主链基线 + Precision Sculpting 全站收口**：16 个正式页面的像素级精修、物理动效、AI 流光反馈均已并入 `main`。
- **Runtime 路由面完整**：`apps/py-runtime/src/app/factory.py` 已注册 23 个业务 Router（accounts / ai-capabilities / ai-providers / assets / automation / bootstrap / dashboard / device-workspaces / license / prompt-templates / publishing / renders / review / search / scripts / settings / storyboards / subtitles / tasks / video-deconstruction / voice / workspace / ws），覆盖 16 页所需的基础面。
- **AI Provider 适配层雏形**：`apps/py-runtime/src/ai/providers/` 下已落地 `openai_chat` / `openai_responses` / `anthropic_messages` / `gemini_generate` / `cohere_chat` / `tts_openai` 适配器与基类，文本生成服务与 TTS 骨架已接通。
- **任务总线 + WebSocket**：`services/task_manager.py` 与 `services/ws_manager.py` 已承载视频导入等长任务进度分发，前端通过 TaskBus 与 AI 流光条消费状态。
- **测试网**：`tests/runtime/` 34 个单元测试、`tests/contracts/` 18 个契约测试，覆盖 license、bootstrap、scripts、storyboards、workspace、video-deconstruction、voice、subtitles、renders、review、tasks、settings-config、ai-capabilities 等主链。
- **开发态体验**：`npm run app:dev` 已支持复用现有 Runtime / 前端开发服务器，避免 8000 / 1420 端口误报。
- **知识图谱**：`graphify-out/` 已刷新到 2400 节点 / 5870 边 / 182 社区的最终状态，可作为架构快速导航。

## 3. 16 页状态表

状态说明：

- **UI 已落地**：页面壳、动效、状态反馈、空/错误态齐备，至少一条主流程可走通（可能接真实 Runtime 或占位数据）。
- **Runtime 已接线**：有对应 Runtime routes，且前端 `runtime-client.ts` 与 Pinia store 已消费。
- **契约已登记**：`docs/RUNTIME-API-CALLS.md` 已收录全部接口并保持与代码一致。
- **V2 进度**：对应 V2 文档包中本页需求的验收状态，取值 `未启动 / 进行中 / 已验收 / 已回流`（已回流表示验收结论已写回 PRD / UI-DESIGN-PRD / RUNTIME-API-CALLS，本页 V2 条款可在下一轮归档）。
- **深度功能待打通**：真实 AI / FFmpeg / TTS / 设备执行等端到端链路需后续深化。

| 序号 | Route ID | 页面 | UI | Runtime | 契约 | V2 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `setup_license_wizard` | 首启与许可证向导 | 已落地 | 已接线 | 已登记 | 未启动 | 离线授权、向导动效、粒子反馈、机器码/激活码已走真实链路。 |
| 2 | `creator_dashboard` | 创作总览 | 已落地 | 已接线 | 部分登记 | 进行中 | F-01 项目软删除贯通仪表盘/项目仓库/Runtime；sparkline / quick-jump 字段仍在 D2。 |
| 3 | `script_topic_center` | 脚本与选题中心 | 已落地 | 已接线 | 部分登记 | 进行中 | V2 状态栏 + 3 栏布局已落地；变体 / 段级改写 / 历史版本持久化仍待扩展。 |
| 4 | `storyboard_planning_center` | 分镜规划中心 | 已落地 | 已接线 | 部分登记 | 未启动 | 镜头卡片瀑布流、脚本段落联动齐备；Shot CRUD / 模板仍待补齐。 |
| 5 | `ai_editing_workspace` | AI 剪辑工作台 | 已落地 | 已接线 | 已登记 | 未启动 | 多轨时间线草稿读取 / 创建 / 保存 + AI 命令阻塞态契约已落档；clip 原子操作 / 导出 / 预览仍待深化。 |
| 6 | `video_deconstruction_center` | 视频拆解中心 | 已落地 | 已接线 | 已登记 | 进行中 | F-08 FFprobe 降级提示 + 真实 `router.push` 跳诊断已落地；阶段 / 转写 / 切段 / 回流还在 D2/D4。 |
| 7 | `voice_studio` | 配音中心 | 已落地 | 已接线 | 已登记 | 未启动 | 音色列表、波形动画、系统设置双向绑定齐备；profiles 写入 / 段级 / 试听 / 停顿仍在 D4。 |
| 8 | `subtitle_alignment_center` | 字幕对齐中心 | 已落地 | 已接线 | 已登记 | 未启动 | 扫描脉冲、字幕段水平流转、统计指标齐备；手动对齐 / 模板 / 导出 / 源波形仍在 D4。 |
| 9 | `asset_library` | 资产中心 | 已落地 | 已接线 | 已登记 | 未启动 | 预览引擎修复、资产墙无缝平移、原生 Dialog 异步加载齐备；缩略图 / 批量 / 分组 / refs 子接口待文档对齐。 |
| 10 | `account_management` | 账号管理 | 已落地 | 已接线 | 未登记 | 进行中 | F-03 校验态与能力绑定已接通；13 个路由待写入 `RUNTIME-API-CALLS.md`。 |
| 11 | `device_workspace_management` | 设备与工作区管理 | 已落地 | 已接线 | 未登记 | 进行中 | F-02 浏览器实例 CRUD + B-02 迁移/路由 已接通；6 个路由待文档化。 |
| 12 | `automation_console` | 自动化执行中心 | 已落地 | 已接线 | 未登记 | 未启动 | tasks CRUD + trigger + runs 存在，7 个路由未文档化；暂停 / 恢复 / 取消 / 日志待补。 |
| 13 | `publishing_center` | 发布中心 | 已落地 | 已接线 | 未登记 | 未启动 | plans CRUD + precheck/submit/cancel 存在，8 个路由未文档化；日历 / 回执待补。 |
| 14 | `render_export_center` | 渲染与导出中心 | 已落地 | 已接线 | 未登记 | 未启动 | tasks CRUD + cancel 存在，6 个路由未文档化；模板 / 重试 / 资源 / 真实进度待补。 |
| 15 | `review_optimization_center` | 复盘与优化中心 | 已落地 | 已接线 | 已登记 | 未启动 | V2 后端服务扩展已合入；建议列表 / 回流能力仍待接通前端。 |
| 16 | `ai_system_settings` | AI 与系统设置 | 已落地 | 已接线 | 已登记 | 进行中 | F-04 日志目录 + F-05/06/07 就绪徽章/能力画像/重复模型拦截 + B-03/B-04/B-05 提供商健康/Secret/能力绑定已接通。 |

**契约完成率**（参照 `docs/BACKEND-REQUIREMENTS-2026-04-17.md` 0.1.2 节）：96 个真实路由中 34 个完成"实现 + 文档 + 前端 + 测试"四步（约 35%），62 个处于"代码已有、文档 / 测试 / 前端任一缺失"状态。

## 4. 已知待收口问题（工程债，与 V2 需求收口并行推进）

> 以下条款聚焦"代码 / 文档 / 结构"层面的工程债，与第 6 章 V2 文档包的"用户体验 / 契约状态"收口是两条并行轨道：V2 负责把页面从"能看"收口到"能继续完成任务"，本节负责把代码库从"能跑"收口到"可维护"。两套清单不可互相替代。


1. **页面文件超标**：除 `AIEditingWorkspacePage.vue`（250 行）与 `AISystemSettingsPage.vue`（412 行，且已按 page/composable/helpers/types 拆分）外，8 个页面超过 CLAUDE.md 规定的 600 行硬性拆分线——`accounts` 1075 / `publishing` 946 / `assets` 912 / `automation` 893 / `devices` 865 / `renders` 860 / `scripts` 800 / `storyboards` 737；另有 `setup` 622 / `video` 588 / `review` 560 / `dashboard` 503 / `subtitles` 488 / `voice` 462 超过 400 行评审线。当前只有 settings 页面落地了 `page / composable / helpers / types / styles` 分层范式，其余页面仍是单文件堆积，需按 Superpowers S 档纳入规划。
2. **RUNTIME-API-CALLS 缺口**：M10 账号 (13) / M11 设备 (6) / M12 自动化 (7) / M13 发布 (8) / M14 渲染 (6) 共 40 个已实现路由尚未登记；M02 dashboard、M03 scripts、M04 storyboards、M06 video-deconstruction、M09 assets 还有字段级差口（D2）。这是"接口真源与代码已有漂移"的核心债。
3. **深度功能未通**：M05-M08 四页的 UI 层已落地，但真实的 OpenAI Chat / FFmpeg 解析 / TTS 合成 / 字幕对齐后端路径仍在骨架。AI Provider 适配器虽已就位，真正贯穿 Script → Storyboard → Voice → Subtitle → Workspace 的 AI 链路仍需逐段落地。
4. **导航分组漂移**：`apps/desktop/src/app/router/route-manifest.ts` 使用"全局管理 / 核心管线"等实现口径，与 `docs/UI-DESIGN-PRD.md` 五组导航口径存在差异，调整前必须先同步文档。
5. **历史蓝图未标注**：`.claude/plan/tkops-frontend-modules.md` 仍沿用"待开发"口径，需在顶部显式标注为历史蓝图，避免后续代理误判。
6. **Stitch 参考稿混入旧后台口径**：`docs/stitch_text_document/` 同时包含当前可参考的创作工具稿和旧 CRM/经营系统稿，UI 实现只能参考视觉节奏，不得让旧产品范围回流。
7. **编码约束**：中文文档在 PowerShell 中读取时必须显式使用 UTF-8，避免乱码污染文档与测试输出；`tests/contracts/test_text_encoding_contract.py` 需保持常绿。

## 5. 下一步建议（工程债轨道，V2 需求轨道见第 6 章）

按优先级：

1. **立即**：补齐 `docs/RUNTIME-API-CALLS.md` 中 M10-M14 共 40 个路由的登记，把"已实现未文档化"的 62 项债压回 0，让契约真源与代码一致。
2. **本迭代**：按 Superpowers S 档立计划，对 8 个超 600 行页面实施 `page / composable / helpers / types / styles` 拆分，以 `accounts` / `publishing` / `assets` 三页为首批示范。
3. **本迭代**：开启 M05-M08 深度功能阶段，优先打通 Script 真实 AI 生成与 Voice TTS 端到端；以 AI Provider 适配层为收口点，保证统一重试 / 超时 / 结构化错误码。
4. **下迭代**：补齐 M02 dashboard 的 sparkline / quick-jump、M06 视频拆解的阶段与转写字段，覆盖 D2 字段级差口。
5. **持续**：在所有重大改动提交前运行 `graphify update .` 保持 `graphify-out/` 作为架构快速导航的最新快照；同时巩固 `tests/runtime` 与 `tests/contracts` 双网覆盖。
6. **文档治理**：在 `.claude/plan/` 顶部标注历史蓝图口径，在 `docs/stitch_text_document/` 目录顶部区分"当前可参考"与"旧后台仅供视觉参考"。


## 6. V2 文档状态

- 当前仓库已建立 V2 文档包：产品总文档、前端需求文档、后端需求文档。
- 下一阶段需求收口应优先以 V2 文档包作为入口，再分别同步到 PRD、UI 真源和 API 真源。
- 当前状态应理解为“已有实现 + V2 文档已建档 + 待按 V2 收口”，而不是继续以零散评审意见推动开发。

### V2 文档入口

1. `docs/V2-PRODUCT-REQUIREMENTS-2026-04-20.md`
2. `docs/V2-FRONTEND-REQUIREMENTS-2026-04-20.md`
3. `docs/V2-BACKEND-REQUIREMENTS-2026-04-20.md`

### V2 与真源的回流闭环

1. **进入**：任何新需求或体验问题，先以 V2 文档包作为收口入口，按"产品问题 → 前端需求 → 后端需求"三件套补齐。
2. **推进**：单页验收按 V2 三件套的验收标准执行；第 3 章 16 页状态表的 **V2 列** 从 `未启动 → 进行中 → 已验收` 逐步迁移。
3. **回流**：某页 V2 验收通过后，立即把验收结论同步写回 `docs/PRD.md`（范围/页面）、`docs/UI-DESIGN-PRD.md`（视觉/交互）、`docs/RUNTIME-API-CALLS.md`（接口契约），并在 V2 对应章节顶部标注"已回流"。V2 列标记为 `已回流`。
4. **退役**：当 16 页全部进入 `已回流` 状态后，V2 文档包整体移入 `docs/archive/`，PROJECT-STATUS.md 第 6 章同步压缩为一行归档记录。
5. **变更**：V2 文档包在回流前如需迭代，统一在文件名加版本后缀（如 `V2.1-FRONTEND-REQUIREMENTS-YYYY-MM-DD.md`），禁止无版本覆盖，避免历史需求被悄悄改写。
6. **冲突裁决**：V2 与 PRD / UI-DESIGN-PRD / RUNTIME-API-CALLS 发生冲突时，未回流前以 V2 为准；回流后以主真源为准。

### V2 用户实测反馈（2026-04-20，已分发）

本轮真实使用中发现的 8 条体验与功能缺口已按前后端切分，分发至 V2 前后端文档，并在两边建立交叉索引：

- **前端缺陷清单**：见 `docs/V2-FRONTEND-REQUIREMENTS-2026-04-20.md` 第 5 章 "实测缺陷索引（2026-04-20）"，编号 F-01 ~ F-08。
- **后端缺陷清单**：见 `docs/V2-BACKEND-REQUIREMENTS-2026-04-20.md` 第 7 章 "实测缺陷索引（2026-04-20）"，编号 B-01 ~ B-06。

修复档位速览：

- **L 档（直接开工）**：F-01 / F-03 / F-04 / F-07 + B-01 / B-05。
- **M 档（单页 plan 推进）**：F-05 / F-06 / F-08 + B-03 / B-04 / B-06。
- **S 档（需立计划）**：F-02 + B-02（浏览器实例对象模型）。

PROJECT-STATUS.md 只保留本索引入口，不复述具体修复方案，避免与 V2 真源漂移。

### V2 落地进度（2026-04-22）

| 档位 | 项 | 落地证据 |
| --- | --- | --- |
| L | F-01 项目软删除 | `stores/project.ts:deleteProject` + `CreatorDashboardPage.vue` 删除确认链路 |
| L | F-03 账号校验态 | `AccountManagementPage.vue` 对齐 V2 能力绑定与校验态 |
| L | F-04 日志目录 | `pages/settings/use-system-settings.ts:openLogDirectory` |
| L | F-07 提供商重复模型拦截 | `ProviderConfigDrawer.vue` 重复校验 + `provider.model.*` 错误码 |
| L | B-01 软删除持久化 | `persistence/engine.py:_repair_legacy_project_schema` + `projects.deleted_at` |
| L | B-05 Secret 写入 | `services/settings_service.py` Secret 合并策略 |
| M | F-05 就绪徽章 / F-06 能力画像 | `ProviderCard.vue` + `ProviderConfigDrawer.vue` V2 视觉与数据绑定 |
| M | F-08 FFprobe 降级提示 | `VideoDeconstructionCenterPage.vue` alert bar + `router.push('/settings/ai-system')` |
| M | B-03 提供商健康检查 | `services/ai_capability_service.py` + Runtime 事件 `ai-capability.changed` |
| M | B-04 能力绑定契约 | `schemas/ai_capabilities.py` + 新增契约测试 |
| M | B-06 FFprobe 诊断 | `services/ffprobe.py:get_ffprobe_availability` + `failed_degraded` + `media.ffprobe_unavailable` |
| S | F-02 浏览器实例 UI | `DeviceWorkspaceManagementPage.vue` 实例创建/列表/删除 |
| S | B-02 浏览器实例对象模型 | 迁移 `0007` + `api/routes/device_workspaces.py` 6 路由 |
| — | Modules A-H 运行时事件层 | `config-bus` / `ai-capability` / `task-bus` / `video-import` / `subtitle-alignment` 等 store 接入 revision 同步 |

尚待收口：
1. V2 新增路由登记到 `docs/RUNTIME-API-CALLS.md`（B-02 / B-03 / B-06 共约 10 条）。
2. `DeviceWorkspaceManagementPage.vue`(949) / `ScriptTopicCenterPage.vue`(834) / `VideoDeconstructionCenterPage.vue`(1038) 三个超 600 行硬限的页面仍需按 `page/composable/helpers/types/styles` 拆分。
