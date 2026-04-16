# Runtime API 与前端调用唯一文档

> 本文件是 TK-OPS 前后端 Runtime 接口与前端调用关系的唯一真源。
> 任何新增、删除、重命名、字段调整、状态语义调整或调用入口调整，都必须在同一次变更中更新本文件。
> 编码约定：本文档和相关中文产品文档统一使用 UTF-8 无 BOM 保存；读取、生成、校验脚本必须显式按 UTF-8 处理，避免中文文案在 PowerShell、测试输出或 IDE 中出现乱码。

## 1. 使用规则

- 唯一性：不要再为单个模块创建并行 API 文档。模块计划、spec、测试说明可以引用本文件，但不能复制出另一套接口真源。
- 同步性：后端 route、service、schema、前端 `runtime-client.ts`、store、页面状态和 contract tests 任一项变化，都必须同步更新本文件。
- 入口约束：前端页面不得直接拼接 Runtime URL；所有 HTTP 调用必须先进入 `apps/desktop/src/app/runtime-client.ts`，再由 store 或页面消费。
- 信封约束：Runtime HTTP 成功统一返回 `{ "ok": true, "data": ... }`，失败统一返回 `{ "ok": false, "error": "中文可见错误" }`。
- 测试约束：接口变更必须同时更新 `tests/contracts/`；前端调用变更必须同时更新 `apps/desktop/tests/`。
- 文档优先级：当本文件与临时计划冲突时，先更新本文件，再进入实现；当本文件与 `docs/PRD.md`、`docs/UI-DESIGN-PRD.md`、`docs/ARCHITECTURE-BOOTSTRAP.md` 冲突时，先回到真源文档对齐。

## 2. 更新流程

每次接口或调用变更必须按以下顺序处理：

1. 更新本文件中的接口表、请求/响应字段、前端调用函数和测试入口。
2. 更新或新增后端 schema、route、service、repository。
3. 更新 `apps/desktop/src/types/runtime.ts`。
4. 更新 `apps/desktop/src/app/runtime-client.ts`。
5. 更新对应 Pinia store、页面状态和错误反馈。
6. 更新 contract tests、client tests、store/page tests。
7. 运行验证命令并记录结果。

验收时必须能回答：

- 后端接口在哪里定义。
- 前端通过哪个函数调用。
- 哪个 store 或页面消费。
- 成功和失败信封是什么。
- 哪个测试覆盖该契约。
- 本文件是否已同步更新。

## 3. 全局 Runtime 信封

成功响应：

```json
{
  "ok": true,
  "data": {}
}
```

失败响应：

```json
{
  "ok": false,
  "error": "操作失败，请稍后重试"
}
```

要求：

- `error` 必须是中文、用户可见、可恢复的提示。
- 不得向 UI 暴露 traceback。
- 后端异常必须记录日志。
- 404、409、422、500 等错误也必须通过统一信封转换。

## 4. M09 资产中心

> 2026-04-16 修订：Runtime 启动时会兼容修复旧版 `assets` 表，避免旧本地库缺少 `name`、`type`、`updated_at` 等列导致 `GET /api/assets` 直接 500，也避免旧版 `kind` / `file_name` 非空约束阻断新图片导入。点击“导入资产”必须弹出桌面文件选择器并支持多选；每个被选中的真实本地路径逐个通过 `importAsset(input)` 进入 Runtime。Tauri 主窗口 capability 必须包含 `dialog:allow-open`，否则文件选择器会被运行时权限拒绝；`tauri.conf.json` 必须启用 `app.security.assetProtocol` 并允许用户素材目录，否则 `convertFileSrc(filePath)` 生成的真实预览地址无法在 WebView 中读取。资产中心前端已采用素材墙、批量导入状态、真实本地预览、UTF-8 文档预览和全局右侧抽屉联动；页面不得回退到手动路径输入或图标占位预览。

### 4.1 数据对象

`AssetDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 资产 ID |
| `name` | `string` | 资产名称 |
| `type` | `string` | `video`、`audio`、`image`、`document`、`other` |
| `source` | `string` | `local`、`generated`、`imported` 等真实来源 |
| `filePath` | `string | null` | 本地文件路径 |
| `fileSizeBytes` | `number | null` | 文件大小，不能伪造 |
| `durationMs` | `number | null` | 媒体时长，未知时为 `null` |
| `thumbnailPath` | `string | null` | 缩略图路径，未生成时为 `null` |
| `tags` | `string | null` | JSON 字符串；前端展示前必须安全解析 |
| `projectId` | `string | null` | `null` 表示全局资产，非空表示项目资产 |
| `metadataJson` | `string | null` | 扩展元数据 JSON 字符串 |
| `createdAt` | `string` | 创建时间 |
| `updatedAt` | `string` | 更新时间 |

`AssetReferenceDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 引用 ID |
| `assetId` | `string` | 资产 ID |
| `referenceType` | `string` | `script`、`storyboard`、`timeline`、`render` 等引用类型 |
| `referenceId` | `string` | 引用对象 ID |
| `createdAt` | `string` | 创建时间 |

`AssetImportInput`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `filePath` | `string` | 真实本地文件路径，后端必须检查存在性 |
| `type` | `string` | `video`、`audio`、`image`、`document`、`other` |
| `source` | `string` | 默认 `local`，不得伪造来源 |
| `projectId` | `string | null` | 可选项目归属 |
| `tags` | `string | null` | 可选 JSON 字符串标签 |
| `metadataJson` | `string | null` | 可选扩展元数据 |

`AssetDeleteResult`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `deleted` | `boolean` | 删除是否完成 |

### 4.2 后端接口与前端调用

| 状态 | 方法 | 路径 | 后端入口 | 前端调用 | 消费方 | 测试 |
| --- | --- | --- | --- | --- | --- | --- |
| 当前 | `GET` | `/api/assets?type=&source=&project_id=&q=` | `api/routes/assets.py:list_assets` | `fetchAssets(type?, q?)` | `asset-library` store | `tests/contracts/test_runtime_page_modules_contract.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts` |
| 当前 | `POST` | `/api/assets` | `api/routes/assets.py:create_asset` | 暂无公开页面调用 | 后端测试/内部注册 | `tests/contracts/test_runtime_page_modules_contract.py` |
| 当前 | `POST` | `/api/assets/import` | `api/routes/assets.py:import_asset` | `importAsset(input)` | `asset-library` store、资产中心页面 | `tests/contracts/test_runtime_page_modules_contract.py`、`tests/runtime/test_asset_service.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts`、`apps/desktop/tests/runtime-stores-m09-m15.spec.ts`、`apps/desktop/tests/asset-library.spec.ts` |
| 当前 | `GET` | `/api/assets/{asset_id}` | `api/routes/assets.py:get_asset` | `fetchAsset(id)` | Runtime client、后续资产检查器编辑能力 | `tests/contracts/test_runtime_page_modules_contract.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts` |
| 当前 | `PATCH` | `/api/assets/{asset_id}` | `api/routes/assets.py:update_asset` | `updateAsset(id, input)` | Runtime client、后续资产检查器编辑能力 | `tests/contracts/test_runtime_page_modules_contract.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts` |
| 当前 | `DELETE` | `/api/assets/{asset_id}` | `api/routes/assets.py:delete_asset` | `deleteAsset(id)` | `asset-library` store | `tests/contracts/test_runtime_page_modules_contract.py`、`tests/runtime/test_asset_service.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts`、`apps/desktop/tests/runtime-stores-m09-m15.spec.ts` |
| 当前 | `GET` | `/api/assets/{asset_id}/references` | `api/routes/assets.py:list_asset_references` | `fetchAssetReferences(id)` | 资产检查器、删除确认 | `tests/contracts/test_runtime_page_modules_contract.py`、`apps/desktop/tests/runtime-client-m09-m15.spec.ts` |
| 当前 | `POST` | `/api/assets/{asset_id}/references` | `api/routes/assets.py:add_asset_reference` | 暂无公开页面调用 | 后端测试/其他模块注册引用 | `tests/contracts/test_runtime_page_modules_contract.py` |
| 当前 | `DELETE` | `/api/assets/references/{ref_id}` | `api/routes/assets.py:delete_asset_reference` | 暂无公开页面调用 | 后端测试/后续引用管理 | `tests/contracts/test_runtime_page_modules_contract.py` |
| 当前 | `GET` | `/api/assets/references/{ref_id}` | `api/routes/assets.py:get_reference` | 暂无公开页面调用 | 后端测试/后续引用管理 | `tests/contracts/test_runtime_page_modules_contract.py` |

### 4.3 `POST /api/assets/import`

当前已实现接口。

请求：

```json
{
  "filePath": "D:/tkops/assets/clip.mp4",
  "type": "video",
  "source": "local",
  "projectId": "project-1",
  "tags": "[\"开场\", \"产品镜头\"]"
}
```

成功响应：

```json
{
  "ok": true,
  "data": {
    "id": "asset-1",
    "name": "clip.mp4",
    "type": "video",
    "source": "local",
    "filePath": "D:/tkops/assets/clip.mp4",
    "fileSizeBytes": 123456,
    "durationMs": null,
    "thumbnailPath": null,
    "tags": "[\"开场\", \"产品镜头\"]",
    "projectId": "project-1",
    "metadataJson": null,
    "createdAt": "2026-04-16T10:00:00",
    "updatedAt": "2026-04-16T10:00:00"
  }
}
```

失败响应：

```json
{
  "ok": false,
  "error": "文件不存在，请确认本地路径后重试"
}
```

约束：

- 必须检查真实本地文件是否存在。
- 必须记录真实文件大小。
- 不生成假缩略图。
- 不生成假 AI 标签。
- 不伪造媒体时长。
- 普通导入注册不进入 TaskBus；后续资产分析才进入 TaskBus。
- 页面点击导入时不得无响应，不得使用 `alert`/`prompt` 或手动路径输入作为核心流程；必须调用桌面文件选择器，支持一次多选并逐个注册真实路径。
- 资产预览不使用假缩略图：视频、图片、可嵌入文档优先通过 `@tauri-apps/api/core` 的 `convertFileSrc(filePath)` 渲染真实本地文件；有 `thumbnailPath` 时优先渲染真实缩略图路径。该能力依赖 Tauri `assetProtocol.enable = true`，并且 `scope` 至少覆盖用户常用素材目录。
- `.txt`、`.md`、`.json`、`.csv`、`.srt` 等文本类文档不得直接交给 iframe 猜测编码；前端必须读取 `convertFileSrc(filePath)` 返回的内容，并按 UTF-8 文本预览渲染。PDF 保持 iframe 嵌入预览。

### 4.4 删除与引用影响范围

删除前端流程：

1. 用户在资产检查器触发删除。
2. store 调用 `fetchAssetReferences(assetId)`。
3. 如果引用列表非空，页面展示引用影响范围并禁用直接删除。
4. 如果引用列表为空，store 调用 `deleteAsset(assetId)`。
5. 删除成功后刷新资产列表并清空检查器。

后端要求：

- `DELETE /api/assets/{asset_id}` 必须在服务层检查引用关系。
- 存在引用时返回统一错误信封，中文错误说明引用影响。
- 删除成功返回 `{ "deleted": true }`。

### 4.5 旧版本地库兼容

历史本地库可能已经存在旧版 `assets` 表，字段为 `kind`、`file_name` 等旧命名，缺少当前 `AssetDto` 依赖的 `name`、`type`、`duration_ms`、`thumbnail_path`、`tags`、`updated_at` 等列。Runtime 初始化必须在 `initialize_domain_schema(engine)` 中执行兼容修复：

- 只补齐当前模型查询必需的缺失列。
- `file_name` 回填到 `name`，`kind` 回填到 `type`。
- `updated_at` 为空时回填为 `created_at`。
- 如旧列 `kind`、`file_name`、`mime_type` 带有非空约束并会阻断新 ORM 插入，允许原地重建 `assets` 表；重建必须保留旧数据和旧列值，不清空用户本地资产。
- 兼容修复必须由 `tests/runtime/test_asset_schema_migration.py` 覆盖。

## 4.6 TaskBus WebSocket 依赖

前端任务总线连接 `ws://127.0.0.1:8000/api/ws`。Runtime 运行环境必须安装 `websockets` 或 `wsproto` 之一；当前项目依赖固定为 `websockets>=14.0,<16.0`。如果缺少该依赖，Uvicorn 会记录 `No supported WebSocket library detected`，升级请求会退化成普通 `GET /api/ws` 并持续返回 404。

## 5. 前端调用登记表

| 函数 | 文件 | Runtime 路径 | 返回类型 | 主要消费方 | 更新要求 |
| --- | --- | --- | --- | --- | --- |
| `fetchAssets(type?, q?)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/assets` | `AssetDto[]` | `asset-library` store | 如新增筛选参数，必须同步本文件、类型和测试 |
| `fetchAssetReferences(id)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/assets/{id}/references` | `AssetReferenceDto[]` | `asset-library` store | 删除确认依赖该调用 |
| `deleteAsset(id)` | `apps/desktop/src/app/runtime-client.ts` | `DELETE /api/assets/{id}` | `AssetDeleteResult` | `asset-library` store | 删除前必须先检查引用；后端仍会阻断有引用资产 |
| `importAsset(input)` | `apps/desktop/src/app/runtime-client.ts` | `POST /api/assets/import` | `AssetDto` | `asset-library` store、资产中心页面 | 点击导入必须使用桌面文件选择器多选；只能注册真实本地文件路径，不生成假资产数据 |
| `fetchAsset(id)` | `apps/desktop/src/app/runtime-client.ts` | `GET /api/assets/{id}` | `AssetDto` | Runtime client、后续资产检查器编辑能力 | 如页面直接消费，必须补页面状态测试 |
| `updateAsset(id, input)` | `apps/desktop/src/app/runtime-client.ts` | `PATCH /api/assets/{id}` | `AssetDto` | Runtime client、后续资产检查器编辑能力 | 编辑能力开放时必须补 store/page 测试 |

前端本地预览调用登记：

| 调用 | 文件 | 用途 | 更新要求 |
| --- | --- | --- | --- |
| `convertFileSrc(filePath)` | `apps/desktop/src/components/assets/AssetPreview.vue` | 将真实本地视频、图片、文档路径转换为 WebView 可渲染地址；文本类文档读取后按 UTF-8 渲染 | 依赖 Tauri 桌面环境和 `app.security.assetProtocol`；不得用假缩略图替代真实文件预览 |

## 6. 验证命令

接口或调用文档变化后，至少运行：

```powershell
npm --prefix apps/desktop run test
venv\Scripts\python.exe -m pytest tests\contracts -q
```

如涉及页面、样式或 Runtime 服务层，还必须运行：

```powershell
npm --prefix apps/desktop run build
venv\Scripts\python.exe -m pytest tests\runtime -q
```

提交前检查：

```powershell
git diff --check --cached
```
