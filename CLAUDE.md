# CLAUDE.md

本文档为 Claude Code(claude.ai/code)及协作 AI(Codex / Gemini 等)在本仓库工作时的行为准则。

---

## 一、项目概览

TK-OPS 是面向内容创作者的 **AI 视频创作中枢**(非运营后台、非团队协作平台),以 TikTok 为第一目标平台,采用本地优先、一机一码离线授权的 Windows 桌面工作台模式。

当前阶段:创作主链基线已打通——桌面壳、Runtime 配置总线、离线授权首启链路、项目上下文总线,以及 Dashboard / Script / Storyboard 最小联通链路已完成。

---

## 二、技术栈

- **桌面壳**:Tauri 2 + Vue 3 + TypeScript + Vite(`apps/desktop`)
- **业务运行时**:Python 3.13+ + FastAPI + SQLAlchemy + Alembic(`apps/py-runtime`)
- **前端状态**:Pinia + Vue Router
- **本地数据**:SQLite
- **通信**:HTTP + WebSocket,Runtime 统一 JSON 信封
  - 成功:`{ "ok": true, "data": ... }`
  - 失败:`{ "ok": false, "error": "...", "error_code": "..." }`(error_code 用于前端路由到具体的中文提示)

---

## 三、常用命令

```bash
# 一键启动桌面应用(自动启动 Runtime + 健康检查 + Tauri)
npm run app:dev

# 单独启动
npm run runtime:dev          # 仅 Runtime(FastAPI on :8000)
npm run desktop:tauri:dev    # 仅 Tauri 开发态

# 前端
npm --prefix apps/desktop install
npm --prefix apps/desktop run build
npm --prefix apps/desktop run test

# Runtime
venv\Scripts\python.exe -m pip install -e "./apps/py-runtime[dev]"
venv\Scripts\python.exe -m pytest tests/runtime -q
venv\Scripts\python.exe -m pytest tests/contracts -q

# 版本管理(唯一真源:根 package.json#version)
npm run version:sync
npm run version:check
```

---

## 四、架构与目录结构

### 4.1 双进程架构

桌面应用由两个进程组成:

1. **Tauri 进程** — 加载 Vue SPA,提供桌面窗口壳
2. **Python Runtime 进程** — FastAPI 服务,承载所有业务逻辑、数据持久化与 AI 调用

前端通过 `apps/desktop/src/app/runtime-client.ts` 与 Runtime HTTP API 通信。

### 4.2 进程生命周期与崩溃语义(必须遵守)

双进程场景下异常路径多,以下规则是硬约束:

- **启动顺序**:启动器先启动 Runtime → 轮询 `/api/settings/health` 就绪 → 再启动 Tauri 窗口
- **端口占用**:Runtime 启动失败时不得静默退出,必须向启动器返回结构化错误,由壳层展示中文提示并提供"查看端口占用/重试"操作
- **Runtime 崩溃**:Tauri 进程检测到 Runtime 掉线时,自动重启最多 3 次;3 次内未恢复则进入"离线降级态",禁用所有需要 Runtime 的功能,保留窗口与日志导出
- **用户强杀 Runtime**:Tauri 不得跟随退出,必须显式弹出恢复入口
- **Tauri 退出**:必须优雅关闭 Runtime(SIGTERM → 2s 宽限 → SIGKILL),禁止留下孤儿进程
- **日志**:进程切换、崩溃、重启必须写入统一日志,便于用户反馈时导出

### 4.3 前端关键路径

- **路由真源**:`apps/desktop/src/app/router/route-manifest.ts`
- **路由 ID**:`apps/desktop/src/app/router/route-ids.ts`
- **壳层布局**:`apps/desktop/src/layouts/AppShell.vue`
- **首启流程**:`apps/desktop/src/bootstrap/BootstrapGate.vue`(加载 → 授权 → 初始化三阶段)
- **状态管理**:`apps/desktop/src/stores/`(config-bus / license / project / bootstrap 等)
- **页面组件**:`apps/desktop/src/pages/`

### 4.4 Runtime 关键路径

- **应用工厂**:`apps/py-runtime/src/app/factory.py`
- **配置总线**:`apps/py-runtime/src/app/config.py` + `secret_store.py`
- **路由层**:`apps/py-runtime/src/api/routes/`(只做入参校验与出参包装)
- **服务层**:`apps/py-runtime/src/services/`(业务编排与跨模型协同)
- **数据层**:`apps/py-runtime/src/repositories/`(SQLite 读写封装)
- **离线授权**:`apps/py-runtime/src/services/license_service.py` + `license_activation.py`

### 4.5 跨层动态流规则

静态分层(routes → services → repositories)只解决"代码放哪里",真正的协作难点是动态流,以下是硬性约定:

- **AI 调用**:统一走 `services/ai_gateway`,强制重试(指数退避 + 最多 3 次)、强制超时、强制结构化错误码。禁止页面或路由直接调第三方 SDK
- **长任务**:超过 2s 的操作必须走 task 机制(`tasks/` 目录),前端通过 WebSocket 订阅进度,禁止同步阻塞 HTTP
- **WebSocket 消息**:所有消息类型必须带 `schema_version` 字段,变更时走兼容发布流程(新增字段兼容、删除字段走 deprecation 一个版本)
- **错误传播**:Runtime 异常在服务层捕获转换为带 `error_code` 的业务错误,路由层只负责包 JSON 信封。UI 根据 `error_code` 映射中文提示

### 4.6 项目主模型链

```
Project → Script → Storyboard → Timeline → VoiceTrack → SubtitleTrack → RenderTask
```

从零创作与导入拆解最终必须回到同一 Project,不允许为不同入口建两套数据模型。

---

## 五、文档真源体系

文档冲突时的优先级:

1. **产品范围/页面/能力边界**:`docs/PRD.md`
2. **视觉/壳层/布局**:`docs/UI-DESIGN-PRD.md`
3. **目录/路由/模块/模型落点**:`docs/ARCHITECTURE-BOOTSTRAP.md`
4. **工程约束/协作流程**:`AGENTS.md`

---

## 六、工程约束(硬性)

### 6.1 通用

- **语言**:全局文案、注释、交互提示使用中文,代码标识符使用英文
- **编码采用 UTF-8**：无 BOM，文档、注释、字符串必须保持中文可见，禁止出现乱码。
- **产品范围**:页面的新增、删除、合并必须先更新 `docs/PRD.md` 与路由真源,未更新文档不得改 `route-manifest.ts`
- **文件大小阈值**:单文件超过 **400 行**触发拆分评审;超过 **600 行**强制拆分,不接受"这个文件特殊"的理由
- **全局配置总线**:配置不得散落在页面/脚本/服务内部,一律走 config-bus
- **真实数据驱动**:无真实后端数据时用空态/引导态,禁止假业务数字与 mock 残留
- **全局日志**:Runtime 使用模块级 `logger = logging.getLogger(__name__)`,前端使用全局日志服务,禁止无日志的关键路径

- **保证全局性**：所有新开发必须遵循统一架构、统一规范、统一目录边界，避免局部特例破坏整体一致性。
- **全局采用中文注释**：新增注释必须使用中文，并保持简洁，只解释代码意图、边界和复杂逻辑。
- **全局异常处理以及日志记录**：所有异常必须被捕获、记录并转换为可见反馈；日志格式和错误处理方式必须统一。
- **全局配置总线**：所有配置必须通过统一配置入口或配置总线管理，禁止页面、脚本、服务各自保存一套配置。
- **禁止伪业务范围回流**：不得把订单、退款、商品、重 CRM、团队协作后台重新写回当前产品主线。
- **禁止高风险环境伪装**：设备管理只允许管理真实 PC 工作区、浏览器实例和执行环境。
- **UI 设计采用 Stitch 设计系统**：当前默认通过 Stitch CLI 生成设计参考，禁止在界面里掺入大量英文占位和开发者语气文案。
- **UI 交互必须有异常、日志和状态反馈**：禁止静默失败或只在控制台输出错误。
- **UI 设计必须适配不同屏幕尺寸**：禁止只针对桌面宽屏设计，必须考虑紧凑窗口和不同分辨率的适配。
- **UI 设计必须有视觉层次和引导**：禁止把功能堆在一起，必须通过视觉设计引导用户操作。
- **UI 设计必须与产品定位一致**：禁止把产品漂回旧后台口径、假数据演示、旧壳路径或失控的自动化范围。
- **UI 交互要有极高体验感**：要好看、流畅、易用，禁止出现卡顿、闪烁、错位等问题。
- **UI设计以及交互可以参考**：https://github.com/DavidHDev/react-bits.git以及 https://www.unicorn.studio
- **禁止在 UI 层直接拼接业务规则**：必须通过服务层接口处理业务逻辑。
- **UI 交互必须至少覆盖加载中、空状态、正常状态、错误状态**: 必须处理异常、日志、重试、取消和状态反馈；必须同步处理缓存失效、任务刷新与全局状态更新；必须补齐至少一条改动相关测试。
- **UI设计要求至少覆盖桌面宽屏和紧凑窗口两种布局，特别是时间线、任务队列、状态栏、Detail Panel等核心交互组件**。
- **UI设计必须与当前产品定位一致**，禁止把产品漂回旧后台口径、假数据演示、旧壳路径或失控的自动化范围。
- **UI要有设计感**，禁止直接把功能堆在一起，必须有合理的视觉层次和交互引导。
- **UI必须有明确的状态反馈**，禁止让用户无感知地等待或不确定操作结果。
- **UI要有一致的风格和交互模式**，禁止同一页面或功能里出现多种不同的设计语言或交互方式。
- **禁止在未核对 `docs/ARCHITECTURE-BOOTSTRAP.md` 的情况下擅自创建 `apps/desktop`、`apps/py-runtime` 目录或扩展路由、模块和模型**。
- **禁止在未核对 `docs/PRD.md` 和 `docs/UI-DESIGN-PRD.md` 的情况下擅自扩页或改产品定位**。
- **禁止新增“看起来像真实结果”的假业务数字**：无真实后端数据时，必须使用中性空态或引导态。
- **禁止绕过授权开发后续功能**：授权、一机一码、目录初始化、Runtime 健康检查必须走真实链路。
- **禁止账号、设备、工作区、浏览器实例与执行环境做假绑定**：它们必须是真实对象。
- **禁止任何自动化、发布、渲染或 AI 长任务没有超时、失败提示和重试路径**：必须保证用户可见的反馈和重试机制。
- **禁止在未核对 `docs/superpowers/plans/` 和 `docs/superpowers/specs/` 中相关计划和设计的情况下，直接进入实现阶段**。
- **UI 代码必须优先按页面、composable、helpers、types、styles 分层拆分；禁止把页面状态、服务调用和样式堆进单个超大文件**。
- **所有数据请求必须统一通过 Runtime 适配层发起；禁止组件内直接 fetch**。
- **样式必须优先使用设计令牌和 CSS Variables；同一改动需同时考虑 Light / Dark 双主题**。
- **Python 代码必须遵循统一规范**：包括文件头、导入顺序、类型标注、命名、日志、异常记录、事务控制、错误处理、配置管理和改动原则。
- **后端开发完成要给到明确的接口文档给到前端，前端开发完成要给到明确的接口调用文档给到后端，禁止接口不明确导致的前后端对接问题**。
- **接口文档以及调用文档必须包含接口地址、请求方法、请求参数、返回结果、错误码和示例，禁止模糊不清的接口说明**。
- **前后端接口必须保持一致，禁止接口变更导致的前后端不兼容问题**。
- **前后端接口必须有版本控制，禁止接口变更导致的版本冲突问题**。
- **前后端接口文档唯一且及时更新以及追加，禁止接口文档过时导致的对接问题**。
- **前后端接口必须有明确的错误处理机制，禁止接口调用失败导致的用户体验问题**。

### 6.2 Runtime 分层

- 路由层 → 服务层 → 仓储层 → tasks / media / ai,单向依赖,不得反向
- 路由层只做入参/出参,禁止编排业务流程
- 异常必须用 `log.exception(...)` 记录完整 traceback,禁止 `log.error(str(e))`
- 所有顶层入口必须捕获异常转换为业务错误,避免进程崩溃

### 6.3 前端

- 页面按 `page / composable / helpers / types / styles` 拆分
- 数据请求统一通过 Runtime 适配层,禁止组件内直接 fetch
- 样式优先使用设计令牌与 CSS Variables,考虑 Light/Dark 双主题
- `@` 别名指向 `apps/desktop/src/`

### 6.4 授权

- 离线授权链路先跑通再优化体验,禁止绕过授权开发后续功能
- 授权失败态与过期态必须有明确 UI 路径,不得静默退化

## 七、开发流程与协作规范

### 7.6 Superpowers 工作流(分级触发)

不是所有任务都需要 plan + spec 全流程。按任务影响面分三档:

**S 档(必须走完整 plan + spec)**:
- 跨模块改动(同时改前端 + Runtime + 数据模型)
- 新增数据模型或修改主模型链
- 新增页面或修改路由真源
- 外部集成(新三方 API、新 AI 模型)

**M 档(只需 plan,可跳过 spec)**:
- 单模块内的新功能
- 既有数据模型的非破坏性扩展

**L 档(直接开工,在 PR 描述里说清楚即可)**:
- Bug 修复
- 单组件/单接口的小改
- 文档、配置、测试补齐

**Superpowers skills 对应**:
- 规划:`superpowers:writing-plans`
- 执行:`superpowers:executing-plans`
- 审查:`superpowers:requesting-code-reviews`
- 调试:`superpowers:systematic-debugging`
- 完成:`superpowers:finishing-a-development-branch`

## 八、决策三问(Linus 风格)

每次重大决策前自问:

1. **这是现实问题还是想象问题?** — 拒绝过度设计
2. **有没有更简单的做法?** — 始终寻找最简方案
3. **会破坏什么?** — 向后兼容是铁律

---

## 九、Git 规范

- 功能开发在 `feature/<task-name>` 分支
- 提交前必须通过代码审查(Claude 自审或委派 review)
- 提交信息格式:`<类型>: <描述>`(中文)
- 类型:`feat` / `fix` / `docs` / `refactor` / `chore` / `test`
- **禁止**:force push 到共享分支、修改已 push 的历史

---

## 十、代码规范速查

### Python

- 文件头:`from __future__ import annotations`
- 类型:完整标注,使用 `|` 联合类型
- 日志:`log = logging.getLogger(__name__)`,异常用 `log.exception(...)`
- 错误:UI 可感知错误转中文并带 `error_code`,不暴露 traceback

### Vue / TypeScript

- 页面按 `page / composable / helpers / types / styles` 拆分
- 数据请求统一走 Runtime 适配层
- 样式优先 CSS Variables + 设计令牌
- 别名 `@` → `apps/desktop/src/`

---

## 十一、本文档的维护

本文档不是一次性产物。以下情况必须更新:

- 架构分层调整
- AI 协作规则调整(如模型能力画像变化)
- 新增硬性工程约束
- 决策三问得出"需要破坏向后兼容"的结论时

每季度由 Claude 主导一次整体 review,修剪过时条款,避免文档堆积成化石。