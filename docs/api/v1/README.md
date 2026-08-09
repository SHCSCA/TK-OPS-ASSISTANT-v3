# Runtime API v1

本目录是 TK-OPS `/api/v1` 接口的唯一真源。本文档只描述当前代码中已经注册的路由、DTO、安全门禁、任务和事件协议；批准规格中尚未实现的能力只保留阶段索引，不提供虚构请求或响应。

Python Runtime 启动前可用的 Tauri 状态、连接、重启与脱机诊断命令见 [Desktop Runtime Supervisor 契约](../desktop-runtime-supervisor.md)。

最后静态核对日期：2026-08-09。

P0-B 至 P0-F 均已通过阶段与最终验收。P0-G 已补齐持久任务列表、执行环境动作、失败恢复与真实归档清理接口，当前静态库存为 97 个 HTTP 与 1 个 WebSocket。

## 当前接口库存

| 领域 | 已注册接口 | 文档 |
| --- | ---: | --- |
| Bootstrap 与许可证 | 5 个 HTTP | [bootstrap.md](bootstrap.md) |
| 系统配置与诊断 | 4 个 HTTP | [system-config-and-diagnostics.md](system-config-and-diagnostics.md) |
| 持久任务 | 6 个 HTTP | [tasks-and-events.md](tasks-and-events.md) |
| Runtime 事件 | 1 个 WebSocket | [tasks-and-events.md](tasks-and-events.md) |
| 账号、生命周期、真实连接与监督登录 | 22 个 HTTP | [accounts.md](accounts.md) |
| 执行环境 | 8 个 HTTP | [execution-environments.md](execution-environments.md) |
| 定位、知识、品牌与发布默认值 | 17 个 HTTP | [account-knowledge.md](account-knowledge.md) |
| AI 系统 v1 | 35 个 HTTP | [ai-system.md](ai-system.md) |

HTTP 合计：`5 + 4 + 6 + 22 + 8 + 17 + 35 = 97`。路由库存只统计 `V1_HTTP_ROUTERS` 中实际注册的装饰器端点，不统计 legacy 路由或 WebSocket。

错误信封、状态码、恢复动作和 legacy 错误映射见 [errors.md](errors.md)。

## 基础地址与版本边界

- HTTP 基础地址：正式 Desktop 从 Tauri Supervisor 获取本次动态 `http://127.0.0.1:<port>`；`8000` 只用于手动开发示例。
- v1 HTTP 前缀：`/api/v1`。
- v1 WebSocket：`/api/v1/ws`。
- legacy HTTP 使用无版本 `/api/...` 路径。Bootstrap、许可证、系统设置与任务的受控兼容适配器在所有模式注册，并在生产模式强制本机 Host / Origin 与 Runtime Session 门禁；其余尚未迁移的 legacy HTTP 路由只在非生产模式注册。
- legacy WebSocket `/api/ws` 仍注册，但只发送经过白名单和字段脱敏的系统事件。
- `docs/RUNTIME-API-CALLS.md` 已冻结为 legacy 索引，不是 v1 真源。

## HTTP 公共安全门禁

所有 `/api/v1` HTTP 请求都会先校验 Host 和可选 Origin；除 `OPTIONS` 外还会校验 Runtime Session。进入具体业务路由后，再按端点执行许可证门禁：

| 项目 | 要求 | 失败 |
| --- | --- | --- |
| `Host` | 必须唯一且精确匹配 Runtime 启动配置 | `RUNTIME_HOST_INVALID` |
| `Origin` | 可省略；存在时必须唯一、不能为 `*`，且精确命中允许列表 | `RUNTIME_ORIGIN_FORBIDDEN` |
| `Authorization` | `Bearer <runtime-session-token>`，只允许一个 Header | `RUNTIME_SESSION_REQUIRED` 或 `RUNTIME_SESSION_INVALID` |
| 许可证 | 除三条许可证引导接口外必须为实时 `active` | `LICENSE_INVALID`、`LICENSE_MACHINE_MISMATCH` 或 `LICENSE_STORE_UNAVAILABLE` |

许可证引导豁免仅指“不要求许可证已经 active”，不豁免 Host、Origin 或 Runtime Session：

- `GET /api/v1/bootstrap/status`
- `GET /api/v1/bootstrap/license`
- `POST /api/v1/bootstrap/license/activate`

Runtime Session 和许可证密钥不得进入 URL、日志、事件 payload 或任务快照。

Runtime 启动模式只接受 `dev / development / test / prod / production`；
未知值直接拒绝启动，不允许按开发模式降级。生产模式会忽略开发 Origin
扩展，并要求 `TK_OPS_RUNTIME_SESSION_TOKEN` 为 43 至 256 位 URL-safe
随机字符串，同时要求 `TK_OPS_RUNTIME_EXPECTED_HOST` 精确指向
`127.0.0.1:<受控端口>`。

## HTTP 公共 Headers

| Header | 方向 | 说明 |
| --- | --- | --- |
| `Authorization` | 请求 | 所有非 `OPTIONS` v1 HTTP 请求必填 |
| `Content-Type: application/json` | 请求 | 有 JSON Body 的请求使用 |
| `X-Operation-ID` | 请求，可选 | 1 至 128 位受控标识；用于串联一次业务操作 |
| `Idempotency-Key` | 请求，按端点 | 1 至 128 位受控标识；需要时由端点条目明确标注 |
| `If-Match` | 请求，按端点 | 系统配置和账号聚合写操作的乐观修订锁；具体语义由资源文档定义 |
| `X-Request-ID` | 请求可选、响应必有 | 合法入站值用于关联并回显；未提供时由 Runtime 生成 |
| `X-Operation-ID` | 响应 | 回显合法请求值；未提供时由 Runtime 生成 |

`X-Operation-ID` 和 `Idempotency-Key` 的允许格式为：

```text
^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$
```

账号、任务、事件和嵌套资源等持久资源 ID 使用更严格的公共语法
`^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`；资源 ID 不允许冒号，避免与事件
Topic 的结构分隔符混淆。

## 成功信封

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "revision": 3,
    "invalidations": ["system-config"]
  }
}
```

- `meta` 仅在端点显式返回时存在。
- `meta.revision` 是资源修订，不是 HTTP 请求序号。
- `meta.invalidations` 是客户端应失效的缓存键；读请求若返回该字段，其值为空数组。

## 失败信封

```json
{
  "ok": false,
  "error": "请求参数校验失败",
  "error_code": "REQUEST_VALIDATION_FAILED",
  "fieldErrors": [
    {
      "field": "body.checks",
      "code": "literal_error",
      "message": "字段值不在允许范围内"
    }
  ]
}
```

- `fieldErrors`、`log_id` 和 `meta` 没有内容时会被省略，不返回空占位。
- `log_id` 只在服务端实际生成可追踪诊断记录时存在。
- `X-Request-ID` 位于响应 Header；v1 错误 Body 不使用 legacy `requestId`。

## 超时与重试

- 普通同步 HTTP 端点当前没有端点级客户端超时参数；客户端应使用自己的受控请求超时。
- 长任务创建快速返回 `202`，实际执行超时由配置总线和任务处理器控制。
- 只有文档明确要求 `Idempotency-Key` 的写端点才可按其幂等语义自动重试。
- `500` 或 `503` 后是否可直接重试取决于端点条目；系统配置存在“已保存但运行时刷新失败”的特殊边界，必须先重新读取。
- WebSocket 首帧超时、消息大小和事件重放窗口由配置总线管理。

## 当前未实现边界

下列能力虽已在产品规格中定义，但当前没有对应 `/api/v1` 路由：

- 任务重试以及通用任务创建端点。
- WebSocket 事件历史查询端点。

账号基础纵向链与 AI 配置纵向链已经进入 v1 路由库存并通过验收；正式 Desktop、sidecar 与安装包也已在 P0-F 完成切换。P1 / P2 尚未实现的能力不得用 legacy `/api/...` 路由或伪响应替代。
