# 执行环境 API v1

本文件描述当前账号真实执行环境的创建、读取与生命周期动作契约。执行环境固定聚合 `DeviceWorkspace -> BrowserInstance -> ExecutionBinding`，所有对象共同绑定 `account_id`；Desktop 只提交由 Tauri 目录注册表签发的 `rootRef`，HTTP 不接收绝对工作路径。

## 共同约束

- 所有接口要求公共 Runtime Session、active 许可证和账号范围门禁。
- 创建任务只在已授权根目录内建立受控子目录并启动真实浏览器；浏览器 PID、调试端口、命令行 Profile、owner marker 和监听端口全部匹配后才进入 ready。
- `eligibility.evidenceRevision` 由绑定、浏览器和工作区修订共同生成。连接绑定必须回传该修订，并在事务内重新校验。
- 返回 DTO 不包含绝对路径、浏览器 Profile 路径、进程命令行、owner nonce 或 Runtime Session。

## 接口总览

| 方法 | 地址 | 幂等键 | 成功 |
| --- | --- | --- | ---: |
| `GET` | `/api/v1/accounts/{account_id}/execution-environments` | 无 | 200 |
| `GET` | `/api/v1/accounts/{account_id}/execution-environments/{environment_id}` | 无 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/execution-environments` | 必填 | 202 |
| `POST` | `/api/v1/accounts/{account_id}/execution-environments/{environment_id}/retry` | 必填 | 202 |
| `POST` | `/api/v1/accounts/{account_id}/execution-environments/{environment_id}/start` | 必填 | 202 |
| `POST` | `/api/v1/accounts/{account_id}/execution-environments/{environment_id}/stop` | 必填 | 202 |
| `POST` | `/api/v1/accounts/{account_id}/execution-environments/{environment_id}/checks` | 必填 | 202 |
| `DELETE` | `/api/v1/accounts/{account_id}/execution-environments/{environment_id}` | 必填 | 202 |

### GET `/api/v1/accounts/{account_id}/execution-environments`

- 返回：`{items: ExecutionEnvironmentDto[]}`，仅包含当前账号对象。空账号返回 `{items:[]}`。
- 每项包含环境、工作区、浏览器、资格、修订和安全错误引用；资格失败必须带稳定 blocking issue 和 recovery action。
- 错误：`ACCOUNT_NOT_FOUND`、`ACCOUNT_ARCHIVED` 或公共错误。只读请求可直接重试。

### GET `/api/v1/accounts/{account_id}/execution-environments/{environment_id}`

- 返回：单个 `ExecutionEnvironmentDto`。
- `environment_id` 不存在或属于其他账号时统一返回 `EXECUTION_ENVIRONMENT_NOT_FOUND`，不暴露跨账号对象。
- 读取会实时投影资格，不启动、停止或修复进程。

### POST `/api/v1/accounts/{account_id}/execution-environments`

- Headers：`Authorization`、`Idempotency-Key`、JSON 必填。
- Body：`{name,rootRef,browser:{kind:"chrome"|"edge",selection:"auto"},activateWhenReady}`。`rootRef` 必须匹配 `wr_` 加 32 位小写十六进制；禁止绝对路径和任意浏览器可执行文件路径。
- 返回：HTTP 202，`{environmentId,taskId}`。HTTP 事务只创建聚合、任务、幂等与事件；目录和进程副作用由 `execution_environment.provision` 持久任务执行。
- 错误与恢复：目录无效、过期、撤销或不可写时修复授权；浏览器启动或所有权证明失败时环境保留失败状态与 `errorLogId`，不得作为候选。相同幂等键只重放同一请求。

请求示例：

```http
POST /api/v1/accounts/acc_example/execution-environments HTTP/1.1
Authorization: Bearer <runtime-session-token>
Idempotency-Key: environment-create-001
Content-Type: application/json

{"name":"主执行环境","rootRef":"wr_0123456789abcdef0123456789abcdef","browser":{"kind":"chrome","selection":"auto"},"activateWhenReady":false}
```

成功响应：

```json
{
  "ok": true,
  "data": {
    "environmentId": "environment_example",
    "taskId": "task_example"
  },
  "meta": {
    "invalidations": [
      "account:acc_example:execution-environments",
      "account:acc_example:tasks"
    ]
  }
}
```

### POST `/api/v1/accounts/{account_id}/execution-environments/{environment_id}/retry`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key` 必填。Body、Query：无。
- 仅允许重试当前账号下 `failed` 状态、且仍保留原 `execution_environment.provision` 任务上下文的执行环境。
- 返回：HTTP 202，`{environmentId,taskId,retryOfTaskId}`。Runtime 在同一 `environmentId`、工作区与浏览器聚合上创建重试任务，不新建替代环境。
- 错误：环境或原任务不存在返回 `EXECUTION_ENVIRONMENT_RETRY_CONTEXT_MISSING`；状态或任务类型不允许重试返回 `EXECUTION_ENVIRONMENT_NOT_RETRYABLE`；修订变化返回 `REVISION_CONFLICT`。失败后重新读取环境详情与任务日志再决定是否继续重试。

### POST `/api/v1/accounts/{account_id}/execution-environments/{environment_id}/start`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key` 必填。Body、Query：无。
- 返回 HTTP 202 的账号 `TaskAcceptedDto`，任务类型 `execution_environment.start`。已运行环境只在重新证明所有权后幂等收敛；已停止环境重新创建 owner marker、启动真实浏览器并写入新证据。

### POST `/api/v1/accounts/{account_id}/execution-environments/{environment_id}/stop`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key` 必填。Body、Query：无。
- 返回 HTTP 202，任务类型 `execution_environment.stop`。停止前必须证明 PID、可执行文件、Profile、调试端口和 owner marker 同属该账号；无法证明时标记 `cleanup_failed/orphaned`，禁止误杀进程。

### POST `/api/v1/accounts/{account_id}/execution-environments/{environment_id}/checks`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key` 必填。Body、Query：无。
- 返回 HTTP 202，任务类型 `execution_environment.check`。任务读取真实进程与调试端口健康状态并更新资格和错误引用，不伪造可用状态。

### DELETE `/api/v1/accounts/{account_id}/execution-environments/{environment_id}`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key` 必填。Query `preserveUserFiles` 当前必须为 `true`，Body 无。
- 返回 HTTP 202，任务类型 `execution_environment.delete`。任务先安全停止受控浏览器，再软删除绑定记录；工作目录和用户文件始终保留。无法证明进程归属时失败封闭。

## Desktop 调用映射

| Desktop 函数 | Runtime 地址 |
| --- | --- |
| `listExecutionEnvironments` | `GET /accounts/{account_id}/execution-environments` |
| `getExecutionEnvironment` | `GET /accounts/{account_id}/execution-environments/{environment_id}` |
| `createExecutionEnvironment` | `POST /accounts/{account_id}/execution-environments` |
| `retryExecutionEnvironment` | `POST /accounts/{account_id}/execution-environments/{environment_id}/retry` |
| `startExecutionEnvironment` | `POST /accounts/{account_id}/execution-environments/{environment_id}/start` |
| `stopExecutionEnvironment` | `POST /accounts/{account_id}/execution-environments/{environment_id}/stop` |
| `checkExecutionEnvironment` | `POST /accounts/{account_id}/execution-environments/{environment_id}/checks` |
| `deleteExecutionEnvironment` | `DELETE /accounts/{account_id}/execution-environments/{environment_id}` |

表中地址省略统一前缀 `/api/v1`。组件不得直接 fetch；创建后必须通过账号任务客户端轮询或事件更新，并在终态重新读取候选资格。
