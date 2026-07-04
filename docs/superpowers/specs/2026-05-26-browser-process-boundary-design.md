# 阶段 5 浏览器实例真实进程边界设计

## 背景

设备与工作区管理当前已经能创建真实本地工作区目录、创建浏览器 profile 目录，并写入浏览器实例状态。但 `start / stop / health-check` 仍只是数据库状态翻转，无法证明浏览器实例真的运行、可停止或可被发布/自动化链路引用。

本切片只做最小真实进程边界：Runtime 必须能从配置总线读取浏览器可执行文件路径，启动本地浏览器进程，持久化 PID、调试端口和运行证据；无法启动时必须返回明确错误，不能把状态写成 `running`。

## 文档依据

- `docs/PRD.md`：设备体系核心对象是 `DeviceWorkspace`，设备与工作区必须真实存在、可审计、可恢复。
- `docs/UI-DESIGN-PRD.md`：UI 必须呈现真实健康状态和真实错误，状态不能只靠颜色表达。
- `docs/ARCHITECTURE-BOOTSTRAP.md`：`/api/devices` 归属设备工作区管理，服务层负责业务流程与任务编排，页面消费 Runtime DTO。
- `docs/superpowers/plans/2026-05-25-delivery-readiness.md`：阶段 5 要求浏览器实例具备真实进程、profile、PID、端口、健康检查和停止恢复。

## 本轮范围

### Runtime 配置总线

- 在 `AppSettings` 增加 `browser.executablePath`。
- 默认值为空，表示未配置自定义浏览器路径。
- Runtime 启动时从配置总线读取该值，传给浏览器运行时解析器。

### 浏览器实例模型与 DTO

浏览器实例响应补充以下字段：

- `processId`: 当前浏览器进程 PID，未运行时为 `null`。
- `debugPort`: Runtime 分配的远程调试端口，未运行时为 `null`。
- `runtimeMode`: `local_process` 或 `metadata_only`。
- `launchSupported`: 当前 Runtime 是否有可用浏览器执行器。
- `runtimeEvidence`: 结构化证据，至少包含 `executablePath`、`profilePath`、`debugPort`、`processId`、`startedAt` 或失败原因。

### start

- start 必须尝试启动真实本地进程。
- 成功时状态为 `running`，写入 PID、端口、profile 路径和运行证据。
- 失败时状态为 `error`，写入 `browser_instance.executable_missing`、`browser_instance.launch_failed` 或 `browser_instance.profile_missing`，不得返回 `running`。
- 已运行实例再次 start 时应保持幂等，返回当前运行证据。

### health-check

- health-check 必须检查 profile 目录、PID 存活状态和 DevTools 调试端口可达性。
- PID 存活且 DevTools 调试端口可达时状态为 `ready`。
- PID 缺失或进程已退出时状态为 `error`，错误码 `browser_instance.process_missing`。
- PID 存活但调试端口不可达时状态为 `error`，错误码 `browser_instance.devtools_unreachable`，不得把“任意存活 PID”视为可用浏览器实例。

### stop

- stop 必须尝试停止 PID 对应进程。
- 成功或进程已不存在时状态为 `stopped`，清空 PID 和调试端口，并记录停止证据。
- 停止失败时状态为 `error`，错误码 `browser_instance.stop_failed`。

## 非目标

- 不实现 TikTok 自动发布。
- 不实现浏览器内 DOM 自动化、登录态检测、反检测能力或环境伪装。
- 不实现跨 Runtime 重启后的完整进程重连策略；本轮只通过持久化 PID 和 health-check 收敛状态。
- 不要求测试机器安装 Chrome / Edge；测试可注入本地假运行时或短生命周期进程，用于验证 Runtime 持久化和错误语义。

## 文件地图

- `apps/py-runtime/src/services/browser_runtime.py`
- `apps/py-runtime/src/services/device_workspace_service.py`
- `apps/py-runtime/src/domain/models/device_workspace.py`
- `apps/py-runtime/src/repositories/device_workspace_repository.py`
- `apps/py-runtime/src/schemas/device_workspaces.py`
- `apps/py-runtime/src/schemas/settings.py`
- `apps/py-runtime/src/services/settings_service.py`
- `apps/py-runtime/src/persistence/engine.py`
- `apps/py-runtime/alembic/versions/0012_add_browser_runtime_fields.py`
- `apps/desktop/src/types/runtime.ts`
- `tests/runtime/test_browser_instances.py`
- `tests/contracts/test_browser_instances_contract.py`
- `tests/contracts/test_settings_config_contract.py`
- `docs/RUNTIME-API-CALLS.md`

## 验收标准

- 无浏览器可执行文件时，start 不返回 `running`，并返回 `browser_instance.executable_missing`。
- 注入可用运行时后，start 返回 `running`，DTO 包含 `processId`、`debugPort`、`runtimeMode=local_process`、`launchSupported=true`。
- health-check 对运行中 PID 且 DevTools 可达的实例返回 `ready`，对缺失 PID 返回 `browser_instance.process_missing`，对调试端口不可达返回 `browser_instance.devtools_unreachable`。
- stop 清空 PID 和端口，状态变为 `stopped`。
- 配置接口包含 `browser.executablePath`，默认值为空，更新后可持久化。
- 契约文档同步新增字段、错误码和示例。

## 回退点

如本切片影响设备工作区已有创建、绑定或健康检查流程，可回退浏览器运行时注入和新增字段映射，保留 profile 目录创建逻辑。数据库新增字段均为可空字段，不影响旧数据读取。
