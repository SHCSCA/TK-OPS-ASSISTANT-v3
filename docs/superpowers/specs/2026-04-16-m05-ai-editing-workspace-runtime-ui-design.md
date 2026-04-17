# M05 AI 剪辑工作台 Runtime 与 UI 最小闭环设计

> 计划来源：`docs/superpowers/plans/2026-04-16-m05-ai-editing-workspace-runtime-ui.md`  
> `.claude` 蓝图：`.claude/plan/modules/M05-ai-editing-workspace.md`、`.claude/plan/backend/B-M05-ai-editing-workspace.md`  
> 状态：Implemented，已于 2026-04-17 获批执行并合入 `main`
> 适用流程：`tkops-agent-council` + `tkops-ui-experience-council` + `tkops-runtime-contract-council`
> 实施结论：本设计对应的 M05-A 已落地，Runtime 已提供 `/api/workspace` 时间线读写与 `blocked` AI command，前端已拆分 page/store/modules/styles 并移除静态假轨道。
> 验证结论：前端 M05 page/store/runtime-client tests 与 Runtime service/contract 回归已通过，本次主线 build 和全量 tests 已重新验证。

## 1. 设计目标

M05 AI 剪辑工作台是 TK-OPS 的核心创作工作台。当前页面已经具备三栏布局、预览区、时间线和 AI 工具入口，但数据主要来自页面内静态数组和临时交互状态，不能作为最终交付。

本批 M05-A 目标是建立最小真实闭环：

- Runtime 提供项目级时间线草稿读取、创建和保存接口。
- 前端只通过 Runtime client 与 Pinia store 获取工作台数据。
- 页面不再展示静态假素材、假轨道、假视频进度或假 AI 结果。
- 无时间线时展示中性空态，引导创建真实草稿。
- 时间线存在时展示 Runtime 返回的轨道与片段。
- AI 魔法剪入口先走 Runtime 阻断态，明确说明本阶段尚未接入 AI Provider。
- 将 858 行页面拆分为页面 shell、workspace 组件、store、类型和样式。
- 更新 `docs/RUNTIME-API-CALLS.md`，保持接口文档唯一。

## 2. 非目标

- 不实现真实媒体播放、视频帧预览、缩略图生成或音频波形。
- 不接入 FFmpeg、渲染管线、导出文件或 M14 渲染任务。
- 不接入真实 AI 视频生成、魔法剪、自动转场、音频清洗或风格迁移 Provider。
- 不新增 `timeline_tracks`、`timeline_clips`、`workspace_ai_commands` 数据表。
- 不把 `.claude` 中的静态三轨示例当作真实结果。
- 不新增 WebGL、Three.js、GSAP 或重型动效依赖。
- 不修改路由树、16 页范围或导航分组。

## 3. Council 决议

Product Manager：通过。M05 是主链中枢，必须尽快从静态工作台切到真实项目时间线；第一批只做草稿闭环，不把范围扩大到专业剪辑软件。

Creative Director：有条件通过。页面视觉锚点必须是“预览窗口 + 时间线能量 + 右侧属性检查器”，不能变成普通后台表单或卡片墙。

Interaction Designer：通过。主路径是进入项目 -> 读取时间线 -> 无草稿时创建 -> 显示轨道/片段 -> 保存草稿 -> AI 命令显示阻断说明。错误和阻断要靠近工作对象展示。

Motion Engineer：通过。只使用 CSS transition 和必要的状态扫描动效；`prefers-reduced-motion` 下关闭重复扫描与位移动效。

Frontend Lead：通过。必须拆分当前 858 行页面，页面仅负责项目上下文和 store 编排；组件只渲染 DTO，不在组件内生成业务数据。

Backend Runtime Lead：通过。`/api/workspace` 路由保持薄层，业务在 `WorkspaceService`，数据访问在 `TimelineRepository`。错误使用中文信封，不暴露 traceback。

Data & Contract Agent：通过。M05-A 复用现有 `timelines.tracks_json`，避免本批迁移风险。前后端 DTO 必须一致，文档和测试同步更新。

AI Pipeline Agent：有条件通过。AI 魔法剪不能假装已开始，也不能生成假任务。未接入 Provider 时返回 `blocked`，后续真实 AI 命令另开 TaskBus/AI Provider 计划。

QA & Verification Agent：通过。必须覆盖 contract、service、runtime-client、store、page 测试，并跑前端全量测试、后端 contracts/runtime、build 与 `git diff --check`。

Independent Reviewer：评分 8.2 / 10。无 P0；P1 风险是页面继续堆进大文件或用假轨道填充视觉，该风险已转为强制拆分和空态要求。

Project Leader：已于 2026-04-17 获批执行，并按本设计完成 M05-A 合流到 `main`。

## 4. Runtime 契约

所有接口使用统一信封：

```json
{ "ok": true, "data": {} }
```

失败：

```json
{ "ok": false, "error": "中文可见错误" }
```

### 4.1 DTO

`WorkspaceTimelineClipDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 片段 ID，由前端或后续服务生成后保存 |
| `trackId` | `string` | 所属轨道 ID |
| `sourceType` | `asset \| imported_video \| voice_track \| subtitle_track \| manual` | 片段来源 |
| `sourceId` | `string \| null` | 来源对象 ID |
| `label` | `string` | UI 显示名称 |
| `startMs` | `number` | 时间线起点 |
| `durationMs` | `number` | 片段持续时间 |
| `inPointMs` | `number` | 素材入点 |
| `outPointMs` | `number \| null` | 素材出点 |
| `status` | `ready \| blocked \| missing_source \| error` | 片段状态 |

`WorkspaceTimelineTrackDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 轨道 ID |
| `kind` | `video \| audio \| subtitle` | 轨道类型 |
| `name` | `string` | 轨道名称 |
| `orderIndex` | `number` | 排序 |
| `locked` | `boolean` | 是否锁定 |
| `muted` | `boolean` | 是否静音或隐藏 |
| `clips` | `WorkspaceTimelineClipDto[]` | 片段列表 |

`WorkspaceTimelineDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 时间线 ID |
| `projectId` | `string` | 项目 ID |
| `name` | `string` | 时间线名称 |
| `status` | `draft \| committed` | 时间线状态 |
| `durationSeconds` | `number \| null` | 当前时长 |
| `source` | `manual \| imported_video \| generated` | 创建来源 |
| `tracks` | `WorkspaceTimelineTrackDto[]` | 轨道列表 |
| `createdAt` | `string` | UTC ISO 时间 |
| `updatedAt` | `string` | UTC ISO 时间 |

`WorkspaceTimelineResultDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `timeline` | `WorkspaceTimelineDto \| null` | 当前项目时间线，没有则为 `null` |
| `message` | `string` | 中文结果说明 |

`WorkspaceAICommandResultDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | `blocked` | 本批固定为阻断态 |
| `task` | `object \| null` | 本批不创建任务，固定 `null` |
| `message` | `string` | 中文阻断说明 |

### 4.2 API

`GET /api/workspace/projects/{project_id}/timeline`

- 用途：读取项目当前时间线草稿。
- 无草稿：返回 `timeline: null` 和中文引导。
- 有草稿：返回 `WorkspaceTimelineDto`。
- 前端调用：`fetchWorkspaceTimeline(projectId)`。

`POST /api/workspace/projects/{project_id}/timeline`

- 用途：创建空时间线草稿。
- 不自动填充示例轨道。
- 前端调用：`createWorkspaceTimeline(projectId, input)`。

`PATCH /api/workspace/timelines/{timeline_id}`

- 用途：保存时间线名称、时长、轨道和片段 JSON。
- 轨道类型只接受 `video/audio/subtitle`。
- 前端调用：`updateWorkspaceTimeline(timelineId, input)`。

`POST /api/workspace/projects/{project_id}/ai-commands`

- 用途：承接 AI 魔法剪入口。
- 本批返回 `blocked`，不创建假任务。
- 前端调用：`runWorkspaceAICommand(projectId, input)`。

## 5. Runtime 实现设计

`TimelineRepository`

- 查询项目当前时间线：按 `updated_at DESC` 取最新一条。
- 创建空草稿：`status="draft"`、`source="manual"`、`tracks_json="[]"`。
- 更新时间线：只更新 `name`、`duration_seconds`、`tracks_json`、`updated_at`。

`WorkspaceService`

- 解析 `tracks_json` 为 DTO。
- 如果历史脏数据导致 JSON 解析失败，记录 `log.exception(...)`，返回空轨道和中文说明，不让页面崩溃。
- 校验轨道类型和片段时间字段。
- 仓储异常统一转为中文 `HTTPException`。
- AI 命令返回阻断态，不创建 `AIJobRecord`，因为没有真实 Provider 调用。

`api/routes/workspace.py`

- 只做 service 调用和 `ok_response(...)` 包装。
- 不在 route 内拼业务规则。

## 6. 前端设计

### 6.1 数据流

页面进入：

1. `ProjectContextGuard` 确保当前项目存在。
2. 页面从项目上下文 store 读取 `currentProjectId`。
3. `editing-workspace` store 调用 `fetchWorkspaceTimeline(projectId)`。
4. `timeline: null` 时进入 `empty` 状态。
5. 用户点击“创建时间线草稿”后调用 `createWorkspaceTimeline()`。
6. 用户保存轨道变更时调用 `updateWorkspaceTimeline()`。
7. 用户点击“AI 魔法剪”后调用 `runWorkspaceAICommand()` 并显示 `blocked` 信息。

### 6.2 组件结构

`AIEditingWorkspacePage.vue`

- 路由级 shell。
- 只处理项目上下文、store 加载、事件转发和布局。

`WorkspaceToolbar.vue`

- 选择、剪切、缩放、保存、AI 魔法剪入口。
- 显示 loading/saving/blocked/disabled。

`WorkspaceAssetRail.vue`

- 左侧素材和来源提示。
- M05-A 不展示假素材；无资产接入时显示“资产中心导入后会出现在这里”。

`WorkspacePreviewStage.vue`

- 中央预览舞台。
- 无真实视频时显示项目时间线状态和选中片段信息。
- 不显示假播放进度。

`WorkspaceTimeline.vue`

- 只渲染 Runtime 返回的 `tracks` 和 `clips`。
- 无轨道时显示“当前时间线还没有轨道”。
- 选中轨道/片段后通知 store。

`WorkspaceInspector.vue`

- 右侧属性与诊断。
- 显示选中轨道、选中片段、时间线保存状态和 AI 阻断原因。

`WorkspaceStateNotice.vue`

- loading、empty、error、blocked 的就近反馈。
- 提供重试、创建草稿、关闭提示动作。

### 6.3 状态矩阵

| 状态 | UI 行为 |
| --- | --- |
| `loading` | 保持工作台骨架，提示正在读取项目时间线 |
| `empty` | 显示创建草稿入口，不显示假轨道 |
| `ready` | 展示 Runtime 时间线、轨道、片段和 inspector |
| `saving` | 保存按钮禁用，时间线尺寸稳定 |
| `blocked` | AI 操作显示中文阻断说明，可继续编辑 |
| `error` | 中文错误靠近工作区展示，提供重试 |
| `disabled` | 无项目、无时间线或保存中时说明动作不可用原因 |

## 7. 视觉与交互

Visual thesis:
这个页面应像“轻量剪辑控制台”，以预览舞台和时间线作为视觉重心，用稳定的轨道层级和右侧检查器支撑创作者判断当前工程能否继续推进。

Primary workspace:
宽屏采用左侧素材来源区、中部预览与时间线、右侧检查器。紧凑窗口中右侧检查器下移或转为可折叠区域，不挤压时间线核心区。

Core interaction:

1. 进入页面先判断有没有真实时间线。
2. 没有草稿时创建真实空草稿。
3. 选中轨道或片段后右侧显示属性和状态。
4. AI 魔法剪未接入时就近显示阻断态，而不是弹窗或假进度。

Motion purpose:

- 时间线片段 hover、选中、阻断提示出现可使用 160-220ms transition。
- AI 阻断提示可短暂高亮，但不做持续扫描。
- `prefers-reduced-motion: reduce` 关闭重复动画。

## 8. 错误与恢复

Runtime 离线：

- store 进入 `error`，显示“读取时间线失败，请检查 Runtime 后重试。”
- 保留已有 timeline，不清空用户可见上下文。

创建失败：

- 保持 `empty`，显示失败原因和重试按钮。

保存失败：

- 保留当前前端草稿，显示“保存失败，草稿未丢失。”

AI 阻断：

- 不算错误，不清空状态。
- 显示“AI 剪辑命令尚未接入 Provider，本阶段仅保存时间线草稿。”

历史 JSON 异常：

- Runtime 记录异常。
- UI 收到空轨道和中文说明，引导用户重新保存草稿。

## 9. 测试与验收

后端：

- Contract：接口信封、字段、空态、创建、更新、AI 阻断。
- Service：JSON 解析、轨道校验、仓储异常、时间线保存。

前端：

- Runtime client：路径、方法、请求体。
- Store：loading、empty、ready、saving、blocked、error。
- Page：项目上下文加载、空态创建、真实轨道渲染、AI 阻断反馈、旧静态内容移除。

验收命令：

```powershell
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\contracts\test_workspace_runtime_contract.py -q
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\runtime\test_workspace_service.py -q
npm --prefix apps/desktop run test -- runtime-client-workspace.spec.ts editing-workspace-store.spec.ts ai-editing-workspace-page.spec.ts
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\contracts -q
apps\py-runtime\venv\Scripts\python.exe -m pytest tests\runtime -q
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
git diff --check
```

UI 验收：

- 宽屏截图或人工记录：左 rail、中预览、时间线、右 inspector 可读。
- 紧凑窗口截图或人工记录：时间线不被挤压，inspector 可访问。
- Light/Dark 检查：轨道、错误、禁用、阻断状态可辨识。
- 空态检查：无假轨道、假素材、假视频进度。

## 10. 后续计划

M05-B 可考虑：

- 轨道/片段表规范化迁移。
- 资产中心资产拖入时间线。
- 配音轨和字幕轨回写时间线。
- AI 魔法剪进入 TaskBus 和 AI Provider 日志。
- 与 M14 渲染导出中心共享 Timeline 输入。

这些都需要独立 plan/spec，不进入 M05-A。

