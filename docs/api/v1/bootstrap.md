# Bootstrap、许可证与目录 API v1

本文件列出的五个端点均为 P0-B 已注册实现；未列出的 Bootstrap 草案不构成契约。

公共门禁、框架错误与未预期 `INTERNAL_ERROR` 见 [errors.md](errors.md)；各端点条目补充其领域错误和恢复动作。

## 接口总览

| 方法 | 地址 | Active 许可证 | 幂等键 | 成功状态 |
| --- | --- | --- | --- | ---: |
| `GET` | `/api/v1/bootstrap/status` | 豁免 | 无 | 200 |
| `GET` | `/api/v1/bootstrap/license` | 豁免 | 无 | 200 |
| `POST` | `/api/v1/bootstrap/license/activate` | 豁免 | 必填 | 200 |
| `POST` | `/api/v1/bootstrap/directories/initialize` | 必须 | 必填 | 200 |
| `POST` | `/api/v1/bootstrap/self-checks` | 必须 | 必填 | 202 |

“许可证豁免”只表示允许许可证尚未激活；所有端点仍要求合法 Host、可接受 Origin 和 Runtime Session。公共规则见 [README.md](README.md)。

Desktop 已通过统一 Runtime 适配层调用这些 v1 端点；legacy 客户端使用旧 DTO，不能直接映射到本文件。

## 公共 DTO

### `LicenseStatusDto`

```json
{
  "status": "active",
  "machineCode": "<current-machine-code>",
  "machineCodeMasked": "<masked-machine-code>",
  "expiresAt": null,
  "activatedAt": "2026-07-26T08:00:00Z",
  "blockingIssue": null,
  "revision": 1,
  "machineIdentityStatus": "verified",
  "machineIdentityAlgorithm": "v2",
  "matchedFactorCount": 3,
  "mismatchedFactorCount": 0,
  "unavailableFactorCount": 0
}
```

`status` 只能是 `missing | active | expired | invalid | machine_mismatch`。当前许可证适配器只接受受支持的永久许可证，因此成功状态的 `expiresAt` 为 `null`。
`machineIdentityStatus` 只能是 `verified | degraded | unavailable | mismatch`。`degraded` 表示当前仅有一项稳定因子与受保护基线匹配，许可证仍可使用但 UI 必须提示稍后复检；`unavailable` 不会以成功 DTO 返回，而会转换为可重试的 HTTP 503。

### `DirectoryReportDto`

```json
{
  "status": "ready",
  "workspaceRootDisplay": "…\\runtime\\data",
  "directories": [
    {
      "key": "data_root",
      "status": "ready",
      "writable": true
    }
  ],
  "issues": [],
  "revision": 1
}
```

以上为 DTO 结构缩略示例；真实报告会返回 `data_root`、`projects`、`assets`、`renders`、`cache`、`exports`、`logs`、`licenses` 八个目录项。`workspaceRootDisplay` 是截断后的展示路径，不应当作可重新提交的文件引用。

## GET `/api/v1/bootstrap/status`

返回许可证、目录、Runtime 和媒体工具的组合状态。许可证缺失或无效会体现在 `data.license` 与 `data.blockingIssues` 中，正常情况下仍返回 HTTP 200。

### 请求

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path、Query、Body：无。
- Active 许可证：不要求。

### 成功

```json
{
  "ok": true,
  "data": {
    "license": {
      "status": "active",
      "machineCode": "<current-machine-code>",
      "machineCodeMasked": "<masked-machine-code>",
      "expiresAt": null,
      "activatedAt": "2026-07-26T08:00:00Z",
      "blockingIssue": null,
      "revision": 1,
      "machineIdentityStatus": "verified",
      "machineIdentityAlgorithm": "v2",
      "matchedFactorCount": 3,
      "mismatchedFactorCount": 0,
      "unavailableFactorCount": 0
    },
    "directories": {
      "status": "ready",
      "workspaceRootDisplay": "…\\runtime\\data",
      "directories": [
        {
          "key": "data_root",
          "status": "ready",
          "writable": true
        },
        {
          "key": "projects",
          "status": "ready",
          "writable": true
        },
        {
          "key": "assets",
          "status": "ready",
          "writable": true
        },
        {
          "key": "renders",
          "status": "ready",
          "writable": true
        },
        {
          "key": "cache",
          "status": "ready",
          "writable": true
        },
        {
          "key": "exports",
          "status": "ready",
          "writable": true
        },
        {
          "key": "logs",
          "status": "ready",
          "writable": true
        },
        {
          "key": "licenses",
          "status": "ready",
          "writable": true
        }
      ],
      "issues": [],
      "revision": 1
    },
    "runtime": {
      "status": "ready",
      "version": "0.4.8"
    },
    "mediaTools": {
      "status": "ready",
      "issues": []
    },
    "canContinue": true,
    "blockingIssues": [],
    "revision": 1
  }
}
```

### 错误、超时与恢复

- 公共门禁错误。
- `MACHINE_IDENTITY_RETRY_REQUIRED`：稳定机器因子不足，HTTP 503；稍后重试，不得重新签发许可证或判定机器不匹配。
- `MACHINE_IDENTITY_STORE_UNAVAILABLE`：受保护机器身份基线损坏或不可读，HTTP 503；根据 `log_id` 修复安全存储，不得静默重建基线。
- `LICENSE_STORE_UNAVAILABLE`：许可证记录、安全存储或激活校验不可用，HTTP 503；查看 `log_id` 后重试。
- `RUNTIME_NOT_READY`：Bootstrap 服务未装配，HTTP 503。
- 本端点没有幂等键或端点级超时参数。

### 事件、敏感边界与 legacy

- 只读，不产生 Runtime 事件。
- 不返回许可证原文、目录绝对根路径或媒体工具命令行。完整机器码只通过本地 Runtime Session 保护的 Bootstrap 响应提供给首启页复制，不写入普通日志。
- legacy `/api/bootstrap/readiness`、`/api/license/status` 与 `/api/settings/health` 是始终注册的受控兼容适配器：前者从同一 Bootstrap 状态服务转换旧就绪 DTO，许可证状态接口只转换旧许可证 DTO，health 还聚合同一诊断服务与系统任务摘要；它们都不是本组合 DTO 的等形响应，生产模式强制本机会话门禁，其中 health 还要求 active 许可证。

## GET `/api/v1/bootstrap/license`

返回实时许可证状态，不要求许可证已经 active。

### 请求

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path、Query、Body：无。

### 成功

```json
{
  "ok": true,
  "data": {
    "status": "missing",
    "machineCode": "<current-machine-code>",
    "machineCodeMasked": "<masked-machine-code>",
    "expiresAt": null,
    "activatedAt": null,
    "blockingIssue": {
      "code": "LICENSE_MISSING",
      "message": "许可证尚未激活"
    },
    "revision": 0,
    "machineIdentityStatus": "verified",
    "machineIdentityAlgorithm": "v2",
    "matchedFactorCount": 3,
    "mismatchedFactorCount": 0,
    "unavailableFactorCount": 0
  }
}
```

### 错误、超时与恢复

- 公共门禁错误。
- `MACHINE_IDENTITY_RETRY_REQUIRED`：HTTP 503；等待设备信息源恢复后重试。
- `MACHINE_IDENTITY_STORE_UNAVAILABLE`：HTTP 503；检查安全存储与诊断日志，禁止重新生成机器基线。
- `LICENSE_STORE_UNAVAILABLE`：HTTP 503；根据 `log_id` 检查安全存储或机器码服务。
- `RUNTIME_NOT_READY`：HTTP 503。
- 本端点没有幂等键或端点级超时参数。

### 事件、敏感边界与 legacy

- 只读，不产生 Runtime 事件。
- 返回 Runtime 根据当前 PC 稳定硬件信息生成的完整机器码和掩码机器码，供本机首启页展示与复制；不返回许可证密钥或安全存储引用，完整机器码不得进入普通日志。
- legacy `GET /api/license/status` 调用同一许可证状态服务并转换为旧字段和 legacy 错误信封；该受控适配器在生产模式仍注册，但会强制本机会话门禁。

## POST `/api/v1/bootstrap/license/activate`

Runtime 自动读取本机机器码并验证许可证，把许可证原文写入安全存储；数据库保存机器绑定标识、安全引用和掩码信息。

### 请求

- Headers：
  - `Authorization` 必填。
  - `Idempotency-Key` 必填。
  - `X-Operation-ID` 可选。
  - `Content-Type: application/json`。
- Path、Query：无。
- Body：

```json
{
  "licenseKey": "<license-key>"
}
```

`licenseKey` 长度为 1 至 16384；Body 不允许额外字段。机器码由 Runtime 自动读取，Desktop 不提交。为兼容旧客户端，Body 仍临时接受可选 `machineCode`（1 至 128），提供时只作为一致性校验，不作为实际绑定来源。

### 成功

```json
{
  "ok": true,
  "data": {
    "status": "active",
    "machineCode": "<current-machine-code>",
    "machineCodeMasked": "<masked-machine-code>",
    "expiresAt": null,
    "activatedAt": "2026-07-26T08:00:00Z",
    "blockingIssue": null,
    "revision": 1,
    "machineIdentityStatus": "verified",
    "machineIdentityAlgorithm": "v2",
    "matchedFactorCount": 3,
    "mismatchedFactorCount": 0,
    "unavailableFactorCount": 0
  },
  "meta": {
    "revision": 1,
    "invalidations": ["bootstrap"]
  }
}
```

### 错误、幂等、超时与恢复

- 公共门禁错误；不要求许可证预先 active。
- `REQUEST_VALIDATION_FAILED`：缺少或非法 `Idempotency-Key`，或 Body 不符合 Schema，HTTP 422。
- `LICENSE_MACHINE_MISMATCH`：许可证签发机器码与 Runtime 当前机器码不一致，或 legacy 客户端提交的可选机器码不一致，HTTP 403；复制当前机器码后重新签发许可证。
- `MACHINE_IDENTITY_RETRY_REQUIRED`：采集证据不足，HTTP 503；稍后重试，不得映射为机器不匹配。
- `MACHINE_IDENTITY_STORE_UNAVAILABLE`：受保护机器身份基线不可读，HTTP 503；根据日志修复安全存储。
- `LICENSE_INVALID`：许可证签名或类型无效，HTTP 403。
- `LICENSE_STORE_UNAVAILABLE`：激活依赖、许可证仓储、安全存储或机器码服务不可用，HTTP 503。
- `RUNTIME_NOT_READY`：HTTP 503。
- 同一许可证已经 active 时会返回当前状态；当前实现不提供通用的 HTTP 响应重放仓储。
- 没有 Body 超时字段；激活依赖超时由许可证适配器控制。

### 事件

成功后写入 outbox：

```json
{
  "schemaVersion": 1,
  "eventId": "evt_bootstrap_license_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "eventType": "bootstrap.license.changed",
  "topic": "system:bootstrap",
  "sequence": 1,
  "occurredAt": "2026-07-26T08:00:00Z",
  "accountId": null,
  "resourceType": null,
  "resourceId": null,
  "taskId": null,
  "revision": 1,
  "payload": {
    "status": "active",
    "invalidations": ["bootstrap", "license"]
  }
}
```

许可证数据库记录与 outbox 事件在同一 SQL 事务内提交。许可证原文先写安全存储；若数据库或事件事务失败，当前实现会删除本次新建的安全存储项，或恢复被覆盖的旧值，然后让 HTTP 失败。对已经 active 的同一许可证重放时，Runtime 会按幂等键稳定补齐或核对同一事件。客户端仍应以后续 `GET /bootstrap/license` 为最终真源。

### 敏感边界与 legacy

- 许可证原文只用于本次请求和安全存储，不进入返回、事件或普通日志。
- 完整机器码仅用于本机展示和许可证绑定，不进入普通日志；审计事件只记录掩码值。
- legacy `POST /api/license/activate` 调用同一激活服务，但 Body 使用 `activationCode`，缺少幂等键时由适配器从许可证生成稳定键，并返回旧 DTO 与 legacy 错误码；该受控适配器在生产模式仍注册并强制本机会话门禁。

## POST `/api/v1/bootstrap/directories/initialize`

创建并检查 Runtime 数据根目录及其受控子目录。

### 请求

- Headers：
  - `Authorization`、`Idempotency-Key` 必填。
  - `X-Operation-ID` 可选。
  - `Content-Type: application/json`。
- Path、Query：无。
- Body：

```json
{
  "workspaceRootRef": null
}
```

`workspaceRootRef` 可为 `null` 或 1 至 512 字符的受控引用。当前容器没有装配外部工作区引用解析器，因此 P0-B 可用值只有 `null`；提交非空引用会返回 `DIRECTORY_CREATE_FAILED`，不得提交原始任意路径代替受控引用。

### 成功

```json
{
  "ok": true,
  "data": {
    "status": "ready",
    "workspaceRootDisplay": "…\\runtime\\data",
    "directories": [
      {
        "key": "data_root",
        "status": "ready",
        "writable": true
      },
      {
        "key": "projects",
        "status": "ready",
        "writable": true
      },
      {
        "key": "assets",
        "status": "ready",
        "writable": true
      },
      {
        "key": "renders",
        "status": "ready",
        "writable": true
      },
      {
        "key": "cache",
        "status": "ready",
        "writable": true
      },
      {
        "key": "exports",
        "status": "ready",
        "writable": true
      },
      {
        "key": "logs",
        "status": "ready",
        "writable": true
      },
      {
        "key": "licenses",
        "status": "ready",
        "writable": true
      }
    ],
    "issues": [],
    "revision": 1
  },
  "meta": {
    "revision": 1,
    "invalidations": ["bootstrap"]
  }
}
```

首次创建的目录项可返回 `created`；已存在且可写时返回 `ready`。

### 错误、幂等、超时与恢复

- 公共门禁与 active 许可证错误。
- `REQUEST_VALIDATION_FAILED`：幂等键或 Body 无效，HTTP 422。
- `DIRECTORY_CREATE_FAILED`：受控引用不可解析、目录创建失败或目录不可写，HTTP 500；响应必含 `log_id`，先据此定位失败阶段，再修复引用或权限后重试。
- `RUNTIME_NOT_READY`：HTTP 503。
- 创建操作本身可重复执行；当前实现要求幂等键，并用其派生稳定事件 ID，但不保存通用 HTTP 响应重放记录。同一键只能表达同一目录初始化意图。
- 没有端点级超时参数。

### 事件

成功后写入：

```json
{
  "schemaVersion": 1,
  "eventId": "evt_bootstrap_directories_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "eventType": "bootstrap.directories.changed",
  "topic": "system:bootstrap",
  "sequence": 2,
  "occurredAt": "2026-07-26T08:00:01Z",
  "accountId": null,
  "resourceType": null,
  "resourceId": null,
  "taskId": null,
  "revision": 1,
  "payload": {
    "status": "ready",
    "invalidations": ["bootstrap", "directories"]
  }
}
```

目录创建先于独立 outbox 提交，文件系统与数据库无法组成同一事务。事件按幂等键使用稳定 ID；事件写入失败会让 HTTP 失败，但不会删除已经创建的目录。客户端应使用同一键重试，并重新读取 Bootstrap 状态对账。

### 敏感边界与 legacy

- 返回展示路径经过截断；事件不携带路径。
- legacy `POST /api/bootstrap/initialize-directories` 调用同一目录服务，固定使用 Runtime 默认根目录，并在缺少幂等键时补充稳定键；它返回旧目录 DTO，在生产模式仍注册且要求本机会话与 active 许可证。

## POST `/api/v1/bootstrap/self-checks`

创建持久化系统任务，异步检查数据库、目录、媒体工具和 Runtime 状态。

### 请求

- Headers：
  - `Authorization`、`Idempotency-Key` 必填。
  - `X-Operation-ID` 可选。
  - `Content-Type: application/json`。
- Path、Query：无。
- Body：

```json
{
  "checks": ["database", "directories", "media_tools", "runtime"]
}
```

`checks` 必须包含 1 至 4 项；每项只能是 `database | directories | media_tools | runtime`；Body 不允许额外字段。重复项会在任务快照前去重。

### 成功

HTTP 202：

```json
{
  "ok": true,
  "data": {
    "taskId": "task_0123456789abcdef0123456789abcdef",
    "scope": "system",
    "accountId": null,
    "taskType": "bootstrap.self_check",
    "status": "queued",
    "cancellable": true,
    "createdAt": "2026-07-26T08:00:00Z"
  },
  "meta": {
    "invalidations": ["system:tasks"]
  }
}
```

### 错误、幂等、超时与恢复

- 公共门禁与 active 许可证错误。
- `REQUEST_VALIDATION_FAILED`：幂等键缺失或检查项无效，HTTP 422。
- `SELF_CHECK_ALREADY_RUNNING`：系统作用域已有自检任务活动，HTTP 409；错误 `meta.taskId` 指向现有任务。
- `TASK_IDEMPOTENCY_CONFLICT`：同一幂等键用于不同检查 payload，HTTP 409。
- `TASK_HANDLER_NOT_FOUND`：任务处理器未装配，HTTP 503。
- `TASK_SNAPSHOT_INVALID`：受控任务快照校验失败，通常为 HTTP 422。
- `RUNTIME_NOT_READY`：任务服务未就绪，HTTP 503。
- 相同幂等键和相同 payload 在任务仍为 `queued` 时返回同一任务；任务进入其他状态后再次使用该键会返回 `SELF_CHECK_ALREADY_RUNNING`。要发起一次新的检查，应使用新的幂等键。
- 执行超时取配置总线 `runtime.taskTimeoutSeconds`，默认 900 秒，并受 `runtime.taskMaxTimeoutSeconds` 上限约束。HTTP 202 只表示接受任务。

### 事件和最终状态

- Topic：`system:tasks`。
- 当前任务事件：`task.queued`、`task.started`、`task.progress`、`task.cancelling`、`task.completed`、`task.failed`。
- 最终状态通过 `GET /api/v1/system/tasks/{task_id}` 获取；WebSocket 事件不是数据库最终状态的替代品。
- 取消使用 `POST /api/v1/system/tasks/{task_id}/cancel`。

### 敏感边界与 legacy

- 任务快照只保存检查项、请求/操作关联标识和幂等键摘要，不保存 Runtime Session 或密钥。
- legacy `POST /api/bootstrap/runtime-selfcheck` 调用同一持久任务入口，固定执行四项检查，并把接受结果转换为旧自检报告；缺少幂等键时使用按分钟滚动的兼容键。该适配器在生产模式仍注册且要求本机会话与 active 许可证。
