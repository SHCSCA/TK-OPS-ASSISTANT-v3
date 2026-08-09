# TK-OPS 拆解表格、AI 配置闭环与空状态交互规格

> 日期：2026-07-19  
> 状态：已批准  
> 对应计划：`docs/superpowers/plans/2026-07-19-deconstruction-tables-ai-configuration-empty-states.md`  
> 增量基线：`docs/superpowers/specs/2026-07-19-creative-item-chain-and-library-taxonomy-prototype-design.md`  
> 外部参考：[`ATH-MaaS/Pixelle-Video`](https://github.com/ATH-MaaS/Pixelle-Video)  
> 研究记录：`docs/research/2026-07-19-pixelle-video-adoption-analysis.md`  
> 实现范围：`docs/prototypes/tk-ops-account-workspace/`、`tests/prototypes/`  
> 目标终端：Windows PC 桌面应用，不考虑手机端

## 1. 规格定位

本规格解决三个已确认的小而关键的问题：

1. 视频拆解结果难以连续阅读和跨行比较。
2. AI 设置只有 Provider 外壳，没有 Provider 新增、模型、能力路由和 Prompt 配置闭环。
3. 原型只演示有数据状态，没有页面级首次使用、无数据、筛选为空和前置不足。

同时，本规格把 Pixelle-Video 中已验证的输入模式、线性流水线、能力契约、结构化进度、视觉风格、模板预览和已有素材分析正式映射到 TK-OPS。

发生冲突时，本规格只覆盖增量基线中的以下部分：

- 视频拆解结果容器及四类结果组件。
- 系统设置中的 AI 能力分区。
- 批量生产向导中的固定脚本、已有素材和能力参数展示。
- 十个账号级页面与 AI 设置的业务空态。
- 相关演示数据、状态、配置、样式和测试。

规格批准前禁止修改原型实现。批准后不得借本轮恢复 AI 剪辑工作台、增加手机端、接入真实密钥或扩展主导航。

## 2. Pixelle-Video 采用结论

### 2.1 直接采用

| 能力 | TK-OPS 落点 |
| --- | --- |
| 主题生成 / 固定脚本 | 批次输入模式与单条生产共用 |
| 固定脚本按段落 / 行 / 句子拆分 | 固定脚本步骤的镜头草稿预览 |
| 内容、视觉、逐镜头媒体、TTS、合成流水线 | `GenerationRun` / `GenerationStep` |
| 直接 API / ComfyUI / RunningHub 统一来源 | Provider 适配层与能力路由 |
| 能力元数据驱动模型参数 | `ModelCapability.parameterSchema` |
| 任务级 / 镜头级结构化进度 | 生成节点、任务抽屉和 Detail Panel |
| Prompt 风格前缀 | 版本化 `PromptProfile.visualStylePrefix` |
| 静态 / 图片 / 视频模板与预览 | `CompositionTemplateProfile` |
| 已有素材分析和场景匹配 | 当前账号资产分析与分镜候选 |
| 批量与历史 | 账号级批次、任务日志和内容库 |

### 2.2 适配后采用

- “每句一帧”改为“每个已确认分镜镜头一份媒体计划”。
- “一键全自动”改为通过脚本采用、分镜确认、素材权利确认和发布预检门槛的自动执行。
- 全局 Prompt 前缀改为系统 Prompt、账号配方和单次批次覆盖的版本化继承。
- 全局 Provider 配置改为 Provider、模型、能力契约、能力路由、Prompt 和账号配方分层。
- 自动回退素材改为候选、置信度和人工确认。
- 审核失败自动改写 Prompt 改为可见建议和新版本，禁止静默改变创作意图。

### 2.3 当前不采用

- Streamlit 三栏外观和单工作区状态。
- 动作迁移、参考视频生成、数字人、参考音色和声音克隆。
- 普通用户编辑 ComfyUI 原始 JSON、命令行或供应商私有请求体。
- 将完整 Prompt、请求正文、私密路径或密钥写入日志。
- 将供应商营销能力直接视为可用能力。

## 3. AI 配置对象与继承

### 3.1 系统对象

```text
ProviderProfile
└── ModelProfile[]
    └── ModelCapability[]

PromptProfile[]
CompositionTemplateProfile[]

CapabilityRoute
├── primaryModelProfileId
├── fallbackModelProfileId
├── promptProfileVersionId
└── parameterDefaults
```

### 3.2 运行继承

```text
系统 CapabilityRoute
→ 账号 AccountAIRecipe 覆盖
→ 单次 ProductionBatch 覆盖
→ 不可变 GenerationRun 配置快照
```

Provider 只负责连接；Model 表示真实调用实体；ModelCapability 表示事实能力；CapabilityRoute 决定产品功能调用什么；PromptProfile 管理提示与结构化输出；AccountAIRecipe 管理账号风格、音色、模板、成本和回退。

### 3.3 核心字段

#### ProviderProfile

| 字段 | 说明 |
| --- | --- |
| `id` | 稳定标识 |
| `name` | 用户可识别名称 |
| `adapterType` | direct-api、openai-compatible、comfyui、runninghub |
| `baseUrl` | 脱敏显示 |
| `credentialRef` | 安全存储引用，不保存明文 |
| `region` | 可选区域 |
| `proxyRef` | 可选代理配置引用 |
| `concurrency` | 并发上限 |
| `timeoutSeconds` | 默认超时 |
| `health` | untested、testing、ready、warning、error |
| `lastTestedAt` | 最近测试时间 |
| `logId` | 最近测试日志引用 |

#### ModelProfile

| 字段 | 说明 |
| --- | --- |
| `id` | 系统对象 ID |
| `providerProfileId` | 所属 Provider |
| `modelId` | 真实调用模型 ID |
| `displayName` | 显示名 |
| `enabled` | 是否允许进入路由 |
| `discoverySource` | discovered 或 manual |
| `contextLimit` | 文本上下文或媒体基础限制 |
| `capabilityRevision` | 当前能力契约修订 |

#### ModelCapability

| 字段 | 说明 |
| --- | --- |
| `declaredAbilities` | 供应商或工作流声明能力 |
| `adapterAbilities` | 当前适配器真实接入能力 |
| `inputModalities` | 声明输入模态 |
| `adapterInputModalities` | 当前适配器实际接受的模态 |
| `parameterSchema` | 时长、比例、分辨率、负向提示、原生音频、水印、并发等 |
| `contractVerified` | 契约是否验证 |
| `verifiedAt` | 最近验证时间 |
| `sourceUrls` | 契约来源 |
| `contractIssues` | 已知限制与缺口 |

可用能力只取：

```text
declaredAbilities ∩ adapterAbilities，且 contractVerified = true
```

#### PromptProfile

| 字段 | 说明 |
| --- | --- |
| `name` | 模板名称 |
| `capabilityId` | 所属产品能力 |
| `systemPrompt` | 系统提示 |
| `taskTemplate` | 任务模板 |
| `variables` | 变量定义、类型、必填和默认值 |
| `outputSchema` | 结构化输出 Schema |
| `visualStylePrefix` | 图像 / 视频风格前缀 |
| `safetyConstraints` | 禁止项与安全约束 |
| `version` | 不可变版本号 |
| `status` | draft、active、archived |
| `referencedBy` | 路由与账号配方引用 |

#### CompositionTemplateProfile

| 字段 | 说明 |
| --- | --- |
| `name` | 模板名称 |
| `templateType` | static、image、video |
| `aspectRatio` | 9:16、16:9、1:1 等 |
| `parameterSchema` | 强调色、背景、字幕样式等受控参数 |
| `previewAssetId` | 真实预览资产；可为空 |
| `compatibleAbilities` | 可接受的媒体能力 |
| `version` | 模板版本 |
| `enabled` | 是否可选 |

## 4. 视频拆解结果表格

### 4.1 总体布局

```text
┌──────────── 拆解任务 220–240 ───────────┬──────────────── 结果区 ───────────────┐
│ 任务列表                                │ 来源 · 阶段 · 结果状态          [详情] │
│ 当前任务                                ├───────────────────────────────────────┤
│ 其他任务                                │ 脚本文案 | 关键词 | 关键帧 | 内容结构 │
│                                         ├───────────────────────────────────────┤
│                                         │ 当前标签的表格 / 稳定空态             │
│                                         ├───────────────────────────────────────┤
│                                         │ 已选摘要                  [应用至创作] │
└─────────────────────────────────────────┴───────────────────────────────────────┘
```

- 表格区与底部动作区独立滚动边界清晰。
- 行选择不使用整行青色填充，只使用复选框、浅背景和左侧细线。
- 正文列最多三行；完整内容通过行展开或 Detail Panel 阅读。
- 所有表头有 `scope=col`，复选框有包含时间或关键词的可访问名称。

### 4.2 脚本文案表

| 列 | 建议宽度 | 表现 |
| --- | --- | --- |
| 选择 | 44 | 固定列 |
| 时间段 | 86 | `00:00–00:04` 两行或紧凑显示 |
| 脚本文案 | 自适应，最小 280 | 两至三行，超出展开 |
| 段落作用 | 92 | Hook、方法、证据、CTA 等短标签 |
| 置信度 | 90 | 高 / 中 / 低 + 数值 |

行点击只选中并打开详情，不直接切换复选框。证据不足的置信度显示“待复核”，不能用假百分比填充。

### 4.3 关键词表

| 列 | 建议宽度 | 表现 |
| --- | --- | --- |
| 选择 | 44 | 固定列 |
| 关键词 | 自适应，最小 180 | 主文字 |
| 分类 | 100 | 主题、对象、视觉、动作、语气 |
| 权重 | 130 | 数值 + 低对比细条 |
| 命中 | 72 | 次数 |
| 证据 | 150 | 一个或多个可聚焦时间点 |

点击时间点切换到对应脚本段或打开来源详情。标签颜色只区分类别，不表达权重。

### 4.4 关键帧表

| 列 | 建议宽度 | 表现 |
| --- | --- | --- |
| 选择 | 44 | 固定列 |
| 预览 | 112 | 真实 16:9 或 9:16 缩略图 |
| 时间点 | 76 | 精确到秒 |
| 镜头作用 | 100 | 结果前置、步骤切换、验证等 |
| 画面摘要 | 自适应，最小 220 | 两行 |
| 可复用方向 | 130 | 分镜参考、封面、图片资产 |

无真实帧时不渲染表头，使用：

```text
尚未提取到真实关键帧
当前结果不能作为分镜或图片资产使用。
[重新提取]
```

### 4.5 内容结构

表格上方为低高度结构摘要：

```text
特点总结：前 4 秒直接展示结果，随后用三步方法和效果验证完成闭环。
主要类型：结果前置教学   总时长：36 秒   结构：4 段
[结果前置] [步骤教学] [证据闭环] [短 CTA] [快节奏口播]
```

Tag 最多显示五个，更多进入“查看全部”。Tag 来自已完成分析或人工确认；缺失时显示“尚未形成特点标签”，不自动生成演示标签。

| 列 | 建议宽度 | 表现 |
| --- | --- | --- |
| 选择 | 44 | 固定列 |
| 结构段 | 92 | Hook、方法、证据、CTA |
| 时间 | 96 | 起止时间 |
| 时长占比 | 100 | 数值 + 比例条 |
| 作用 | 150 | 一句总结 |
| 对应文案 | 自适应，最小 220 | 两行 |
| 证据关键词 | 160 | 最多三个短标签 |

### 4.6 紧凑窗口

- `1180px`：保留全部主列，次要说明缩短，表格局部滚动。
- `960px`：任务列表收窄至 `188px`；脚本表隐藏置信数值、关键词表隐藏命中、关键帧表隐藏可复用方向、结构表隐藏证据关键词，但详情仍可查看。
- 页面本身不得出现横向滚动；底部“应用至创作”始终可见。

## 5. AI 能力设置

### 5.1 页面层级

```text
AI 与系统设置
├── AI 能力
│   ├── Provider
│   ├── 模型与能力
│   └── Prompt 模板
├── Runtime 与工作区
└── 日志与诊断
```

进入 AI 能力默认打开 Provider。二级标签固定在内容表面顶部，不增加左侧三级导航。

### 5.2 Provider 页面

顶部只保留：

```text
AI 能力就绪  9 / 11    需处理 2 项                         [添加 Provider]
```

Provider 使用紧凑列表或表格，列为名称、适配方式、连接健康、可用模型、已路由能力、最近测试和一个主动作。点击行打开右侧详情；“添加 Provider”必须打开向导，禁止 Toast 占位。

### 5.3 添加 Provider 向导

向导宽度 `760px`，五步：

1. 连接类型。
2. 地址与凭据引用。
3. 网络与并发。
4. 发现或手动添加模型。
5. 测试并保存。

#### 第一步：连接类型

选项只显示名称与一句差异：直接 API、OpenAI Compatible、本地 ComfyUI、RunningHub。选择后才显示该类型字段，不把全部 Provider 表单堆在同一页。

#### 第二步：地址与凭据

- Provider 名称。
- Base URL。
- 区域，仅适用时出现。
- 凭据安全存储引用。
- 代理配置引用，仅适用时出现。

原型使用明确的“演示凭据引用”，不展示看似真实的密钥。

#### 第三步：网络与并发

- 超时。
- 并发上限。
- 代理启用状态。
- 本地 Runtime 依赖检查。

字段范围来自统一 `prototypeConfig`，组件内不硬编码。

#### 第四步：模型

- “发现模型”运行稳定加载状态，并返回明确标注的演示结果。
- 发现失败保留输入，提供“重试发现”和“手动添加”。
- 手动添加要求真实模型 ID、显示名和基础类型，不能直接勾选任意营销能力。

#### 第五步：测试并保存

测试项：地址格式、凭据引用、Runtime 可达、模型可见、能力元数据。结果按通过、警告、失败展示；失败时保留向导状态和日志引用。

只有必需项通过才允许保存。保存后选中新 Provider，显示“尚未配置能力路由”而不是假装系统已就绪。

### 5.4 Provider 状态机

```text
draft -> testing -> ready
draft -> testing -> error
ready -> testing -> ready | warning | error
warning | error -> testing -> ready | warning | error
```

关闭有未保存内容的向导时询问“继续编辑 / 放弃草稿”。测试请求支持取消，取消后返回当前步骤。

## 6. 模型与能力

### 6.1 双区布局

```text
┌──────────────── 模型档案 ────────────────┐
│ 搜索 · Provider 筛选 · 验证状态          │
│ 模型表                                    │
├──────────────── 能力路由 ────────────────┤
│ 产品能力 -> 主模型 -> 回退 -> Prompt      │
└───────────────────────────────────────────┘
```

模型表默认显示模型 ID、Provider、启用、已接入能力、验证状态和限制。供应商声明的额外能力只在详情显示为“尚未接入”。

### 6.2 能力详情

详情分为：

- 已接入能力。
- 供应商声明但未接入。
- 输入模态。
- 可用参数。
- 契约来源与验证时间。
- 已知限制。

未验证模型显示“契约未验证”，不能进入默认能力路由。界面不使用禁用参数墙；不支持的参数完全隐藏。

### 6.3 产品能力路由

能力固定为：

- 选题推荐。
- 脚本生成。
- 脚本优化。
- 分镜规划。
- 视频拆解。
- 语音转写。
- 文生图。
- 文生视频。
- 图生视频。
- TTS。
- 字幕对齐。
- Embedding。

每行显示主模型、回退模型、Prompt、就绪状态和一个“配置”动作。路由保存前校验：

1. 主模型已启用。
2. 主模型能力已接入且契约已验证。
3. Prompt 能力匹配并处于 active。
4. 回退模型若存在，能力与输入模态兼容。

缺失路由必须回传脚本、分镜、拆解和生产入口，显示具体缺项和“前往配置”。

## 7. Prompt、视觉风格与模板

### 7.1 Prompt 页面

左侧为 Prompt 列表，右侧为编辑器。列表只显示名称、能力、版本、状态和引用数量；正文不在列表预览，降低噪音。

编辑器分区：

1. 基础信息。
2. 系统提示与任务模板。
3. 变量与输出 Schema。
4. 视觉风格与安全约束。
5. 版本与引用。

### 7.2 变量预览

变量预览使用脱敏、明确标注的演示输入。预览结果只展示填充后的字段摘要和 Schema 校验，不显示或记录完整账号私密知识。

校验错误就地显示：缺少变量、未知变量、重复变量、Schema 无效、能力不匹配。保存新版本前必须全部通过。

### 7.3 风格前缀

图像和视频 Prompt 可以配置 `visualStylePrefix`，但最终执行按以下顺序合并：

```text
PromptProfile 风格基础
→ AccountAIRecipe / BrandKit 账号约束
→ Storyboard 镜头画面描述
→ 本批次显式覆盖
```

合并结果生成安全摘要和版本引用，不把完整 Prompt 写入节点列表或日志。

### 7.4 模板选择

模板选择器按静态、图片、视频和画幅筛选，卡片只显示真实预览、名称、类型、画幅与适用能力。点击后在 Detail Panel 显示可配置参数和兼容性。

普通设置页不编辑 HTML。无真实预览时使用类型图标和“暂无预览”，不能生成假模板画面。

## 8. 批量生产中的 Pixelle 能力落点

### 8.1 固定脚本

选择固定脚本后出现拆分方式：段落、行、句子。下方实时显示镜头草稿数量与前三段预览；超过合理上限时显示影响并要求缩减，不静默截断。

脚本拆分完成后仍生成 `ScriptVersion` 和 `StoryboardVersion`，只是脚本生成节点标记为 skipped。用户可返回脚本 / 分镜校对，不从向导直接跳过业务版本。

### 8.2 已有素材

流程为：

```text
选择当前账号资产
→ 资产分析
→ 生成或读取脚本
→ 分镜素材匹配
→ 低置信项确认
→ 进入统一生产节点
```

分析失败的资产保留并标记，不把首个资产作为静默回退。匹配详情记录资产版本、分析模型、Prompt 版本和置信度。

### 8.3 模型专属参数

能力参数由 `parameterSchema` 渲染：

- 视频时长。
- 分辨率。
- 比例。
- 负向提示。
- 原生音频。
- 水印。
- 并发限制只读摘要。

只显示当前模型适用字段。改变主模型后重新校验并清理不兼容覆盖，清理前显示影响确认。

### 8.4 进度

节点主行显示：

```text
图片 / 视频       生成镜头 3 / 8 · 视频       42%       01:18
```

详情显示当前镜头、动作、已完成、排队、失败、Provider、模型、版本和日志引用。并发任务仍按分镜顺序展示；重试单镜头不重跑脚本、分镜或其他成功镜头。

## 9. 页面级空状态

### 9.1 状态分类

| 类型 | 条件 | 行为 |
| --- | --- | --- |
| `first_use` | 模块从未建立对象 | 解释第一步并给唯一主动作 |
| `no_data` | 无业务对象 | 创建或导入 |
| `filtered_empty` | 有对象但筛选无结果 | 清除筛选 |
| `dependency_blocked` | 缺上游版本、连接或能力 | 前往最近的修复入口 |
| `waiting_external` | 等 Provider、任务或平台回执 | 查看任务或刷新 |
| `restricted` | 账号、工作区或能力不可用 | 修复账号或系统能力 |

业务页面自行解析状态。全局 `StatePanel` 只处理应用加载和全局错误。

### 9.2 页面矩阵

| 页面 | 主要判定 | 标题 | 主动作 |
| --- | --- | --- | --- |
| 工作台 | 账号未就绪 | 当前账号尚未完成设置 | 完成账号设置 |
| 工作台 | 已就绪且无内容 | 从第一个选题开始 | 新建选题 |
| 定位与知识 | 无定位 | 先建立账号定位 | 建立定位 |
| 定位与知识 | 有定位无来源 | 添加第一条知识来源 | 添加知识来源 |
| 脚本与选题 | 无内容 | 创建第一个选题 | 新建选题 |
| 脚本与选题 | 筛选为空 | 没有符合筛选的内容 | 清除筛选 |
| 分镜规划 | 无采用脚本 | 先采用脚本版本 | 返回脚本 |
| 分镜规划 | 有脚本无分镜 | 尚未生成分镜 | 生成分镜 |
| 视频拆解 | 无任务 | 导入参考视频开始拆解 | 导入视频 |
| 视频拆解 | 等待 Provider | 拆解能力暂不可用 | 前往 AI 设置 |
| 批量生产 | 无确认内容 | 先完成脚本与分镜 | 继续创作 |
| 批量生产 | 有确认内容无批次 | 创建第一个生产批次 | 创建批次 |
| 内容库 | 无资产 | 还没有内容资产 | 导入素材 |
| 内容库 | 筛选为空 | 没有符合筛选的资产 | 清除筛选 |
| 媒体工具箱 | 无任务 | 选择工具创建任务 | 选择工具 |
| 发布 | 无成片 | 尚无可发布成片 | 前往生产 |
| 复盘 | 等回执 | 正在等待真实回执 | 查看发布任务 |
| AI 设置 | 无 Provider | 添加第一个 AI Provider | 添加 Provider |
| AI 设置 | 有 Provider 无模型 | 尚未配置可调用模型 | 添加模型 |
| AI 设置 | 有模型无路由 | AI 能力尚未就绪 | 配置能力路由 |

### 9.3 视觉规则

- 空态宽度不超过 `440px`，置于当前工作容器中，不另加大卡片。
- 只使用一个中性图标、标题、说明和主动作。
- 依赖阻断允许一个文字型“查看原因”，不增加第二个按钮。
- `filtered_empty` 保留筛选工具栏，便于清除条件。
- 等待态不使用无限旋转大图；显示状态、最近更新时间和查看任务。

## 10. 状态、异常与恢复

### 10.1 AI 配置错误

| 错误 | 可见反馈 | 恢复 |
| --- | --- | --- |
| 地址格式错误 | 字段就地错误 | 修正后重试 |
| 凭据引用无效 | 向导稳定错误摘要 | 重新选择安全引用 |
| 连接超时 | 保留已填内容与日志 ID | 重试或修改超时 |
| 模型发现失败 | 不清空已发现列表 | 重试或手动添加 |
| 契约未验证 | 模型详情警告 | 补充来源或改用已验证模型 |
| Prompt 变量错误 | 编辑器就地标注 | 修复后保存新版本 |
| 路由能力不匹配 | 路由行阻断 | 切换模型 / Prompt |

### 10.2 数据保存

- 原型所有异步动作使用统一错误捕获与 `prototypeLogger`。
- 保存成功刷新 AI 就绪摘要、路由列表和受影响业务入口。
- 保存失败保留编辑状态，不用 Toast 替代稳定错误。
- Provider、模型、Prompt、路由和模板修改增加 `aiConfigRevision`。
- 运行中的批次继续使用创建时快照，不被新配置静默改变。

## 11. 可访问性、主题与窗口

### 11.1 键盘与焦点

- 二级标签支持方向键切换，具有 `role=tablist`、`role=tab` 和 `aria-selected`。
- 表格复选框、证据时间点、行详情、向导按钮和编辑器均可键盘访问。
- 对话框打开后焦点进入标题或首字段，关闭后回到触发按钮。
- Esc 关闭无修改对话框；有未保存内容时触发守卫。
- 进度更新使用非打断式状态播报，失败使用可感知错误摘要。

### 11.2 Light / Dark

- 表格表头、行 Hover、选择态、警告和焦点均使用设计令牌。
- 深色主题避免整行高亮；权重条、比例条和进度线保持可辨识对比度。
- Prompt 编辑区、代码样式 Schema 区和 Detail Panel 在两种主题下有明确层级。

### 11.3 窗口档位

| 档位 | 布局 |
| --- | --- |
| `1440×900` | 完整双栏、全部主要列、右侧 Detail Panel |
| 约 `1180×760` | 次要列压缩、表格局部滚动、详情覆盖打开 |
| `960×640` | Sidebar 紧凑、任务栏收窄、隐藏次要列、对话框留 24px 边距 |

不考虑手机端，不实现抽屉式移动导航或触屏手势。

## 12. 原型数据与状态边界

### 12.1 数据模块

AI 数据拆分为：

```text
src/data/ai/
├── providerProfiles.js
├── modelProfiles.js
├── modelCapabilities.js
├── promptProfiles.js
├── capabilityRoutes.js
└── compositionTemplates.js
```

演示数据必须标记 `demo: true` 或使用明显的演示名称。不得出现看似真实的密钥、请求结果、成本、关键帧或业务指标。

### 12.2 状态模块

```text
src/state/ai-settings/
├── useProviderProfilesState.js
├── useModelProfilesState.js
├── usePromptProfilesState.js
├── useCapabilityRoutesState.js
└── useAIReadinessState.js
```

如果原型规模不值得建立目录，仍须至少按职责拆成独立 hooks，禁止继续扩大单个 `useAISettingsState.js`。

页面空态统一使用纯函数解析器：

```text
resolvePageEmptyState(pageId, accountWorkspace, aiReadiness, filters)
```

解析器只返回状态定义，页面负责呈现；不得在通用空态组件里拼接业务规则。

## 13. 实现文件地图

### 13.1 视频拆解

- 修改 `src/data/deconstructionResults.js`。
- 重构 `src/components/video-deconstruction/DeconstructionResult.jsx`。
- 重构 `ScriptSegmentsResult.jsx`、`KeywordResult.jsx`、`KeyframeResult.jsx`、`StructureResult.jsx`。
- 新增 `ResultDataTable.jsx`、`deconstructionColumns.js`。
- 修改 `src/styles/deconstruction-results.css`、`responsive.css`。

### 13.2 AI 设置

- 拆分 `src/data/aiCapabilities.js` 为 `src/data/ai/` 下的职责文件。
- 拆分 `src/state/useAISettingsState.js`。
- 修改 `AICapabilitiesCenter.jsx`、`ProviderDetailDrawer.jsx`。
- 新增 `AICapabilityTabs.jsx`、`ProviderWizard.jsx`、`ModelProfileTable.jsx`、`ModelCapabilityDetail.jsx`、`CapabilityRouteTable.jsx`、`PromptProfileTable.jsx`、`PromptProfileEditor.jsx`、`CompositionTemplatePicker.jsx`、`AIReadinessSummary.jsx`。
- 新增独立 AI 设置样式文件。
- 修改 `prototypeConfig.js`，集中适配方式、能力枚举、超时、并发、Prompt 变量和状态延迟。

### 13.3 生产与空态

- 修改 `BatchWizard.jsx`，增加固定脚本拆分、资产分析摘要和能力参数。
- 修改生成节点数据与组件，增加镜头级进度字段。
- 新增 `PageEmptyState.jsx`、`emptyStateDefinitions.js`、`resolvePageEmptyState.js`。
- 修改十个账号级页面与 AI 设置的空态判断。
- 修改 `App.jsx` / `StatePanel.jsx`，移除全局业务空态替代。

### 13.4 测试

- 将现有大测试文件按职责拆为：
  - `deconstruction-tables.test.mjs`
  - `ai-settings.test.mjs`
  - `empty-states.test.mjs`
  - 保留一条跨页主链回归。

## 14. 必须通过的交互测试

1. 四类拆解结果均有正确表头、选择、局部滚动与回流摘要。
2. 内容结构显示特点总结、叙事类型和 Tag；无真实分析时不显示伪标签。
3. 无真实关键帧显示稳定空态；重新提取动作可触发并反馈。
4. 点击添加 Provider 可完成五步向导；字段错误、取消、测试失败、重试和保存成功稳定可见。
5. 模型发现失败后可手动添加；未验证模型不能绑定默认路由。
6. 模型切换后参数只显示能力契约允许的字段，不兼容覆盖需确认清理。
7. Prompt 新建、变量校验、保存新版本、引用查看和未保存守卫可完成。
8. 能力路由缺失会阻断脚本 / 分镜 / 生产动作；修复后返回页面动作恢复。
9. 固定脚本三种拆分方式产生不同镜头草稿，脚本生成节点标记 skipped。
10. 已有素材分析失败或低置信时不静默替代，并可人工确认候选。
11. 生成节点显示任务级与镜头级进度；单镜头失败可局部重试且保留其他镜头。
12. 零数据场景下十个页面显示符合前置顺序的唯一主动作。
13. 筛选为空只提供清除筛选，清除后恢复已有数据。
14. Light / Dark 与 1440、1180、960 三档完成主链，无控制台错误和页面级横向滚动。

## 15. 验收标准

| 维度 | 要求 |
| --- | --- |
| 阅读效率 | 拆解结果可沿列比较，正文不被标签和元数据挤压 |
| 结构洞察 | 视频特点、叙事类型、Tag、比例和证据同时可见但分层清楚 |
| Provider | 添加入口真实可完成，失败可恢复，不再是无动作按钮 |
| 模型 | 模型、声明能力、已接入能力、验证状态和参数边界可追溯 |
| Prompt | 可配置、版本化、校验变量、查看引用和处理未保存状态 |
| 能力路由 | 每个 AI 功能可追溯主模型、回退模型、Prompt 和继承来源 |
| Pixelle 吸收 | 输入、流水线、进度、能力参数、视觉风格、模板和资产分析均有 TK-OPS 落点 |
| 安全边界 | 不引入动作迁移、数字人、声音克隆、明文凭据或完整 Prompt 日志 |
| 空态 | 由真实数据与依赖推导，主动作符合创作顺序 |
| 低噪音 | 页面不形成 Provider / 模型 / Prompt 卡片墙，不堆未支持参数 |
| PC 适配 | 三档窗口和双主题可完成主要任务 |
| 工程边界 | 配置、状态、组件、样式和测试按职责拆分，异常有日志与反馈 |

## 16. 非目标

- 不接入真实 Provider、真实密钥、真实模型发现或真实生成任务。
- 不复制 Pixelle-Video 源代码或 Streamlit 布局。
- 不实现动作迁移、参考视频生成、数字人或声音克隆。
- 不实现 Prompt 市场、团队共享、计费后台或供应商商城。
- 不恢复剪辑工作台或手动时间线。
- 不修改 `apps/desktop`、`apps/py-runtime`、数据库或生产 API。
- 不做手机端适配。
