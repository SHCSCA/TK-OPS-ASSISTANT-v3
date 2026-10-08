# P0-H 真实 AI 执行详细设计规格

> 日期：2026-08-09
> 版本目标：`0.5.0`
> 状态：已批准，实施待开始
> 上游路线：`docs/superpowers/plans/2026-08-08-production-ai-creation-real-validation.md` 的 B1-B5
> 真源优先级：安全与数据真实性 > 账号隔离与可恢复 > 功能完整 > 开发速度

## 1. 目标、范围与退出口径

本规格只定义 P0-H 真实 AI 执行，不改变 `0.4.11` P0-G，也不开放八个 `p1_pending` / `p2_pending` 正式业务路由。实施完成后的唯一退出口径是：至少一个 OpenAI-compatible 文本模型完成“真实模型发现 → 真实小调用 → 系统 Route 与 Prompt → 当前账号 Recipe → 受控知识文件 → 可追溯 AIExecution”的纵向链，并产生绑定当前制品的脱敏人工证据。

### 1.1 H1-H5 固定依赖顺序

| 阶段 | 必须交付 | 依赖 | 阻断后处理 |
| --- | --- | --- | --- |
| H1 Provider 实测 | 网络、鉴权、模型发现、真实小调用分层证据；OpenAI-compatible 文本端口 | P0-E Provider/Model/Capability | 未通过不得进入可用 Route；其他适配器只保留契约状态 |
| H2 依赖图 | Provider、Model、Capability Route、Prompt、Composition Template、Recipe 的显式修订、不可变激活快照、问题与修复动作 | H1 的真实验证记录 | 阻断依赖允许保存草稿，不允许激活或执行 |
| H3 受控知识文件 | Tauri `rootRef` 下的文件授权、账号 Asset、KnowledgeSource、持久索引任务与恢复 | P0-G rootRef、P0-C Knowledge | 文件桥不可用时失败封闭，不回退绝对路径或复制源文件 |
| H4 AI Execution Gateway | AIExecution、AIJob、Provider 端口、任务、快照、usage/cost、输出、错误、取消、重试与 fallback | H1-H3 | 任一快照不完整即拒绝创建，不调用外部 Provider |
| H5 真实验收 | 自动确定性证据与目标机器人工真实证据，两者均绑定同一 0.5.0 制品 | H1-H4 | 自动假 Provider 不得替代人工真实 Provider 证据 |

### 1.2 明确不做

- 不实现 P0-I 的 ContentItem、Script、Storyboard、ProductionBatch 或八个正式页面。
- 不把 ComfyUI、RunningHub、`direct_api` 标记为真实验收通过；它们在 P0-H 只完成统一端口契约和确定性测试。
- 不读取、生成、提交或记录真实 API Key；凭据只由用户在目标机器通过现有安全存储入口人工提供。
- 不让 Desktop 直连 Provider，不新增页面私有配置，不让旧 `AITextGenerationService` 继续读取另一套配置。
- 不用 seed、静态 capability、mock 响应或本地假 Provider 冒充 H5 人工真实证据。

## 2. 当前事实与迁移裁决

| 现有事实 | P0-H 裁决 |
| --- | --- |
| `ProviderAdapter` 只有 `check_health`、`discover_models`、`probe_capabilities` | 保留为 H1 配置检查兼容层；新增执行端口，静态 probe 不再产生“真实已验证”状态 |
| `AITextGenerationService` 直接读取 legacy capability 并写 `ai_job_records` | 改为新 Gateway 的兼容外观；`ai_job_records` 停止新增，仅供历史读取 |
| Prompt、Composition Template、Account Recipe 已按版本存储 | 原版本记录继续不可变；P0-H 增加依赖快照，不复制正文到日志或任务快照 |
| Provider、Model、Capability Route 当前只保留最新可变记录 | 0023 回填不可变 revision 表；以后每次修改同时写新 revision |
| `KnowledgeSource` 已支持 `file_ref_...`，但解析器是 `UnavailableControlledFileResolver` | H3 用 Tauri `rootRef` 注册表实现真实解析；HTTP 仍只接收 `fileRef`，不接收路径 |
| legacy `assets` 没有 `account_id` | P0-H 新建 `account_assets`；旧 `assets` 只读，P0-I 再显式迁移 |
| Runtime 持久任务已有 timeout、cancel、retryOfTaskId 与重启恢复 | AI 执行复用该内核，外部调用任务采用 `interrupt`，重启后绝不自动重复扣费调用 |

## 3. 全局不变量

1. 所有账号级数据表、仓储查询、缓存键、事件 Topic、输出引用和任务必须显式包含 `account_id`。
2. 系统 Provider 凭据只存安全存储；数据库可保存不透明 `credential_ref`，但 API、日志、事件、任务快照、幂等响应和 manifest 均不得返回它。
3. AIExecution 创建后，其配置、Prompt、Recipe、知识、定位、Route 候选、输入哈希和预算快照不可修改；变更配置后只能创建新执行。
4. 外部调用不得位于数据库事务中。外部结果写入时使用任务提交协调器，在取消与提交之间只允许一个终态获胜。
5. Provider 原始请求、原始响应、完整 Prompt、知识正文、绝对路径、用户账号资料和凭据不得进入普通日志或 release evidence。
6. 所有金额以整数 `cost_micros` 保存，币种为 ISO 4217 大写代码；不得使用浮点数累计成本。
7. `idempotency`、`timeout`、`retry`、`cancel`、fallback、并发和 `cost` 上限必须由统一配置总线和不可变 Route 快照共同约束。
8. 自动假 Provider 只证明确定性契约；只有人工提供凭据后的真实 OpenAI-compatible 调用才满足 H5。

## 4. 0023 加法迁移与数据模型

迁移文件固定为 `apps/py-runtime/alembic/versions/0023_p0h_real_ai_execution.py`，`down_revision="0022_p0g_production_hardening"`。迁移只新增表、索引和有默认值的列；不删除旧表、不改写历史 AI 输出、不把 legacy 项目推断为账号数据。已有 Provider、Model、Route 在迁移内生成 revision 1 的保守快照；无法解析的记录保持当前数据不变，并使 P0-H 写门失败封闭。

### 4.1 配置与依赖快照表

| 表 | 关键字段 | 约束 |
| --- | --- | --- |
| `provider_profile_revisions` | `id,provider_profile_id,revision,adapter_type,base_url,base_url_hash,region,proxy_ref,timeout_ms,max_concurrency,extra_params_json,cost_policy_json,credential_ref,content_hash,created_at` | `(provider_profile_id,revision)` 唯一；Base URL 与安全引用供旧 revision 执行，DTO/log/evidence 不返回；`credential_ref` 仅 Runtime 内部读取 |
| `model_profile_revisions` | `id,model_profile_id,provider_profile_revision_id,revision,model_id,display_name,enabled,context_window,base_limits_json,content_hash,created_at` | `(model_profile_id,revision)` 唯一；引用不可变 Provider revision |
| `capability_route_revisions` | `id,capability_route_id,capability_key,revision,status,prompt_profile_id,candidate_policy_json,timeout_ms,max_retries,retry_policy_json,max_concurrency,max_cost_micros,currency,enabled,dependency_snapshot_id,content_hash,created_at` | `(capability_route_id,revision)` 唯一，且每个 Route 至多一个 `status=active`；`status=draft|active|archived`；候选按优先级固定排序 |
| `ai_dependency_snapshots` | `id,owner_type,owner_id,owner_revision,status,graph_json,issues_json,repair_actions_json,content_hash,created_at` | `owner_type` 为 `route|recipe|composition_template|execution_preflight`；内容不可更新 |
| `ai_provider_validation_runs` | `id,provider_profile_id,provider_revision,model_profile_id,model_revision,capability_key,stage,status,task_id,request_hash,response_hash,response_id_hash,usage_json,duration_ms,error_code,error_log_id,verified_at,created_at` | `stage` 为 `network|authentication|model_discovery|real_small_call`；只有真实响应可写 `status=verified` |

0023 同时给 `provider_profiles` 增加 `extra_params_json`、`cost_policy_json`、`active_revision_id`，给 `model_profiles` 与 `capability_routes` 增加 `active_revision_id`，给 `account_ai_recipes` 与 `composition_template_profiles` 增加 `dependency_snapshot_id`。活动指针使用复合约束保证 revision 属于同一基础记录；Route 使用部分唯一索引保证至多一个 active revision。新增列先允许空值；服务写门只接受已回填且通过验证的记录。迁移不伪造真实验证记录。Provider、credential 或 Model 的写入都创建不可变 revision，并在同一事务切换对应 `active_revision_id`；旧 revision 只供历史快照读取，基础表不再成为执行期配置真源。

### 4.2 AIExecution 聚合

`AIExecution` 映射 `ai_executions`，字段固定如下：

| 字段 | 类型/含义 | 规则 |
| --- | --- | --- |
| `id` | 稳定资源 ID | 主键 |
| `account_id` | 账号 ID | 非空、外键、所有读取必须同时过滤 |
| `capability_key` | 产品能力 | P0-H 首条链为 `script_generation` |
| `status` | `queued|running|cancelling|failed|completed` | 与 Runtime 任务语义一致 |
| `completion_kind` | `succeeded|cancelled|null` | 仅 completed 非空 |
| `failure_kind` | `error|timed_out|restart_interrupted|result_unknown|null` | 仅 failed 非空；result_unknown 表示请求已发送但无法证明 Provider 终态 |
| `snapshot_id` | AIExecutionSnapshot ID | 非空唯一外键，一对一、创建后不可替换 |
| `runtime_task_id` | `ai.execution` 任务 ID | 非空、同账号作用域 |
| `active_job_id` | 当前或最终 AIJob | 可空；必须属于同一 execution/account |
| `retry_of_execution_id` | 原执行 ID | 同账号；默认重试复用原 snapshot |
| `input_ref` | 受控输入引用 | 不透明 `ai-input://...`，API 不返回 |
| `input_hash` | SHA-256 | 幂等与审计使用 |
| `idempotency_key_hash` | 幂等键摘要 | 原文不落库 |
| `request_hash` | 规范化请求摘要 | 同键异请求返回冲突 |
| `budget_limit_micros` | 本次总预算 | 非负整数 |
| `currency` | 成本币种 | 默认由 Route 快照给出 |
| `usage_input_units` | 输入 token/单位合计 | 可空代表 Provider 未报告 |
| `usage_output_units` | 输出 token/单位合计 | 可空代表 Provider 未报告 |
| `usage_cached_units` | 缓存 token/单位合计 | 可空 |
| `cost_micros` | 所有尝试成本合计 | 可空，禁止猜测 |
| `cost_status` | `reported|estimated|unavailable` | estimated 必须有 pricing revision |
| `output_count` | 已提交输出数量 | 非负整数 |
| `error_code,error_log_id` | 安全错误与日志引用 | 不存原始异常 |
| `revision` | 聚合修订 | 每次状态转换递增 |
| 时间字段 | `created_at,started_at,completed_at,updated_at` | UTC ISO-8601 |

### 4.3 不可变 AIExecutionSnapshot 与候选

`ai_execution_snapshots` 保存：

- `id,account_id,capability_key,account_revision,ai_config_revision`。
- `positioning_profile_id,positioning_version,positioning_content_hash`。
- `knowledge_snapshot_id,knowledge_snapshot_version,knowledge_content_hash`。
- `account_recipe_id,recipe_version,recipe_revision,recipe_content_hash`。
- `capability_route_id,route_revision_id,route_content_hash`。
- `prompt_profile_id,prompt_version,prompt_revision,prompt_content_hash,rendered_prompt_hash`。
- `dependency_snapshot_id,input_schema_hash,output_schema_hash,policy_json,snapshot_hash,created_at`。

快照只保存 Prompt 与输入的哈希和不可变版本引用，不复制 Prompt 正文。执行处理器通过 `prompt_profile_id + prompt_version + prompt_revision` 精确读取不可变正文，通过 `input_ref` 读取账号受控输入；两者读取后再次校验哈希。Snapshot 不反向保存 `execution_id`，一对一关系仅由 `ai_executions.snapshot_id` 的非空唯一外键建立，避免创建时形成循环外键。

`ai_execution_candidates` 每个候选一行：

- `id,account_id,execution_snapshot_id,ordinal`。
- `provider_profile_id,provider_revision_id,adapter_type,credential_ref`。
- `model_profile_id,model_revision_id,model_id,capability_contract_revision,validation_run_id`。
- `timeout_ms,max_retries,max_concurrency,max_cost_micros,retry_policy_json,extra_params_json,snapshot_hash`。

候选顺序在创建时冻结。`credential_ref` 使用安全存储的 copy-on-write 引用；凭据轮换创建新引用，旧引用仅在非终态执行仍引用时保留，之后按配置总线保留期清理。

### 4.4 AIJob、usage/cost、输出与错误证据

| 模型/表 | 必填字段 | 安全与一致性 |
| --- | --- | --- |
| `AIJob` / `ai_execution_jobs` | `id,account_id,execution_id,candidate_snapshot_id,attempt,fallback_index,retry_index,status,completion_kind,failure_kind,provider_request_id_hash,request_hash,response_hash,duration_ms,timeout_at,error_evidence_id,revision,created_at,started_at,completed_at` | 每次真实外部尝试一行；不存原始请求/响应；同 execution 串行 fallback |
| `AIUsageRecord` / `ai_usage_records` | `id,account_id,execution_id,job_id,provider_profile_id,model_profile_id,input_units,output_units,cached_units,total_units,cost_micros,currency,cost_source,pricing_revision,raw_usage_hash,created_at` | usage 缺失保留 null 与 `cost_source=unavailable`，不得填 0 冒充 |
| `AIExecutionOutput` / `ai_execution_outputs` | `id,account_id,execution_id,job_id,kind,mime_type,content_ref,content_hash,byte_size,schema_status,safe_summary_json,created_at` | 正文进入账号受控 OutputStore；DTO 可按账号授权读取正文，日志/manifest 只用摘要和哈希 |
| `AIErrorEvidence` / `ai_error_evidence` | `id,account_id,execution_id,job_id,stage,error_code,provider_status_code,retryable,safe_summary,provider_request_id_hash,response_body_hash,log_id,created_at` | 不存 URL、Header、原始 Body、Prompt 或 traceback |

新类名使用 `AIExecutionJob`，对外 DTO 使用 `AIJobDto`，避免与 legacy `AIJobRecord` 混淆。`ai_job_records` 不迁移、不删除，也不接受 P0-H 新写入。

### 4.5 账号 Asset 与知识索引派生数据

| 表 | 字段 | 边界 |
| --- | --- | --- |
| `account_assets` | `id,account_id,kind,source_kind,controlled_file_ref,root_ref,display_name,media_type,byte_size,content_hash,status,authorization_basis,error_code,error_log_id,revision,created_at,updated_at` | `source_kind=controlled_file`；无绝对路径；账号外查询返回 404 |
| `knowledge_source_assets` | `account_id,knowledge_source_id,account_asset_id,created_at` | 三者同账号；一来源在 P0-H 绑定一个源 Asset |
| `knowledge_index_chunks` | `id,account_id,knowledge_source_id,source_revision,ordinal,content_ref,content_hash,token_count,extractor_version,created_at` | 只保存派生文本引用与哈希，不复制源文件；旧 snapshot 不自动获得新 chunk |

P0-H 第一条真实链只要求 UTF-8 `text/plain`、Markdown 和 JSON 文档形成文本 chunk。图片、视频、音频及其他文档仍可创建 Asset/KnowledgeSource 并完成真实字节哈希，但若没有已验证分析 Route，只形成 `metadata_only` 证据，不能作为脚本生成的文本上下文。依赖图必须返回明确修复动作。

## 5. 状态机与事务边界

### 5.1 AIExecution 状态机

| 当前状态 | 事件 | 下一状态 | 原子副作用 |
| --- | --- | --- | --- |
| 无 | 创建成功 | `queued` | 冻结 snapshot/candidates/input hash，创建 RuntimeTask，发布 `ai.execution.queued` |
| `queued` | TaskRunner claim | `running` | 写 started_at，创建首个 AIJob |
| `queued|running` | 用户取消 | `cancelling` | RuntimeTask 同步进入 cancelling，调用 Provider cancel |
| `running` | 候选成功且提交获胜 | `completed+succeeded` | 同事务写 output、usage/cost、job、execution 与事件 |
| `running` | 可重试失败 | `running` | 当前 job failed，按策略创建同候选下一 retry job |
| `running` | 可 fallback 失败 | `running` | 当前 job failed，创建下一 candidate job |
| `running` | 超时且无后续候选 | `failed+timed_out` | 写安全错误、任务 failed |
| `running` | 请求已发送但终态不可证明 | `failed+result_unknown` | 禁止自动 retry/fallback，写计费不确定证据 |
| `running` | 全候选耗尽 | `failed+error` | 错误码 `AI_ALL_CANDIDATES_FAILED` |
| `cancelling` | 取消提交获胜 | `completed+cancelled` | job 与 task 均取消终态，清理未提交输出临时文件 |
| 非终态 | Runtime 重启 | `failed+restart_interrupted` | 不重放外部调用，保留快照并提供同快照重试 |

终态不可回退。迟到 Provider 响应只有在任务提交协调器裁决“提交获胜”时可写入；取消获胜后响应只做内存清理，不生成输出或 usage 猜测。

### 5.2 AIJob 状态机

AIJob 使用 `queued|running|cancelling|failed|completed`，completion/failure 语义与 RuntimeTask 一致。一个 execution 同时最多一个 running job；`retry_index` 在同候选内递增，`fallback_index` 只在候选切换时递增。失败 job 永不覆盖，新的 retry/fallback 必须创建新行。

### 5.3 事务边界

1. 创建事务：先预生成 execution、snapshot 与 task ID，再把账号门禁、依赖解析、快照、Execution、RuntimeTask、幂等记录与 outbox 一次提交；任何外键都不得要求先提交另一半聚合。
2. 外部调用：事务外执行，持有只读不可变 candidate 和受控输入；不得保持数据库 Session。
3. 结果事务：校验取消裁决后，一次提交 output、usage/cost、error、AIJob、AIExecution、RuntimeTask 与 outbox。
4. 文件写入：先把正文写入账号 OutputStore 临时文件并 fsync，再以不覆盖既有异哈希文件的方式原子改名为最终 content-addressed 路径，最后在结果事务提交 `content_ref/content_hash`。原子改名失败不提交数据库；数据库失败或进程在改名后崩溃会留下无引用最终文件，由启动对账按保留期清理。数据库绝不先提交一个尚不存在的最终文件引用。

## 6. account_id 隔离、幂等与修订

- 所有 Repository 方法签名把 `account_id` 放在资源 ID 前；禁止仅按 execution/job/output ID 查询。
- 外键使用账号冗余与复合唯一键保证 execution、job、snapshot、output、usage、error 不能跨账号拼接。
- 列表游标绑定 `account_id + resource_type + filter_hash + sort_position`；跨账号使用返回 `INVALID_SCOPED_CURSOR`。
- Desktop 缓存键固定以 `account:${accountId}:ai-executions` 开头；账号切换时取消旧请求、断开旧 Topic、清空 Detail Panel，迟到响应不得写入新账号 Store。
- 创建、retry、cancel 以及任何会新增 Runtime 记录的 POST 均要求 `Idempotency-Key`。只读 Evidence GET 不要求幂等键；原文只在请求内存中存在，持久层保存 SHA-256。
- 同键同 request hash 返回原 execution/task 与 `meta.idempotentReplay=true`；同键不同请求返回 `REQUEST_CONFLICT`。
- 默认 retry 只接受 `{mode:"same_snapshot"}`，创建新 AIExecution 并指向 `retry_of_execution_id`；“按最新配置重新运行”必须走普通创建端点并形成新 snapshot。
- 配置对象使用其自身 revision；账号写使用 `If-Match` 的账号 revision。执行详情中的历史 revision 与 hash 只读，不受后续配置修改影响。

## 7. H1 Provider 端口与真实验证

### 7.1 统一端口

新 `AIProviderPort` 只暴露以下方法：

| 方法 | 输入 | 输出 | 要求 |
| --- | --- | --- | --- |
| `health` | Provider revision、deadline、cancel token | network/auth 分段证据 | 网络与鉴权不可合并成一个“正常”布尔值 |
| `discover_models` | Provider revision、分页上限 | 规范化模型列表 | 禁止跟随重定向；响应有大小和条数上限 |
| `validate_capability` | model revision、capability、内置最小输入 | 真实响应摘要、usage、耗时、哈希 | 必须实际调用模型；静态声明不得返回 verified |
| `execute` | AIProviderRequest、deadline、cancel token | AIProviderResult 或安全分类错误 | 不返回可直接日志化的原始 HTTP 对象 |
| `cancel` | ProviderCallHandle | `remote_cancelled|local_transport_closed|unsupported` | unsupported 不得表述为远端已取消 |

retry、fallback、并发和 cost 上限由 Gateway 统一控制，不由适配器私自决定。适配器只将外部错误归一为 `network|authentication|rate_limit|timeout|server|invalid_request|content_rejected|invalid_response|cancelled`。

### 7.2 OpenAI-compatible 第一条链

- `extra_params_json.protocolVariant` 必须显式为 `chat_completions` 或 `responses`，默认 `chat_completions`；禁止运行时猜测协议。
- Base URL 必须为 HTTPS，只有 loopback 可使用 HTTP；拒绝 query、fragment、userinfo 和重定向。
- 模型发现使用已配置鉴权访问 `/models`。
- 真实小调用使用内置非用户 Prompt、`max_output_tokens<=8`、温度 0，并要求非空响应、可识别 finish reason 与 Provider usage。
- `ai_provider_validation_runs.status=verified` 只在真实 HTTP 成功、响应结构有效、模型 ID 匹配且 usage 存在时写入；usage 缺失写 `partial`，不能成为 H5 Route。
- Provider/Profile/Model 任一 revision 改变后，旧真实验证证据不再满足新 revision 的可用性，但历史 AIExecution 继续引用旧证据。

### 7.3 timeout、retry、fallback、并发与成本

| 策略 | 固定规则 |
| --- | --- |
| timeout | 使用单调时钟总 deadline；连接、首字节、读取分别受限；Route timeout 不得超过配置总线最大值 |
| retry | 仅请求正文未发送的连接失败、明确 429、明确可恢复 5xx，或 Provider 明确支持同一幂等键的调用；认证、参数、内容拒绝、取消、预算和响应 Schema 错误不重试 |
| retry backoff | 指数退避加抖动，尊重受上限约束的 `Retry-After`；所有等待都可取消 |
| fallback | 同候选 retry 耗尽后，仅对 Route 允许的错误类别切换；用户取消、认证失败、内容拒绝和预算不足不 fallback |
| 并发 | 取系统、Provider revision、Route revision 三者最小值；队列等待有独立超时，账号公平调度 |
| cost | 调用前按输入估算、最大输出和 pricing revision 做最坏值预检；每次 retry/fallback 都计入总预算 |
| usage | Provider 未返回则记 unavailable；不得写 0；H5 人工验收要求 reported usage |

成本上限为 hard 时，缺少可验证定价或 Provider 成本即返回 `AI_COST_UNAVAILABLE`，不调用外部服务。Provider 忽略输出上限导致实际成本越界时保留输出与真实 usage 证据，但 execution 进入 failed、错误码 `AI_COST_LIMIT_EXCEEDED`，输出标记 quarantined，只有用户显式确认后才能另建业务对象。

连接在请求正文发送后中断、总 timeout 或进程重启时，若 Provider 不支持查询请求终态或稳定幂等键，Gateway 必须写 `AI_PROVIDER_RESULT_UNKNOWN` 与 `cost_status=unavailable`，禁止自动 retry/fallback。用户可在看到“可能已产生调用与费用”的提示后显式创建 same_snapshot retry；新 execution 必须保留 `retry_of_execution_id`，不得把两次调用合并为一次成本。

## 8. H2 配置依赖图与不可变激活快照

依赖解析顺序固定为：

```text
系统 CapabilityRoute revision
→ AccountAIRecipe version 的显式 route override
→ 单次允许的非敏感参数覆盖
→ Provider/Model/真实验证证据
→ Prompt/Composition Template 不可变版本
→ Positioning/Knowledge 不可变快照
→ ResolvedAIExecutionPlan
```

单次覆盖只允许 output schema 已声明的温度、最大输出、语言、画幅等字段；不允许覆盖 Provider、credential、Base URL、未验证模型、Prompt 正文或账号 Recipe。

### 8.1 DependencyIssue 与 RepairAction

| DTO | 字段 |
| --- | --- |
| `DependencyIssueDto` | `code,severity,nodeType,nodeId,path,message,blocking,evidenceRef` |
| `RepairActionDto` | `kind,label,targetPage,targetSection,targetResourceId,requiredAccountId` |
| `DependencySnapshotDto` | `id,ownerType,ownerId,ownerRevision,status,contentHash,issues[],repairActions[],createdAt` |

`severity=info|warning|error`；只有 `blocking=true` 阻止激活/执行。RepairAction 只导航或打开编辑器，不自动修改配置。保存草稿可带问题；Route、Recipe、Template 激活必须生成 `status=valid` 的新依赖快照。运行中的执行继续使用旧快照。

### 8.2 固定问题码

- `AI_PROVIDER_DISABLED`
- `AI_PROVIDER_REAL_VALIDATION_REQUIRED`
- `AI_MODEL_DISABLED`
- `AI_MODEL_CAPABILITY_UNVERIFIED`
- `AI_ROUTE_INCOMPLETE`
- `AI_PROMPT_VERSION_MISSING`
- `AI_PROMPT_SCHEMA_INVALID`
- `AI_RECIPE_STALE`
- `AI_RECIPE_ROUTE_CONFLICT`
- `AI_KNOWLEDGE_SNAPSHOT_NOT_READY`
- `AI_KNOWLEDGE_TEXT_CONTEXT_UNAVAILABLE`
- `AI_COST_POLICY_INVALID`
- `AI_CONCURRENCY_POLICY_INVALID`

### 8.3 配置 revision 生命周期

1. Provider PATCH、credential PUT 与 Model PATCH 都创建新的不可变 revision，并原子切换基础记录的 `active_revision_id`；校验或保存失败不改变活动指针。
2. CapabilityRoute 新建 revision 固定进入 `draft`。validate 为该 revision 生成不可变 DependencySnapshot；只有 `status=valid` 且没有 blocking issue 的 revision 才能 activate。
3. activate 使用 `If-Match` 锁定 CapabilityRoute 聚合 revision，在同一事务把上一活动 revision 标记为 `archived`、目标标记为 `active`、切换 `active_revision_id` 并发布配置失效事件；历史 AIExecution 继续引用旧 revision。
4. AccountAIRecipe 与 CompositionTemplate 复用既有 version 创建、validate、activate 端点；validate 必须写入 dependency snapshot，activate 必须再次校验目标 version 与 snapshot hash，禁止只依赖旧 UI 状态。
5. 既有 CapabilityRoute PUT 与无 revision validate 端点在 0.5.0 仅作兼容适配：它们调用同一 revision service 完成“创建草稿 → 校验 → 可用时激活”，失败时保留可修复草稿并返回 issues；不得直接更新基础表或形成第二套配置真源。Desktop 生产调用统一迁移到显式 revision 端点。

## 9. H3 rootRef 受控知识文件

### 9.1 Tauri 文件授权链

1. Desktop 先取得当前账号已授权 `rootRef`。
2. `pick_account_controlled_file(accountId,rootRef,filters)` 打开系统文件选择器。
3. Tauri 校验账号拥有该 rootRef、root revision 有效、文件规范路径位于根目录内、不是目录、不是符号链接/重解析逃逸、大小和扩展名符合配置总线。
4. Tauri 在 `controlled-files.v1.json` 写入 `fileRef,accountId,rootRef,rootRevision,canonicalPath,relativePath,fileIdentity,size,mtime,status,revision`；只向 WebView 返回 `fileRef,displayName,kind,size,rootRef,revision`。
5. Desktop 调用现有 KnowledgeSource POST，只传 `controlledFileRef=file_ref_...`。
6. Runtime `ControlledFileResolver` 读取本地注册表，再次校验 account/root/revision/文件身份和根目录包含关系；HTTP 请求中的任何路径字段都被拒绝。

Supervisor 通过统一 Runtime 启动配置注入 `TK_OPS_CONTROLLED_FILE_REGISTRY_PATH`，值固定指向 `app_local_data_dir/controlled-files.v1.json`；Runtime 启动时校验该路径仍位于本机应用数据目录，随后只把已验证 Path 注入 Resolver。该路径不经 WebView 或 HTTP 传递，配置摘要与日志只能记录哈希，不能记录原文。

绝对路径只存在于 Tauri 私有注册表、受保护的 Runtime 启动环境与进程内解析结果，不进入数据库、Runtime API、日志、事件、缓存、证据或 manifest。文件在授权根外时只允许用户显式授权其父目录；系统不得自动复制文件到工作区。

### 9.2 Asset、KnowledgeSource 与索引

- 创建 file KnowledgeSource 时，Runtime 在同一事务创建 `account_assets`、KnowledgeSource 和关联行；任一失败全部回滚。
- Tauri grant 已创建但 HTTP 失败时属于无业务引用 grant；Tauri 启动对账在保留期后清理，绝不删除用户源文件。
- `knowledge.index` 冻结 sourceIds、fileRef、rootRef revision、文件 fingerprint、索引策略和 extractor version。
- 索引读取前后都校验 fingerprint；变化返回 `CONTROLLED_FILE_CHANGED`，来源进入 stale，保留 taskId/logId 和“重新授权并重试”。
- 源文件只读且不复制。文本抽取与 chunk 是派生索引数据，保存在账号隔离的 Runtime ContentStore，并记录源 hash 与 extractor version。
- 失败只更新对应 Asset/KnowledgeSource/任务；已成功来源不回滚。retry 使用新 RuntimeTask，保留 `retryOfTaskId`。
- rootRef revoked、文件缺失、文件变化、大小越界、类型不支持均有可见中文错误与恢复动作。

## 10. H4 AI Execution Gateway

### 10.1 创建与执行流程

```text
校验 Runtime/许可证/账号
→ 校验 If-Match 与 Idempotency-Key
→ 读取当前 Recipe/Route/Prompt/定位/知识
→ 构建依赖图与候选顺序
→ 预算、并发、真实验证预检
→ 写受控输入并计算 hash
→ 原子创建 snapshot + candidates + AIExecution + RuntimeTask + outbox
→ TaskRunner 逐候选执行 AIJob
→ 写 output + usage/cost + error evidence
→ 更新 Execution/Task 终态并广播
```

第一条 `script_generation` 链必须真实使用知识而不是只记录引用：Gateway 按 KnowledgeSnapshot manifest v2 校验 `account_id/source_revision/chunk_hash`，按来源 ID 与 chunk ordinal 稳定排序，在 Route 的 `knowledgeMaxInputUnits` 内截断并生成 `context_manifest_hash`；随后用不可变 Prompt version 渲染受控变量和知识上下文，校验 `rendered_prompt_hash` 后才交给 Provider。正文只在进程内与账号受控 InputStore 中存在，任务快照、日志和 evidence 只保存 hash。没有可用文本 chunk 时 preflight 返回 `AI_KNOWLEDGE_TEXT_CONTEXT_UNAVAILABLE`，不得发送一个忽略知识的请求冒充完整链。

任务类型固定为 `ai.execution`，scope 为 account，handler version 1，resume policy 为 `interrupt`，cancellable 为 true。任务 snapshot 只含 `executionId,snapshotHash`，不含输入、Prompt、credential、路径或 Provider 请求正文。

### 10.2 取消与恢复

- Execution cancel 端点先验证同账号，再调用 RuntimeTask cancel；仅停止 Desktop 轮询不算取消。
- Provider 支持远程 cancel 时发送；否则关闭本地传输并记录 `local_transport_closed`，不宣称远端已取消。
- Provider 在取消提交前返回 reported usage 时照实记录；取消终态仍未获得 usage 时标记 `cost_status=unavailable` 与 `billingStatus=unknown`，UI 明示“远端可能已产生费用”，不得填 0。
- Runtime 重启时，尚未发送请求的非终态执行标为 `restart_interrupted`；已发送但没有可证明终态的执行标为 `result_unknown`。两者都同步 failed，不猜测 Provider 是否成功，也不自动重发。
- 用户点击“按原快照重试”创建新 execution、task 和 jobs；输入、配置、Prompt、Recipe、知识与候选 hash 保持相同。
- 用户选择“按最新配置重新运行”走普通创建流程，形成新 snapshot，并在 UI 明确展示差异。

### 10.3 legacy 收口

`AITextGenerationService` 保留旧方法外观，但内部只调用 `AIExecutionGateway`：

- 必须解析出明确 `account_id`；无法从 legacy project 唯一映射账号时返回 `ACCOUNT_SCOPE_MISMATCH`。
- capability、Provider、模型、Prompt、timeout 与凭据全部从 Gateway/配置总线解析。
- 同步调用只允许有界等待新 RuntimeTask，并返回新 output；不再写 `ai_job_records`。
- feature flag 关闭 Gateway 时 legacy 调用明确返回 `AI_EXECUTION_DISABLED`，不得恢复旧直连链。

## 11. Runtime API v1

所有端点需要 Runtime Session、许可证、Host/Origin 门禁与 `X-Request-ID`。成功使用 `{ok:true,data,meta?}`，失败使用 `{ok:false,error,error_code,log_id?,fieldErrors?,meta?}`。唯一接口文档落在 `docs/api/v1/ai-executions.md`，同文件包含 Desktop 调用映射；`ai-system.md`、`account-knowledge.md`、`tasks-and-events.md` 只追加交叉引用和各自资源差异。

### 11.1 接口总览

| 方法 | 地址 | Headers | 参数 | 成功 |
| --- | --- | --- | --- | --- |
| PATCH | `/api/v1/system/providers/{provider_id}` | If-Match | Body `name,baseUrl,region,proxyRef,timeoutMs,maxConcurrency,enabled,extraParams,costPolicy` 的完整允许字段子集 | 200 `ProviderDto` 与新 revision；未知字段 422 |
| PUT | `/api/v1/system/providers/{provider_id}/credential` | If-Match | Body `{credential}`；空白拒绝；保存采用 copy-on-write secret ref | 200 `CredentialSummaryDto`，不返回 secret ref 原文 |
| POST | `/api/v1/system/providers/{provider_id}/checks` | Idempotency-Key | Body `{stages:[network,authentication],force}` | 202 `TaskAcceptedDto` |
| POST | `/api/v1/system/providers/{provider_id}/model-discovery` | Idempotency-Key | Body `{replaceMissing:false}` | 202 `TaskAcceptedDto` |
| PATCH | `/api/v1/system/models/{model_profile_id}` | If-Match | Body `displayName,enabled,contextWindow,baseLimits` 的完整允许字段子集 | 200 `ModelProfileDto` 与新 revision |
| POST | `/api/v1/system/models/{model_profile_id}/capability-checks` | Idempotency-Key | Body `{capabilityKeys,mode,force}` | 202；真实小调用模式 |
| GET | `/api/v1/system/capability-routes/{capability_key}/revisions` | 无 | Query `cursor?,limit?` | 200 `CapabilityRouteRevisionPageDto` |
| POST | `/api/v1/system/capability-routes/{capability_key}/revisions` | If-Match、Idempotency-Key | Body `promptProfileId,candidates,timeoutMs,maxRetries,retryPolicy,maxConcurrency,maxCostMicros,currency,enabled` | 201 `CapabilityRouteRevisionDto(status=draft)` |
| POST | `/api/v1/system/capability-routes/{capability_key}/revisions/{revision}/validate` | Idempotency-Key | Path；Body 无 | 200 `CapabilityRouteValidationDto`，含 dependency snapshot/issues/actions |
| POST | `/api/v1/system/capability-routes/{capability_key}/revisions/{revision}/activate` | If-Match、Idempotency-Key | Path；Body 无 | 200 `CapabilityRouteDto` 与新活动 revision |
| PUT | `/api/v1/system/capability-routes/{capability_key}` | If-Match、Idempotency-Key | 兼容 Body `CapabilityRouteInput` | 200 活动 Route；内部仅调用 revision lifecycle，并返回 `meta.compatibilityAdapter=true` |
| POST | `/api/v1/system/capability-routes/{capability_key}/validate` | Idempotency-Key | Path；Body 无 | 200 当前活动 revision 的 `CapabilityRouteValidationDto`；兼容适配 |
| POST | `/api/v1/accounts/{account_id}/ai-recipe/versions/{version}/validate` | Idempotency-Key | Path；Body 无 | 200 `AccountAIRecipeValidationDto` 与 dependency snapshot |
| POST | `/api/v1/accounts/{account_id}/ai-recipe/versions/{version}/activate` | If-Match、Idempotency-Key | Path；Body 无 | 200 `AccountAIRecipeDto` |
| POST | `/api/v1/system/composition-templates/{template_key}/versions/{version}/validate` | Idempotency-Key | Path；Body 无 | 200 `CompositionTemplateValidationDto` 与 dependency snapshot |
| POST | `/api/v1/system/composition-templates/{template_key}/versions/{version}/activate` | If-Match、Idempotency-Key | Path；Body 无 | 200 `CompositionTemplateDto` |
| GET | `/api/v1/system/ai-dependencies` | 无 | Query `ownerType=route|composition_template,ownerId,ownerRevision` | 200 `DependencySnapshotDto` 预览 |
| POST | `/api/v1/accounts/{account_id}/ai-executions/preflight` | If-Match | Body 为创建参数去掉真实 input，改用 `inputSummary` | 200 `AIExecutionPreflightDto` |
| POST | `/api/v1/accounts/{account_id}/ai-executions` | If-Match、Idempotency-Key | Body `capabilityKey,knowledgeSnapshotId,recipeVersionId,input,executionPolicy` | 202 `AIExecutionAcceptedDto` |
| GET | `/api/v1/accounts/{account_id}/ai-executions` | 无 | Query `status?,capabilityKey?,cursor?,limit?` | 200 `AIExecutionPageDto` 与 `meta.nextCursor` |
| GET | `/api/v1/accounts/{account_id}/ai-executions/{execution_id}` | 无 | Path；Query/Body 无 | 200 `AIExecutionDetailDto` |
| POST | `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/cancel` | Idempotency-Key | Path；Body 无 | 200 `AIExecutionDetailDto` |
| POST | `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/retry` | Idempotency-Key | Body `{mode:"same_snapshot"}` | 202 `AIExecutionAcceptedDto` |
| GET | `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/outputs/{output_id}` | 无 | Path；Query/Body 无 | 200 `AIExecutionOutputDto` |
| GET | `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/evidence` | 无 | Path；Query/Body 无 | 200 `AIExecutionEvidenceDto` allowlist 投影 |

Provider、credential 和 Model 写端点返回的 revision 都是新活动 revision；CapabilityRoute、Recipe 与 Template 则严格执行“保存不可变草稿/版本 → validate → activate”。所有 activate 端点必须重新解析依赖并比对 dependency snapshot hash，避免验证后到激活前发生配置漂移。兼容 CapabilityRoute 端点只是一层 service adapter，不拥有独立 Repository 写路径。

### 11.2 Provider 检查参数

`POST /system/providers/{provider_id}/checks` Body：

```json
{"stages":["network","authentication"],"force":true}
```

`POST /system/models/{model_profile_id}/capability-checks` Body：

```json
{"capabilityKeys":["script_generation"],"mode":"real_small_call","force":true}
```

`mode=contract_only` 只更新适配器契约，永远不写真实验证状态；`mode=real_small_call` 才可产生 `ai_provider_validation_runs`。

### 11.3 Preflight 与创建

Preflight Body：

```json
{
  "capabilityKey": "script_generation",
  "knowledgeSnapshotId": "knowledge_snapshot_01",
  "recipeVersionId": "recipe_version_01",
  "inputSummary": {"estimatedInputUnits": 600},
  "executionPolicy": {
    "timeoutMs": 60000,
    "allowFallback": true,
    "maxRetries": 1,
    "maxCostMicros": 50000,
    "currency": "USD"
  }
}
```

Preflight 返回依赖节点、blocking issues、repair actions、候选数量、预算估算区间和 snapshot preview hash，不返回 Prompt、凭据、模型私有参数或知识正文。

创建请求：

```http
POST /api/v1/accounts/account_01/ai-executions
If-Match: 12
Idempotency-Key: ai-exec-script-20260809-01
Content-Type: application/json

{
  "capabilityKey": "script_generation",
  "knowledgeSnapshotId": "knowledge_snapshot_01",
  "recipeVersionId": "recipe_version_01",
  "input": {
    "topic": "用三点解释一个产品方法",
    "language": "zh-CN",
    "targetDurationSeconds": 45
  },
  "executionPolicy": {
    "timeoutMs": 60000,
    "allowFallback": true,
    "maxRetries": 1,
    "maxCostMicros": 50000,
    "currency": "USD"
  }
}
```

HTTP 202：

```json
{
  "ok": true,
  "data": {
    "executionId": "ai_execution_01",
    "taskId": "task_01",
    "accountId": "account_01",
    "capabilityKey": "script_generation",
    "status": "queued",
    "snapshotHash": "64位小写十六进制摘要",
    "revision": 1,
    "createdAt": "2026-08-09T08:00:00Z"
  },
  "meta": {
    "invalidations": [
      "account:account_01:ai-executions",
      "account:account_01:tasks"
    ],
    "idempotentReplay": false
  }
}
```

### 11.4 Detail、retry、cancel 与输出

`AIExecutionDetailDto` 包含 execution/task/job 状态、进度、候选摘要、snapshot 引用与 hash、usage/cost、output 摘要、error、logId 和可用动作；不包含 credentialRef、Prompt 正文、输入正文、路径或原始 Provider 响应。

retry Body 固定为：

```json
{"mode":"same_snapshot"}
```

cancel 无 Body；重复取消或终态取消返回当前对象，不制造新事件。输出端点只允许同账号读取，并在响应 Header 使用 `Cache-Control: private, no-store`。文本/JSON 输出可返回正文供当前用户查看，但 Runtime 日志和 release evidence 只记录 output hash、大小和 schema 状态。

列表 `limit` 默认 50、范围 1-200；非法或跨账号 cursor 返回 `INVALID_SCOPED_CURSOR`。Detail、Output 与 Evidence 对其他账号的资源统一返回 404，不暴露资源是否存在。Preflight 不写业务记录、不使用 Idempotency-Key；`If-Match` 冲突返回最新账号 revision。Provider PATCH/credential、真实验证和 AIExecution 写入成功后均返回精确 `meta.invalidations`。

### 11.5 错误码与恢复

| error_code | HTTP | UI 摘要 | 恢复动作 |
| --- | ---: | --- | --- |
| `AI_EXECUTION_NOT_FOUND` | 404 | 执行不存在 | 刷新当前账号列表 |
| `AI_EXECUTION_DISABLED` | 503 | AI 执行能力未开启 | 查看系统诊断 |
| `AI_EXECUTION_INVALID` | 422 | 执行输入不完整 | 修正 fieldErrors |
| `AI_EXECUTION_STATE_CONFLICT` | 409 | 执行状态已变化 | GET 最终状态 |
| `AI_DEPENDENCY_INVALID` | 409 | AI 依赖尚未就绪 | 按 repairActions 修复 |
| `AI_PROVIDER_REAL_VALIDATION_REQUIRED` | 409 | 模型尚未通过真实小调用 | 前往 Provider 验证 |
| `AI_PROVIDER_AUTH_FAILED` | 502 | Provider 鉴权失败 | 轮换凭据后重新验证 |
| `AI_PROVIDER_RATE_LIMITED` | 429 | Provider 暂时限流 | 等待 Retry-After 或稍后 retry |
| `AI_PROVIDER_TIMEOUT` | 504 | 请求发送前超时，或 Provider 已明确返回超时失败 | 同快照 retry 或修正 Route timeout |
| `AI_PROVIDER_RESULT_UNKNOWN` | 502 | 已发送请求，但无法确认远端终态或费用 | 查看计费风险后决定是否同快照 retry |
| `AI_PROVIDER_RESPONSE_INVALID` | 502 | Provider 返回无法解析 | 查看脱敏日志并切换模型 |
| `AI_CONTENT_REJECTED` | 422 | Provider 拒绝当前内容 | 用户确认后创建新输入版本 |
| `AI_COST_UNAVAILABLE` | 409 | 无法证明本次成本上限 | 配置 pricing 或调整成本策略 |
| `AI_COST_LIMIT_EXCEEDED` | 409 | 本次预算不足或已越界 | 提高预算后新建执行 |
| `AI_ALL_CANDIDATES_FAILED` | 502 | 所有候选均失败 | 查看每个 AIJob 的安全错误 |
| `AI_USAGE_UNAVAILABLE` | 409 | Provider 未返回验收所需 usage | 更换支持 usage 的模型 |
| `CONTROLLED_FILE_CHANGED` | 409 | 授权文件已变化 | 重新授权、索引并创建新快照 |
| `CONTROLLED_FILE_REF_INVALID` | 422/503 | 文件授权无效或桥不可用 | 重新选择文件或修复 Runtime |

公共 `REVISION_CONFLICT`、`REQUEST_CONFLICT`、`TASK_ALREADY_RUNNING`、`TASK_NOT_CANCELLABLE`、`RUNTIME_NOT_READY` 和 `INTERNAL_ERROR` 继续复用 v1 契约。

依赖阻断失败信封示例：

```json
{
  "ok": false,
  "error": "AI 依赖尚未就绪，请先完成模型真实验证",
  "error_code": "AI_DEPENDENCY_INVALID",
  "log_id": "log_<safe_id>",
  "fieldErrors": [
    {
      "field": "dependencies.modelValidation",
      "code": "real_validation_required",
      "message": "当前模型尚未通过真实小调用"
    }
  ],
  "meta": {
    "dependencySnapshotId": "dependency_snapshot_<safe_id>",
    "repairActions": [
      {
        "kind": "navigate",
        "label": "前往验证模型",
        "targetPage": "ai-system",
        "targetSection": "providers",
        "targetResourceId": "model_<safe_id>"
      }
    ]
  }
}
```

失败信封只返回稳定错误码、安全中文摘要、可选 `log_id`、安全字段位置与结构化恢复动作；不得回显 credential、Prompt、用户输入、知识正文、绝对路径、Provider URL 或原始响应。

## 12. 事件、缓存与任务投影

- 新 Topic：`account:{account_id}:ai-executions`；系统真实验证继续发布 `system:ai`。
- 事件类型：`ai.execution.queued|started|job_started|job_failed|fallback_started|progress|cancelling|completed|failed`。
- 事件只含 `accountId,executionId,taskId,jobId,status,revision,progress,errorCode,logId,outputHash?`，不含输入/输出正文、Prompt、Provider 响应或路径。
- 账号切换取消旧账号订阅但不取消后台执行。切回后用 HTTP 列表与 Detail 重建。
- 配置变更递增 `aiConfigRevision`，失效依赖预览与 Recipe readiness；已创建 AIExecution 不失效。
- 知识索引/快照变更失效 preflight；已创建执行继续使用旧 snapshot。
- WebSocket 断线按 `last_event_id` 重放，随后 GET execution/task 最终态。

## 13. Desktop 交互规格

P0-H 不新增主导航 Route。系统级操作进入现有“AI 与系统设置”；账号级真实调用入口放在现有 `AccountAIRecipePanel`，名称为“运行真实调用验证”，只用于验证 Gateway，不创建 Script 业务对象。

### 13.1 Provider 与依赖图

- Provider Detail Panel 分开展示“网络、鉴权、模型发现、真实小调用”四项状态及验证时间。
- 静态契约使用“契约已接入”，真实调用使用“真实已验证”，禁止共用同一个绿色状态。
- 添加/编辑 Provider 支持完整 Base URL、凭据轮换、timeout、并发、白名单额外参数和成本策略；密钥只在输入瞬间可编辑，保存后只显示 configured 与遮罩。
- Route/Recipe 保存前显示局部 dependency issues；阻断项只给一个推荐 repair action，技术图谱进入 Detail Panel。
- Provider 列表 loading 保留壳层与上次安全摘要；empty 只显示“添加 Provider”；error 显示中文原因、`logId`、重试和系统诊断，不渲染伪健康数字。
- 四阶段检查以 RuntimeTask 驱动，running 显示阶段与取消；failed/partial 显示安全错误和重试；completed 只在对应 revision 的真实证据有效时显示绿色状态。
- CapabilityRoute 编辑器分为 revision 列表、草稿详情、依赖检查和激活确认；用户能查看自己配置的 Prompt、候选、超时、并发与成本摘要，并能从旧 revision 创建新草稿，禁止把 revision 号当成唯一可读名称。
- 知识文件来源覆盖选择中、索引中、空、成功、stale、缺失、授权撤销与失败恢复；页面只显示 displayName/rootRef 摘要/hash 前缀，不显示绝对路径。

### 13.2 AIExecution 状态矩阵

| 页面状态 | 主区域 | 主动作 | Detail Panel |
| --- | --- | --- | --- |
| loading | 局部 skeleton，不清空已知账号标题 | 禁用 | 保留上次选中项并标记刷新中 |
| first_use | 一句说明“尚无真实执行记录” | 运行真实调用验证 | 关闭 |
| dependency_blocked | 缺失依赖摘要 | 唯一 repair action | 节点、问题、证据引用 |
| queued/running | 阶段、真实进度、不确定进度说明 | 取消 | task/job、候选、耗时、当前阶段 |
| normal completed | 结果正文/结构化预览、usage/cost | 复制结果或按最新配置重跑 | snapshot、模型摘要、output hash |
| error | 中文摘要、影响对象、推荐修复 | retry 或 repair 二选一 | AIJob 历史、安全错误、logId |
| cancelled | “已取消，未生成可用输出” | 按原快照重试 | 取消方式与终态 |
| restricted | 许可证/Runtime/Provider 不可用 | 前往修复 | 受限原因 |

输出正文可以在当前账号界面查看，但不会出现在 Toast、日志、事件、浏览器持久缓存或 evidence。技术详情默认折叠。

### 13.3 PC 布局与主题

- 宽屏：执行列表与 360px Detail Panel 并排；系统设置保持现有低高度标签。
- 约 1180px：Detail Panel 改覆盖抽屉，列表隐藏 Provider 摘要但保留状态、usage/cost 和动作。
- 960px：仍为 PC Sidebar；执行详情使用全高覆盖抽屉，主动作始终可见，不产生页面级横向滚动。
- Light/Dark 全部使用现有 CSS Variables；状态同时用图标、文字和颜色；Reduced Motion 关闭循环动画。
- 所有请求只经 `app/runtime-client`；错误进入稳定卡片并记录 Runtime client 安全日志，不允许组件直接 fetch。

## 14. 配置总线与 redaction

### 14.1 新配置键

| 配置键 | 范围 | 约束 |
| --- | --- | --- |
| `ai.execution.enabled` | system | 默认 false，验收前显式开启 |
| `ai.execution.defaultTimeoutSeconds` | system | 正整数，不超过 task 最大 timeout |
| `ai.execution.maxRetries` | system | 0-3 |
| `ai.execution.retryBaseDelayMs` | system | 100-10000 |
| `ai.execution.retryMaxDelayMs` | system | 不小于 base |
| `ai.execution.globalMaxConcurrency` | system | 正整数 |
| `ai.execution.defaultMaxCostMicros` | system | 非负整数 |
| `ai.execution.outputMaxBytes` | system | 正整数 |
| `ai.providerValidation.maxOutputUnits` | system | 1-32 |
| `knowledge.controlledFiles.maxBytes` | system | 正整数 |
| `knowledge.controlledFiles.grantRetentionHours` | system | 正整数 |
| `ai.evidence.retentionDays` | system | 正整数 |

页面、Provider adapter 和脚本不得保存本地默认副本。Route/Recipe 只能保存经配置总线校验的覆盖。

### 14.2 redaction 规则

`redaction` 必须在 Provider 异常转换、结构化日志、事件、任务 snapshot、API DTO、evidence export 和 release manifest 七个出口执行 allowlist：

- 禁止字段：`credential,credentialRef,apiKey,authorization,headers,prompt,input,rawRequest,rawResponse,absolutePath,userProfile,cookie,token`。
- 禁止值模式：Windows/UNC/Unix 绝对路径、`Bearer `、常见 API Key/JWT 形态、URL userinfo、完整邮箱和 TikTok handle。
- 可输出：稳定资源 ID 的哈希、adapter type、capability key、revision、duration、usage、cost、状态、错误码、logId、response/output hash。
- Provider 原始错误先在适配器内转成安全枚举；`log.exception` 只记录受控异常，不串入外部响应文本。
- redaction 失败会阻止 evidence 写入和 production manifest 创建，错误码 `AI_EVIDENCE_REDACTION_FAILED`。

## 15. 精确实施文件地图

任何新增文件不得超过 500 行；Page/Component 目标不超过 300 行，service/repository 目标不超过 400 行。超过时必须按本地图职责拆分，禁止把状态、Provider 协议、持久化和样式堆进同一文件。

### 15.1 Runtime 与迁移

| 文件 | 职责 |
| --- | --- |
| `apps/py-runtime/alembic/versions/0023_p0h_real_ai_execution.py` | 加法表、列、revision 回填、Schema 校验、数据承载 downgrade 拒绝 |
| `apps/py-runtime/src/domain/models/ai_execution.py` | AIExecution 与 AIExecutionJob |
| `apps/py-runtime/src/domain/models/ai_execution_snapshot.py` | snapshot、candidate、dependency snapshot |
| `apps/py-runtime/src/domain/models/ai_execution_evidence.py` | usage、output、error、provider validation |
| `apps/py-runtime/src/domain/models/account_asset.py` | account_assets、knowledge_source_assets、knowledge chunks |
| `apps/py-runtime/src/domain/models/ai_configuration_v1.py` | Provider/Model/Route 不可变 revision 与活动指针关系 |
| `apps/py-runtime/src/repositories/ai_configuration_v1/revisions.py` | 配置 revision 创建、读取与历史保留 |
| `apps/py-runtime/src/repositories/ai_configuration_v1/providers.py` | Provider/Model 活动 revision 原子切换 |
| `apps/py-runtime/src/repositories/ai_configuration_v1/routes.py` | Route draft/validate/activate 持久化 |
| `apps/py-runtime/src/repositories/ai_execution_v1/__init__.py` | 仓储导出 |
| `apps/py-runtime/src/repositories/ai_execution_v1/facade.py` | 事务与聚合入口 |
| `apps/py-runtime/src/repositories/ai_execution_v1/executions.py` | execution/job 状态与账号查询 |
| `apps/py-runtime/src/repositories/ai_execution_v1/snapshots.py` | 不可变快照和候选 |
| `apps/py-runtime/src/repositories/ai_execution_v1/evidence.py` | usage/output/error/validation 证据 |
| `apps/py-runtime/src/repositories/ai_execution_v1/assets.py` | account asset、source 关联与 chunk |
| `apps/py-runtime/src/services/ai_execution_v1/types.py` | 内部值对象与安全枚举 |
| `apps/py-runtime/src/services/ai_execution_v1/provider_ports.py` | AIProviderPort 与取消句柄 |
| `apps/py-runtime/src/services/ai_execution_v1/provider_registry.py` | adapter 注册，不含业务路由 |
| `apps/py-runtime/src/services/ai_execution_v1/openai_compatible.py` | 首条真实文本协议实现 |
| `apps/py-runtime/src/services/ai_execution_v1/dependency_graph.py` | 依赖解析、issues、repair actions |
| `apps/py-runtime/src/services/ai_execution_v1/snapshot_builder.py` | 执行快照、候选与 hash |
| `apps/py-runtime/src/services/ai_execution_v1/policies.py` | timeout/retry/fallback/concurrency/cost |
| `apps/py-runtime/src/services/ai_execution_v1/gateway.py` | 创建、preflight、retry/cancel 编排 |
| `apps/py-runtime/src/services/ai_execution_v1/executor.py` | Provider 调用与结果归一 |
| `apps/py-runtime/src/services/ai_execution_v1/output_store.py` | 账号受控输入/输出原子存储与对账 |
| `apps/py-runtime/src/services/ai_execution_v1/redaction.py` | 日志/API/evidence allowlist |
| `apps/py-runtime/src/services/ai_execution_v1/task_submission.py` | `ai.execution` 任务创建 |
| `apps/py-runtime/src/services/ai_execution_v1/task_handlers.py` | handler 与提交协调 |
| `apps/py-runtime/src/services/ai_execution_v1/task_registration.py` | handler 注册与恢复策略 |
| `apps/py-runtime/src/services/ai_execution_v1/presentation.py` | DTO 投影，不读取秘密 |
| `apps/py-runtime/src/services/ai_execution_v1/legacy_adapter.py` | AITextGenerationService 兼容桥 |
| `apps/py-runtime/src/services/ai_configuration_v1/providers.py` | Provider/credential/Model 写入创建不可变 revision |
| `apps/py-runtime/src/services/ai_configuration_v1/routes.py` | Route revision lifecycle 与旧端点适配 |
| `apps/py-runtime/src/services/ai_configuration_v1/route_validation.py` | 依赖 snapshot 与激活前 hash 复检 |
| `apps/py-runtime/src/services/knowledge/controlled_files.py` | Tauri grant 解析、rootRef 与文件身份复检 |
| `apps/py-runtime/src/services/knowledge/file_extractors.py` | text/Markdown/JSON 派生 chunk |
| `apps/py-runtime/src/app/config.py` | 校验并加载受控文件注册表启动配置，不输出路径原文 |
| `apps/py-runtime/src/schemas/v1/ai_executions.py` | 请求、Detail、Output、Evidence DTO |
| `apps/py-runtime/src/schemas/v1/ai_provider_validation.py` | H1 check/validation DTO |
| `apps/py-runtime/src/api/routes/v1/account_ai_executions.py` | 账号 execution HTTP |
| `apps/py-runtime/src/api/routes/v1/system_ai_dependencies.py` | 系统依赖预览与 Provider 验证扩展 |
| `apps/py-runtime/src/api/routes/v1/system_providers.py` | Provider revision 与真实验证入口 |
| `apps/py-runtime/src/api/routes/v1/system_models.py` | Model revision 写入 |
| `apps/py-runtime/src/api/routes/v1/system_capability_routes.py` | Route revision list/create/validate/activate 与兼容 adapter |
| `apps/py-runtime/src/app/repository_assembly.py` | 新仓储装配 |
| `apps/py-runtime/src/app/container.py` | Gateway、Provider、OutputStore 装配 |
| `apps/py-runtime/src/app/route_registry.py` | 注册 P0-H v1 routes |
| `apps/py-runtime/src/services/ai_text_generation_service.py` | 仅改为调用 legacy_adapter，不保留旧配置解析 |

### 15.2 Tauri 与 Desktop

| 文件 | 职责 |
| --- | --- |
| `apps/desktop/src-tauri/src/controlled_files/mod.rs` | 模块导出 |
| `apps/desktop/src-tauri/src/controlled_files/commands.rs` | 选择、描述、撤销 fileRef |
| `apps/desktop/src-tauri/src/controlled_files/registry.rs` | 私有 grant 注册表与原子写 |
| `apps/desktop/src-tauri/src/controlled_files/validation.rs` | root 包含、链接逃逸、身份与大小检查 |
| `apps/desktop/src-tauri/src/controlled_files/types.rs` | DTO/错误类型 |
| `apps/desktop/src-tauri/src/controlled_files/logging.rs` | 不含路径的安全日志 |
| `apps/desktop/src-tauri/src/main.rs` | 注册命令和状态 |
| `apps/desktop/src-tauri/src/runtime_supervisor/process.rs` | 只向受管 Runtime 注入受控文件注册表路径 |
| `apps/desktop/src/app/controlled-files/client.ts` | Tauri bridge 客户端 |
| `apps/desktop/src/app/controlled-files/types.ts` | fileRef DTO |
| `apps/desktop/src/app/runtime-client/ai-executions.ts` | Runtime API 调用 |
| `apps/desktop/src/types/runtime/ai-executions.ts` | v1 DTO 与运行时校验类型 |
| `apps/desktop/src/modules/ai-executions/ai-execution-store.ts` | account-scoped 缓存与迟到响应隔离 |
| `apps/desktop/src/modules/ai-executions/ai-execution-operations.ts` | preflight/create/cancel/retry |
| `apps/desktop/src/modules/ai-executions/ai-execution-helpers.ts` | 状态、usage/cost、repair 映射 |
| `apps/desktop/src/modules/ai-executions/components/AIExecutionLauncher.vue` | 真实调用验证入口 |
| `apps/desktop/src/modules/ai-executions/components/AIExecutionStatePanel.vue` | loading/empty/error/受限状态 |
| `apps/desktop/src/modules/ai-executions/components/AIExecutionDetailPanel.vue` | snapshot/job/log/output 详情 |
| `apps/desktop/src/modules/ai-executions/styles/ai-execution.css` | 宽屏、紧凑、Light/Dark |
| `apps/desktop/src/modules/system/ai-config/components/ProviderWorkspace.vue` | 四阶段真实验证展示 |
| `apps/desktop/src/modules/system/ai-config/components/CapabilityRouteEditor.vue` | dependency issues/repair actions |
| `apps/desktop/src/modules/ai-recipes/components/AccountAIRecipePanel.vue` | 挂载 Launcher，不创建新主路由 |
| `apps/desktop/src/modules/knowledge/KnowledgeSourcesPanel.vue` | rootRef 文件选择、索引恢复与 Asset 证据 |
| `apps/desktop/src/pages/settings/ai-system/AISystemSettingsPage.vue` | 在现有系统页挂载 Provider 验证、Route revision 与执行详情，不新增 Route |
| `apps/desktop/src/pages/settings/ai-system/use-ai-system-page.ts` | 页面级加载、错误、重试、取消、失效刷新编排 |
| `apps/desktop/src/pages/strategy-knowledge/AccountStrategyKnowledgePage.vue` | 在现有账号页挂载受控知识来源与真实执行验证入口 |
| `apps/desktop/src/pages/strategy-knowledge/use-controlled-knowledge-source.ts` | 把 fileRef、索引任务和恢复状态移出 Page，避免页面继续膨胀 |

### 15.3 测试、证据与唯一文档

| 文件 | 验证责任 |
| --- | --- |
| `tests/runtime/test_p0_h_migration.py` | 0023、回填、约束、降级拒绝 |
| `tests/runtime/test_p0_h_provider_real_validation.py` | H1 成功/鉴权/响应无效/usage 缺失/脱敏 |
| `tests/runtime/test_p0_h_dependency_graph.py` | H2 revision、issue/action、历史不变 |
| `tests/runtime/test_p0_h_controlled_file_ingestion.py` | H3 rootRef、逃逸、变化、失败恢复、不复制 |
| `tests/runtime/test_p0_h_ai_execution_gateway.py` | H4 成功、retry、fallback、cost、output |
| `tests/runtime/test_p0_h_ai_execution_recovery.py` | timeout、cancel、重启、post-send result_unknown、禁止自动重发、提交竞态 |
| `tests/runtime/test_p0_h_ai_execution_isolation.py` | account_id、游标、缓存/Topic 隔离 |
| `tests/runtime/test_p0_h_ai_execution_redaction.py` | credential/Prompt/路径/用户资料负向扫描 |
| `tests/contracts/test_p0_h_ai_execution_api.py` | 地址、方法、参数、信封、错误码、接口文档库存 |
| `apps/desktop/tests/p0/p0-h-provider-validation.spec.ts` | Provider 四阶段 UI |
| `apps/desktop/tests/p0/p0-h-ai-execution.spec.ts` | 状态矩阵、repair、retry/cancel、账号切换 |
| `apps/desktop/tests/p0/p0-h-controlled-file.spec.ts` | fileRef 选择与恢复反馈 |
| `apps/desktop/tests/e2e/support/p0-h-provider-server.py` | 自动化受控 Provider，明确标记非真实验收 |
| `apps/desktop/tests/e2e/p0-h-ai-execution.e2e.ts` | 真实 Runtime + 受控 Provider 的确定性链 |
| `tests/manual/p0-h-real-provider-evidence.ps1` | 导出并校验人工真实证据，不读取 Key |
| `tests/packaging/test_release_manifest_v2.py` | AI 人工证据和制品哈希绑定策略 |
| `scripts/release-evidence-policy.mjs` | production 需要 P0-H 人工证据 |
| `scripts/p0-h-real-provider-evidence.mjs` | 严格 allowlist、Runtime evidence 转换、四制品绑定与 release 包装；拆分以保持发布脚本不超过 500 行 |
| `scripts/attach-p0-h-release-evidence.mjs` | 在不重建、不改变已验收制品的前提下，把 H5 人工证据原子附加到现有 Manifest |
| `scripts/build-windows-release.mjs` | 接收 `--target-ai-evidence`，不自动外呼 |
| `docs/api/v1/ai-executions.md` | Runtime API 与 Desktop 调用的唯一真源 |
| `docs/api/v1/README.md` | 仅登记索引与库存 |
| `docs/api/v1/ai-system.md` | 仅追加真实验证差异和交叉引用 |
| `docs/api/v1/account-knowledge.md` | 仅追加 rootRef file bridge 与 Asset 字段 |
| `docs/api/v1/tasks-and-events.md` | 仅追加 `ai.execution` 任务类型 |

## 16. H5 两层验收证据

### 16.1 自动化证据

受控 Provider 必须覆盖：

1. 成功返回、reported usage、输出 Schema 与 output hash。
2. 网络失败、鉴权失败、429、5xx、无效响应和 usage 缺失。
3. 总 timeout、队列 timeout、运行中 cancel、取消与提交竞态，以及 post-send 断线不自动 retry/fallback。
4. retry 次数、fallback 顺序、每次成本累计和预算阻断。
5. 账号 A 的 execution/job/output/事件/游标对账号 B 不可见。
6. 配置、Prompt、Recipe、知识修改后旧 snapshot/hash/输出保持不变。
7. 日志、事件、任务、API、evidence 和 manifest 的 redaction 扫描。

自动化受控 Provider 的 evidence 必须写 `providerEvidenceKind=controlled_contract`，release verifier 禁止把它当作 `real_provider`。

### 16.2 人工真实 OpenAI-compatible 证据

用户在目标机器通过 UI 人工输入 Key，完成模型发现、真实小调用和完整 AIExecution。导出的 allowlist JSON 只包含：

```json
{
  "schemaVersion": 1,
  "evidenceKind": "p0h_openai_compatible_real_execution",
  "appVersion": "0.5.0",
  "artifactBindings": {
    "desktop": "SHA-256",
    "sidecar": "SHA-256",
    "installer": "SHA-256",
    "portable": "SHA-256"
  },
  "provider": {
    "adapterType": "openai_compatible",
    "providerRefHash": "SHA-256",
    "modelIdHash": "SHA-256",
    "validationRunHash": "SHA-256"
  },
  "execution": {
    "capabilityKey": "script_generation",
    "finalStatus": "succeeded",
    "snapshotHash": "SHA-256",
    "responseIdHash": "SHA-256",
    "outputHash": "SHA-256",
    "durationMs": 1234,
    "usage": {"inputUnits": 1, "outputUnits": 1, "totalUnits": 2},
    "cost": {"micros": 1, "currency": "USD", "source": "reported"},
    "responseSummary": {"outputType": "text", "schemaValid": true, "byteSize": 1}
  },
  "redaction": {"passed": true, "schemaAllowlistPassed": true}
}
```

示例数字只表达 JSON 类型，不作为业务或验收结果。真实 evidence 必须来自当前执行。文件中禁止 Key、credentialRef、Provider/模型明文、Prompt 正文、输入/输出正文、绝对路径、URL、账号 handle、用户资料、Runtime Session、Cookie 和原始 response。

### 16.3 H5 真实验收顺序

1. 从待验收 0.5.0 安装包或 portable 制品首启，记录 Desktop、sidecar、installer、portable 与 release manifest 的 SHA-256；禁止复用开发服务或旧证据。
2. 选择一个真实账号工作区，在系统设置创建 OpenAI-compatible Provider，由用户在 UI 人工输入 Key；确认 API、日志、事件和诊断均不返回 Key 或 Base URL 原文。
3. 依次完成网络、鉴权、模型发现和 `real_small_call`，确认四个 validation stage、reported usage、duration 与 response hash 均绑定当前 Provider/Model revision。
4. 创建 Prompt version 与 CapabilityRoute draft，配置已验证模型、timeout、retry、fallback、并发和成本策略；validate 无 blocking issue 后 activate，并核对 active revision 与 dependency snapshot hash。
5. 在当前账号创建并激活 AccountAIRecipe version；用系统文件选择器选择授权根内真实文本文件，生成 AccountAsset、KnowledgeSource、索引任务与 KnowledgeSnapshot，证明源文件未被复制。
6. 执行 `script_generation` preflight，核对 Recipe、Route、Prompt、定位、知识、Provider/Model、usage/cost policy 全部可追溯且不返回正文；随后创建真实 AIExecution。
7. 等待 AIJob 成功，核对真实输出、reported usage、cost source、duration、snapshot hash、output hash、任务终态、日志引用与账号隔离；输出正文只在当前账号详情可见。
8. 另行执行受控的运行中 cancel、可安全 retry、fallback 和 post-send result_unknown 场景；确认取消到达 Runtime/Provider、自动重发受限、失败可见且可能费用有明确提示。
9. 修改 Prompt、Route 或知识后按原 snapshot retry，证明旧 hash/输出不变；再按最新配置新建 execution，证明形成新 snapshot 且 UI 能展示差异。
10. 通过人工 evidence 脚本导出 allowlist JSON，完成七出口 redaction 扫描，并验证 artifactBindings 与当前 Manifest 完全一致；任一哈希不符、usage 非 reported、cost unavailable 或敏感字段命中都使 H5 失败。

## 17. 阶段验证命令

实施只在每个 H 阶段完成后集中运行一次“阶段相关测试 + 一条主链回归”，最终再跑全量：

```powershell
# H1
venv\Scripts\python.exe -m pytest -q tests/runtime/test_p0_h_provider_real_validation.py tests/contracts/test_p0_h_ai_execution_api.py

# H2
venv\Scripts\python.exe -m pytest -q tests/runtime/test_p0_h_dependency_graph.py tests/runtime/test_p0_h_migration.py

# H3
venv\Scripts\python.exe -m pytest -q tests/runtime/test_p0_h_controlled_file_ingestion.py tests/runtime/test_p0_c_knowledge_index_contract.py
cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml controlled_files

# H4
venv\Scripts\python.exe -m pytest -q tests/runtime/test_p0_h_ai_execution_gateway.py tests/runtime/test_p0_h_ai_execution_recovery.py tests/runtime/test_p0_h_ai_execution_isolation.py tests/runtime/test_p0_h_ai_execution_redaction.py
npm --prefix apps/desktop run test -- p0-h-provider-validation.spec.ts p0-h-ai-execution.spec.ts p0-h-controlled-file.spec.ts
npm --prefix apps/desktop run typecheck

# 自动 P0-H E2E；只能证明 controlled_contract
npm --prefix apps/desktop exec -- playwright test tests/e2e/p0-h-ai-execution.e2e.ts

# 最终全量与桌面/Rust
npm run test:runtime
npm --prefix apps/desktop run test
npm --prefix apps/desktop run typecheck
cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml

# 人工真实证据校验和 test release
powershell -NoProfile -ExecutionPolicy Bypass -File tests/manual/p0-h-real-provider-evidence.ps1 -EvidencePath <脱敏证据文件>
node scripts/build-windows-release.mjs --channel test --target-ai-evidence <脱敏证据文件>
node scripts/verify-release-manifest.mjs --manifest dist/releases/0.5.0/windows-x86_64/release-manifest.json
```

H5 只有在自动证据通过、人工 evidence `evidenceKind` 正确、四个 artifactBindings 与 Manifest 一致、redaction 通过时才通过。受控 Provider 无论测试数量多少都不能替代人工证据。

人工 evidence 的 `usage` 必须为 Provider reported；`cost.source` 允许 `reported`，或在 Provider 不返回金额时使用绑定 `pricingRevision` 的 `estimated`。`cost.source=unavailable` 不能通过 H5。

## 18. rollback 与失败恢复

| 失败点 | rollback | 数据处理 |
| --- | --- | --- |
| 0023 升级失败 | 写门开放前恢复迁移前 DB/WAL/SHM 备份 | 不 stamp、不猜测补列 |
| H1 Provider 实测失败 | Provider/Model 保留配置但状态 failed/partial | 不删除凭据；用户轮换或重试 |
| H2 依赖图错误 | 禁止激活对应 revision，回到上一 active revision | 不改写历史 snapshot |
| H3 文件桥失败 | 关闭 `knowledge.controlledFiles`，file 来源失败封闭 | 保留 Asset/Source/task/log；不删除源文件 |
| H4 Gateway 失败 | 关闭 `ai.execution.enabled` 和创建入口 | 已有 execution/output 只读；不恢复 legacy 直连 |
| Provider 调用中断 | 发送前标记 interrupted；发送后无法证明终态则标记 result_unknown | 不自动重发；展示计费风险后才允许用户发起 same_snapshot retry |
| 0.5.0 release 失败 | 不覆盖 `current.json` | 保留失败 evidence 供诊断，不提升 production |

数据库 downgrade 仅在所有 P0-H 表无数据且没有新 revision 引用时允许；存在数据时明确拒绝。rollback 关闭写入口，不物理删除表，不删除用户文件，不把 `AITextGenerationService` 切回旧配置真源。

## 19. 验收矩阵与完成定义

| 验收项 | 通过证据 | 不通过示例 |
| --- | --- | --- |
| H1 | OpenAI-compatible 四阶段真实验证，usage 存在 | 仅 `/models` 成功或静态 probe |
| H2 | revision/依赖 snapshot 不可变，issues/actions 可执行 | 配置修改后历史 execution 漂移 |
| H3 | rootRef 文件真实读取、Asset/Source/chunk、变化恢复、不复制 | HTTP 传绝对路径或复制源文件 |
| H4 | AIExecution/AIJob 成功、失败、timeout、retry、cancel、fallback、usage/cost | Desktop 直连或旧服务旁路 |
| 隔离 | 账号 A 的所有资源对 B 返回 404/空范围 | 仅 UI 过滤 |
| redaction | 七个出口负向扫描与人工 evidence allowlist 通过 | Key、Prompt、路径、用户资料任一泄漏 |
| UI | loading/empty/normal/error/retry/cancel/详情、宽屏/紧凑、双主题 | 静默等待、Console-only 错误、页面溢出 |
| H5 | 同一 0.5.0 制品的自动 + 人工真实 evidence | mock 冒充真实 Provider |

规格批准不等于 0.5.0 完成。只有实现、自动化、目标机器人工真实证据、全量测试、release manifest 和回退验证全部通过后，P0-H 才能标记完成；八个正式业务 Route 仍保持 pending，直到 P0-I 各纵切片独立通过。
