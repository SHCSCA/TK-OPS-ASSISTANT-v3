# Python Runtime M0

`apps/py-runtime` 是 TK-OPS 的本地 Python Runtime 入口，技术主线固定为 `Python + FastAPI + SQLAlchemy + Alembic`。

## 当前职责

- 提供最小 FastAPI 应用、基础配置与日志初始化。
- 提供 `/api/settings/health` 健康检查接口，并遵守统一 JSON 信封协议。
- 固定 `src/` 下的模块边界，为后续真实接口和模型实现提供稳定落点。
- 为下一轮真实服务、任务和模型实现提供入口结构。

## 本轮未做

- 未实现除健康检查以外的业务接口。
- 未创建数据库模型、仓储和任务执行逻辑。
- 未接入 WebSocket、持久化和媒体流水线。

## 本地运行

- 安装依赖：`python -m pip install -e "./apps/py-runtime[dev]"`
- 启动 Runtime：`python -m uvicorn main:app --app-dir apps/py-runtime/src --host 127.0.0.1 --port 8000 --reload`
- 运行 Runtime 测试：`python -m pytest tests/runtime -q`
- 运行契约测试：`python -m pytest tests/contracts -q`

## 目录说明

- `src/api/routes/`
  Runtime 路由入口分组。
- `src/app/`
  应用启动、配置和依赖装配。
- `src/domain/models/`
  核心持久化模型。
- `src/services/`
  业务编排服务。
- `src/repositories/`
  数据访问层。
- `src/schemas/`
  请求响应 schema。
- `src/tasks/`
  长任务与队列任务。
- `src/media/`
  渲染与转码流水线。
- `src/ai/providers/`
  AI Provider 适配层。
- `src/persistence/`
  数据库和持久化基础设施。

