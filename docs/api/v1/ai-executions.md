# 账号 AI 执行 API v1

本文档是 P0-H `AIExecution Gateway` 与 Desktop 调用方式的唯一接口真源。接口只验证真实 AI 调用链，不创建脚本、分镜或其他 P0-I 业务对象。

## 1. 公共约束

- 前缀：`/api/v1/accounts/{account_id}/ai-executions`。
- 所有端点要求 Runtime Session、有效许可证、Host / Origin 门禁和 `X-Request-ID` 上下文。
- `account_id` 是强隔离边界；跨账号读取统一返回 `AI_EXECUTION_NOT_FOUND`，不暴露资源是否存在。
- `preflight` 与 `create` 要求 `If-Match` 等于当前账号聚合修订。
- `create`、`cancel`、`retry` 要求 `Idempotency-Key`；同键不同请求返回 `REQUEST_CONFLICT`。
- 请求正文、Prompt、知识正文、Credential、Provider URL 与绝对路径不进入任务快照、事件、日志或 evidence。
- 成功信封为 `{ "ok": true, "data": ..., "meta": ...? }`；失败信封遵循 [errors.md](errors.md)。

## 2. 接口总览

| 方法 | 地址 | Body / Query | 成功 |
| --- | --- | --- | --- |
| POST | `/api/v1/accounts/{account_id}/ai-executions/preflight` | `AIExecutionPreflightInput` | 200 `AIExecutionPreflightDto` |
| POST | `/api/v1/accounts/{account_id}/ai-executions` | `AIExecutionCreateInput` | 202 `AIExecutionAcceptedDto` |
| GET | `/api/v1/accounts/{account_id}/ai-executions` | `status?`、`capabilityKey?`、`cursor?`、`limit?` | 200 `AIExecutionPageDto` |
| GET | `/api/v1/accounts/{account_id}/ai-executions/{execution_id}` | 无 | 200 `AIExecutionDetailDto` |
| POST | `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/cancel` | 无 | 200 `AIExecutionDetailDto` |
| POST | `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/retry` | `{ "mode": "same_snapshot" }` | 202 `AIExecutionAcceptedDto` |
| GET | `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/outputs/{output_id}` | 无 | 200 `AIExecutionOutputDto` |
| GET | `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/evidence` | 无 | 200 `AIExecutionEvidenceDto` |

## 3. 预检与创建

### POST `/api/v1/accounts/{account_id}/ai-executions/preflight`

Headers：`Authorization`、`If-Match` 必填；`X-Request-ID`、`X-Operation-ID` 可选。

请求字段：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `capabilityKey` | string | 当前实现入口使用 `script_generation` |
| `knowledgeSnapshotId` | stable id | 必须属于当前账号且具有 v2 文本块清单 |
| `recipeVersionId` | stable id | 必须是当前账号已激活、有效版本 |
| `inputSummary.estimatedInputUnits` | integer | `0..10000000`，只用于预检估算 |
| `executionPolicy` | object | 可覆盖 timeout、fallback、retry、cost 与 currency，但不能放宽冻结 Route 上限 |

结构示例：

```json
{
  "capabilityKey": "script_generation",
  "knowledgeSnapshotId": "ksnap_example",
  "recipeVersionId": "recipe_example",
  "inputSummary": {"estimatedInputUnits": 16},
  "executionPolicy": {
    "timeoutMs": 30000,
    "allowFallback": true,
    "maxRetries": 1,
    "maxCostMicros": 1000,
    "currency": "USD"
  }
}
```

返回 `ready=true`、冻结候选数量、阻断问题、唯一修复动作、成本区间与 `snapshotPreviewHash`。预检不创建任务，也不调用 Provider。

### POST `/api/v1/accounts/{account_id}/ai-executions`

Headers：在预检基础上增加 `Idempotency-Key`。

Body 与预检相同，但使用 `input` JSON 对象替代 `inputSummary`。Runtime 先把输入保存为账号受控引用，再在同一事务创建 dependency snapshot、execution snapshot、candidate、AIExecution、`ai.execution` RuntimeTask 与 outbox。任务快照只含：

```json
{
  "executionId": "aiexec_example",
  "snapshotHash": "sha256"
}
```

返回 HTTP 202：

```json
{
  "ok": true,
  "data": {
    "executionId": "aiexec_example",
    "taskId": "task_example",
    "accountId": "acct_example",
    "capabilityKey": "script_generation",
    "status": "queued",
    "snapshotHash": "sha256",
    "revision": 1,
    "createdAt": "RFC3339"
  },
  "meta": {
    "invalidations": [
      "account:acct_example:ai-executions",
      "account:acct_example:tasks"
    ],
    "idempotentReplay": false
  }
}
```

上述值仅说明字段形态，不是业务或验收结果。

## 4. 列表与详情

### GET `/api/v1/accounts/{account_id}/ai-executions`

- `status` 可重复传入：`queued | running | cancelling | failed | completed`。
- `capabilityKey` 可选。
- `limit` 与 `cursor` 使用 Runtime 公共游标；游标绑定账号与筛选条件，跨账号或改筛选后返回 `REQUEST_VALIDATION_FAILED`。
- 返回 `data.items` 与 `meta.nextCursor`；不返回输入或输出正文。

### GET `/api/v1/accounts/{account_id}/ai-executions/{execution_id}`

详情包含：

- execution 状态、completion / failure、成本状态、任务与重试来源；
- 冻结 snapshot 的资源 ID、revision 与 hash；
- 候选、AIJob、usage、输出安全摘要与脱敏错误；
- `availableActions=cancel | retry_same_snapshot | view_output`。

`costStatus=unavailable` 表示不得把费用显示为 0。`failureKind=result_unknown` 表示请求已经发送，但 Provider 终态和费用无法证明。

## 5. 取消与同快照重试

### POST `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/cancel`

- Body 必须为空；要求 `Idempotency-Key`。
- 先执行账号门禁，再取消对应 RuntimeTask；只停止 Desktop 轮询不算取消。
- 终态重复取消返回当前详情，不新增事件。
- 已发送但未取得 reported usage 时，取消结果使用 `costStatus=unavailable`，UI 必须提示远端可能已产生费用。

### POST `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/retry`

- Body 固定为 `{ "mode": "same_snapshot" }`；要求 `Idempotency-Key`。
- 仅 failed / completed execution 可重试。
- 新建 execution、task、jobs 与输入受控引用；设置 `retryOfExecutionId`。
- 输入、Prompt、Recipe、Route、知识、候选和 `snapshotHash` 必须与原执行一致；不会解析当前最新配置，也不会自动合并两次成本。

## 6. 输出与证据

### GET `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/outputs/{output_id}`

- 仅当前账号可读；响应 Header 固定 `Cache-Control: private, no-store`。
- 文本或 JSON 正文只在此端点返回，不进入 Toast、事件、日志、浏览器持久缓存或 evidence。
- 成本越界输出标记 `quarantined=true`，正文读取返回 `AI_COST_LIMIT_EXCEEDED`。
- 受控文件摘要与 `contentHash` 不一致时返回 `AI_EXECUTION_INVALID`。

### GET `/api/v1/accounts/{account_id}/ai-executions/{execution_id}/evidence`

返回 `capabilityKey`、执行终态、snapshot hash、job、reported usage 标记、输出 hash / 大小 / Schema 状态和错误 code / logId。成功任务还会返回以下 H5 安全摘要：

- `provider.adapterType` 固定为 `openai_compatible`；Provider 引用、模型 ID 与 validation run 仅返回 SHA-256。
- `validationStage=real_small_call`、`validationStatus=verified`，用于证明活动候选绑定了当前修订的真实小调用。
- `responseIdHash`、`durationMs` 与 `usageReported`；不返回 Provider response ID 原文。

它不返回 Credential、Provider URL、Provider / 模型明文、Prompt、输入、输出正文、知识正文或路径。该接口只提供账号隔离的 Runtime allowlist 投影，不能独立宣称 H5 完成。

目标机器人工验收时，先把本接口成功信封保存为临时 Runtime evidence，再使用当前制品 `release-manifest.json` 生成最终 allowlist：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File tests/manual/p0-h-real-provider-evidence.ps1 `
  -EvidencePath <最终脱敏证据.json> `
  -RuntimeEvidencePath <Runtime-evidence.json> `
  -ManifestPath <当前制品-release-manifest.json>
```

脚本不读取 API Key；最终文件只保留四制品哈希、Provider / 模型 / validation 摘要、execution / response / output 摘要、reported usage、可验证成本与 redaction 结果。`controlled_contract`、`cost.source=unavailable`、estimated cost 缺少 `pricingRevision`、额外字段或任一制品哈希不一致都会失败。

H5 使用两阶段发布，避免重新打包改变已经人工验收的哈希：

1. 先运行 `node scripts/build-windows-release.mjs --channel test` 生成待验收 `0.5.0` 制品与 Manifest。
2. 在该制品中完成人工真实 Provider 链并生成最终脱敏证据。
3. 再运行 `node scripts/build-windows-release.mjs --channel test --target-ai-evidence <最终脱敏证据.json>`；此模式只原子附加并复验 H5 证据，不重建四个制品。

Production 同样先生成固定制品，再附加 H5 证据；只有干净源码、全部 Production 证据和四制品绑定均通过时才允许 `--promote` 更新 `current.json`。

## 7. 状态、重试与恢复

执行状态：

```text
queued -> running -> completed+succeeded
                 -> completed+cancelled
                 -> failed+error|timed_out|restart_interrupted|result_unknown
```

- retry 只处理明确安全的发送前连接失败、429 和可恢复 5xx；指数退避带抖动，并在上限内尊重 `Retry-After`。
- post-send 网络断开或总超时进入 `result_unknown`，禁止自动 retry / fallback。
- fallback 只在冻结 Route 允许且当前错误可回退时按候选顺序执行。
- 并发取系统、Provider revision 与 Route revision 三者最小值；排队超时与 Provider 调用超时分开计算。
- Runtime 重启时，未发送请求进入 `restart_interrupted`；已有活动 Job 进入 `result_unknown`；两者都同步为失败且不自动外呼。

## 8. 错误码与恢复动作

| 错误码 | HTTP | 含义 | 恢复 |
| --- | ---: | --- | --- |
| `AI_EXECUTION_DISABLED` | 503 | 配置总线未开启 Gateway | 在系统设置开启并重启要求的组件 |
| `AI_EXECUTION_INVALID` | 409 / 422 | 输入、输出或受控内容不完整 | 修正输入或重新创建 |
| `AI_EXECUTION_NOT_FOUND` | 404 | 当前账号不可见 | 刷新当前账号列表 |
| `AI_EXECUTION_STATE_CONFLICT` | 409 | 终态或修订已变化 | GET 最新详情后重试 |
| `AI_RECIPE_STALE` | 409 | Recipe 与 AI 配置修订不一致 | 创建并激活 Recipe 新版本 |
| `AI_ROUTE_INCOMPLETE` | 409 | 没有有效活动 Route | 前往 AI 设置修复 Route |
| `AI_PROVIDER_REAL_VALIDATION_REQUIRED` | 409 | 候选当前修订未完成真实小调用 | 重新运行四阶段检查 |
| `AI_KNOWLEDGE_SNAPSHOT_NOT_READY` | 409 | 知识快照与派生块不一致 | 重新索引并建立快照 |
| `AI_COST_UNAVAILABLE` | 409 | 硬预算缺少定价证据 | 配置 pricing 或取消硬预算 |
| `AI_COST_LIMIT_EXCEEDED` | 409 | 预估或实际成本越界 | 调整预算；隔离输出不能直接使用 |
| `AI_USAGE_UNAVAILABLE` | 409 | Provider 未返回 required usage | 使用支持 usage 的模型 |
| `AI_PROVIDER_AUTH_FAILED` | 401 | Provider 鉴权失败 | 轮换凭据并重新验证 |
| `AI_PROVIDER_RATE_LIMITED` | 429 | Provider 限流 | 等待 Retry-After 或显式重试 |
| `AI_PROVIDER_TIMEOUT` | 504 | 发送前或队列超时 | 稍后重试或调整冻结策略 |
| `AI_PROVIDER_RESULT_UNKNOWN` | 502 | 发送后终态与费用不可证明 | 阅读费用提示后按原快照重试 |
| `AI_PROVIDER_RESPONSE_INVALID` | 502 | 响应无法解析或不符合 Schema | 查看脱敏日志并切换模型 |
| `AI_ALL_CANDIDATES_FAILED` | 502 | 冻结候选均失败 | 查看 Job 证据并修复 Route |
| `AI_EVIDENCE_REDACTION_FAILED` | 500 | evidence 未通过敏感信息检查 | 按 `log_id` 诊断，禁止导出 |

## 9. Desktop 调用映射

| Desktop 模块 | Runtime 调用 | 缓存 / 交互 |
| --- | --- | --- |
| `ai-execution-operations.ts` | preflight、create、cancel、retry | 统一生成幂等键，不直接 fetch |
| `ai-execution-store.ts` | list、detail、output | 缓存键以 `account:${accountId}:ai-executions` 开头 |
| `AIExecutionLauncher.vue` | 预检后创建 | dependency blocked 只展示一个推荐修复动作 |
| `AIExecutionStatePanel.vue` | 列表与状态矩阵 | loading / empty / normal / error / cancelled |
| `AIExecutionDetailPanel.vue` | detail、output、evidence | 默认折叠技术详情；账号切换立即清空 |

账号切换会取消旧 HTTP 请求、停止旧轮询并清空详情，但不会取消后台 execution；迟到响应通过账号 generation 校验后丢弃。事件 Topic 为 `account:{account_id}:ai-executions`，断线后先按游标重放，再以 HTTP 详情为最终真源。
