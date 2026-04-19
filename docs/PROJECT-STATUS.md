# TK-OPS 项目状态总览

> 更新日期：2026-04-19  
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
- 全站 16 个正式页面已完成像素级 UI 精修 (Precision Sculpting)，物理动效、AI 处理感官反馈全面上线。
- M05 AI 剪辑工作台已并入主干，具备多轨时间线弹性流转、AI 魔法剪流光反馈及工业级布局加固。
- M06 视频拆解、M08 字幕对齐、M10-M15 执行治理类页面已完成交互闭环，补齐了列表动效与 Input 规范。
- 视频预览引擎已修复，支持动态路径转换与首帧强制抓取，解决了资产墙黑屏问题。
- 开发态桌面启动链路已支持复用现有 Runtime 与前端开发服务器，调试时不再强依赖 8000 / 1420 端口完全空闲。

## 3. 16 页状态表

状态说明：

- 已落地：有真实 Runtime/页面/测试闭环，且有明确实施或验收记录。
- 已接线：已存在页面、store、Runtime route 或 API 基础调用，但体验和契约文档仍需继续收口。
- 部分接线：页面或后端基础存在，但主业务闭环仍未完整落地。
- 待深化：主要停留在页面骨架、历史蓝图或待实现计划。

| 序号 | Route ID | 页面 | 当前状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | `setup_license_wizard` | 首启与许可证向导 | 已落地 | 离线授权、向导动效与粒子反馈已作为基线存在。 |
| 2 | `creator_dashboard` | 创作总览 | 已落地 | 极光 Hero、项目列表弹性删除、原生确认弹窗已落地。 |
| 3 | `script_topic_center` | 脚本与选题中心 | 已落地 | 编辑器 AI 流光、版本轨迹弹性流转、一键复制功能已落地。 |
| 4 | `storyboard_planning_center` | 分镜规划中心 | 已落地 | 镜头卡片瀑布流、弹性排队动效、脚本段落联动已落地。 |
| 5 | `ai_editing_workspace` | AI 剪辑工作台 | 已落地 | 多轨时间线弹性重排、AI 魔法剪流光、预览台淡入动效、工业级三栏布局已落地。 |
| 6 | `video_deconstruction_center` | 视频拆解中心 | 已落地 | 真实预览组件、TaskBus 丝滑进度条、卡片弹性删除已落地。 |
| 7 | `voice_studio` | 配音中心 | 已落地 | 音色列表弹性重排、播放波形动画、系统设置双向绑定已落地。 |
| 8 | `subtitle_alignment_center` | 字幕对齐中心 | 已落地 | 预览台扫描脉冲、字幕段列表水平流转、统计指标弹性反馈已落地。 |
| 9 | `asset_library` | 资产中心 | 已落地 | 预览引擎修复（杜绝黑屏）、资产墙无缝平移、动态路径解析、原生 Dialog 异步加载已落地。 |
| 10 | `account_management` | 账号管理 | 已落地 | 账号卡片物理反馈、抽屉弹性滑入、Input 组件规范化已落地。 |
| 11 | `device_workspace_management` | 设备与工作区管理 | 已落地 | 工作区列表弹性补位、健康检查状态保真、原生文件夹选择已落地。 |
| 12 | `automation_console` | 自动化执行中心 | 已落地 | 任务列表弹性流转、Terminal 滚动条优化、新建任务抽屉闭环已落地。 |
| 13 | `publishing_center` | 发布中心 | 已落地 | 预检清单弹性清单、提交流光反馈、回执逻辑展示已落地。 |
| 14 | `render_export_center` | 渲染与导出中心 | 已落地 | 导出队列传送带动效、实时进度位移补强、三栏弹性入场已落地。 |
| 15 | `review_optimization_center` | 复盘与优化中心 | 已落地 | UI 风格与全站对齐，建议列表动效补齐。 |
| 16 | `ai_system_settings` | AI 与系统设置 | 已落地 | 侧边栏分段淡入、音色保存闭环、原生文件夹/日志目录唤起已落地。 |

## 4. 已知待收口问题

1. `docs/RUNTIME-API-CALLS.md` 已补到 M05、M07、M08、M09、M16 和前端调用登记，仍需继续补齐 M10-M15、视频导入 TaskBus 与其它已存在 Runtime routes 的完整记录。
2. `apps/desktop/src/app/router/route-manifest.ts` 当前导航分组使用“全局管理 / 核心管线”等实现口径，和 `docs/UI-DESIGN-PRD.md` 的五组导航口径存在差异，后续如调整导航必须先做文档与路由同步。
3. `.claude/plan/tkops-frontend-modules.md` 的模块状态仍是历史“待开发”口径，后续需要另行标注为历史蓝图或更新状态。
4. `docs/stitch_text_document/` 同时包含当前可参考的创作工具稿和旧后台/CRM/经营系统稿，后续 UI 实现只能参考视觉节奏，不能让旧产品范围回流。
5. 中文文档在 PowerShell 中读取时必须显式使用 UTF-8，避免乱码污染文档和测试输出。

## 5. 下一步建议

1. 继续补齐 `docs/RUNTIME-API-CALLS.md` 中 M10-M15、视频导入 TaskBus 和剩余 Runtime routes 的调用登记。
2. 更新 `.claude/plan` 顶部状态说明，避免历史计划误导后续代理。
3. 开启 M05-M08 的“深度功能（Functional Deep Dive）”阶段，打通真实的 OpenAI / FFmpeg / TTS 闭环。
