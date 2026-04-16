# M07 配音中心 Runtime 与 UI 闭环设计

> 计划来源：`docs/superpowers/plans/2026-04-16-m07-voice-studio-runtime-ui.md`
> 接口真源：`docs/RUNTIME-API-CALLS.md`
> 状态：Draft，等待用户审批
> 适用流程：`tkops-agent-council` + `tkops-ui-experience-council` + `tkops-runtime-contract-council`

## 1. 设计目标

M07 配音中心要从当前“乱码页面 + 前端模拟生成”升级为创作者可用的配音工作台。第一批只做真实 Runtime 闭环和 UI 交互底座，不接入真实外部 TTS Provider。

本轮目标：

- 修复配音中心所有中文乱码，文案、注释和错误提示按 UTF-8 无 BOM 保存。
- 建立 `/api/voice` 最小 Runtime 契约，包含音色列表、项目配音轨列表、生成配音轨、查询详情和删除版本。
- 生成动作必须落库为真实 `VoiceTrack`，无 TTS Provider 时返回 `blocked` 状态和中文说明，不伪造成音频生成成功。
- 前端移除 `setTimeout` 模拟生成，所有数据请求统一通过 `runtime-client.ts` 和 `voice-studio` store。
- 页面拆分为 Studio 工作台组件，覆盖脚本段落、音色选择、参数调节、预览状态和版本列表。
- 配音结果保留段落级映射，为后续字幕对齐和时间线音轨回流预留真实数据结构。

本轮非目标：

- 不接入真实 OpenAI、Azure、本地 TTS 或任何外部音频生成 Provider。
- 不生成假音频、假波形、假媒体时长、假任务成功。
- 不新增 `voice_profiles` 表；音色列表先由 `VoiceService` 的安全默认配置输出。
- 不实现音频合并、资产注册、时间线落轨、字幕自动对齐。
- 不新增 WebGL、Three.js、GSAP 或其他重型动效依赖。

## 2. Council 决议

Product Manager：通过。M07 是 16 页内核心媒体链路，目标应聚焦 TTS 配音、音色、参数、段落映射和版本管理，不扩展到团队协作、经营后台或素材商城。

Creative Director：有条件通过。页面要像“声音录制与配音控制台”，不是普通设置表单。视觉锚点应来自脚本段落、音色选择和波形/状态预览，而不是 KPI 或后台卡片。

Interaction Designer：通过。主路径是读取脚本 -> 选择音色 -> 调参数 -> 生成版本 -> 查看阻断/版本结果。无 Provider、空脚本、加载失败、删除失败都必须有就近中文反馈。

Motion Engineer：通过。本批仅使用 CSS/Vue transition。生成中可用轻量波形脉冲表达进度，但 `prefers-reduced-motion` 下必须降级。

Backend Runtime Lead：有条件通过。路由必须薄，业务在 service，错误进入统一信封，不向 UI 暴露 traceback。无 Provider 是可预期业务状态，不是 500。

Data & Contract Agent：通过。沿用现有 `voice_tracks` 表，使用 `segments_json` 保存段落映射，避免本批扩大迁移范围。

AI Pipeline Agent：有条件通过。必须明确 `pending_provider` 不是 Provider 成功；后续真实 TTS 接入必须另开 plan，补 AI 调用日志、耗时、失败原因和资产注册。

Frontend Lead：通过。必须拆组件，页面根组件只负责编排；Runtime client 是唯一 HTTP 入口。

QA & Verification Agent：通过。后端 contract/service、前端 client/store/page 测试都必须覆盖。

Independent Reviewer：评分 8.4 / 10。无 P0；P1 风险已转为设计约束：无 Provider 不能假成功、接口文档必须同步、页面不能继续乱码。

Project Leader：批准本 design spec 进入用户审批；审批通过后才能实现。

## 3. Runtime 契约

### 3.1 统一信封

所有 `/api/voice` 接口继续使用统一信封：

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
- route 不拼业务逻辑；route 只调用 `VoiceService`。
- 本批不创建长任务；真实 TTS 接入后再进入 TaskBus。

### 3.2 DTO

`VoiceProfileDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 前端选择用的稳定音色 ID |
| `provider` | `string` | 当前为 `pending_provider` 或后续真实 Provider |
| `voiceId` | `string` | Provider 侧音色 ID 或占位配置 ID |
| `displayName` | `string` | 中文展示名称 |
| `locale` | `string` | 语言区域，如 `zh-CN` |
| `tags` | `string[]` | 中文标签 |
| `enabled` | `boolean` | 是否可选 |

`VoiceTrackSegmentDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `segmentIndex` | `number` | 段落序号，从 0 开始 |
| `text` | `string` | 段落文本 |
| `startMs` | `number \| null` | 真实音频起始时间；无音频时为 `null` |
| `endMs` | `number \| null` | 真实音频结束时间；无音频时为 `null` |
| `audioAssetId` | `string \| null` | 后续资产中心音频资产 ID |

`VoiceTrackDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 配音轨 ID |
| `projectId` | `string` | 项目 ID |
| `timelineId` | `string \| null` | 后续时间线 ID |
| `source` | `string` | 本批为 `tts` |
| `provider` | `string \| null` | 当前为 `pending_provider` |
| `voiceName` | `string` | 中文音色名称 |
| `filePath` | `string \| null` | 真实音频路径；本批无 Provider 时为 `null` |
| `segments` | `VoiceTrackSegmentDto[]` | 段落映射 |
| `status` | `string` | `blocked` / `ready` / `error` 等 |
| `createdAt` | `string` | UTC ISO 时间 |

`VoiceTrackGenerateInput`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `profileId` | `string` | 选择的音色 ID |
| `sourceText` | `string` | 待配音脚本文本 |
| `speed` | `number` | 0.5 到 2.0 |
| `pitch` | `number` | -50 到 50 |
| `emotion` | `string` | `calm` / `happy` / `news` / `tender` |

`VoiceTrackGenerateResultDto`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `track` | `VoiceTrackDto` | 已创建的配音轨记录 |
| `task` | `TaskInfo \| null` | 本批无真实任务时为 `null` |
| `message` | `string` | 中文结果说明 |

### 3.3 接口

`GET /api/voice/profiles`

- 作用：获取可选择音色。
- 前端调用：`fetchVoiceProfiles()`
- 消费方：`voice-studio` store、`VoiceProfileRail.vue`
- 测试：`tests/contracts/test_voice_runtime_contract.py`、`apps/desktop/tests/runtime-client-voice.spec.ts`

`GET /api/voice/projects/{project_id}/tracks`

- 作用：获取项目配音版本列表。
- 前端调用：`fetchVoiceTracks(projectId)`
- 消费方：`voice-studio` store、`VoiceVersionPanel.vue`
- 返回排序：`createdAt DESC`

`POST /api/voice/projects/{project_id}/tracks/generate`

- 作用：根据脚本文本和参数创建配音轨记录。
- 前端调用：`generateVoiceTrack(projectId, input)`
- 无 Provider：返回 `track.status = "blocked"`、`task = null`、中文 message。
- 空文本：返回失败信封，错误为“脚本文本为空，请先在脚本与选题中心创建内容。”

`GET /api/voice/tracks/{track_id}`

- 作用：获取单条配音轨详情。
- 前端调用：`fetchVoiceTrack(trackId)`

`DELETE /api/voice/tracks/{track_id}`

- 作用：删除未被使用的配音版本。
- 前端调用：`deleteVoiceTrack(trackId)`
- 后续若存在时间线引用，必须返回 409 统一错误信封。

## 4. 后端设计

### 4.1 Schema

创建 `apps/py-runtime/src/schemas/voice.py`：

- `VoiceProfileDto`
- `VoiceTrackSegmentDto`
- `VoiceTrackDto`
- `VoiceTrackGenerateInput`
- `VoiceTrackGenerateResultDto`

命名采用前端友好的 camelCase 字段，Pydantic schema 负责输出 DTO，不把 ORM 字段名直接泄漏给页面。

### 4.2 Repository

创建 `apps/py-runtime/src/repositories/voice_repository.py`：

- `list_tracks(project_id: str) -> list[VoiceTrack]`
- `create_track(...) -> VoiceTrack`
- `get_track(track_id: str) -> VoiceTrack | None`
- `delete_track(track_id: str) -> None`

约束：

- `segments_json` 保存 JSON 数组，不保存 Python repr。
- `file_path` 无真实音频时必须为 `None`。
- 删除不存在的记录由 service 转为中文 404。

### 4.3 Service

创建 `apps/py-runtime/src/services/voice_service.py`：

- `list_profiles()`
- `list_tracks(project_id)`
- `generate_track(project_id, payload)`
- `get_track(track_id)`
- `delete_track(track_id)`

段落切分：

- 使用 `sourceText.splitlines()`。
- 去掉纯空行。
- 保留中文标点和原句内容。
- `segmentIndex` 从 0 开始。

无 Provider 策略：

- `provider = "pending_provider"`。
- `status = "blocked"`。
- `message = "尚未配置可用 TTS Provider，已保存配音版本草稿。"`
- 不创建 TaskBus 任务，不广播假进度。

时间：

- 使用 `apps/py-runtime/src/common/time.py` 的 `utc_now_iso()`。

### 4.4 Route 与依赖注入

创建 `apps/py-runtime/src/api/routes/voice.py`，前缀为 `/api/voice`。

更新：

- `apps/py-runtime/src/api/routes/__init__.py`
- `apps/py-runtime/src/app/factory.py`

依赖注入：

- `voice_repository = VoiceRepository(session_factory=session_factory)`
- `voice_service = VoiceService(voice_repository)`
- `app.state.voice_repository = voice_repository`
- `app.state.voice_service = voice_service`
- `app.include_router(voice_router)`

## 5. 前端设计

### 5.1 Runtime 类型

修改 `apps/desktop/src/types/runtime.ts`，新增：

- `VoiceProfileDto`
- `VoiceTrackSegmentDto`
- `VoiceTrackDto`
- `VoiceTrackGenerateInput`
- `VoiceTrackGenerateResultDto`

状态枚举不单独创建复杂 enum，沿用字符串联合即可：

```ts
export type VoiceTrackStatus = "blocked" | "ready" | "error" | "generating";
```

### 5.2 Runtime client

修改 `apps/desktop/src/app/runtime-client.ts`：

- `fetchVoiceProfiles(): Promise<VoiceProfileDto[]>`
- `fetchVoiceTracks(projectId: string): Promise<VoiceTrackDto[]>`
- `generateVoiceTrack(projectId: string, input: VoiceTrackGenerateInput): Promise<VoiceTrackGenerateResultDto>`
- `fetchVoiceTrack(trackId: string): Promise<VoiceTrackDto>`
- `deleteVoiceTrack(trackId: string): Promise<void>`

所有函数必须通过 `requestRuntime<T>()`。

### 5.3 Store

重构 `apps/desktop/src/stores/voice-studio.ts`。

状态：

```ts
type VoiceStudioStatus =
  | "idle"
  | "loading"
  | "ready"
  | "generating"
  | "blocked"
  | "error";
```

字段：

- `profiles`
- `tracks`
- `selectedProfileId`
- `selectedTrackId`
- `generationResult`
- `document`
- `paragraphs`
- `config`
- `error`
- `projectId`
- `status`

行为：

- `load(projectId)`：并行加载脚本文档、音色、配音版本。
- `selectProfile(profileId)`：选择音色。
- `generate()`：拼接当前脚本段落并调用 Runtime。
- `selectTrack(trackId)`：切换版本。
- `deleteTrack(trackId)`：删除版本后刷新列表。

错误：

- Runtime 错误转为 store `error`。
- 页面不使用 `alert()`。
- 中文错误直接渲染到状态区。

## 6. UI 体验设计

### 6.1 视觉主张

配音中心是“声音导演台”：左侧是脚本文本和段落节奏，中间是声音预览与生成状态，右侧是音色和版本管理。

它应通过以下方式体现设计感：

- 脚本段落像音轨 cue list，可以快速定位当前段。
- 中央预览区使用稳定波形和状态文字，表达“声音正在被组织”。
- 音色选择使用横向或网格化候选，不做普通下拉框。
- 版本列表表达可回溯，而不是后台表格。
- 所有状态都围绕“声音版本能否进入后续字幕/时间线”解释。

### 6.2 外部参考转译

Unicorn Studio：

- 借鉴空间层次：脚本、预览、版本之间有清楚前后关系。
- 借鉴指针反馈：音色卡、版本项、段落项有轻微响应。
- 不引入背景光球、无业务意义 3D 或沉浸式营销 hero。

React Bits：

- 借鉴 animated list：段落和版本进入有轻量淡入。
- 借鉴 hover feedback：音色卡 hover 显示试听/状态提示。
- 借鉴 preloader：生成中波形条轻微脉冲。
- 不复制 React 组件，不引入重型动效库。

### 6.3 布局

宽屏：

```text
+--------------------+------------------------------+--------------------+
| 脚本段落           | 声音预览 / 生成状态           | 音色 / 版本         |
| 段落列表           | 当前段落、波形、阻断说明       | 音色卡、参数、版本   |
+--------------------+------------------------------+--------------------+
```

紧凑窗口：

- 顶部显示标题、当前项目、生成按钮。
- 脚本段落与预览上下排列。
- 音色和版本区域移到下方或抽屉式区域。
- 不允许横向溢出，不用 viewport 字体缩放。

### 6.4 组件边界

`VoiceStudioPage.vue`

- 只负责项目上下文、页面网格和组件装配。
- 不写 Runtime 调用。
- 不堆积全部样式。

`VoiceScriptPanel.vue`

- 展示脚本段落。
- loading、empty、error 都有中文文案。
- 点击段落更新 `activeParagraphIndex`。

`VoiceProfileRail.vue`

- 展示音色候选。
- 选中态、不可用态、标签可见。
- 后续试听按钮仅展示可用状态，本批不播放假音频。

`VoiceParamsPanel.vue`

- 语速、音调、情绪。
- 值域与后端 schema 一致。

`VoicePreviewStage.vue`

- 展示当前段落、生成状态、Provider 阻断状态。
- 无真实音频时不显示播放按钮假装可播放。
- `blocked` 时显示“待配置 AI Provider”。

`VoiceVersionPanel.vue`

- 展示版本列表。
- 版本状态中文化：`blocked` -> “待配置”，`ready` -> “可用”，`error` -> “失败”。
- 删除动作有确认和错误反馈。

### 6.5 状态矩阵

| 状态 | 页面表现 | 操作 |
| --- | --- | --- |
| Loading | “正在读取脚本和配音版本” | 禁用生成按钮 |
| Empty | “请先在脚本与选题中心创建内容” | 禁用生成按钮 |
| Ready | 脚本段落、音色、参数和版本可见 | 允许生成 |
| Generating | 生成按钮进入忙碌态，波形轻微脉冲 | 禁止重复点击 |
| Blocked | “尚未配置可用 TTS Provider，已保存配音版本草稿。” | 可跳转或提示去 AI 与系统设置 |
| Error | 中文错误、重试入口 | 允许重新加载 |
| Disabled | 无项目上下文、空脚本、无音色说明原因 | 禁用相关动作 |

### 6.6 动效

允许：

- 段落列表进入淡入。
- 音色卡 hover 边框和阴影微增强。
- 生成中波形条轻微脉冲。
- 版本切换淡入。

禁止：

- 用装饰动画替代真实状态。
- 循环背景动画。
- 大面积渐变球。
- 引入 GSAP、Three.js、WebGL。

`prefers-reduced-motion: reduce`：

- 禁用波形脉冲和位移。
- 保留颜色、文案和进度状态。

## 7. 接口文档同步

实现阶段必须先更新 `docs/RUNTIME-API-CALLS.md`，再改 route/client/store。

M07 章节必须包含：

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
- 无 Provider、空脚本、删除失败分别返回什么错误。
- 哪些测试覆盖。

## 8. 测试设计

### 8.1 后端 contract tests

新增 `tests/contracts/test_voice_runtime_contract.py`：

- `GET /api/voice/profiles` 返回统一信封和至少一个中文音色。
- `GET /api/voice/projects/{project_id}/tracks` 返回数组。
- `POST /api/voice/projects/{project_id}/tracks/generate` 无 Provider 返回 `blocked`。
- 空 `sourceText` 返回失败信封。
- `GET /api/voice/tracks/{track_id}` 返回段落映射。
- `DELETE /api/voice/tracks/{track_id}` 删除后列表刷新。

### 8.2 后端 service tests

新增 `tests/runtime/test_voice_service.py`：

- 段落切分保留中文。
- 无 Provider 不抛异常。
- `segments_json` 是合法 JSON。
- 不写假 `file_path`。
- 删除不存在版本返回中文错误。

### 8.3 前端 client tests

新增 `apps/desktop/tests/runtime-client-voice.spec.ts`：

- 路径和方法完全匹配 `/api/voice` 契约。
- 生成请求体字段为 camelCase。
- 错误信封转换为 `RuntimeRequestError`。

### 8.4 前端 store tests

新增 `apps/desktop/tests/voice-studio-store.spec.ts`：

- `load()` 加载脚本、音色和版本。
- 空脚本进入 disabled/empty 语义。
- `generate()` 成功但 blocked 时状态为 `blocked`。
- Runtime 失败时写入中文错误。
- 删除版本后刷新列表。

### 8.5 页面测试

新增 `apps/desktop/tests/voice-studio-page.spec.ts`：

- loading、empty、ready、blocked、error 状态文案。
- 点击生成调用 store。
- 页面不出现乱码片段。
- 页面不使用 `alert()`。
- 宽屏和紧凑布局关键区域存在。

## 9. 实现顺序

1. 更新 `docs/RUNTIME-API-CALLS.md` 的 M07 接口章节。
2. 写 `tests/contracts/test_voice_runtime_contract.py` 红测。
3. 写 `tests/runtime/test_voice_service.py` 红测。
4. 实现 `schemas/voice.py`、`voice_repository.py`、`voice_service.py`、`routes/voice.py`。
5. 注册 `voice_router`、repository 和 service。
6. 写前端 Runtime client 和 store 红测。
7. 实现前端 DTO、client、store。
8. 写页面测试。
9. 重写页面根组件并拆分 `apps/desktop/src/modules/voice/` 组件。
10. 运行验证矩阵。
11. 触发 `tkops-acceptance-gate` 验收。

## 10. 多 Agent 分工

Backend Worker：

- 写入范围：`apps/py-runtime/src/schemas/voice.py`、`apps/py-runtime/src/repositories/voice_repository.py`、`apps/py-runtime/src/services/voice_service.py`、`apps/py-runtime/src/api/routes/voice.py`、`apps/py-runtime/src/api/routes/__init__.py`、`apps/py-runtime/src/app/factory.py`、`tests/contracts/test_voice_runtime_contract.py`、`tests/runtime/test_voice_service.py`。
- 禁止范围：前端页面、store、样式。

Frontend Worker：

- 写入范围：`apps/desktop/src/types/runtime.ts`、`apps/desktop/src/app/runtime-client.ts`、`apps/desktop/src/stores/voice-studio.ts`、`apps/desktop/src/pages/voice/VoiceStudioPage.vue`、`apps/desktop/src/modules/voice/`、`apps/desktop/tests/runtime-client-voice.spec.ts`、`apps/desktop/tests/voice-studio-store.spec.ts`、`apps/desktop/tests/voice-studio-page.spec.ts`。
- 禁止范围：后端 route/service/schema。

Docs/QA Owner：

- 写入范围：`docs/RUNTIME-API-CALLS.md`、本 spec、验证记录。
- 禁止范围：业务实现文件，除非 Project Leader 明确授权。

Project Leader：

- 负责接口字段裁决、共享文件串行编辑、最终集成和验收。
- 不允许两个 Worker 同时写同一文件。

## 11. 验证矩阵

后端：

```powershell
venv\Scripts\python.exe -m pytest tests\runtime\test_voice_service.py tests\contracts\test_voice_runtime_contract.py -q
venv\Scripts\python.exe -m pytest tests\runtime -q
venv\Scripts\python.exe -m pytest tests\contracts -q
```

前端：

```powershell
npm --prefix apps/desktop run test -- runtime-client-voice.spec.ts voice-studio-store.spec.ts voice-studio-page.spec.ts
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
```

仓库：

```powershell
git diff --check
```

UI 人工验收：

- 宽屏检查三栏 Studio 工作台。
- 紧凑窗口检查不横向溢出。
- Light / Dark 各检查一次。
- 检查无 Provider 阻断文案。
- 检查无乱码、无英文占位、无假播放按钮。

## 12. 阻断条件

- 页面仍存在 mojibake 乱码。
- `generate()` 仍使用前端 `setTimeout` 模拟。
- 无 Provider 时显示“生成完成”或出现假音频、假波形、假路径。
- 前端页面或组件直接 `fetch` Runtime。
- `docs/RUNTIME-API-CALLS.md` 未同步 M07。
- `/api/voice` 返回非统一信封或英文/traceback 错误。
- 页面根组件继续承担大部分业务逻辑和样式，未拆分组件。
- 测试失败且无明确非阻断说明。

## 13. 通过标准

spec 可进入实现的条件：

- 用户确认本 design spec。
- M07 接口边界、UI 状态、无 Provider 策略和测试矩阵均被接受。
- `docs/RUNTIME-API-CALLS.md` 仍作为唯一接口文档。
- 多 Agent 分工文件范围不重叠。
- 没有未解决 P0/P1 风险。
