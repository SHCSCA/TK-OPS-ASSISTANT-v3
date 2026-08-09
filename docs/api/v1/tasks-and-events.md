# 持久任务与 Runtime 事件 API v1

本文件描述已注册的六个持久任务 HTTP 端点、一个 Runtime WebSocket 端点，以及账号、执行环境和系统 AI 任务类型。任务状态以数据库和 HTTP 查询为最终真源；WebSocket 用于低延迟通知、按 Topic 隔离和有界断线重放。

P0-D 才接入 Desktop v1 领域客户端。现存 legacy 任务客户端继续消费旧 DTO；受控兼容适配器已经调用同一持久任务协调器，但响应形状、列表范围和取消幂等门禁不等同于本契约。

公共 HTTP 错误、WebSocket 错误和 legacy 字符串映射见 [errors.md](errors.md)。

## 任务 HTTP 总览

| 方法 | 地址 | 作用域 | 幂等键 | 成功状态 |
| --- | --- | --- | --- | ---: |
| `GET` | `/api/v1/system/tasks` | 系统 | 无 | 200 |
| `GET` | `/api/v1/system/tasks/{task_id}` | 系统 | 无 | 200 |
| `POST` | `/api/v1/system/tasks/{task_id}/cancel` | 系统 | 必填 | 200 |
| `GET` | `/api/v1/accounts/{account_id}/tasks` | 账号 | 无 | 200 |
| `GET` | `/api/v1/accounts/{account_id}/tasks/{task_id}` | 账号 | 无 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/tasks/{task_id}/cancel` | 账号 | 必填 | 200 |

六个端点都要求公共 Host、Origin、Runtime Session 和 active 许可证门禁。当前没有通用任务创建或重试 HTTP 端点；任务只能从受控领域入口创建：

- [Bootstrap 自检](bootstrap.md#post-apiv1bootstrapself-checks)。
- [账号恢复与健康检查](accounts.md#3-账号读取与生命周期)。
- [真实连接检查](accounts.md#4-真实连接)。
- [知识索引](account-knowledge.md#post-apiv1accountsaccount_idknowledgeindex-jobs)。
- [Provider 检查、模型发现与能力验证](ai-system.md#任务事件与缓存失效)。

## `TaskDto`

```json
{
  "taskId": "task_0123456789abcdef0123456789abcdef",
  "scope": "system",
  "accountId": null,
  "taskType": "bootstrap.self_check",
  "status": "running",
  "cancellable": true,
  "createdAt": "2026-07-26T08:00:00Z",
  "completionKind": null,
  "failureKind": null,
  "progress": 0.5,
  "resultRef": null,
  "errorCode": null,
  "logId": null,
  "revision": 3
}
```

字段约束：

- `scope`：`system | account`。账号任务的 `accountId` 非空；系统任务为 `null`。
- `status`：`queued | running | cancelling | failed | completed`。
- `completionKind`：仅完成态使用，取 `succeeded | cancelled`。
- `failureKind`：仅失败态使用，取 `error | timed_out | restart_interrupted`。
- `progress`：0 至 1。
- `resultRef`：成功处理器返回的不透明受控引用；Bootstrap 自检返回 `null`，账号健康任务返回 `account://...`，知识索引返回 `knowledge://...`。任务内核不解析该字符串，客户端不得把它当任意文件路径或 URL 直接打开。
- `errorCode` 与 `logId`：失败任务的安全诊断引用；不得把 traceback 填入 DTO。
- `revision`：每次持久状态转换递增，用于忽略旧事件。

## 已注册任务类型

| `taskType` | 创建入口与作用域 | 冻结业务 payload | 恢复策略 | 成功 `resultRef` |
| --- | --- | --- | --- | --- |
| `bootstrap.self_check` | Bootstrap，自系统作用域 | Bootstrap 自检快照 | 按 Bootstrap 文档 | `null` |
| `account.health_check` | 账号健康检查，账号作用域 | `checks` | `interrupt`；Runtime 重启不重做外部探测 | `account://{account_id}/health?revision={revision}` |
| `account.restore_health_check` | 账号恢复，账号作用域 | `checks`、`expectedRevision` | `interrupt`；必须重新由用户发起恢复 | 同上 |
| `account.connection_check` | 连接检查，账号作用域 | 固定 `checks=["connection"]` | `interrupt` | 同上 |
| `knowledge.index` | 知识索引，账号作用域 | `sourceIds`、创建时的索引 `policy` | `resume`；启动时先完成持久任务恢复决策，再校验非终态任务快照并只保护其 `sourceIds`，同账号未被活动任务承接的 indexing 来源仍调和为孤儿失败态 | `knowledge://{account_id}/index-jobs/{task_id}` |
| `provider.health_check` | Provider 检查，系统作用域 | `providerId`、`providerRevision`、`force` | `interrupt`；外部调用存在 crash window，重启后不自动重做 | `provider://{provider_id}/health?aiConfigRevision={revision}` |
| `provider.model_discovery` | 模型发现，系统作用域 | `providerId`、`providerRevision`、`replaceMissing=false` | `interrupt`；P0 不删除未返回模型，重启后由用户显式重试 | `provider://{provider_id}/models?aiConfigRevision={revision}` |
| `model.capability_check` | 能力验证，系统作用域 | `modelProfileId`、模型与 Provider 修订、能力键、`force` | `interrupt`；只提交受控能力契约结果，重启不误报成功 | `model://{model_profile_id}/capabilities?aiConfigRevision={revision}` |
| `execution_environment.provision` | 新建执行环境，账号作用域 | `environmentId`、`rootRef`、激活开关 | `interrupt`；失败保留环境和日志，不猜测进程归属 | `execution-environment://{environment_id}?revision={revision}` |
| `execution_environment.start` | 启动执行环境，账号作用域 | `environmentId`、`expectedRevision` | `interrupt`；重启后不猜测新启动进程归属 | 同上 |
| `execution_environment.stop` | 停止执行环境，账号作用域 | `environmentId`、`expectedRevision` | `resume`；每次停止前重新证明进程所有权 | 同上 |
| `execution_environment.check` | 检查执行环境，账号作用域 | `environmentId`、`expectedRevision` | `resume`；重新读取真实进程与调试端口状态 | 同上 |
| `execution_environment.delete` | 删除环境记录，账号作用域 | `environmentId`、`expectedRevision` | `resume`；停止受控进程后软删除，保留用户文件 | 同上 |
| `account.archive_cleanup` | 归档账号，账号作用域 | `expectedRevision`、`reasonProvided` | `resume`；所有权证明失败时进入待处理状态，不删除目录 | `account://{account_id}/archive?revision={revision}` |
| `account.login.prepare` | 监督登录准备，账号作用域 | `loginSessionId` | `interrupt`；重启后由用户重新打开可见登录页 | `login-session://{session_id}` |
| `account.login.probe` | 公开身份探测，账号作用域 | `loginSessionId` | `interrupt`；不自动重做平台探测 | `login-session://{session_id}` |
| `account.logout` | 安全登出，账号作用域 | 空对象 | `interrupt`；清理证明失败时不撤销会话引用 | `account-session://{account_id}/revoked` |

任务均使用处理器版本 1，并按作用域与任务类型限制活动任务。归档、停止和删除属于不可取消的安全收口任务；其他任务是否可取消以 `TaskDto.cancellable` 为准。存在活动任务时返回 `TASK_ALREADY_RUNNING` 和 `meta.taskId`。相同创建幂等键只在既有任务仍为 `queued` 时重放受理结果；任务已进入运行态或终态后，如需重新执行必须先查询原任务并使用新的业务幂等键。AI 任务快照只保存资源 ID、修订、能力键和非敏感开关，处理器执行时才按安全引用读取凭据。

## GET `/api/v1/system/tasks`

读取最近的系统级持久任务，Query `limit` 默认为 50，范围 1 至 200。返回 `TaskListDto{items:TaskDto[]}`，按创建时间和任务 ID 倒序；不包含任何账号任务。该接口用于页面重建、Runtime 重启和 WebSocket 断档后的最终对账。

## GET `/api/v1/accounts/{account_id}/tasks`

读取指定账号最近的持久任务，Query `limit` 默认为 50，范围 1 至 200。返回 `TaskListDto{items:TaskDto[]}`，只包含持久记录中 `account_id` 精确匹配的任务；允许读取已归档账号，便于确认归档终态。错误账号不能探测其他账号任务。

## GET `/api/v1/system/tasks/{task_id}`

读取系统作用域任务的最终持久状态。

### 请求

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`task_id` 为 Runtime 返回的不透明任务标识，必须匹配公共稳定资源 ID
  语法 `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`。
- Query、Body：无。

格式错误返回 `REQUEST_VALIDATION_FAILED`；客户端仍应原样复用 Runtime
返回值，不得自行构造。

### 成功

HTTP 200：

```json
{
  "ok": true,
  "data": {
    "taskId": "task_0123456789abcdef0123456789abcdef",
    "scope": "system",
    "accountId": null,
    "taskType": "bootstrap.self_check",
    "status": "completed",
    "cancellable": true,
    "createdAt": "2026-07-26T08:00:00Z",
    "completionKind": "succeeded",
    "failureKind": null,
    "progress": 1.0,
    "resultRef": null,
    "errorCode": null,
    "logId": null,
    "revision": 5
  }
}
```

### 错误、幂等、超时与恢复

| 错误码 | HTTP | 恢复动作 |
| --- | ---: | --- |
| `TASK_NOT_FOUND` | 404 | 丢弃本地任务引用，必要时回到创建入口 |
| `ACCOUNT_SCOPE_MISMATCH` | 403 | 该 ID 存在但不是系统任务；使用创建响应中的作用域路径 |
| `RUNTIME_NOT_READY` | 503 | 等待持久任务协调器完成装配 |
| `INTERNAL_ERROR` | 500 | 使用 `log_id` 诊断并重试只读请求 |

本端点只读，不使用幂等键或端点级超时参数，不产生事件。

### 敏感边界与 legacy

- 返回受控快照的投影，不返回任务输入快照、幂等键原文、Runtime Session 或处理器异常。
- legacy `GET /api/tasks/{task_id}` 调用同一持久任务协调器读取系统任务，再转换为旧任务 DTO；该受控适配器在生产模式仍注册，但要求本机会话与 active 许可证。

## POST `/api/v1/system/tasks/{task_id}/cancel`

为可取消的系统任务提交协作式取消请求。

### 请求

- Headers：
  - `Authorization`、`Idempotency-Key` 必填。
  - `X-Operation-ID` 可选。
- Path：`task_id` 为 Runtime 返回的不透明任务标识。
- Query、Body：无。

### 成功

HTTP 200：

```json
{
  "ok": true,
  "data": {
    "taskId": "task_0123456789abcdef0123456789abcdef",
    "scope": "system",
    "accountId": null,
    "taskType": "bootstrap.self_check",
    "status": "cancelling",
    "cancellable": true,
    "createdAt": "2026-07-26T08:00:00Z",
    "completionKind": null,
    "failureKind": null,
    "progress": 0.5,
    "resultRef": null,
    "errorCode": null,
    "logId": null,
    "revision": 4
  },
  "meta": {
    "revision": 4,
    "invalidations": ["system:tasks"]
  }
}
```

任务已经为 `cancelling` 或终态时，端点返回当前 DTO，不重复转换状态。

### 错误、幂等、超时与恢复

| 错误码 | HTTP | 恢复动作 |
| --- | ---: | --- |
| `REQUEST_VALIDATION_FAILED` | 422 | 补充合法 `Idempotency-Key`，或修正请求关联 Header |
| `TASK_NOT_FOUND` | 404 | 丢弃无效任务引用 |
| `ACCOUNT_SCOPE_MISMATCH` | 403 | 改用正确作用域路径 |
| `TASK_NOT_CANCELLABLE` | 409 | 保留任务运行，等待最终态 |
| `TASK_STATE_CONFLICT` | 409 | 并发状态已变化；立即 GET 最终状态 |
| `RUNTIME_NOT_READY` | 503 | 等待任务协调器就绪 |
| `INTERNAL_ERROR` | 500 | 先 GET 对账，再决定是否重试 |

- `Idempotency-Key` 在取消端点中是必填的格式与意图门禁，不建立跨任务响应重放记录。重复取消依靠任务状态转换本身收敛。
- HTTP 请求没有端点级超时参数。进入 `cancelling` 只表示已提交协作式取消；最终通常为 `completed + completionKind=cancelled`，必须继续 GET 或监听事件。

### 事件、敏感边界与 legacy

- 首次进入 `cancelling` 时，任务记录和 `task.cancelling` outbox 事件在同一数据库事务内提交，Topic 为 `system:tasks`。
- 事件只包含任务投影，不包含输入快照或密钥。
- legacy `POST /api/tasks/{task_id}/cancel` 调用同一持久任务协调器；缺少幂等键时补充 `legacy:cancel:{task_id}`，并转换为旧任务 DTO。该适配器在生产模式仍注册并执行本机会话与 active 许可证门禁。

## GET `/api/v1/accounts/{account_id}/tasks/{task_id}`

读取指定账号作用域内任务的最终持久状态。

### 请求

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：
  - `account_id`：创建任务时绑定的账号标识。
  - `task_id`：Runtime 返回的不透明任务标识。
- Query、Body：无。

`task_id` 必须匹配公共稳定资源 ID 语法
`^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`；格式错误返回
`REQUEST_VALIDATION_FAILED`。格式通过后，作用域仍由持久任务记录中的
`scope` 和 `account_id` 精确校验。

### 成功

```json
{
  "ok": true,
  "data": {
    "taskId": "task_0123456789abcdef0123456789abcdef",
    "scope": "account",
    "accountId": "account_01",
    "taskType": "account.health_check",
    "status": "failed",
    "cancellable": true,
    "createdAt": "2026-07-26T08:00:00Z",
    "completionKind": null,
    "failureKind": "timed_out",
    "progress": 0.4,
    "resultRef": null,
    "errorCode": "TASK_TIMEOUT",
    "logId": null,
    "revision": 6
  }
}
```

账号任务只能由其领域创建入口提交，不能通过任务查询接口自行构造 `taskType` 或 payload。

### 错误、幂等、超时与恢复

- `TASK_NOT_FOUND`：HTTP 404。
- `ACCOUNT_SCOPE_MISMATCH`：任务属于系统或其他账号，HTTP 403；使用创建响应中的账号和作用域重新查询。
- `RUNTIME_NOT_READY`：HTTP 503。
- `INTERNAL_ERROR`：HTTP 500。
- 只读，无幂等键、端点级超时或事件。

### 敏感边界与 legacy

- 账号 Path 不能覆盖持久记录的作用域；错误账号不会返回任务 DTO。
- legacy `/api/tasks/{task_id}` 没有账号 Path 隔离，不构成本接口契约。

## POST `/api/v1/accounts/{account_id}/tasks/{task_id}/cancel`

为指定账号作用域内的可取消任务提交协作式取消请求。

### 请求

- Headers：`Authorization`、`Idempotency-Key` 必填；`X-Operation-ID` 可选。
- Path：`account_id` 和 `task_id` 必填。
- Query、Body：无。

### 成功

```json
{
  "ok": true,
  "data": {
    "taskId": "task_0123456789abcdef0123456789abcdef",
    "scope": "account",
    "accountId": "account_01",
    "taskType": "account.health_check",
    "status": "cancelling",
    "cancellable": true,
    "createdAt": "2026-07-26T08:00:00Z",
    "completionKind": null,
    "failureKind": null,
    "progress": 0.4,
    "resultRef": null,
    "errorCode": null,
    "logId": null,
    "revision": 4
  },
  "meta": {
    "revision": 4,
    "invalidations": ["account:account_01:tasks"]
  }
}
```

### 错误、幂等、超时与恢复

错误集合与系统取消端点相同：`REQUEST_VALIDATION_FAILED` 422、`TASK_NOT_FOUND` 404、`ACCOUNT_SCOPE_MISMATCH` 403、`TASK_NOT_CANCELLABLE` 409、`TASK_STATE_CONFLICT` 409、`RUNTIME_NOT_READY` 503、`INTERNAL_ERROR` 500。

- 幂等键只作为取消意图门禁；重复调用依靠终态或 `cancelling` 状态收敛。
- 没有端点级超时参数。先以当前账号路径 GET 对账，再重试未知结果。

### 事件、敏感边界与 legacy

- 首次状态转换与 `task.cancelling` 事件原子提交，Topic 为 `account:{account_id}:tasks`，事件的 `accountId` 必须与 Topic 一致。
- 不向系统 Topic 或其他账号 Topic 复制账号事件。
- legacy 任务取消同样调用持久任务协调器，但只处理系统作用域、没有账号 Path 隔离，并返回旧任务 DTO；它不构成本账号接口契约。

## 任务状态、超时与恢复

| 当前状态 | 可见下一状态 |
| --- | --- |
| `queued` | `running`、`cancelling` 或 `failed` |
| `running` | `cancelling`、`completed + succeeded`、`failed`；可恢复处理器在重启恢复时可重新排队 |
| `cancelling` | 通常进入 `completed + cancelled`；异常收尾可进入 `failed` |
| `completed`、`failed` | 终态，不再转换 |

- `cancelling` 是非终态；协作式处理器可能在收到取消后才结束。
- 账号健康任务在真实数据库提交处执行单一裁决：取消或超时先赢则回滚；提交
  先赢则等待提交完成并以 `completed + succeeded` 收口，不把已提交的数据
  标记成取消或超时。
- 创建时冻结处理器版本、受控 payload、请求/操作关联标识，以及幂等键和请求摘要；不会保存会话令牌或密钥原文。
- 内部非空列 `idempotency_key_hash`、`request_hash`、`handler_version` 分别用于作用域幂等且不保存明文键、校验冻结正文完整性、判断重启恢复兼容性；它们不属于公开 `TaskDto`。
- 内部 `config_snapshot_json` 当前为 `schemaVersion=2`，冻结 `command.creationAttempt`、`retryOfTaskId` 和 `requestedTimeoutSeconds`。恢复过程可以递增任务运行 `attempt`，但不会改写原始创建语义或幂等请求摘要。
- 默认执行超时取配置总线 `runtime.taskTimeoutSeconds`，当前默认 900 秒，并受 `runtime.taskMaxTimeoutSeconds` 上限约束。
- Runtime 重启先整理非终态任务，但暂不调度可恢复任务：超时任务失败为
  `TASK_TIMEOUT`；缺失处理器或快照不兼容会以受控错误码进入失败态；
  可恢复处理器先重新排队。随后知识启动对账校验这些非终态
  `knowledge.index` 快照的完整性和 `sourceIds`；全部对账成功后才统一调度
  可恢复任务。异常会记录统一诊断日志并阻止 Runtime 进入就绪状态，禁止
  任务在对账快照前执行或据此误改来源状态。
- Runtime 停机使用统一单调时钟截止点；宽限期内未结束的任务不会伪造完成态或从内存索引中静默清除，持久状态由下一次启动恢复。停机期间未完成实时投递或未确认 `mark_published` 的 outbox 事件仍保持未发布，下一次启动继续重放。
- 当前没有公开 retry 路由。账号健康类任务因重启中断或业务失败后，应回到原领域入口重新确认前置条件并使用新的业务幂等键；知识索引可由 Runtime 恢复，明确失败后也应修复来源再新建任务，不得把新任务伪装成原任务重试。
- 启动对账仅扫描 Runtime 管理的 `accounts/{account_id}/knowledge/{source_id}.txt` 生成路径。数据库中所有 `sourceMode=text` 的 `source_ref`（包括软删除墓碑）均受保护；只有账号 ID、来源 ID、目录层级和 `.txt` 文件名同时符合生成规则且数据库完全无引用的文件才会作为崩溃遗留孤儿清理。扫描、引用校验或删除异常会记录日志并阻止就绪。

## WebSocket `/api/v1/ws`

### 连接地址、方法与安全握手

- 地址：`ws://<runtime-host>/api/v1/ws`；由 TLS 终止层提供安全传输时使用 `wss://`。
- 方法：WebSocket Upgrade。
- Headers：
  - `Host` 必须唯一且精确匹配 Runtime 配置。
  - `Origin` 可省略；存在时必须唯一、不能为 `*` 且命中允许列表。
  - `Sec-WebSocket-Protocol` 必须且只能包含两个协议值：
    - `tk-ops-runtime-v1`
    - `tk-ops-session.<base64url-runtime-session-token-without-padding>`
- 不使用 HTTP `Authorization`、`Idempotency-Key` 或 `If-Match`。
- 许可证必须实时为 `active`。

浏览器侧握手形式：

```ts
new WebSocket(runtimeWsUrl, [
  "tk-ops-runtime-v1",
  `tk-ops-session.${encodedRuntimeSession}`,
]);
```

Runtime 只接受并回显 `tk-ops-runtime-v1` 子协议。`tk-ops-session.*` 是凭据承载，不是加密；不得写入日志、URL Query、本地持久缓存或遥测。

### 握手失败与连接关闭

握手门禁失败发生在 `accept` 之前，不发送 JSON 错误帧：

| Close code | 当前触发条件 |
| ---: | --- |
| 4403 | `RUNTIME_HOST_INVALID`、`RUNTIME_ORIGIN_FORBIDDEN`、`LICENSE_INVALID` |
| 4401 | Runtime Session 无效，以及当前未映射到 4403 的许可证门错误，例如 `LICENSE_MACHINE_MISMATCH` |

连接建立后的关闭码：

| Close code | 当前触发条件 |
| ---: | --- |
| 4400 | 单条 UTF-8 消息超过 `websocket.maxMessageBytes` |
| 4408 | 在 `websocket.subscribeTimeoutSeconds` 内未完成首个有效订阅 |
| 1011 | 未预期会话异常、发送超时或发送失败 |

当前默认首订阅超时为 10 秒，消息上限为 65536 字节，单次发送超时为 5 秒，关闭等待为 3 秒；这些值来自配置总线。首订阅前发送 `ping` 可以收到 `pong`，但不会延长订阅截止时间。

### 订阅帧

连接后发送：

```json
{
  "type": "subscribe",
  "subscriptionRevision": 1,
  "accountId": null,
  "topics": [
    {
      "topic": "system:tasks",
      "lastEventId": null,
      "afterSequence": null
    },
    {
      "topic": "system:config",
      "lastEventId": "evt_0123456789abcdef0123456789abcdef",
      "afterSequence": 12
    }
  ]
}
```

约束：

- 顶层和 Topic 项都不允许额外字段。
- `subscriptionRevision` 为大于等于 1 的整数，且必须严格大于当前连接已接受的订阅修订。
- `accountId` 为 `null` 或 1 至 128 字符；非空时还必须匹配 `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`。
- `topics` 包含 1 至 64 项，不允许重复；单个 Topic 长度为 1 至 512。
- 系统 Topic 当前白名单：`system:bootstrap`、`system:config`、`system:health`、`system:ai`、`system:tasks`。
- 账号 Topic 格式为 `account:{account_id}:{resource}`；资源段使用小写字母、数字、点、下划线、连字符和受控冒号层级。
- Topic 不允许首尾空白。
- `accountId=null` 时只能订阅系统 Topic。
- `accountId` 非空时可订阅该账号 Topic 和获准系统 Topic，但即使帧内只有系统 Topic，Runtime 仍会校验该账号存在且未归档。
- `lastEventId` 与 `afterSequence` 必须同时为空或同时提供；`afterSequence` 大于等于 0。

### 订阅确认、重放与重订阅

Runtime 先发送订阅确认：

```json
{
  "type": "subscribed",
  "subscriptionRevision": 1,
  "topics": [
    {
      "topic": "system:tasks",
      "currentSequence": 21,
      "replayedCount": 0
    },
    {
      "topic": "system:config",
      "currentSequence": 14,
      "replayedCount": 2
    }
  ]
}
```

随后按 Topic 顺序发送重放事件，再进入实时投递。Topic 的 `sequence` 单调递增：

- 两个游标字段都为 `null`：以订阅时的 `currentSequence` 建立实时基线，不补历史。
- 两个游标都存在：事件 ID、Topic 和 sequence 必须精确匹配；Runtime 最多重放 `websocket.replayLimit` 条，当前默认 500。
- 同一连接变更账号或 Topic 时，发送更高的 `subscriptionRevision`；新订阅原子替换旧订阅世代。
- 旧或相同订阅修订、游标错配、越过当前位置等情况发送 `WS_CURSOR_MISMATCH` 错误帧，不接受该订阅。

### 断档帧与 HTTP 最终对账

游标早于可重放窗口、事件序列不连续或重放超过上限时，Runtime 在 `subscribed` 后针对该 Topic 发送：

```json
{
  "type": "sync.required",
  "subscriptionRevision": 2,
  "topic": "system:tasks",
  "currentSequence": 900,
  "reason": "WS_EVENT_GAP"
}
```

该 Topic 不进入实时订阅；同一帧中未断档的其他 Topic 仍可正常激活。恢复步骤：

1. 暂停使用该 Topic 的增量事件。
2. 通过对应 HTTP GET 读取最终状态：任务用本文件的系统或账号任务 GET，配置用 `GET /api/v1/system/config`，Bootstrap 用其状态 GET。
3. 清理该 Topic 的本地增量缓存。
4. 使用更高 `subscriptionRevision`，并将该 Topic 的两个游标都设为 `null`，在当前 sequence 建立新实时基线。

当前没有事件历史 HTTP 端点，不得自行猜测缺失事件。

### 协议错误与心跳

订阅期错误帧：

```json
{
  "type": "error",
  "errorCode": "WS_CURSOR_MISMATCH",
  "message": "事件游标与 Topic 不一致。",
  "subscriptionRevision": 2
}
```

- 非 JSON 对象、Schema 错误、重复 Topic 或非法 Topic：`REQUEST_VALIDATION_FAILED`。
- Topic 与账号不一致或无权订阅：`ACCOUNT_SCOPE_MISMATCH`。
- 账号不存在或已归档：`ACCOUNT_NOT_FOUND` 或 `ACCOUNT_ARCHIVED`。
- 游标或订阅世代不一致：`WS_CURSOR_MISMATCH`。
- 普通校验错误只发送错误帧，连接保持可用；超大消息按 4400 关闭。
- 心跳请求 `{"type":"ping"}`，响应 `{"type":"pong"}`。

### Runtime 事件 DTO

```json
{
  "schemaVersion": 1,
  "eventId": "evt_0123456789abcdef0123456789abcdef",
  "eventType": "task.started",
  "topic": "system:tasks",
  "sequence": 21,
  "occurredAt": "2026-07-26T08:00:01Z",
  "accountId": null,
  "resourceType": null,
  "resourceId": null,
  "taskId": "task_0123456789abcdef0123456789abcdef",
  "revision": 2,
  "payload": {
    "taskId": "task_0123456789abcdef0123456789abcdef",
    "scope": "system",
    "accountId": null,
    "taskType": "bootstrap.self_check",
    "status": "running",
    "completionKind": null,
    "failureKind": null,
    "progress": 0.0,
    "cancellable": true,
    "resultRef": null,
    "errorCode": null,
    "logId": null,
    "attempt": 1,
    "retryOfTaskId": null,
    "revision": 2,
    "createdAt": "2026-07-26T08:00:00Z",
    "startedAt": "2026-07-26T08:00:01Z",
    "completedAt": null,
    "updatedAt": "2026-07-26T08:00:01Z"
  }
}
```

客户端先按 Topic 和 `sequence` 排序，再比较资源 `revision`。事件 payload 是失效和进度提示，不能覆盖较新的 HTTP 快照。

### 当前事件生产者

| Topic | 事件类型 | 原子性或恢复边界 |
| --- | --- | --- |
| `system:bootstrap` | `bootstrap.license.changed` | 许可证数据库记录与事件原子提交；安全存储写入失败时不提交 |
| `system:bootstrap` | `bootstrap.directories.changed` | 文件系统操作先发生，事件按幂等键稳定写入；失败后可见目录可能已存在 |
| `system:config` | `config.changed` | 配置记录与事件原子提交 |
| `system:tasks` | `task.queued`、`task.started`、`task.progress`、`task.cancelling`、`task.completed`、`task.failed` | 系统任务状态与事件原子提交 |
| `system:ai` | `provider.updated`、`provider.health.updated`、`model.updated`、`model.capability.updated`、Prompt / Template 激活与 `ai.config.changed` | AI 配置、系统 AI 修订与 outbox 同事务；不包含凭据或 Prompt 正文 |
| `account:{account_id}:tasks` | 同一组任务事件 | 账号任务状态与事件原子提交，不复制到其他 Topic |
| `account:{account_id}:workspace` | `account.created`、`account.updated`、`account.workspace.activated`、`account.archived`、`account.config.copied`、`account.health.updated`、`account.connection.updated`、定位/品牌/发布默认值事件 | 领域记录、账号聚合修订与 outbox 同事务；事件用于失效提示 |
| `account:{account_id}:connection` | 健康探测产生的 `account.connection.updated` | 连接状态证据、账号修订与事件同事务 |
| `account:{account_id}:knowledge` | `knowledge.rules.updated`、`knowledge.source.created`、`knowledge.source.removed`、`knowledge.index.updated`、`knowledge.snapshot.created` | 知识记录、账号聚合修订与事件同事务 |
| `account:{account_id}:ai-recipe` | `ai.recipe.updated` | Recipe 版本、账号修订与事件同事务；系统 AI 修订漂移会使就绪态失效 |

`system:health` 仍是已授权但尚无 canonical 生产者的系统 Topic；`system:ai` 已由 P0-E AI 配置链接管。

### 敏感边界

- 事件不携带 Authorization、Session 子协议、许可证原文、Provider 密钥、Prompt 正文、知识正文、任务输入快照或 traceback。任务结果只允许放不透明受控引用。
- 账号事件的 Topic、顶层 `accountId` 和任务 payload `accountId` 必须一致。
- 事件持久化不依赖在线客户端；无连接时仍进入 outbox，重放受配置上限约束。

## legacy WebSocket `/api/ws`

legacy WebSocket 在生产模式仍注册，用于旧 Desktop 的有限过渡：

- 使用与 v1 相同的 Host、Origin、双子协议 Session 和 active 许可证握手。
- 不接收订阅帧；只投递白名单内、`accountId=null` 的系统事件。
- 账号事件永不转发。
- 输出形态为 `{"schema_version":1,"type":"task.started",...安全字段}`，不包含 canonical `eventId`、Topic、sequence 或完整 payload。
- legacy 白名单仍只允许账号为空的 Bootstrap、配置和系统任务事件；账号事件永不转发到 legacy WebSocket。AI 配置事件仍以 v1 `system:ai` 为真源，不向旧客户端复制敏感领域 payload。
- 客户端文本 `ping` 只被忽略，不返回 `pong`；其他客户端消息也不改变订阅。
- 单条消息受 `websocket.legacyMaxMessageBytes` 约束，当前默认 4096 字节。

legacy `/api/ws` 不是 v1 事件的完整等价接口。退出条件是旧 Desktop 不再依赖无 Topic、无 sequence 的全局系统通知。
