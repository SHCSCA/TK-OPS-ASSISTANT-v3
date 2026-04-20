# TK-OPS V2 后端需求文档

## 1. 文档定位

本文用于把 V2 产品问题拆成后端可执行需求，重点聚焦契约、任务状态、广播、保存结果、错误可追踪性和真实数据约束。  
本文不直接替代 `docs/RUNTIME-API-CALLS.md` 的字段真源，但会列出后续必须同步到 API 真源的接口影响清单。

## 2. 跨页面后端 V2 要求

### 2.1 阻断态必须可转成中文 UI 提示

所有阻断态接口都必须返回：

- 当前不能继续的原因
- 受影响对象
- 下一步建议
- 用户可执行动作

禁止只返回“not ready”“unavailable”“invalid config”这类前端无法直接使用的结果。

### 2.2 所有长任务必须具备统一任务状态

长任务至少具备：

- 已开始
- 处理中
- 成功
- 失败
- 可重试
- 已取消

并且要返回任务归属、最近更新时间、失败原因和下一步动作建议。

### 2.3 关键写操作必须返回保存确认

所有关键数据写入接口都必须返回：

- 保存结果
- 版本号或修订号
- 更新时间
- 归属项目或对象
- 相关任务编号（如有）

### 2.4 页面状态变化必须触发刷新与广播

- 写入成功后必须能触发缓存失效。
- 长任务状态变化必须进入统一广播通道。
- 前端需要感知的状态变化必须支持 WebSocket 或等价广播。

### 2.5 统一错误码、错误信封与日志字段

- 返回统一 JSON 信封。
- 错误码必须稳定、可文档化、可测试。
- 日志至少包含：时间、模块、对象 ID、任务 ID、错误码、错误摘要、操作结果。

## 3. 逐页后端需求

### 3.1 首启与许可证向导

- 需要补齐或调整的接口 / 字段 / 错误码：许可校验明细、目录初始化明细、Runtime 诊断分项结果。
- 任务状态和广播要求：检测类任务要支持开始、处理中、失败、成功。
- 配置依赖与鉴权依赖：依赖配置总线中的许可与目录配置。
- 数据真实性要求：所有校验项必须基于真实本地环境。
- 验收标准：前端可逐项显示失败原因与修复动作。

### 3.2 创作总览

- 需要补齐或调整的接口 / 字段 / 错误码：最近项目、最近任务、待处理事项、风险摘要。
- 任务状态和广播要求：最近任务状态变化能实时刷新总览。
- 配置依赖与鉴权依赖：依赖当前项目上下文。
- 数据真实性要求：摘要必须来自真实任务和真实项目。
- 验收标准：总览接口能直接支持”继续当前任务”。

#### 3.2.1 实测缺陷（后端侧）

- **Bug B-01 项目删除接口缺失**：`api/routes/dashboard.py` 只有 `GET/POST/PUT`，没有 `DELETE` 路由；前端被迫用前端过滤绕过，所以删除操作不落库（详见前端 Bug F-01）。
- 修复方向：
  - 新增 `DELETE /api/dashboard/projects/{project_id}`，调用 `ProjectRepository.delete(project_id)`。
  - 删除策略采用软删除：`projects` 表增加 `deleted_at: datetime | None`，列表接口过滤 `deleted_at IS NULL`；保留软删除是为了支持关联资产 / 任务 / 时间线的回滚窗口。
  - 删除时校验：若有未完成任务（渲染 / 发布 / 自动化）则返回 `error_code = project.delete_blocked` + 阻断原因中文（”项目存在 N 个未完成任务，无法删除”）+ 可执行动作（”先取消未完成任务”）。
  - 若项目为 `current_project`，删除后自动清空 `current_project` 指针。
  - 广播：通过 TaskBus 发送 `project.deleted` 事件，携带 `project_id` 与 `deleted_at`，让打开中的其他页面自动刷新。
- 契约回流：新增 `error_code` `project.delete_blocked`、响应字段 `deleted_at`；必须同步写入 `docs/RUNTIME-API-CALLS.md` 第 3 节。
- 验收：前端调用删除后列表不再出现；重启 Runtime 后仍然不出现；有未完成任务时返回可直接展示的中文阻断。

### 3.3 脚本与选题中心

- 需要补齐或调整的接口 / 字段 / 错误码：脚本版本号、保存结果、生成任务状态、改写失败原因。
- 任务状态和广播要求：生成任务和保存动作都要有可追踪状态。
- 配置依赖与鉴权依赖：依赖脚本 Provider 与当前项目。
- 数据真实性要求：版本信息与内容快照必须真实可回溯。
- 验收标准：前端能判断当前脚本是否已保存及属于哪个版本。

### 3.4 分镜规划中心

- 需要补齐或调整的接口 / 字段 / 错误码：来源脚本版本、分镜同步状态、冲突摘要。
- 任务状态和广播要求：同步任务要支持处理中、冲突、失败、成功。
- 配置依赖与鉴权依赖：依赖脚本上下文与项目上下文。
- 数据真实性要求：分镜来源必须能回溯到真实脚本版本。
- 验收标准：前端能知道分镜是否落后于脚本。

### 3.5 AI 剪辑工作台

- 需要补齐或调整的接口 / 字段 / 错误码：时间线版本、素材引用状态、关键任务状态、保存确认。
- 任务状态和广播要求：时间线相关任务必须实时广播。
- 配置依赖与鉴权依赖：依赖项目、资产、时间线、Provider。
- 数据真实性要求：引用素材、任务结果和时间线状态都必须真实。
- 验收标准：前端可稳定展示“当前项目 + 当前时间线 + 当前任务”。

### 3.6 视频拆解中心

- 需要补齐或调整的接口 / 字段 / 错误码：上传、解析、转写、结构化四段状态与失败原因。
- 任务状态和广播要求：支持阶段级广播、取消与重试。
- 配置依赖与鉴权依赖：依赖导入源和解析配置。
- 数据真实性要求：阶段状态必须来自真实任务执行。
- 验收标准：前端能知道当前卡在拆解哪一段。

#### 3.6.1 实测缺陷（后端侧）

- **Bug B-06 FFprobe 不可用导致降级至"只记录路径 / 大小"**：`services/ffprobe.py:42` 当 PATH 中找不到 `ffprobe` 即走降级分支，`runtime_tasks/video_tasks.py:53` 写入中文降级原因；用户现象就是导入视频后元数据大面积缺失。
- 修复方向（分两层）：
  1. **打包层**：Tauri 构建脚本把 `ffprobe.exe` 作为 sidecar 资源嵌入 `apps/desktop/src-tauri/bin/ffprobe.exe`；Runtime 启动时优先使用 sidecar 路径（通过配置总线 `paths.ffprobeBinary` 暴露），其次回落到 PATH，最后才走降级；所有失败都写 `error_code` 与 `last_check_at`。
  2. **诊断层**：新增 `GET /api/settings/diagnostics/media`，返回 `{ ffprobe: { status: 'ready'|'missing'|'incompatible', path, version, last_check_at } }`；Bootstrap 启动阶段触发一次探测并写入首启诊断分项；失败时返回结构化 `error_code = media.ffprobe_unavailable` + 可执行动作"下载 FFmpeg 并重新打开"（含文档链接占位）。
  3. **任务层**：`video_tasks` 遇到 `media.ffprobe_unavailable` 不再静默降级，改为任务状态 `failed_degraded`，携带 `error_code`、`error_message`、`can_retry_after_install=True`；TaskBus 广播让前端可以在视频拆解页展示醒目警示条（前端 Bug F-08）。
- 契约回流：RUNTIME-API-CALLS §17 / §20 需补 `/api/settings/diagnostics/media`；新增 `error_code` `media.ffprobe_unavailable` / `media.ffprobe_incompatible`；`BACKEND-REQUIREMENTS-2026-04-17.md` 的"首启诊断分项"条目需要从 0 更新为进入中。
- 验收：打包版自带 FFprobe 的机器上导入视频能拿到 duration / resolution / bitrate；未安装时视频拆解 / 首启向导 / AI 与系统设置三处都能看到一致的 FFprobe 状态与修复动作。

### 3.7 配音中心

- 需要补齐或调整的接口 / 字段 / 错误码：音轨版本、音色配置、试听资源状态、生成任务状态。
- 任务状态和广播要求：TTS 任务需要完整状态链路。
- 配置依赖与鉴权依赖：依赖 TTS Provider、项目文本、配置总线。
- 数据真实性要求：音轨必须能回溯到真实文本版本与参数。
- 验收标准：前端能展示音轨的来源、状态和失败原因。

### 3.8 字幕对齐中心

- 需要补齐或调整的接口 / 字段 / 错误码：来源音轨版本、对齐状态、差异摘要、失败原因。
- 任务状态和广播要求：对齐任务支持处理中、部分成功、失败、重试。
- 配置依赖与鉴权依赖：依赖字幕策略与音轨上下文。
- 数据真实性要求：对齐结果与差异必须来自真实时间码数据。
- 验收标准：前端能判断是重跑对齐还是回到音轨修复。

### 3.9 资产中心

- 需要补齐或调整的接口 / 字段 / 错误码：资产来源、可用状态、引用计数、失效原因。
- 任务状态和广播要求：资产生成或分析状态需要广播。
- 配置依赖与鉴权依赖：依赖项目资产上下文。
- 数据真实性要求：引用关系与来源链路必须真实存在。
- 验收标准：前端能判断资产是否适合当前项目使用。

### 3.10 账号管理

- 需要补齐或调整的接口 / 字段 / 错误码：账号可发布状态、最近校验时间、失效原因、建议动作。
- 任务状态和广播要求：校验任务变更需要实时刷新。
- 配置依赖与鉴权依赖：依赖账号鉴权与发布上下文。
- 数据真实性要求：账号状态必须来自真实校验。
- 验收标准：前端能明确标记当前可发布账号。

### 3.11 设备与工作区管理

- 需要补齐或调整的接口 / 字段 / 错误码：工作区状态、执行环境状态、绑定关系、健康检查结果。
- 任务状态和广播要求：健康检查要有任务状态与最近结果。
- 配置依赖与鉴权依赖：依赖工作区与绑定配置。
- 数据真实性要求：所有设备对象都必须是真实对象。
- 验收标准：前端能确认哪个真实环境能执行任务。

#### 3.11.1 实测缺陷（后端侧）

- **Bug B-02 浏览器实例对象模型缺失**：当前 `device_workspaces.py` 只管理本地目录型工作区，没有浏览器实例对象；前端 Bug F-02 所述空态就是因为后端根本没这个模型。
- 修复方向（按 S 档立计划，不抢在本轮修复内强行堆代码）：
  - 新增 `browser_instances` 表，字段至少包含：`id`、`workspace_id`（外键）、`engine`（`chromium` / `firefox` / `webkit`）、`profile_dir`、`status`（`idle` / `running` / `error` / `binding`）、`last_check_at`、`error_code`、`error_message`、`created_at`、`updated_at`。
  - 新增 Router `browser_instances.py`：`GET/POST/PATCH/DELETE /api/devices/workspaces/{workspace_id}/browser-instances`，另加 `POST /{id}/start`、`POST /{id}/stop`、`POST /{id}/health-check`。
  - 所有对象必须指向真实 profile 目录与可启动引擎，禁止伪造在线率。
  - 健康检查走 TaskBus 广播；失败返回结构化 `error_code`（`browser.engine_missing` / `browser.profile_locked` / `browser.port_in_use`）+ 中文原因 + 下一步动作。
- 契约回流：新增 6 个 Router 路由 + 1 张表 + 3 个 `error_code`，需在 RUNTIME-API-CALLS §12 新增一节并更新 `BACKEND-REQUIREMENTS-2026-04-17.md` M11 缺口矩阵。
- 验收：前端列表能显示真实浏览器实例；启动 / 停止 / 健康检查都能拿到真实状态；任一阻断都能转成中文提示而不是空态。

### 3.12 自动化执行中心

- 需要补齐或调整的接口 / 字段 / 错误码：任务来源、队列位置、最近执行结果、失败可重试原因。
- 任务状态和广播要求：队列状态、执行状态、回执结果需要统一广播。
- 配置依赖与鉴权依赖：依赖自动化配置和执行绑定。
- 数据真实性要求：状态必须来自真实任务实例。
- 验收标准：前端能追踪一个任务的全生命周期。

### 3.13 发布中心

- 需要补齐或调整的接口 / 字段 / 错误码：预检结果、提交结果、回执状态、失败分段原因。
- 任务状态和广播要求：预检、提交、回执都要能广播。
- 配置依赖与鉴权依赖：依赖账号、设备、发布配置。
- 数据真实性要求：回执和发布结果必须来自真实发布链路。
- 验收标准：前端可准确展示发布卡点与恢复动作。

### 3.14 渲染与导出中心

- 需要补齐或调整的接口 / 字段 / 错误码：渲染阶段、输出路径、文件确认状态、失败原因。
- 任务状态和广播要求：渲染与导出状态要分段广播。
- 配置依赖与鉴权依赖：依赖渲染配置、项目上下文、文件系统。
- 数据真实性要求：输出路径和文件存在状态必须真实可验证。
- 验收标准：前端可确认导出文件是否真实产出。

### 3.15 复盘与优化中心

- 需要补齐或调整的接口 / 字段 / 错误码：复盘摘要、问题分类、回流目标、执行结果。
- 任务状态和广播要求：复盘生成与回流动作状态要可追踪。
- 配置依赖与鉴权依赖：依赖项目历史、任务历史、发布结果。
- 数据真实性要求：建议必须基于真实任务和真实结果。
- 验收标准：前端能把复盘建议落到具体回流动作。

### 3.16 AI 与系统设置

- 需要补齐或调整的接口 / 字段 / 错误码：Provider 就绪状态、测试结果、配置版本、作用范围、诊断摘要。
- 任务状态和广播要求：测试任务和配置刷新必须有状态广播。
- 配置依赖与鉴权依赖：依赖配置总线与 Provider 鉴权。
- 数据真实性要求：配置生效状态必须来自真实配置与真实探测。
- 验收标准：前端能确认某个 Provider 是否已真实可用。

#### 3.16.1 实测缺陷（后端侧）

- **Bug B-03 Provider 启动时无静默自检 / 健康聚合接口**：当前 `ai-providers/test` 只是单 Provider 单次手动测试，缺少一个"启动时一口气探测所有已启用 Provider + 持久化最近一次结果"的聚合通道，导致前端 Bug F-05 无法实现徽标。
- 修复方向：
  - 新增 `GET /api/ai-providers/health`，返回 `{ providers: [{ id, readiness: 'ready'|'degraded'|'unavailable', last_checked_at, latency_ms, error_code, error_message }] }`，结果来自后台最近一次探测。
  - 新增 `POST /api/ai-providers/health/refresh`，触发一次全 Provider 并行探测（并发上限 3，单 Provider 超时 5s，指数退避最多 2 次），写回数据库并通过 TaskBus 广播 `provider.health.updated`。
  - Bootstrap 启动阶段自动触发一次 `refresh`（标记为 `silent=true`，失败不阻断桌面启动，仅写日志）。
  - 探测结果有独立表 `ai_provider_health`，字段：`provider_id`、`status`、`latency_ms`、`error_code`、`checked_at`，保留最近 10 条用于趋势。
- **Bug B-04 自定义 model_id 无能力类型持久化**：schema 已有 `capabilityTypes`，但 Provider 模型保存路径没有强制要求客户端传 `capability_kinds`，也没有按此字段路由能力矩阵；自定义 model_id 因此无法被视觉 / 视频 / TTS 场景正确识别。
- 修复方向：
  - Provider 模型写入接口（`POST /api/ai-providers/{id}/models` / `PATCH .../models/{model_id}`）要求 `capability_kinds: list[str]` 必填，允许取值限定为 `text_generation` / `vision` / `video` / `tts` / `asset_analysis`，至少一项。
  - `ai_capability_service.get_capability_support_matrix` 改为从 `capability_kinds` 直接路由，不再依赖内置元数据猜测。
  - 历史无标注模型做一次迁移：已知 GPT-5 / GPT-5-mini 等按内置元数据回填；无法识别的标为 `text_generation` 并在 UI 上给"请确认能力类型"黄色提示。
- **Bug B-05 同一 Provider 下 model_id 可重复保存**：Repository 层没有 `(provider_id, model_id)` 唯一约束，前端重复粘贴会入库两条。
- 修复方向：
  - Alembic 迁移给 `ai_provider_models` 增加 `UniqueConstraint('provider_id', 'model_id')`。
  - Repository 的 `save_model` 改为 upsert：命中唯一键时按字段覆盖并返回 `updated_at`；返回 payload 增加 `was_upsert: bool` 供前端决定提示语。
  - 并发写入的最后一次保存胜出，冲突时返回 `error_code = provider.model.duplicate_model_id` + 中文原因。
- 契约回流：
  - RUNTIME-API-CALLS §17 新增 `/api/ai-providers/health` / `/health/refresh` 两节。
  - RUNTIME-API-CALLS §17 Provider 模型接口追加 `capability_kinds` 必填说明与 `was_upsert` 字段。
  - 新增 `error_code`：`provider.health.refresh_failed` / `provider.model.capability_required` / `provider.model.duplicate_model_id`。
- 验收：
  - Bootstrap 完成后 `config-bus` 能拿到所有已启用 Provider 的就绪状态。
  - 新建模型未填 `capability_kinds` 时返回 422 + 中文提示。
  - 同一 `(provider_id, model_id)` 重复保存时返回 upsert 成功或显式冲突，不会出现两条记录。

## 4. 后端共性专题

### 4.1 项目选择上下文

- 所有核心页面接口都应能识别当前项目上下文。
- 未提供项目上下文时，返回可直接转成引导态的错误码与说明。

### 4.2 Provider 就绪状态

- 所有依赖 AI Provider 的页面都需要统一的就绪状态接口。
- 返回内容应包含是否可用、缺失项、测试结果、下一步动作。

### 4.3 任务可追踪性

- 所有长任务必须具备任务 ID、对象 ID、来源页面、来源项目、最近更新时间。
- 所有状态变化必须能通过统一广播总线送达前端。

### 4.4 保存成功可确认

- 关键写操作不能只返回 200。
- 必须返回版本号、更新时间、对象摘要和最近写入结果。

### 4.5 失败后重试路径

- 所有可重试失败都需要明确重试条件、重试入口和重试后可能影响的对象。
- 不可重试失败也要明确下一步去哪里修复。

## 5. 后续需同步到 API 真源的接口影响清单

1. 项目上下文与最近任务摘要接口
2. 首启许可 / Runtime 诊断分项结果接口
3. 脚本、分镜、时间线、音轨、字幕的版本与保存确认字段
4. 所有长任务统一状态字段与广播事件
5. Provider 就绪状态、测试结果与配置版本接口
6. 渲染、发布、自动化的回执与失败原因字段

## 6. 后端验收标准

1. 所有核心页面都能拿到可直接转成中文 UI 提示的阻断原因与下一步。
2. 所有长任务都具备统一状态链、任务归属与失败恢复信息。
3. 所有关键写操作都返回保存确认、版本号与更新时间。
4. 所有关键状态变化都支持刷新和广播。

## 7. 实测缺陷索引（2026-04-20）

| 编号 | 模块 | 现象摘要 | 档位 | 与前端关联 |
| --- | --- | --- | --- | --- |
| B-01 | Dashboard | 项目删除接口缺失，前端被迫假删 | L | 对应 F-01 |
| B-02 | Devices | 浏览器实例对象模型缺失 | S | 对应 F-02 |
| B-03 | AI Providers | 启动时无静默自检 / 健康聚合接口 | M | 对应 F-05 |
| B-04 | AI Providers | 自定义 model_id 无能力类型持久化 | M | 对应 F-06 |
| B-05 | AI Providers | 同一 Provider 下 model_id 可重复保存 | L | 对应 F-07 |
| B-06 | Video Decon / Settings | FFprobe 不可用仅降级无诊断 | M | 对应 F-08 |

档位解释：L = 单点修复直接开工；M = 跨 Runtime + 前端协作按 V2 单页推进；S = 需要新模型 / 新链路按 V2 S 档立计划。
