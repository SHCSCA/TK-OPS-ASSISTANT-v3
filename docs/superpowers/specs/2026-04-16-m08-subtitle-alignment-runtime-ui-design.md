# M08 字幕对齐中心 Runtime 与 UI 闭环设计

> 计划来源：`docs/superpowers/plans/2026-04-16-m08-subtitle-alignment-runtime-ui.md`
> 接口真源：`docs/RUNTIME-API-CALLS.md`
> 状态：Implemented，用户已于 2026-04-16 确认通过并完成实现
> 适用流程：`tkops-agent-council` + `tkops-ui-experience-council` + `tkops-runtime-contract-council`

## 1. 设计目标

M08 字幕对齐中心要从当前“前端模拟对齐 + 页面内临时字幕”升级为创作者可用的字幕校对台。第一批只做真实 Runtime 闭环和 UI 交互底座，不接入真实外部字幕对齐 Provider，不伪造成精准时间码完成。

本轮目标：

- 建立 `/api/subtitles` 最小 Runtime 契约，包含项目字幕轨列表、生成字幕草稿、查询详情、更新字幕轨和删除版本。
- 生成动作必须落库为真实 `SubtitleTrack`；无字幕对齐 Provider 或无真实音频时返回 `blocked` 状态和中文说明。
- 字幕段落必须来自真实项目脚本文本切分，不使用固定 5 条静态示例字幕。
- 前端移除 `setTimeout` 模拟对齐、随机假字幕和页面内直接 Runtime 调用。
- 页面拆分为 Studio 工作台组件，覆盖字幕段落、预览叠字、时间码校正、样式面板和版本列表。
- 字幕结果保留段落级映射，为后续配音、时间线和 AI 剪辑工作台回流预留真实数据结构。
- 更新 `docs/RUNTIME-API-CALLS.md`，保持接口文档唯一且及时。

本轮非目标：

- 不接入 OpenAI、Whisper、Azure、本地 ASR 或任何真实字幕对齐 Provider。
- 不生成假转写、假精准时间码、假视频播放进度、假任务成功。
- 不实现 SRT 文件导入/导出落盘。
- 不把字幕模板做成页面本地孤立配置；字幕模板资产化后续由资产中心承接。
- 不新增数据库表；优先复用现有 `subtitle_tracks` 表。
- 不引入 GSAP、Three.js、WebGL 或其他重型动效依赖。

## 2. Council 决议

Product Manager：通过。M08 是 16 页内核心创作媒体链路，第一批应聚焦字幕轨真实记录、段落编辑、时间码校正和版本管理，不扩展成字幕模板商城或协作后台。

TK Operations：通过。TikTok 创作者关注的是字幕能否解释来源、修正节奏并进入后续时间线。无 Provider 时可以保存草稿，但不能声称自动对齐完成。

Creative Director：有条件通过。页面应像“字幕校对台”，视觉锚点来自字幕段落、时间码、预览叠字和版本诊断，不做普通表格页或按钮堆叠页。

Interaction Designer：通过。主路径是读取脚本 -> 生成字幕草稿 -> 选中字幕段 -> 校正文案和时间码 -> 保存版本。无项目、空脚本、无 Provider、保存失败、删除失败都必须有就近中文反馈。

Motion Engineer：通过。本批只使用 CSS/Vue transition。允许字幕段落进入、选中锚点、对齐中轻量扫描；`prefers-reduced-motion` 下必须关闭位移和持续动画。

Backend Runtime Lead：有条件通过。路由必须薄，业务在 service，错误进入统一信封，不向 UI 暴露 traceback。无 Provider 是可预期业务状态，不是 500。

Data & Contract Agent：通过。沿用现有 `subtitle_tracks` 表，`segments_json` 保存字幕段，`style_json` 保存样式配置，避免本批扩大迁移范围。

AI Pipeline Agent：有条件通过。必须明确 `pending_provider` 不是 Provider 成功；真实字幕对齐接入必须另开 plan，补 AI 调用日志、耗时、失败原因、音频源和 TaskBus。

Frontend Lead：通过。必须拆组件，页面根组件只负责编排；Runtime client 是唯一 HTTP 入口；store 负责加载、生成、保存、删除和错误态。

QA & Verification Agent：通过。后端 contract/service、前端 client/store/page 测试都必须覆盖；全量前端测试、build、后端 contracts/runtime 都要跑。

Independent Reviewer：评分 8.3 / 10。无 P0；P1 风险已转为设计约束：不得假时间码、接口文档必须同步、页面不得继续静默失败或 alert。

Project Leader：批准本 design spec 进入用户审批；审批通过后才能实现。

实现结果：已按本 design spec 完成 M08-A。新增 `/api/subtitles` Runtime 契约、字幕轨 service/repository/route、前端 Runtime client/store、字幕校对台组件拆分和页面装配；无 Provider 时保存真实字幕草稿并显示 `blocked` 中文状态，不伪造精准时间码或视频播放结果。

验证结果：`npm --prefix apps/desktop run test`、`npm --prefix apps/desktop run build`、`venv\Scripts\python.exe -m pytest tests\contracts -q`、`venv\Scripts\python.exe -m pytest tests\runtime -q`、`venv\Scripts\python.exe -m pytest tests\contracts\test_text_encoding_contract.py -q` 已通过。Vite build 的 Material Symbols 字体运行时解析提示为已知非阻断项。

## 3. Runtime 契约

### 3.1 统一信封

所有 `/api/subtitles` 接口继续使用统一信封：

```json
{ "ok": true, "data": {} }
```

失败：

```json
{ "ok": false, "error": "中文可见错误" }
```

要求：

- `error` 必须可直接展示给用户。
- 业务阻断使用中文说明，不把 traceback 暴露给前端。
- route 不拼业务逻辑；route 只调用 `SubtitleService`。
- 本批不创建长任务；真实字幕对齐 Provider 接入后再进入 TaskBus。

### 3.2 DTO

`SubtitleStyleDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `preset` | `string` | 当前样式预设，默认 `creator-default` |
| `fontSize` | `number` | 字号，默认 32，范围 18 到 72 |
| `position` | `bottom \| center \| top` | 字幕位置 |
| `textColor` | `string` | 字幕文字颜色 |
| `background` | `string` | 字幕背景，允许 `rgba(...)` |

`SubtitleSegmentDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `segmentIndex` | `number` | 字幕段序号，从 0 开始 |
| `text` | `string` | 字幕文本 |
| `startMs` | `number \| null` | 起始时间；无真实对齐时为 `null` |
| `endMs` | `number \| null` | 结束时间；无真实对齐时为 `null` |
| `confidence` | `number \| null` | 后续 Provider 置信度；本批为 `null` |
| `locked` | `boolean` | 用户是否手动锁定该段 |

`SubtitleTrackDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 字幕轨 ID |
| `projectId` | `string` | 项目 ID |
| `timelineId` | `string \| null` | 后续时间线 ID |
| `source` | `script \| manual \| provider` | 字幕来源；本批生成默认为 `script` |
| `language` | `string` | 语言，如 `zh-CN` |
| `style` | `SubtitleStyleDto` | 字幕样式 |
| `segments` | `SubtitleSegmentDto[]` | 字幕段落 |
| `status` | `blocked \| ready \| error \| aligning` | 字幕轨状态 |
| `createdAt` | `string` | UTC ISO 时间 |

`SubtitleTrackGenerateInput`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `sourceText` | `string` | 待生成字幕草稿的脚本文本 |
| `language` | `string` | 默认 `zh-CN` |
| `stylePreset` | `string` | 默认 `creator-default` |

`SubtitleTrackUpdateInput`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `segments` | `SubtitleSegmentDto[]` | 用户校正后的字幕段 |
| `style` | `SubtitleStyleDto` | 用户调整后的字幕样式 |

`SubtitleTrackGenerateResultDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `track` | `SubtitleTrackDto` | 已创建的字幕轨记录 |
| `task` | `TaskInfo \| null` | 本批无真实任务时为 `null` |
| `message` | `string` | 中文结果说明 |

### 3.3 接口

`GET /api/subtitles/projects/{project_id}/tracks`

- 作用：获取项目字幕轨版本列表。
- 前端调用：`fetchSubtitleTracks(projectId)`
- 消费方：`subtitle-alignment` store、`SubtitleVersionPanel.vue`
- 返回排序：`createdAt DESC`
- 测试：`tests/contracts/test_subtitle_runtime_contract.py`、`apps/desktop/tests/runtime-client-subtitles.spec.ts`

`POST /api/subtitles/projects/{project_id}/tracks/generate`

- 作用：根据脚本文本创建字幕轨草稿。
- 前端调用：`generateSubtitleTrack(projectId, input)`
- 无 Provider：返回 `track.status = "blocked"`、`task = null`、中文 message。
- 空文本：返回失败信封，错误为“字幕源文本为空，请先在脚本与选题中心创建内容。”

`GET /api/subtitles/tracks/{track_id}`

- 作用：获取单条字幕轨详情。
- 前端调用：`fetchSubtitleTrack(trackId)`

`PATCH /api/subtitles/tracks/{track_id}`

- 作用：保存字幕文本、时间码和样式校正。
- 前端调用：`updateSubtitleTrack(trackId, input)`
- 成功后返回更新后的 `SubtitleTrackDto`。

`DELETE /api/subtitles/tracks/{track_id}`

- 作用：删除未被使用的字幕版本。
- 前端调用：`deleteSubtitleTrack(trackId)`
- 后续若存在时间线引用，必须返回 409 统一错误信封。

## 4. 后端设计

### 4.1 Schema

创建 `apps/py-runtime/src/schemas/subtitles.py`：

- `SubtitleStyleDto`
- `SubtitleSegmentDto`
- `SubtitleTrackDto`
- `SubtitleTrackGenerateInput`
- `SubtitleTrackUpdateInput`
- `SubtitleTrackGenerateResultDto`

命名采用前端友好的 camelCase 字段，Pydantic schema 负责输出 DTO，不把 ORM 字段名直接泄漏给页面。

### 4.2 Repository

创建 `apps/py-runtime/src/repositories/subtitle_repository.py`：

- `list_tracks(project_id: str) -> list[SubtitleTrack]`
- `create_track(track: SubtitleTrack) -> SubtitleTrack`
- `get_track(track_id: str) -> SubtitleTrack | None`
- `update_track(track_id, segments_json, style_json, status) -> SubtitleTrack | None`
- `delete_track(track_id: str) -> bool`

约束：

- `segments_json` 保存 JSON 数组，不保存 Python repr。
- `style_json` 保存样式对象，不保存前端临时状态。
- 删除不存在的记录由 service 转为中文 404。
- 查询列表按 `created_at DESC`。

### 4.3 Service

创建 `apps/py-runtime/src/services/subtitle_service.py`：

- `list_tracks(project_id)`
- `generate_track(project_id, payload)`
- `get_track(track_id)`
- `update_track(track_id, payload)`
- `delete_track(track_id)`

段落切分：

- 使用 `sourceText.splitlines()`。
- 去掉纯空行。
- 保留中文标点和原句内容。
- `segmentIndex` 从 0 开始。
- 本批不推断真实 `startMs/endMs`，无真实对齐时保留 `null`。

无 Provider 策略：

- `source = "script"`。
- `status = "blocked"`。
- `message = "尚未配置可用字幕对齐 Provider，已保存字幕草稿。"`
- `task = None`。
- 不创建 TaskBus 任务，不广播假进度。

错误策略：

- 空文本返回 400：“字幕源文本为空，请先在脚本与选题中心创建内容。”
- 字幕轨不存在返回 404：“字幕版本不存在”。
- 数据库异常使用 `log.exception(...)` 记录，返回中文 500。

### 4.4 Route 与依赖注入

创建 `apps/py-runtime/src/api/routes/subtitles.py`，前缀为 `/api/subtitles`。

更新：

- `apps/py-runtime/src/api/routes/__init__.py`
- `apps/py-runtime/src/app/factory.py`

依赖注入：

- `subtitle_repository = SubtitleRepository(session_factory=session_factory)`
- `subtitle_service = SubtitleService(subtitle_repository)`
- `app.state.subtitle_repository = subtitle_repository`
- `app.state.subtitle_service = subtitle_service`
- `app.include_router(subtitles_router)`

## 5. 前端设计

### 5.1 Runtime 类型

修改 `apps/desktop/src/types/runtime.ts`，新增：

- `SubtitleStyleDto`
- `SubtitleSegmentDto`
- `SubtitleTrackDto`
- `SubtitleTrackGenerateInput`
- `SubtitleTrackUpdateInput`
- `SubtitleTrackGenerateResultDto`

状态枚举沿用字符串联合：

```ts
export type SubtitleTrackStatus = "blocked" | "ready" | "error" | "aligning";
```

### 5.2 Runtime client

修改 `apps/desktop/src/app/runtime-client.ts`：

- `fetchSubtitleTracks(projectId: string): Promise<SubtitleTrackDto[]>`
- `generateSubtitleTrack(projectId: string, input: SubtitleTrackGenerateInput): Promise<SubtitleTrackGenerateResultDto>`
- `fetchSubtitleTrack(trackId: string): Promise<SubtitleTrackDto>`
- `updateSubtitleTrack(trackId: string, input: SubtitleTrackUpdateInput): Promise<SubtitleTrackDto>`
- `deleteSubtitleTrack(trackId: string): Promise<void>`

所有函数必须通过 `requestRuntime<T>()`。

### 5.3 Store

重构 `apps/desktop/src/stores/subtitle-alignment.ts`。

状态：

```ts
type SubtitleAlignmentStatus =
  | "idle"
  | "loading"
  | "ready"
  | "aligning"
  | "blocked"
  | "saving"
  | "error";
```

字段：

- `projectId`
- `document`
- `tracks`
- `selectedTrackId`
- `generationResult`
- `activeSegmentIndex`
- `draftSegments`
- `style`
- `status`
- `error`

行为：

- `load(projectId)`：并行加载脚本文档和字幕轨。
- `generate()`：拼接当前脚本正文并调用 Runtime。
- `selectTrack(trackId)`：切换版本并同步草稿段。
- `selectSegment(index)`：高亮当前字幕段。
- `updateDraftSegment(index, patch)`：本地更新当前草稿段，不直接绕过 Runtime 保存。
- `updateSelectedTrack()`：保存当前段落和样式到 Runtime。
- `deleteTrack(trackId)`：删除版本后刷新列表。

错误：

- Runtime 错误转为 store `error`。
- 页面不使用 `alert()`。
- 中文错误直接渲染到状态区。

## 6. UI 体验设计

### 6.1 视觉主张

字幕对齐中心是“字幕校对台”：左侧是可编辑字幕段和脚本文本节奏，中间是预览叠字与当前段落反馈，右侧是时间码、样式和版本诊断。

它应通过以下方式体现设计感：

- 字幕段落像 cue sheet，可快速定位当前字幕段。
- 中央预览区以黑底画面和字幕叠字表达最终观看效果，但不假装有真实视频播放。
- 时间码校正区强调“当前段能否进入后续时间线”，而不是堆表单字段。
- 版本列表表达可追溯，而不是后台表格。
- 所有状态围绕“字幕轨能否进入 AI 剪辑工作台/时间线”解释。

### 6.2 外部参考转译

Unicorn Studio：

- 借鉴空间层次：字幕段、预览、诊断之间有清晰前后关系。
- 借鉴指针反馈：字幕段、版本项、时间码按钮有轻微响应。
- 不引入背景光球、无业务意义 3D 或沉浸式营销 hero。

React Bits：

- 借鉴 animated list：字幕段和版本进入有轻量淡入。
- 借鉴 hover feedback：字幕段 hover 显示可编辑状态。
- 借鉴 preloader：对齐中用细扫描线或字幕行 shimmer。
- 不复制 React 组件，不引入重型动效库。

### 6.3 布局

宽屏：

```text
+----------------------+------------------------------+----------------------+
| 字幕段落              | 预览叠字 / 当前状态           | 时间码 / 样式 / 版本  |
| 文本与段落列表        | 当前字幕、阻断说明、保存状态   | 校正、样式、版本诊断  |
+----------------------+------------------------------+----------------------+
```

紧凑窗口：

- 顶部显示标题、当前项目、生成字幕草稿按钮。
- 字幕段落与预览上下排列。
- 时间码、样式和版本移到下方折叠式区域或纵向区域。
- 不允许横向溢出，不使用 viewport 字体缩放。

### 6.4 组件边界

`SubtitleAlignmentCenterPage.vue`

- 只负责项目上下文、页面网格和组件装配。
- 不写 Runtime 调用。
- 不堆积全部样式。

`SubtitleSegmentList.vue`

- 展示字幕段落。
- 支持 loading、empty、error 中文文案。
- 点击段落更新 `activeSegmentIndex`。
- 文本编辑只更新 store 草稿，不直接 fetch。

`SubtitlePreviewStage.vue`

- 展示当前段落、字幕叠字、生成状态和 Provider 阻断状态。
- 无真实视频时显示中性预览画布，不显示播放按钮假装可播放。
- `blocked` 时显示“待配置 Provider”。

`SubtitleTimingPanel.vue`

- 展示当前字幕段的 `startMs/endMs`。
- 支持手动输入和 +/- 微调。
- `null` 时间码显示“待对齐”，不渲染成 00:00 假时间。

`SubtitleStylePanel.vue`

- 展示样式字段：字号、位置、文字颜色、背景。
- 本批只保存到 `style_json`，不创建本地模板资产。

`SubtitleVersionPanel.vue`

- 展示版本列表。
- 版本状态中文化：`blocked` -> “待配置”，`ready` -> “可用”，`error` -> “失败”。
- 删除动作有确认和错误反馈。

### 6.5 状态矩阵

| 状态 | 页面表现 | 操作 |
| --- | --- | --- |
| Loading | “正在读取脚本和字幕版本” | 禁用生成按钮 |
| Empty | “请先在脚本与选题中心创建内容” | 禁用生成按钮 |
| Ready | 字幕段落、预览、时间码、样式和版本可见 | 允许生成和保存 |
| Aligning | 生成按钮忙碌，预览区出现轻量扫描状态 | 禁止重复点击 |
| Blocked | “尚未配置可用字幕对齐 Provider，已保存字幕草稿。” | 允许编辑和保存草稿 |
| Error | 中文错误、重试入口 | 允许重新加载或重新保存 |
| Disabled | 无项目上下文或无脚本，说明原因 | 禁用相关动作 |

### 6.6 动效

允许：

- 字幕段列表进入淡入。
- 当前字幕段边框和背景轻微变化。
- 对齐中扫描线或 shimmer。
- 版本切换淡入。

禁止：

- 用装饰动画替代真实状态。
- 循环背景动画。
- 大面积渐变球。
- 引入 GSAP、Three.js、WebGL。

`prefers-reduced-motion: reduce`：

- 禁用扫描线、shimmer 和位移。
- 保留颜色、文案和状态反馈。

## 7. 接口文档同步

实现阶段必须先更新 `docs/RUNTIME-API-CALLS.md`，再改 route/client/store。

M08 章节必须包含：

- 数据对象表。
- 接口表。
- 请求和返回示例。
- 错误信封示例。
- 前端调用登记表。
- 测试入口。

验收时必须能回答：

- 后端接口在哪个 route 定义。
- 前端通过哪个 `runtime-client.ts` 函数调用。
- 哪个 store 和组件消费。
- 无 Provider、空脚本、保存失败、删除失败分别返回什么错误。
- 哪些测试覆盖。

## 8. 测试设计

### 8.1 后端 contract tests

新增 `tests/contracts/test_subtitle_runtime_contract.py`：

- `POST /api/subtitles/projects/{project_id}/tracks/generate` 无 Provider 返回 `blocked`。
- `GET /api/subtitles/projects/{project_id}/tracks` 返回真实字幕轨数组。
- `PATCH /api/subtitles/tracks/{track_id}` 保存用户校正后的段落和样式。
- `GET /api/subtitles/tracks/{track_id}` 返回段落和样式。
- `DELETE /api/subtitles/tracks/{track_id}` 删除后返回统一信封。
- 空 `sourceText` 返回中文失败信封。

### 8.2 后端 service tests

新增 `tests/runtime/test_subtitle_service.py`：

- 段落切分保留中文。
- 无 Provider 不抛异常。
- `segments_json` 和 `style_json` 是合法 JSON。
- 更新字幕段能持久化 `locked/startMs/endMs`。
- 删除不存在版本返回中文错误。

### 8.3 前端 client tests

新增 `apps/desktop/tests/runtime-client-subtitles.spec.ts`：

- 验证所有 `/api/subtitles` 路径、方法、请求体。
- 验证 Runtime 错误信封转换为中文 `RuntimeRequestError`。

### 8.4 前端 store tests

新增 `apps/desktop/tests/subtitle-alignment-store.spec.ts`：

- `load()` 同时加载脚本文档和字幕版本。
- `generate()` 成功但 blocked 时状态为 `blocked`。
- 空脚本不请求 Runtime 并进入中文错误态。
- `updateSelectedTrack()` 保存手动校正。
- `deleteTrack()` 删除后刷新列表。

### 8.5 页面测试

新增 `apps/desktop/tests/subtitle-alignment-page.spec.ts`：

- 有项目时展示字幕校对台和真实脚本文本。
- 点击生成后展示 Provider 阻断状态。
- loading、empty、ready、blocked、error 状态文案。
- 页面不出现乱码片段。
- 页面不使用 `alert()`。
- 宽屏和紧凑布局关键区域存在。

## 9. 验证命令

前端：

```powershell
npm --prefix apps/desktop run test -- runtime-client-subtitles.spec.ts subtitle-alignment-store.spec.ts subtitle-alignment-page.spec.ts
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
```

后端：

```powershell
venv\Scripts\python.exe -m pytest tests\contracts\test_subtitle_runtime_contract.py -q
venv\Scripts\python.exe -m pytest tests\runtime\test_subtitle_service.py -q
venv\Scripts\python.exe -m pytest tests\contracts -q
venv\Scripts\python.exe -m pytest tests\runtime -q
```

文档和提交前检查：

```powershell
venv\Scripts\python.exe -m pytest tests\contracts\test_text_encoding_contract.py -q
git diff --check
```

## 10. 验收标准

- `/api/subtitles` 契约、service、repository、route、factory 注入完整。
- 前端所有字幕请求只通过 Runtime client/store。
- 无 Provider 时生成真实 `SubtitleTrack` 草稿，状态为 `blocked`。
- 页面没有假精准时间码、假转写、假视频播放、假导出成功。
- 页面有 loading、empty、ready、aligning、blocked、error、disabled 状态。
- UI 文案中文可见，无乱码。
- `docs/RUNTIME-API-CALLS.md` 同步 M08 接口和调用登记。
- 新增测试覆盖 contract、service、client、store、page。
- 不混入当前无关 dirty 文件：`apps/desktop/src-tauri/Cargo.toml`、`scripts/stitch-connect.js`、`scripts/stitch-generate-dashboard.js`。

## 11. 后续扩展

后续独立 plan 再处理：

- 真实字幕对齐 Provider。
- ASR / Whisper 类转写。
- TaskBus 长任务进度、取消和失败原因。
- SRT/VTT 导入导出。
- 字幕模板资产化。
- 字幕轨回写 AI 剪辑工作台时间线。
- 与 M07 配音音轨的真实时间码联动。
