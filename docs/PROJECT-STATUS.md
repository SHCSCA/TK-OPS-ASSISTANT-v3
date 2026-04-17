# TK-OPS 项目状态总览

> 更新日期：2026-04-17  
> 状态来源：根 `README.md`、`CHANGELOG.md`、`docs/` 真源文档、`docs/superpowers/` 实施记录，以及当前仓库文件结构。  
> 本文只记录当前实现与文档对齐状态，不替代产品真源、UI 真源、架构真源或 Runtime API 真源。

## 1. 真源关系

| 事项 | 真源 |
| --- | --- |
| 产品范围、页面树、能力边界 | `docs/PRD.md` |
| UI 视觉语言、壳层结构、布局规则 | `docs/UI-DESIGN-PRD.md` |
| 目录、路由、模块、模型落点 | `docs/ARCHITECTURE-BOOTSTRAP.md` |
| 工程协作、实现硬约束 | `AGENTS.md`、`CLAUDE.md` |
| Runtime 接口与前端调用关系 | `docs/RUNTIME-API-CALLS.md` |
| 已审批实施计划与设计 | `docs/superpowers/plans/`、`docs/superpowers/specs/` |

`.claude/plan/` 目录下的 M05-M15 文档保留为历史模块蓝图，不单独代表当前实现状态。后续判断状态时，以代码、测试、`docs/superpowers/`、`CHANGELOG.md` 和本文为准。

## 2. 当前阶段

当前工程版本以根 `package.json#version` 为准，本文件不维护独立版本号。

当前阶段可概括为：

- 桌面壳、首启授权、配置总线、项目上下文、TaskBus、Dashboard / Script / Storyboard 主链基线已打通。
- 16 个正式页面文件已存在，并进入按页接入 Runtime 与真实状态的阶段。
- M05 AI 剪辑工作台 M05-A 已并入主干，具备时间线草稿读取、创建、保存与 AI 阻断态最小闭环。
- M07 配音中心、M09 资产中心、TaskBus、视频导入 TaskBus pilot、M09-M15 Runtime 页面接线已有实施记录。
- 开发态桌面启动链路已支持复用现有 Runtime 与前端开发服务器，调试时不再强依赖 8000 / 1420 端口完全空闲。
- 仍需继续补齐唯一 Runtime API 文档、逐页体验验收、测试矩阵和模块状态记录。

## 3. 16 页状态表

状态说明：

- 已落地：有真实 Runtime/页面/测试闭环，且有明确实施或验收记录。
- 已接线：已存在页面、store、Runtime route 或 API 基础调用，但体验和契约文档仍需继续收口。
- 部分接线：页面或后端基础存在，但主业务闭环仍未完整落地。
- 待深化：主要停留在页面骨架、历史蓝图或待实现计划。

| 序号 | Route ID | 页面 | 当前状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | `setup_license_wizard` | 首启与许可证向导 | 已落地 | 离线一机一码授权、机器码复制、授权码校验与首启前置流程已作为基线存在。 |
| 2 | `creator_dashboard` | 创作总览 | 已落地 | Dashboard 与项目上下文、系统状态、壳层基线已打通。 |
| 3 | `script_topic_center` | 脚本与选题中心 | 已落地 | Script 最小 Runtime 联通链路已进入基线。 |
| 4 | `storyboard_planning_center` | 分镜规划中心 | 已落地 | Storyboard 最小 Runtime 联通链路已进入基线。 |
| 5 | `ai_editing_workspace` | AI 剪辑工作台 | 已接线 | M05-A 时间线草稿 Runtime/UI 闭环已并入主干，覆盖真实时间线读取、创建、保存与 AI 阻断态；真实媒体预览、AI Provider 与渲染联动仍待后续阶段。 |
| 6 | `video_deconstruction_center` | 视频拆解中心 | 已接线 | 视频导入、FFprobe/TaskBus pilot 已有实施计划和接线记录；转写、切段、结构抽取仍待后续阶段。 |
| 7 | `voice_studio` | 配音中心 | 已落地 | M07 Runtime 与 UI 闭环设计标记已实现并进入验收；无 Provider 时返回真实 `blocked` 状态。 |
| 8 | `subtitle_alignment_center` | 字幕对齐中心 | 部分接线 | 页面和 store 存在，后端蓝图明确；字幕生成、对齐与时间线回写仍需独立闭环。 |
| 9 | `asset_library` | 资产中心 | 已落地 | M09 Batch 2-A 已标记通过验收，覆盖真实导入、预览、引用阻断与旧库兼容。 |
| 10 | `account_management` | 账号管理 | 已接线 | Runtime route、store、页面和测试基础存在；仍需继续验证真实账号/工作区绑定语义。 |
| 11 | `device_workspace_management` | 设备与工作区管理 | 已接线 | Runtime route、store、页面和测试基础存在；真实 PC 工作区与浏览器实例能力需继续深化。 |
| 12 | `automation_console` | 自动化执行中心 | 已接线 | Runtime route、store、页面和 TaskBus 基础存在；真实自动化执行层仍需分阶段接入。 |
| 13 | `publishing_center` | 发布中心 | 已接线 | Runtime route、store、页面和基础契约存在；发布预检、合规执行和回执仍需深化。 |
| 14 | `render_export_center` | 渲染与导出中心 | 已接线 | Runtime route、store、页面和基础契约存在；真实 FFmpeg 渲染链路仍需独立计划。 |
| 15 | `review_optimization_center` | 复盘与优化中心 | 已接线 | Runtime route、store、页面和基础契约存在；AI 优化建议回流仍需继续落地。 |
| 16 | `ai_system_settings` | AI 与系统设置 | 已落地 | 配置总线、AI 能力配置和系统诊断基础已进入基线；真实 Provider Secret UI 与 OpenAI 链路仍待后续。 |

## 4. 已知待收口问题

1. `docs/RUNTIME-API-CALLS.md` 已补到 M05、M07、M08、M09、M16 和前端调用登记，仍需继续补齐 M10-M15、视频导入 TaskBus 与其它已存在 Runtime routes 的完整记录。
2. `apps/desktop/src/app/router/route-manifest.ts` 当前导航分组使用“全局管理 / 核心管线”等实现口径，和 `docs/UI-DESIGN-PRD.md` 的五组导航口径存在差异，后续如调整导航必须先做文档与路由同步。
3. `.claude/plan/tkops-frontend-modules.md` 的模块状态仍是历史“待开发”口径，后续需要另行标注为历史蓝图或更新状态。
4. `docs/stitch_text_document/` 同时包含当前可参考的创作工具稿和旧后台/CRM/经营系统稿，后续 UI 实现只能参考视觉节奏，不能让旧产品范围回流。
5. 中文文档在 PowerShell 中读取时必须显式使用 UTF-8，避免乱码污染文档和测试输出。

## 5. 下一步建议

1. 继续补齐 `docs/RUNTIME-API-CALLS.md` 中 M10-M15、视频导入 TaskBus 和剩余 Runtime routes 的调用登记。
2. 更新 `.claude/plan` 顶部状态说明，避免历史计划误导后续代理。
3. 按 16 页状态表逐页补齐页面状态、错误反馈、真实数据路径和测试矩阵。
