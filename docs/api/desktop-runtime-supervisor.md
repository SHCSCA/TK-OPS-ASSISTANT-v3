# Desktop Runtime Supervisor 契约

> 版本：v1  
> Owner：Tauri 桌面宿主  
> Consumer：Desktop Runtime 连接适配层、启动门禁

该契约在 Python Runtime 启动之前可用，不属于 HTTP API。页面不得直接读取宿主配置或日志文件，必须通过下列 Tauri 命令访问。

## 状态事件

- 事件：`runtime-supervisor://status`
- 关键字段：`status`、`phase`、`generation`、`restartAttempt`、`maxRestartAttempts`、`errorCode`、`logId`
- 不包含：会话令牌、许可证密钥、环境变量值和完整文件路径。

Desktop 必须先订阅状态事件，再获取 Runtime 连接。`generation` 变化后，连接适配层取消旧 HTTP 请求、暂停写操作、关闭旧 WebSocket，并在新状态为 `ready` 后重新握手和刷新账号工作区。

## `get_runtime_connection`

返回：

```json
{
  "baseUrl": "http://127.0.0.1:43100",
  "generation": 3,
  "sessionToken": "仅在内存中使用的会话令牌"
}
```

`sessionToken` 禁止写入日志、诊断文件和持久化配置。

## `get_runtime_supervisor_diagnostics`

Runtime HTTP 不可用时仍可调用。返回桌面版本、generation、启动阶段、最近退出码、重试次数、Runtime 制品哈希和脱敏 Supervisor 日志尾部。

## `export_runtime_supervisor_diagnostics`

将同一份脱敏诊断原子写入应用数据目录的 `runtime/diagnostics` 子目录，返回 `fileName` 与导出路径。失败返回稳定错误码 `RUNTIME_DIAGNOSTICS_EXPORT_FAILED` 和 `logId`。

## `restart_runtime`

显式停止当前受管进程并启动新 generation。启动或停止正在进行时返回 `RUNTIME_RESTART_IN_PROGRESS`。

## 宿主配置

唯一配置文件为 `resources/runtime/runtime-supervisor.bootstrap.json`。默认重启策略为最多 3 次、初始退避 500ms、最大退避 5000ms；诊断日志尾部为 200 行。页面不得直接读取该文件。
