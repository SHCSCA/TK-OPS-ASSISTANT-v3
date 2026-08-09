# TK-OPS Python Runtime

`apps/py-runtime` 是 TK-OPS 的本地 Runtime，技术栈主线为 `Python + FastAPI + SQLite`。

## 当前职责

- 在 HTTP 监听前执行正式 Alembic 迁移、旧库指纹校验、迁移锁和目标契约检查
- 提供 `/api/v1` 的 Bootstrap、系统配置、诊断、持久任务、账号事件与 AI 配置纵向链
- 强制本机 Host、Origin、Runtime Session 和许可证门禁
- 使用 SQLite 持久化配置、许可证、任务、事件以及 legacy 迁移期业务数据
- 输出结构化日志、统一大写错误码、`log_id` 和 v1 成功/失败信封
- 提供离线一机一码授权，并将许可证原文保存到系统安全存储
- legacy `/api/...` 仅作为受控迁移适配层；新增能力只进入 `/api/v1`

## 本地运行（使用项目根 venv）

1. 在仓库根创建虚拟环境：`python -m venv venv`
2. 安装依赖：`venv\\Scripts\\python.exe -m pip install -e "./apps/py-runtime[dev]"`
3. 启动 Runtime：`npm run runtime:dev`

也可直接使用：
`venv\\Scripts\\python.exe -m uvicorn main:app --app-dir apps/py-runtime/src --host 127.0.0.1 --port 8000 --reload`

上面的 `8000` 只用于手动开发。正式桌面应用由 Tauri Supervisor 启动已校验的 Runtime sidecar，并为每次会话分配动态 loopback 端口；生产链路不调用系统 Python。

## 测试

- P0-A 至 P0-F 已按批准节奏完成阶段验证和最终全量验收
- 后续 P1 / P2 仍按批准计划完成一个阶段后集中验证一次，开发过程中不反复运行整套测试

## 目录说明

- `src/api/routes/v1/`：当前版本化 HTTP 路由
- `src/api/websocket/`：v1 与 legacy WebSocket 协议
- `src/api/routes/legacy/`：受控 legacy 薄适配器
- `src/app/`：应用装配、门禁、生命周期、配置、日志与异常处理
- `src/services/tasks/`、`src/services/events/`：持久任务、恢复和事件 outbox
- `src/services/ai_configuration_v1/`：Provider、模型、能力、Route、Prompt、合成模板与账号 Recipe
- `src/services/config/`：统一配置总线
- `src/repositories/`：SQLite 数据访问封装
- `src/persistence/migration/`：数据库接管、备份恢复和迁移契约
- `src/schemas/v1/`：版本化请求/响应 DTO 与信封
- `tools/license-issuer/`：离线授权机工具、密钥生成脚本、BAT 入口

接口真源位于 `docs/api/v1/`。旧接口调用索引
`docs/RUNTIME-API-CALLS.md` 已冻结，不再承载新增契约。

## 离线授权

- Runtime 只持有公钥，用于校验授权码
- 授权机持有私钥，用于生成授权码
- 公钥路径默认读取 `TK_OPS_LICENSE_PUBLIC_KEY_PATH`，未配置时回退到仓库受控路径
- 可使用以下脚本生成密钥对：

```powershell
venv\Scripts\python.exe apps/py-runtime/tools/license-issuer/generate_keypair.py --output-dir .runtime-data/licenses
```

- 授权机签发授权码：

```powershell
venv\Scripts\python.exe apps/py-runtime/tools/license-issuer/issue_license.py --machine-code TKOPS-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
```
