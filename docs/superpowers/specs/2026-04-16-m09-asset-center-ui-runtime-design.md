# M09 资产中心 UI 与 Runtime 闭环设计

> 计划来源：`docs/superpowers/plans/2026-04-16-m09-asset-center-ui-runtime.md`
> 接口真源：`docs/RUNTIME-API-CALLS.md`
> 状态：M09 Batch 2-A 已完成并通过验收，准备合并主分支
> 验收记录：资产中心素材墙、批量导入、真实本地预览、UTF-8 文档预览、右侧抽屉、引用阻断删除和上海时区时间均已落地。
> 适用流程：`tkops-agent-council` + `tkops-ui-experience-council` + `tkops-runtime-contract-council`

## 1. 设计目标

M09 资产中心要从“基础卡片列表”升级为“创作者素材墙 + 资产检查器 + Runtime 真实契约”的工作台闭环。

本轮目标：

- 修复 M09 当前前后端用户可见乱码。
- 建立本地文件导入注册能力，接入真实 Runtime 数据。
- 修复旧版本地 `assets` 表缺少新列导致资产列表查询 500 的兼容问题。
- 删除资产前检查引用影响范围。
- 使用唯一接口文档维护前后端调用关系。
- 将资产中心 UI 设计为有视觉主张和交互反馈的桌面工作台，不做普通后台素材表。

本轮非目标：

- 不实现素材商城、团队资产库、经营后台能力。
- 不生成假缩略图、假 AI 标签、假分析结果或假媒体时长。
- 不接入真实 `AssetAnalysisProvider`。
- 不引入 Three.js、GSAP 或新动效依赖。
- 不修改旧壳目录、`.ccb/`、Stitch 脚本或用户未确认的本地文档改动。

## 2. 真源与同步规则

`docs/RUNTIME-API-CALLS.md` 是 Runtime API 与前端调用关系的唯一文档。

实现时必须同步检查：

- 后端 route 是否与 `docs/RUNTIME-API-CALLS.md` 一致。
- 后端 schema 是否与 `apps/desktop/src/types/runtime.ts` 一致。
- 前端 `runtime-client.ts` 是否登记在 `docs/RUNTIME-API-CALLS.md`。
- store 和页面是否只通过 Runtime client 调用接口。
- contract/client/store/page tests 是否覆盖本次契约变化。

本 spec 不复制完整接口表；接口路径、前端调用名、消费方和测试入口以 `docs/RUNTIME-API-CALLS.md` 为准。

## 3. Council 决议

Product Manager：通过。资产中心属于 16 页内 P1 模块，是 M05/M07/M08/M14 的资源基础，不应漂移到素材商城或后台资产管理。

Creative Director：有条件通过。视觉必须形成“编辑素材墙 + 检查器”的工作台气质，参考 Unicorn Studio 的空间层次和 React Bits 的交互节奏，但不能成为装饰性特效页面。

Interaction Designer：有条件通过。必须覆盖扫描、筛选、导入、选择、预览、删除阻断和错误恢复，不允许 `alert` 作为核心反馈。

Backend Runtime Lead：有条件通过。必须消除裸 `NotImplementedError`，补齐 `POST /api/assets/import`，删除前检查引用，所有失败进入统一中文错误信封。

Data & Contract Agent：有条件通过。第一阶段沿用现有 `AssetDto`，只补必要输入和引用检查结果，不做模型大迁移。

Frontend Lead：通过。先用 Vue/CSS transition 和现有设计变量实现，不新增动效依赖。

QA & Verification Agent：通过。必须新增后端 service/contract 测试，前端 client/store/page 测试，并保留 M09-M15 回归。

Independent Reviewer：评分 8.2 / 10。无 P0；P1 已纳入阶段 1 和阶段 2。

## 4. UI 体验设计

### 4.1 视觉主张

资产中心是“可快速扫描、可触摸预览、可追踪引用的编辑素材墙”。

页面不使用 KPI 卡片、经营后台统计卡或装饰性背景。设计核心是：

- 素材墙：快速浏览、筛选、搜索、选择。
- 检查器：预览、元数据、来源、标签、引用影响范围。
- 导入反馈：拖拽覆盖层、导入中状态、失败恢复。
- 点击导入反馈：调用桌面系统文件选择器，支持一次多选真实本地资产路径，并逐个进入 Runtime 导入契约。
- 右侧抽屉反馈：点击资产卡片后自动打开全局右侧抽屉，资产详情、引用影响范围和删除前检查都在抽屉中完成。
- 真实预览反馈：资产卡片和右侧抽屉共用同一个本地预览组件，视频、图片和可嵌入文档都必须优先展示真实本地文件画面，而不是图标占位。
- 删除决策：引用影响范围可见后再允许删除。

### 4.2 外部参考转译

Unicorn Studio 参考项：

- 空间层次：素材墙、检查器、拖拽覆盖层有明确深度关系。
- 指针反馈：卡片 hover 时局部高亮和预览强化，但不出现持续噪音。
- 视觉焦点：选中资产后，卡片和检查器形成同一上下文。
- 拖拽响应：拖入文件时页面边界和工作区进入接收状态。

React Bits 参考项：

- animated list：筛选、搜索、导入后卡片进入和重排有短过渡。
- hover preview：卡片 hover 500ms 后显示静默预览或更强缩略状态。
- preloader：导入中使用稳定的轻量状态反馈。
- text reveal：搜索结果、空态和错误态可以用短淡入，不做营销式大标题。
- perspective grid：只借鉴“素材墙有层次”的节奏，不做重型 3D 依赖。

落地约束：

- 必须重写为 Vue 3 + scoped CSS。
- 不直接复制 React Bits 组件。
- 不新增 WebGL/Canvas/GSAP 依赖。
- `prefers-reduced-motion: reduce` 下关闭大位移动效和循环动画。

### 4.3 布局

宽屏布局：

- 顶部工具带：项目范围、搜索、类型筛选、排序、导入入口。
- 左侧主区：资产素材墙，自适应网格。
- 右侧检查器：固定宽度 360-420px。
- 全页拖拽层：只在 drag-over 时出现，展示文件数量和导入提示。

紧凑窗口：

- 顶部工具带允许换行或压缩按钮文本，但不得遮挡搜索和导入入口。
- 检查器转为底部抽屉或覆盖式面板。
- 卡片最小宽度保持稳定，名称使用省略，不允许文本挤出。

### 4.4 状态矩阵

| 状态 | 页面表现 | 操作 |
| --- | --- | --- |
| Loading | “正在读取资产库” + 轻量加载状态 | 禁用导入以外的资产操作 |
| Empty | “当前项目还没有可复用资产” + 导入入口 | 支持点击导入和拖拽导入 |
| Ready | 素材墙 + 检查器 | 支持筛选、搜索、选择、查看引用 |
| Busy | 导入中或后续分析中显示稳定状态条 | 禁用重复导入同一文件 |
| Error | 就近展示中文错误和重试按钮 | 支持重试读取或重新导入 |
| Disabled | 无项目上下文、文件无效、存在引用等原因可见 | 禁止危险动作 |

### 4.5 交互规则

- 搜索和筛选改变列表时，卡片重排过渡不能改变工具带高度。
- 卡片 hover preview 延迟 500ms；没有缩略图时展示类型化真实空态。
- 卡片点击选中资产，检查器切换到该资产上下文。
- 删除按钮不放在 hover 后直接危险执行，删除入口放在检查器的引用影响范围附近。
- 导入失败靠近导入入口展示错误。
- 点击导入不得无响应；文件选择器不可用、用户取消选择、批量导入中和部分失败都必须有明确页面状态。
- 桌面文件选择器依赖 Tauri v2 capability；`apps/desktop/src-tauri/capabilities/default.json` 必须允许 `dialog:allow-open`，并由测试锁定。
- 资产预览不得生成假缩略图；前端通过 `convertFileSrc(filePath)` 渲染真实本地视频、图片、PDF/文本类文档，无法嵌入时展示基于真实文件名和路径的中性文档面。
- 文本类文档预览必须适配 UTF-8：`.txt`、`.md`、`.json`、`.csv`、`.srt` 读取 `convertFileSrc(filePath)` 后的内容并渲染为文本预览，不使用 iframe 让 WebView 猜测编码。PDF 仍使用 iframe 预览。
- 本地预览依赖 Tauri `assetProtocol`；`apps/desktop/src-tauri/tauri.conf.json` 必须启用 `app.security.assetProtocol.enable`，并至少允许 `$HOME/**`、`$PICTURE/**`、`$VIDEO/**`、`$DOCUMENT/**` 等用户素材目录。
- 删除阻断靠近引用影响范围展示错误。
- 加载失败靠近素材墙展示错误。

## 5. 前端设计

### 5.1 类型

修改 `apps/desktop/src/types/runtime.ts`：

- 新增 `AssetImportInput`。
- 新增 `AssetUpdateInput`，如果本阶段开放名称或标签编辑。
- 新增 `AssetDeleteResult` 或调整 `deleteAsset()` 返回类型为 `{ deleted: true }`。

第一阶段保留现有 `AssetDto` 字段，不改名，不新增必须迁移字段。

### 5.2 Runtime client

修改 `apps/desktop/src/app/runtime-client.ts`：

- 新增 `importAsset(input): Promise<AssetDto>`。
- 新增 `fetchAsset(id): Promise<AssetDto>`，如果检查器需要详情刷新。
- 新增 `updateAsset(id, input): Promise<AssetDto>`，如果本阶段支持名称/标签编辑。
- 调整 `deleteAsset(id)` 返回类型，和后端 `{ deleted: true }` 保持一致。
- `fetchAssets()` 如新增 `source` 或 `project_id` 筛选参数，必须同步 `docs/RUNTIME-API-CALLS.md` 和 tests。

### 5.3 Store

重构 `apps/desktop/src/stores/asset-library.ts`。

建议状态：

```ts
type AssetLibraryStatus = "idle" | "loading" | "ready" | "error";
type AssetImportStatus = "idle" | "dragging" | "importing" | "succeeded" | "failed";

state: {
  assets: AssetDto[];
  selectedId: string | null;
  references: AssetReferenceDto[];
  filter: { type: string; q: string; source: string; projectId: string | null };
  status: AssetLibraryStatus;
  importStatus: AssetImportStatus;
  error: string | null;
  importError: string | null;
  deleteError: string | null;
}
```

动作：

- `load()`：加载资产列表。
- `select(id)`：选中资产并加载引用。
- `setFilterType(type)`：更新类型筛选并加载。
- `setSearchQuery(q)`：更新搜索词并加载。
- `importLocalFile(input)`：调用 `importAsset()`，成功后刷新并选中新资产。
- `prepareDelete(id)`：加载引用，返回是否可删除。
- `deleteSelected()`：无引用时删除资产并刷新。
- `parseTags(asset)`：安全解析 JSON 字符串标签，失败返回空数组。

错误处理：

- Runtime error 写入 store 对应错误字段。
- 页面禁止只写 `console.error`。
- 所有用户可见错误保持中文。

### 5.4 页面

重构 `apps/desktop/src/pages/assets/AssetLibraryPage.vue`。

结构：

- `ProjectContextGuard`
- `.asset-library`
- `.asset-library__toolbar`
- `.asset-library__workspace`
- `.asset-wall`
- `.asset-card`
- `.asset-inspector`
- `.asset-drop-overlay`
- `.asset-inline-error`

页面内必须移除：

- `alert(...)`
- 乱码文案
- hover 删除直接危险执行

页面内必须补齐：

- 导入入口。
- 点击导入后的系统文件选择器多选流程。
- 卡片选择后与全局右侧抽屉联动。
- 视频、图片和文档资产预览。
- 拖拽导入态。
- 空态。
- 错误态。
- 检查器引用影响范围。
- 删除阻断反馈。
- reduced motion CSS。

### 5.5 全局 Detail Panel

修改 `apps/desktop/src/components/shell/details/AssetDetail.vue`：

- 修复乱码。
- 与资产中心检查器文案一致。
- 无选中资产时展示中性引导态。
- 不承担真实数据加载逻辑，真实详情仍由页面/store 管理。

## 6. 后端设计

### 6.1 Schema

修改 `apps/py-runtime/src/schemas/assets.py`：

- 新增 `AssetImportInput`。
- 新增 `AssetDeleteResult` 或使用 `dict[str, bool]`，但 contract test 必须固定响应 `{ "deleted": true }`。
- 如实现引用详情，新增或复用 `AssetReferenceDto`。

建议 `AssetImportInput`：

```python
class AssetImportInput(BaseModel):
    filePath: str
    type: str
    source: str = "local"
    projectId: str | None = None
    tags: str | None = None
```

### 6.2 Repository

修改 `apps/py-runtime/src/repositories/asset_repository.py`：

- 新增 `get_reference(reference_id) -> AssetReference | None`，如果保留引用详情路由。
- 新增 `has_references(asset_id) -> bool` 或 `count_references(asset_id) -> int`。
- `delete_asset()` 不直接承担业务阻断判断，阻断逻辑放在 service。

### 6.3 Service

修改 `apps/py-runtime/src/services/asset_service.py`：

- 修复全部中文乱码。
- 新增 `import_asset(payload)`。
- `import_asset()` 使用 `Path(payload.filePath)` 检查真实文件存在。
- 文件不存在时抛出用户可见中文错误。
- 文件存在时记录真实文件大小。
- 删除资产前先检查引用；有引用时返回 409 或等价业务错误信封。
- 普通导入不调用 TaskBus。

异常策略：

- 预期业务错误用 `HTTPException` 返回中文 detail。
- 非预期异常使用 `log.exception(...)` 记录，返回中文失败提示。
- 不暴露 traceback。

### 6.4 Route

修改 `apps/py-runtime/src/api/routes/assets.py`：

- 新增 `POST /api/assets/import`。
- 实现或移除 `GET /api/assets/references/{ref_id}`，不允许 `NotImplementedError`。
- 保留 `/api/assets/{asset_id}/references`。
- 所有成功返回 `ok_response(...)`。

### 6.5 旧库兼容

修改 `apps/py-runtime/src/persistence/engine.py`：

- `initialize_domain_schema(engine)` 在 `Base.metadata.create_all(engine)` 后执行旧 `assets` 表兼容修复。
- 默认只补齐缺失列，不清空用户本地数据。
- 旧列 `file_name` 回填到 `name`，旧列 `kind` 回填到 `type`。
- `updated_at` 为空时回填为 `created_at`。
- 当旧列 `kind`、`file_name` 或 `mime_type` 带有非空约束并阻断新 ORM 插入时，允许原地重建 `assets` 表；重建必须保留旧资产数据与旧列值，避免用户本地资产丢失。
- 修复逻辑必须由 `tests/runtime/test_asset_schema_migration.py` 锁定。

### 6.6 WebSocket 运行依赖

TaskBus 前端连接 `ws://127.0.0.1:8000/api/ws`，Runtime 运行环境必须具备 WebSocket server transport。

- `apps/py-runtime/pyproject.toml` 必须声明 `websockets>=14.0,<16.0` 或等价 `wsproto`。
- 当前 venv 缺少依赖时，必须安装该依赖并重启 Runtime。
- 该依赖由 `tests/runtime/test_runtime_dependencies.py` 锁定。

## 7. 接口文档同步

每次实现阶段完成一个接口或调用调整后，必须同步更新：

- `docs/RUNTIME-API-CALLS.md`
- `apps/desktop/src/types/runtime.ts`
- `apps/desktop/src/app/runtime-client.ts`
- `tests/contracts/test_runtime_page_modules_contract.py`
- `apps/desktop/tests/runtime-client-m09-m15.spec.ts`

验收时如果任一处不一致，视为 P1 阻断。

## 8. 测试设计

### 8.1 后端 contract tests

扩展 `tests/contracts/test_runtime_page_modules_contract.py`：

- `POST /api/assets/import` 导入真实临时文件，返回 `AssetDto`。
- `POST /api/assets/import` 文件不存在时返回 `{ ok: false, error: "..." }`。
- `DELETE /api/assets/{asset_id}` 无引用时返回 `{ deleted: true }`。
- `DELETE /api/assets/{asset_id}` 有引用时返回失败信封。
- `GET /api/assets/references/{ref_id}` 不再返回 500 traceback 或裸 `NotImplementedError`。

### 8.2 后端 service tests

新增 `tests/runtime/test_asset_service.py`：

- 文件存在时 `import_asset()` 记录真实大小。
- 文件不存在时 `import_asset()` 返回中文错误。
- 有引用时 `delete_asset()` 阻断。
- 无引用时 `delete_asset()` 删除成功。

新增 `tests/runtime/test_asset_schema_migration.py`：

- 旧版 `assets` 表缺少 `name`、`type`、`updated_at` 时，初始化后补齐缺失列。
- 旧数据可被 `AssetRepository.list_assets()` 正常读取，不再触发 `no such column: assets.name`。
- 旧表的 `kind` / `file_name` 仍为 `NOT NULL` 时，初始化后导入新图片不再触发 `assets.kind` 约束失败。

新增 `tests/runtime/test_runtime_dependencies.py`：

- Runtime 环境必须能找到 `websockets` 或 `wsproto`，避免 `/api/ws` 升级请求在 Uvicorn 中退化为普通 GET。

### 8.3 前端 client tests

扩展 `apps/desktop/tests/runtime-client-m09-m15.spec.ts`：

- `importAsset()` 使用 `POST /api/assets/import`。
- `fetchAsset()` 使用 `GET /api/assets/{id}`。
- `updateAsset()` 使用 `PATCH /api/assets/{id}`，如果本阶段开放编辑。
- `deleteAsset()` 与后端删除结果类型一致。
- 失败信封转换为 `RuntimeRequestError`。

### 8.4 前端 store tests

扩展 `apps/desktop/tests/runtime-stores-m09-m15.spec.ts`：

- `load()` 成功和失败状态。
- `importLocalFile()` 成功后刷新并选中新资产。
- `importLocalFile()` 失败后写入 `importError`。
- `prepareDelete()` 有引用时阻断。
- `deleteSelected()` 无引用时删除并清空检查器。
- tags JSON 解析失败时不抛异常。

### 8.5 页面测试

新增 `apps/desktop/tests/asset-library.spec.ts`：

- loading、empty、ready、error 状态。
- 拖拽导入覆盖层出现和消失。
- 选择资产后检查器展示元数据和引用。
- 存在引用时删除阻断文案出现。
- 点击导入调用桌面文件选择器且传入 `multiple: true`，多选结果逐个通过 `POST /api/assets/import` 登记真实路径。
- 资产中心选择卡片后，全局右侧抽屉打开并展示该资产详情与引用影响范围。
- 视频、图片和文档资产使用真实本地路径转换后的预览地址，不回退到图标占位。
- 文本类文档资产按 UTF-8 读取并展示中文内容，避免 iframe 编码猜测导致乱码。
- 页面不调用 `window.alert`。

新增 `apps/desktop/tests/tauri-capabilities.spec.ts`：

- 主窗口 capability 必须包含 `dialog:allow-open`，防止桌面文件选择器在运行时被权限拒绝。
- Tauri `assetProtocol` 必须开启并覆盖用户常用素材目录，防止资产卡片和右侧抽屉只显示空白预览框。

新增 `tests/contracts/test_text_encoding_contract.py`：

- `docs/RUNTIME-API-CALLS.md`、本 plan/spec 和资产中心用户可见前端文本文件必须能以 UTF-8 无 BOM 读取。
- 禁止常见中文 mojibake 片段回流到资产中心文档和界面源码。

## 9. 实现顺序

1. 文档与测试锁定：确认 `docs/RUNTIME-API-CALLS.md` 与 spec 一致。
2. 后端测试先行：写 contract/service 失败测试。
3. 后端最小实现：schema、repository、service、route。
4. 前端 client/type 测试先行。
5. 前端 store 最小实现。
6. 页面 UI 重构与交互状态补齐。
7. 页面测试补齐。
8. Tauri capability 与真实本地预览补丁验证。
9. 文档同步核对。
10. 运行验证矩阵。
11. 触发 `tkops-acceptance-gate`。

## 10. 多 Agent 分工

如果进入真实多 Agent 执行，建议分派：

Backend Worker：

- 写入范围：`apps/py-runtime/src/api/routes/assets.py`、`apps/py-runtime/src/services/asset_service.py`、`apps/py-runtime/src/repositories/asset_repository.py`、`apps/py-runtime/src/schemas/assets.py`、`tests/contracts/test_runtime_page_modules_contract.py`、`tests/runtime/test_asset_service.py`
- 禁止范围：前端页面、store、样式、旧壳目录。

Frontend Worker：

- 写入范围：`apps/desktop/src/types/runtime.ts`、`apps/desktop/src/app/runtime-client.ts`、`apps/desktop/src/stores/asset-library.ts`、`apps/desktop/src/pages/assets/AssetLibraryPage.vue`、`apps/desktop/src/components/shell/details/AssetDetail.vue`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts`、`apps/desktop/tests/runtime-stores-m09-m15.spec.ts`、`apps/desktop/tests/asset-library.spec.ts`
- 禁止范围：后端 route/service/schema、旧壳目录。

Docs/QA Owner：

- 写入范围：`docs/RUNTIME-API-CALLS.md`、本 spec、验收记录。
- 禁止范围：业务实现文件，除非 Project Leader 明确授权。

Project Leader：

- 串行处理共享接口命名、类型字段和最终集成。
- 检查 workers 是否越界。
- 运行最终验证。

## 11. 验证矩阵

必须运行：

```powershell
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
venv\Scripts\python.exe -m pytest tests\runtime -q
venv\Scripts\python.exe -m pytest tests\contracts -q
git diff --check --cached
```

UI 验收需要：

- 宽屏资产墙截图。
- 紧凑窗口检查器截图。
- 空态、错误态、导入态证据。
- hover preview、筛选切换、检查器切换、拖拽导入态证据。
- Light/Dark 说明。
- Unicorn Studio 与 React Bits 参考项转译说明。

## 12. 阻断条件

- 仍存在乱码文案。
- 页面仍使用 `alert` 作为核心反馈。
- UI 仍是普通后台卡片堆叠，没有素材墙、检查器和互动反馈。
- Runtime 存在裸 `NotImplementedError`、traceback 或非统一信封。
- 前端绕过 `runtime-client.ts` 请求后端。
- 接口、类型、store、测试变化但未同步 `docs/RUNTIME-API-CALLS.md`。
- 删除资产不检查引用影响范围。
- 使用假 AI 标签、假缩略图、假媒体时长或假分析结果。
- 测试失败且无明确非阻断说明。

## 13. 通过标准

spec 可进入实现的条件：

- 用户确认本 design spec。
- `docs/RUNTIME-API-CALLS.md` 作为唯一接口文档被接受。
- UI 参考转译边界清晰。
- 前后端写入范围清晰且不重叠。
- 验证矩阵可执行。
