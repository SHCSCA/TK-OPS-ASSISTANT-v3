# 系统配置与诊断 API v1

本文件描述已注册的系统配置与诊断接口，以及 P0-C 新增的账号分页、普通写幂等和知识索引策略键。所有接口均为系统作用域、要求 active 许可证，并遵循 [README.md](README.md) 的 Host、Origin、Runtime Session、请求关联 Header 和统一信封。P0-C 已通过阶段验收。

公共错误码和 legacy 字符串映射见 [errors.md](errors.md)；下文逐端点列出领域错误和恢复动作。

## 接口总览

| 方法 | 地址 | `If-Match` | `Idempotency-Key` | 成功状态 |
| --- | --- | --- | --- | ---: |
| `GET` | `/api/v1/system/config` | 无 | 无 | 200 |
| `PATCH` | `/api/v1/system/config` | 必填 | 无 | 200 |
| `GET` | `/api/v1/system/diagnostics` | 无 | 无 | 200 |
| `GET` | `/api/v1/system/logs/{log_id}` | 无 | 无 | 200 |

P0-D 已通过 `apps/desktop/src/app/runtime-client/system-config.ts` 接入对应 v1 领域客户端；页面仍必须以本文件为唯一契约，不得直接复用 legacy DTO。

## 配置总线公开键

`GET` 返回全部公开可写键及其当前值。`PATCH` 只接受下表键；Provider 密钥、许可证原文、Runtime Session、Prompt 正文和任意文件内容不属于配置总线。

| 键 | 类型与范围 | 默认值 | 修改后需重启 |
| --- | --- | --- | --- |
| `logging.level` | `DEBUG \| INFO \| WARNING \| ERROR` | `INFO` | 否 |
| `media.ffprobePath` | 字符串，最长 1024 | `""` | 否 |
| `media.ffmpegPath` | 字符串，最长 1024 | `""` | 否 |
| `browser.executablePath` | 字符串，最长 1024 | `""` | 是 |
| `runtime.taskTimeoutSeconds` | 整数，1 至 86400 | `900` | 是 |
| `runtime.taskMaxTimeoutSeconds` | 整数，1 至 604800 | `86400` | 是 |
| `runtime.taskSnapshotMaxBytes` | 整数，1024 至 1048576 | `262144` | 是 |
| `runtime.taskMaxConcurrency` | 整数，1 至 32 | `4` | 是 |
| `http.retry.maxAttempts` | 整数，0 至 10 | `3` | 否 |
| `http.retry.baseDelayMs` | 整数，50 至 60000 | `500` | 否 |
| `websocket.reconnect.maxDelayMs` | 整数，100 至 60000 | `30000` | 否 |
| `websocket.replayLimit` | 整数，10 至 10000 | `500` | 是 |
| `websocket.publishBatchSize` | 整数，1 至 1000 | `100` | 是 |
| `websocket.publishIntervalMs` | 整数，50 至 10000 | `250` | 是 |
| `websocket.subscribeTimeoutSeconds` | 整数，1 至 60 | `10` | 是 |
| `websocket.sendTimeoutSeconds` | 整数，1 至 60 | `5` | 是 |
| `websocket.closeTimeoutSeconds` | 整数，1 至 30 | `3` | 是 |
| `websocket.maxMessageBytes` | 整数，1024 至 1048576 | `65536` | 是 |
| `websocket.legacyMaxMessageBytes` | 整数，256 至 65536 | `4096` | 是 |
| `migration.backupRetention` | 整数，1 至 50 | `5` | 是 |
| `provider.defaultTimeoutMs` | 整数，1000 至 600000 | `120000` | 是 |
| `provider.maxConcurrency` | 整数，1 至 32 | `4` | 是 |
| `accounts.requiredCapabilities` | 最多 32 个字符串；每项 1 至 128 字符 | `["script_generation","storyboard_generation","text_to_video"]` | 否 |
| `api.paginationDefaultLimit` | 整数，1 至 1000；不得大于最大值 | `50` | 否 |
| `api.paginationMaxLimit` | 整数，1 至 1000；不得小于默认值 | `200` | 否 |
| `api.mutationIdempotencyTtlSeconds` | 整数，3600 至 2592000 秒 | `604800` | 否 |
| `knowledge.index.maxSourceBytes` | 整数，1048576 至 104857600 字节 | `20971520` | 否 |
| `knowledge.index.urlTimeoutSeconds` | 整数，1 至 120 秒 | `15` | 否 |
| `knowledge.index.maxRedirects` | 整数，0 至 10 | `3` | 否 |
| `ui.theme` | `light \| dark \| system` | `system` | 否 |
| `ui.lastAccountId` | `null` 或 1 至 128 字符 | `null` | 否 |
| `ui.recentPages` | 最多 200 项的对象；键 1 至 128 字符，值 1 至 256 字符 | `{}` | 否 |
| `ui.compactWindow` | 布尔值 | `false` | 否 |

关系约束：

- `runtime.taskTimeoutSeconds` 不得大于 `runtime.taskMaxTimeoutSeconds`。
- `api.paginationDefaultLimit` 不得大于 `api.paginationMaxLimit`。
- 知识索引任务创建时冻结三个 `knowledge.index.*` 值和配置修订；在途任务不随之后的配置变更漂移。

## GET `/api/v1/system/config`

读取统一配置总线快照，可按键前缀筛选 `values`。

### 请求

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Query：`prefix` 可选，最长 128 字符；服务端去除首尾空白后执行区分大小写的 `startsWith` 筛选。
- Path、Body：无。
- 稳定级别：P0-B 路由已实现，P0-C 扩展公开键。

### 成功

以下完整示例对应 `?prefix=runtime.`：

```json
{
  "ok": true,
  "data": {
    "values": {
      "runtime.taskTimeoutSeconds": 900,
      "runtime.taskMaxTimeoutSeconds": 86400,
      "runtime.taskSnapshotMaxBytes": 262144,
      "runtime.taskMaxConcurrency": 4
    },
    "writableKeys": [
      "accounts.requiredCapabilities",
      "api.mutationIdempotencyTtlSeconds",
      "api.paginationDefaultLimit",
      "api.paginationMaxLimit",
      "browser.executablePath",
      "http.retry.baseDelayMs",
      "http.retry.maxAttempts",
      "knowledge.index.maxRedirects",
      "knowledge.index.maxSourceBytes",
      "knowledge.index.urlTimeoutSeconds",
      "logging.level",
      "media.ffmpegPath",
      "media.ffprobePath",
      "migration.backupRetention",
      "provider.defaultTimeoutMs",
      "provider.maxConcurrency",
      "runtime.taskMaxConcurrency",
      "runtime.taskMaxTimeoutSeconds",
      "runtime.taskSnapshotMaxBytes",
      "runtime.taskTimeoutSeconds",
      "ui.compactWindow",
      "ui.lastAccountId",
      "ui.recentPages",
      "ui.theme",
      "websocket.closeTimeoutSeconds",
      "websocket.legacyMaxMessageBytes",
      "websocket.maxMessageBytes",
      "websocket.publishBatchSize",
      "websocket.publishIntervalMs",
      "websocket.reconnect.maxDelayMs",
      "websocket.replayLimit",
      "websocket.sendTimeoutSeconds",
      "websocket.subscribeTimeoutSeconds"
    ],
    "restartRequiredKeys": [
      "browser.executablePath",
      "migration.backupRetention",
      "provider.defaultTimeoutMs",
      "provider.maxConcurrency",
      "runtime.taskMaxConcurrency",
      "runtime.taskMaxTimeoutSeconds",
      "runtime.taskSnapshotMaxBytes",
      "runtime.taskTimeoutSeconds",
      "websocket.legacyMaxMessageBytes",
      "websocket.closeTimeoutSeconds",
      "websocket.maxMessageBytes",
      "websocket.publishBatchSize",
      "websocket.publishIntervalMs",
      "websocket.replayLimit",
      "websocket.sendTimeoutSeconds",
      "websocket.subscribeTimeoutSeconds"
    ],
    "revision": 3
  },
  "meta": {
    "revision": 3,
    "invalidations": []
  }
}
```

`prefix` 只筛选 `data.values`，不裁剪 `writableKeys` 或 `restartRequiredKeys`。

### 错误、幂等、超时与恢复

- 公共门禁与 active 许可证错误。
- `REQUEST_VALIDATION_FAILED`：`prefix` 超长或请求关联 Header 无效，HTTP 422。
- `RUNTIME_NOT_READY`：配置总线未装配，HTTP 503。
- `INTERNAL_ERROR`：持久配置结构损坏或读取异常，HTTP 500；按 `log_id` 打开安全日志摘要。
- 只读请求不使用 `If-Match` 或幂等键；没有端点级超时参数。

### 事件、敏感边界与 legacy

- 只读，不产生事件或缓存失效。
- 返回值只包含公开配置键，不返回安全存储引用或环境密钥。
- legacy `GET /api/settings/config` 从同一配置总线读取后转换为嵌套旧 DTO；该受控适配器在生产模式仍注册，但要求本机会话与 active 许可证。

## PATCH `/api/v1/system/config`

以乐观修订锁更新一个或多个公开配置键。

### 请求

- Headers：
  - `Authorization`、`If-Match` 必填。
  - `X-Operation-ID` 可选。
  - `Content-Type: application/json`。
- `If-Match`：十进制修订号，可写为 `3` 或 `"3"`。
- Path、Query：无。
- Body：

```json
{
  "values": {
    "logging.level": "DEBUG",
    "ui.compactWindow": true
  }
}
```

`values` 内的键和值必须符合“配置总线公开键”表。当前 Schema 只把 `values` 定义为契约字段；客户端不得依赖额外顶层字段被忽略的实现细节。

### 成功

```json
{
  "ok": true,
  "data": {
    "values": {
      "logging.level": "DEBUG",
      "media.ffprobePath": "",
      "media.ffmpegPath": "",
      "browser.executablePath": "",
      "runtime.taskTimeoutSeconds": 900,
      "runtime.taskMaxTimeoutSeconds": 86400,
      "runtime.taskSnapshotMaxBytes": 262144,
      "runtime.taskMaxConcurrency": 4,
      "http.retry.maxAttempts": 3,
      "http.retry.baseDelayMs": 500,
      "websocket.reconnect.maxDelayMs": 30000,
      "websocket.replayLimit": 500,
      "websocket.publishBatchSize": 100,
      "websocket.publishIntervalMs": 250,
      "websocket.subscribeTimeoutSeconds": 10,
      "websocket.sendTimeoutSeconds": 5,
      "websocket.closeTimeoutSeconds": 3,
      "websocket.maxMessageBytes": 65536,
      "websocket.legacyMaxMessageBytes": 4096,
      "migration.backupRetention": 5,
      "provider.defaultTimeoutMs": 120000,
      "provider.maxConcurrency": 4,
      "accounts.requiredCapabilities": [
        "script_generation",
        "storyboard_generation",
        "text_to_video"
      ],
      "api.paginationDefaultLimit": 50,
      "api.paginationMaxLimit": 200,
      "api.mutationIdempotencyTtlSeconds": 604800,
      "knowledge.index.maxSourceBytes": 20971520,
      "knowledge.index.urlTimeoutSeconds": 15,
      "knowledge.index.maxRedirects": 3,
      "ui.theme": "system",
      "ui.lastAccountId": null,
      "ui.recentPages": {},
      "ui.compactWindow": true
    },
    "writableKeys": [
      "accounts.requiredCapabilities",
      "api.mutationIdempotencyTtlSeconds",
      "api.paginationDefaultLimit",
      "api.paginationMaxLimit",
      "browser.executablePath",
      "http.retry.baseDelayMs",
      "http.retry.maxAttempts",
      "knowledge.index.maxRedirects",
      "knowledge.index.maxSourceBytes",
      "knowledge.index.urlTimeoutSeconds",
      "logging.level",
      "media.ffmpegPath",
      "media.ffprobePath",
      "migration.backupRetention",
      "provider.defaultTimeoutMs",
      "provider.maxConcurrency",
      "runtime.taskMaxConcurrency",
      "runtime.taskMaxTimeoutSeconds",
      "runtime.taskSnapshotMaxBytes",
      "runtime.taskTimeoutSeconds",
      "ui.compactWindow",
      "ui.lastAccountId",
      "ui.recentPages",
      "ui.theme",
      "websocket.closeTimeoutSeconds",
      "websocket.legacyMaxMessageBytes",
      "websocket.maxMessageBytes",
      "websocket.publishBatchSize",
      "websocket.publishIntervalMs",
      "websocket.reconnect.maxDelayMs",
      "websocket.replayLimit",
      "websocket.sendTimeoutSeconds",
      "websocket.subscribeTimeoutSeconds"
    ],
    "restartRequiredKeys": [
      "browser.executablePath",
      "migration.backupRetention",
      "provider.defaultTimeoutMs",
      "provider.maxConcurrency",
      "runtime.taskMaxConcurrency",
      "runtime.taskMaxTimeoutSeconds",
      "runtime.taskSnapshotMaxBytes",
      "runtime.taskTimeoutSeconds",
      "websocket.legacyMaxMessageBytes",
      "websocket.closeTimeoutSeconds",
      "websocket.maxMessageBytes",
      "websocket.publishBatchSize",
      "websocket.publishIntervalMs",
      "websocket.replayLimit",
      "websocket.sendTimeoutSeconds",
      "websocket.subscribeTimeoutSeconds"
    ],
    "revision": 4
  },
  "meta": {
    "revision": 4,
    "invalidations": ["system-config"],
    "restartRequired": false
  }
}
```

实际响应返回完整配置快照。若更新后的 Runtime 刷新回调失败，配置和事件仍已提交，HTTP 200 的 `meta.warnings` 会包含“配置已保存，运行时刷新失败；请重启 Runtime 后生效”。

### 错误、修订、幂等与恢复

| 错误码 | HTTP | 默认含义 | 恢复动作 |
| --- | ---: | --- | --- |
| `CONFIG_REVISION_CONFLICT` | 412 | 缺少 `If-Match`，或当前修订已变化 | 重新 GET；并发修订冲突响应含 `meta.currentRevision`，缺少 Header 的响应不含该字段 |
| `REQUEST_VALIDATION_FAILED` | 422 | `If-Match` 格式、值类型、范围或跨键关系无效 | 按错误摘要修正 Header；响应含 `fieldErrors` 时逐项修正配置字段 |
| `CONFIG_KEY_NOT_WRITABLE` | 422 | `values` 包含未公开的配置键 | 移除该键，不要尝试写入密钥或内部配置 |
| `RUNTIME_NOT_READY` | 503 | 配置总线未装配 | 等待 Runtime 就绪后重新 GET |
| `INTERNAL_ERROR` | 500 | 配置与事件事务保存失败，或持久配置损坏 | 根据 `log_id` 诊断，并先 GET 确认当前修订 |

- 本端点不使用 `Idempotency-Key`。每次通过修订校验的 PATCH 都产生下一修订，即使提交空对象或与当前值相同；不得在未知结果后盲目重放原请求。
- 没有端点级超时参数。网络中断、`500` 或带 `warnings` 的 `200` 后，先 GET 对账，再决定是否用新修订提交。

### 事件与事务

配置文档和 outbox 事件在同一数据库事务内提交：

```json
{
  "schemaVersion": 1,
  "eventId": "evt_0123456789abcdef0123456789abcdef",
  "eventType": "config.changed",
  "topic": "system:config",
  "sequence": 8,
  "occurredAt": "2026-07-26T08:00:00Z",
  "accountId": null,
  "resourceType": null,
  "resourceId": null,
  "taskId": null,
  "revision": 4,
  "payload": {
    "changedKeys": ["logging.level", "ui.compactWindow"],
    "invalidations": ["system-config"]
  }
}
```

事件 payload 不是完整配置对象。`changedKeys` 当前表示本次 `values` 提交的键集合，即使值与原值相同也会列出。客户端收到事件后应失效 `system-config`，再 GET 最终快照。

### 敏感边界与 legacy

- 审计日志只记录 `changedKeys` 和修订，不记录凭据；事件也只含键名和失效范围。
- legacy `PUT /api/settings/config` 使用旧嵌套 DTO，不暴露 `If-Match` 修订锁；适配器只把日志级别、媒体工具路径和浏览器路径写入同一配置总线，旧 Runtime / Paths / AI 写入返回 `LEGACY_WRITE_UNSUPPORTED`。该适配器在生产模式仍注册并执行本机会话与 active 许可证门禁。

## GET `/api/v1/system/diagnostics`

读取 Runtime、数据库、目录、媒体工具和 sidecar 的安全诊断摘要。

### 请求

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Query：`sections` 可选，最长 128 字符；逗号分隔，可选值为 `runtime`、`database`、`directories`、`mediaTools`、`sidecar`。
- Path、Body：无。
- `sections` 省略或只含空白时返回全部分区；分区筛选始终保留 `checkedAt`。

### 成功

```json
{
  "ok": true,
  "data": {
    "runtime": {
      "status": "ready",
      "version": "0.4.8",
      "mode": "development"
    },
    "database": {
      "status": "ready",
      "schemaRevision": "0018_p0_runtime_kernel",
      "migrationChanged": false
    },
    "directories": {
      "status": "ready",
      "items": [
        {
          "key": "runtimeData",
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
        }
      ]
    },
    "mediaTools": {
      "status": "ready",
      "ffprobe": {
        "status": "ready",
        "source": "configured",
        "errorCode": null
      },
      "ffmpeg": {
        "status": "ready",
        "source": "configured",
        "errorCode": null
      }
    },
    "sidecar": {
      "status": "not_managed",
      "managed": false,
      "nextStage": "P0-F"
    },
    "checkedAt": "2026-07-26T08:00:00Z"
  }
}
```

当前状态取值：`database.status=ready|failed`；`directories.status=ready|attention`，目录项为 `ready|missing`；`mediaTools.status=ready|attention`，工具项为 `ready|unavailable`。媒体工具 `source` 来自真实解析结果，可为 `config`、`configured`、`bundled`、`path` 或 `fallback`，不保证等于示例值。

### 错误、幂等、超时与恢复

- 公共门禁与 active 许可证错误。
- `REQUEST_VALIDATION_FAILED`：未知分区或 Query 超限，HTTP 422。
- `RUNTIME_NOT_READY`：诊断服务未装配，HTTP 503。
- `DIAGNOSTICS_UNAVAILABLE`：媒体工具解析或诊断采集失败，HTTP 503；使用 `log_id` 定位后重试。
- 只读，无幂等键或端点级超时参数。

### 事件、敏感边界与 legacy

- 只读，不产生事件。
- 不返回数据库路径、目录绝对路径、媒体工具命令行、环境变量或原始异常。
- legacy `GET /api/settings/diagnostics` 与 `/api/settings/diagnostics/media` 从同一诊断服务转换旧 DTO；两条受控适配器在生产模式仍注册，但要求本机会话与 active 许可证。

## GET `/api/v1/system/logs/{log_id}`

按 v1 错误信封返回的 `log_id` 获取一条白名单字段诊断摘要。

### 请求

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`log_id` 必须匹配 `^log_[A-Za-z0-9]{8,128}$`。
- Query、Body：无。

### 成功

```json
{
  "ok": true,
  "data": {
    "logId": "log_0123456789abcdef0123456789abcdef",
    "severity": "error",
    "summary": "Runtime 未知请求异常",
    "errorCode": "INTERNAL_ERROR",
    "stage": null,
    "occurredAt": "2026-07-26T08:00:00Z",
    "suggestedActions": [
      "重试操作",
      "如仍失败请打开系统诊断"
    ],
    "requestId": "req_0123456789abcdef0123456789abcdef",
    "operationId": "op_0123456789abcdef0123456789abcdef"
  }
}
```

`severity` 为 `error | warning | info`。字段可为 `null` 的是 `errorCode`、`stage`、`requestId` 和 `operationId`。

### 错误、幂等、超时与恢复

| 错误码 | HTTP | 恢复动作 |
| --- | ---: | --- |
| `REQUEST_VALIDATION_FAILED` | 422 | 只使用错误信封原样返回的 `log_id` |
| `LOG_NOT_FOUND` | 404 | 日志引用不存在或已过期；重新触发诊断并使用新的引用 |
| `DIAGNOSTICS_UNAVAILABLE` | 503 | 日志文件暂不可读；修复权限或等待 Runtime 恢复 |
| `RUNTIME_NOT_READY` | 503 | 等待诊断服务完成装配 |

本端点只读，无幂等键或端点级超时参数。

### 事件、敏感边界与 legacy

- 不产生事件。
- 只返回 `SafeLogExcerpt` 白名单字段，不返回原始 JSONL、traceback、任意上下文、路径、请求 Body、Header 或密钥。
- legacy `GET /api/settings/logs` 不迁移旧全量日志列表语义，当前受控适配器固定返回 `LEGACY_WRITE_UNSUPPORTED`（HTTP 410），并指向本端点；它在生产模式仍注册，但要求本机会话与 active 许可证。
