# Runtime API v1 错误契约

本文件是当前 `/api/v1` HTTP、WebSocket 和持久任务错误码的唯一索引。P0-C 账号、定位、知识和品牌错误已经物化并通过阶段验收；P0-E Provider、模型、Prompt、能力路由、Composition Template 和 AI Recipe 错误已经进入生产路径，阶段测试尚未执行。

## HTTP 失败信封

```json
{
  "ok": false,
  "error": "系统配置包含不可写或无效字段",
  "error_code": "CONFIG_KEY_NOT_WRITABLE",
  "fieldErrors": [
    {
      "field": "values.provider.secret",
      "code": "not_writable",
      "message": "该配置项不可由用户修改"
    }
  ]
}
```

- 必有字段：`ok=false`、面向用户的 `error`、稳定大写 `error_code`。
- 可选字段：`log_id`、`fieldErrors`、`meta`；无内容时省略。
- `fieldErrors` 只提供安全字段位置、规则码和中文摘要，不回显请求值；深层映射键和额外字段等可能由用户输入产生的位置统一显示为中性 `field`。
- 所有 HTTP `5xx` 失败都会建立可追踪 `log_id`；`4xx` 仅在处理器显式要求审计引用时返回。
- `X-Request-ID` 与 `X-Operation-ID` 位于响应 Header，不写入 v1 Body。
- Runtime Session 错误额外返回 `WWW-Authenticate: Bearer`。

`error` 摘要可按具体上下文变化；客户端分支必须以 `error_code` 为准，并把 `error` 直接用于中文状态反馈。

## HTTP 公共错误

| 错误码 | HTTP | 当前摘要或含义 | 恢复动作 | legacy 映射 |
| --- | ---: | --- | --- | --- |
| `RUNTIME_HOST_INVALID` | 400 | Runtime 请求目标不合法 | 使用 Runtime 启动时公布的精确 Host | `runtime.host.invalid` |
| `RUNTIME_ORIGIN_FORBIDDEN` | 403 | 请求来源不受信任 | 使用允许的桌面 Origin；非浏览器调用可省略 Origin | `runtime.origin.forbidden` |
| `RUNTIME_SESSION_REQUIRED` | 401 | 缺少本机 Runtime 会话凭据 | 重新建立桌面 Runtime Session | `runtime.session.required` |
| `RUNTIME_SESSION_INVALID` | 401 | Session 格式错误、失效或服务端未就绪 | 丢弃旧 Token 并重新握手 | `runtime.session.invalid` |
| `LICENSE_INVALID` | 403 | 许可证无效，请先完成激活 | 返回许可证向导并读取实时状态 | `license.invalid` |
| `LICENSE_MACHINE_MISMATCH` | 403 | 许可证与本机不匹配 | 使用当前机器码重新激活或更换授权 | `license.machine.mismatch` |
| `MACHINE_IDENTITY_RETRY_REQUIRED` | 503 | 当前稳定机器因子不足，无法可靠判定身份 | 稍后重试并保持原许可证，不得按不匹配处理 | `machine.identity.retry.required` |
| `MACHINE_IDENTITY_STORE_UNAVAILABLE` | 503 | 受保护机器身份基线不可读或完整性失败 | 查看日志并修复安全存储，禁止静默重建 | `machine.identity.store.unavailable` |
| `LICENSE_STORE_UNAVAILABLE` | 503 | 许可证安全存储或机器码依赖不可用 | 根据 `log_id` 修复安全存储后重试 | `license.store.unavailable` |
| `REQUEST_VALIDATION_FAILED` | 422 | 请求参数、Header、Path、Query、Body 或 WS 帧校验失败 | 读取 `fieldErrors`；不要原样重试 | `request.validation_failed` |
| `ROUTE_NOT_FOUND` | 404 | 请求的接口不存在 | 核对 `/api/v1` 地址和方法 | `runtime.resource_not_found` |
| `METHOD_NOT_ALLOWED` | 405 | 请求方法不受支持 | 使用接口文档规定的方法 | `runtime.method_not_allowed` |
| `RUNTIME_NOT_READY` | 503 | 对应 Runtime 服务尚未完成装配 | 等待启动完成或查看系统诊断 | `runtime.not.ready` |
| `INTERNAL_ERROR` | 500 | 系统内部错误或未预期异常 | 保存 `log_id`，先查询最终状态再谨慎重试 | `runtime.internal_error` |

框架还保留两个通用回退：未带稳定领域码的 HTTP 409 映射为 `REQUEST_CONFLICT` / `task.conflict`，HTTP 504 映射为 `REQUEST_TIMEOUT` / `runtime.timeout`。普通账号写操作也会明确使用 `REQUEST_CONFLICT` 表示同一幂等键绑定了不同请求摘要。

## Bootstrap、配置与诊断错误

| 错误码 | HTTP | 端点或状态 | 当前摘要或含义 | 恢复动作 | legacy 映射 |
| --- | ---: | --- | --- | --- | --- |
| `DIRECTORY_CREATE_FAILED` | 500 | 目录初始化 | 受控工作区引用不可解析、目录创建失败或不可写 | 修复目录权限；未知结果先重新读取 Bootstrap 状态 | `directory.create.failed` |
| `SELF_CHECK_ALREADY_RUNNING` | 409 | 创建 Bootstrap 自检 | 系统作用域已有自检活动；`meta.taskId` 指向现有任务 | 跟踪现有任务，不创建并行自检 | `self.check.already.running` |
| `TASK_IDEMPOTENCY_CONFLICT` | 409 | 创建持久任务 | 同一幂等键对应不同请求摘要 | 纠正调用方键复用；新业务意图使用新键 | `task.idempotency.conflict` |
| `TASK_ALREADY_RUNNING` | 409 | 创建账号健康、连接或知识任务 | 同一账号和任务类型已有活动任务，或相同创建幂等键对应的任务已离开排队态；`meta.taskId` 指向既有任务 | 先查询既有任务；任务终态后如需重新执行，应使用新的业务幂等键 | `task.already.running` |
| `TASK_HANDLER_NOT_FOUND` | 503 或任务失败码 | 自检提交、重启恢复 | 任务处理器未注册 | 修复 Runtime 装配；保留失败任务供诊断 | `task.handler.not.found` |
| `TASK_SNAPSHOT_INVALID` | HTTP 422 或任务失败码 | 自检提交、任务恢复 | 新快照输入无效，或存量快照/处理器版本不兼容 | 422 修正请求；恢复失败时保留原任务与日志 | `task.snapshot.invalid` |
| `CONFIG_REVISION_CONFLICT` | 412 | PATCH 系统配置 | 缺少 `If-Match` 或修订已变化 | GET 最新快照；并发冲突可用 `meta.currentRevision` 对账，缺 Header 时该字段不存在 | `config.revision.conflict` |
| `CONFIG_KEY_NOT_WRITABLE` | 422 | PATCH 系统配置 | 配置键不在公开写白名单 | 移除内部键、凭据和任意扩展字段 | `config.key.not.writable` |
| `DIAGNOSTICS_UNAVAILABLE` | 503 | 系统诊断、日志摘要 | 诊断采集或日志文件暂不可用 | 根据 `log_id` 修复依赖或权限后重试 | `diagnostics.unavailable` |
| `LOG_NOT_FOUND` | 404 | 日志摘要 | `log_id` 不存在或已过期 | 使用错误信封新返回的日志引用 | `log.not.found` |

`LICENSE_MISSING` 目前只可能出现在 `LicenseStatusDto.blockingIssue.code`，表示 Bootstrap 数据状态；它不是 HTTP `error_code`。

## 账号、连接与并发错误

| 错误码 | HTTP/表面 | 当前含义 | 恢复动作 | legacy 映射 |
| --- | --- | --- | --- | --- |
| `ACCOUNT_NOT_FOUND` | 404 | 账号不存在；账号级子资源也以此阻断 | 刷新账号列表并清除无效上下文 | `account.not.found` |
| `ACCOUNT_ARCHIVED` | 409 | 已归档账号不能进入普通工作区或修改子资源 | 切换账号，或通过恢复接口完成真实健康复检 | `account.archived` |
| `ACCOUNT_STATE_TRANSITION_INVALID` | 409 或任务失败码 | 当前五状态不允许目标转换 | GET 最新账号；恢复允许未完成向导的 `archived -> draft`，不要在 UI 强改状态 | `account.state.transition.invalid` |
| `ACCOUNT_CONNECTION_REQUIRED` | 409 或 readiness 数据码 | 缺少可用真实连接或无可解除绑定 | 建立真实绑定并运行连接检查 | `account.connection.required` |
| `ACCOUNT_PLATFORM_UNSUPPORTED` | 422 | P0 创建账号的平台不是 `tiktok` | 改为 TikTok；不得伪装其他平台 | `account.platform.unsupported` |
| `ACCOUNT_USERNAME_INVALID` | 422 | TikTok 标识格式无效 | 按 `fieldErrors` 修正 | `account.username.invalid` |
| `ACCOUNT_WIZARD_INCOMPLETE` | 409 | 添加向导未完整提交六个步骤 | 使用 `meta.missingSteps` 返回缺失步骤 | `account.wizard.incomplete` |
| `WORKSPACE_UNAVAILABLE` | 409 或任务失败码 | 当前账号没有真实可用工作区/绑定 | 修复工作区或重新选择真实对象 | `workspace.unavailable` |
| `BROWSER_INSTANCE_NOT_FOUND` | 404 | 浏览器实例不存在或不属于当前账号 | 刷新当前账号的浏览器实例 | `browser.instance.not.found` |
| `EXECUTION_BINDING_INVALID` | 409 或 readiness 数据码 | 工作区、浏览器实例和执行绑定证据不一致 | GET 连接，重新选择同一账号下匹配对象 | `execution.binding.invalid` |
| `EXECUTION_ENVIRONMENT_NOT_FOUND` | 404 或 409 | 执行环境不存在或不属于当前账号 | 刷新当前账号环境与候选 | `execution.environment.not.found` |
| `EXECUTION_ENVIRONMENT_INVALID` | 409 | rootRef、工作目录或聚合证据发生不一致 | 重新授权或重建环境 | `execution.environment.invalid` |
| `EXECUTION_ENVIRONMENT_NOT_ELIGIBLE` | 409 | 环境未 ready、浏览器未运行、所有权未证明或资格修订过期 | 重新读取资格并执行 recovery action | `execution.environment.not.eligible` |
| `EXECUTION_ENVIRONMENT_PROVISION_FAILED` | 任务失败码或 409 | 目录结构、浏览器启动或所有权校验失败 | 查看 `logId`，修复后创建新环境或重试受控任务 | `execution.environment.provision.failed` |
| `EXECUTION_ENVIRONMENT_NOT_RETRYABLE` | 409 | 环境状态或原任务类型不允许重试 | 重新读取环境与任务状态，按 recovery action 处理 | `execution.environment.not.retryable` |
| `EXECUTION_ENVIRONMENT_RETRY_CONTEXT_MISSING` | 409 | 原环境或 provision 任务上下文已缺失 | 保留诊断日志并重新创建环境 | `execution.environment.retry.context.missing` |
| `LOGIN_SESSION_NOT_FOUND` | 404 | 登录尝试不存在或不属于当前账号 | 丢弃本地会话引用并重新创建 | `login.session.not.found` |
| `LOGIN_SESSION_EXPIRED` | 409 | 监督登录窗口已过期 | 新建登录尝试 | `login.session.expired` |
| `LOGIN_SESSION_STATE_CONFLICT` | 409 | 当前账号已有活动尝试或状态不允许操作 | GET 当前会话，取消或等待后重试 | `login.session.state.conflict` |
| `LOGIN_SESSION_CANCEL_INCOMPLETE` | 409 | 登录任务取消未在限定时间内闭环 | GET 会话与任务终态，对账后重试取消 | `login.session.cancel.incomplete` |
| `ACCOUNT_PLATFORM_AUTH_REQUIRED` | 任务失败码 | 公开页面尚未显示已登录状态 | 回到可见浏览器完成登录 | `account.platform.auth.required` |
| `ACCOUNT_PLATFORM_IDENTITY_UNAVAILABLE` | 任务失败码 | 已打开平台但无法识别公开账号身份 | 打开个人主页后重新探测 | `account.platform.identity.unavailable` |
| `ACCOUNT_PLATFORM_IDENTITY_MISMATCH` | 409 或任务失败码 | 探测身份与当前账号用户名不一致 | 在浏览器切换正确账号后重试 | `account.platform.identity.mismatch` |
| `ACCOUNT_PLATFORM_SESSION_INVALID` | 409 或任务失败码 | 受控浏览器或平台会话不可达 | 重启环境并重新登录 | `account.platform.session.invalid` |
| `ACCOUNT_COPY_SECTION_INVALID` | 422 | 配置复制分区不在白名单 | 只提交定位、知识规则、BrandKit、AI Recipe 或发布默认值 | `account.copy.section.invalid` |
| `ACCOUNT_COPY_SOURCE_EQUALS_TARGET` | 409 | 来源与目标为同一账号 | 选择不同来源账号 | `account.copy.source.equals.target` |
| `REVISION_CONFLICT` | 412 | 缺少账号 `If-Match`，或账号聚合修订已变化 | GET 最新资源并基于新修订重做用户意图 | `revision.conflict` |
| `REQUEST_CONFLICT` | 409 | 普通持久幂等键对应不同请求摘要 | 修复调用方键复用；新业务意图使用新键 | `task.conflict` |

跨账号来源、快照、工作区和浏览器实例不会暴露其他账号的数据。资源查询通常返回本账号范围内的 `*_NOT_FOUND` 或一致性错误；任务和 WebSocket 的明确作用域错配使用 `ACCOUNT_SCOPE_MISMATCH`。

## 定位、知识、品牌与发布默认值错误

| 错误码 | HTTP/表面 | 当前含义 | 恢复动作 | legacy 映射 |
| --- | --- | --- | --- | --- |
| `POSITIONING_INVALID` | 422 | 内容支柱、受众、语气或禁用主题不符合定位契约 | 按 `fieldErrors` 修正后创建新版本 | `positioning.invalid` |
| `POSITIONING_VERSION_NOT_FOUND` | 404 | 定位版本不存在或已归档 | 刷新定位版本列表 | `positioning.version.not.found` |
| `KNOWLEDGE_SOURCE_INVALID` | 422 或任务失败码 | 来源模式、URL、来源清单或持久证据无效 | 修正当前账号来源；不得绕过受控摄取 | `knowledge.source.invalid` |
| `KNOWLEDGE_SOURCE_NOT_FOUND` | 404 | 来源不存在或不属于当前账号 | 刷新来源列表 | `knowledge.source.not.found` |
| `CONTROLLED_FILE_REF_INVALID` | 422、HTTP 503 或任务失败码 | 文件引用不是受控选择器令牌，无法在当前账号解析，或 P0-F Tauri 文件桥尚未装配 | 重新通过文件选择器取得引用；503 时等待文件桥落线后重试 | `controlled.file.ref.invalid` |
| `KNOWLEDGE_SNAPSHOT_INVALID` | 422 | 快照来源为空、重复、跨账号或未索引成功 | 先完成来源索引，再创建新快照 | `knowledge.snapshot.invalid` |
| `KNOWLEDGE_SNAPSHOT_NOT_FOUND` | 404 | 快照不存在或不属于当前账号 | 刷新快照列表 | `knowledge.snapshot.not.found` |
| `KNOWLEDGE_INDEX_FAILED` | 任务失败码，部分读取错误为 422 | 受控文件、正文或公共 HTTPS 来源读取/哈希失败 | 查看来源 `errorCode` / `logId`，修复后新建索引任务 | `knowledge.index.failed` |
| `BRAND_KIT_INVALID` | 422 | 品牌列表、颜色或 Logo 资产引用无效 | 按 `fieldErrors` 修正 | `brand.kit.invalid` |
| `PUBLISH_DEFAULTS_INVALID` | 422 或 409 | 时区、隐私互动约束无效，或初始化记录缺失 | 422 修正字段；409 运行数据修复 | `publish.defaults.invalid` |

## AI 配置与账号 Recipe 错误

| 错误码 | HTTP/表面 | 当前含义 | 恢复动作 | legacy 映射 |
| --- | --- | --- | --- | --- |
| `PROVIDER_NOT_FOUND` | 404 | Provider Profile 不存在 | 刷新 Provider 列表并清除无效选择 | `provider.not.found` |
| `PROVIDER_ADAPTER_UNSUPPORTED` | 422 | 适配器类型没有显式接入 | 选择已接入适配器或先完成协议实现 | `provider.adapter.unsupported` |
| `PROVIDER_BASE_URL_INVALID` | 422 | 地址格式、凭据嵌入、协议或远程明文 HTTP 不安全 | 修正为合法 HTTPS；仅 loopback 可用 HTTP | `provider.base.url.invalid` |
| `PROVIDER_SECRET_UNAVAILABLE` | 503 | 凭据无法写入或安全引用无法读取 | 重新设置凭据；持续失败时按 `log_id` 修复安全存储 | `provider.secret.unavailable` |
| `PROVIDER_CONNECTION_FAILED` | 502 或任务失败码 | 连接超时、HTTP 失败、响应过大或响应格式无效 | 检查地址、凭据与网络后创建新检查任务 | `provider.connection.failed` |
| `PROVIDER_CHECK_TIMED_OUT` | 任务失败码 | Provider 检查超过受控超时 | 调整配置或修复 Provider 后创建新任务 | `provider.check.timed.out` |
| `MODEL_NOT_FOUND` | 404 | Model Profile 不存在或不属于目标 Provider | 刷新模型列表 | `model.not.found` |
| `MODEL_ALREADY_EXISTS` | 409 | 同一 Provider 下模型标识重复 | 使用已有模型或更换稳定标识 | `model.already.exists` |
| `MODEL_IN_USE` | 409 | 模型仍被已启用 Capability Route 引用 | 先迁移或停用相关路由 | `model.in.use` |
| `MODEL_CAPABILITY_UNVERIFIED` | 422 | 模型宣称能力但适配器或契约尚未验证 | 运行能力检查并修复失败项 | `model.capability.unverified` |
| `CAPABILITY_ROUTE_INVALID` | 422 | 路由模型、Prompt、回退或启用状态不满足能力契约 | 按校验问题修正后重新验证 | `capability.route.invalid` |
| `CAPABILITY_ROUTE_UNAVAILABLE` | 409 或 readiness 数据码 | 账号 Recipe 依赖的系统路由当前不可用 | 修复系统路由或合法账号覆盖 | `capability.route.unavailable` |
| `PROMPT_PROFILE_INVALID` | 422 | Profile 键、变量、Schema 或 Prompt 版本内容无效 | 修正后创建新版本 | `prompt.profile.invalid` |
| `PROMPT_PROFILE_NOT_FOUND` | 404 | Prompt Profile 不存在 | 刷新 Profile 列表 | `prompt.profile.not.found` |
| `PROMPT_VERSION_NOT_FOUND` | 404 | 指定 Prompt 版本不存在 | 刷新版本列表 | `prompt.version.not.found` |
| `PROMPT_VERSION_IMMUTABLE` | 409 | 试图覆盖不可变 Prompt 版本 | 创建新版本并显式激活 | `prompt.version.immutable` |
| `COMPOSITION_TEMPLATE_INVALID` | 422 | 模板定义、受控引用或必需能力无效 | 修正定义并重新验证新版本 | `composition.template.invalid` |
| `COMPOSITION_TEMPLATE_NOT_FOUND` | 404 | 合成模板 Profile 不存在 | 刷新模板列表 | `composition.template.not.found` |
| `COMPOSITION_TEMPLATE_VERSION_NOT_FOUND` | 404 | 指定模板版本不存在 | 刷新模板版本 | `composition.template.version.not.found` |
| `AI_RECIPE_INVALID` | 422 或 readiness 数据码 | 账号 Recipe 不完整、引用失效或系统 AI 修订已变化 | 创建或重新验证 Recipe 版本 | `ai.recipe.invalid` |

## 任务 HTTP 与任务终态错误

| 错误码 | HTTP/表面 | 当前摘要或含义 | 恢复动作 | legacy 映射 |
| --- | --- | --- | --- | --- |
| `TASK_NOT_FOUND` | HTTP 404 | 任务不存在 | 丢弃无效任务引用 | `task.not.found` |
| `ACCOUNT_SCOPE_MISMATCH` | HTTP 403 或 WS 错误帧 | 任务或 Topic 不属于请求账号/作用域 | 使用创建响应中的账号和作用域重新查询 | `account.scope.mismatch` |
| `TASK_NOT_CANCELLABLE` | HTTP 409 | 当前任务不允许取消 | 等待任务终态 | `task.not.cancellable` |
| `TASK_STATE_CONFLICT` | HTTP 409 | 并发状态已变化或转换不合法 | 立即 GET 最终状态 | `task.state.conflict` |
| `TASK_TIMEOUT` | `TaskDto.errorCode`、`task.failed` | 执行或重启恢复判断超时 | 检查超时配置和处理器；P0-B 无公开 retry 路由 | `task.timeout` |
| `TASK_HANDLER_NOT_FOUND` | `TaskDto.errorCode`、`task.failed` | 重启时找不到原处理器 | 升级或恢复匹配处理器后由后续受控入口重试 | `task.handler.not.found` |
| `TASK_SNAPSHOT_INVALID` | `TaskDto.errorCode`、`task.failed` | 快照损坏或处理器版本不匹配 | 保留任务与日志，禁止绕过快照校验 | `task.snapshot.invalid` |

任务处理器也可把稳定领域错误写入 `TaskDto.errorCode`。当前处理器包括 `bootstrap.self_check`、三个账号健康类型、`knowledge.index`、`provider.health_check`、`provider.model_discovery` 和 `model.capability_check`；`failureKind` 描述失败类别，`errorCode` 描述可恢复原因，两者不可互换。

## WebSocket 错误与同步信号

WebSocket 建立后使用独立错误帧，不使用 HTTP 失败信封：

```json
{
  "type": "error",
  "errorCode": "ACCOUNT_SCOPE_MISMATCH",
  "message": "事件订阅与账号范围不匹配。",
  "subscriptionRevision": 3
}
```

下表“legacy 映射”仅表示统一大写码的字符串转换结果；legacy `/api/ws` 本身不发送这些 v1 错误或同步帧。

| 错误码或信号 | 表面 | 含义 | 恢复动作 | legacy 映射 |
| --- | --- | --- | --- | --- |
| `REQUEST_VALIDATION_FAILED` | `error` 帧 | JSON、Schema、Topic 或消息内容无效 | 修正帧；超大消息连接会以 4400 关闭 | `request.validation_failed` |
| `ACCOUNT_SCOPE_MISMATCH` | `error` 帧 | Topic 不属于订阅账号或系统 Topic 未授权 | 清除旧账号订阅并重建正确世代 | `account.scope.mismatch` |
| `ACCOUNT_NOT_FOUND` | `error` 帧 | `accountId` 在真实账号仓储中不存在 | 刷新账号列表或创建真实账号 | `account.not.found` |
| `ACCOUNT_ARCHIVED` | `error` 帧 | 账号已归档，不能订阅工作区事件 | 切换可用账号或通过恢复 API 完成复检 | `account.archived` |
| `WS_CURSOR_MISMATCH` | `error` 帧 | 订阅修订不递增，或事件 ID/Topic/sequence 不一致 | HTTP 对账后用更高修订和正确游标重订阅 | `ws.cursor.mismatch` |
| `WS_EVENT_GAP` | `sync.required` 帧 | 游标已越过有界重放窗口或序列不连续 | HTTP 补拉最终状态，清缓存，再用空游标建立实时基线 | `ws.event.gap` |
| `REQUEST_TIMEOUT` | `error` 帧后关闭 4408 | 首个有效订阅帧超时 | 重连并在配置时限内订阅 | `runtime.timeout` |
| `INTERNAL_ERROR` | 可能的 `error` 帧或连接 1011 | 账号门禁或会话处理发生内部异常 | 重连；持续失败时打开诊断 | `runtime.internal_error` |

握手前门禁失败不发送错误帧：

- 4403：Host、Origin 或普通 `LICENSE_INVALID`。
- 4401：Runtime Session 错误，以及当前未映射到 4403 的许可证错误，例如 `LICENSE_MACHINE_MISMATCH`。

完整订阅和断档恢复流程见 [tasks-and-events.md](tasks-and-events.md#websocket-apiv1ws)。

## legacy 错误码转换

Bootstrap、许可证、系统设置与任务的受控 legacy HTTP 适配器在所有模式注册；其余尚未迁移的 legacy HTTP 路由只在非生产模式注册。统一异常处理器对所有非 `/api/v1` 路径执行以下转换：

| v1 / 内部大写码 | legacy 特例 |
| --- | --- |
| `REQUEST_VALIDATION_FAILED` | `request.validation_failed` |
| `ROUTE_NOT_FOUND` | `runtime.resource_not_found` |
| `METHOD_NOT_ALLOWED` | `runtime.method_not_allowed` |
| `REQUEST_CONFLICT` | `task.conflict` |
| `REQUEST_TIMEOUT` | `runtime.timeout` |
| `INTERNAL_ERROR` | `runtime.internal_error` |

其他全大写下划线错误码统一转为小写点分形式，例如：

```text
LICENSE_MACHINE_MISMATCH -> license.machine.mismatch
CONFIG_REVISION_CONFLICT -> config.revision.conflict
TASK_IDEMPOTENCY_CONFLICT -> task.idempotency.conflict
WS_CURSOR_MISMATCH -> ws.cursor.mismatch
```

这只是错误码字符串映射，不保证 legacy 与 v1 的 Body、状态码、幂等、修订、作用域或事务语义等价。

## 尚未物化或非 HTTP 的错误码

`KNOWLEDGE_RULES_INVALID` 尚未由当前实现直接发出；知识规则的 Schema 校验当前使用 `REQUEST_VALIDATION_FAILED`。

`DATABASE_SCHEMA_UNSUPPORTED` 与 `MIGRATION_FAILED` 是 Runtime 启动迁移阻断码，不是已启动 HTTP 端点的响应；它们通过启动日志和宿主生命周期反馈处理。`WS_PROTOCOL_INVALID` 不由当前 v1 HTTP 端点直接发出；`LEGACY_WRITE_UNSUPPORTED` 只用于危险 legacy 写入口的 HTTP 410 响应。
