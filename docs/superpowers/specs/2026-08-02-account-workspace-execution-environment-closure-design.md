# P0-G 账号工作区与执行环境生产闭环设计规格

> 日期：2026-08-02
> 状态：已批准，G0-G5 已完成，G6 实施中
> 已批准计划：`docs/superpowers/plans/2026-08-02-account-workspace-execution-environment-closure.md`
> 审计依据：`docs/audits/2026-08-02-production-chain-closure-audit.md`
> 实施顺序：G0 → G1 → G2 → G3 → G4 → G5 → G6 → G7
> 平台边界：Windows PC 桌面应用，不适配手机端

## 1. 规格目的

本规格锁定 P0-G 的模型、状态机、API、Tauri 桥、UI、任务、错误、迁移、测试和回退边界。规格批准后才能修改生产代码；实施中若需要改变本文的不变量、增加页面、引入高风险自动化或进入 P0-H/P0-I，必须先更新计划和规格。

P0-G 完成后的唯一主链是：

```text
正式制品启动并激活
→ 新建 TikTok 账号
→ 原生选择账号工作目录
→ Runtime 创建真实工作区、浏览器实例和执行绑定
→ 启动可见受控浏览器
→ 用户自行完成 TikTok 登录
→ 用户点击“我已完成登录”
→ Runtime 探测真实会话和账号身份
→ 连接进入 ready
→ 重启、切换账号和失败恢复仍保持隔离与可追踪
```

## 2. 已确认现状与兼容约束

### 2.1 必须复用

- `DeviceWorkspace`、`BrowserInstance`、`ExecutionBinding` 现有表和模型。
- `AccountConnection` 的账号唯一连接、修订和 `session_ref` / `credential_ref` 安全引用。
- `RuntimeTask` 的持久任务内核、幂等摘要、快照、超时、取消和恢复。
- `RuntimeEvent` 的账号 Topic、sequence、重放和 outbox。
- `/api/v1` 许可证门、请求上下文、统一信封、稳定错误码和 `If-Match`。
- Tauri Runtime Supervisor、动态端口、会话 token、单实例和 Windows 原生标题栏。
- Desktop Account Context、Runtime Client、六步账号向导和系统设置容器。

### 2.2 必须纠正

- `DeviceWorkspace.account_id` 与 `BrowserInstance.account_id` 当前允许空值；v1 新写必须强制账号所有权。
- `root_path` 当前是裸绝对路径且是唯一字段；v1 需要 `root_ref` 作为配置真源，绝对路径只能作为 Runtime 内部派生缓存。
- `BrowserInstance.runtime_evidence_json` 尚无严格版本 Schema，停止逻辑不能仅凭 PID。
- 正式连接 API 只能列候选和绑定，不能创建执行环境。
- `AccountConnection.auth_status` 创建后停在 `unknown`，没有生产登录和探测入口。
- Desktop 只缓存 taskId，没有恢复完整任务投影。
- Supervisor 已发送 `runtime-supervisor://status`，Desktop 尚未用 generation 驱动连接失效。

### 2.3 任务状态兼容决策

不新建第二套持久任务状态。数据库继续使用：

```text
status: queued | running | cancelling | completed | failed
completionKind: succeeded | cancelled | null
failureKind: error | timed_out | restart_interrupted | null
```

UI 可以把组合结果显示为“成功、已取消、超时、失败、重启中断”，但 API 和仓储仍遵循现有 `TaskDto`。计划中写到的 `succeeded/cancelled/timed_out` 是终态结果，不是新的 `status` 枚举。

## 3. 核心不变量

1. `DeviceWorkspace`、`BrowserInstance`、`ExecutionBinding`、`AccountConnection` 和登录尝试必须属于同一 `account_id`。
2. 正式 API 不接受绝对目录、PID、调试端口、Profile 路径、Cookie 或 token 作为用户输入。
3. 候选展示与绑定提交调用同一个 eligibility service；绑定事务提交前必须重新检查。
4. Runtime 只能停止能够证明由 TK-OPS 为该浏览器实例启动的进程；证据不足必须 fail-closed。
5. TikTok 密码、验证码和 Cookie 不进入 Vue、HTTP Body、数据库普通列、事件或日志。
6. 用户登录动作只能发生在可见浏览器；系统不自动填写凭据、不规避验证码或平台风控。
7. 所有创建、启动、停止、检查、登录探测、登出和删除动作均为持久任务。
8. 工作区目录、浏览器 Profile、连接状态、任务、日志、缓存和事件均按账号隔离。
9. Runtime 全局数据根与账号工作区是两类对象；P0-G 不热迁移 Runtime 数据根。
10. 旧 `/api/devices/*` 不再写入；旧数据不能被猜测归属。

## 4. 领域模型

### 4.1 聚合关系

```text
Account
  ├─ AccountConnection（每账号一条）
  ├─ AccountLoginSession（可有历史，最多一个活动尝试）
  └─ ExecutionEnvironment（API 聚合，不新增同名表）
       ├─ DeviceWorkspace
       ├─ BrowserInstance
       └─ ExecutionBinding（environmentId 等于 binding.id）
```

`ExecutionEnvironment` 是服务和 DTO 聚合，不复制三张实体表。创建命令会在单个数据库事务中建立完整 draft 聚合和对应 `RuntimeTask`；外部目录、Profile 和进程操作在任务阶段执行。

### 4.2 DeviceWorkspace

保留现有字段，新增：

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `root_ref` | Text nullable | v1 owned 对象必须非空且唯一 | Tauri 受控目录引用 |
| `ownership_state` | String | `owned / needs_reauthorization / legacy_unclaimed` | 区分正式对象与旧数据 |
| `revision` | Integer | `>=1` | 并发更新修订 |
| `error_code` | String nullable | 稳定错误码 | 最近工作区错误 |
| `error_log_id` | String nullable | 安全日志引用 | 不保存 traceback |

`root_path` 暂时保留用于旧 Runtime 兼容，但语义降为 resolver 派生缓存：

- 新建时由 Runtime 根据 `root_ref` 解析后写入规范路径。
- v1 API、事件、普通日志和 Desktop 类型不得返回 `root_path`。
- 重新授权后在同一事务更新 `root_ref` 和派生 `root_path`。
- P0-G 不删除该列；删除需另立兼容计划。

状态使用：

```text
draft → provisioning → offline → ready
                   ↘ failed
ready/offline/failed → deleting → deleted | cleanup_failed
```

数据库不物理保存 `deleted`；成功删除后只保留审计事件。`cleanup_failed` 保留对象和日志，允许重试。

### 4.3 BrowserInstance

复用现有 `process_id`、`debug_host`、`debug_port`、`executable_path`、`profile_path` 和 `runtime_evidence_json`。v1 新对象必须 `account_id` 非空且与 workspace 相同。

状态：

```text
stopped → starting → running
   ↑         ↘ failed ↘ unhealthy
stopping ← running/unhealthy
任意非删除态 → orphaned（所有权证据不足，不允许强杀）
```

`runtime_evidence_json` 固定 Schema v1：

```json
{
  "schemaVersion": 1,
  "runtimeGeneration": "runtime-generation-id",
  "executableCanonicalPathHash": "sha256",
  "profileCanonicalPathHash": "sha256",
  "processId": 14236,
  "processCreatedAt": "2026-08-02T09:00:00Z",
  "launchNonceHash": "sha256",
  "debugHost": "127.0.0.1",
  "debugPort": 49152,
  "ownerMarkerVersion": 1
}
```

原始路径继续保存在现有内部列中，但不进入普通日志和事件。Profile 内创建 `.tk-ops/runtime-owner.v1.json`，原子写入实例 ID、账号 ID、创建时间、nonce hash 和 generation。停止前同时核验：

1. PID 仍存在且创建时间一致。
2. 可执行文件规范路径哈希一致。
3. 命令行 `--user-data-dir` 指向该 Profile。
4. 调试端口监听进程就是该 PID，Host 仅为 loopback。
5. owner marker、实例 ID、账号 ID 和 nonce hash 一致。

任一不满足即转 `orphaned`，返回 `BROWSER_PROCESS_OWNERSHIP_UNPROVEN`，不得调用 `os.kill`。Runtime 增加 `psutil>=6,<7` 作为唯一新增 Python 运行依赖，用于进程创建时间、可执行文件、命令行、连接和进程树验证；禁止通过 PowerShell 文本解析或仅按 PID 猜测。

### 4.4 ExecutionBinding

`environmentId = execution_bindings.id`。保留现有字段，新增 `revision >= 1`、`error_code`、`error_log_id`。状态：

```text
provisioning | inactive | active | unhealthy | failed | deleting | cleanup_failed
```

一个账号同一时刻最多一个 `active` binding；同一 browser instance 最多属于一个未删除 binding。激活新 binding 必须在事务内把旧 binding 降为 `inactive`，不能先解绑再绑定造成空窗。

### 4.5 AccountConnection 与登录尝试

`AccountConnection.auth_status` 保持现有数据库枚举，避免破坏已验证契约：

| `auth_status` | UI 含义 |
| --- | --- |
| `unknown` | 尚未探测 |
| `required` | 需要登录、会话过期或已登出 |
| `valid` | 最近一次探测身份一致且会话有效 |
| `expired` | 已确认会话失效 |
| `failed` | 探测过程失败，需查看日志后重试 |

新增 `account_login_sessions` 表表示登录尝试，而不是保存平台 Cookie：

| 字段 | 约束 |
| --- | --- |
| `id` | 稳定资源 ID |
| `account_id` | 非空 FK，账号作用域 |
| `execution_binding_id` | 非空 FK，必须为当前账号有效 binding |
| `browser_instance_id` | 非空 FK，必须匹配 binding |
| `state` | `preparing / waiting_user / probing / completed / cancelled / failed / timed_out` |
| `prepare_task_id` | 可空 FK |
| `probe_task_id` | 可空 FK |
| `expected_identity` | 当前账号规范化 TikTok handle |
| `detected_identity` | 可空，普通标识而非凭据 |
| `expires_at` | 登录尝试超时 |
| `error_code` / `error_log_id` | 可空 |
| `revision` | `>=1` |
| 时间字段 | UTC ISO 8601 |

每账号最多一个 `preparing/waiting_user/probing` 活动尝试。登录成功后：

- `AccountConnection.session_ref` 指向 Secret Store 中的最小会话证明，只保存身份、Profile/实例绑定和探测时间；不要求导出原始 Cookie。
- 浏览器 Profile 自身保存平台会话，仍受账号工作区和进程所有权保护。
- 探测身份必须与账号 handle 一致；无法识别或不一致时不得写 `valid`。

## 5. 受控工作目录桥

### 5.1 Tauri 命令

新增 `src-tauri/src/workspace_roots/`，`main.rs` 只注册命令：

```text
pick_account_workspace_root(accountId, suggestedName?)
describe_account_workspace_root(accountId, rootRef)
reauthorize_account_workspace_root(accountId, rootRef)
revoke_account_workspace_root(accountId, rootRef)
```

`pick` 返回 `null` 表示用户取消，不作为异常。成功返回：

```json
{
  "rootRef": "wr_01J...",
  "displayPath": "D:\\TK-OPS\\accounts\\demo",
  "displayName": "demo",
  "revision": 1
}
```

Desktop 可以在用户主动选择/管理目录时显示完整 `displayPath`，但不得把它提交给 Runtime 或写入普通日志。

### 5.2 引用注册表

- Tauri 是唯一写入者，文件固定在应用本地配置目录 `workspace-roots.v1.json`。
- Supervisor 通过只由宿主设置的 `TK_OPS_WORKSPACE_ROOT_REGISTRY_PATH` 把该文件路径传给 sidecar；Runtime resolver 只读并按文件 mtime/revision 原子重载，HTTP 和页面不得覆盖该环境变量。
- 文件采用临时文件 + flush + 原子 replace；保留 `.bak`，解析失败时使用最后一次已验证快照并记录诊断。
- 每条记录包含 `rootRef`、`accountId`、规范路径、displayName、状态、revision、createdAt、updatedAt。
- 文件 ACL 只允许当前 Windows 用户；路径不视为密码，但按敏感本地信息脱敏。
- `rootRef` 使用不可猜测随机 ID；Runtime 解析时必须同时校验 `accountId`。

### 5.3 路径校验

拒绝：磁盘根目录、用户 Home 根、Windows/Program Files/应用数据根、仓库根、Runtime 数据根、现有其他账号工作区、不可写路径和无法解析的重解析点。允许用户选择普通父目录，Runtime 在其下创建安全账号子目录时必须把最终规范路径再次校验在授权根内。

工作区固定子目录：

```text
<root>/
├── browser-profile/
├── assets/
├── outputs/
├── tasks/
├── cache/
└── .tk-ops/
```

删除执行环境默认只删除 `.tk-ops` 和尚未含用户资产的受控临时目录；包含资产、输出或未知文件时必须保留目录并提示用户，不递归删除整个选择目录。

## 6. Eligibility 与 provisioning

### 6.1 唯一资格服务

`ExecutionEnvironmentEligibilityService.evaluate(account_id, environment_id)` 返回：

```json
{
  "eligible": false,
  "blockingIssues": [
    {
      "code": "BROWSER_NOT_RUNNING",
      "message": "浏览器尚未运行。",
      "recoveryAction": "start_environment"
    }
  ],
  "checkedAt": "2026-08-02T09:00:00Z",
  "evidenceRevision": 8
}
```

资格必须同时满足：账号 active/draft 且未归档、workspace owned 且 rootRef 可解析、目录可写、browser 账号/工作区一致、进程所有权已证明、loopback 调试端口健康、binding 引用一致且非删除态、没有冲突活动任务。

候选 API 只返回 `eligible=true` 的环境；管理页可以看到不合格环境和阻断原因。绑定命令在持锁事务中重新运行资格检查，防止查询后状态变化。

### 6.2 provisioning 阶段

```text
create_draft_aggregate
→ resolve_root_ref
→ create_workspace_structure
→ discover_browser
→ create_profile_and_owner_marker
→ launch_browser
→ verify_process_ownership
→ create_health_evidence
→ mark_environment_inactive_or_active
→ publish_event
```

- 创建请求事务内同时写三对象、任务、幂等证据和 outbox 事件。
- 任务失败时不留下“缺一张表”的半聚合；完整聚合进入 `failed`，外部副作用按 stage journal 反向补偿。
- Profile 已产生平台会话或未知文件时不得自动删除；进入 `cleanup_failed` 并提供人工处理说明。
- 重试复用同一 environmentId，`attempt` 增加；不同请求意图必须使用新幂等键。

## 7. HTTP API v1

共同要求：active 许可证、Runtime Session、账号 scope、`X-Request-ID`、写请求 `X-Idempotency-Key`；更新/删除还要求 `If-Match`。响应沿用统一信封。

### 7.1 执行环境列表与详情

```http
GET /api/v1/accounts/{account_id}/execution-environments
GET /api/v1/accounts/{account_id}/execution-environments/{environment_id}
```

响应项：

```json
{
  "id": "binding_id",
  "accountId": "account_id",
  "name": "主执行环境",
  "status": "inactive",
  "workspace": {
    "id": "workspace_id",
    "rootRef": "wr_01J...",
    "displayName": "demo",
    "status": "ready",
    "ownershipState": "owned"
  },
  "browser": {
    "id": "browser_id",
    "kind": "chrome",
    "displayName": "Google Chrome",
    "status": "running",
    "ownershipVerified": true,
    "lastCheckedAt": "2026-08-02T09:00:00Z"
  },
  "eligibility": {
    "eligible": true,
    "blockingIssues": [],
    "evidenceRevision": 8
  },
  "revision": 3,
  "errorCode": null,
  "errorLogId": null
}
```

禁止返回 root_path、profile_path、executable_path、PID、debug port、runtime evidence、session_ref 和 credential_ref。

### 7.2 创建

```http
POST /api/v1/accounts/{account_id}/execution-environments
X-Idempotency-Key: <business-key>
```

```json
{
  "name": "主执行环境",
  "rootRef": "wr_01J...",
  "browser": {
    "kind": "chrome",
    "selection": "auto"
  },
  "activateWhenReady": false
}
```

返回 `202`：

```json
{
  "ok": true,
  "data": {
    "environmentId": "binding_id",
    "taskId": "task_id"
  },
  "meta": {
    "invalidations": [
      "account:account_id:execution-environments",
      "account:account_id:tasks"
    ]
  }
}
```

### 7.3 动作

```http
POST /api/v1/accounts/{account_id}/execution-environments/{id}/start
POST /api/v1/accounts/{account_id}/execution-environments/{id}/stop
POST /api/v1/accounts/{account_id}/execution-environments/{id}/checks
DELETE /api/v1/accounts/{account_id}/execution-environments/{id}
PUT /api/v1/accounts/{account_id}/execution-environments/{id}/workspace-root
```

所有动作返回 `202 + taskId`，除 `workspace-root` 在验证/更新引用后返回最新环境；如需重建目录则同时返回任务。删除请求支持 `preserveUserFiles=true`，P0-G 固定默认 true，前端不能关闭。

### 7.4 候选与绑定

保留：

```http
GET /api/v1/accounts/{account_id}/connection/candidates
PUT /api/v1/accounts/{account_id}/connection/binding
DELETE /api/v1/accounts/{account_id}/connection/binding
```

候选 DTO 改为引用 `environmentId` 并携带 eligibility evidence revision。绑定 Body：

```json
{
  "environmentId": "binding_id",
  "eligibilityRevision": 8
}
```

服务端仍重新检查，不能信任客户端 revision。成功绑定后 `AccountConnection.auth_status` 若没有有效同实例 sessionRef，则设为 `required`。

### 7.5 登录、探测和登出

```http
POST   /api/v1/accounts/{account_id}/connection/login-sessions
GET    /api/v1/accounts/{account_id}/connection/login-sessions/{session_id}
POST   /api/v1/accounts/{account_id}/connection/login-sessions/{session_id}/probe
DELETE /api/v1/accounts/{account_id}/connection/login-sessions/{session_id}
DELETE /api/v1/accounts/{account_id}/connection/session
```

`POST login-sessions` 创建登录尝试和 `account.login.prepare` 任务。准备完成后浏览器进入前台并导航到 TikTok 官方登录/主页，session state 为 `waiting_user`。UI 只显示：

- “浏览器已打开，请在浏览器中自行登录”。
- “我已完成登录”。
- “取消登录”。

点击“我已完成登录”后 `POST probe` 创建 `account.login.probe` 任务。`TikTokSessionProbe` 只通过本地受控浏览器读取当前登录态和公开账号标识；探测失败不抓取密码、不自动重试验证码。

`DELETE connection/session` 创建 `account.logout` 任务，撤销 Secret Store 引用并清理受控 Profile 的平台会话数据；若安全清理无法证明完成，则状态为 `failed` 并保留日志，不把连接显示为已安全登出。

## 8. 任务和事件

### 8.1 新任务类型

```text
execution_environment.provision
execution_environment.start
execution_environment.stop
execution_environment.check
execution_environment.delete
execution_environment.reauthorize_root
account.login.prepare
account.login.probe
account.logout
```

任务快照必须包含 `schemaVersion`、`handlerVersion`、accountId、environmentId/loginSessionId、config snapshot 和请求哈希；不得包含绝对路径、Cookie、明文 nonce 或 session secret。

### 8.2 Topic 和事件

```text
account:{account_id}:execution-environments
account:{account_id}:connection
account:{account_id}:tasks
system:runtime-supervisor（Tauri 本地事件，不通过 Runtime WS）
```

领域事件：

```text
execution_environment.created|updated|failed|deleted
browser_instance.started|stopped|orphaned
account_connection.binding_changed
account_connection.auth_changed
account_login_session.updated
```

每次写响应和事件都给出 invalidation keys。Desktop 若发现 sequence gap，按现有协议 HTTP 补拉环境、连接和任务最终状态，再重新订阅。

## 9. 稳定错误码与恢复动作

复用现有码：`WORKSPACE_UNAVAILABLE`、`BROWSER_INSTANCE_NOT_FOUND`、`EXECUTION_BINDING_INVALID`、`ACCOUNT_CONNECTION_REQUIRED`、`TASK_*`、`REVISION_CONFLICT`、`CONTROLLED_FILE_REF_INVALID`、`DIAGNOSTICS_UNAVAILABLE`。

新增：

| 错误码 | HTTP/表面 | 中文恢复动作 |
| --- | --- | --- |
| `WORKSPACE_ROOT_REF_INVALID` | 422/任务失败 | 重新通过原生选择器授权目录 |
| `WORKSPACE_ROOT_FORBIDDEN` | 422 | 更换非系统根、非其他账号的可写目录 |
| `WORKSPACE_ROOT_UNAVAILABLE` | 409/任务失败 | 连接磁盘或重新授权 |
| `EXECUTION_ENVIRONMENT_NOT_FOUND` | 404 | 刷新当前账号环境列表 |
| `EXECUTION_ENVIRONMENT_NOT_ELIGIBLE` | 409 | 按 blockingIssues 执行修复动作 |
| `EXECUTION_ENVIRONMENT_BUSY` | 409 | 跟踪 meta.taskId，不并发启动新动作 |
| `BROWSER_NOT_INSTALLED` | 422/任务失败 | 安装或选择受支持 Chrome/Edge |
| `BROWSER_START_FAILED` | 任务失败 | 查看 logId，修复 Profile/权限后重试 |
| `BROWSER_PROCESS_OWNERSHIP_UNPROVEN` | 409/任务失败 | 手工检查浏览器；系统不会强制结束 |
| `LOGIN_SESSION_NOT_FOUND` | 404 | 重新开始登录 |
| `LOGIN_SESSION_EXPIRED` | 409 | 新建登录尝试 |
| `LOGIN_SESSION_STATE_CONFLICT` | 409 | GET 当前状态后继续 |
| `ACCOUNT_PLATFORM_AUTH_REQUIRED` | readiness/任务结果 | 打开监督登录流程 |
| `ACCOUNT_PLATFORM_IDENTITY_UNAVAILABLE` | 409/任务失败 | 在浏览器打开当前账号主页后重新探测 |
| `ACCOUNT_PLATFORM_IDENTITY_MISMATCH` | 409/任务失败 | 登出错误账号并登录目标账号 |
| `ACCOUNT_PLATFORM_SESSION_INVALID` | readiness/任务结果 | 重新登录 |
| `RUNTIME_CONNECTION_CHANGED` | Desktop 本地错误 | 丢弃旧请求，重新握手后重试 |

所有 5xx 和任务失败必须有 `log_id`；UI 分支以 error_code 为准，显示 Runtime 中文摘要，不展示 traceback。

## 10. Desktop 交互规格

### 10.1 账号切换器

- 壳层使用 `width/height: 100%` 与独立滚动容器，禁止页面级 `100vw` 横向溢出。
- 菜单推荐宽 320px，最大不超过 `min(360px, viewportWidth - 24px)`。
- 打开态放入统一 overlay root；四边离视口至少 12px，不被 sidebar/topbar 覆盖。
- 切换时禁用重复点击，显示目标账号；失败保留原账号并显示可重试反馈。
- 深链目标账号选择失败与人工切换使用同一错误反馈。

### 10.2 向导连接步骤

状态优先级：

```text
loading
→ empty（新建执行环境 / 刷新）
→ creating（阶段进度、取消、查看日志）
→ candidates（选择、阻断原因、管理）
→ binding
→ login_required
→ waiting_user
→ probing
→ ready
→ recoverable_error
```

“新建执行环境”打开桌面侧面板，不新增正式 Route：

1. 名称。
2. 原生选择工作目录。
3. 自动发现 Chrome/Edge，用户确认。
4. 创建进度。
5. 成功后自动选择并绑定。

创建失败保留账号向导草稿、environmentId、taskId 和 logId；允许重试或取消。不得在 UI 中手填绝对路径、PID、端口或 executable path。

### 10.3 监督登录

- 创建环境并绑定后，如果 auth 不是 valid，显示主按钮“打开浏览器登录”。
- 浏览器准备好后显示说明、“我已完成登录”和“取消登录”。
- 探测期间可取消；成功显示探测到的 TikTok handle 并进入下一步。
- 身份不一致同时显示期望/检测到的公开 handle，提供“返回浏览器重新登录”。
- 不提供账号密码输入框、Cookie 导入框或“跳过验证”。

### 10.4 账号详情和系统设置

- 账号详情“连接与工作区”管理当前账号环境、目录授权、启动/停止、检查、登录/登出、解除绑定和删除。
- 系统设置“Runtime 与工作区”只展示全局 Runtime 数据根、Supervisor 状态、环境总数、诊断导出和浏览器发现；不能越权修改其他账号绑定。
- 所有列表覆盖 loading/empty/normal/error/refreshing；所有任务覆盖 queued/running/cancelling/terminal/reconnecting。

### 10.5 Typed action router

统一结构：

```ts
type WorkspaceAction = {
  version: 1;
  action: string;
  accountId: string;
  routeId: string;
  wizardStep?: string;
  environmentId?: string;
  taskId?: string;
  logId?: string;
  returnTo?: { routeId: string; query?: Record<string, string> };
};
```

只允许白名单 action；解析失败或账号不匹配时 fail-closed 并显示反馈。工作台建议动作、账号健康问题、任务失败和 Recipe 后续修复都复用该路由器；P0-G 只实现账号/连接/环境动作。

## 11. Runtime Supervisor 与机器码

### 11.1 generation 驱动连接恢复

Supervisor 状态 DTO 新增 `generation`，每次 sidecar 成功启动递增。Desktop 启动时先订阅 `runtime-supervisor://status` 再请求连接；generation 或 token 指纹变化时：

1. 取消/标记当前 in-flight HTTP 请求为 `RUNTIME_CONNECTION_CHANGED`。
2. 清空 connection Promise 和 WebSocket。
3. 暂停 mutation，保留用户草稿。
4. 按集中配置退避获取新连接。
5. 重新拉取 bootstrap、active account、环境、连接和任务。
6. 使用新 subscription revision 重建订阅。

### 11.2 Runtime 启动前诊断

新增 Tauri 命令：

```text
get_runtime_supervisor_diagnostics()
export_runtime_supervisor_diagnostics()
```

诊断包含版本、generation、启动阶段、退出码、重启次数、脱敏日志尾部和制品哈希；不含 session token、完整路径、许可证密钥和环境变量值。BootstrapErrorScreen 在 Runtime 不可用时仍能复制摘要和导出包。

### 11.3 机器码兼容

- 现有机器码算法标记 `v1`，已签发许可证继续按 v1 验证。
- 注册表、CIM、系统盘序列分项捕获和记录错误，满足最小稳定因子后生成 v1；不足时返回 `LICENSE_STORE_UNAVAILABLE` 和 logId。
- 不在 P0-G 无提示更换算法或让已激活机器重新授权。
- 实机矩阵至少覆盖普通用户、CIM 服务不可用、单个因子读取失败和应用重启。

## 12. 配置总线

Runtime 用户配置新增并由明确 consumer 读取：

| 配置键 | 默认值 | Consumer |
| --- | ---: | --- |
| `execution.provisionTimeoutSeconds` | 120 | provision handler |
| `execution.cleanupTimeoutSeconds` | 30 | cleanup service |
| `browser.startTimeoutSeconds` | 30 | browser runtime |
| `browser.stopTimeoutSeconds` | 15 | browser runtime |
| `browser.healthTimeoutSeconds` | 10 | eligibility/check service |
| `connection.loginSessionTimeoutSeconds` | 600 | login session service |
| `connection.probeTimeoutSeconds` | 20 | TikTok session probe |

Tauri 在 Runtime 之前使用单一宿主配置 `runtime-supervisor.bootstrap.json`，新增：

| 配置键 | 默认值 |
| --- | ---: |
| `restart.maxAttempts` | 3 |
| `restart.initialDelayMs` | 500 |
| `restart.maxDelayMs` | 5000 |
| `diagnostics.tailLines` | 200 |

页面不直接读取 bootstrap 文件。规格实施必须提供 owner/validator/consumer 测试；无 consumer 的配置不进入公开设置。

## 13. 数据迁移与兼容

新增 `0021_p0g_execution_environment_closure.py`，只做加法和受控约束重建：

1. 为三类现有对象增加 rootRef/ownership/revision/error 字段。
2. 新建 `account_login_sessions`、索引和“每账号一个活动尝试”部分唯一索引。
3. 从唯一且一致的 `ExecutionBinding.account_id` 回填 workspace/browser `account_id`；多账号冲突或无证据对象标记 `legacy_unclaimed`，不猜测。
4. 具有账号但没有受控 rootRef 的旧 workspace 标记 `needs_reauthorization`，从候选中排除。
5. 现有一致 binding 保留但在重新授权、启动和资格检查完成前为 `inactive/unhealthy`。
6. migration report 记录数量和稳定原因码，不记录完整路径。

v1 新写服务强制 `ownership_state=owned`、非空 account_id/root_ref；legacy_unclaimed 只能在系统诊断看到数量，不能通过账号 API 读取或绑定。

回退遵循现有 cutover 策略：写门开放前可恢复迁移前备份；写门开放后使用兼容当前 Schema 的上一 Desktop + 回退 Runtime，不物理删新表/列、不覆盖用户数据库。旧 Runtime 不得调用新写路由。

## 14. 事务、补偿和归档

- HTTP mutation 事务只写数据库状态、任务、幂等记录和 outbox；外部副作用由持久任务执行。
- 每个 handler 在快照中保存已完成 stage，重启后从幂等边界继续或补偿。
- 文件创建只在账号授权根内；补偿只删除本任务创建且 owner marker 一致的空目录/临时文件。
- 进程补偿必须通过所有权证明；证明不足转 orphaned。
- 账号归档先提交 `account.archive_cleanup` 任务，依次取消账号环境任务、撤销登录、停止受控浏览器、解绑连接，再允许归档终态。
- 任一步失败保留账号在 `attention`/归档待处理状态，提供 logId 和重试；不得把仍运行的环境伪装成已归档完成。

## 15. 文件地图

### 15.1 Desktop

```text
apps/desktop/src/
├── app/actions/
│   ├── action-types.ts
│   ├── action-parser.ts
│   └── action-router.ts
├── app/runtime-supervisor/
│   ├── supervisor-client.ts
│   └── supervisor-recovery.ts
├── app/workspace-roots/
│   ├── workspace-root-client.ts
│   └── workspace-root-types.ts
├── app/runtime-client/
│   ├── execution-environments.ts
│   └── accounts.ts
├── modules/execution-environments/
│   ├── components/
│   ├── execution-environment-store.ts
│   ├── use-execution-environment-creator.ts
│   ├── execution-environment-types.ts
│   └── execution-environment.css
├── modules/accounts/
└── layouts/account-workspace/
```

### 15.2 Tauri

```text
apps/desktop/src-tauri/src/
├── workspace_roots/
│   ├── commands.rs
│   ├── registry.rs
│   ├── validation.rs
│   ├── types.rs
│   └── mod.rs
└── runtime_supervisor/
    ├── diagnostics.rs
    └── 现有模块最小修改
```

`main.rs` 只装配 plugin、state 和 command。新增 Rust 文件目标不超过约 350 行，接近 500 行必须继续拆分。

### 15.3 Runtime

```text
apps/py-runtime/src/
├── api/routes/v1/
│   ├── execution_environments.py
│   └── account_login_sessions.py
├── schemas/v1/
│   ├── execution_environments.py
│   └── account_login_sessions.py
├── services/execution_environments/
│   ├── service.py
│   ├── provisioning.py
│   ├── eligibility.py
│   ├── browser_process.py
│   ├── root_resolver.py
│   ├── cleanup.py
│   └── task_handlers.py
├── services/accounts/
│   ├── login_sessions.py
│   └── tiktok_session_probe.py
├── repositories/
│   ├── execution_environment_v1_repository.py
│   └── account_login_session_repository.py
└── domain/models/account_login_session.py
```

所有 Python 文件遵循统一日志、异常、类型和中文注释规范；路由不拼业务规则。

### 15.4 文档与测试

- `docs/api/v1/execution-environments.md`
- 更新 `docs/api/v1/accounts.md`、`errors.md`、`tasks-and-events.md`、README inventory。
- 更新 `docs/P0-ACCOUNT-FOUNDATION-COMPATIBILITY-MATRIX.md`。
- Runtime：`tests/runtime/test_p0_g_*`。
- Contract：`tests/contracts/test_p0_g_*`。
- Desktop：`apps/desktop/tests/p0/p0-g-*.spec.ts`。
- E2E：正式首启/账号执行主链，不调用 seed helper。
- Packaging：Windows 可见 GUI smoke 与 manifest verifier。

## 16. 分阶段验证命令与证据

开发中只做静态检查和代码审查；每个 G 阶段完成后集中执行一次“阶段相关测试 + 一条主链回归”。下列脚本若当前不存在，由对应阶段按规格创建，不能提前声称已通过。

### G0

```powershell
npm --prefix apps/desktop run test:active
npm --prefix apps/desktop run typecheck
Push-Location apps/desktop
npx playwright test -g "真实首启链完成授权且不注入执行环境"
Pop-Location
```

证据：测试清单、零意外 warning、匹配公钥指纹、无 seed 调用、当前 build manifest。

### G1

```powershell
npm --prefix apps/desktop run test -- account-workspace-layout-contract account-switcher
Push-Location apps/desktop
npx playwright test -g "账号切换器在两档 PC 窗口完整可见"
Pop-Location
```

证据：Light/Dark 两档截图、scrollWidth 和菜单 bounding box 数值。

### G2

```powershell
Push-Location apps/desktop/src-tauri
cargo test workspace_roots
Pop-Location
python -m pytest tests/runtime/test_p0_g_workspace_root_resolver.py tests/contracts/test_p0_g_workspace_root_contract.py -q
npm --prefix apps/desktop run test -- p0-g-workspace-root
```

证据：成功/取消/危险根/无权限/重解析点/过期/重授权/重启恢复。

### G3

```powershell
python -m pytest tests/runtime/test_p0_g_execution_environment_service.py tests/runtime/test_p0_g_process_ownership.py tests/contracts/test_p0_g_execution_environment_api.py -q
npm --prefix apps/desktop run test -- p0-g-execution-environment
```

证据：新鲜 DB 无 seed 创建、跨账号拒绝、并发幂等、故障补偿、Runtime 重启和 PID 复用。

### G4

```powershell
python -m pytest tests/runtime/test_p0_g_login_session.py tests/contracts/test_p0_g_login_session_api.py -q
npm --prefix apps/desktop run test -- p0-g-account-login p0-g-action-router
Push-Location apps/desktop
npx playwright test -g "新账号建立环境并完成监督登录"
Pop-Location
```

真实 TikTok E2E 标为受控人工验收，不在 CI 保存凭据。自动化契约测试使用本地确定性探测适配器，但最终阶段必须附一次真实受控浏览器探测证据。

### G5

```powershell
Push-Location apps/desktop/src-tauri
cargo test runtime_supervisor
Pop-Location
npm --prefix apps/desktop run test -- p0-g-supervisor-recovery
python -m pytest tests/runtime/test_machine_code_service.py tests/contracts/test_p0_g_diagnostics.py -q
```

证据：新 generation/端口/token 恢复、启动前诊断、四类 Windows 机器码矩阵、旧许可证回归。

### G6

```powershell
python -m pytest tests/runtime/test_p0_g_task_lifecycle.py tests/runtime/test_p0_g_compensation.py tests/runtime/test_p0_g_archive_cleanup.py tests/runtime/test_p0_g_execution_environment_actions.py -q
npm --prefix apps/desktop run test -- p0-g-task-recovery
```

证据：全部任务终态、断网/重启、重复事件、事务故障注入、补偿失败和归档清理。

### G7

```powershell
npm test
npm run typecheck
npm run test:e2e
npm run build:windows-release
powershell -File tests/packaging/windows-gui-smoke.ps1
node scripts/verify-release-manifest.mjs
git diff --check
```

证据：当前 sidecar/NSIS/免安装运行包 SHA256、可见 WebView、激活、标准窗口按钮、单实例聚焦、优雅关闭、重启和干净数据主链。

## 17. 测试真实性规则

1. Production E2E 禁止调用 `seedExecutionBinding`、直接 SQLite insert/update 或测试专用状态突变。
2. 测试可在仓储/服务层使用 fixture，但不得把 fixture 结果当 GUI 闭环证据。
3. TikTok 外部网络可在单元/契约测试使用明确命名的 deterministic adapter；真实验收必须由可见浏览器完成一次且不保存凭据。
4. 不允许通过扩大 Tauri asset scope、降低资格规则、mock 被审计对象或放宽断言制造全绿。
5. 默认门禁维护 active/compatibility/retired 清单；retired 必须有原因、替代测试和删除阶段。
6. Vue Router、未处理 Promise、console error/warn 均属于 E2E 失败，已批准的预期日志必须结构化白名单。
7. 每个验收报告记录命令、退出码、测试数、环境、Git 状态和制品哈希；历史结果不得覆盖当前结果。

## 18. G0-G7 失败恢复与回退矩阵

| 阶段 | 失败恢复 | 回退点 |
| --- | --- | --- |
| G0 | 保留失败输出，修测试环境或契约，不改生产规则迎合旧测试 | 恢复上一测试编排；历史证据不改 |
| G1 | 菜单关闭后可继续导航，布局异常不改变账号状态 | 独立回退 CSS/overlay |
| G2 | rootRef 失效时重新授权；不移动/删除目录 | 关闭新建，保留只读引用和原数据 |
| G3 | 失败聚合可重试；补偿不足进入 cleanup_failed/orphaned | 关闭写路由，保留表和只读诊断 |
| G4 | 登录失败回 required；账号草稿和环境保留 | 禁用登录入口，不伪装 valid |
| G5 | 自动重连失败回 BootstrapErrorScreen，仍可导出诊断 | 关闭自动恢复，保留手动重启和旧机器码 |
| G6 | WebSocket 降级轮询；补偿失败保留审计对象 | 回退投影 UI，不删除任务/事件 |
| G7 | 失败制品不提升 current | current 指针回上一 manifest/制品 |

## 19. 规格完成条件

规格批准后的实施只有同时满足以下条件才可认定 P0-G 完成：

- 审计中的 G0-G7 对应 S0/S1 全部有当前证据，不只靠代码审查。
- 新鲜数据、production mode、无 seed 的正式制品走完账号执行主链。
- 登录身份一致、会话可过期/登出，敏感信息不泄漏。
- Runtime 重启后连接、任务、进程所有权和账号隔离可恢复。
- 两档 PC 窗口和双主题完成真实交互验收。
- API 文档、错误码、配置 consumer、migration、测试和 release manifest 与代码一致。
- P0-H/P0-I 仍保持未获授权边界，不因 P0-G 完成而冒充 AI/创作生产链完成。

## 20. 批准门

- **批准记录**：用户在 2026-08-02 的退回结论中明确要求“先纠正规格批准状态并补齐 H/I，再按 G0→G7 真正实施”，本规格据此获批。
- **当前状态**：从 G0 开始实施，不跳过验收真源直接开发 G2/G3。
- **每阶段完成后**：更新 `PROGRESS.md` 和阶段证据；出现超范围变更先修订本文。
- **G7 完成后**：交付新的免安装 EXE/ZIP、manifest、SHA256 和真实 GUI 验收报告。

## 21. G0 精确实施批次

本节根据 2026-08-02 只读预检锁定 G0 文件落点。当前静态库存为 94 个 Vitest 文件，其中 `tests/p0` 24 个、门禁外 70 个；另有 1 个 Playwright E2E 文件。仓库当前没有 release/build artifact manifest。

### G0-A 首启许可证 E2E 校准

修改范围：

- `apps/desktop/tests/e2e/support/e2e-environment.mjs`
- `apps/desktop/tests/e2e/account-workspace.e2e.ts`
- 必要时增加许可证测试 helper，但不修改生产许可证算法。

固定改动：

1. `generate_keypair.py` 继续在 E2E 临时目录生成一次性公私钥。
2. `issue_license.py` 必须显式传入 `--runtime-public-key <temporary-public-key>`；Runtime 继续通过 `TK_OPS_LICENSE_PUBLIC_KEY_PATH` 读取同一公钥。
3. 删除 E2E 对“完整机器码”输入框的 `fill`；只断言机器码只读显示和复制能力，激活只输入许可证密钥。
4. 首启基线测试拆成独立 active E2E，不 import `p0-main-chain.ts`、`execution-fixture.ts` 或 `seed-execution-binding.py`。
5. 基线止于真实账号空态，不把 API 创建账号、AI 配置和直接数据库 seed 计入首启证明。

验收：

```powershell
Push-Location apps/desktop
npx playwright test -g "真实首启链完成授权且不注入执行环境"
Pop-Location
```

静态守卫扫描 active E2E，命中 `seedExecutionBinding`、`seed-execution-binding.py`、SQLite `INSERT/UPDATE` 或“完整机器码”写操作即失败。

### G0-B 测试库存唯一真源

新增：

```text
apps/desktop/tests/test-inventory.v1.json
apps/desktop/scripts/validate-test-inventory.mjs
apps/desktop/scripts/run-active-vitest.mjs
```

`test-inventory.v1.json` 对每个 `*.spec.ts` 指定且只指定一个分类：

| 分类 | 含义 | 默认门禁 |
| --- | --- | --- |
| `active` | 当前十三 Route、Tauri 或共享基础的生产契约 | 必跑 |
| `compatibility` | 当前仍有读取/迁移兼容价值，但不是生产页面完成证据 | 独立命令运行，不计入默认生产通过数 |
| `retired` | 锁定已删除产品方向或已被新测试完全替代 | 不运行；必须写替代测试、原因和删除阶段 |

库存校验必须保证：

- 文件系统中的 94 个 Vitest 文件全部登记且无重复。
- 新测试未登记时默认门禁失败，不能静默遗漏。
- `retired` 必须有 `reason`、`replacement` 和 `removeAfterStage`。
- `active` 不得 import legacy 页面、旧壳或测试 seed。
- `tauri-capabilities.spec.ts` 按当前最小权限改为 active；只断言 `$APPLOCALDATA/runtime/accounts/**/*` 等批准范围，禁止为旧断言开放 `$HOME/**`。
- 意外 Vue Router warning、console warn/error 和未处理 Promise 使 active 测试失败。

`apps/desktop/package.json` 调整为：

```text
test            → 校验库存并运行 active
test:compat     → 校验库存并运行 compatibility
test:inventory  → 只校验覆盖和分类规则
```

根 `package.json` 的 `test:desktop` 继续调用 Desktop `test`，因此根门禁自动获得 active 真源。

### G0-C release manifest 唯一真源

新增：

```text
scripts/create-release-manifest.mjs
scripts/verify-release-manifest.mjs
scripts/build-windows-release.mjs
dist/releases/<version>/<platform>/release-manifest.json（生成物）
dist/releases/current.json（验收后原子提升）
```

manifest Schema v1：

```json
{
  "schemaVersion": 1,
  "product": "TK-OPS",
  "version": "0.4.7",
  "channel": "test",
  "platform": "windows",
  "architecture": "x86_64",
  "git": {
    "commit": "full-sha",
    "branch": "main",
    "dirty": true,
    "statusSha256": "sha256"
  },
  "inputs": {
    "packageLockSha256": "sha256",
    "cargoLockSha256": "sha256",
    "pyprojectSha256": "sha256",
    "tauriConfigSha256": "sha256",
    "runtimePublicKeySha256": "sha256"
  },
  "tests": [],
  "artifacts": [],
  "builtAtUtc": "2026-08-02T00:00:00Z"
}
```

每个 test evidence 包含 command、exitCode、测试数、开始/结束时间和 evidence 文件 SHA256；每个 artifact 包含 kind、相对路径、size、SHA256。manifest 禁止写许可证私钥、session token、完整用户路径或环境变量值。

构建规则：

- dirty worktree 只允许 `channel=test`，不能提升 `current` 或标记 production。
- `channel=production` 必须 clean、所有批准门禁通过、制品哈希复验一致。
- `current.json` 只保存已通过 G7 GUI smoke 的 manifest 相对路径和 manifest SHA256。
- 任一测试、构建、哈希或 GUI smoke 失败均保留失败 evidence，但不覆盖 current。
- sidecar、NSIS 和免安装运行包必须来自同一次 orchestrator 运行，禁止手工混包。

### G0-D 状态文档校准

- 历史 P0-F 数字和哈希原样保留，明确标记“当时有效，当前已失效”。
- `PROJECT-STATUS` 的“当前制品”只能由 verified manifest 更新，不手工复制哈希。
- `PROGRESS.md` 记录 G0 的实际命令、退出码和测试数量；不能用定向复验替代完整阶段结果。
- G0 完成只证明验收真源恢复，不证明执行环境、登录、AI 或八个 pending 页面完成。
