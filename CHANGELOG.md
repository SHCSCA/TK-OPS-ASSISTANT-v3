# Changelog

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
