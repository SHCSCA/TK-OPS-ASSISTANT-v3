# TK-OPS 0.4.10 P0-G Production Hardening 规格

> 日期：2026-08-08  
> 状态：已批准（2026-08-08）  
> 对应计划：`docs/superpowers/plans/2026-08-08-production-ai-creation-real-validation.md`  
> 目标版本：`0.4.10`  
> 范围：机器身份、许可证状态、执行环境恢复、登录取消、发布证据和状态真源

## 1. 规格目标

本规格只关闭 `0.4.9` 的 Production 阻断，不实现 P0-H/P0-I 功能：

1. 单一硬件因子临时失败不能改变同一台机器的公开机器码。
2. 机器身份不确定不能误报 `machine_mismatch`。
3. 失败执行环境必须可见、可诊断、可基于原对象重试。
4. 监督登录任一阶段取消必须传递到 Runtime 任务和浏览器进程。
5. Production manifest 必须绑定全部必需测试、源码内容和制品。
6. 项目状态文档必须与真实阶段一致。

## 2. 不变量

- 机器身份原始因子不写普通数据库、日志、API 或 manifest。
- 机器身份基线只保存因子 SHA-256 摘要，并由系统安全存储保护。
- 已激活许可证在身份采集源短暂不可用时不得被改写或删除。
- `machine_mismatch` 只能由足够的明确冲突证据产生。
- 失败环境、失败任务和登录会话不静默删除，用户工作目录始终保留。
- 取消前端等待不等于取消业务任务；Runtime 是任务终态真源。
- Production 构建只允许干净工作树；test 构建也必须内容可追溯。

## 3. 机器身份 v2

### 3.1 采集结果

新增内部结构：

```text
MachineFactorObservation
- key: registry | cim | system_volume
- status: available | unavailable | invalid
- value_hash: SHA-256(normalized key + value) | null
- error_code: stable code | null
```

采集器保留固定键，不再返回可变长度 list。每个采集异常记录稳定错误码和 logId，日志不包含原值。

### 3.2 安全基线

SecretStore 新增 `machine-identity/v2` 记录：

```json
{
  "formatVersion": 2,
  "algorithmVersion": "v2",
  "canonicalMachineCode": "TKOPS-...",
  "factorHashes": {
    "registry": "...",
    "cim": "...",
    "system_volume": "..."
  },
  "createdAt": "ISO-8601",
  "lastVerifiedAt": "ISO-8601"
}
```

- 不保存原始 MachineGuid、UUID 或卷序列号。
- 无基线时至少两个有效因子才可创建；摘要按固定 key 排序生成公开机器码。
- 已有 v1 激活记录升级时，优先在三因子完整且 legacy 摘要与存储机器码一致时登记旧机器码为 canonical，避免许可证失效。
- 旧许可证迁移时证据不足返回 `MACHINE_IDENTITY_RETRY_REQUIRED`，不得直接返回 mismatch。
- 基线解密或完整性失败返回 `MACHINE_IDENTITY_STORE_UNAVAILABLE`，不得静默重建。

### 3.3 解析状态

新增内部结果：

```text
MachineIdentityResolution
- machine_code
- status: verified | degraded | unavailable | mismatch
- matched_factor_count
- mismatched_factor_count
- unavailable_factor_count
- algorithm_version
```

规则：

- 两个及以上基线因子匹配：`verified`，返回 canonical。
- 至少一个匹配、其余只有 unavailable：`degraded`，返回 canonical 并显示可恢复提示。
- 明确观测到两个及以上因子与基线冲突：`mismatch`。
- 无足够匹配且不能证明冲突：`unavailable`，返回 503 可重试状态，不改变许可证。
- 测试 override 只在测试/开发受控标志存在时生效；production sidecar 禁止普通环境变量改写机器码。

### 3.4 许可证服务与 API

- `LicenseV1Service` 消费 resolution，不再只比较一次动态字符串。
- `verified/degraded` 使用 canonical 校验已存许可证。
- `unavailable` 映射 503 和中文恢复提示，不返回 `machine_mismatch`。
- `mismatch` 才返回 `LICENSE_MACHINE_MISMATCH`。
- `LicenseStatusDto` 加法增加 `machineIdentityStatus`、`machineIdentityAlgorithm` 和三个计数；不返回因子名称对应的具体硬件信息。
- 首启 UI 在 degraded 时允许已激活许可证继续工作并提示“设备信息采集不完整，稍后自动复检”；unavailable 进入可重试错误态。

## 4. 执行环境恢复

### 4.1 数据与 DTO

Alembic 新增加法迁移 `0022_p0g_production_hardening`：

- `execution_bindings.last_task_id nullable`。
- `execution_bindings.last_retry_of_task_id nullable`。
- 必要索引和外键采用与 RuntimeTask 生命周期兼容的保守策略。

`ExecutionEnvironmentDto` 加法增加：

- `lastTaskId`
- `lastRetryOfTaskId`
- `recoveryActions[]`
- `errorMessage`

`recoveryActions` 只允许 `retry_provision`、`check`、`reauthorize_root`、`view_log`、`delete_preserving_files`。

### 4.2 接口

保留现有接口并新增：

```text
POST /api/v1/accounts/{account_id}/execution-environments/{environment_id}/retry
If-Match: <environment revision>
Idempotency-Key: <key>
→ 202 { environmentId, taskId, retryOfTaskId }
```

- 只允许失败、停止或 attention 且具有可恢复动作的环境重试。
- 重试复用原 workspace、browser、binding 和 rootRef。
- 新 RuntimeTask 的 `retry_of_task_id` 必须指向原失败任务。
- 原任务不存在时保留 environmentId，返回稳定错误并要求执行检查，不创建新环境。

### 4.3 Desktop 状态

账号连接步骤同时维护：

- `environments`：全部环境，包括 creating、failed、attention、stopped、active。
- `candidates`：当前可绑定候选。

显示优先级：加载错误 → 现有失败/处理中环境 → 可绑定候选 → 真正空态。只有 `environments.length === 0` 才显示“还没有执行环境”。

Creator 在失败后保留 `environmentId`、`taskId`、目录和名称；“重试”调用 retry 接口，不重新提交 create。刷新或重启后从 list DTO 恢复。

## 5. 监督登录取消

### 5.1 Desktop

- `createAccountLoginSession` 返回后立即保存 `sessionId` 和 `prepareTaskId`，再等待任务。
- 取消按钮根据当前阶段执行：停止本地轮询 → DELETE login session → cancel prepare/probe RuntimeTask → 拉取最终会话状态。
- 如果 DELETE 或 task cancel 任一失败，UI 保留 session/task 上下文，显示重试与日志；不得直接发出“已取消”。
- `onBeforeUnmount` 只停止轮询，不自动产生有外部影响的业务取消；再次进入页面从 Runtime 恢复状态。

### 5.2 Runtime

`DELETE /login-sessions/{session_id}` 改为异步服务实现，但保持成功信封兼容：

- 锁定账号和会话修订。
- 查找 prepare/probe task，调用 TaskCoordinator 取消。
- 若本会话启动了受控浏览器，执行有界停止和进程归属校验。
- 完成补偿后写 `cancelled`、事件、revision、task/log 证据。
- 已完成/已取消调用幂等返回当前终态；commit 已胜出时返回真实完成状态。

## 6. Release Manifest v2

### 6.1 源码快照

manifest 增加：

```text
git.commit
git.tree
git.statusSha256
git.trackedDiffSha256
git.untrackedContentSha256
git.sourceSnapshotSha256
```

- `trackedDiffSha256` 基于 `git diff --binary --no-ext-diff HEAD` 原始字节。
- `untrackedContentSha256` 基于排序后的 `path + NUL + file hash`；忽略规则继续由 Git 真源决定。
- `sourceSnapshotSha256` 组合 commit、tree、tracked diff 和 untracked 内容摘要。
- verify 必须重新计算全部字段；仅修改文件内容但不改变 status 行时也必须失败。
- Production 继续强制 `dirty=false`，此时 commit/tree 是正式源码真源。

### 6.2 必需证据

Production promotion 要求以下唯一 evidence ID：

```text
runtime-full
desktop-active
desktop-typecheck
rust-tauri
playwright-first-run
playwright-account-workspace
sidecar-smoke
windows-gui-smoke
windows-installer-smoke
packaged-license-activation
target-tiktok-supervised-login
```

- 每份 evidence 记录命令、开始/完成时间、退出码、测试数和 stdout/stderr 摘要。
- GUI、installer、license、目标机器证据必须绑定 Desktop/Runtime/installer 的 SHA-256。
- `target-tiktok-supervised-login` 为人工脱敏 JSON，只包含证据 ID、目标制品哈希、结果、时间和脱敏 logId；不包含账号身份、Cookie、Token、机器码或页面内容。
- build orchestrator 负责生成自动证据；禁止手工把未执行的 evidence 写成通过。

### 6.3 构建顺序

```text
version-check
→ Runtime full
→ Desktop active/typecheck
→ Rust
→ first-run + account workspace E2E
→ sidecar build/smoke
→ Tauri/NSIS/portable build
→ GUI smoke
→ installer smoke
→ packaged license activation
→ 生成 test manifest
→ 目标机器人工登录证据
→ 干净提交重新构建 production
→ 校验并提升 current
```

任何阶段失败立即停止，不组装可交付 manifest。

## 7. 配置、错误与日志

新增配置全部进入配置总线：

- 机器因子采集超时和重试次数。
- 身份 degraded 自动复检间隔。
- 环境恢复和登录取消超时。
- Release evidence 必需 ID 由版本化代码常量维护，不允许页面配置绕过。

新增错误至少包括：

- `MACHINE_IDENTITY_RETRY_REQUIRED`
- `MACHINE_IDENTITY_STORE_UNAVAILABLE`
- `EXECUTION_ENVIRONMENT_NOT_RETRYABLE`
- `EXECUTION_ENVIRONMENT_RETRY_CONTEXT_MISSING`
- `LOGIN_SESSION_CANCEL_INCOMPLETE`
- `RELEASE_SOURCE_SNAPSHOT_MISMATCH`
- `RELEASE_REQUIRED_EVIDENCE_MISSING`

所有异常使用统一日志，包含 operation、稳定资源 ID、error_code 和 logId；不记录原始硬件值、凭据、本地绝对路径或 TikTok 身份。

## 8. 测试矩阵

### Runtime

- 机器身份：3→2 因子机器码不变、单因子异常、明确两因子冲突、基线损坏、v1 迁移、production override 拒绝。
- 许可证：degraded 保持 active、unavailable 返回可恢复状态、明确 mismatch、密钥签发/激活兼容。
- 环境：失败对象出现在 list、原环境重试、retryOfTaskId、重启恢复、跨账号拒绝、用户文件保留。
- 登录：preparing/waiting/probing 取消、任务取消失败、浏览器补偿失败、幂等取消、重启恢复。
- manifest：同 status 不同内容失败、缺任一 evidence 失败、哈希错配失败、dirty production 失败。

### Desktop

- “失败环境”与“没有环境”状态分离。
- 创建失败后保留上下文并重试原对象。
- 登录准备阶段取消调用会话与任务 API；失败时不显示已取消。
- machine identity degraded/unavailable UI 状态与重试。

### E2E 与制品

- 首启、账号完整链路、环境失败恢复和登录取消新增真实 Runtime 场景。
- GUI smoke 保持八项并增加失败环境恢复可见状态。
- 安装包 smoke、打包 Runtime 许可证签发激活、免安装单入口继续通过。
- 目标机器用最终候选完成一次可见 TikTok 监督登录。

## 9. 文件边界

允许修改：

- `apps/py-runtime/src/services/machine_code.py`
- `apps/py-runtime/src/services/bootstrap_v1/`
- `apps/py-runtime/src/services/execution_environments/`
- `apps/py-runtime/src/services/accounts/login_sessions.py`
- 对应 domain/repository/schema/api/config 与新加法迁移
- `apps/desktop/src/modules/accounts/`
- `apps/desktop/src/modules/execution-environments/`
- 对应 runtime-client/types/tests
- `scripts/*release*`、`scripts/build-windows-release.mjs`
- `tests/runtime`、`tests/contracts`、`tests/packaging`、Desktop tests/E2E
- 版本、API、状态与 superpowers 文档

禁止在本规格中修改八个 pending Route 为 ready，禁止实现 AI Execution Gateway 或 P0-I 数据主链。

## 10. 回退与交付

- 身份 v2 写入失败保留旧许可证与旧基线，不覆盖。
- 新环境字段为 nullable 加法；回退代码忽略它们。
- 登录取消补偿失败保留 attention/failed 状态和日志，不伪造 cancelled。
- Manifest v2 不覆盖旧 v1 manifest；0.4.10 使用独立目录。
- 只有全部自动证据和目标机器人工证据通过，才能将 `0.4.10` 标记 Production。

## 11. 实施顺序

1. 版本升为 `0.4.10`，同步版本真源和状态文档。
2. 机器身份与许可证定向实现和测试。
3. 环境恢复与登录取消 Runtime 实现和测试。
4. Desktop 状态与交互实现和测试。
5. Manifest v2 与发布编排实现和测试。
6. 阶段相关测试 + 主链回归。
7. 全量自动验收、测试候选和目标机器人工验收。
8. 干净提交重新构建 Production，校验 manifest 并保留回退制品。

## 12. 2026-08-09 验收修订

`0.4.10` 已形成测试候选，但外部验收确认第 8 节要求的执行环境失败恢复、监督登录准备取消仍缺独立真实 Runtime E2E，GUI 冷启动也出现一次窗口句柄/样式过渡波动。本修订不扩展 P0-G 产品范围，只补齐既定验收：

- Playwright 增加“环境首次创建失败后恢复原对象”和“登录 preparing 阶段取消后 Runtime 任务真实结束”两条场景，并验证 UI 可见恢复状态。
- E2E Runtime 仅在测试入口提供一次性故障控制，生产 Runtime 不暴露故障注入 API。
- 登录导航移入可取消的后台边界，取消后不得继续把会话推进为 `waiting_user`。
- GUI smoke 从本次 portable ZIP 全新解压目录启动，窗口句柄连续稳定后才执行标准窗口控制验证；证据同时绑定 Desktop 与 portable SHA-256。
- 八个 pending Route 保持不变，继续由 P0-H / P0-I 实施。

由于 `0.4.10` 测试包已经对外验收且本修订包含代码变化，依据 `docs/VERSIONING.md` 升级为补丁版本 `0.4.11`；原 `0.4.10` 规格和制品作为历史记录保留。
