# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 1. 项目定位

TK-OPS 是面向内容创作者的 **AI 视频创作中枢**，不是运营后台、团队协作平台或经营系统。第一目标平台是 TikTok，产品形态是本地优先、一机一码离线授权的 Windows 桌面工作台。

当前实现已落到新主线：`apps/desktop` 承载 Tauri 2 + Vue 3 桌面壳，`apps/py-runtime` 承载 FastAPI Runtime；16 个正式路由、首启授权、配置总线、项目上下文、脚本/分镜/工作台/语音/字幕/资产/账号/设备/自动化/发布/渲染/复盘等模块均已有实现入口。后续功能必须继续回到同一条创作主链，不得回流旧后台口径或旧壳路径。

核心模型链固定为：

```text
Project -> Script -> Storyboard -> Timeline -> VoiceTrack -> SubtitleTrack -> RenderTask
```

从零创作与导入拆解只是入口不同，最终必须回到同一 Project，不允许为不同入口创建两套割裂模型。

---

## 2. 常用命令

> 运行环境以 Windows 为主；仓库根目录是命令默认执行位置。根 `package.json#version` 是版本唯一真源。

```bash
# 依赖安装
npm --prefix apps/desktop install
python -m venv venv
venv\Scripts\python.exe -m pip install -e "./apps/py-runtime[dev]"

# 一键启动桌面应用：检查 Python / npm / cargo / node_modules，启动 Runtime，等待 /api/settings/health，再启动 Tauri
npm run app:dev

# Smoke 模式：Runtime、Vite/Tauri 就绪后自动退出，适合验证启动链路
TK_OPS_APP_DEV_EXIT_AFTER_READY=1 npm run app:dev

# 单独启动
npm run runtime:dev
venv\Scripts\python.exe -m uvicorn main:app --app-dir apps/py-runtime/src --host 127.0.0.1 --port 8000 --reload
npm run desktop:dev          # 仅 Vite，默认 127.0.0.1:1420
npm run desktop:tauri:dev    # 仅 Tauri dev

# 构建
npm run desktop:build
npm --prefix apps/desktop run build

# 前端测试（Vitest，jsdom，测试文件在 apps/desktop/tests）
npm --prefix apps/desktop run test
npm --prefix apps/desktop run test -- tests/script-topic-center.spec.ts

# Runtime / Contract 测试
venv\Scripts\python.exe -m pytest tests/runtime -q
venv\Scripts\python.exe -m pytest tests/runtime/test_settings_health.py -q
venv\Scripts\python.exe -m pytest tests/runtime/test_settings_health.py::test_health_returns_runtime_status -q
venv\Scripts\python.exe -m pytest tests/contracts -q
venv\Scripts\python.exe -m pytest tests/contracts/test_runtime_health_contract.py -q

# 开发数据、媒体工具、版本同步
npm run runtime:seed-dev
npm --prefix apps/desktop run prepare:media-tools
npm run version:sync
npm run version:check
```

当前没有独立 lint 脚本；不要在未实际运行的情况下声称 lint 已通过。

`npm run app:dev` 会占用/复用 `8000`（Runtime）与 `1420`（Vite）端口：端口被占用但健康检查可用时会复用现有服务；端口被占用且不可访问时会报中文错误。Tauri 开发态还要求本机存在 Rust/Cargo。

---

## 3. 文档真源与工作流

文档冲突时按以下优先级处理：

1. 产品范围、页面、能力边界：`docs/PRD.md`
2. 视觉、壳层、布局、设计令牌：`docs/UI-DESIGN-PRD.md`
3. 目录、路由、模块、模型落点：`docs/ARCHITECTURE-BOOTSTRAP.md`
4. 工程约束、协作流程：`AGENTS.md`

实现前必须核对 `docs/superpowers/plans/` 与 `docs/superpowers/specs/` 中相关计划和设计，尤其是 M05/M14/M15、AI 设置、媒体、授权、发布、渲染等已有计划。

Superpowers 分级：

- **S 档**：跨前端 + Runtime + 数据模型、新增/修改主模型链、新增页面或改路由真源、外部集成。必须完整 plan + spec。
- **M 档**：单模块新功能、既有数据模型非破坏性扩展。至少需要 plan。
- **L 档**：Bug 修复、单组件/单接口小改、文档/配置/测试补齐。可直接开工，但交付说明要写清楚。

Graphify 规则：本仓库有 `graphify-out/`。回答架构或代码库问题前先读 `graphify-out/GRAPH_REPORT.md`；如果未来出现 `graphify-out/wiki/index.md`，优先走 wiki。修改代码文件后运行 `graphify update .`（AST-only，无 API 成本）。

---

## 4. 架构大图

### 4.1 双进程桌面架构

- **Tauri / Vue 进程**：加载 Vue SPA，提供 Windows 桌面壳、路由、页面状态、用户交互和桌面能力入口。
- **Python Runtime 进程**：FastAPI 服务，承载业务编排、SQLite 持久化、AI Provider、媒体/任务、授权与诊断。
- **通信方式**：前端只通过 Runtime HTTP / WebSocket 通信，不允许组件内直接 `fetch` 业务接口，也不允许回退旧 PySide6/Qt 壳。

启动链路由 `scripts/run-desktop-app.mjs` 编排：检查依赖 → 启动或复用 Runtime → 轮询 `/api/settings/health` → 启动 Tauri。Runtime 单独启动由 `scripts/run-runtime-dev.mjs` 或 `apps/py-runtime/src/main.py` 负责。

### 4.2 前端关键结构

- 入口：`apps/desktop/src/main.ts` 创建 Pinia 与 Router，加载 `apps/desktop/src/styles/index.css`。
- 应用根：`apps/desktop/src/App.vue` 只挂载 `BootstrapGate`。
- 首启门禁：`apps/desktop/src/bootstrap/BootstrapGate.vue` + `apps/desktop/src/stores/bootstrap.ts` 管理 `boot_loading -> license_required -> initialization_required -> ready` 等阶段。
- 路由真源：`apps/desktop/src/app/router/route-manifest.ts` 与 `route-ids.ts`。16 个正式路由都必须在这里维护；首启页在正常导航中为 `HIDDEN`。
- 路由守卫：`apps/desktop/src/app/router/index.ts` 负责授权跳转；需要项目上下文的页面不再硬跳 Dashboard，页面应通过 ProjectContextGuard/空态处理缺失上下文。
- Runtime 适配层：`apps/desktop/src/app/runtime-client.ts` 是前端请求唯一集中入口，负责 JSON 信封解析、`RuntimeRequestError`、`requestId`、任务 DTO 兼容。
- 状态层：`apps/desktop/src/stores/` 管理 license、config-bus、project、bootstrap、task、workspace、voice、subtitle 等全局状态。
- 页面与模块：`apps/desktop/src/pages/` 放页面根组件，复杂逻辑下沉到 `apps/desktop/src/modules/`、`stores/`、`types/`、`styles/`，禁止在页面根组件堆满状态、请求和样式。
- 样式：优先使用 `apps/desktop/src/styles/` 的 CSS Variables 与语义设计令牌，Light / Dark 双主题同时考虑。

### 4.3 Runtime 关键结构

- 入口：`apps/py-runtime/src/main.py` 调用 `app.factory.create_app()`。
- 应用工厂：`apps/py-runtime/src/app/factory.py` 加载 RuntimeConfig、SecretStore、SQLite engine，初始化 domain schema，创建 repositories/services，并将依赖放入 `app.state`。
- 路由：`apps/py-runtime/src/api/routes/` 下按资源前缀拆分，`api/routes/__init__.py` 统一导出，factory 统一 include。
- 配置与日志：`apps/py-runtime/src/app/config.py`、`secret_store.py`、`logging.py` 是配置、密钥和日志入口。
- 模型与持久化：SQLAlchemy 模型在 `apps/py-runtime/src/domain/models/`，数据库基础设施在 `apps/py-runtime/src/persistence/`，迁移在 `apps/py-runtime/alembic/`。
- 服务层：`apps/py-runtime/src/services/` 承接业务编排、AI、媒体、任务、授权、脚本、分镜、工作台等跨模型流程。
- 仓储层：`apps/py-runtime/src/repositories/` 只封装 SQLite 查询与写入。
- 任务与 WebSocket：`services/task_manager.py` 维护当前内存态长任务并通过 `services/ws_manager.py` 广播，事件必须带 `schema_version`。
- AI Provider：`apps/py-runtime/src/ai/providers/` 与 `AICapabilityService` 管理能力路由、Provider 健康、模型和密钥状态。

### 4.4 Runtime 协议

统一 JSON 信封：

```json
{ "ok": true, "data": {} }
```

```json
{ "ok": false, "error": "中文错误说明", "error_code": "request.validation_failed", "requestId": "...", "details": {} }
```

`schemas/envelope.py` 是信封真源。`factory.py` 中间件为每个 HTTP 请求生成 `X-Request-ID`，异常处理器将参数错误、HTTPException 和未捕获异常统一转为错误信封。前端 `runtime-client.ts` 依赖 `error_code`、`requestId` 和 `details` 显示中文反馈与诊断入口。

---

## 5. 工程硬约束

- 全局文案、注释、交互提示使用中文；代码标识符使用英文。
- UTF-8 无 BOM；文档、注释、字符串必须保持中文可见，禁止乱码。
- 单文件超过 **400 行**触发拆分评审；超过 **600 行**强制拆分。
- 页面新增、删除、合并或正式路由变更，必须先更新 `docs/PRD.md`、`docs/ARCHITECTURE-BOOTSTRAP.md` 与路由真源。
- 禁止把产品范围漂回订单、退款、商品、重 CRM、团队协作后台或高风险环境伪装。
- 禁止新增“看起来像真实结果”的假业务数字；无真实后端数据时使用中性空态或引导态。
- 授权、一机一码、目录初始化、Runtime 健康检查必须走真实链路，禁止绕过授权开发后续功能。
- 配置必须走 Runtime 配置入口或前端 config-bus，禁止散落在页面、脚本或服务内部。
- UI 必须覆盖加载中、空状态、正常状态、错误状态；涉及任务还要有运行、取消、失败、重试和日志入口。
- UI 必须覆盖桌面宽屏和紧凑窗口，尤其是时间线、任务队列、状态栏、Detail Panel。
- 样式优先设计令牌和 CSS Variables；同一改动同时考虑 Light / Dark。
- 所有数据请求统一通过 Runtime 适配层，禁止组件内直接拼业务 API 或业务规则。
- 后端接口变更必须同步接口/调用说明，包含地址、方法、参数、返回、错误码和示例；前后端契约测试要同步更新。

---

## 6. Runtime 开发规则

- 依赖方向固定：`api/routes -> services -> repositories -> domain/persistence`；`tasks`、`media`、`ai` 作为服务层调用的系统能力，禁止反向依赖路由或页面。
- 路由层只做入参校验、服务调用和出参包装，不编排复杂业务流程。
- 新 Python 文件使用 `from __future__ import annotations`，导入顺序为标准库、第三方、本地模块。
- 模块级日志使用 `log = logging.getLogger(__name__)`；异常必须用 `log.exception(...)` 保留 traceback，禁止只 `log.error(str(e))`。
- UI 可感知错误必须转换为中文消息和稳定 `error_code`，不得向用户暴露 traceback。
- 超过 2 秒的 AI、渲染、发布、转写、导入、分析等操作必须走 task 机制并通过 WebSocket/任务接口反馈，禁止同步阻塞 HTTP。
- CORS origin 必须通过 `RuntimeConfig.allowed_origins` / 环境变量配置，不要在路由里临时放宽，更不要使用 `*`。
- 不要在 routes 中重新构建服务图；统一复用 `app.state` 中由 `create_app()` 注入的服务与仓储。

---

## 7. 前端开发规则

- 页面根组件只负责装配；复杂状态、请求、推导和样式拆到 composable、helpers、types、styles、store 或 Runtime 服务层。
- `@` 别名指向 `apps/desktop/src/`。
- 修改正式页面必须同步核对 `route-manifest.ts`、`route-ids.ts`、`docs/PRD.md` 和 UI 文档；未经文档更新不得新增第 17 个正式页面。
- 授权和项目上下文使用现有 stores / guards / ProjectContextGuard，不要在页面里写另一套判断。
- Runtime 错误要展示中文原因、重试、日志/请求 ID；禁止只在 console 输出。
- AI 输出必须可解释、可编辑、可重试、可回滚；覆盖用户内容必须有明确确认。
- 不使用英文占位和开发者语气文案；空态必须告诉用户“当前没有什么”和“下一步可以做什么”。

---

## 8. 测试与验证

- 功能改动至少跑“改动相关测试 + 1 条主链路回归”。
- 前端改动优先覆盖页面状态、Runtime DTO 契约、store 行为、关键交互和响应式布局。
- Runtime 改动优先覆盖服务层、仓储/模型、任务状态、接口信封和 contracts。
- 文档更新后至少做文本级一致性检查，确认产品范围、16 页结构、术语和命令未冲突。
- 如果某条测试、脚本或依赖不存在，不要伪称已验证；说明缺失事实和已完成的替代检查。

---

## 9. Git 与交付

- 功能开发使用 `feature/<task-name>` 分支；禁止 force push 到共享分支或修改已 push 历史。
- 提交信息格式：`<类型>: <中文描述>`，类型包括 `feat`、`fix`、`docs`、`refactor`、`chore`、`test`。
- 提交前必须进行代码审查（Claude 自审或委派 review），并在交付说明中如实列出运行过的验证命令和结果。

---

## 10. 维护本文件

以下情况必须更新本文件：

- 架构分层、启动链路、测试命令或目录边界变化。
- 新增硬性工程约束或 Superpowers 流程变化。
- Runtime 信封、错误码、任务/WebSocket 协议发生兼容性变化。
- graphify 入口、文档真源或 16 页产品范围发生调整。
