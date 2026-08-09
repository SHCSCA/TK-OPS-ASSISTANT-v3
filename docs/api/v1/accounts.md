# 账号 API v1

本文件是账号生命周期、工作区上下文、真实执行连接和监督登录的 HTTP 契约真源。当前实现共注册 22 个账号相关 HTTP 接口；执行环境本身的 8 个接口见 [execution-environments.md](execution-environments.md)。

所有接口均遵循 [README.md](README.md) 的本机 Host、Origin、Runtime Session、active 许可证、统一信封和请求关联规则。公共错误见 [errors.md](errors.md)，持久任务的查询、取消和事件协议见 [tasks-and-events.md](tasks-and-events.md)。

## 1. 共同约束

### 1.1 账号范围与状态

- `account_id` 必须匹配 `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`。冒号只允许出现在请求关联标识和幂等键中，不属于资源 ID 语法。
- `0019_p0_account_vertical_chain` 会在任何账号默认对象或状态回填前校验全部历史 `accounts.id`。旧正式创建链生成的 UUID 可直接兼容；手工导入或直写数据库产生的非法 ID 会令迁移以 `P0C_MIGRATION_VALIDATION_FAILED` 失败封闭，Runtime 不会自动重映射主键。应保留迁移前备份，修复 ID 及其真实引用后再重试。
- 除账号列表、创建、读取详情、读取健康和恢复外，账号 Path 默认拒绝 `archived`，返回 `ACCOUNT_ARCHIVED`。
- `GET /{account_id}`、`GET /{account_id}/health` 与 `POST /{account_id}/restore` 可解析已归档账号；恢复仍要求账号当前确为 `archived`。
- 账号状态固定为 `draft | unbound | ready | attention | archived`。状态由 Runtime 的向导完成度、真实连接、知识和 AI readiness 共同计算，Body 不能直接指定状态。
- 归档恢复允许 `archived -> draft`：未完成六步向导的账号复检后回到 `draft`；已完成向导的账号才根据真实 readiness 进入 `unbound | ready | attention`。
- 当前平台只允许 `tiktok`；不接受其他平台占位值。

### 1.2 修订与幂等

- 需要 `If-Match` 的接口接受正整数或带双引号的正整数。缺少 Header 返回 `REVISION_CONFLICT`（412），格式错误返回 `REQUEST_VALIDATION_FAILED`（422），修订落后返回 `REVISION_CONFLICT`（412，可能含 `meta.currentRevision`）。
- 普通持久幂等接口使用 `Idempotency-Key`，格式与 README 的公共 Header 规则一致。相同作用域、操作名、键和请求摘要重放原响应，并令 `meta.idempotentReplay=true`；同键不同请求返回 `REQUEST_CONFLICT`（409）。
- 普通写幂等记录的保留时间来自 `api.mutationIdempotencyTtlSeconds`；命中键时会按记录精确清理过期项，Runtime 持久任务恢复后还会分批清理全局过期记录。任务创建使用任务内核自己的作用域幂等，冲突码为 `TASK_IDEMPOTENCY_CONFLICT`。
- 未声明幂等键的写接口不得自动重放；未知结果应先 GET 对账。

### 1.3 主要 DTO

`AccountDto`：

| 字段 | 类型与语义 |
| --- | --- |
| `id` | Runtime 生成的稳定账号 ID |
| `name` | 1 至 128 字符 |
| `username` | `null` 或规范化 TikTok 标识，不含前导 `@` |
| `platform` | 固定 `tiktok` |
| `status` | `draft | unbound | ready | attention | archived` |
| `readiness` | `AccountReadinessDto` |
| `positioningSummary` | 当前激活定位的中性摘要；未配置时为 `null` |
| `lastUsedAt` | 最近一次成功激活账号工作区的 UTC 时间；从未激活时为 `null` |
| `wizardCompletedAt` | UTC 时间或 `null` |
| `revision` | 账号聚合正整数修订 |

`AccountReadinessDto` 包含 `connection`、`knowledge`、`ai`、`overall`、`checkedAt` 和 `suggestedAction`。三个子项包含 `status`、`label`、`errorCode`、`logId`、`checkedAt` 和 `suggestedAction`；`overall` 为 `ready | attention | blocked`。AI readiness 在 P0-E 接管前保持失败封闭，不会因占位配置变为 ready。

`ConnectionDto`：

| 字段 | 类型与语义 |
| --- | --- |
| `accountId` | 当前账号 |
| `authStatus` | `unknown | required | valid | expired | failed` |
| `healthStatus` | `unknown | checking | ready | attention | failed` |
| `deviceWorkspace` | `{id,name,status}` 或 `null` |
| `browserInstance` | `{id,name,status,lastCheckedAt}` 或 `null` |
| `executionBinding` | `{id,status,deviceWorkspaceId,browserInstanceId}` 或 `null` |
| `lastCheck` | `{status,checkedAt,errorCode,logId}` 或 `null` |
| `revision` | 当前账号聚合修订 |

`ConnectionCandidatesDto` 为 `{items: ConnectionCandidateDto[]}`。每个候选项包含 `environmentId`、`eligibilityRevision` 以及同一账号下完整一致且当前合格的 `deviceWorkspace`、`browserInstance`、`executionBinding` 摘要。无合格候选时返回空数组，不创建或猜测绑定。

`TaskAcceptedDto` 为 `{taskId,scope,accountId,taskType,status,cancellable,createdAt}`；本文件创建的任务均为 `scope=account`、`status=queued`。

## 2. 接口总览

| 方法 | 地址 | `If-Match` | `Idempotency-Key` | 成功 |
| --- | --- | --- | --- | ---: |
| `GET` | `/api/v1/accounts` | 无 | 无 | 200 |
| `POST` | `/api/v1/accounts` | 无 | 必填 | 201 |
| `GET` | `/api/v1/accounts/{account_id}` | 无 | 无 | 200 |
| `PATCH` | `/api/v1/accounts/{account_id}` | 必填 | 无 | 200 |
| `GET` | `/api/v1/accounts/{account_id}/workspace-context` | 无 | 无 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/workspace-activation` | 必填 | 必填 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/complete-wizard` | 必填 | 必填 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/copy-config` | 必填 | 必填 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/archive` | 必填 | 必填 | 202 |
| `POST` | `/api/v1/accounts/{account_id}/restore` | 必填 | 必填 | 202 |
| `GET` | `/api/v1/accounts/{account_id}/health` | 无 | 无 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/health-checks` | 无 | 必填 | 202 |
| `GET` | `/api/v1/accounts/{account_id}/connection` | 无 | 无 | 200 |
| `GET` | `/api/v1/accounts/{account_id}/connection/candidates` | 无 | 无 | 200 |
| `PUT` | `/api/v1/accounts/{account_id}/connection/binding` | 必填 | 必填 | 200 |
| `DELETE` | `/api/v1/accounts/{account_id}/connection/binding` | 必填 | 必填 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/connection/checks` | 无 | 必填 | 202 |
| `POST` | `/api/v1/accounts/{account_id}/connection/login-sessions` | 无 | 必填 | 202 |
| `GET` | `/api/v1/accounts/{account_id}/connection/login-sessions/{session_id}` | 无 | 无 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/connection/login-sessions/{session_id}/probe` | 无 | 必填 | 202 |
| `DELETE` | `/api/v1/accounts/{account_id}/connection/login-sessions/{session_id}` | 无 | 必填 | 200 |
| `DELETE` | `/api/v1/accounts/{account_id}/connection/session` | 无 | 必填 | 202 |

## 3. 账号读取与生命周期

### GET `/api/v1/accounts`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path、Body：无。
- Query：`q` 可选且最长 128；`status` 可选，取五种账号状态；`cursor` 可选且最长 2048；`limit` 可选。默认 50、当前最大 200，均由配置总线控制。游标绑定系统账号列表、规范化筛选摘要和排序位置，改变 `q` / `status` 或挪用其他资源游标会返回 `invalid_scoped_cursor`。
- 返回：`data=AccountListDto{items: AccountDto[], totalKnown: number|null}`，`meta.nextCursor` 为下一页不透明游标或 `null`。
- 错误与恢复：`REQUEST_VALIDATION_FAILED`（筛选、游标或分页无效）应修正参数；`RUNTIME_NOT_READY` / `INTERNAL_ERROR` 应保留 `log_id` 后重试只读。
- Revision / 幂等：只读，不使用 `If-Match` 或幂等键。
- Invalidations / 事件：无。
- legacy：`GET /api/accounts` 的分组、旧状态和发布摘要语义不同，不是本接口映射；生产模式不注册该未迁移路由。

### POST `/api/v1/accounts`

- Headers：`Authorization`、`Idempotency-Key`、`Content-Type: application/json` 必填；`X-Operation-ID` 可选。
- Path、Query：无。
- Body：`{name, username?, platform}`；`name` 去除首尾空白后非空，`username` 为 2 至 64 位字母、数字、点或下划线，`platform` 必须为 `tiktok`。
- 返回：HTTP 201，`data=AccountDto`；新账号为真实 `draft`，同时建立一对一空知识库和保守发布默认值；`meta={revision,invalidations,idempotentReplay}`。
- 错误与恢复：`ACCOUNT_PLATFORM_UNSUPPORTED`、`ACCOUNT_USERNAME_INVALID`、`REQUEST_VALIDATION_FAILED` 应修正输入；`REQUEST_CONFLICT` 应换用与新业务意图匹配的幂等键。
- Revision / 幂等：不使用 `If-Match`；普通写幂等。
- Invalidations / 事件：失效 `accounts:list`；原子写入 `account.created` 到 `account:{account_id}:workspace`。
- legacy：旧 `POST /api/accounts` 可直接指定旧状态及扩展字段，不映射；生产模式不注册。

### GET `/api/v1/accounts/{account_id}`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`；可读取已归档账号。Query、Body：无。
- 返回：`data=AccountDto`，无 `meta`。
- 错误与恢复：`ACCOUNT_NOT_FOUND` 时刷新列表；`REQUEST_VALIDATION_FAILED` 时修正 ID；服务未就绪或内部错误按 `log_id` 诊断。
- Revision / 幂等：只读；DTO 的 `revision` 是后续写入基线。
- Invalidations / 事件：无。
- legacy：旧详情 DTO 含旧发布统计，不是一对一映射；生产模式不注册旧账号路由。

### PATCH `/api/v1/accounts/{account_id}`

- Headers：`Authorization`、`If-Match`、`Content-Type: application/json` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。
- Body：至少一个 `{name?, username?, avatarAssetRef?}`；`avatarAssetRef` 仅接受稳定受控资产引用或受控 `asset://` 引用。字段设为 `null` 的规则以 Schema 为准，`name` 不能设空。
- 返回：`data=AccountDto`，`meta={revision,invalidations}`。当前公开 `AccountDto` 不回显头像引用。
- 错误与恢复：`ACCOUNT_NOT_FOUND`、`ACCOUNT_ARCHIVED`、`ACCOUNT_USERNAME_INVALID`、`REQUEST_VALIDATION_FAILED`；`REVISION_CONFLICT` 后先 GET 再合并。
- Revision / 幂等：要求账号修订；不使用幂等键，未知结果必须 GET 对账。
- Invalidations / 事件：失效 `account:{id}:detail`、`account:{id}:workspace`；原子写入 `account.updated`。
- legacy：旧 PATCH 的字段和状态修改能力更宽，不映射；生产模式不注册。

### GET `/api/v1/accounts/{account_id}/workspace-context`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：`include` 可重复提交 `readiness | taskSummary | navigation`，P0-C 为前向兼容提示，响应仍保持完整固定形状。Body：无。
- 返回：`AccountWorkspaceContextDto{account,readiness,navigation,taskSummary,workspaceRevision}`；`navigation.availableRoutes` 固定为十个账号工作区 Route ID，`lastRoute` 只从账号级受控路径恢复。
- 错误与恢复：`ACCOUNT_NOT_FOUND`、`ACCOUNT_ARCHIVED`；服务未就绪或内部错误按公共规则处理。
- Revision / 幂等：只读；`workspaceRevision` 等于账号聚合修订，不是 WebSocket `subscriptionRevision`。
- Invalidations / 事件：无。
- legacy：没有等价 legacy 聚合接口。

### POST `/api/v1/accounts/{account_id}/workspace-activation`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query、Body：无。
- 返回：`data=AccountDto`，成功后 `lastUsedAt` 更新为本次激活时间；`meta={revision,invalidations,idempotentReplay}`。
- 错误与恢复：`ACCOUNT_NOT_FOUND`、`ACCOUNT_ARCHIVED`、`REVISION_CONFLICT`、`REQUEST_CONFLICT`；修订冲突时先重新获取账号或工作区上下文，幂等冲突时换用与新切换意图匹配的键。
- Revision / 幂等：账号修订锁 + 普通写幂等。Desktop 只在目标账号真正成为当前账号时调用，不在普通刷新或 WebSocket 补拉中重复激活。
- Invalidations / 事件：失效 `accounts:list`、`current-context`、账号详情和工作区；原子写入 `account.workspace.activated`。
- legacy：没有等价 legacy 接口。

请求示例：

```http
POST /api/v1/accounts/acc_example/workspace-activation HTTP/1.1
Authorization: Bearer <runtime-session-token>
If-Match: "7"
Idempotency-Key: switch-acc-example-01
```

响应示例：

```json
{
  "ok": true,
  "data": {
    "id": "acc_example",
    "name": "示例账号",
    "username": "example",
    "platform": "tiktok",
    "status": "draft",
    "positioningSummary": null,
    "lastUsedAt": "2026-07-26T10:00:00Z",
    "readiness": {
      "connection": {
        "status": "missing",
        "label": "未连接",
        "errorCode": null,
        "logId": null,
        "checkedAt": null,
        "suggestedAction": {
          "actionKey": "open_connection",
          "label": "配置真实连接",
          "routeId": "account_management",
          "section": "connection",
          "taskId": null
        }
      },
      "knowledge": {
        "status": "empty",
        "label": "待补充",
        "errorCode": null,
        "logId": null,
        "checkedAt": null,
        "suggestedAction": {
          "actionKey": "open_knowledge",
          "label": "添加知识来源",
          "routeId": "account_strategy_knowledge",
          "section": "knowledge",
          "taskId": null
        }
      },
      "ai": {
        "status": "missing",
        "label": "AI 配方待配置",
        "errorCode": "AI_RECIPE_REQUIRED",
        "logId": null,
        "checkedAt": null,
        "suggestedAction": {
          "actionKey": "open_ai_recipe",
          "label": "配置 AI 创作档案",
          "routeId": "ai_system_settings",
          "section": "account-recipe",
          "taskId": null
        }
      },
      "overall": "blocked",
      "checkedAt": null,
      "suggestedAction": {
        "actionKey": "open_connection",
        "label": "配置真实连接",
        "routeId": "account_management",
        "section": "connection",
        "taskId": null
      }
    },
    "wizardCompletedAt": null,
    "revision": 8
  },
  "meta": {
    "revision": 8,
    "invalidations": [
      "accounts:list",
      "current-context",
      "account:acc_example:detail",
      "account:acc_example:workspace"
    ],
    "idempotentReplay": false
  }
}
```

### POST `/api/v1/accounts/{account_id}/complete-wizard`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。
- Body：`{completedSteps:[...]}`，必须完整且无重复地包含 `identity`、`connection`、`positioning`、`knowledge`、`ai_recipe`、`health`。
- 返回：`data=AccountDto`，`meta={revision,invalidations,idempotentReplay}`；状态由实时 readiness 决定，不保证直接成为 ready。
- 错误与恢复：`ACCOUNT_WIZARD_INCOMPLETE` 应回到缺失步骤；`ACCOUNT_STATE_TRANSITION_INVALID` 表示不是草稿；`REVISION_CONFLICT` 先 GET；`REQUEST_CONFLICT` 修正幂等键复用。
- Revision / 幂等：账号修订锁 + 普通写幂等。
- Invalidations / 事件：失效 `accounts:list`、详情、工作区、readiness；原子写入 `account.updated`。
- legacy：无映射。

### POST `/api/v1/accounts/{account_id}/copy-config`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path 中账号是目标账号；Query：无。
- Body：`{sourceAccountId,sections}`；`sections` 为不重复的 `positioning | knowledgeRules | brandKit | aiRecipe | publishDefaults`，至少一项。来源可归档，目标必须是未归档 `draft`，且来源与目标不能相同。
- 返回：`AccountConfigCopyResultDto{runId,sourceAccountId,targetAccountId,requestedSections,copiedSections,skippedSections,status,targetRevision,completedAt}`；缺失来源分区进入 `skippedSections`，不会伪造内容。P0-E 前 `aiRecipe` 失败封闭为跳过。
- 错误与恢复：`ACCOUNT_COPY_SECTION_INVALID`、`ACCOUNT_COPY_SOURCE_EQUALS_TARGET`、`ACCOUNT_STATE_TRANSITION_INVALID`、`ACCOUNT_NOT_FOUND`、`REVISION_CONFLICT`、`REQUEST_CONFLICT`。
- Revision / 幂等：锁定目标账号修订；全部分区、复制审计、账号修订、事件和幂等响应同事务提交。
- Invalidations / 事件：失效目标详情、工作区、readiness；原子写入 `account.config.copied`。
- legacy：无映射；不得复用旧账号克隆或项目复制接口。

### POST `/api/v1/accounts/{account_id}/archive`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。Body：`{reason?}`，理由最长 512；事件只记录是否提供理由，不记录正文。
- 返回：HTTP 202，`data=TaskAcceptedDto`，`taskType=account.archive_cleanup`、`cancellable=false`。提交成功不等于归档完成，Desktop 必须查询持久任务终态。
- 错误与恢复：`ACCOUNT_ARCHIVED`、`REVISION_CONFLICT`、`TASK_IDEMPOTENCY_CONFLICT`、`TASK_ALREADY_RUNNING`、浏览器所有权无法证明或清理失败。失败时账号保持 `attention + ARCHIVE_CLEANUP_FAILED`，执行环境进入 `cleanup_failed` 或 `orphaned`，不会删除工作目录或伪造归档成功。
- Revision / 幂等：创建时冻结账号修订；持久任务执行时再次核对。相同业务意图复用任务幂等键。
- Invalidations / 事件：提交失效账号任务；任务会先取消其他账号任务、撤销平台会话并在所有权证明通过后停止浏览器，最后才写入 `account.archived`，失效 `accounts:list`、`current-context`、账号工作区与任务列表。
- legacy：旧 DELETE 是删除语义，不映射；v1 只归档真实账号。

### POST `/api/v1/accounts/{account_id}/restore`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path：已归档 `account_id`。Query：无。Body：`{checks?}`，可选且无重复，值为 `connection | knowledge | ai`；省略时检查全部三项。
- 返回：HTTP 202，`data=TaskAcceptedDto`，`taskType=account.restore_health_check`；`meta.invalidations=["accounts:list","account:{id}:tasks"]`。任务成功后，未完成六步向导的账号恢复为 `draft`；已完成向导的账号按真实 readiness 恢复为 `unbound | ready | attention`。
- 错误与恢复：`ACCOUNT_NOT_FOUND`、`ACCOUNT_STATE_TRANSITION_INVALID`、`REVISION_CONFLICT`、`TASK_IDEMPOTENCY_CONFLICT`、`TASK_ALREADY_RUNNING`、任务装配错误；按 `meta.taskId` 或创建响应中的任务地址 GET 取得最终状态。
- Revision / 幂等：创建时冻结预期账号修订；执行阶段再次核对。幂等由任务作用域处理。
- Invalidations / 事件：提交产生账号任务事件；执行可能产生 `account.connection.updated`，最终原子写入 `account.health.updated`，并刷新列表、详情、工作区和 readiness。
- legacy：无映射。

### GET `/api/v1/accounts/{account_id}/health`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`，可读取已归档账号。Query、Body：无。
- 返回：`data=AccountReadinessDto`，无 `meta`。
- 错误与恢复：`ACCOUNT_NOT_FOUND` 或公共错误；这是只读快照，不会主动执行探测。
- Revision / 幂等：无。
- Invalidations / 事件：无。
- legacy：旧刷新统计不是该 readiness DTO 的等价接口。

### POST `/api/v1/accounts/{account_id}/health-checks`

- Headers：`Authorization`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。Body：`{checks?}`，规则与恢复接口相同；省略时检查三项。
- 返回：HTTP 202，`TaskAcceptedDto`，`taskType=account.health_check`；失效账号 tasks 与 readiness。
- 错误与恢复：`ACCOUNT_NOT_FOUND`、`ACCOUNT_ARCHIVED`、`TASK_IDEMPOTENCY_CONFLICT`、`TASK_ALREADY_RUNNING`、任务处理器/快照错误；通过账号任务 GET、取消接口和 WebSocket 跟踪。
- Revision / 幂等：无需 `If-Match`；任务作用域幂等。
- Invalidations / 事件：`task.*`；真实连接探测时写 `account.connection.updated`，收口写 `account.health.updated`。
- legacy：旧 `refresh-stats` 的统计与发布检查语义不同，不映射。

## 4. 真实连接

### GET `/api/v1/accounts/{account_id}/connection`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query、Body：无。
- 返回：`data=ConnectionDto`。无绑定时各真实对象为 `null`，不创建假工作区。
- 错误与恢复：`ACCOUNT_NOT_FOUND`、`ACCOUNT_ARCHIVED` 或公共错误。
- Revision / 幂等：只读；`ConnectionDto.revision` 是账号修订基线。
- Invalidations / 事件：无。
- legacy：旧账号 binding DTO 不能表达 `DeviceWorkspace -> BrowserInstance -> ExecutionBinding` 一致性，不映射。

### GET `/api/v1/accounts/{account_id}/connection/candidates`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query、Body：无。
- 返回：`data=ConnectionCandidatesDto`。只列出该账号下 `DeviceWorkspace -> BrowserInstance -> ExecutionBinding` 完整一致且通过实时资格检查的候选；每项返回绑定用的 `environmentId` 和不可猜测的 `eligibilityRevision`。不合格环境不进入候选，无候选时返回 `{items:[]}`。
- 错误与恢复：`ACCOUNT_NOT_FOUND`、`ACCOUNT_ARCHIVED` 或公共错误。空数组是可恢复业务状态，Desktop 应显示创建或检查真实执行环境的引导，不伪造候选。
- Revision / 幂等：只读，不使用 `If-Match` 或幂等键。
- Invalidations / 事件：无；连接变化后由 `account.connection.updated` 触发客户端重新读取。
- legacy：旧绑定接口不提供可验证候选集合，不映射。

请求示例：

```http
GET /api/v1/accounts/acc_example/connection/candidates HTTP/1.1
Authorization: Bearer <runtime-session-token>
```

响应示例：

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "environmentId": "binding_example",
        "eligibilityRevision": 7,
        "deviceWorkspace": {
          "id": "workspace_example",
          "name": "本机发布工作区",
          "status": "ready"
        },
        "browserInstance": {
          "id": "browser_example",
          "name": "TikTok 浏览器",
          "status": "running",
          "lastCheckedAt": "2026-07-26T09:58:00Z"
        },
        "executionBinding": {
          "id": "binding_example",
          "status": "active",
          "deviceWorkspaceId": "workspace_example",
          "browserInstanceId": "browser_example"
        }
      }
    ]
  }
}
```

### PUT `/api/v1/accounts/{account_id}/connection/binding`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。Body：`{environmentId,eligibilityRevision}`；禁止客户端分别提交工作区和浏览器 ID 拼接绑定。
- 返回：`data=ConnectionDto`，`meta={revision,invalidations,idempotentReplay}`。Runtime 在同一事务内重新读取执行环境、复算资格并核对证据修订；通过后激活该绑定，新环境的授权状态为 `required`、健康为 `unknown`。仅同一已验证绑定可安全保留原状态。
- 错误与恢复：`EXECUTION_ENVIRONMENT_NOT_FOUND` 表示环境不存在或不属于当前账号；`EXECUTION_ENVIRONMENT_NOT_ELIGIBLE` 表示环境状态或资格证据已变化，应重新读取候选；`EXECUTION_BINDING_INVALID`、`REVISION_CONFLICT`、`REQUEST_CONFLICT` 按最新状态恢复。
- Revision / 幂等：账号修订锁 + 普通写幂等；绑定、连接状态、账号修订和事件同事务。
- Invalidations / 事件：失效 `accounts:list`、connection、readiness、workspace；写入 `account.connection.updated`。
- legacy：旧 `PUT /api/accounts/{id}/binding` 不强制完整账号一致性，不映射。

### DELETE `/api/v1/accounts/{account_id}/connection/binding`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query、Body：无。
- 返回：`data=ConnectionDto`，绑定对象为空且连接健康转为 attention；`meta={revision,invalidations,idempotentReplay}`。
- 错误与恢复：`ACCOUNT_CONNECTION_REQUIRED` 表示无可解除绑定；`EXECUTION_BINDING_INVALID`、`REVISION_CONFLICT`、`REQUEST_CONFLICT` 按最新连接状态恢复。
- Revision / 幂等：账号修订锁 + 普通写幂等。
- Invalidations / 事件：失效 `accounts:list`、connection、readiness、workspace；写入 `account.connection.updated`。
- legacy：没有等价解除绑定接口。

### POST `/api/v1/accounts/{account_id}/connection/checks`

- Headers：`Authorization`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。Body 为 `{checks?}`；省略时固定检查连接，显式提交时只允许精确 `["connection"]`。
- 返回：HTTP 202，`TaskAcceptedDto`，`taskType=account.connection_check`；失效账号 tasks 与 connection。
- 错误与恢复：其他检查项返回 `REQUEST_VALIDATION_FAILED`，字段规则码为 `connection_check_only`；`WORKSPACE_UNAVAILABLE` 表示缺少真实完整绑定；`TASK_ALREADY_RUNNING` 时按 `meta.taskId` 跟踪既有任务；另有账号门禁和任务幂等/装配错误。修复输入或绑定后使用新业务幂等键重新提交。
- Revision / 幂等：无需 `If-Match`；任务作用域幂等。
- Invalidations / 事件：任务事件写入账号 tasks Topic；执行写 `account.connection.updated` 和 `account.health.updated`。
- legacy：旧刷新统计或浏览器健康接口不映射。

### POST `/api/v1/accounts/{account_id}/connection/login-sessions`

- Headers：`Authorization`、`Idempotency-Key`、JSON 必填。Body：`{environmentId}`。
- 返回：HTTP 202，`{sessionId,taskId,state}`。准备任务只在当前账号已激活的执行环境中打开可见 TikTok 登录页，不接收密码、Cookie 或验证码。
- 错误与恢复：`ACCOUNT_CONNECTION_REQUIRED` 时先绑定合格环境；`LOGIN_SESSION_STATE_CONFLICT` 时取消当前活动尝试后再创建。

### GET `/api/v1/accounts/{account_id}/connection/login-sessions/{session_id}`

- 返回：`LoginSessionDto`，状态为 `preparing | waiting_user | probing | completed | cancelled | failed | timed_out`，并包含期望/已探测公开身份、任务引用、错误码和修订。
- 账号与会话共同限定读取范围；跨账号读取返回 `LOGIN_SESSION_NOT_FOUND`，不泄漏会话是否存在。

### POST `/api/v1/accounts/{account_id}/connection/login-sessions/{session_id}/probe`

- Headers：`Authorization`、`Idempotency-Key`、JSON 必填。Body：`{revision}`。
- 返回：HTTP 202，提交公开页面身份探测任务。任务只读取可见 TikTok 页面身份，不读取凭据或 Cookie；身份一致后安全存储最小会话证明并把连接更新为 `authStatus=valid`、`healthStatus=ready`。
- 错误与恢复：修订变化返回 `REVISION_CONFLICT`；未登录、身份不可识别或身份不一致分别返回稳定平台错误，用户可回到同一可见浏览器修复后重试。

### DELETE `/api/v1/accounts/{account_id}/connection/login-sessions/{session_id}`

- Headers：`Authorization`、`Idempotency-Key` 必填。取消当前监督登录尝试，返回 Runtime 已确认的最终 `LoginSessionDto`。取消只改变登录尝试，不删除账号或执行环境。
- Runtime 会取消准备或探测任务并等待终态；若任务已成功提交身份结果，则返回 `completed` 而不伪装为取消。取消未闭环时返回 `LOGIN_SESSION_CANCEL_INCOMPLETE` 并保留会话与任务引用，客户端必须重新 GET 会话对账后重试。

### DELETE `/api/v1/accounts/{account_id}/connection/session`

- Headers：`Authorization`、`Idempotency-Key` 必填。返回 HTTP 202 的 `{taskId}`。
- 登出任务先通过受控浏览器清理 TikTok origin 存储，证明成功后才撤销最小会话引用并把账号连接降为需重新登录；失败时不伪装已登出。

## 5. 事件、敏感数据与恢复边界

- 账号聚合事件默认 Topic 为 `account:{account_id}:workspace`；连接健康执行中的连接事件使用 `account:{account_id}:connection`；任务事件使用 `account:{account_id}:tasks`。
- 事件只携带受控状态、资源 ID、修订和失效键，不携带归档理由、凭据、Session、浏览器 Profile 路径、Prompt、正文或 traceback。
- 账号列表和 HTTP 快照是最终真源。WebSocket 断档时先按 `workspaceRevision` / DTO `revision` 重新 GET，再以更高 `subscriptionRevision` 重订阅；这两个修订不可混用。
- 三个健康任务都支持协作式取消和任务超时。终止先于业务提交时事务回滚并进入取消或超时终态；真实提交先进入时终止请求等待提交完成，任务以成功终态收口，禁止出现“数据已提交但任务显示取消”。恢复任务只有在真实复检完成后才解除归档，不会先伪造 ready。
- 本组未迁移 legacy 账号路由仍只在非生产模式注册，不是 v1 薄适配；其中账号写接口统一返回 410，P0-D 受控新壳已经直接接入本文件契约。

## 6. Desktop 调用映射

P0-D 账号页面只通过 `apps/desktop/src/app/runtime-client/accounts.ts` 调用本组接口，不在 Vue 组件内直接请求 Runtime：

| Desktop 函数 | Runtime 地址 |
| --- | --- |
| `listAccounts` / `createAccount` | `GET /accounts` / `POST /accounts` |
| `getAccount` / `patchAccount` | `GET /accounts/{account_id}` / `PATCH /accounts/{account_id}` |
| `getAccountWorkspaceContext` / `activateAccountWorkspace` | `GET /accounts/{account_id}/workspace-context` / `POST /accounts/{account_id}/workspace-activation` |
| `completeAccountWizard` / `copyAccountConfig` | `POST /accounts/{account_id}/complete-wizard` / `POST /accounts/{account_id}/copy-config` |
| `archiveAccount` / `restoreAccount` | `POST /accounts/{account_id}/archive` / `POST /accounts/{account_id}/restore` |
| `getAccountHealth` / `startAccountHealthChecks` | `GET /accounts/{account_id}/health` / `POST /accounts/{account_id}/health-checks` |
| `getAccountConnection` / `listAccountConnectionCandidates` | `GET /accounts/{account_id}/connection` / `GET /accounts/{account_id}/connection/candidates` |
| `bindAccountConnection` / `unbindAccountConnection` | `PUT /accounts/{account_id}/connection/binding` / `DELETE /accounts/{account_id}/connection/binding` |
| `startAccountConnectionCheck` | `POST /accounts/{account_id}/connection/checks` |
| `createAccountLoginSession` / `getAccountLoginSession` | `POST /accounts/{account_id}/connection/login-sessions` / `GET /accounts/{account_id}/connection/login-sessions/{session_id}` |
| `probeAccountLoginSession` / `cancelAccountLoginSession` | `POST .../login-sessions/{session_id}/probe` / `DELETE .../login-sessions/{session_id}` |
| `logoutAccountSession` | `DELETE /accounts/{account_id}/connection/session` |

表中地址省略统一前缀 `/api/v1`。账号切换由 Account Context 应用层编排：先读取 `workspace-context`，预建目标账号事件订阅与界面资源并原子提交订阅、配置和路由；目标账号可见后再调用 `workspace-activation` 并重新读取最终上下文。提交前失败回滚原账号；提交后的激活或补拉失败保留目标账号，显示可重试的刷新错误，避免界面与已提交上下文反复跳转。
