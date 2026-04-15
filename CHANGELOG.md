# Changelog

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
