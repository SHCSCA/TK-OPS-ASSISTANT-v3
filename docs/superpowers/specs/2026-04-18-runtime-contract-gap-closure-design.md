# Runtime 契约缺口收口设计

## 目标

本轮只收口当前已经暴露出的 Runtime 契约缺口：

1. `prompt-templates` 后端真实存在，但 API 文档漏记。
2. `/api/search` 与 `/api/bootstrap` 已被前端类型和文档引用，但当前后端未落地。
3. `runtime-client.ts` 中仍保留若干孤儿 wrapper，与真实后端路由不一致。

## 设计决策

### 1. `/api/bootstrap`

- 新增独立 `bootstrap` route。
- 接口仅覆盖当前前端已声明的两个能力：
  - `POST /api/bootstrap/initialize-directories`
  - `POST /api/bootstrap/runtime-selfcheck`
- 返回字段严格对齐前端已有类型 `BootstrapDirectoryReport` 与 `RuntimeSelfCheckReport`。
- 不引入新配置入口；直接基于现有 runtime config、路径和基础运行环境给出真实检查结果。

### 2. `/api/search`

- 新增独立 `search` route 和轻量 search service。
- 仅聚合当前前端 `GlobalSearchResult` 已声明的六类对象：
  - `projects`
  - `scripts`
  - `tasks`
  - `assets`
  - `accounts`
  - `workspaces`
- 查询参数仅支持文档已声明的 `q`、`types?`、`limit?`。
- 若仓库现有 repository 能力不足，允许先做最小只读聚合，不扩出新业务字段。

### 3. 前端孤儿 wrapper

- 原则：页面未消费且后端无真实路由支撑的 wrapper，直接删除，不保留假兼容。
- 本轮优先清理：
  - `runAccountStatusCheck`
  - `fetchAutomationRun`
  - `cancelAutomationRun`
  - `fetchAutomationRunLogs`
  - `createExecutionBinding`
  - `fetchReviewSuggestions`
  - `generateReviewSuggestions`
  - `updateReviewSuggestion`
- `applyReviewSuggestionToScript` 若后端真实存在，则保留，但类型需与真实返回保持一致。

### 4. 文档真源

- `docs/RUNTIME-API-CALLS.md` 必须反映“当前真实代码”。
- 文档里不再写“已覆盖”但代码未落地的接口。
- `prompt-templates` 要作为独立模块登记，不再隐含在脚本模块描述中。

## 风险与边界

- 当前工作树已有未提交改动，特别是：
  - `apps/py-runtime/src/api/routes/__init__.py`
  - `apps/py-runtime/src/app/factory.py`
  - `apps/py-runtime/src/domain/models/render.py`
  - `docs/RUNTIME-API-CALLS.md`
- 本轮实现必须在这些改动基础上继续推进，不能回滚已有内容。
- `/api/search` 与 `/api/bootstrap` 采用最小真实实现，不借机扩功能。

## 验收标准

- 后端存在并注册 `/api/bootstrap` 与 `/api/search`。
- `prompt-templates` 被补入 API 文档。
- `runtime-client.ts` 不再保留本轮列出的孤儿 wrapper。
- 新增/更新测试通过，且相关契约测试能覆盖本轮改动。
