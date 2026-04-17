# Runtime 接口文档补齐与剩余后端接口收口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 `docs/RUNTIME-API-CALLS.md` 对当前已落地接口的登记，更新 `.claude/plan` 顶部状态口径，并按 `.claude/plan/backend` 的模块边界完成剩余未落地 Runtime 接口、测试与文档收口。

**Architecture:** 本轮按“先盘点真实现状与文档缺口，再同步历史计划状态，最后按模块批次补齐剩余接口”的顺序推进。后端继续沿用 `routes -> services -> repositories -> domain/models` 分层；对当前前端已消费且测试已覆盖的接口，不为了追平历史蓝图做破坏式重命名，优先通过补齐缺失端点、补文档或补兼容入口处理差异。

**Tech Stack:** FastAPI + SQLAlchemy + SQLite + pytest + Vue Runtime client + Pinia + `docs/RUNTIME-API-CALLS.md`

---

## Status

- 状态：Draft，待用户审批后进入 design spec。
- 创建时间：2026-04-17。
- 本计划覆盖接口文档补齐、`.claude/plan` 状态同步、M06/M11/M12/M13/M14/M15 剩余 Runtime 接口开发，以及相应测试与文档收口。
- 本计划不覆盖新的产品页扩展、不改变 16 页边界、不引入假业务数据、不把旧后台范围带回主线。
- 本计划默认在当前 `main` 工作树内执行；未经批准不跳过 plan/spec 直接实现。

## Council

### Council roles

- Project Leader
- Product Manager
- Backend Runtime Lead
- Data & Contract Agent
- Frontend Integration Agent
- QA & Verification Agent
- Independent Reviewer

### Facts found

- 当前 Runtime 已注册 route 文件 20 个，覆盖 `accounts / ai_capabilities / ai_providers / assets / automation / dashboard / device_workspaces / license / publishing / renders / review / scripts / settings / storyboards / subtitles / tasks / video_deconstruction / voice / workspace / ws`。
- 当前 `docs/RUNTIME-API-CALLS.md` 只形成了 M05、M07、M08、M09、M16 的主文档区块，以及一部分前端调用登记；尚未把 `license / dashboard / scripts / storyboards / video_deconstruction / tasks / ws / accounts / device_workspaces / automation / publishing / renders / review` 等已存在接口写成完整模块级接口文档。
- 当前 `.claude/plan/tkops-frontend-modules.md` 仍把多个已接线或已落地模块写成“待开发”；`.claude/plan/modules/` 与 `.claude/plan/backend/` 多份文档顶部状态仍停留在历史蓝图口径。
- M10 账号管理的 Runtime 基本接口已存在：账号 CRUD、分组 CRUD、成员增删、`refresh-stats` 已实现并被前端与测试消费；缺口主要在文档和历史计划状态同步。
- M11 设备与工作区当前只实现了 `workspaces` CRUD + `health-check`；`.claude/plan/backend/B-M11-device-workspace.md` 中的 `browser-instances` 与 `bindings` 仍未落地。
- M12 自动化执行中心当前实现了任务 CRUD、`trigger`、`runs` 列表；缺少按计划应有的 `run` 详情、取消运行、日志查询等接口。
- M13 发布中心当前实现了 `plans` CRUD、`precheck / submit / cancel`；缺少 `.claude/plan/backend/B-M13-publishing-center.md` 里的 `receipt` 查询接口。
- M14 渲染与导出中心当前实现了 `tasks` CRUD + `cancel`；缺少导出配置 `profiles`、失败任务 `retry` 等计划接口。
- M15 复盘与优化中心当前只实现了 `summary` 读取/更新与 `analyze`；缺少建议列表、建议生成、建议状态更新、`apply-to-script` 回流等计划接口。
- M06 视频拆解中心当前只实现了导入、列表、删除；`.claude/plan/backend/B-M06-video-deconstruction.md` 中的转写、切段、结构抽取和回流接口仍未落地。
- 现有前端 `runtime-client.ts`、stores 与 `tests/contracts/test_runtime_page_modules_contract.py` / `apps/desktop/tests/runtime-client-m09-m15.spec.ts` 已消费并校验 M10-M15 的部分基础接口；新增接口必须与现有 client/store 保持兼容并同步扩充测试。

### Role consensus

| 角色 | 结论 | 关键判断 | 风险 | 验收建议 |
| --- | --- | --- | --- | --- |
| Product Manager | 通过 | 这是主线接口与文档收口，不改变产品边界 | 历史 `.claude/plan` 容易被误当成当前事实 | 所有状态更新必须区分“历史蓝图 / 已接线 / 已落地 / 待深化” |
| Backend Runtime Lead | 通过 | 应优先补齐已存在 route 的唯一文档，再按模块补剩余端点 | 直接照抄历史计划可能和当前前端/测试冲突 | 以当前 route + service + runtime-client + tests 四点交叉核对 |
| Data & Contract Agent | 通过 | 新接口要进入统一 JSON 信封、schema、client、contract tests | 若只补后端不补文档/测试，会继续失真 | 每批接口必须同时更新 `docs/RUNTIME-API-CALLS.md` 与对应 contract/runtime tests |
| Frontend Integration Agent | 条件通过 | 已消费的接口不能被破坏式重命名 | 历史计划里的路径命名与当前 client 存在漂移 | 对现有 client 保持兼容，必要时补兼容端点而不是硬改 |
| QA & Verification Agent | 通过 | 这是跨模块 Runtime 收口，必须分批验证 | 一次性做完全部模块容易把失败点混在一起 | 每个批次都跑相关 contract/runtime/client tests，最后再跑全量回归 |
| Independent Reviewer | 8.1 / 10 | 方向正确，但必须拆批次，不适合单次直接实现全部 | 如果不拆，P1 风险是接口/文档/测试不同步 | 先完成 inventory 与 plan/spec，再按批次推进并保留中间提交点 |

### Leader decision

通过，且必须拆成三段推进：

1. **基线收口段**：补齐 `docs/RUNTIME-API-CALLS.md` 已完成接口文档，并更新 `.claude/plan` 顶部状态说明。
2. **核心接口补齐段**：完成 M06、M11、M12 的剩余接口，因为它们是后续自动化、发布、复盘的上游或执行上下文。
3. **下游接口补齐段**：完成 M13、M14、M15 的剩余接口，并再次回写唯一接口文档。

任何一段失败，都不能宣称“所有接口已完成”。

## Scope

### 本轮必须完成

- 把当前仓库里“已经落地”的 Runtime 接口完整写入 `docs/RUNTIME-API-CALLS.md`。
- 更新 `.claude/plan/tkops-frontend-modules.md`、`.claude/plan/modules/*.md`、`.claude/plan/backend/*.md` 顶部状态说明，使其与当前代码事实一致。
- 按 `.claude/plan/backend` 的模块边界完成以下剩余接口：
  - M06：转写、切段、结构抽取、回流到项目。
  - M11：`browser-instances` 与 `execution bindings`。
  - M12：`run` 详情、取消运行、运行日志。
  - M13：发布回执查询。
  - M14：导出配置 `profiles`、任务重试。
  - M15：建议列表、建议生成、建议状态更新、`apply-to-script`。
- 所有新增或补齐接口同步补：
  - schema / repository / service / route
  - `runtime-client.ts`（如前端需消费）
  - contract/runtime/frontend tests
  - `docs/RUNTIME-API-CALLS.md`

### 本轮明确不做

- 不新增产品页，不改变 16 页定义。
- 不把未接入的 AI Provider、真实 FFmpeg、真实发布 API 伪造成已完成。
- 不为追平历史计划而破坏当前前端已消费的路径与字段。
- 不清理用户未要求删除的 `.claude/plan` 历史内容；只补顶部状态和必要说明。
- 不修改 `docs/PRD.md`、`docs/UI-DESIGN-PRD.md`、`docs/ARCHITECTURE-BOOTSTRAP.md` 的产品/架构真源。

## File Map

### 文档与状态真源

- Modify: `docs/RUNTIME-API-CALLS.md`
- Modify: `docs/PROJECT-STATUS.md`
- Modify: `.claude/plan/tkops-frontend-modules.md`
- Modify: `.claude/plan/backend/README.md`
- Modify: `.claude/plan/backend/B-M06-video-deconstruction.md`
- Modify: `.claude/plan/backend/B-M10-account-management.md`
- Modify: `.claude/plan/backend/B-M11-device-workspace.md`
- Modify: `.claude/plan/backend/B-M12-automation-console.md`
- Modify: `.claude/plan/backend/B-M13-publishing-center.md`
- Modify: `.claude/plan/backend/B-M14-render-export.md`
- Modify: `.claude/plan/backend/B-M15-review-optimization.md`
- Modify: `.claude/plan/modules/M06-video-deconstruction-center.md`
- Modify: `.claude/plan/modules/M10-account-management.md`
- Modify: `.claude/plan/modules/M11-device-workspace-management.md`
- Modify: `.claude/plan/modules/M12-automation-console.md`
- Modify: `.claude/plan/modules/M13-publishing-center.md`
- Modify: `.claude/plan/modules/M14-render-export-center.md`
- Modify: `.claude/plan/modules/M15-review-optimization-center.md`

### M06 视频拆解

- Modify: `apps/py-runtime/src/api/routes/video_deconstruction.py`
- Modify: `apps/py-runtime/src/schemas/video_deconstruction.py`
- Modify: `apps/py-runtime/src/services/video_import_service.py`
- Modify: `apps/py-runtime/src/repositories/imported_video_repository.py`
- Modify: `apps/py-runtime/src/domain/models/imported_video.py`
- Add if needed: `tests/contracts/test_video_deconstruction_api.py`
- Add/Modify: `tests/runtime/test_video_import_service.py`

### M10 账号管理

- Modify if needed: `apps/py-runtime/src/api/routes/accounts.py`
- Modify if needed: `apps/py-runtime/src/schemas/accounts.py`
- Modify if needed: `apps/py-runtime/src/services/account_service.py`
- Modify if needed: `apps/py-runtime/src/repositories/account_repository.py`
- Modify if needed: `apps/desktop/src/app/runtime-client.ts`
- Modify: `tests/contracts/test_runtime_page_modules_contract.py`
- Modify if needed: `apps/desktop/tests/runtime-client-m09-m15.spec.ts`

### M11 设备与工作区

- Modify: `apps/py-runtime/src/api/routes/device_workspaces.py`
- Modify: `apps/py-runtime/src/schemas/device_workspaces.py`
- Modify: `apps/py-runtime/src/services/device_workspace_service.py`
- Modify: `apps/py-runtime/src/repositories/device_workspace_repository.py`
- Modify: `apps/py-runtime/src/domain/models/device_workspace.py`
- Modify if needed: `apps/desktop/src/app/runtime-client.ts`
- Modify if needed: `apps/desktop/src/stores/device-workspaces.ts`
- Modify: `tests/contracts/test_runtime_page_modules_contract.py`
- Add/Modify: `tests/runtime/*device*`
- Modify if needed: `apps/desktop/tests/runtime-client-m09-m15.spec.ts`

### M12 自动化执行中心

- Modify: `apps/py-runtime/src/api/routes/automation.py`
- Modify: `apps/py-runtime/src/schemas/automation.py`
- Modify: `apps/py-runtime/src/services/automation_service.py`
- Modify: `apps/py-runtime/src/repositories/automation_repository.py`
- Modify if needed: `apps/desktop/src/app/runtime-client.ts`
- Modify if needed: `apps/desktop/src/stores/automation.ts`
- Modify: `tests/contracts/test_runtime_page_modules_contract.py`
- Add/Modify: `tests/runtime/*automation*`
- Modify if needed: `apps/desktop/tests/runtime-client-m09-m15.spec.ts`
- Modify if needed: `apps/desktop/tests/runtime-stores-m09-m15.spec.ts`

### M13 发布中心

- Modify: `apps/py-runtime/src/api/routes/publishing.py`
- Modify: `apps/py-runtime/src/schemas/publishing.py`
- Modify: `apps/py-runtime/src/services/publishing_service.py`
- Modify: `apps/py-runtime/src/repositories/publishing_repository.py`
- Modify if needed: `apps/desktop/src/app/runtime-client.ts`
- Modify if needed: `apps/desktop/src/stores/publishing.ts`
- Modify: `tests/contracts/test_runtime_page_modules_contract.py`
- Add/Modify: `tests/runtime/*publishing*`
- Modify if needed: `apps/desktop/tests/runtime-client-m09-m15.spec.ts`
- Modify if needed: `apps/desktop/tests/runtime-stores-m09-m15.spec.ts`

### M14 渲染与导出

- Modify: `apps/py-runtime/src/api/routes/renders.py`
- Modify: `apps/py-runtime/src/schemas/renders.py`
- Modify: `apps/py-runtime/src/services/render_service.py`
- Modify: `apps/py-runtime/src/repositories/render_repository.py`
- Modify: `apps/py-runtime/src/domain/models/render.py`
- Modify if needed: `apps/desktop/src/app/runtime-client.ts`
- Modify if needed: `apps/desktop/src/stores/renders.ts`
- Modify: `tests/contracts/test_runtime_page_modules_contract.py`
- Add/Modify: `tests/runtime/*render*`
- Modify if needed: `apps/desktop/tests/runtime-client-m09-m15.spec.ts`
- Modify if needed: `apps/desktop/tests/runtime-stores-m09-m15.spec.ts`

### M15 复盘与优化

- Modify: `apps/py-runtime/src/api/routes/review.py`
- Modify: `apps/py-runtime/src/schemas/review.py`
- Modify: `apps/py-runtime/src/services/review_service.py`
- Modify: `apps/py-runtime/src/repositories/review_repository.py`
- Modify: `apps/py-runtime/src/domain/models/review.py`
- Modify if needed: `apps/desktop/src/app/runtime-client.ts`
- Modify if needed: `apps/desktop/src/stores/review.ts`
- Modify: `tests/contracts/test_runtime_page_modules_contract.py`
- Add/Modify: `tests/runtime/*review*`
- Modify if needed: `apps/desktop/tests/runtime-client-m09-m15.spec.ts`
- Modify if needed: `apps/desktop/tests/runtime-stores-m09-m15.spec.ts`

## Phase Plan

### 阶段 1：接口 inventory 与文档基线

目标：

- 把当前所有“已完成”接口从 route / schema / runtime-client / tests 四个维度盘点出来。
- 在 `docs/RUNTIME-API-CALLS.md` 中补出完整模块目录和接口登记，不遗漏已落地接口。

必须核对的模块：

- 基础：`license`、`dashboard`、`scripts`、`storyboards`、`settings`、`ai_capabilities`、`ai_providers`、`tasks`、`ws`
- 创作链：`workspace`、`video_deconstruction`、`voice`、`subtitles`、`assets`
- M10-M15：`accounts`、`device_workspaces`、`automation`、`publishing`、`renders`、`review`

输出：

- `docs/RUNTIME-API-CALLS.md` 新增或重组为“按模块区块 + 前端调用登记 + 验证命令”的完整文档。
- 每个接口至少登记：路径、方法、后端入口、前端调用、消费方、测试。

边界：

- 本阶段不宣称“后端已全部完成”；只记录当前真实已落地内容。

回退点：

- 如果发现某个接口只有 route 壳、没有 service/test，则在文档中标成“待补齐”，不伪装成已完成。

### 阶段 2：`.claude/plan` 顶部状态同步

目标：

- 把 `.claude/plan` 顶部状态说明同步成“历史蓝图 + 当前实现事实”的真实口径。

必须处理：

- 顶部生成日期后补充“当前状态 / 当前对应 superpowers 文档 / 是否已并入主干 / 是否仍待深化”。
- 对已经部分落地的模块，不能继续写“待开发”。
- 对与当前实现有路径或字段漂移的历史计划，必须明确“以下为历史蓝图，接口真源以 `docs/RUNTIME-API-CALLS.md` 和当前代码为准”。

输出：

- `.claude/plan/tkops-frontend-modules.md` 概览表状态修正。
- `.claude/plan/backend/*.md` 和 `.claude/plan/modules/*.md` 顶部状态修正。

边界：

- 不大改历史内容主体；只更新顶部状态与必要的真源提示。

回退点：

- 如果某份 `.claude/plan` 的正文和当前实现冲突太大，只补顶层“历史蓝图”声明，不在这一轮重写全文。

### 阶段 3：M06 剩余接口补齐

目标：

- 在不破坏现有视频导入链路的前提下，补齐转写、切段、结构抽取和回流到脚本的接口。

必做接口：

- `POST /api/video-deconstruction/videos/{id}/transcribe`
- `GET /api/video-deconstruction/videos/{id}/transcript`
- `POST /api/video-deconstruction/videos/{id}/segment`
- `GET /api/video-deconstruction/videos/{id}/segments`
- `POST /api/video-deconstruction/videos/{id}/extract-structure`
- `GET /api/video-deconstruction/videos/{id}/structure`
- `POST /api/video-deconstruction/extractions/{id}/apply-to-project`

策略：

- V1 可继续使用真实记录 + 规则生成 / `pending_provider`，但必须落库、可查询、可测试。
- `apply-to-project` 必须回到主链 `Project -> Script`，不能创建平行模型。

验证：

- `tests/contracts/test_video_deconstruction_api.py`
- `tests/runtime/test_video_import_service.py`

### 阶段 4：M11 / M12 剩余执行上下文接口

目标：

- 补齐设备执行上下文和自动化运行记录接口，为发布/执行链提供真实可审计对象。

M11 必做接口：

- `GET /api/devices/browser-instances`
- `POST /api/devices/browser-instances`
- `DELETE /api/devices/browser-instances/{id}`
- `GET /api/devices/bindings`
- `POST /api/devices/bindings`
- `DELETE /api/devices/bindings/{id}`

M12 必做接口：

- `GET /api/automation/runs/{run_id}`
- `POST /api/automation/runs/{run_id}/cancel`
- `GET /api/automation/runs/{run_id}/logs`

策略：

- 维持当前已存在的 `/api/automation/tasks/*` 结构，不破坏现有 client。
- 新增 `runs/*` 相关端点时，可以在同一 route 文件内追加，也可以拆新 route 文件；但必须保持服务层统一。

验证：

- `tests/contracts/test_runtime_page_modules_contract.py`
- 新增对应 `tests/runtime/*device*`、`tests/runtime/*automation*`
- 相关 `runtime-client` / store tests

### 阶段 5：M13 / M14 / M15 下游接口补齐

目标：

- 补齐发布回执、导出配置与重试、复盘建议回流等剩余接口。

M13 必做接口：

- `GET /api/publishing/plans/{id}/receipt`

M14 必做接口：

- `GET /api/renders/profiles`
- `POST /api/renders/profiles`
- `POST /api/renders/tasks/{task_id}/retry`

M15 必做接口：

- `GET /api/review/projects/{project_id}/suggestions`
- `POST /api/review/projects/{project_id}/suggestions/generate`
- `PATCH /api/review/suggestions/{id}`
- `POST /api/review/suggestions/{id}/apply-to-script`

策略：

- 发布、渲染、复盘的 V1 允许是规则化或 `manual_required`，但必须是真实持久化对象与真实错误/状态信封。
- `apply-to-script` 必须创建真实脚本新版本或草稿，不伪造“已应用”。

验证：

- `tests/contracts/test_runtime_page_modules_contract.py`
- 新增或扩展 `tests/runtime/*publishing*`、`tests/runtime/*render*`、`tests/runtime/*review*`
- 相关 `runtime-client` / store tests

### 阶段 6：全量接口文档回写与验收

目标：

- 把新增接口全部回写到 `docs/RUNTIME-API-CALLS.md`，并更新 `docs/PROJECT-STATUS.md` 与 `.claude/plan` 状态。

必须完成：

- 文档区块和前端调用登记同步。
- 当前已知差距只保留真实未完成项。
- 验收报告中明确哪些模块达到“已落地”、哪些仍是“已接线/待深化”。

## Verification Matrix

按批次至少运行：

- `venv\Scripts\python.exe -m pytest tests\contracts\test_runtime_page_modules_contract.py -q`
- `venv\Scripts\python.exe -m pytest tests\contracts\test_video_deconstruction_api.py -q`
- `venv\Scripts\python.exe -m pytest tests\runtime -q`
- `npm --prefix apps/desktop run test`
- `npm run version:check`
- `venv\Scripts\python.exe -m pytest tests\contracts\test_text_encoding_contract.py -q`
- `git diff --check`

最终收尾必须再跑：

- `git status --short --branch`
- `git branch --no-merged main`

## Acceptance Gates

- `docs/RUNTIME-API-CALLS.md` 覆盖当前全部已完成接口，不再遗漏已存在 route。
- `.claude/plan` 顶部状态不再把已接线模块写成“待开发”。
- M06/M11/M12/M13/M14/M15 剩余接口全部具备统一 JSON 信封、中文错误、service 层处理和测试。
- 已有前端 runtime-client / store 调用保持兼容。
- 不引入假任务、假 Provider 成功、假发布成功、假渲染完成。
- `tests/contracts`、`tests/runtime`、相关前端 tests 与文本编码校验通过。

## Risks

- 历史 `.claude/plan` 的端点命名与当前前端路径存在漂移，不能机械照抄。
- 一次性跨 6 个模块开发，若不分批提交，回归失败定位会很差。
- M15 `apply-to-script` 牵涉主链回流，若实现不当会破坏 `Project -> Script` 主模型。
- M06 转写/结构抽取若直接接入假 AI 结果，会违反仓库“真实或中性空态”约束。

## Rollback Strategy

- 每个模块批次独立提交，失败时只回退当前批次。
- 文档先记录真实现状；若实现批次未完成，不把计划接口写成“当前已完成”。
- 如新增接口与现有 client 冲突，优先保留现有路径并通过兼容端点或文档说明消解，不做大面积重命名。

## Notes For Spec

- design spec 必须明确：
  - `docs/RUNTIME-API-CALLS.md` 的新章节结构；
  - `.claude/plan` 顶部状态统一模板；
  - M06 / M11 / M12 / M13 / M14 / M15 每个模块的 DTO、route、service、空态与失败态；
  - 哪些接口需要前端新增 client/store 消费，哪些仅做后端与文档准备。

