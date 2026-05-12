# Subtitle Alignment Voice Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让字幕对齐中心优先基于当前项目最新已生成配音轨生成可编辑字幕时间码，并把脚本文案转换为可扫描表格。

**执行状态（2026-05-12）：** 已完成 0.4.4 收口；追加反馈补丁已覆盖 9:16 手机预览、行距/字幕框宽度、拖动定位、旧字幕轨道脏段落修正，以及旧脚本 `S01 0-5s` 前缀清理。

**Architecture:** 后端继续使用现有 `/api/subtitles` 契约，不新增页面；`SubtitleService` 在生成字幕时自动解析来源配音轨，能用配音片段时间码就沿用，缺失时按文本节奏生成可微调时间码并记录来源音轨快照。前端 `subtitle-alignment` store 统一读取脚本文档、字幕轨和最新配音轨，页面用独立表格组件展示脚本文案来源、段号、目标、字幕和时间码状态。

**Tech Stack:** Vue 3 + Pinia + Vitest；FastAPI + SQLAlchemy + Pytest；Runtime HTTP 统一 JSON 信封。

---

## 文件地图

- 修改 `apps/py-runtime/src/services/subtitle_service.py`：补自动选择最新可用配音轨、从配音轨快照生成字幕段、记录对齐来源与错误语义。
- 修改 `tests/runtime/test_subtitle_service.py`：覆盖无显式 `sourceVoiceTrackId` 时自动绑定最新 `ready` 配音轨，以及生成时间码和来源快照。
- 修改 `apps/desktop/src/modules/scripts/script-document-view-model.ts`：新增结构化脚本文案表格行提取函数，兼容 JSON 脚本与旧 Markdown。
- 修改 `apps/desktop/src/stores/subtitle-alignment.ts`：增加 `scriptRows`、`sourceVoiceTrack` 状态；加载时读取配音轨；生成字幕时传入最新配音轨 ID。
- 新增 `apps/desktop/src/modules/subtitles/SubtitleScriptTable.vue`：展示脚本文案表格，不承担服务调用。
- 修改 `apps/desktop/src/pages/subtitles/SubtitleAlignmentCenterPage.vue`：接入脚本文案表格，保留生成、保存和三栏编辑结构。
- 修改 `apps/desktop/src/modules/subtitles/SubtitlePreviewStage.vue`、`SubtitleStylePanel.vue`、`SubtitleTimingPanel.vue`：收敛预览台为纯画面窗口，并确保阻断草稿状态下右侧微调控件保持可编辑。
- 修改 `apps/desktop/src/pages/storyboards/components/StructuredTable.vue`、`apps/desktop/src/pages/scripts/components/ScriptStructuredPreview.vue`：加固结构化表格横向阅读宽度，避免长英文文案被压窄。
- 修改 `apps/py-runtime/src/services/ai_default_prompts.py`、`apps/py-runtime/src/services/storyboard_service.py`：明确英文脚本的中文说明字段边界，并清理分镜延续占位。
- 修改 `apps/desktop/tests/subtitle-alignment-store.spec.ts`：覆盖脚本文案表格行、自动来源配音轨和生成 payload。
- 修改 `apps/desktop/tests/subtitle-alignment-page.spec.ts`：覆盖页面显示脚本文案表格和来源配音状态。
- 修改 `apps/desktop/tests/page-responsive-layout-contract.spec.ts`、`apps/desktop/tests/storyboard-document-json.spec.ts`、`tests/runtime/test_storyboards.py`、`tests/runtime/test_ai_capabilities.py`：覆盖表格列宽、延续占位清理和 Prompt 语言边界。
- 修改 `docs/RUNTIME-API-CALLS.md`：补充字幕生成现在会自动绑定最新配音轨的契约说明。
- 修改 `CHANGELOG.md`、`package.json` 及版本同步文件：发布根版本真源对应的本轮版本号。

## 阶段任务

### Task 1: 后端自动绑定配音轨

- [ ] 在 `tests/runtime/test_subtitle_service.py` 先写失败测试：当项目存在最新 `ready` 配音轨且请求未传 `sourceVoiceTrackId`，`generate_track()` 应自动绑定该音轨。
- [ ] 运行 `pytest tests/runtime/test_subtitle_service.py::test_generate_track_auto_uses_latest_ready_voice_track -q`，确认失败原因是功能未实现。
- [ ] 在 `SubtitleService` 中使用现有 `VoiceRepository.list_tracks(project_id)` 选择最新 `status == "ready"` 的配音轨，不新增仓库特例。
- [ ] 让生成结果的 `sourceVoice.trackId`、`revision`、`alignment.status` 和 `task.sourceVoiceTrackId` 与自动选择的配音轨一致。
- [ ] 运行 `pytest tests/runtime/test_subtitle_service.py -q`，确认字幕服务回归通过。

### Task 2: 后端字幕段时间码生成规则

- [ ] 在 `tests/runtime/test_subtitle_service.py` 先写失败测试：来源配音轨有段落时间码时，字幕段应沿用同序号时间码；没有时间码时仍生成连续可编辑时间码。
- [ ] 运行对应 Pytest 单测，确认先失败。
- [ ] 在 `SubtitleService` 中新增小型私有辅助函数，职责限定为解析来源配音段、匹配同序号字幕段、生成连续时间码。
- [ ] 保持异常统一用 `HTTPException` 中文 detail，并保留 `log.exception` 记录仓库读取失败。
- [ ] 运行 `pytest tests/runtime/test_subtitle_service.py -q`。

### Task 3: 前端脚本文案表格数据

- [ ] 在 `apps/desktop/tests/script-document-json.spec.ts` 或 `subtitle-alignment-store.spec.ts` 先写失败测试：结构化 `segments` 应转换为段号、时间、目标、字幕文本的表格行。
- [ ] 运行对应 Vitest，确认失败。
- [ ] 在 `script-document-view-model.ts` 新增 `extractScriptDocumentSubtitleRows()`，只做纯数据转换，不引入页面状态。
- [ ] 在 `subtitle-alignment` store 中保存 `scriptRows`，并保留现有 `paragraphs/sourceText` 兼容生成链路。
- [ ] 运行 `npm --prefix apps/desktop run test -- subtitle-alignment-store.spec.ts script-document-json.spec.ts`。

### Task 4: 前端自动使用最新配音轨

- [ ] 在 `subtitle-alignment-store.spec.ts` 先写失败测试：`load()` 应读取 `/api/voice/projects/{project_id}/tracks` 并选中最新 `ready` 配音轨。
- [ ] 写失败测试：`generate()` 请求体应包含 `sourceVoiceTrackId`。
- [ ] 在 store 中复用 `fetchVoiceTracks`，不在组件内直接 fetch。
- [ ] 更新错误反馈：没有可用配音轨时仍允许生成草稿，但页面提示“先生成配音可获得更可靠时间码”。
- [ ] 运行字幕 store 相关 Vitest。

### Task 5: 页面脚本文案表格与状态反馈

- [ ] 新增 `SubtitleScriptTable.vue` 的页面测试，先验证“段号、时间、字幕、时间码状态”列出现并失败。
- [ ] 实现 `SubtitleScriptTable.vue`，使用现有 CSS Variables；支持加载、空态、正常态、错误态。
- [ ] 在 `SubtitleAlignmentCenterPage.vue` 左列接入表格，避免组件内直接请求 Runtime。
- [ ] 调整响应式布局，宽屏维持脚本表格/字幕段/预览/右侧工具的清晰层级，紧凑窗口纵向堆叠。
- [ ] 运行 `npm --prefix apps/desktop run test -- subtitle-alignment-page.spec.ts subtitle-alignment-store.spec.ts`。

### Task 6: 文档、版本与验证

- [ ] 更新 `docs/RUNTIME-API-CALLS.md` 的 M08 字幕契约说明。
- [ ] 更新 `CHANGELOG.md` 并 bump 到 `0.4.4`，运行 `npm run version:sync`。
- [ ] 运行 `npm run version:check`。
- [ ] 运行 `pytest tests/runtime/test_subtitle_service.py tests/contracts/test_runtime_contract_inventory.py -q`。
- [ ] 运行 `npm --prefix apps/desktop run test -- subtitle-alignment-store.spec.ts subtitle-alignment-page.spec.ts script-document-json.spec.ts`。
- [ ] 运行 `npm --prefix apps/desktop run build`。

### Task 7: 反馈补丁收口

- [ ] 移除字幕对齐中心顶部脚本文案摘要卡，脚本文案只保留表格视图。
- [ ] 将字幕校对台收敛为纯预览画面窗口，去掉说明文案和状态详情。
- [ ] 保证阻断草稿下右侧时间码和样式控件仍可编辑。
- [ ] 加固脚本/分镜表格列宽与横向滚动，避免英文长句或拍摄注意竖排。
- [ ] Prompt 中约束英文脚本只让面向观众的文案字段使用目标语言，制作说明字段保持中文。
- [ ] Runtime 保存 AI 分镜前清理“延续上句 / 同上”占位并回填来源脚本文案。

### Task 8: 字幕预览与旧轨道脏数据修复

- [x] 将字幕校对台预览画面固定为 9:16 手机窗口。
- [x] 样式面板增加行距和字幕框宽度，字体大小最小值保持 18。
- [x] 预览字幕支持拖动，并通过 `offsetX/offsetY` 回写到统一 `SubtitleStyleDto`。
- [x] 旧脚本文案中 `S01 0-5s` 类前缀只进入表格段号和时间，不进入字幕文案。
- [x] 加载历史脏字幕轨道时，按脚本文案表格行修正可编辑草稿，避免 5 行脚本显示成 7 段字幕。

## 边界与回退点

- 不新增新的字幕页面，不改变 16 页产品范围。
- 不伪装为声学级 forced alignment；本次仅做“配音轨来源绑定 + 段落级时间码生成 + 人工微调”。
- 不把字幕模板落到页面本地配置；样式仍沿用现有 `SubtitleStyleDto` 和后续资产中心模板边界。
- 如果自动配音轨选择引发异常，回退为现有无来源音轨草稿生成，并给出中文可见提示。
- 若构建或契约失败，先回退本次字幕相关文件，不影响已合并的配音 TTS2 链路。
