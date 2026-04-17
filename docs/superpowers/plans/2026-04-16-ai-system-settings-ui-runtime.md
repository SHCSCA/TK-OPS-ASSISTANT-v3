# M16 AI 与系统设置 UI 重构与 Runtime 接口文档计划

> 日期：2026-04-16
> 任务等级：A 档，UI 体验重构计划 + Runtime 契约收口
> 主流程：`tkops-ui-experience-council` + `tkops-runtime-contract-council`
> 当前状态：只生成计划与接口文档；未进入页面重构或后端实现。

## 背景

`AI 与系统设置` 是 TK-OPS 的系统可信入口。用户进入这个页面时，真正关心的不是“有多少表单项”，而是：

1. 当前 Runtime、授权、目录和日志是否健康。
2. AI 能力现在能不能用，不能用时差在哪一步。
3. 每个创作能力到底绑定了哪个 Provider、模型、角色和提示词。
4. 凭据是否安全保存，前端能否测试连接但看不到明文密钥。
5. 修改配置后是否可确认、可撤销、可恢复，而不是一次性提交一大张表单。

当前实现已经有基础链路：

- 页面：`apps/desktop/src/pages/settings/AISystemSettingsPage.vue`
- 配置总线 store：`apps/desktop/src/stores/config-bus.ts`
- AI 能力 store：`apps/desktop/src/stores/ai-capability.ts`
- Runtime client：`apps/desktop/src/app/runtime-client.ts`
- 前端类型：`apps/desktop/src/types/runtime.ts`
- 设置路由：`apps/py-runtime/src/api/routes/settings.py`
- AI 能力路由：`apps/py-runtime/src/api/routes/ai_capabilities.py`
- 设置服务：`apps/py-runtime/src/services/settings_service.py`
- AI 能力服务：`apps/py-runtime/src/services/ai_capability_service.py`
- 接口真源：`docs/RUNTIME-API-CALLS.md`
- 已有测试：`apps/desktop/tests/ai-system-settings.spec.ts`、`tests/contracts/test_settings_config_contract.py`、`tests/contracts/test_ai_capabilities_contract.py`、`tests/runtime/test_settings_config.py`、`tests/runtime/test_ai_capabilities.py`

主要问题：

- 页面当前是表单卡片堆叠，用户需要自己理解 Runtime、目录、日志、AI 默认项、能力配置和 Provider 状态之间的关系。
- Provider secret 与健康检查 Runtime client 已存在，但页面尚未提供完整的凭据录入和测试连接体验。
- 当前后端 Provider 元数据仍是固定内置表，不能把产品设计成“只配置一个 OpenAI”的单 Provider 设置页。
- AI 能力配置以卡片形式纵向展开，提示词编辑成本高，比较多个能力时扫描效率低。
- 系统诊断信息没有形成右侧诊断台，用户无法快速定位“为什么 AI 不可用”。
- 保存动作缺少清晰的脏状态、确认范围、保存后反馈和失败恢复路径。
- 紧凑窗口下现有两列网格会变成长列表，用户需要大量滚动才能完成常见任务。

## 多 Provider 与模型目录硬约束

M16 的产品目标不是接入单个 AI，而是成为 TK-OPS 的 AI Provider 与模型编排中心，支持市面主流 AI 模型接入、测试、筛选和按能力选用。后续实现必须按以下边界设计：

- Provider 是可扩展注册对象，不是页面内硬编码选项。
- 模型是 Provider 下的可选能力，不是一个全局文本输入框。
- 每个能力都可以独立选择 Provider、模型、角色、提示词和启用状态。
- 同一 Provider 可服务多个能力，不同能力也可以使用不同 Provider。
- Provider 密钥、Base URL、模型目录、能力支持范围、健康检查状态必须由 Runtime 提供，页面只消费契约。
- 页面必须支持主流商业云 Provider、OpenAI-compatible 聚合服务、本地模型服务和专用媒体/语音 Provider 的扩展。
- 不允许为了视觉完整而展示未真实注册、未配置或未验证的“可用模型”。

目标覆盖方向：

- 文本与多模态模型：OpenAI、Anthropic、Google Gemini、DeepSeek、通义千问/Qwen、月之暗面/Kimi、智谱 GLM、MiniMax、火山/豆包、百度千帆/ERNIE、腾讯混元、xAI、Mistral、Cohere、OpenRouter、OpenAI-compatible。
- 本地与私有化：Ollama、LM Studio、vLLM、LocalAI，以及企业自建 OpenAI-compatible Endpoint。
- 语音与 TTS：OpenAI TTS、Azure Speech、ElevenLabs、火山语音、MiniMax Speech，以及后续真实 TTS Provider。
- 视频与媒体生成：按 `VideoGenerationProvider` 独立接入，不把视频模型硬塞进文本 Provider。
- 资产分析：按 `AssetAnalysisProvider` 独立接入，支持多模态模型或本地分析服务。

上述清单是产品设计覆盖面，不表示当前代码已经全部实现。当前实现仍以 `openai`、`openai_compatible`、`anthropic`、`gemini` 为基线；实现阶段必须先把固定 Provider 元数据升级为可测试的 Provider 注册表和模型目录，再扩展更多 Provider。

## UI 体验会议结论

Visual thesis:
这个界面应该像一个安静、精密、可信的 AI 控制台，通过清晰分区、稳定密度和系统级反馈，让创作者知道“现在能不能创作，哪里需要处理”。

Primary workspace:
设置页不做营销式 hero，也不做后台卡片墙。主工作区采用“状态总览条 + 左侧设置分区 + 中央编辑工作区 + 右侧诊断面板”的桌面设置模板。

Core interaction:
用户先看到全局健康，再选择要处理的设置域；修改内容进入草稿状态，底部或顶部出现稳定的“待保存变更”操作条；Provider 测试、错误和恢复动作就近出现。

Motion purpose:
动效只用于状态变化、分区切换、诊断结果出现和保存确认。第一阶段使用 Vue transition 与 CSS transition，不引入 GSAP、Three.js 或新动效库。

State coverage:
覆盖 loading、empty、ready、dirty、saving、checking、error、disabled。错误必须是中文、可恢复、靠近失败对象展示。

Implementation boundary:
页面重构必须拆分页面、组件、composable/store、types、styles 和测试，不再继续扩大单文件页面。

Performance/fallback:
宽屏保持三栏设置工作台；紧凑窗口中右侧诊断面板转为抽屉或顶部状态区。支持 `prefers-reduced-motion`。

Review verdict:
计划通过，但实现前必须先写 design spec，经确认后再进入代码改造。

## 用户视角分析

### 新用户：我能不能开始用 AI？

新用户需要在 10 秒内看到答案：

- Runtime 是否在线。
- 授权是否有效。
- 默认 OpenAI 是否配置。
- 脚本生成、脚本改写、分镜生成是否启用。
- 如果不能用，下一步是配置 API Key、检查 Base URL，还是处理 Runtime 目录。

设计响应：

- 顶部改为“系统就绪度”状态条，展示 Runtime、配置修订号、AI 可用能力数、Provider 凭据状态。
- 每个状态都可点击跳转到对应分区。
- 不展示假可用状态。未配置凭据时明确写“需要配置 API Key”。

### 日常创作者：我只想调整某个 AI 能力

日常用户最常改的是某个能力的模型、角色和提示词。当前卡片堆叠不利于横向比较。

设计响应：

- 中央主区使用“AI 能力矩阵”：每行一个能力，每列是启用、Provider、模型、角色、提示词摘要、健康状态。
- 点击某一行后，右侧诊断/详情区展示完整提示词编辑器、Provider 说明和最近测试结果。
- 行内只展示核心字段，长提示词不塞进卡片里。

### 系统维护者：我需要知道哪里坏了

维护者需要定位 Runtime、目录、日志、Provider、Base URL 和能力配置的故障。

设计响应：

- 右侧诊断面板固定显示当前选中对象的健康、来源、最后同步、失败原因和恢复动作。
- Provider 健康检查按钮与具体 Provider 行绑定，结果展示 `ready`、`missing_secret`、`misconfigured`、`unsupported`。
- 诊断信息不暴露 API Key 明文，不暴露 traceback。

### 紧凑窗口用户：我不想被长表单淹没

紧凑窗口下要保持任务路径清楚，不能把所有表单简单堆成一列。

设计响应：

- 左侧设置分区变成顶部 segmented rail。
- 右侧诊断面板收为抽屉。
- 能力矩阵降级为分组列表，但保持每项高度稳定，保存条固定在可见区域。

## 推荐信息架构

### 顶部状态总览条

展示：

- Runtime：在线 / 离线 / 读取中。
- 配置修订号：来自 `settings.revision`。
- AI 能力：已启用能力数 / 总能力数。
- Provider：已配置凭据数 / 总 Provider 数。
- 诊断：数据库、日志目录、运行模式。

动作：

- 刷新状态。
- 打开诊断详情。
- 有未保存变更时显示“保存变更 / 放弃变更”。

### 左侧设置分区

建议分区：

1. 总览
2. AI 能力
3. Provider 凭据
4. Runtime 与目录
5. 日志与诊断

规则：

- 分区切换不丢失草稿。
- 有未保存变更的分区显示点状标记。
- 有错误的分区显示错误状态标记。

### 中央编辑工作区

`AI 能力` 分区：

- 使用能力矩阵替代卡片网格。
- 支持按能力族筛选：脚本、分镜、媒体、资产。
- 每行展示启用、能力名称、Provider、模型、状态、最后操作。
- 点击行进入详情编辑。

`Provider 凭据` 分区：

- 每个 Provider 是一行或紧凑面板。
- 展示 label、provider id、baseUrl、secretSource、maskedSecret、supportsTextGeneration。
- 展示该 Provider 可用模型目录、能力标签和当前被哪些能力使用。
- 操作包括配置密钥、更新 Base URL、测试连接。
- 不展示明文 API Key；输入后只显示保存结果和 maskedSecret。

`Runtime 与目录` 分区：

- 编辑运行模式、工作区目录、缓存目录、导出目录、日志目录。
- 目录字段后续应接入 Tauri 目录选择器；本计划不新增后端接口。
- 保存前展示将要改变的路径列表，避免误写目录。

`日志与诊断` 分区：

- 编辑日志级别。
- 展示 `databasePath`、`logDir`、`mode`、`healthStatus`。
- 提供刷新，不直接打开本地日志文件，除非另有桌面权限计划。

### 右侧诊断面板

展示当前上下文：

- 选中能力：完整 prompt、provider、model、启用状态、风险提示。
- 选中 Provider：凭据来源、Base URL、文本生成支持、健康检查结果。
- 选中目录：路径、用途、保存影响。
- 全局诊断：Runtime、数据库、日志、修订号。

## 交互规划

### 1. 页面进入

1. 页面进入后由 `config-bus` 并发请求 health/config/diagnostics。
2. `ai-capability` 请求 AI 能力配置。
3. 顶部状态条先进入 skeleton；任一请求失败时，失败分区显示中文错误与重试入口。
4. 成功后默认落在“总览”，并突出第一个需要处理的问题。

### 2. 修改配置

1. 用户修改任意字段后进入 dirty 状态。
2. 保存条显示改动数量和分区名称。
3. 保存时禁用相关字段，保持布局尺寸不变。
4. 成功后刷新 health/diagnostics 或 AI capabilities。
5. 失败时保留用户草稿，错误靠近失败分区展示。

### 3. Provider 凭据

1. 用户点击“配置密钥”打开轻量内联编辑区或抽屉。
2. 输入 API Key 和可选 Base URL。
3. 调用 `PUT /api/settings/ai-capabilities/providers/{provider_id}/secret`。
4. 成功后只展示 maskedSecret 和 secretSource。
5. 用户点击“测试连接”调用 health-check。
6. 结果就地展示，不用弹窗。

### 4. AI 能力编辑

1. 用户选中能力行。
2. 右侧打开能力详情。
3. Provider/model/role 可以内联编辑。
4. systemPrompt 和 userPromptTemplate 使用双编辑区，保留模板变量提示。
5. 保存时必须提交完整 7 项能力列表，因为当前后端要求能力集合完整。

### 5. 错误恢复

错误类型与恢复动作：

- Runtime 离线：重试读取，提示检查 Runtime 启动。
- 配置保存失败：保留草稿，重试保存。
- AI 能力配置不完整：提示刷新后重试，不允许提交部分能力列表。
- Provider 缺少密钥：跳到 Provider 凭据分区。
- OpenAI-compatible 缺少 Base URL：定位到 Base URL 字段。
- Provider 不支持文本生成：禁用测试成功状态，说明本阶段尚未接入文本生成。

## Motion 与视觉规则

- 不使用全屏 hero。
- 不使用普通后台 KPI 卡片填充界面。
- 不使用装饰性渐变球、bokeh 或单一紫蓝调。
- 使用 `role.system` 方向的系统强调色，但不让页面变成单色主题。
- 卡片只用于可选项、Provider 行或详情块；页面结构优先使用分区、表格、列表和诊断面板。
- 分区切换使用 160-220ms 淡入和轻微位移。
- 诊断面板进入使用 220ms transition。
- 保存成功用短暂状态确认，不用阻断式弹窗。
- `prefers-reduced-motion: reduce` 时关闭位移和重复动画。

## Runtime 契约会议结论

API boundary:
本模块已完成的后端接口集中在 `/api/settings` 与 `/api/settings/ai-capabilities`。本次只梳理并登记接口，不新增接口。下一阶段必须把固定 Provider 元数据升级为 Provider 注册表与模型目录接口，避免页面只能围绕单个 AI 配置工作。

Data contract:
配置总线返回 `AppSettings`，AI 能力返回 `AICapabilitySettings`。Provider secret 只返回脱敏状态，不返回明文密钥。目标数据契约需要新增 Provider catalog、model catalog、capability support matrix、provider feature flags 和 model availability 状态。

Task/event flow:
当前模块没有 TaskBus 长任务。Provider health-check 是同步 HTTP 检查，不通过 WebSocket。

Frontend integration:
前端必须通过 `runtime-client.ts`，再由 `config-bus` 与 `ai-capability` stores 消费。页面不得直接 fetch。

Error/logging behavior:
系统配置更新会写 `settings.updated` audit log。Provider secret 目前走 SecretStore；后续如增加真实 Provider 调用日志，应另开 AI provider observability 计划。

Verification:
已有 contracts/runtime/page 测试覆盖基础字段、持久化、secret 脱敏和页面保存。实现 UI 重构时必须扩展页面状态、Provider secret UI、health-check UI、dirty state 和紧凑布局测试。

Blockers:
全局 validation error 当前测试期望 `Request validation failed`，不是中文用户提示。实现时需决定是后端统一改中文，还是前端先映射为中文提示；最终目标必须满足中文可见错误。

## 文件所有权规划

### 前端 UI

- `apps/desktop/src/pages/settings/AISystemSettingsPage.vue`：路由级页面、分区切换、store 编排。
- `apps/desktop/src/modules/settings/components/SettingsStatusDock.vue`：顶部状态总览条。
- `apps/desktop/src/modules/settings/components/SettingsSectionRail.vue`：设置分区导航。
- `apps/desktop/src/modules/settings/components/AICapabilityMatrix.vue`：AI 能力矩阵。
- `apps/desktop/src/modules/settings/components/AICapabilityInspector.vue`：能力详情和 prompt 编辑。
- `apps/desktop/src/modules/settings/components/ProviderSecretPanel.vue`：Provider 凭据和健康检查。
- `apps/desktop/src/modules/settings/components/RuntimePathPanel.vue`：Runtime 与目录编辑。
- `apps/desktop/src/modules/settings/components/SettingsDiagnosticsPanel.vue`：系统诊断详情。
- `apps/desktop/src/modules/settings/types.ts`：页面内部视图模型和分区状态。
- `apps/desktop/src/modules/settings/useSettingsDraft.ts`：配置草稿、脏状态和变更摘要。
- `apps/desktop/src/styles/settings.css`：模块样式，使用现有 CSS variables。

### 前端数据层

- `apps/desktop/src/stores/config-bus.ts`：保留 health/config/diagnostics 加载与保存；必要时增加 refresh/save 状态细分。
- `apps/desktop/src/stores/ai-capability.ts`：增加 Provider secret 和 health-check actions。
- `apps/desktop/src/app/runtime-client.ts`：已有 Provider secret/health-check 函数，重构时补返回类型和测试。
- `apps/desktop/src/types/runtime.ts`：确认 settings 与 AI capability 类型和文档一致。

### 后端与文档

- `docs/RUNTIME-API-CALLS.md`：已登记 M16 接口。
- `apps/py-runtime/src/api/routes/settings.py`：当前无需改动。
- `apps/py-runtime/src/api/routes/ai_capabilities.py`：当前无需改动。
- `apps/py-runtime/src/services/settings_service.py`：当前无需改动。
- `apps/py-runtime/src/services/ai_capability_service.py`：当前无需改动；后续如补 provider id 校验或中文 validation 错误，必须配套测试。

### 测试

- `apps/desktop/tests/ai-system-settings.spec.ts`：扩展页面状态、分区切换、保存条、Provider secret、health-check、错误态。
- 新增 `apps/desktop/tests/runtime-client-settings.spec.ts`：覆盖 settings 与 ai-capabilities client 方法。
- `tests/contracts/test_settings_config_contract.py`：如字段或错误语义变化则更新。
- `tests/contracts/test_ai_capabilities_contract.py`：如 health status 或 Provider 状态字段变化则更新。
- `tests/runtime/test_settings_config.py`：如保存行为变化则更新。
- `tests/runtime/test_ai_capabilities.py`：如 provider 校验、secret 或 health 逻辑变化则更新。

## 开发顺序

### 阶段 0：设计确认

- 用户确认本计划的 UI 方向和接口文档。
- 生成 `docs/superpowers/specs/2026-04-16-ai-system-settings-ui-runtime-design.md`。
- spec 明确组件结构、状态矩阵、字段映射、测试验收和不可做范围。

### 阶段 1：接口与测试基线

- 确认 `docs/RUNTIME-API-CALLS.md` 与当前 route/client/type/test 一致。
- 补前端 runtime-client settings 测试。
- 补页面错误态与能力配置保存测试缺口。

### 阶段 1.5：多 Provider / 多模型契约设计

- 将当前 `_provider_metadata()` 固定字典升级为 Provider 注册表设计。
- 定义 Provider catalog DTO：Provider ID、显示名、类型、Base URL 策略、密钥字段、支持能力、是否支持文本/多模态/语音/视频。
- 定义 Model catalog DTO：模型 ID、显示名、所属 Provider、能力类型、上下文长度、输入输出模态、默认用途、是否可选。
- 定义能力支持矩阵：每个 `capabilityId` 可选择哪些 Provider 和模型。
- Provider secret 接口必须支持不同 Provider 的密钥字段差异，但响应仍只返回脱敏状态。
- OpenAI-compatible、OpenRouter、本地 Ollama/LM Studio/vLLM 必须按可配置 Base URL 处理，不能写死。
- 写 contract tests，证明未知 Provider 不会 500，而是返回中文错误信封。

### 阶段 2：页面拆分

- 把当前单页表单拆为页面 shell、状态总览、分区导航、AI 能力矩阵、Provider 面板、Runtime 目录面板、诊断面板。
- 页面只负责组合和调度。
- store/composable 负责草稿与保存。

### 阶段 3：Provider 凭据体验

- 接入 `updateAIProviderSecret()`。
- 接入 `checkAIProviderHealth()`。
- 在 UI 中展示 maskedSecret、secretSource、baseUrl、supportsTextGeneration。
- 不展示明文 API Key。

### 阶段 4：AI 能力矩阵体验

- 将 7 个能力从卡片改为矩阵。
- 右侧详情编辑提示词。
- 保存时提交完整 capabilities 列表。
- 对不完整列表或 Runtime 错误给出中文恢复提示。

### 阶段 5：系统设置体验

- Runtime、路径、日志改为分区编辑。
- 保存前显示变更摘要。
- 保存成功后刷新 health/diagnostics。
- 紧凑窗口下诊断面板转抽屉。

### 阶段 6：验收

- 前端页面测试覆盖 loading、ready、dirty、saving、error、disabled。
- 后端 contract/runtime 测试保持通过。
- 做宽屏和紧凑窗口截图检查。
- Light/Dark 至少各检查一次。
- 使用 `tkops-acceptance-gate` 做 UI/runtime 验收。

## 非目标

- 不在本阶段新增真实 OpenAI 调用。
- 不在本阶段实现 TTS Provider、字幕对齐 Provider 或视频生成 Provider。
- 不把 AI 与系统设置设计成单一 OpenAI 配置页。
- 不在页面里硬编码“主流模型”列表；模型目录必须来自 Runtime。
- 不把设置页做成营销页或仪表盘。
- 不加入假指标、假健康状态、假 AI 结果。
- 不绕过 Runtime client 直接请求后端。
- 不在 UI 中展示 API Key 明文。
- 不直接复制 React Bits 组件；可以借鉴动效节奏并用 Vue/CSS 重写。
- 不新增 WebGL、Three.js、GSAP 或重型动效依赖。

## 验证矩阵

文档阶段已验证：

- `docs/RUNTIME-API-CALLS.md` 包含本模块接口登记。
- 本计划只引用当前存在的 route、client、store、schema 和测试文件。

实现阶段必须运行：

```powershell
npm --prefix apps/desktop run test -- ai-system-settings
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
venv\Scripts\python.exe -m pytest tests\contracts\test_settings_config_contract.py tests\contracts\test_ai_capabilities_contract.py -q
venv\Scripts\python.exe -m pytest tests\runtime\test_settings_config.py tests\runtime\test_ai_capabilities.py -q
git diff --check
```

UI 验收还需要：

- 宽屏截图：状态总览 + 分区 + 中央工作区 + 右侧诊断。
- 紧凑窗口截图：分区导航压缩、诊断抽屉、能力列表可读。
- Provider 未配置、已配置、missing_secret、misconfigured、unsupported、ready 状态证据。
- 保存成功、保存失败、保留草稿、放弃变更证据。
- Light/Dark 主题截图或人工检查记录。

## 阻断条件

- 页面仍然只是普通卡片表单堆叠。
- Provider secret 和 health-check client 存在但没有 UI 入口。
- 错误只在控制台输出或只显示英文错误。
- 保存失败后丢失用户已编辑内容。
- 能力配置提交不完整导致后端 400，却没有中文恢复提示。
- 紧凑窗口下需要大量滚动才能完成常见任务。
- 前端页面直接 fetch Runtime。
- 文档、类型、Runtime client、store、测试任一项变更后未同步 `docs/RUNTIME-API-CALLS.md`。
