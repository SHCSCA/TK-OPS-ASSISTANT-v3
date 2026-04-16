# M09 资产中心 UI 与 Runtime 闭环计划

> 日期：2026-04-16
> 任务等级：A 档，UI/前端/后端契约联合推进
> 主流程：`tkops-agent-council` + `tkops-ui-experience-council` + `tkops-runtime-contract-council`
> 当前状态：M09 Batch 2-A 已完成并通过验收，准备合并主分支
> 验收记录：前端测试、前端构建、Runtime tests、contracts tests 均已通过；资产中心 UI/导入/预览/右侧抽屉链路完成。

## 背景

Batch 0-1 已经收口 TaskBus、视频导入基线与 M09-M15 最小测试硬化。下一步按既定优先级进入 M09 资产中心。资产中心是后续配音、字幕、渲染、发布复盘和 AI 剪辑工作台的基础资源池，不能只做静态素材页，也不能用假指标填充界面。

当前仓库已存在 M09 前后端骨架：

- 前端页面：`apps/desktop/src/pages/assets/AssetLibraryPage.vue`
- 前端 store：`apps/desktop/src/stores/asset-library.ts`
- Runtime client：`apps/desktop/src/app/runtime-client.ts`
- Runtime 类型：`apps/desktop/src/types/runtime.ts`
- 接口与调用唯一文档：`docs/RUNTIME-API-CALLS.md`
- 后端路由：`apps/py-runtime/src/api/routes/assets.py`
- 后端服务：`apps/py-runtime/src/services/asset_service.py`
- 后端仓储：`apps/py-runtime/src/repositories/asset_repository.py`
- 后端模型：`apps/py-runtime/src/domain/models/asset.py`
- 后端 schema：`apps/py-runtime/src/schemas/assets.py`
- 契约测试：`tests/contracts/test_runtime_page_modules_contract.py`

已发现的 P1 问题：

- 资产中心页面、详情组件、store、后端资产服务里存在中文文案乱码，影响可用性和验收。
- `GET /api/assets/references/{ref_id}` 当前直接 `raise NotImplementedError`，会破坏统一 JSON 信封。
- 后端计划文档要求 `POST /api/assets/import`，现有实现只有 `POST /api/assets` 手工创建资产。
- 当前接口与调用关系分散在代码、测试和计划中，已新增 `docs/RUNTIME-API-CALLS.md` 作为唯一真源，后续实现必须随接口变化同步更新。
- 删除资产前的引用影响提示尚未形成完整 UI/Runtime 闭环。
- 资产中心 UI 目前偏基础卡片网格，没有形成明确的“素材墙 + 预览 + 引用影响范围”的设计主张。
- 2026-04-16 实测旧本地库存在 `assets` 旧表字段，缺少 `name`、`type`、`updated_at` 等新列，导致 `GET /api/assets` 抛出 `no such column: assets.name`。
- 2026-04-16 实测点击“导入资产”反馈不足，且不符合桌面工作台预期；导入必须弹出系统文件选择器并支持批量选中导入。
- 2026-04-16 资产详情需要进入全局右侧抽屉，与顶部“属性面板”按钮和资产卡片选中态联动，不再挤占资产墙主区。
- 2026-04-16 右下角最近同步时间必须按上海时区展示，不能直接显示 UTC ISO 字符串。
- 2026-04-16 二次实测文件选择器仍报错，根因为 Tauri v2 capability 缺少 `dialog:allow-open`；同时资产卡片仍只显示图标占位，需要用真实本地文件路径渲染视频、图片和文档预览。
- 2026-04-16 三次实测导入图片失败，根因为旧版 `assets.kind` / `assets.file_name` 非空约束仍留在本地库，新 ORM 插入只写 `type` / `name`，触发 `NOT NULL constraint failed: assets.kind`。
- 2026-04-16 运行窗口持续出现 `/api/ws` 404 与 `No supported WebSocket library detected`，根因为 Runtime venv 缺少 `websockets` 或 `wsproto`，Uvicorn 无法处理 WebSocket 升级请求。
- 2026-04-16 四次实测资产可导入但无预览画面，根因为 Tauri `assetProtocol` 未启用，`convertFileSrc(filePath)` 生成的真实本地预览地址无法被 WebView 读取。
- 2026-04-16 五次实测要求文档预览适配 UTF-8：`.txt`、`.md`、`.json`、`.csv`、`.srt` 等文本类文档不能依赖 iframe 自行猜测编码，必须由前端读取后按 UTF-8 文本渲染。

## 会议组织

本轮先在主线程按 role cards 模拟会议，未 spawn 真实子 agent。进入实现时如用户确认多 Agent 执行，可按前端组、后端组、QA 组分派真实 worker，且每个 worker 必须有不重叠写入范围。

### UI/前端组会议

参与角色：

- Creative Director
- Interaction Designer
- Motion Engineer
- Frontend Lead
- Product Manager
- QA & Verification Agent

结论：有条件通过。

视觉主张：

资产中心应是“可快速扫描、可触摸预览、可追踪引用的编辑素材墙”，而不是普通后台素材表或 KPI 仪表盘。主视觉锚点是资产墙与右侧检查器，上传/导入是入口动作，引用影响范围是删除与复用决策的核心。

核心交互：

- 顶部工具带：项目范围、类型筛选、搜索、排序、导入入口。
- 中央素材墙：稳定网格，卡片展示类型、名称、来源、体积/时长、分析状态、标签摘要。
- 右侧检查器：预览、元数据、引用影响范围、最近来源、可执行动作。
- 导入体验：拖拽进入全页导入态，释放后进入导入确认或错误提示，不用 `alert`。
- 点击导入体验：调用桌面系统文件选择器，允许一次多选视频、图片、音频和文档；导入进度在页面内反馈，不使用手动输入路径作为核心流程。
- 详情体验：点击资产卡片后选中资产，并自动打开全局右侧抽屉展示资产详情、引用影响范围和删除前检查。
- 预览体验：视频使用真实本地视频首帧/静默预览，图片使用真实本地图片，PDF/文本类文档使用嵌入式文档画面；无真实路径时只展示中性空态，不伪造缩略图。
- 删除体验：删除前必须加载引用影响范围；存在引用时禁止静默删除，给出可见说明。

动效目的：

- hover 500ms 后展示静默预览或缩略强化，用于提高扫描效率。
- 详情面板进入/切换用轻量 Vue transition，保持空间连续。
- 导入和分析状态用稳定尺寸的进度/状态条，不造成网格跳动。
- 支持 `prefers-reduced-motion`，关闭循环动画和大位移动效。

前端边界：

- 页面不直接拼接 Runtime 规则，所有请求从 `runtime-client.ts` 和 `asset-library` store 进入。
- 第一阶段不引入 Three.js、GSAP 或新动效库。
- 先拆掉乱码、`alert`、hover-only 关键操作，再做视觉增强。
- 页面必须覆盖 loading、empty、ready、busy、error、disabled 状态。

外部参考转译：

- Unicorn Studio 作为空间层次、互动视觉和指针反馈参考。资产中心可以借鉴它的“层级深度、指针响应、视觉焦点跟随”思路，用在拖拽导入覆盖层、资产卡片 hover preview、检查器切换和素材墙扫描反馈上。
- React Bits 作为动效组件思路参考。重点借鉴 animated list、hover preview、text reveal、preloader、perspective grid 的交互节奏，但必须重写为 Vue 3 + CSS transition 实现，不直接复制 React 组件。
- 参考目标不是做炫技页面，而是让用户更快识别资产、预览素材、理解引用影响和恢复错误。
- 禁止把参考转译成装饰性渐变、粒子背景、无业务意义的 shader 动效、过度弹跳或纯展示动效。

### 后端组会议

参与角色：

- Backend Runtime Lead
- Data & Contract Agent
- Frontend Integration Agent
- AI Pipeline Agent
- QA & Verification Agent
- Independent Reviewer

结论：有条件通过。

API 边界：

- 保留现有 `/api/assets` CRUD 与 `/api/assets/{asset_id}/references`。
- 新增或补齐 `POST /api/assets/import`，用于从真实本地路径注册资产，第一阶段只做文件存在性、类型/来源/大小记录，不生成假缩略图。
- `GET /api/assets/references/{ref_id}` 必须实现或移除，不允许暴露 `NotImplementedError`。
- 删除资产前检查引用；存在引用时返回统一错误信封，中文错误可直接展示。
- 每个接口新增、字段调整、前端调用入口调整都必须同步更新 `docs/RUNTIME-API-CALLS.md`，该文件是唯一接口与调用真源。
- Runtime 启动时必须兼容旧版 `assets` 表，保留旧数据并补齐新模型查询所需列，不能让旧本地库因为字段缺失直接 500。

数据契约：

- 第一阶段沿用现有 `AssetDto` 字段，不做大规模迁移。
- 可通过 `metadataJson` 承载分析状态、媒体信息或导入来源补充信息，但字段语义必须在 spec 中固定。
- `tags` 当前是 JSON 字符串；前端展示需要安全解析，解析失败展示空标签并保留原始文本。
- `projectId = null` 表示全局资产，非空表示项目资产。

任务与事件：

- 普通导入注册不进入 TaskBus。
- 后续资产分析如果接入 `AssetAnalysisProvider`，必须升级为 TaskBus 长任务，并有 queued/running/succeeded/failed/cancelled 状态、失败原因和恢复路径。
- 本阶段只为分析入口预留 UI 状态，不接入假分析结果。

错误与日志：

- 后端服务使用模块 logger 记录异常。
- UI 可见错误必须是中文，不暴露 traceback。
- 前端 store 捕获 Runtime error 后写入 `error` 字段，页面就近展示重试入口。

## 统一目标

完成 M09 Batch 2-A：资产中心契约与界面设计闭环。

本阶段完成后，资产中心应具备：

- 中文可读、无乱码的资产中心界面。
- 基于真实 Runtime 数据的资产列表、筛选、搜索、详情和引用关系。
- 本地文件导入注册的真实后端接口。
- 删除前引用影响范围检查。
- 前端 store/client 与后端契约测试覆盖。
- 可进入下一阶段 AI 资产分析和与 M05/M07/M08/M14 串联的稳定基础。

## 非目标

- 不在本阶段实现素材商城、团队资产库或经营后台能力。
- 不引入假业务指标、假缩略图、假 AI 标签或假分析结论。
- 不实现完整媒体转码、缩略图生成、波形生成。
- 不把资产分析接入具体 AI Provider，除非另开 Batch。
- 不改旧壳目录，不改 `.ccb/`、Stitch 脚本或用户未确认的本地文档改动。

## 文件所有权

### UI/前端组

- `apps/desktop/src/pages/assets/AssetLibraryPage.vue`：页面布局、素材墙、导入态、详情检查器、错误态。
- `apps/desktop/src/components/assets/AssetPreview.vue`：资产卡片与右侧抽屉共用的真实本地预览组件。
- `apps/desktop/src/components/shell/details/AssetDetail.vue`：全局 Detail Panel 的资产详情文案和结构同步。
- `apps/desktop/src/stores/asset-library.ts`：资产状态、筛选、选择、导入、删除前引用检查、错误状态。
- `apps/desktop/src/app/runtime-client.ts`：资产导入、更新、引用查询和错误信封适配。
- `apps/desktop/src/types/runtime.ts`：资产输入类型、删除检查结果或导入结果类型。
- `apps/desktop/src-tauri/capabilities/default.json`：桌面文件选择器必须具备 `dialog:allow-open`。
- `apps/desktop/src-tauri/tauri.conf.json`：必须启用 `app.security.assetProtocol`，并将用户常用素材目录纳入预览读取范围。
- `docs/RUNTIME-API-CALLS.md`：同步记录 M09 前后端接口、前端调用、消费方和测试入口。
- `tests/contracts/test_text_encoding_contract.py`：锁定中文文档和用户可见前端文本文件必须使用 UTF-8 无 BOM，并禁止常见乱码片段回流。
- `apps/desktop/tests/runtime-client-m09-m15.spec.ts`：M09 client 合同更新。
- `apps/desktop/tests/runtime-stores-m09-m15.spec.ts`：资产 store 状态测试。
- 新增 `apps/desktop/tests/asset-library.spec.ts`：页面状态、导入态、错误态、详情面板测试。

### 后端组

- `apps/py-runtime/src/api/routes/assets.py`：资产导入、引用详情或路由移除、统一信封。
- `apps/py-runtime/src/services/asset_service.py`：导入注册、文件检查、引用删除规则、中文错误。
- `apps/py-runtime/src/repositories/asset_repository.py`：引用计数/引用详情查询。
- `apps/py-runtime/src/schemas/assets.py`：导入输入、引用影响结果、必要 DTO。
- `apps/py-runtime/src/domain/models/asset.py`：仅在必要字段缺失时最小扩展；默认不迁移。
- `apps/py-runtime/src/persistence/engine.py`：旧 `assets` 表兼容修复；当旧非空列阻断新导入时，原地重建为兼容表并保留旧数据。
- `apps/py-runtime/pyproject.toml`：Runtime 必须声明 WebSocket 服务器依赖，避免 `/api/ws` 升级请求退化成普通 GET。
- `tests/contracts/test_runtime_page_modules_contract.py`：资产导入、引用删除阻断、错误信封。
- 新增或扩展 `tests/runtime/test_asset_service.py`：服务层文件检查、引用删除规则。
- `tests/runtime/test_runtime_dependencies.py`：WebSocket 服务器依赖存在性检查。
- `docs/RUNTIME-API-CALLS.md`：后端 route/schema/service 与前端调用映射必须同步更新。

### Project Leader

- `docs/superpowers/plans/2026-04-16-m09-asset-center-ui-runtime.md`：本计划。
- `docs/RUNTIME-API-CALLS.md`：项目唯一 Runtime API 与前端调用文档，验收时检查是否随实现同步。
- 后续 `docs/superpowers/specs/2026-04-16-m09-asset-center-ui-runtime-design.md`：获批后生成的设计 spec。
- 集成所有 worker 输出，运行验证，触发 acceptance gate。

## 数据流与状态流

1. 页面进入资产中心。
2. `AssetLibraryPage.vue` 调用 `asset-library` store。
3. store 通过 `fetchAssets()` 请求 `/api/assets`。
4. Runtime 返回 `{ "ok": true, "data": AssetDto[] }`。
5. 用户选择资产后，store 请求 `/api/assets/{asset_id}/references`。
6. 右侧检查器展示资产预览、元数据、来源、引用影响范围。
7. 用户拖拽或点击导入本地文件。
8. 前端调用 `importAsset()`，后端检查真实文件路径，创建 `Asset`。
9. 成功后刷新列表并选中新资产；失败时页面显示中文错误和重试入口。
10. 用户删除资产前，store 先加载引用；存在引用则展示阻断原因，不直接删除。

## UI 设计规划

参考基准：

- 必须明确参考 Unicorn Studio 和 React Bits 的交互感，但落地为 TK-OPS 桌面工作台语言。
- Unicorn Studio 参考项：空间层次、沉浸式素材墙、拖拽时的响应式覆盖层、指针靠近时的局部高亮、预览区域的深度感。
- React Bits 参考项：资产列表进入/重排动效、卡片 hover preview、搜索结果 reveal、导入 preloader、筛选切换时的连续过渡。
- 参考项必须服务真实工作流：扫描、导入、选择、预览、引用检查、错误恢复。
- 第一阶段不新增重型动效依赖；如后续确实需要 Three.js、GSAP 或 Canvas，必须在单独 spec 中说明性能预算、降级方案和截图/录屏验收方式。

布局：

- 顶部工具带高度稳定，包含范围、搜索、类型、排序、导入。
- 主区采用两栏：左侧素材墙自适应网格，右侧检查器固定宽度 360-420px。
- 紧凑窗口下检查器改为底部或覆盖抽屉，不能压碎卡片文本。

视觉：

- 资产卡片是可交互对象，可以使用轻边框、缩略占位、来源标识、类型角标。
- 页面避免 KPI 卡、后台统计卡、渐变堆叠和装饰性背景。
- 使用现有 CSS variables 和 Stitch 设计系统语义，不新增单一紫蓝或深蓝主题。
- 资产墙要有清晰的视觉节奏：卡片尺寸稳定、缩略区与元数据分层明确、选中态和 hover 态有足够差异。
- 检查器要像创作工具的属性面板，而不是表单卡片；预览、元数据、引用影响和操作区需要形成清晰层级。
- 拖拽导入态要有“桌面工作台正在接收素材”的明确反馈，可用边界高亮、局部暗化和文件数量提示，不使用全屏营销式 hero。

交互：

- hover 预览只作为加速扫描，键盘/点击也必须能进入详情。
- 拖拽态覆盖页面但不拦截状态文案；释放后进入导入流程。
- 删除动作必须靠近引用影响范围，不在卡片 hover 删除里直接危险执行。
- 所有空态文案为中文产品口径，不使用开发者语气。
- 筛选、搜索、排序后素材墙要有轻量重排过渡，保持卡片尺寸稳定，不让工具带或检查器跳动。
- 卡片 hover preview 必须有 500ms 延迟，避免鼠标扫过时产生噪音；无缩略或无预览时显示真实空态，不伪造预览。
- 检查器切换资产时使用短过渡说明上下文变化，同时保留可读性和 reduced motion 降级。
- 错误恢复动作必须就近出现：导入失败靠近导入区域，删除阻断靠近引用影响范围，加载失败靠近素材墙。

状态矩阵：

- Loading：展示“正在读取资产库”。
- Empty：展示“当前项目还没有可复用资产”，提供导入入口。
- Ready：展示素材墙和检查器。
- Busy：导入中或后续分析中显示稳定状态条。
- Error：展示 Runtime 中文错误与重试按钮。
- Disabled：无项目上下文、文件路径无效、资产存在引用时禁用相应动作。

## 开发顺序

### 阶段 0：接口真源锁定

- 使用 `docs/RUNTIME-API-CALLS.md` 作为唯一接口与调用文档。
- 在 design spec 中引用该文档，不再复制一套平行接口表。
- 后续任何 M09 route、schema、Runtime client、store 调整，都必须先或同时更新该文档。
- 验收时检查该文档与代码、类型、测试一致。

### 阶段 1：P1 清障

- 修复 M09 前端和后端资产相关中文乱码。
- 移除页面 `alert`，改为 store 状态与页面内反馈。
- 处理 `GET /api/assets/references/{ref_id}` 的 `NotImplementedError`。
- 补后端错误信封测试，证明未实现路由不再裸露。

### 阶段 2：后端导入契约

- 写失败测试：`POST /api/assets/import` 成功导入真实临时文件。
- 写失败测试：不存在的文件返回中文错误信封。
- 写失败测试：旧版 `assets` 表缺少 `name`、`type`、`updated_at` 时，Runtime 初始化后可以正常查询资产列表。
- 写失败测试：旧版 `assets.kind` / `assets.file_name` 非空约束存在时，Runtime 初始化后仍可以导入新图片。
- 实现 `AssetImportInput`、route、service。
- 文件存在时记录 `filePath`、`fileSizeBytes`、`type/source/projectId`。
- 不生成假缩略图、不伪造媒体分析。

### 阶段 3：引用影响范围

- 写失败测试：资产存在引用时 DELETE 被阻断。
- 实现引用计数或引用列表检查。
- 前端 store 删除前加载引用，并在页面展示影响范围。
- 删除成功后刷新列表与检查器状态。

### 阶段 4：UI/前端体验升级

- 重构 `AssetLibraryPage.vue` 为素材墙 + 检查器结构。
- 补齐 loading/empty/error/busy/disabled。
- 实现拖拽导入视觉状态和文件确认反馈。
- 实现点击导入的可见入口：桌面文件选择器 `multiple: true`，批量选择后逐个调用 Runtime 导入契约。
- 把资产详情移入全局右侧抽屉，资产页主区只保留素材墙和状态反馈。
- 右下角最近同步时间统一格式化为 `Asia/Shanghai`。
- 补齐 Tauri dialog capability 权限测试，防止系统文件选择器在桌面端被权限层拒绝。
- 提取真实本地预览组件，卡片和抽屉统一使用 `convertFileSrc(filePath)` 渲染视频、图片和可嵌入文档；同时锁定 `tauri.conf.json` 的 `assetProtocol` 配置，避免预览 URL 生成但 WebView 不能读取。文本类文档读取后按 UTF-8 直接渲染，PDF 保持 iframe 预览。
- 补齐 WebSocket 服务器依赖，避免 TaskBus 连接持续产生 `/api/ws` 404 和 Uvicorn WebSocket library warning。
- 解析 tags 并展示 1-3 个真实标签；无标签时不伪造 AI 标签。
- 按 Unicorn Studio 参考补入空间层次、指针响应和拖拽覆盖层，但只使用轻量 CSS/Vue transition。
- 按 React Bits 参考补入素材墙进入、筛选重排、hover preview、搜索结果 reveal 和导入 preloader 的交互节奏。
- 增加 reduced motion CSS。

### 阶段 5：测试与验收

- 前端 client/store/page 测试覆盖导入、删除阻断、错误态。
- 后端 contract/service 测试覆盖导入、引用阻断、错误信封。
- 检查 `docs/RUNTIME-API-CALLS.md` 与后端 route、前端 `runtime-client.ts`、`runtime.ts`、store 和测试一致。
- 运行完整验证矩阵。
- 使用 `tkops-acceptance-gate` 做最终验收。

## 验证矩阵

- `npm --prefix apps/desktop run test`
- `npm --prefix apps/desktop run build`
- `venv\Scripts\python.exe -m pytest tests\runtime -q`
- `venv\Scripts\python.exe -m pytest tests\contracts -q`
- `git diff --check --cached`
- 人工核对 `docs/RUNTIME-API-CALLS.md` 与本次接口/调用变更一致。

UI 验收还需要：

- 宽屏资产墙截图。
- 紧凑窗口检查器截图。
- 空态、错误态、导入态截图或测试证据。
- hover preview、筛选切换、检查器切换、拖拽导入态的交互证据。
- 对 Unicorn Studio 与 React Bits 参考项的转译说明，明确哪些被采用、哪些因性能或产品边界被排除。
- Light/Dark 主题至少做一次人工检查或截图说明。

## 阻断条件

- 仍存在乱码文案。
- UI 仍使用 `alert` 作为核心反馈。
- UI 只是普通后台卡片堆叠，没有可识别的素材墙、检查器和互动反馈。
- 只堆视觉效果但不改善扫描、导入、预览、引用检查或错误恢复。
- 直接复制 React Bits 组件，或在未批准情况下引入重型动效依赖。
- Runtime 出现裸 `NotImplementedError`、traceback 或非统一信封。
- 前后端接口、类型、Runtime client、store、测试发生变化但未同步 `docs/RUNTIME-API-CALLS.md`。
- 删除资产不检查引用影响范围。
- 前端绕过 Runtime client 直接请求接口。
- 用假业务数字、假 AI 标签或假分析结果填充页面。
- 测试失败且无明确非阻断说明。

## Reviewer 初评

评分：8.1 / 10。

通过条件：无 P0；P1 已识别并有第一阶段清障方案；文件所有权清晰；UI 与 Runtime 都有可验证路径。

保留风险：

- 现有文档和部分源码输出存在乱码，需要在实现时确认文件实际编码与用户可见文本。
- 资产导入涉及本地路径，桌面端必须通过 Tauri 文件选择器多选；浏览器测试环境通过 mock 文件选择器验证，不再把手动路径输入作为产品流程。
- 资产分析属于 AI Provider 边界，应另开 Batch，不能混入本阶段。
