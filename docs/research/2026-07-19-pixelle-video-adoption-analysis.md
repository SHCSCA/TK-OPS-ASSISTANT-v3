# Pixelle-Video 能力吸收分析

> 日期：2026-07-19  
> 参考仓库：[`ATH-MaaS/Pixelle-Video`](https://github.com/ATH-MaaS/Pixelle-Video)  
> 研究范围：仓库 `main` 分支的 README、配置 Schema、标准流水线、素材流水线、模型能力元数据、进度模型、API Schema、设置页和模板文档  
> 用途：为 TK-OPS 账号级 AI 视频创作中枢提供产品与架构参考，不构成源代码移植决定

## 1. 核心判断

Pixelle-Video 的优势不在三栏 Streamlit 页面，而在以下可组合内核：

1. 从主题或固定脚本进入统一线性生成流水线。
2. 直接 API、ComfyUI、RunningHub 使用统一媒体工作流外形。
3. 模型参数由能力元数据决定，而不是所有模型共用一套表单。
4. 生成任务能报告阶段、总体进度、镜头进度和镜头内动作。
5. 视觉风格前缀、TTS、BGM、模板和模型来源可以组合。
6. 已有图片 / 视频可以先分析，再生成脚本并匹配镜头。

这些机制与 TK-OPS 的“账号定位与知识 -> 脚本 -> 分镜 -> 批量生产 -> 自动合成”方向一致，但必须增加账号隔离、版本采用、能力路由、配置总线、安全凭据、权利确认和发布回执边界。

## 2. 代码证据

| 证据 | 已确认事实 | TK-OPS 含义 |
| --- | --- | --- |
| [`README.md`](https://github.com/ATH-MaaS/Pixelle-Video/blob/main/README.md) | 主题到视频、固定脚本、图像 / 视频、TTS、BGM、模板、批量、历史、直接 API、ComfyUI、RunningHub | 产品链路参考，不照搬 UI |
| [`pixelle_video/pipelines/standard.py`](https://github.com/ATH-MaaS/Pixelle-Video/blob/main/pixelle_video/pipelines/standard.py) | 内容生成、标题、视觉规划、分镜、逐镜头资产、合成 / BGM 的线性流水线 | 对应节点化 `GenerationRun` / `GenerationStep` |
| [`pixelle_video/pipelines/asset_based.py`](https://github.com/ATH-MaaS/Pixelle-Video/blob/main/pixelle_video/pipelines/asset_based.py) | 分析已有图片 / 视频、生成结构化场景脚本、把真实资产匹配到镜头 | 对应当前账号内容库资产分析和分镜素材候选 |
| [`pixelle_video/config/schema.py`](https://github.com/ATH-MaaS/Pixelle-Video/blob/main/pixelle_video/config/schema.py) | LLM、直接 API Provider、ComfyUI / RunningHub、TTS、图像 / 视频风格前缀和模板配置 | 对应统一配置对象，但凭据必须改为安全引用 |
| [`pixelle_video/services/api_media.py`](https://github.com/ATH-MaaS/Pixelle-Video/blob/main/pixelle_video/services/api_media.py) | 模型记录能力类型、输入模态、适配器能力、时长、分辨率、比例、契约来源和已知问题 | 直接启发 `ModelCapability` 的声明 / 接入 / 验证分层 |
| [`web/pipelines/api_workflows.py`](https://github.com/ATH-MaaS/Pixelle-Video/blob/main/web/pipelines/api_workflows.py) | 页面按已验证能力动态显示时长、分辨率、比例、负向提示、水印和原生音频 | TK-OPS 的模型参数必须由 Schema 渲染 |
| [`pixelle_video/models/progress.py`](https://github.com/ATH-MaaS/Pixelle-Video/blob/main/pixelle_video/models/progress.py) | 结构化进度包含事件、总体进度、当前帧 / 总帧、步骤、动作和附加信息 | 扩充任务总线与镜头级进度 |
| [`web/components/content_input.py`](https://github.com/ATH-MaaS/Pixelle-Video/blob/main/web/components/content_input.py) | 固定脚本支持按段落、行、句子拆分；批量主题有数量限制与预览 | TK-OPS 固定脚本入口增加拆分和镜头草稿预览 |
| [`web/components/style_config.py`](https://github.com/ATH-MaaS/Pixelle-Video/blob/main/web/components/style_config.py) | BGM、TTS 预览、静态 / 图片 / 视频模板、画幅分组和真实预览 | 对应账号配方、模板档案和渐进配置 |
| [`docs/zh/reference/api-overview.md`](https://github.com/ATH-MaaS/Pixelle-Video/blob/main/docs/zh/reference/api-overview.md) | 同步 / 异步生成、任务查询、模板参数、媒体工作流、TTS、风格前缀和 BGM 参数 | 为后续 Runtime 契约提供字段参考，不复制返回信封 |

## 3. 已经进入当前 TK-OPS 原型的部分

| 已有原型能力 | 本地证据 | 来源关系 |
| --- | --- | --- |
| 直接 API、ComfyUI、RunningHub Provider | `docs/prototypes/tk-ops-account-workspace/src/data/aiCapabilities.js` | 已吸收多来源能力组合思想 |
| AI 主题、固定脚本、已有素材、已确认内容 | `docs/prototypes/tk-ops-account-workspace/src/components/batch-wizard/BatchWizard.jsx` | 已扩展为 TK-OPS 四种账号级输入 |
| 脚本、分镜、图片 / 视频、TTS、字幕、合成 / BGM、预览节点 | `docs/prototypes/tk-ops-account-workspace/src/data/generationRuns.js` | 已吸收线性流水线，并补入 TK-OPS 脚本 / 分镜版本边界 |
| 节点状态、进度和局部重试 | `docs/prototypes/tk-ops-account-workspace/src/components/generation-pipeline/GenerationPipeline.jsx` | 已吸收结构化进度与最小失败范围思想 |
| 系统 -> 账号 Recipe -> 批次覆盖 | `docs/prototypes/tk-ops-account-workspace/src/components/ai-capabilities/AICapabilitiesCenter.jsx` | 已完成 Provider、模型、路由与 Prompt 的原型配置闭环 |

## 3.1 本轮实现结果

- Provider 已形成五步新增向导，覆盖模型发现、手动录入、连接测试、安全凭据引用和未保存关闭守卫。
- Provider、模型、模型契约、能力路由、Prompt 与组合模板已拆为独立数据和状态职责。
- 固定脚本已支持按段落、行、句子拆分和前三段预览，脚本节点保留但标记为 skipped。
- 已有素材输入已绑定当前账号内容库，并增加“视觉规划”节点与输入快照。
- 视频模型参数由已验证 `parameterSchema` 决定；未验证或能力不匹配的模型不能形成就绪路由。
- 生成节点已加入视觉规划的当前项 / 总项、当前动作和局部重试证据。
- Prompt 已支持变量校验、保存新版本、模板引用和未保存切换守卫。

## 4. 本轮正式采用

### 4.1 输入与流水线

- AI 主题和固定脚本进入同一生产链。
- 固定脚本增加段落、行、句子拆分和镜头草稿预览。
- 已有素材先分析再匹配分镜，保留来源、置信度和人工确认。
- 节点统一为内容、视觉规划、镜头媒体、TTS、字幕、合成 / BGM 和预览。
- 任务级与镜头级进度统一进入 `GenerationStep`，支持并发归并和局部重试。

### 4.2 Provider、模型与能力

- 直接 API、OpenAI-compatible、ComfyUI 和 RunningHub 进入同一 Provider 适配层。
- Provider 只表示连接；`ModelProfile` 表示真实模型；`ModelCapability` 表示能力契约；`CapabilityRoute` 表示产品能力实际调用路径。
- `ModelCapability` 同时记录供应商声明、适配器已接入、契约是否验证、来源、验证时间和已知限制。
- 产品可用能力只取“声明、接入、已验证”的交集，未验证参数不出现在业务页面。
- 模型参数由 Schema 动态显示，包括时长、比例、分辨率、负向提示、原生音频、水印和并发。

### 4.3 Prompt、风格与模板

- 全局风格前缀升级为版本化 `PromptProfile`，并通过账号配方和批次覆盖继承。
- Prompt 包含系统提示、任务模板、变量、输出 Schema、视觉风格前缀和安全约束。
- 模板升级为 `CompositionTemplateProfile`，记录静态 / 图片 / 视频类型、画幅、参数 Schema、真实预览、兼容能力和版本。
- TTS、BGM、模板和模型参数进入不可变任务快照，不能只存在于页面临时状态。

## 5. 适配后采用

- Pixelle-Video 的“每句旁白一帧”改为“每个已确认分镜镜头一份媒体计划”。
- 一键全自动改为有脚本采用、分镜确认、素材权利确认和发布预检门槛的自动执行。
- 自动修正素材路径或回退首个素材改为展示候选、置信度和人工确认。
- 内容审核失败后的 Prompt 调整改为创建可见建议和新版本，不静默改写。
- 全局配置改为系统能力路由、账号 AI 配方和单次批次覆盖，且所有写入统一配置总线。

## 6. 当前不采用

- Streamlit 三栏布局和单一全局工作区。
- 动作迁移、参考视频生成、数字人、参考音色和声音克隆。
- 普通页面编辑 ComfyUI 原始 JSON、命令行或供应商私有请求参数。
- 把完整 Prompt、请求正文、私密路径或密钥写入调试日志。
- 把供应商营销能力直接当成产品可用能力。
- 绕过版本采用、账号隔离、权利确认或真实发布回执的一键执行。

## 7. 许可证与实现边界

Pixelle-Video 使用 Apache-2.0 许可证。当前阶段只吸收公开的产品与架构思路，没有复制源代码。若后续决定复用具体实现，必须单独记录文件来源、许可证头、修改说明、NOTICE 要求和安全审查结果。
