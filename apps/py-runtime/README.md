# Python Runtime M0

`apps/py-runtime` 是 TK-OPS 的本地 Runtime，技术栈主线为 `Python + FastAPI + SQLite`。

## 当前职责

- 提供 FastAPI 应用工厂和启动入口
- 提供统一配置服务 `SettingsService`
- 提供统一许可证服务 `LicenseService`
- 使用 SQLite 持久化 `system_config`
- 使用 SQLite 持久化 `license_grant`
- 输出结构化日志文件 `runtime.jsonl`
- 为请求分配 `requestId`
- 将异常与验证失败统一包装为 JSON 错误信封

## 已落地接口

- `GET /api/settings/health`
  - 返回服务状态、版本、当前时间和运行模式
- `GET /api/settings/config`
  - 返回完整配置文档与 revision
- `PUT /api/settings/config`
  - 写入完整配置文档并递增 revision
- `GET /api/settings/diagnostics`
  - 返回数据库路径、日志目录、revision、模式和健康状态
- `GET /api/license/status`
  - 返回当前授权状态、受限模式、机器标识和绑定状态
- `POST /api/license/activate`
  - 使用本地占位适配器激活许可证并绑定当前 `machineId`

## 本地运行

- 安装依赖：`python -m pip install -e "./apps/py-runtime[dev]"`
- 启动 Runtime：`python -m uvicorn main:app --app-dir apps/py-runtime/src --host 127.0.0.1 --port 8000 --reload`
- 运行 Runtime 测试：`python -m pytest tests/runtime -q`
- 运行契约测试：`python -m pytest tests/contracts -q`

## 目录说明

- `src/api/routes/`
  - `/api/settings` 与 `/api/license` 路由组
- `src/app/`
  - 应用启动、配置、日志和异常处理
- `src/services/`
  - 业务编排服务，当前包括 `SettingsService` 与 `LicenseService`
- `src/repositories/`
  - SQLite 数据访问封装
- `src/persistence/`
  - 数据库初始化与连接基础设施
- `src/schemas/`
  - 请求/响应 DTO 与信封定义

## 环境与数据目录

- 默认数据目录：仓库根 `.runtime-data/`
- 可覆盖：`TK_OPS_RUNTIME_DATA_DIR`
- 可单独覆盖数据库路径：`TK_OPS_RUNTIME_DB_PATH`
- 默认模式来自 `TK_OPS_RUNTIME_MODE`，未设置时为 `development`

## 当前边界

- 当前许可证激活通过本地占位适配器完成，尚未接入远端授权服务
- 尚未接入任务队列、媒体流水线和 WebSocket
- 尚未接入 API Key 安全存储、许可证撤销和多设备迁移，只预留后续扩展空间
- 日志当前写入文件，不写入数据库表
