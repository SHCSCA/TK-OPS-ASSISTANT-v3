# TK-OPS-ASSISTANT-v3 功能体验重构与参考项目吸收实施方案

> 文档版本：V1.0  
> 生成日期：2026-05-16  
> 适用项目：`SHCSCA/TK-OPS-ASSISTANT-v3`  
> 目标读者：产品、前端、Runtime 后端、媒体处理、测试、后续 AI 代理开发者  
> 文档目标：把前面讨论的产品判断、体验问题、三个参考项目的可借鉴点，整理成一份开发可直接开工的实施文档。

---

## 0. 结论先行

当前 TK-OPS 的底层方向是正确的：它已经具备桌面壳、项目上下文、Runtime、任务总线、AI Provider、配音、字幕、资产、时间线、发布、渲染等完整工程骨架。问题不在于“没有功能”，而在于：

1. **功能太像模块集合，不够像用户任务流。**
2. **页面很多，但用户打开后第一步不够明确。**
3. **M05 AI 剪辑工作台已经有结构，但还没有形成强结果感。**
4. **脚本、分镜、配音、字幕、视频拆解、时间线之间还缺一个统一的中间数据协议。**
5. **缺少从“资料/参考视频”到“可预览/可导出视频”的一键主链。**

本方案建议把 TK-OPS 从：

```text
AI 视频创作中枢 / 16 个功能页面
```

重构为：

```text
围绕项目时间线的 AI 短视频生产工作台
```

用户不应该先理解 16 个模块，而应该先看到 4 个明确入口：

```text
1. 从产品资料生成视频
2. 导入参考视频重制
3. 批量混剪素材
4. 继续编辑项目
```

技术上新增三条主干能力：

```text
CreativeSegment        统一片段协议
CreativePipeline       创作流水线任务
MediaNormalize         素材归一化/代理文件/预检
```

它们分别解决：

| 问题 | 新能力 | 说明 |
|---|---|---|
| 脚本、分镜、配音、字幕、时间线互相割裂 | `CreativeSegment` | 把每个视频片段作为统一创作单元 |
| 用户需要跨多个页面操作 | `CreativePipeline` | 用一个任务流串起生成、拆解、汇入、预览、导出 |
| 素材格式混乱、预览/渲染不稳定 | `MediaNormalize` | 统一尺寸、比例、FPS、编码、代理文件 |
| 生成后没有结果墙 | `PipelineResultWall` | 所有脚本、音频、字幕、视频、导出结果集中展示 |
| M05 时间线“有结构但不够结果型” | `Segment -> Timeline Assembly` | 让 M05 真正承接主链输出 |

---

## 1. 当前项目诊断

### 1.1 当前强项

TK-OPS 当前不应被视为普通 Demo。它已经具备较强工程基础：

- 16 个正式页面已经有 UI 与 Runtime 接线。
- Runtime 路由面完整，当前已有大量业务 Router。
- M05 AI 剪辑工作台已接入脚本、分镜、配音、字幕汇入能力。
- 配音中心已接入真实 TTS 链路。
- TaskBus 和 WebSocket 已经作为长任务反馈基础存在。
- `RUNTIME-API-CALLS.md` 和契约测试已经形成接口治理体系。
- 桌面壳结构稳定，具备 Title Bar、Sidebar、Content Host、Detail Panel、Status Bar。

这些能力应保留，不要推倒重来。

### 1.2 当前核心问题

#### 问题 A：用户入口像“模块列表”，不是“任务入口”

当前用户很容易面对：

```text
创作总览
脚本与选题中心
分镜规划中心
AI 剪辑工作台
视频拆解中心
配音中心
字幕对齐中心
资产中心
账号管理
设备与工作区管理
自动化执行中心
发布中心
渲染与导出中心
复盘中心
AI 与系统设置
```

对开发者清晰，但对用户不够直接。用户真实想法是：

```text
我要做一条视频
我要拆一个参考视频
我要把配音和字幕生成出来
我要批量生成几个版本
我要导出成片
```

因此前台体验要从“页面树”转为“任务树”。

#### 问题 B：功能接线已经很多，但主链结果感不足

现在很多能力是“已接线”：页面能调接口、接口有返回、状态能显示。但用户更关心：

- 是否能真实导入视频？
- 是否能生成可编辑脚本？
- 是否能生成真实配音？
- 是否能自动生成字幕？
- 是否能汇入时间线？
- 是否能预览？
- 是否能导出一个 MP4？

产品体验必须用“最终结果”来组织，而不是用“模块完成度”组织。

#### 问题 C：缺少统一片段模型

当前脚本、分镜、配音、字幕、视频拆解、资产、时间线都各有模型。问题是：

- 脚本段落如何对应分镜镜头？
- 分镜镜头如何对应配音段？
- 配音段如何对应字幕段？
- 字幕段如何对应时间线 clip？
- 视频拆解后的原视频时间戳如何回流到新时间线？

现在需要一个统一中间层：`CreativeSegment`。

#### 问题 D：M05 工作台必须从“显示时间线”升级为“主链终点”

M05 的地位应该是：

```text
脚本、分镜、视频拆解、配音、字幕、资产全部汇入这里，最终在这里预览和导出。
```

它不是一个普通页面，而是主链中枢。

---

## 2. 参考项目分析与可借鉴点

本节只提炼可以吸收的产品/代码思路，不建议直接复制源代码。尤其要注意开源项目许可证与商业授权限制。

### 2.1 MoneyPrinterTurbo

#### 它解决什么问题

MoneyPrinterTurbo 的核心思路非常直接：

```text
输入主题/关键词
→ 自动生成脚本
→ 生成素材搜索词
→ 生成配音
→ 生成字幕
→ 获取素材
→ 合成视频
```

它的最大价值不是界面，而是“结果型流水线”。用户很快能理解它：输入一个主题，输出一个视频。

#### 值得吸收

##### A. 标准化生成流水线

建议 TK-OPS 新增类似流水线：

```text
script
storyboard
voice
subtitle
timeline
preview
render
```

每个阶段都可以单独运行，也可以连续运行。

##### B. `stopAt` 分阶段停止能力

参考 MoneyPrinterTurbo 的 `stop_at` 设计，TK-OPS 新增：

```ts
type CreativePipelineStopAt =
  | 'script'
  | 'storyboard'
  | 'voice'
  | 'subtitle'
  | 'timeline'
  | 'preview'
  | 'render'
```

用户可以选择：

- 只生成脚本；
- 只生成配音；
- 生成到字幕后手动改；
- 生成到时间线后手动剪；
- 一路导出成片。

##### C. 聚合参数对象

MoneyPrinterTurbo 的 `VideoParams` 把主题、脚本、画幅、视频数量、素材源、音色、BGM、字幕样式等合并到一个参数对象。

TK-OPS 应新增：

```ts
type CreativeJobParams = {
  projectId: string
  inputMode: 'product_info' | 'reference_video' | 'manual_script' | 'asset_mix'
  stopAt: CreativePipelineStopAt
  targetLanguage: string
  aspectRatio: '9:16' | '16:9' | '1:1'
  durationTargetSec?: number
  variantCount: number
  voiceProfileId?: string
  subtitleStyleId?: string
  renderProfileId?: string
  sourceVideoId?: string
  productInfo?: ProductInfoInput
  customScript?: string
}
```

##### D. 素材合成实用细节

MoneyPrinterTurbo 的视频处理里有很多实战细节值得吸收：

- ffmpeg 路径自动解析；
- 图片转视频；
- 低分辨率素材过滤；
- 素材按音频时长循环；
- 字幕换行、描边、位置控制；
- BGM 混合；
- 临时文件清理；
- 多视频批量生成。

这些能力建议不要散落在业务服务里，应收敛到 `MediaNormalizeService` 与 `RenderService`。

#### 不建议照搬

- 不要把 TK-OPS 改成“输入主题直接出视频”的单一工具。
- 不要牺牲 M05 时间线和可编辑性。
- 不要照搬 Streamlit UI。
- 不要直接复制代码，尤其涉及版权和商业授权。

---

### 2.2 NarratoAI

#### 它解决什么问题

NarratoAI 核心是“视频解说 + 自动剪辑”。它最重要的设计是：用一个脚本 JSON 驱动后续裁剪、配音、字幕、合成。

典型结构：

```json
{
  "_id": 1,
  "timestamp": "00:00:00,600-00:00:07,559",
  "picture": "画面描述",
  "narration": "解说词",
  "OST": 0
}
```

#### 值得吸收

##### A. 结构化脚本作为剪辑中间态

这是最重要的借鉴点。TK-OPS 应将脚本、分镜、配音、字幕、视频拆解统一到 `CreativeSegment`。

##### B. OST 音频模式

NarratoAI 的 OST 逻辑：

| OST | 含义 | 处理方式 |
|---|---|---|
| 0 | 纯解说 | 按 TTS 时长裁剪，移除原声 |
| 1 | 原声片段 | 按原时间戳裁剪，保留原声 |
| 2 | 解说 + 原声 | 按 TTS 时长裁剪，保留原声 |

TK-OPS 不建议叫 OST，建议转为：

```ts
type SegmentAudioMode = 'voiceover' | 'original' | 'mixed' | 'silent'
```

用户界面显示：

```text
仅旁白
保留原声
旁白 + 原声
静音
```

##### C. 统一裁剪策略

NarratoAI 不是简单裁剪，而是根据音频模式差异化裁剪：

- 仅旁白：按 TTS 时长裁剪，去原声；
- 保留原声：按原视频时间戳裁剪；
- 混合：按 TTS 时长裁剪，并保留原声。

这正适合 TK-OPS 的“参考视频重制”。

##### D. 剪映草稿导出

NarratoAI 支持导出剪映草稿。TK-OPS 后续可以做：

```text
导出 MP4
导出 SRT
导出配音音频
导出剪映草稿
导出项目包
```

这对国内用户非常实用。

#### 不建议照搬

- 不要照搬它的 Streamlit 表单式界面。
- 不要把脚本 JSON 裸露给普通用户作为主交互。
- 可以给高级用户 JSON 编辑入口，但默认应使用表格/卡片式片段编辑。

---

### 2.3 MoneyPrinterPlus

#### 它解决什么问题

MoneyPrinterPlus 更偏“批量混剪 + 一键生成 + 自动发布”。它的用户入口比 TK-OPS 更直观：

```text
自动短视频生成器
视频批量混剪工具
批量视频自动发布工具
```

#### 值得吸收

##### A. 任务化入口

TK-OPS 应从 16 个模块入口上升到 4-6 个任务入口。

##### B. 批量混剪

MoneyPrinterPlus 支持多场景资源目录 + 多段文本，然后批量生成视频。

TK-OPS 应新增：

```text
批量变体生成器
```

能力包括：

- 多开头；
- 多卖点顺序；
- 多音色；
- 多字幕样式；
- 多素材组合；
- 一次生成多个版本。

##### C. 素材归一化

MoneyPrinterPlus 的视频处理会做：

- 图片转视频；
- 统一分辨率；
- 统一 FPS；
- 裁切比例；
- 控制片段最短/最长时长；
- 拼接；
- 加音频；
- 加背景音乐。

TK-OPS 应把这部分能力产品化为 `MediaNormalizeService`。

##### D. 发布配置结构

MoneyPrinterPlus 的发布页按平台配置标题、标签、合集、原创声明等。TK-OPS 可以借鉴发布配置结构，但不要急着做强自动化发布。

#### 不建议照搬

- 不建议照搬“自动发布到平台”的强自动化实现。
- 不建议使用“赚钱、一键万条”等产品叙事。
- 不建议直接复制带商业限制声明的代码。

---

## 3. 重构目标

### 3.1 产品目标

把 TK-OPS 从：

```text
功能中心型系统
```

变成：

```text
任务流驱动的 AI 短视频生产工作台
```

### 3.2 用户主路径

重构后的主路径：

```text
进入首页
→ 选择任务入口
→ 创建/选择项目
→ 输入资料或导入参考视频
→ 生成结构化片段 CreativeSegment
→ 生成配音与字幕
→ 汇入 M05 时间线
→ 本地预览
→ 手动微调
→ 导出结果
```

### 3.3 首页入口调整

当前首页不应只展示最近项目和状态，应增加任务卡片：

```text
你想做什么？

[从产品资料生成视频]
输入商品名称、卖点、目标语言，自动生成脚本、配音、字幕和时间线。

[导入参考视频重制]
上传参考视频，拆解结构、转写字幕、生成改写脚本，再汇入时间线。

[批量混剪素材]
选择素材目录、卖点和音色，一次生成多个版本。

[继续编辑项目]
回到最近项目的剪辑工作台。
```

### 3.4 导航结构调整建议

开发层 16 页可以保留，但用户感知导航建议压缩为：

```text
项目
生成
拆解
剪辑
批量
导出
设置
```

映射关系：

| 用户导航 | 底层页面/模块 |
|---|---|
| 项目 | dashboard / project / assets summary |
| 生成 | scripts / storyboards / voice / subtitles |
| 拆解 | video-deconstruction / transcription / segment |
| 剪辑 | workspace / assets / inspector |
| 批量 | variant batch / mix tasks |
| 导出 | renders / publishing / result wall |
| 设置 | ai-system / providers / paths / diagnostics |

注意：这不要求立即删除原路由，只要求首页和 Sidebar 展示上收口。

---

## 4. 核心新增模型

### 4.1 CreativeSegment

#### 4.1.1 设计目的

`CreativeSegment` 是所有创作结果之间的统一片段协议。它连接：

```text
视频拆解 → 脚本 → 分镜 → 配音 → 字幕 → 时间线 → 渲染
```

#### 4.1.2 TypeScript DTO

```ts
type SegmentAudioMode = 'voiceover' | 'original' | 'mixed' | 'silent'
type CreativeSegmentStatus = 'draft' | 'ready' | 'needs_review' | 'error'

type CreativeSegmentDto = {
  id: string
  projectId: string
  index: number

  title?: string | null
  visualDescription: string
  narrationText: string
  subtitleText: string

  sourceType: 'manual' | 'script' | 'storyboard' | 'video_deconstruction' | 'asset_mix' | 'pipeline'
  sourceVideoId?: string | null
  sourceAssetId?: string | null
  sourceScriptSegmentId?: string | null
  sourceStoryboardShotId?: string | null

  sourceStartMs?: number | null
  sourceEndMs?: number | null
  durationMs?: number | null

  audioMode: SegmentAudioMode
  voiceTrackId?: string | null
  subtitleTrackId?: string | null

  assetRefs: string[]
  tags: string[]
  status: CreativeSegmentStatus

  createdAt: string
  updatedAt: string
}
```

#### 4.1.3 Python Schema

```python
class CreativeSegmentDto(BaseModel):
    id: str
    projectId: str
    index: int
    title: str | None = None
    visualDescription: str = ''
    narrationText: str = ''
    subtitleText: str = ''
    sourceType: Literal['manual', 'script', 'storyboard', 'video_deconstruction', 'asset_mix', 'pipeline']
    sourceVideoId: str | None = None
    sourceAssetId: str | None = None
    sourceScriptSegmentId: str | None = None
    sourceStoryboardShotId: str | None = None
    sourceStartMs: int | None = None
    sourceEndMs: int | None = None
    durationMs: int | None = None
    audioMode: Literal['voiceover', 'original', 'mixed', 'silent'] = 'voiceover'
    voiceTrackId: str | None = None
    subtitleTrackId: str | None = None
    assetRefs: list[str] = []
    tags: list[str] = []
    status: Literal['draft', 'ready', 'needs_review', 'error'] = 'draft'
    createdAt: datetime
    updatedAt: datetime
```

#### 4.1.4 数据库表建议

表名：`creative_segments`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | TEXT PK | segment id |
| `project_id` | TEXT index | 项目 ID |
| `order_index` | INTEGER | 排序 |
| `title` | TEXT nullable | 片段标题 |
| `visual_description` | TEXT | 画面说明 |
| `narration_text` | TEXT | 配音文本 |
| `subtitle_text` | TEXT | 字幕文本 |
| `source_type` | TEXT | 来源类型 |
| `source_video_id` | TEXT nullable | 来源视频 |
| `source_asset_id` | TEXT nullable | 来源资产 |
| `source_script_segment_id` | TEXT nullable | 来源脚本段 |
| `source_storyboard_shot_id` | TEXT nullable | 来源分镜 |
| `source_start_ms` | INTEGER nullable | 来源起点 |
| `source_end_ms` | INTEGER nullable | 来源终点 |
| `duration_ms` | INTEGER nullable | 目标时长 |
| `audio_mode` | TEXT | voiceover/original/mixed/silent |
| `voice_track_id` | TEXT nullable | 配音轨 |
| `subtitle_track_id` | TEXT nullable | 字幕轨 |
| `asset_refs_json` | TEXT | JSON 数组 |
| `tags_json` | TEXT | JSON 数组 |
| `status` | TEXT | 状态 |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

#### 4.1.5 文件落点

```text
apps/py-runtime/src/domain/models/creative_segment.py
apps/py-runtime/src/repositories/creative_segment_repository.py
apps/py-runtime/src/schemas/creative_segments.py
apps/py-runtime/src/services/creative_segment_service.py
apps/py-runtime/src/api/routes/creative_segments.py
```

前端：

```text
apps/desktop/src/types/creative-segment.ts
apps/desktop/src/stores/creative-segments.ts
apps/desktop/src/modules/creative-segments/CreativeSegmentTable.vue
apps/desktop/src/modules/creative-segments/CreativeSegmentCard.vue
apps/desktop/src/modules/creative-segments/CreativeSegmentEditorDrawer.vue
```

---

### 4.2 CreativePipelineJob

#### 4.2.1 设计目的

`CreativePipelineJob` 是贯穿脚本、配音、字幕、时间线、渲染的主任务对象。它不是替代现有 TaskBus，而是作为更上层的业务任务。

现有 TaskBus 负责底层任务状态；CreativePipelineJob 负责业务阶段。

#### 4.2.2 状态定义

```ts
type CreativePipelineStage =
  | 'prepare'
  | 'script'
  | 'storyboard'
  | 'voice'
  | 'subtitle'
  | 'segment'
  | 'timeline'
  | 'preview'
  | 'render'
  | 'complete'

type CreativePipelineStatus =
  | 'queued'
  | 'running'
  | 'paused'
  | 'succeeded'
  | 'failed'
  | 'cancelled'
```

#### 4.2.3 Job DTO

```ts
type CreativePipelineJobDto = {
  id: string
  projectId: string
  status: CreativePipelineStatus
  currentStage: CreativePipelineStage
  progress: number
  message: string
  params: CreativeJobParams
  steps: CreativePipelineStepDto[]
  result?: CreativePipelineResultDto | null
  error?: RuntimeRequestErrorShape | null
  createdAt: string
  updatedAt: string
}
```

#### 4.2.4 Step DTO

```ts
type CreativePipelineStepDto = {
  id: string
  stage: CreativePipelineStage
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped'
  progress: number
  message: string
  startedAt?: string | null
  finishedAt?: string | null
  outputRefs: PipelineOutputRef[]
}
```

#### 4.2.5 文件落点

```text
apps/py-runtime/src/domain/models/creative_pipeline.py
apps/py-runtime/src/repositories/creative_pipeline_repository.py
apps/py-runtime/src/schemas/creative_pipeline.py
apps/py-runtime/src/services/creative_pipeline_service.py
apps/py-runtime/src/api/routes/creative_pipeline.py
```

前端：

```text
apps/desktop/src/stores/creative-pipeline.ts
apps/desktop/src/modules/pipeline/CreativePipelineLauncher.vue
apps/desktop/src/modules/pipeline/CreativePipelineProgress.vue
apps/desktop/src/modules/pipeline/CreativePipelineStepList.vue
apps/desktop/src/modules/pipeline/PipelineResultWall.vue
```

---

### 4.3 MediaProfile / NormalizedAsset

#### 4.3.1 设计目的

媒体素材进入时间线前必须经过检查：分辨率、比例、FPS、编码、时长、是否可读、是否适合 9:16、是否需要转码。

#### 4.3.2 DTO

```ts
type MediaProfileDto = {
  assetId: string
  filePath: string
  mediaType: 'video' | 'image' | 'audio' | 'subtitle' | 'unknown'
  readable: boolean
  width?: number | null
  height?: number | null
  fps?: number | null
  durationMs?: number | null
  codec?: string | null
  audioCodec?: string | null
  aspectRatio?: string | null
  needsNormalize: boolean
  warnings: string[]
  checkedAt: string
}
```

```ts
type MediaNormalizeResultDto = {
  assetId: string
  status: 'ready' | 'warning' | 'failed'
  sourcePath: string
  normalizedPath?: string | null
  proxyPath?: string | null
  thumbnailPath?: string | null
  profile: MediaProfileDto
  message: string
}
```

#### 4.3.3 文件落点

```text
apps/py-runtime/src/media/probe.py
apps/py-runtime/src/media/normalize.py
apps/py-runtime/src/services/media_normalize_service.py
apps/py-runtime/src/schemas/media_profile.py
```

---

## 5. 新增 Runtime API 设计

### 5.1 Creative Segments API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/creative-segments/projects/{project_id}` | 查询项目片段 |
| POST | `/api/creative-segments/projects/{project_id}` | 创建片段 |
| PUT | `/api/creative-segments/{segment_id}` | 更新片段 |
| DELETE | `/api/creative-segments/{segment_id}` | 删除片段 |
| POST | `/api/creative-segments/projects/{project_id}/reorder` | 重排片段 |
| POST | `/api/creative-segments/projects/{project_id}/validate` | 校验片段完整性 |

#### GET Response

```json
{
  "ok": true,
  "data": {
    "projectId": "project-1",
    "segments": [],
    "summary": {
      "total": 0,
      "ready": 0,
      "needsReview": 0,
      "estimatedDurationMs": 0
    }
  }
}
```

### 5.2 Creative Pipeline API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/creative-pipeline/projects/{project_id}/run` | 启动流水线 |
| GET | `/api/creative-pipeline/jobs/{job_id}` | 查询任务详情 |
| GET | `/api/creative-pipeline/projects/{project_id}/jobs` | 查询项目任务历史 |
| POST | `/api/creative-pipeline/jobs/{job_id}/cancel` | 取消任务 |
| POST | `/api/creative-pipeline/jobs/{job_id}/retry` | 重试失败阶段 |
| POST | `/api/creative-pipeline/jobs/{job_id}/apply-to-timeline` | 将结果汇入时间线 |

#### POST `/run` Request

```json
{
  "inputMode": "product_info",
  "stopAt": "timeline",
  "targetLanguage": "en-US",
  "aspectRatio": "9:16",
  "durationTargetSec": 35,
  "variantCount": 1,
  "voiceProfileId": "voice-1",
  "subtitleStyleId": "style-1",
  "renderProfileId": "render-1080p",
  "productInfo": {
    "title": "Portable Door Lock",
    "sellingPoints": ["No drilling", "Rental friendly", "Bedroom security"],
    "audience": "US renters",
    "tone": "direct_response"
  }
}
```

#### Response

```json
{
  "ok": true,
  "data": {
    "jobId": "pipeline-job-1",
    "taskId": "task-1",
    "status": "queued",
    "currentStage": "prepare",
    "message": "创作流水线已进入队列。"
  }
}
```

### 5.3 Media Normalize API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/assets/{asset_id}/media-profile` | 获取媒体信息 |
| POST | `/api/assets/{asset_id}/normalize` | 归一化单个素材 |
| POST | `/api/assets/batch-normalize` | 批量归一化 |
| GET | `/api/assets/{asset_id}/proxy` | 获取代理文件 URL |
| GET | `/api/assets/{asset_id}/thumbnail` | 获取缩略图 |

---

## 6. CreativePipelineService 设计

### 6.1 服务职责

`CreativePipelineService` 不直接写复杂底层逻辑。它负责调用现有服务：

| 阶段 | 调用服务 |
|---|---|
| prepare | dashboard / settings / ai capability / asset |
| script | ScriptService / AITextGenerationService |
| storyboard | StoryboardService |
| voice | VoiceService |
| subtitle | SubtitleService |
| segment | CreativeSegmentService |
| timeline | WorkspaceAssemblyService |
| preview | WorkspaceService / RenderService preview |
| render | RenderService |

### 6.2 伪代码

```python
class CreativePipelineService:
    def run_project_pipeline(self, project_id: str, payload: CreativePipelineRunInput) -> CreativePipelineJobDto:
        job = self.repository.create_job(project_id, payload)
        task = self.task_manager.submit(
            task_type='creative-pipeline',
            project_id=project_id,
            coro_factory=lambda progress: self._run_job(job.id, progress),
        )
        return self.to_job_started_dto(job, task)

    async def _run_job(self, job_id: str, progress_callback):
        job = self.repository.get_job(job_id)
        params = job.params

        await self._step(job, 'prepare', 5, self._prepare)
        if params.stopAt == 'prepare': return self._complete(job)

        await self._step(job, 'script', 15, self._generate_script)
        if params.stopAt == 'script': return self._complete(job)

        await self._step(job, 'storyboard', 30, self._generate_storyboard)
        if params.stopAt == 'storyboard': return self._complete(job)

        await self._step(job, 'segment', 45, self._build_segments)
        await self._step(job, 'voice', 60, self._generate_voice)
        if params.stopAt == 'voice': return self._complete(job)

        await self._step(job, 'subtitle', 70, self._generate_subtitle)
        if params.stopAt == 'subtitle': return self._complete(job)

        await self._step(job, 'timeline', 82, self._assemble_timeline)
        if params.stopAt == 'timeline': return self._complete(job)

        await self._step(job, 'preview', 92, self._generate_preview)
        if params.stopAt == 'preview': return self._complete(job)

        await self._step(job, 'render', 100, self._render)
        return self._complete(job)
```

### 6.3 失败处理

每个 step 必须记录：

```text
stage
status
error_code
error_message
request_id
output_refs
recover_action
```

失败时不应直接丢弃已有结果。例如配音失败，脚本和分镜仍要保留。

---

## 7. CreativeSegment 生成策略

### 7.1 从产品资料生成

输入：

```text
商品名称
目标用户
卖点
使用场景
语言
视频时长
```

输出：

```text
CreativeSegment[]
```

建议 LLM 输出 JSON：

```json
[
  {
    "index": 1,
    "title": "痛点开场",
    "visualDescription": "租房卧室门口，用户回头确认门锁",
    "narrationText": "Living in a rental and worried about privacy?",
    "subtitleText": "Worried about privacy in your rental?",
    "audioMode": "voiceover",
    "durationMs": 4500,
    "tags": ["hook", "renter", "bedroom"]
  }
]
```

### 7.2 从参考视频拆解生成

输入：

```text
sourceVideoId
transcript
shots
timestamps
```

输出：

```text
CreativeSegment[] with sourceStartMs/sourceEndMs
```

片段音频模式建议：

| 场景 | audioMode |
|---|---|
| 参考视频只是借结构 | `voiceover` |
| 保留原片精彩原声 | `original` |
| 原声和旁白都需要 | `mixed` |
| 只要画面不要声音 | `silent` |

### 7.3 从手动脚本生成

输入手动脚本后，系统应拆成段落：

```text
每个段落 → CreativeSegment
```

用户可以在表格中编辑：

```text
画面说明 / 配音文本 / 字幕文本 / 音频模式 / 预计时长
```

---

## 8. M05 时间线汇入改造

### 8.1 当前问题

M05 已经具备汇入创作链路和受管轨道，但下一步应让汇入依据从“多个模块的各自输出”升级为：

```text
CreativeSegment[]
```

### 8.2 汇入逻辑

输入：

```text
project_id
segments[]
mode = merge_managed | replace_managed | append_manual
```

输出轨道：

```text
Managed Video Track
Managed Voice Track
Managed Subtitle Track
Original Audio Track
Manual Track
```

### 8.3 Clip 映射规则

| segment 字段 | timeline clip 字段 |
|---|---|
| `id` | `sourceId` |
| `visualDescription` | video clip label/prompt |
| `narrationText` | voice clip label/prompt |
| `subtitleText` | subtitle clip text |
| `durationMs` | clip duration |
| `audioMode` | audio track behavior |
| `sourceStartMs/sourceEndMs` | in/out points |

### 8.4 右侧属性面板要显示来源链路

选择一个 clip 后，右侧显示：

```text
来源片段：S03
来源类型：参考视频拆解
配音模式：旁白 + 原声
字幕状态：已生成
配音状态：已生成
素材状态：已归一化
```

---

## 9. MediaNormalizeService 设计

### 9.1 目标

所有素材进入时间线前必须完成媒体预检或归一化。

### 9.2 处理能力

| 能力 | 说明 |
|---|---|
| `probe` | ffprobe 检查媒体信息 |
| `normalize_video` | 统一比例、编码、FPS |
| `image_to_video` | 图片转指定时长视频 |
| `generate_proxy` | 生成低码率预览代理 |
| `generate_thumbnail` | 首帧缩略图 |
| `validate_for_timeline` | 判断是否可进入时间线 |

### 9.3 归一化策略

默认目标：

```text
format: mp4
codec: h264
pix_fmt: yuv420p
fps: 30
aspect: 9:16
resolution: 1080x1920
```

### 9.4 FFmpeg 命令原则

不要把命令散落在业务层，应封装：

```python
class MediaNormalizeService:
    def build_normalize_command(self, input_path, output_path, profile):
        ...
```

基础滤镜：

```text
scale/crop 到目标比例
统一 fps
去除异常音轨或保留音轨
movflags +faststart
```

### 9.5 硬件加速

先检测：

```text
nvenc
qsv
amf
videotoolbox
software
```

失败时 fallback：

```text
硬件编码 → 软件编码 → 基础编码
```

这部分可借鉴 NarratoAI 的错误分类和 fallback 思路，但不能直接复制代码。

---

## 10. 批量变体生成器

### 10.1 目标

用户不是只需要生成 1 条视频，而是需要生成多个可测试版本。

### 10.2 VariantBatchJob

```ts
type VariantBatchJobInput = {
  projectId: string
  baseSegmentIds: string[]
  variantCount: number
  hookStrategies: ('pain' | 'benefit' | 'question' | 'comparison' | 'testimonial')[]
  voiceProfileIds: string[]
  subtitleStyleIds: string[]
  assetShuffleMode: 'none' | 'safe_shuffle' | 'aggressive_shuffle'
  sceneOrderMode: 'fixed' | 'shuffle_middle' | 'full_shuffle'
  renderProfileId?: string
}
```

### 10.3 结果

```text
Variant A
Variant B
Variant C
```

每个版本保留：

```text
脚本差异
分镜差异
音色
字幕样式
素材组合
导出文件
```

### 10.4 UI

新增模块：

```text
apps/desktop/src/modules/batch/BatchVariantWizard.vue
apps/desktop/src/modules/batch/VariantResultGrid.vue
apps/desktop/src/stores/batch-variants.ts
```

---

## 11. 结果墙 PipelineResultWall

### 11.1 为什么需要

三个参考项目都有一个共同点：生成后马上显示结果视频。

TK-OPS 当前更偏工作台，缺少集中结果感。建议每个项目都增加结果墙。

### 11.2 展示内容

```text
脚本版本
分镜版本
配音音频
字幕文件
时间线草稿
预览文件
导出 MP4
剪映草稿
发布记录
```

### 11.3 操作

每个 artifact 支持：

```text
预览
打开文件夹
导入时间线
重新生成
导出
删除
复制路径
```

### 11.4 后端模型

```text
pipeline_artifacts
```

字段：

| 字段 | 说明 |
|---|---|
| `id` | artifact id |
| `project_id` | 项目 |
| `job_id` | 来源任务 |
| `kind` | script/storyboard/voice/subtitle/timeline/preview/render |
| `name` | 名称 |
| `file_path` | 文件路径 |
| `metadata_json` | 元信息 |
| `created_at` | 创建时间 |

---

## 12. 前端改造方案

### 12.1 首页改造

文件：

```text
apps/desktop/src/pages/dashboard/CreatorDashboardPage.vue
```

新增组件：

```text
apps/desktop/src/modules/dashboard/CreativeEntryCards.vue
apps/desktop/src/modules/dashboard/ProjectProductionFlow.vue
apps/desktop/src/modules/dashboard/RecentPipelineJobs.vue
```

首页结构：

```text
Header
CreativeEntryCards
CurrentProjectProductionFlow
RecentProjects
RecentPipelineJobs
RuntimeHealthSummary
```

### 12.2 ProjectProductionFlow

每个项目显示主链状态：

```text
资料 → 脚本 → 分镜 → 配音 → 字幕 → 时间线 → 导出
```

状态：

```text
未开始 / 生成中 / 待确认 / 已完成 / 有错误
```

每一步都有动作：

```text
生成
编辑
重新生成
汇入时间线
预览
导出
```

### 12.3 PipelineLauncher

弹窗/抽屉：

```text
任务类型
输入方式
目标语言
目标时长
音色
字幕样式
是否批量
停止阶段
```

### 12.4 CreativeSegmentTable

字段：

```text
序号
画面
配音文本
字幕文本
音频模式
来源时间码
预计时长
状态
操作
```

操作：

```text
编辑
试听
预览片段
重新生成配音
重新生成字幕
汇入时间线
```

### 12.5 M05 调整

M05 头部按钮建议改为：

当前：

```text
刷新工作台 / 汇入创作链路 / 本地预检 / 保存时间线 / 智能粗剪
```

建议：

```text
汇入片段
预览当前时间线
导出前检查
保存
AI 优化剪辑
```

减少工程味，强化用户动作。

---

## 13. Runtime Client 改造

新增函数：

```ts
// creative segments
export async function fetchCreativeSegments(projectId: string): Promise<CreativeSegmentListDto>
export async function createCreativeSegment(projectId: string, input: CreativeSegmentInput): Promise<CreativeSegmentDto>
export async function updateCreativeSegment(segmentId: string, input: CreativeSegmentUpdateInput): Promise<CreativeSegmentDto>
export async function deleteCreativeSegment(segmentId: string): Promise<void>
export async function reorderCreativeSegments(projectId: string, segmentIds: string[]): Promise<CreativeSegmentListDto>
export async function validateCreativeSegments(projectId: string): Promise<CreativeSegmentValidationDto>

// creative pipeline
export async function runCreativePipeline(projectId: string, input: CreativePipelineRunInput): Promise<CreativePipelineStartedDto>
export async function fetchCreativePipelineJob(jobId: string): Promise<CreativePipelineJobDto>
export async function fetchProjectCreativePipelineJobs(projectId: string): Promise<CreativePipelineJobDto[]>
export async function cancelCreativePipelineJob(jobId: string): Promise<CreativePipelineJobDto>
export async function retryCreativePipelineJob(jobId: string): Promise<CreativePipelineJobDto>
export async function applyPipelineToTimeline(jobId: string): Promise<WorkspaceTimelineResultDto>

// media normalize
export async function fetchAssetMediaProfile(assetId: string): Promise<MediaProfileDto>
export async function normalizeAsset(assetId: string, input: MediaNormalizeInput): Promise<MediaNormalizeResultDto>
export async function batchNormalizeAssets(input: BatchMediaNormalizeInput): Promise<BatchMediaNormalizeResultDto>
```

---

## 14. TaskBus 事件扩展

新增事件类型：

```ts
type CreativePipelineEventType =
  | 'creative.pipeline.started'
  | 'creative.pipeline.step_started'
  | 'creative.pipeline.step_progress'
  | 'creative.pipeline.step_completed'
  | 'creative.pipeline.step_failed'
  | 'creative.pipeline.completed'
  | 'creative.pipeline.failed'
```

事件结构：

```ts
type CreativePipelineEvent = {
  schema_version: 1
  type: CreativePipelineEventType
  taskId: string
  jobId: string
  projectId: string
  stage: CreativePipelineStage
  progressPct: number
  message: string
  artifactIds?: string[]
  errorCode?: string
}
```

前端 `task-bus.ts` 保持兼容，但要把 `jobId`、`stage` 纳入 `lastEvents` key。

---

## 15. 错误码设计

新增错误码：

| error_code | 场景 |
|---|---|
| `creative.segment.invalid` | 片段字段不完整 |
| `creative.segment.empty` | 项目没有可用片段 |
| `creative.pipeline.invalid_input` | 流水线输入不完整 |
| `creative.pipeline.stage_failed` | 阶段失败 |
| `creative.pipeline.cancelled` | 用户取消 |
| `media.probe_failed` | 媒体信息读取失败 |
| `media.normalize_failed` | 归一化失败 |
| `media.unsupported_format` | 不支持格式 |
| `timeline.assemble_failed` | 汇入时间线失败 |
| `render.preview_failed` | 预览生成失败 |

每个错误要返回：

```json
{
  "ok": false,
  "error": "中文可见错误",
  "error_code": "media.normalize_failed",
  "requestId": "...",
  "details": {
    "assetId": "asset-1",
    "recoverAction": "open_media_diagnostics"
  }
}
```

---

## 16. 代码落地顺序

### M1：模型与接口骨架

目标：先建立 CreativeSegment / CreativePipeline 的数据面。

后端：

```text
creative_segment.py
creative_pipeline.py
creative_segments.py
creative_pipeline.py
creative_segment_repository.py
creative_pipeline_repository.py
creative_segment_service.py
creative_pipeline_service.py
creative_segments_router
creative_pipeline_router
```

前端：

```text
runtime-client.ts 新增函数
stores/creative-segments.ts
stores/creative-pipeline.ts
```

测试：

```text
tests/contracts/test_creative_segments_contract.py
tests/contracts/test_creative_pipeline_contract.py
tests/runtime/test_creative_segment_service.py
tests/runtime/test_creative_pipeline_service.py
```

验收：

```text
可以创建/查询/更新/删除项目片段
可以启动一个 pipeline job，并返回 jobId/taskId
文档路由与 FastAPI 注册路由一致
```

---

### M2：首页任务入口与项目流程

目标：让用户打开软件就知道下一步做什么。

前端：

```text
CreativeEntryCards.vue
ProjectProductionFlow.vue
CreativePipelineLauncher.vue
RecentPipelineJobs.vue
```

验收：

```text
首页可选择 4 个任务入口
选择后打开 PipelineLauncher
可提交任务并看到任务进入队列
```

---

### M3：CreativeSegment 与脚本/分镜联动

目标：脚本生成后落成片段，而不是只留在脚本页。

后端：

```text
ScriptService 生成后可调用 CreativeSegmentService
StoryboardService 可把镜头映射到 segment
```

前端：

```text
CreativeSegmentTable.vue
CreativeSegmentEditorDrawer.vue
```

验收：

```text
生成脚本后自动生成 segments
用户可编辑 segment 的画面/配音/字幕/音频模式
segment 保存后可被 M05 汇入
```

---

### M4：配音/字幕按 Segment 生成

目标：配音和字幕不再只是页面级轨道，而是能绑定到片段。

后端：

```text
VoiceService.generate_for_segments(project_id, segment_ids)
SubtitleService.generate_for_segments(project_id, segment_ids)
```

验收：

```text
每个 segment 可生成 voiceTrackId/subtitleTrackId
音频时长回写 durationMs
字幕时间码可回写
```

---

### M5：MediaNormalizeService

目标：素材进入时间线前可检测、归一化、生成代理。

后端：

```text
media/probe.py
media/normalize.py
services/media_normalize_service.py
```

前端：

```text
MediaProfileBadge.vue
MediaNormalizePanel.vue
AssetNormalizeAction.vue
```

验收：

```text
资产卡片显示分辨率、比例、FPS、编码
不适合 9:16 的素材可一键归一化
M05 优先使用 proxy/normalizedPath 预览
```

---

### M6：Segment -> Timeline 汇入

目标：M05 成为主链终点。

后端：

```text
WorkspaceAssemblyService.assemble_from_segments(project_id)
```

前端：

```text
M05 汇入片段按钮
Segment 来源详情
时间线受管轨道标记
```

验收：

```text
segments 能生成 video/voice/subtitle/original audio 轨道
每个 clip 能追溯 segmentId
用户可选择 replace/merge/append 模式
```

---

### M7：预览、结果墙、导出

目标：形成结果闭环。

后端：

```text
PipelineArtifactRepository
RenderService preview/render 接 pipeline artifact
```

前端：

```text
PipelineResultWall.vue
ArtifactPreviewCard.vue
```

验收：

```text
pipeline 生成的脚本/配音/字幕/时间线/视频集中展示
用户可预览、打开文件夹、重新生成、导出
```

---

### M8：批量变体生成

目标：支持运营场景下的一次多版本生产。

后端：

```text
VariantBatchService
```

前端：

```text
BatchVariantWizard.vue
VariantResultGrid.vue
```

验收：

```text
同一项目可生成多个脚本/音色/字幕/素材组合版本
每个版本可独立进入时间线或导出
```

---

## 17. 测试方案

### 17.1 后端单元测试

新增测试：

```text
tests/runtime/test_creative_segment_service.py
tests/runtime/test_creative_pipeline_service.py
tests/runtime/test_media_normalize_service.py
tests/runtime/test_segment_to_timeline_assembly.py
```

覆盖：

- segment CRUD；
- segment reorder；
- segment validate；
- pipeline stopAt；
- pipeline step failure；
- media probe fallback；
- timeline assembly；
- artifact creation。

### 17.2 契约测试

新增：

```text
tests/contracts/test_creative_segments_contract.py
tests/contracts/test_creative_pipeline_contract.py
tests/contracts/test_media_normalize_contract.py
```

并更新：

```text
tests/contracts/test_runtime_contract_inventory.py
```

要求：

```text
RUNTIME-API-CALLS.md 必须记录新增接口
FastAPI 注册路由必须与文档一致
前端 runtime-client 类型必须与响应 schema 一致
```

### 17.3 前端测试

新增：

```text
apps/desktop/tests/creative-pipeline-store.test.ts
apps/desktop/tests/creative-segments-store.test.ts
apps/desktop/tests/creator-dashboard-entry-cards.test.ts
apps/desktop/tests/project-production-flow.test.ts
apps/desktop/tests/workspace-segment-assembly.test.ts
```

覆盖：

- 首页任务入口；
- PipelineLauncher 参数提交；
- 任务状态展示；
- CreativeSegmentTable 编辑；
- M05 汇入片段；
- 结果墙展示。

### 17.4 E2E 验收场景

最小闭环：

```text
1. 新建项目
2. 点击“从产品资料生成视频”
3. 输入产品标题和 3 个卖点
4. 选择英文、9:16、30 秒、生成到时间线
5. 等待 pipeline 完成
6. 查看 CreativeSegmentTable
7. 汇入 M05 时间线
8. 本地预检通过
9. 生成预览
10. 导出 MP4
```

验收标准：

```text
全流程无假数据
每一步有状态反馈
失败可见且可重试
生成产物可在结果墙找到
导出文件真实存在
```

---

## 18. 文档同步要求

每次改动必须同步：

| 文件 | 要求 |
|---|---|
| `docs/PRD.md` | 更新产品范围、主流程、CreativeSegment 定义 |
| `docs/UI-DESIGN-PRD.md` | 更新首页任务入口、ProjectProductionFlow、结果墙 |
| `docs/ARCHITECTURE-BOOTSTRAP.md` | 更新目录、模型、路由归属 |
| `docs/RUNTIME-API-CALLS.md` | 登记新增 API |
| `docs/PROJECT-STATUS.md` | 更新当前状态 |
| `CHANGELOG.md` | 记录版本变化 |

禁止只改代码不改文档。

---

## 19. 风险与边界

### 19.1 不直接复制参考项目代码

原因：

- NarratoAI 明确写了不得商用，需要商业授权。
- MoneyPrinterPlus 文件头部声明商业使用需授权。
- 即使许可证允许，也不建议把 Streamlit/全局状态/脚本式逻辑直接搬入 TK-OPS。

正确做法：

```text
借鉴产品流程、数据结构、处理策略；重新按 TK-OPS 架构实现。
```

### 19.2 自动发布能力谨慎推进

当前不建议优先做强自动发布。先做：

```text
发布资料打包
发布前检查
标题/标签/文案配置
发布记录
半自动辅助
```

避免产品被带偏为平台规避工具。

### 19.3 不要再扩大模块面

现在不是继续新增第 17、18 个中心页面的阶段。当前重点是：

```text
压缩入口
打通主链
强化结果
提升可编辑性
```

---

## 20. 开发开工清单

### 第一批 PR 建议

#### PR-1：CreativeSegment 模型与 API

范围：

```text
后端模型 / repository / service / router / schema / contract tests
前端 runtime-client 类型和 store
```

验收：

```text
项目可以增删改查 CreativeSegment
接口已登记到 RUNTIME-API-CALLS.md
```

#### PR-2：CreativePipeline 骨架

范围：

```text
pipeline job 模型
run/cancel/retry 查询接口
TaskBus 事件
前端 store
```

验收：

```text
可以提交一个 mock pipeline job
前端能看到阶段进度
```

#### PR-3：首页任务入口

范围：

```text
CreativeEntryCards
CreativePipelineLauncher
ProjectProductionFlow
```

验收：

```text
用户打开首页能看到明确的 4 个任务入口
```

#### PR-4：SegmentTable 与脚本回流

范围：

```text
脚本生成结果落成 CreativeSegment
SegmentTable 支持编辑和保存
```

验收：

```text
生成脚本后可以看到片段表
```

#### PR-5：M05 Segment 汇入

范围：

```text
WorkspaceAssemblyService 从 CreativeSegment 组装轨道
M05 增加“汇入片段”
```

验收：

```text
片段能进入时间线，clip 可追溯 segmentId
```

---

## 21. 开发者关键原则

1. **用户任务优先，不再以模块优先。**
2. **CreativeSegment 是主链中间态，不能绕过。**
3. **Pipeline 是业务任务，TaskBus 是底层状态，不要混淆。**
4. **所有 AI 输出必须可编辑、可重试、可回滚。**
5. **所有媒体进入时间线前必须可 probe、可预检。**
6. **M05 是主链中枢，不是普通页面。**
7. **结果必须集中展示，不能散落在各页面。**
8. **不要新增泛后台能力。**
9. **不要直接复制参考项目代码。**
10. **每个阶段都要能单独验收。**

---

## 22. 最终目标图

```text
用户入口
  ↓
任务选择：产品生成 / 参考视频重制 / 批量混剪 / 继续编辑
  ↓
CreativePipelineJob
  ↓
CreativeSegment[]
  ↓
配音 / 字幕 / 素材归一化
  ↓
M05 时间线
  ↓
预览 / 微调 / 导出
  ↓
结果墙 / 发布准备 / 复盘
```

这就是下一阶段 TK-OPS 应该形成的产品形态：

```text
不是一堆功能中心，
而是一条能真实产出短视频的 AI 创作主链。
```

---

## 23. 附录：参考项目吸收清单

| 参考项目 | 借鉴点 | TK-OPS 落点 |
|---|---|---|
| MoneyPrinterTurbo | 主题到视频的流水线 | CreativePipeline |
| MoneyPrinterTurbo | stop_at 分阶段生成 | Pipeline stopAt |
| MoneyPrinterTurbo | VideoParams 聚合参数 | CreativeJobParams |
| MoneyPrinterTurbo | 字幕/BGM/素材拼接 | Render/MediaNormalize |
| NarratoAI | 结构化脚本 JSON | CreativeSegment |
| NarratoAI | OST 音频模式 | SegmentAudioMode |
| NarratoAI | 统一裁剪策略 | VideoDeconstruction / MediaNormalize |
| NarratoAI | 剪映草稿导出 | RenderExportCenter |
| MoneyPrinterPlus | 任务入口清晰 | 首页重构 |
| MoneyPrinterPlus | 批量混剪 | BatchVariantJob |
| MoneyPrinterPlus | 素材归一化 | MediaNormalizeService |
| MoneyPrinterPlus | 发布配置结构 | PublishingCenter |

---

## 24. 版本落地建议

建议版本规划：

| 版本 | 目标 |
|---|---|
| `0.5.0` | CreativeSegment + Pipeline 骨架 + 首页任务入口 |
| `0.5.1` | 脚本/分镜生成回流 CreativeSegment |
| `0.5.2` | 配音/字幕按 Segment 生成 |
| `0.5.3` | M05 从 Segment 汇入真实时间线 |
| `0.5.4` | MediaNormalize + 资产预检 |
| `0.5.5` | 预览/结果墙/基础导出闭环 |
| `0.6.0` | 批量变体生成 + 剪映草稿导出 PoC |

---

## 25. 最小可交付闭环定义

当以下链路跑通时，TK-OPS 才算进入“产品可体验”阶段：

```text
新建项目
→ 从产品资料生成视频
→ 自动生成 CreativeSegment
→ 生成配音
→ 生成字幕
→ 汇入 M05 时间线
→ 本地预览
→ 导出 MP4
→ 结果墙可查看
```

最小交付不要求自动发布，不要求复杂复盘，不要求多账号执行。

优先保证：

```text
能生成
能编辑
能预览
能导出
能追溯
```

这就是开发团队下一阶段的核心任务。
