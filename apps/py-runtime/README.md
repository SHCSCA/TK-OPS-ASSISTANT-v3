# Python Runtime Skeleton

`apps/py-runtime` 是 TK-OPS 的本地 Python Runtime 入口，技术主线固定为 `Python + FastAPI + SQLAlchemy + Alembic`。

## 当前职责

- 预留 Runtime 路由、服务、模型、任务、媒体流水线和 AI Provider 适配层。
- 固定 `src/` 下的模块边界，为后续真实接口和模型实现提供稳定落点。
- 为下一轮“最小可启动 Runtime”保留 `pyproject.toml` 和源码目录结构。

## 本轮未做

- 未实现 FastAPI 应用。
- 未定义任何 `/api/*` 真实路由。
- 未创建数据库模型、Pydantic schema 或任务执行逻辑。

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

