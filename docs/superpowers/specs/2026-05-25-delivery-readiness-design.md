# 2026-05-25 TK-OPS 交付可用性设计规格

## 1. 对应计划

对应计划：`docs/superpowers/plans/2026-05-25-delivery-readiness.md`

本规格先覆盖第一批执行切片：`阶段 1：信息架构与 UI 真实反馈`。后续阶段进入实现前，应按对应后端或主链路范围追加规格。

## 2. 设计目标

从用户视角先解决“打开后不可信、不一致、不可测”的问题：

- 侧边栏信息架构必须与 UI PRD 的五组结构一致。
- 桌面应用必须能验证紧凑窗口布局，不能被 Tauri 最小宽度阻断。
- 状态栏只能展示真实状态、未知态或诊断态，不能展示模拟延迟。
- M05 预览区必须清楚区分真实媒体预览与结构预览。
- AI 行动、播放、保存、离开等交互必须给出可见反馈，不能静默失败。

本阶段不实现真实渲染、不实现 TikTok 自动发布、不实现持久化任务总线。

## 3. 信息架构规格

PRD 与 UI PRD 定义的侧边栏分组为：

1. 启动与总览
2. 创作前置
3. 创作与媒体
4. 执行与治理
5. 系统与 AI

路由映射：

| 页面 | 路由 id | 分组 |
|------|---------|------|
| 创作总览 | `creatorDashboard` | 启动与总览 |
| 脚本与选题中心 | `scriptTopicCenter` | 创作前置 |
| 分镜规划中心 | `storyboardPlanningCenter` | 创作前置 |
| 视频拆解中心 | `videoDeconstructionCenter` | 创作前置 |
| AI 剪辑工作台 | `aiEditingWorkspace` | 创作与媒体 |
| 配音中心 | `voiceStudio` | 创作与媒体 |
| 字幕对齐中心 | `subtitleAlignmentCenter` | 创作与媒体 |
| 资产中心 | `assetLibrary` | 创作与媒体 |
| 账号管理 | `accountManagement` | 执行与治理 |
| 设备与工作区管理 | `deviceWorkspaceManagement` | 执行与治理 |
| 自动化执行中心 | `automationConsole` | 执行与治理 |
| 发布中心 | `publishingCenter` | 执行与治理 |
| 渲染与导出中心 | `renderExportCenter` | 创作与媒体 |
| 复盘与优化中心 | `reviewOptimizationCenter` | 执行与治理 |
| AI 与系统设置 | `aiSystemSettings` | 系统与 AI |
| 首启与许可证向导 | `setupLicenseWizard` | `HIDDEN` |

实现要求：

- `apps/desktop/src/types/router.ts` 应收窄 `navGroup` 类型，避免继续出现旧分组。
- `apps/desktop/src/app/router/route-manifest.ts` 应按上表更新分组，并与 `docs/PRD.md`、`docs/UI-DESIGN-PRD.md` 保持一致。
- `apps/desktop/src/layouts/AppShell.vue` 生成导航组时应按固定顺序输出，不依赖 manifest 中首次出现顺序。
- 旧分组 `全局管理`、`核心管线` 不应再出现在路由清单和侧边栏测试中。

## 4. 状态栏规格

当前状态栏有 `128ms` 模拟延迟风险。本阶段改为真实语义：

- Runtime 在线且 AI Provider 已配置：显示 `AI <provider> · 等待诊断` 或来自未来真实诊断字段的耗时。
- Runtime 在线但 AI 未配置：显示 `AI 未配置 · 待配置`。
- Runtime 离线：显示 `AI 状态未知 · Runtime 离线`。
- Runtime 加载中：显示 `AI 状态同步中`。

实现要求：

- 移除 `ShellStatusBar.vue` 中的固定 `128ms`。
- 文案使用中文，不展示 `Light` / `Dark`，改为 `浅色` / `深色`。
- 状态栏在窄屏下仍保持不重叠。
- 不新增本地假 Provider 指标；真实诊断字段进入配置总线后再扩展。

## 5. Tauri 窗口规格

UI PRD 要求覆盖桌面宽屏与紧凑窗口。当前 Tauri `minWidth: 1680` 阻断紧凑窗口验证。

实现要求：

- `apps/desktop/src-tauri/tauri.conf.json` 将 `minWidth` 调整为 `960`。
- `minHeight` 可保持不低于核心布局需求，但不能阻断常见 960 宽度验证。
- 保持默认启动宽度 `1680`，不降低宽屏首屏体验。
- 补充或更新 Tauri 配置测试，断言默认宽度与最小宽度分别满足宽屏和紧凑窗口要求。

## 6. M05 预览可信度规格

当前 `WorkspacePreviewStage.vue` 必须以“可信预览”为第一原则：能播放的才叫真实媒体预览，不能播放的只能叫结构预览或 Runtime 预览清单。

当前阶段的 Runtime 契约如下：

- `GET /api/workspace/timelines/{timeline_id}/preview` 返回 `TimelinePreviewDto`。
- `TimelinePreviewDto.previewUrl` 当前只允许是 `data:application/json` manifest，用于描述真实时间线、轨道、片段、时长和上下文。
- `previewUrl` 不是渲染视频地址，不得被前端作为 `<video>` 或 `<audio>` 的 `src` 使用。
- 结构预览可以读取该 manifest 的同步状态，但不得把 manifest 伪装成真实视频或音频。
- 真实媒体预览必须来自 Runtime 显式媒体契约；在契约落地前，前端必须保持 `structure` 模式。

禁止路径：

- 禁止从 `clip.metadata.mediaUrl`、`clip.metadata.previewUrl`、`clip.metadata.assetUrl` 猜测真实媒体地址。
- 禁止拼接本机 `file://`、Tauri `asset://` 或任意本地路径作为工作台媒体预览。
- 禁止无真实媒体文件时显示 `<video>` 或 `<audio>` 播放器。
- 禁止把结构预览、清单预览或 AI 生成计划描述成“已生成真实视频”。

数据设计：

- `WorkspacePreviewContext` 保留以下字段，但媒体字段在当前阶段必须由显式契约驱动：
  - `previewMode: "media" | "structure"`
  - `mediaUrl: string | null`
  - `mediaKind: "video" | "audio" | null`
  - `runtimePreviewUrl: string | null`
  - `truthLabel: string`
  - `truthDescription: string`
- 当前实现只允许 `runtimePreviewUrl` 保存 Runtime manifest 地址。
- `mediaUrl` 和 `mediaKind` 在没有 Runtime 显式媒体字段前必须为 `null`。
- 若 Runtime manifest 同步失败，UI 显示中文错误态，并保留重试或刷新路径，不静默失败。

后续真实媒体契约进入实现前，必须先追加本规格并更新 `docs/RUNTIME-API-CALLS.md`。建议字段边界如下：

- `previewMode: "manifest" | "media" | "unavailable"`
- `media.kind: "video" | "audio"`
- `media.url: string`
- `media.source: "render_task" | "voice_track" | "asset"`
- `media.expiresAt: string | null`
- `error.code: string | null`
- `error.message: string | null`

实现要求：

- `WorkspacePreviewStage.vue` 在 `structure` 模式顶部必须显示 `结构预览`，不能只写“播放器”。
- 无真实媒体时显示大预览舞台、9:16 / 16:9 切换、当前片段上下文和“仅结构预览”的中文说明。
- 若未来 `previewMode === "media"` 且 `mediaKind === "video"`，只允许使用 Runtime 显式 `media.url` 渲染 `<video controls>`。
- 若未来 `previewMode === "media"` 且 `mediaKind === "audio"`，只允许使用 Runtime 显式 `media.url` 渲染 `<audio controls>`。
- 音频片段不生成伪画面；字幕片段不生成伪视频。
- `data-testid="workspace-preview-phone"`、`workspace-preview-ratio-9-16`、`workspace-preview-ratio-16-9` 继续保留，避免布局合同失效。
- 新增或更新测试覆盖：无媒体 URL 时显示结构预览；Runtime manifest 存在时不渲染 video/audio；manifest 同步失败时显示中文错误说明。

## 6.1 M05 时间线同步与紧凑窗口规格

时间线要求：

- AI managed 轨道包括分镜、配音、字幕等由创作链路生成的轨道。
- AI managed 轨道必须以同一个时间线目标时长判定同步状态，不能用各自最长片段吞掉越界问题。
- 视觉 viewport 可以扩展到最长片段，方便用户看到越界内容；同步判定仍以目标时长为准。
- 手动轨道和资产临时轨道不显示 AI 同步徽标，避免误导用户认为它们必须等长。
- 三条 AI generated 轨道在后端组装时应按同一 reference timing 对齐；无法对齐时必须通过预检或同步状态给出中文提示。

紧凑窗口要求：

- 960 x 720 下 M05 首屏必须能看到大预览舞台的主体、基础时间线区域和状态反馈。
- 侧边栏处于抽屉状态时不得永久遮挡工作台；关闭抽屉后，预览区和时间线不得被固定侧栏挤压到不可用。
- 预览舞台在紧凑窗口下仍保留 9:16 / 16:9 切换，按钮文本不得溢出。
- 时间线工具栏在紧凑窗口下允许横向滚动或换行，但不能遮挡轨道内容。
- Detail Panel、素材池和基础属性区在紧凑窗口下可折叠或顺序下移，但不能压缩预览区到不可识别。

## 7. M05 交互反馈规格

本阶段只做体验真实性，不扩大 AI 功能范围：

- AI 行动入口若不可用，必须显示禁用原因或 Runtime 返回错误。
- 播放按钮只驱动当前结构预览进度，不宣称真实播放。
- 离开未保存时间线时，优先替换原生 `confirm` 为已有统一确认模式；若本阶段无法复用统一组件，至少应集中为可替换 helper，避免散落原生调用。
- 所有失败都保持中文提示，不暴露 traceback。

## 8. 测试规格

前端测试：

- `apps/desktop/tests/shell-layout-contract.spec.ts`
  - 断言五组导航名存在且旧分组不存在。
  - 断言 `AppShell` 使用固定导航组顺序。
  - 断言 `ShellStatusBar` 不包含 `128ms`。
- `apps/desktop/tests/tauri-capabilities.spec.ts`
  - 断言默认宽度仍为 1680。
  - 断言最小宽度为 960 或小于等于 960。
- `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
  - 断言结构预览标识。
  - 断言 Runtime manifest 存在时仍不渲染真实媒体元素。
  - 断言 9:16 / 16:9 切换存在且不触发媒体伪播放。
- `apps/desktop/tests/workspace-timeline-view-model.spec.ts`
  - 断言 AI managed 轨道用同一目标时长判定同步状态。
  - 断言视觉 viewport 扩展时仍能暴露 overflow / short 状态。
- `tests/runtime/test_workspace_assembly_service.py`
  - 断言分镜、配音、字幕等 AI managed 片段按 reference timing 对齐。
- `tests/contracts/test_workspace_runtime_contract.py`
  - 断言 `TimelinePreviewDto.previewUrl` 是 manifest 语义，不是媒体播放 URL。

验证命令：

```powershell
npm --prefix apps/desktop test -- shell-layout-contract
npm --prefix apps/desktop test -- tauri-capabilities
npm --prefix apps/desktop test -- ai-editing-workspace-page
npm --prefix apps/desktop test -- workspace-timeline-view-model
python -m pytest tests/runtime/test_workspace_assembly_service.py
python -m pytest tests/contracts/test_workspace_runtime_contract.py
npm --prefix apps/desktop run build
```

截图验证：

- 宽屏：1680 x 960，检查侧边栏五组、状态栏无假延迟。
- 紧凑：960 x 720，检查侧边栏抽屉、状态栏和 M05 预览无重叠。

## 9. 子代理执行顺序

1. `design-ux-architect`：复核五组导航、状态栏文案、M05 真实/结构预览边界。
2. `engineering-frontend-developer`：实现 route / shell / status bar / preview stage 改动。
3. `testing-reality-checker`：运行前端相关测试和构建，收集截图或失败证据。
4. `engineering-code-reviewer`：按 AGENTS.md 审核文件边界、中文注释、真实数据原则和测试覆盖。

主代理负责：

- 审核实现是否偏离 16 页产品范围。
- 防止把结构预览伪装为真实视频。
- 防止新增假指标、假数据或页面内业务规则。
- 控制阶段边界，不在本阶段扩展发布、渲染和任务总线。

## 10. 非目标

- 不实现真实 TikTok 自动发布。
- 不实现 FFmpeg 渲染输出。
- 不重构 `runtime-client.ts`、`runtime.ts` 等大文件。
- 不拆分后端大服务文件。
- 不变更 Runtime API 契约，除非只是前端可选读取已存在的元数据字段。
