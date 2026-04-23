# 工程债修复计划（2026-04-23）

> **来源**：V2 验收后遗留问题整理。所有 V2 功能缺陷（F-01~F-08 / B-01~B-06）已于 2026-04-22 合入 `main`（v0.4.2，315 passed），本文专门记录剩余**工程结构债**，与 V2 功能验收无关。
>
> **执行优先级**：P1（本迭代必须）/ P2（本迭代推进）/ P3（下迭代）
>
> **涉及硬约束**：`CLAUDE.md §6.1`——单文件超 400 行触发拆分评审，超 600 行强制拆分。

---

## 一、页面文件超标（9 个，均超 600 行硬线）

当前只有 `apps/desktop/src/pages/settings/` 完成了 `page / composable / helpers / types / styles` 分层范式（参照：`AISystemSettingsPage.vue` 414 行 + `use-*.ts` 4 个 composable + `types.ts`）。其余 9 个页面仍是单文件堆积。

### 整体拆分规范

每个页面目录结构目标：

```
pages/<module>/
├── <ModuleName>Page.vue       # 纯壳层：<template> + store 组装，<600 行
├── use-<feature>.ts           # composable：逻辑抽取，每个 <200 行
├── components/                # 页内专属组件
│   └── <SubComponent>.vue
├── types.ts                   # 页级 TS 类型（不含全局 runtime 类型）
└── <ModuleName>.module.css    # 样式抽离（可选，样式量大时使用）
```

**拆分原则**：
1. `<template>` 区段保留在页面 `.vue` 内，但模板里的大块 HTML 可提取为页内子组件
2. `<script setup>` 里的 `computed` / `function` / `watch` / `onMounted` 按**功能域**提取到对应 `use-*.ts`
3. `<style scoped>` 超过 200 行时抽离为 `.module.css`（使用 CSS Modules 语法）
4. 拆分后主文件目标行数 ≤ 500 行（模板 + 组合层 + 少量辅助计算）

---

### 1-A `VideoDeconstructionCenterPage.vue`（1040 行）— P1 最优先

**SFC 区段分布**：模板 1-252、脚本 254-446（192 行）、样式 448-1040（**593 行，样式是主体**）

**拆分方案**：

| 目标文件 | 内容 | 预估行数 |
|----------|------|----------|
| `VideoDeconstructionCenterPage.vue` | 模板壳 + store 组装 + 简单 computed | ~280 |
| `use-video-deconstruction.ts` | `handleImportVideo` / `handleApplyExtraction` / `handleRescan` / `handleRerunStage` / `isFfprobeUnavailable` / `selectedVideo` / `selectedVideoStages` / watch + onMounted | ~120 |
| `use-video-helpers.ts` | `pickVideoFilePath` / `formatDuration` / `formatFileSize` / `mapToAsset` / `getStageIcon` / `formatStageStatus` | ~80 |
| `VideoDeconstruction.module.css` | 将 448-1040 的 593 行样式抽离 | ~593 |

**执行步骤**：

- [ ] 新建 `apps/desktop/src/pages/video/use-video-deconstruction.ts`，迁移业务逻辑
- [ ] 新建 `apps/desktop/src/pages/video/use-video-helpers.ts`，迁移工具函数
- [ ] 新建 `apps/desktop/src/pages/video/VideoDeconstruction.module.css`，迁移所有样式
- [ ] 主页面引入 composable + `:class="$style.xxx"` CSS Modules 语法
- [ ] 验证：主文件 ≤ 500 行，`venv/Scripts/python.exe -m pytest tests/ -q` 全绿

---

### 1-B `PublishingCenterPage.vue`（965 行）— P1

**SFC 区段分布**：模板 1-263、脚本 265-464（199 行）、样式 466-965（**500 行**）

**拆分方案**：

| 目标文件 | 内容 | 预估行数 |
|----------|------|----------|
| `PublishingCenterPage.vue` | 模板壳 + store 引用 | ~270 |
| `use-publishing-actions.ts` | `handleCreate` / `handleDelete` / `handlePrecheck` / `handleSubmit` / `handleCancel` + 相关 computed | ~130 |
| `use-publishing-view.ts` | `filteredPlans` / `selectedPlan` / `plans`（含 `normalizePublishStatus`）/ 状态标签 computed | ~100 |
| `Publishing.module.css` | 样式抽离 | ~500 |

**执行步骤**：

- [ ] 新建 `apps/desktop/src/pages/publishing/use-publishing-actions.ts`
- [ ] 新建 `apps/desktop/src/pages/publishing/use-publishing-view.ts`
- [ ] 新建 `apps/desktop/src/pages/publishing/Publishing.module.css`
- [ ] 主页面精简至 ≤ 500 行

---

### 1-C `DeviceWorkspaceManagementPage.vue`（949 行）— P1

**SFC 区段分布**：模板 1-260、脚本 262-393（131 行）、样式 395-949（**555 行**）

**拆分方案**：

| 目标文件 | 内容 | 预估行数 |
|----------|------|----------|
| `DeviceWorkspaceManagementPage.vue` | 模板壳 | ~265 |
| `use-device-workspace.ts` | `handleCreate` / `handleDelete` / `handleHealthCheck` / `buildWorkspaceDetailContext` / `statusTone` / `statusLabel` / `formatDateTime` / `visibleWorkspaces` | ~120 |
| `DeviceWorkspace.module.css` | 样式抽离 | ~555 |

**执行步骤**：

- [ ] 新建 `apps/desktop/src/pages/devices/use-device-workspace.ts`
- [ ] 新建 `apps/desktop/src/pages/devices/DeviceWorkspace.module.css`
- [ ] 主页面精简至 ≤ 400 行

---

### 1-D `AssetLibraryPage.vue`（925 行）— P1

**SFC 区段分布**：模板 1-193、脚本 195-514（319 行，逻辑最复杂）、样式 516-925（409 行）

**拆分方案**：

| 目标文件 | 内容 | 预估行数 |
|----------|------|----------|
| `AssetLibraryPage.vue` | 模板壳 + store 组装 | ~200 |
| `use-asset-upload.ts` | `handleUpload` / `handleDragOver` / `handleDragLeave` / `handleDrop` / `importSuccessMessage` / `importProgress` / `importStatusLabel` / `importStatusHint` | ~130 |
| `use-asset-view.ts` | `visibleAssets` / `selectedAsset` / `selectedTags` / `visibleNotice` / `assetStatus` / `handleSearch` / `handleFilterType` / `handleSort` | ~100 |
| `AssetLibrary.module.css` | 样式抽离 | ~409 |

**执行步骤**：

- [ ] 新建 `apps/desktop/src/pages/assets/use-asset-upload.ts`
- [ ] 新建 `apps/desktop/src/pages/assets/use-asset-view.ts`
- [ ] 新建 `apps/desktop/src/pages/assets/AssetLibrary.module.css`
- [ ] 主页面精简至 ≤ 400 行

---

### 1-E `AutomationConsolePage.vue`（915 行）— P2

**SFC 区段分布**：模板 1-261、脚本 263-456（193 行）、样式 458-916（458 行）

**拆分方案**：

| 目标文件 | 内容 | 预估行数 |
|----------|------|----------|
| `AutomationConsolePage.vue` | 模板壳 | ~265 |
| `use-automation-actions.ts` | `handleCreate` / `handleDelete` / `handlePause` / `handleResume` / `handleTrigger` / `selectTask` | ~110 |
| `use-automation-view.ts` | `filteredTasks` / `selectedTask` / `selectedRuns` / `logSummary` / 各状态 computed | ~100 |
| `Automation.module.css` | 样式抽离 | ~458 |

**执行步骤**：

- [ ] 新建 `apps/desktop/src/pages/automation/use-automation-actions.ts`
- [ ] 新建 `apps/desktop/src/pages/automation/use-automation-view.ts`
- [ ] 新建 `apps/desktop/src/pages/automation/Automation.module.css`

---

### 1-F `RenderExportCenterPage.vue`（875 行）— P2

**SFC 区段分布**：模板 1-244、脚本 246-378（132 行）、样式 380-876（496 行）

**拆分方案**：

| 目标文件 | 内容 | 预估行数 |
|----------|------|----------|
| `RenderExportCenterPage.vue` | 模板壳 | ~248 |
| `use-render-actions.ts` | `handleCreate` / `handleCancel` / `handleRetry` / `selectTask` / `normalizeRenderStatus` | ~100 |
| `use-render-view.ts` | `filteredTasks` / `selectedTask` / 状态 computed / `isTaskBlocked` / `taskTone` / `taskStatusLabel` | ~90 |
| `RenderExport.module.css` | 样式抽离 | ~496 |

---

### 1-G `ScriptTopicCenterPage.vue`（834 行）— P2

**SFC 区段分布**：模板 1-173、脚本 175-389（214 行）、样式 391-834（443 行）

> 注：脚本区段已有 V2 状态栏 computed，是拆分的好时机。

**拆分方案**：

| 目标文件 | 内容 | 预估行数 |
|----------|------|----------|
| `ScriptTopicCenterPage.vue` | 模板壳 | ~175 |
| `use-script-editor.ts`（已存在同类模式）| `content` / `topic` / `instructions` / `generateDisabled` / `rewriteDisabled` / `handleGenerate` / `handleRewrite` / `handleCopy` | ~120 |
| `use-script-view.ts` | `pageState` / `displayedVersion` / `revisionLabel` / `statusLabel` / `statusTone` / `updatedAtLabel` / `currentSourceLabel` / watch + onMounted | ~110 |
| `ScriptTopic.module.css` | 样式抽离 | ~443 |

---

### 1-H `StoryboardPlanningCenterPage.vue`（772 行）— P2

**SFC 区段分布**：模板 1-145、脚本 147-367（220 行）、样式 369-772（403 行）

**拆分方案**：

| 目标文件 | 内容 | 预估行数 |
|----------|------|----------|
| `StoryboardPlanningCenterPage.vue` | 模板壳 | ~148 |
| `use-storyboard-actions.ts` | `handleGenerate` / `handleSceneSelect` / `handleSegmentSelect` / `handleApplyToProject` | ~100 |
| `use-storyboard-view.ts` | `pageState` / `isOutdated` / `scenes` / `selectedScene` / `scriptSegments` / watch + onMounted | ~130 |
| `Storyboard.module.css` | 样式抽离 | ~403 |

---

### 1-I `ReviewOptimizationCenterPage.vue`（681 行）— P2

**SFC 区段分布**：模板 1-185、脚本 187-373（186 行）、样式 375-681（306 行）

**拆分方案**：

| 目标文件 | 内容 | 预估行数 |
|----------|------|----------|
| `ReviewOptimizationCenterPage.vue` | 模板壳 | ~188 |
| `use-review-view.ts` | `visibleSuggestions` / `categorizedSuggestions` / `reviewState` / 各标签 computed（`heroTitle` / `heroSummary` / `feedbackMessage` 等 15 个） | ~150 |
| `use-review-actions.ts` | `handleIgnore` / `handleAnalyze` / `handleApply` / `goToDashboard` / `actionStates` | ~80 |
| `Review.module.css` | 样式抽离 | ~306 |

---

### 额外：`ProviderConfigDrawer.vue`（627 行，超评审线）— P3

位于 `pages/settings/components/`，本身已是 settings 分层下的子组件，但 627 行已接近拆分临界。

**拆分方案**：提取 `use-provider-config-form.ts`（表单状态 + 校验逻辑），使主组件降至 ~450 行。

---

## 二、RUNTIME-API-CALLS.md 文档债与计划纠偏

> 文档位置：`docs/RUNTIME-API-CALLS.md`
>
> 2026-04-23 已对照后端路由、FastAPI 注册结果、前端 Runtime client 与当前文档复核。结论：`M10 / M11 / M12` 的标准五列表已存在，当前真实剩余债务不是“后端缺路由”或“接口未登记”，而是 `M13 / M14` 文档损坏，以及本计划这一节的过期描述需要纠偏。

### 2-A M10 账号管理（`§11`）复核结论 — 已登记，无新增后端缺口

**后端文件**：`apps/py-runtime/src/api/routes/accounts.py`

**当前结论**：

- `§11` 已具备标准五列表，14 条路由均已登记，无需再派“补齐 M10 路由文档”任务
- 计划原文中“前端消费点”为 `stores/device-workspaces.ts` 的描述不准确；当前真实消费点应以账号管理 store / 页面为准
- 后续若继续维护本节，只需要在接口实际变更时做增量同步，不需要重复做一次文档补录

**保留动作**：

- [ ] 后续派工与周报中，不再把 M10 归类为“后端接口登记缺口”

---

### 2-B M11 设备与工作区管理（`§12`）复核结论 — 已登记，计划统计口径需修正

**后端文件**：`apps/py-runtime/src/api/routes/device_workspaces.py`

**当前结论**：

- `§12` 已具备标准五列表，不存在“真实 `workspaces/{ws_id}/browser-instances*` 未展开”的问题
- 当前文档已覆盖：
  - `workspaces*` 7 条 canonical 路由
  - `workspaces/{ws_id}/browser-instances*` 6 条 canonical 路由
  - `bindings*` 4 条 canonical 路由
  - `browser-instances*` 7 条 legacy alias
- 计划原文写“20 条路由”不准确；如果按 canonical 口径统计应为 17 条，若包含 legacy alias 则总计 24 条

**保留动作**：

- [ ] 后续派工与周报中，不再把 M11 归类为“后端接口登记缺口”
- [ ] 若继续引用数量口径，统一改为“17 条 canonical + 7 条 legacy alias”

---

### 2-C M12 自动化执行中心（`§13`）复核结论 — 已登记，路径描述需修正

**后端文件**：`apps/py-runtime/src/api/routes/automation.py`

**当前结论**：

- `§13` 已具备标准五列表，9 条路由均已登记，无需再派“补齐 M12 路由文档”任务
- 计划原文把接口写成 `/api/automation...`，这与当前后端和前端均不一致
- 当前真实 prefix 为 `/api/automation/tasks...`，后端、前端 Runtime client、文档三处已对齐

**保留动作**：

- [ ] 后续派工与周报中，不再把 M12 归类为“后端接口登记缺口”
- [ ] 统一把自动化接口口径修正为 `/api/automation/tasks...`

---

### 2-D M13 发布中心（`§14`）文档损坏修复 — P2

**后端文件**：`apps/py-runtime/src/api/routes/publishing.py`

**真实问题**：

- `§14` 当前不是“缺 11 条路由登记”，而是**标题、表头和大段中文说明发生乱码损坏**
- 路由条目本身已经存在，但当前文档已不适合作为前后端对接真源

**修复动作**：

- [ ] 将 `§14` 标题从乱码修正为 “M13 发布中心”
- [ ] 恢复表头为标准五列：`接口 / 请求参数 / 返回结果 / 错误码 / 当前前端调用点`
- [ ] 对照 `publishing.py`、前端 Runtime client 与现有条目，逐行修复被 `?` 污染的中文说明
- [ ] 修复示例、错误码说明、字段解释中的乱码，确保全文为 UTF-8 无 BOM

---

### 2-E M14 渲染与导出（`§15`）文档损坏修复 — P2

**后端文件**：`apps/py-runtime/src/api/routes/renders.py`

**真实问题**：

- `§15` 当前不是“缺 11 条路由登记”，而是**标题、表头和多处字段解释发生乱码损坏**
- 路由条目本身已经存在，但字段语义和错误码说明已不可靠

**修复动作**：

- [ ] 将 `§15` 标题从乱码修正为 “M14 渲染与导出中心”
- [ ] 恢复表头为标准五列：`接口 / 请求参数 / 返回结果 / 错误码 / 当前前端调用点`
- [ ] 对照 `renders.py`、前端 Runtime client 与现有条目，逐行修复被 `?` 污染的中文说明
- [ ] 修复 WebSocket 事件、示例、错误码说明中的乱码，确保全文为 UTF-8 无 BOM

---

## 三、其他遗留

### 3-A `CreatorDashboardPage.vue` 删除失败使用 `window.alert`（P2）

**位置**：`apps/desktop/src/pages/dashboard/CreatorDashboardPage.vue:310`

```typescript
window.alert("删除项目失败，请检查网络或稍后重试。");
```

**修复方案**：替换为统一错误状态反馈（Toast 或内联错误消息），与 `applyRuntimeError` 产生的 `store.error` 保持一致，不使用原生 alert。

---

### 3-B `use-system-settings.ts` 日志目录提示使用 `alert`（P3，低风险）

**位置**：`apps/desktop/src/pages/settings/use-system-settings.ts:65,72`

```typescript
alert("请先在路径设置中指定日志目录");
alert(`无法打开目录: ${logPath}\n请检查路径是否真实存在。`);
```

**修复方案**：通过 `shellUiStore.notify(...)` 或系统设置页内联消息替代，保持错误可见但不阻断用户流程。

---

### 3-C `.claude/plan/tkops-frontend-modules.md` 历史蓝图标注（P3）

文件仍沿用"待开发"口径，需在顶部增加：

```markdown
> ⚠️ 历史蓝图（已归档）：本文档为 M05-M15 阶段前期规划，当前实现状态以代码、
> `docs/superpowers/`、`CHANGELOG.md` 和 `docs/PROJECT-STATUS.md` 为准，
> 本文不再维护，禁止作为当前实现依据。
```

---

## 四、执行检查清单

### P1（本迭代，立即开工）

- [ ] **1-A** 拆分 `VideoDeconstructionCenterPage.vue`（1040 → ≤500 行）
- [ ] **1-B** 拆分 `PublishingCenterPage.vue`（965 → ≤500 行）
- [ ] **1-C** 拆分 `DeviceWorkspaceManagementPage.vue`（949 → ≤400 行）
- [ ] **1-D** 拆分 `AssetLibraryPage.vue`（925 → ≤400 行）
- [ ] **2-A** 同步派工与周报口径：撤销 M10 / M11 / M12 “后端接口登记缺口”表述
- [ ] **3-A** 替换 `CreatorDashboardPage.vue:310` 的 `window.alert`

### P2（本迭代，有序推进）

- [ ] **1-E** 拆分 `AutomationConsolePage.vue`（915 → ≤500 行）
- [ ] **1-F** 拆分 `RenderExportCenterPage.vue`（875 → ≤500 行）
- [ ] **1-G** 拆分 `ScriptTopicCenterPage.vue`（834 → ≤500 行）
- [ ] **1-H** 拆分 `StoryboardPlanningCenterPage.vue`（772 → ≤500 行）
- [ ] **1-I** 拆分 `ReviewOptimizationCenterPage.vue`（681 → ≤500 行）
- [ ] **2-D** 修复 `RUNTIME-API-CALLS.md` 中 M13 发布中心段落的标题、表头和中文说明乱码
- [ ] **2-E** 修复 `RUNTIME-API-CALLS.md` 中 M14 渲染与导出段落的标题、表头和中文说明乱码

### P3（下迭代）

- [ ] **1-J** 拆分 `ProviderConfigDrawer.vue`（627 → ≤450 行）
- [ ] **3-B** 替换 `use-system-settings.ts` 两处 alert
- [ ] **3-C** 标注 `.claude/plan/tkops-frontend-modules.md` 为历史蓝图

---

## 五、执行后验收标准

每个任务完成后必须满足对应验收项；页面拆分任务默认适用前 4 条，文档修复任务额外适用第 5 条：

1. `wc -l <主文件>` ≤ 500（P1 目标）或 ≤ 600（兜底硬线）
2. `venv/Scripts/python.exe -m pytest tests/runtime tests/contracts -q` — 全绿无回归
3. `npm --prefix apps/desktop run build` — 无 TS 类型错误
4. 新增的 `use-*.ts` 文件：每个 ≤ 200 行，无循环依赖
5. 文档修复任务需额外完成文本级一致性检查：标题无乱码、表头为标准五列、接口路径与 route / Runtime client 一致

---

*文档创建：2026-04-23 | 负责人：Claude Opus 4.7 | 下次 review：P1 完成后*
