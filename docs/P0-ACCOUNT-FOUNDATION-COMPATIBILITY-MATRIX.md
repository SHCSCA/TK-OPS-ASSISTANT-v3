# P0 账号基础兼容矩阵

> 状态：P0-A 至 P0-C 兼容边界真源；阶段验收证据见 `docs/PROJECT-STATUS.md`  
> 更新日期：2026-07-26  
> 适用范围：从旧 Project / Timeline 实现迁移到账号工作区 P0 主线  
> 详细契约：`docs/superpowers/specs/2026-07-19-prototype-to-production-p0-account-foundation-design.md`

## 1. 使用规则

本文件只记录迁移兼容边界，不定义新产品需求。

- 新产品范围以 `docs/PRD.md` 为准。
- 新页面布局以 `docs/UI-DESIGN-PRD.md` 为准。
- 新目录、服务与模型落点以 `docs/ARCHITECTURE-BOOTSTRAP.md` 为准。
- P0-A 不迁移完整创作数据，不删除旧业务表，不切换 Desktop 路由。
- 兼容入口只允许调用新服务并转换 DTO；禁止双写、复制事务或保留第二套状态机。
- 本矩阵与 legacy 索引可以记录旧 Route ID、URL 和 API 作为迁移证据；新产品链接和新增业务代码不得生成这些旧入口。

状态说明：

| 状态 | 含义 |
| --- | --- |
| `P0-A verified` | 数据库结构、启动接管和 P0-A 阶段验证已经通过 |
| `P0-C verified` | 账号纵向链代码、兼容边界和 P0-C 阶段验证已经通过 |
| `legacy active` | 当前旧 Desktop / API 仍在使用 |
| `planned` | 已有批准规格，等待对应阶段实现 |
| `blocked` | 在目标阶段前禁止启用或宣称可用 |
| `retire later` | 当前保留，退出条件满足后另立删除计划 |

## 2. Desktop Route / URL 兼容矩阵

| 旧 Route ID / URL | 新 Route ID / URL | P0-A 行为 | 正式兼容行为 | 退出阶段 |
| --- | --- | --- | --- | --- |
| `setup_license_wizard` `/setup/license` | `setup_license_wizard` `/setup/license` | legacy active | 保留 URL，页面成为唯一许可证与初始化表单 | P0-D |
| `creator_dashboard` `/dashboard` | `account_workspace_home` `/workspace` | legacy active | `replace` 重定向 | P0-F |
| `script_topic_center` `/scripts/topics` | `account_script_topic` `/scripts` | legacy active | `replace` 重定向到真实 P1 前置状态，不读取旧 Project | P0-F |
| `storyboard_planning_center` `/storyboards/planning` | `account_storyboard_planning` `/storyboards` | legacy active | `replace` 重定向到真实 P1 前置状态 | P0-F |
| `video_deconstruction_center` `/video/deconstruction` | `account_video_deconstruction` `/video-deconstruction` | legacy active | `replace` 重定向到真实 P1 前置状态 | P0-F |
| `asset_library` `/assets/library` | `account_content_library` `/content-library` | legacy active | 显示迁移说明，不读取未迁移旧资产 | P0-F |
| `publishing_center` `/publishing/center` | `account_publishing` `/publishing` | legacy active | 显示真实连接 / 执行绑定预检 | P0-F |
| `review_optimization_center` `/review/optimization` | `account_review` `/review` | legacy active | 显示等待真实回执状态 | P0-F |
| `account_management` `/accounts` | `account_management` `/settings/accounts` | legacy active | `replace` 重定向 | P0-F |
| `device_workspace_management` `/devices/workspaces` | `ai_system_settings` `/settings/ai-system?section=runtime` | legacy active | 打开 Runtime 与工作区分区 | P0-F |
| `ai_system_settings` `/settings/ai-system` | `ai_system_settings` `/settings/ai-system` | legacy active | 保留 URL，替换内部配置模型 | P0-E |
| `ai_editing_workspace` `/workspace/editing` | `account_batch_production` `/production/batches?legacySource=editing-workspace` | legacy active | 只显示迁移说明，禁止打开旧工作台 | P0-F |
| `voice_studio` `/voice/studio` | `account_batch_production` `/production/batches?legacyStage=voice` | legacy active | 显示配音已合并到批次节点 | P0-F |
| `subtitle_alignment_center` `/subtitles/alignment` | `account_batch_production` `/production/batches?legacyStage=subtitle` | legacy active | 显示字幕已合并到批次节点 | P0-F |
| `render_export_center` `/renders/export` | `account_batch_production` `/production/batches?legacyStage=render` | legacy active | 显示渲染已合并到批次节点 | P0-F |
| `automation_console` `/automation/console` | `account_workspace_home` `/workspace?legacyRoute=automation-console` | legacy active | 显示自动化已合并到工作流 | P0-F |

旧 URL 重定向只保留一个发布窗口。P0-F 完成后，旧业务页面不可由新导航、收藏入口或内部链接继续访问。

## 3. HTTP / WebSocket 兼容矩阵

| 当前 legacy 接口组 | 目标接口 | P0-A 状态 | 迁移规则 | 退出阶段 |
| --- | --- | --- | --- | --- |
| `/api/bootstrap/*` | `/api/v1/bootstrap/*` | legacy active | P0-B 建立 Runtime 会话、Host / Origin 和许可证门；旧接口调用同一服务 | P0-B |
| `/api/license/*` | `/api/v1/bootstrap/license*` | legacy active | 激活与状态并入 Bootstrap；不得保留第二套许可证状态 | P0-B |
| `/api/settings/health` | `/api/v1/bootstrap/status`、`/api/v1/bootstrap/self-checks` | legacy active | 启动就绪和数据库预检进入 status；可执行 Runtime / 媒体自检由 self-checks 受理 | P0-B |
| `GET/PUT /api/settings/config` | `/api/v1/system/config` | legacy active | P0-B 只薄转发通用系统配置；AI 配置必须进入 P0-E 的独立版本链 | P0-B/E |
| `/api/settings/diagnostics`、`/api/settings/diagnostics/media` | `/api/v1/system/diagnostics` | legacy active | 媒体诊断成为同一诊断响应的 section / 摘要；禁止发明第二个子端点或第二套 Runtime 状态 | P0-B |
| `/api/settings/logs` | `/api/v1/system/logs/{log_id}` | legacy active | v1 只按关联 ID 返回脱敏错误摘要；不迁移旧全量日志列表语义 | P0-B |
| `/api/settings/diagnostics/export` | 待 P0-B 评审明确；当前规格无 v1 HTTP 地址 | legacy active | 不发明目标端点；若保留导出，必须走受控 Tauri 命令或先更新规格 | P0-B |
| `/api/accounts`、`/api/accounts/{account_id}` 等账号对象接口 | `/api/v1/accounts/*` | P0-C verified | 非生产模式暂保留旧读取供旧 Desktop 过渡；创建、绑定、任意更新、物理删除和 refresh-stats 统一返回 410 并指向 v1。生产模式不注册该组未迁移路由 | P0-F |
| `/api/accounts/groups*` | 无 v1 对应 | P0-C verified | 非生产模式只保留分组与成员读取供旧 Desktop 过渡；全部分组与成员写入不解析业务 Body，统一返回 410 且明确无替代接口；生产模式不注册该组路由 | P0-F |
| `/api/devices/*` | `/api/v1/accounts/{account_id}/connection`、`/api/v1/system/*` | legacy active | 账号连接与系统执行环境分离；禁止伪造绑定 | P0-C |
| `/api/devices/browser-instances*` legacy alias | 无直接等价接口 | legacy active | 该别名可能实际读写 DeviceWorkspace；P0-C 必须按真实对象拆分，禁止把 workspace ID 当 browser instance ID | P0-C |
| `/api/settings/ai-providers` | `/api/v1/system/providers`、`/api/v1/system/models` | P0-E read-only | 非生产模式只保留旧 catalog / model 读取；旧刷新返回 410；未验证模型不得成为默认路由 | P0-E |
| `/api/settings/ai-capabilities` | `/api/v1/system/model-capabilities`、`/api/v1/system/capability-routes`、`PUT /api/v1/system/providers/{provider_id}/credential`、`POST /api/v1/system/providers/{provider_id}/checks` | P0-E read-only | 非生产模式只保留旧设置与支持矩阵读取；聚合写、Secret 写和同步健康检查返回 410 | P0-E |
| `/api/ai-providers` | `POST /api/v1/system/providers/{provider_id}/checks`、`POST /api/v1/system/providers/{provider_id}/model-discovery`、`PATCH /api/v1/system/models/{model_profile_id}` | P0-E read-only | 非生产模式只保留旧健康读取；刷新和模型原地覆盖返回 410；禁止形成第三套状态 | P0-E |
| `/api/prompt-templates/*` | `/api/v1/system/prompt-profiles` | P0-E read-only | 非生产模式只保留旧列表读取；原地创建、覆盖和删除全部返回 410；激活版本不可变 | P0-E |
| `/api/tasks*` | `/api/v1/system/tasks`、`/api/v1/accounts/{account_id}/tasks` | legacy active | 切换到持久任务；旧接口仅返回兼容 DTO | P0-B |
| `/api/ws` | `/api/v1/ws` | legacy active | legacy WS 只允许系统事件；账号事件必须使用账号 Topic | P0-B |
| `/api/dashboard/summary` 等只读聚合 | `/api/v1/accounts/{account_id}`、后续计划 / 批次摘要 | legacy active | P0 只提供账号就绪摘要；禁止搬运旧项目统计 | P0-C/D |
| `/api/dashboard/context`、`/api/dashboard/projects*` | 无直接等价接口 | legacy active | 旧 Project Context 和 Project CRUD 不得映射为 Account Context 或账号摘要；P1 只按 ContentPlan / ContentItem 语义重建 | P0-F / P1（子阶段由后续计划确定） |
| `/api/scripts/*` | P1 账号范围脚本资源，具体地址由后续计划冻结 | legacy active | P0 不迁移正文；P1 建立 ContentItem 下的版本链 | P1（子阶段由后续计划确定） |
| `/api/storyboards/*` | P1 账号范围分镜资源，具体地址由后续计划冻结 | legacy active | P0 不迁移正文；P1 绑定已采用脚本版本 | P1（子阶段由后续计划确定） |
| `/api/video-deconstruction/*` | P1 账号范围拆解资源，具体地址由后续计划冻结 | legacy active | 旧覆盖 Project 的写入不得映射为新语义 | P1（子阶段由后续计划确定） |
| `/api/assets/*` | P1 账号范围内容资源，具体地址由后续计划冻结 | legacy active | P1 先建立最小 Asset 与来源追踪，再迁移内容库 | P1（子阶段由后续计划确定） |
| `/api/workspace/*` | P1 账号范围生产批次资源，具体地址由后续计划冻结 | legacy active | Timeline 和 magic-cut 不进入新 API；旧危险写入停止 | P1（子阶段由后续计划确定） |
| `/api/voice/*` | P1 批次 TTS 节点 | legacy active | 不提供独立账号导航或第二套生产任务 | P1（子阶段由后续计划确定） |
| `/api/subtitles/*` | P1 批次字幕节点 | legacy active | 字幕版本归属 ContentVariant，不形成独立主链 | P1（子阶段由后续计划确定） |
| `/api/renders/*` | P1 批次合成节点与 `RenderTask` | legacy active | 自动合成使用受控 `CompositionSpec` | P1（子阶段由后续计划确定） |
| `/api/automation/*` | P1/P2 批次或发布阶段内部任务 | legacy active | 不建立独立自动化后台 | P1/P2（子阶段由后续计划确定） |
| `/api/publishing/*` | P2 账号范围发布资源，具体地址由后续计划冻结 | legacy active | 只有真实执行绑定和平台回执才能成功 | P2（子阶段由后续计划确定） |
| `/api/review/*` | P2 账号范围复盘资源，具体地址由后续计划冻结 | legacy active | 只接受真实表现证据，回流必须人工确认 | P2（子阶段由后续计划确定） |
| `/api/search/*` | 各账号资源的受限查询，具体地址由后续计划冻结 | legacy active | 不新建跨账号全局搜索；按资源逐步退出 | P1/P2（子阶段由后续计划确定） |

所有 v1 接口使用统一信封、稳定大写错误码和 `X-Request-ID`；`log_id` 仅在可见错误或诊断记录实际生成时返回。旧接口不得新增能力；兼容层不得通过 HTTP 回环调用 v1。

## 4. 数据库来源兼容矩阵

| 数据库来源 | 识别方式 | P0-A 处理 | 失败行为 | 当前状态 |
| --- | --- | --- | --- | --- |
| 空数据库 | 无业务表、无 Alembic 版本 | 从 Alembic base 升级到 `0017` | 删除未完成的新数据库单元，不伪称已恢复备份 | P0-A verified |
| 已知 Alembic revision | `alembic_version` 属于当前迁移链 | 从当前 revision 升级到 `0017` | 失败停止 Runtime；有备份时恢复 | P0-A verified |
| `0018` 及更早版本中的历史账号 ID | `accounts.id` 由旧正式创建链生成 UUID，或来自手工导入 / 数据库直写 | `0019` 在任何账号默认对象和状态回填前按稳定资源 ID 语法校验；不自动改写主键 | 非法 ID 返回 `P0C_MIGRATION_VALIDATION_FAILED`，保持迁移前版本并要求依据备份修复真实引用 | P0-C verified |
| frozen fresh legacy cohort | 表、列、约束和持久对象匿名指纹完全匹配 | stamp `0014` 后升级 | 任一漂移只读拒绝 | P0-A verified |
| frozen runtime-current legacy cohort | 表、列、约束和持久对象匿名指纹完全匹配 | stamp `0014` 后升级 | 任一漂移只读拒绝 | P0-A verified |
| frozen schema-v3 legacy cohort | `schema_meta=3` 且完整匿名指纹匹配 | stamp `0014` 后升级 | 任一漂移只读拒绝 | P0-A verified |
| 未知或部分匹配 Schema | 指纹、表、列、CHECK、view 或 trigger 不匹配 | 不 stamp、不修补、不升级 | 返回 `DATABASE_SCHEMA_UNSUPPORTED`，保留原文件 | P0-A verified |
| 已写入 P0 数据后请求 downgrade | P0 表、字段或版本对象已有有效数据 | 拒绝有损 downgrade | 要求使用兼容当前 Schema 的 Runtime | P0-A verified |

匿名指纹不得复制业务正文、文件路径、密钥、Prompt 或个人数据。

## 5. 表与字段兼容矩阵

| legacy 对象 | P0-A 目标 | 回填 / 兼容策略 | 过渡项 | 退出阶段 |
| --- | --- | --- | --- | --- |
| `schema_meta` | `alembic_version` 成为版本真源 | 已知 cohort 可安全 stamp；旧表保留 | 不再由正常启动 repair 驱动 | P0-A |
| `accounts.id` | `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` 稳定资源 ID | 旧正式创建链的 UUID 原样保留；`0019` 先预检再回填，并增加 `ck_accounts_stable_id` 防止后续直写污染 | 冒号、路径分隔符、空白、非 ASCII、非法首字符或超长 ID 均失败封闭；不做猜测性重映射 | P0-C verified |
| `accounts` | 增加向导、原因、健康、归档、revision 字段 | archived 明确迁移；无绑定为 `unbound`；未知状态为 `attention` | v1 五状态已接管，旧任意状态写入已返回 410 | P0-C verified |
| 旧账号物理删除语义 | 归档与恢复 | 不删除历史数据；v1 只允许归档 / 恢复 | legacy DELETE 已返回 410 | P0-C verified |
| `device_workspaces` | 显式 `account_id` 与真实目录边界 | 有真实证据才绑定账号 | 旧数据的 `account_id` 仍可空，v1 不接纳不完整对象 | P0-C verified |
| `browser_instances` | 显式 `account_id` 与 workspace 引用 | 无证据不猜测账号 | 旧数据的 `account_id` 仍可空，v1 不接纳不完整对象 | P0-C verified |
| `execution_bindings` | 账号、workspace、browser、环境一致 | 只选择 Supervisor 已创建且三者一致的现有绑定，不由账号 API 伪造 | 旧数据的 `browser_instance_id` 仍可空 | P0-C verified |
| 无正式账号连接对象 | `account_connections` | 账号范围读取、绑定、解绑、健康状态与聚合修订已接入 | 真实环境创建仍属于 P0-F Supervisor | P0-C verified |
| 旧账号配置复制缺少审计对象 | `account_config_copy_runs` | 白名单复制、持久幂等和脱敏报告已接入 | AI Recipe 复制在 P0-E 前失败封闭 | P0-C verified |
| 无正式定位版本 | `positioning_profiles` | 不可变版本、激活版本和账号聚合修订已接入 | 无 | P0-C verified |
| 无账号知识根对象 | `account_knowledge_bases` | 每账号唯一基础对象，规则、来源、真实索引和启动对账已接入 | file 来源在 P0-F 受控文件桥前明确失败 | P0-C verified |
| 旧知识 / 资产引用 | `knowledge_sources`、`knowledge_snapshots` | 不猜测跨账号引用；来源隔离、正文受控存储和不可变快照已接入 | 需要 P0-F 受控文件引用解析 | P0-C verified |
| 无版本化品牌规范 | `brand_kits` | 不可变版本、激活与账号隔离已接入 | 无 | P0-C verified |
| 旧发布默认配置 | `account_publish_defaults` | 账号范围读写、校验与聚合修订已接入 | 真正发布链属于 P2 | P0-C verified |
| 旧合成模板缺少版本对象 | `composition_template_profiles` | P0-A 只建不可变版本与来源关系 | 生产批次仍未引用 | P0-E / P1 |
| `AIProviderSetting` | `provider_profiles` | P0-A 不迁移旧凭据，`credential_ref` 置空；P0-E 重新建立安全存储引用 | 默认禁用 / 待检查 | P0-E |
| `AIProviderModel` | `model_profiles` | `discovery_source=migrated` | 不代表适配器或契约可用 | P0-E |
| 旧能力声明 | `model_capabilities` | 只迁移 `declared_supported` | `adapter_supported` 重算，`contract_verified=false` | P0-E |
| 旧 Prompt / `AICapabilityConfig` | `prompt_profiles`、`capability_routes` | 形成禁用或 incomplete 草稿 | 退出主线能力不自动路由 | P0-E |
| 无账号 AI 配方 | `account_ai_recipes` | P0-A 只建表与约束 | 继承、验证与激活未接入 | P0-E |
| `system_config` | 增加 `ai_config_revision` | 保守初始化，不切换旧读取路径 | 原子修订与事件未接入 | P0-E |
| 内存任务 | `runtime_tasks` | P0-A 只建表与状态约束 | 当前 TaskManager 未切换 | P0-B |
| 全局广播事件 | `runtime_events` | P0-A 只建表、topic 与 sequence 约束 | WS/outbox/replay 未切换 | P0-B |
| `asset_groups` | 保留 legacy 资产分组并纳入 `assets.group_id` 外键 | 0014 缺失对象按确定性 Schema 补齐，不猜测分组内容 | P1 再映射账号内容库 | P1 |
| `device_workspace_logs` | 保留真实工作区日志 | 0014 缺失对象按确定性 Schema 补齐；不得伪造设备事件 | P0-C 接入账号隔离与诊断 | P0-C |
| `export_profiles` | 保留旧导出配置 | 0014 缺失对象按确定性 Schema 补齐，`config_json` 缺省为中性配置 | P1 迁入受控合成 / 导出配置 | P1 |
| `publish_receipts` | 保留平台发布回执 | 0014 缺失对象按确定性 Schema 补齐；无真实回执不回填成功 | P2 建立新发布链 | P2 |
| `projects.deleted_at` | 保留旧 Project 软删除证据 | 只补列；不把 Project 迁为账号上下文 | P1 决定受控内容迁移 | P1 |
| `assets.group_id/thumbnail_generated_at` | 保留分组引用与缩略图生成证据 | 只补列和 `asset_groups` 外键；无真实证据时保持空值 | P1 |
| `voice_tracks.version/config_json/updated_at` | 保留旧配音版本、配置与更新时间 | 只补列、缺省空配置和时间字段；不推断 TTS 结果 | P1 迁入 ContentVariant 节点 | P1 |
| `subtitle_tracks.metadata_json/updated_at` | 保留旧字幕元数据与更新时间 | 只补列和时间字段；不生成伪对齐结果 | P1 迁入 ContentVariant 节点 | P1 |
| DTO `browserInstanceId` | P0-C 分离 `device_workspace_id` 与 `browser_instance_id` | 旧账号 / 设备 DTO 中该字段可能实际承载 workspace ID；迁移前必须按真实对象类型解析 | 禁止直接写入新 `browser_instance_id` | P0-C |
| Project、Script、Storyboard、Asset | P1 ContentItem 创作链 | P0-A 完全保留旧表 | 不跨账号猜测迁移 | P1 |
| Timeline、Voice、Subtitle、Render | `CompositionSpec` 与批次内部节点 | P0-A 完全保留旧表 | 不重新暴露手动时间线 | P1 |
| Publishing、Review 历史表 | P2 发布与复盘链 | P0-A 完全保留旧表 | 不伪造绑定、回执或指标 | P2 |
| 其余未列出的 legacy 表与字段 | 原样保留 | P0-A 不改变其生产读写语义，不做猜测性回填 | 由所属 P1/P2 阶段逐项迁移 | P1/P2 |

## 6. 配置与文件兼容矩阵

| 当前输入 | 统一行为 | 冲突行为 | 状态 |
| --- | --- | --- | --- |
| `TK_OPS_RUNTIME_DB_PATH` | 数据库主环境变量 | 与 legacy 变量指向不同数据库时拒绝启动 | P0-A verified |
| `TK_OPS_DATABASE_PATH` | legacy 兼容输入，交给同一解析器 | 禁止 Alembic 与 Runtime 解析到不同文件 | P0-A verified |
| 相对数据库路径 | 固定锚定 Runtime 数据目录 | 禁止依赖进程当前工作目录 | P0-A verified |
| 相对备份 / 锁路径 | 固定锚定数据库迁移目录 | 禁止跨数据库共用未解析路径 | P0-A verified |
| Provider Secret | 目标只保存安全存储引用 | 不写数据库、DTO、日志或 Prompt | P0-E planned |
| 账号文件 | text 正文已进入账号隔离内容存储；file 只接受受控引用 | 禁止 UI 传入任意绝对路径；P0-F 文件桥前 file 索引明确失败 | P0-C verified / P0-F bridge |

## 7. 回退与退出条件

### 7.1 P0-A 启动期恢复

- Runtime 容器和业务写入尚未开放时，迁移失败可以恢复迁移前 DB / WAL / SHM 单元。
- 备份必须先校验角色、大小和哈希；恢复失败必须保留可审计恢复副本。
- 未知 Schema 不执行备份、stamp 或写入。

### 7.2 写门开放后的红线

- 写门重新开放后，迁移前备份只作为取证备份，禁止自动覆盖当前数据库。
- 代码回退必须使用兼容 `0015–0017` 的上一 Desktop 与前向兼容 Runtime。
- 维护态、`cutover_event_id`、回退制品兼容、增量导出 / 重放和灾难恢复证据是 P0-F 发布阻断项，P0-A 不宣称已经完成生产灾难恢复闭环。
- `0017_p0_enforce_and_cutover` 中的 `cutover` 仅表示 Schema 约束切换，不表示生产写门、发布切换或灾难恢复已经完成。

### 7.3 legacy 退出条件

1. 新 Desktop 不再调用对应旧 Route 或旧 API。
2. v1 契约、账号隔离和主链阶段测试通过。
3. 一个内部发布窗口内不再出现 `legacy_api.used`。
4. 用户确认 P0 主链后，另立计划删除旧页面、兼容路由和旧表。

## 8. P0-A 文件边界

P0-A 生产代码范围固定为：

- `apps/py-runtime/alembic/env.py`
- `apps/py-runtime/src/app/config.py`
- `apps/py-runtime/src/app/factory.py`
- `apps/py-runtime/src/app/lifecycle.py`
- `apps/py-runtime/src/app/logging.py`
- `apps/py-runtime/src/config/__init__.py`
- `apps/py-runtime/src/config/database.py`
- `apps/py-runtime/src/config/migration.py`
- `apps/py-runtime/src/persistence/migration/__init__.py`
- `apps/py-runtime/src/persistence/migration/types.py`
- `apps/py-runtime/src/persistence/migration/legacy_baseline.py`
- `apps/py-runtime/src/persistence/migration/fingerprint.py`
- `apps/py-runtime/src/persistence/migration/lock.py`
- `apps/py-runtime/src/persistence/migration/backup.py`
- `apps/py-runtime/src/persistence/migration/runner.py`
- `apps/py-runtime/src/persistence/migration/target_columns.py`
- `apps/py-runtime/src/persistence/migration/target_checks.py`
- `apps/py-runtime/src/persistence/migration/target_relations.py`
- `apps/py-runtime/src/persistence/migration/target_contract.py`

P0-A Alembic revision 范围固定为：

- `apps/py-runtime/alembic/versions/0015_p0_expand.py`
- `apps/py-runtime/alembic/versions/0016_p0_backfill.py`
- `apps/py-runtime/alembic/versions/0017_p0_enforce_and_cutover.py`

P0-A 测试范围固定为：

- `tests/conftest.py`
- `tests/contracts/test_runtime_contract_inventory.py`
- `tests/contracts/test_runtime_migration_startup_contract.py`
- `tests/runtime/test_core_model_migrations.py`
- `tests/runtime/test_settings_config.py`
- `tests/runtime/test_database_backup_restore.py`
- `tests/runtime/test_database_path_resolution.py`
- `tests/runtime/test_legacy_schema_fingerprint.py`
- `tests/runtime/test_migration_config.py`
- `tests/runtime/test_migration_lock.py`
- `tests/runtime/test_migration_runner.py`
- `tests/runtime/test_p0_schema_migration_invariants.py`
- `tests/runtime/test_p0_schema_migrations.py`
- `tests/runtime/test_runtime_logging.py`

P0-A 新增文档文件边界仅包含：

- `docs/P0-ACCOUNT-FOUNDATION-COMPATIBILITY-MATRIX.md`

以下既有真源只同步 P0-A 相关段落，不能以整文件作为 P0-A 独占边界；审查或提交时必须按 hunk 排除用户已有的其他修改：

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `CHANGELOG.md`
- `docs/PRD.md`
- `docs/UI-DESIGN-PRD.md`
- `docs/ARCHITECTURE-BOOTSTRAP.md`
- `docs/PROJECT-STATUS.md`
- `docs/RUNTIME-API-CALLS.md`
- `docs/superpowers/plans/2026-07-19-prototype-to-production-p0-account-foundation.md`
- `docs/superpowers/specs/2026-07-19-prototype-to-production-p0-account-foundation-design.md`

产品真源重写、交互原型、Superdesign 工作目录、Pixelle 研究和原型测试不属于 P0-A 生产代码边界。
