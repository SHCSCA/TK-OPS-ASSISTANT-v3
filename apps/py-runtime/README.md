# Python Runtime Creative Chain Baseline

`apps/py-runtime` 是 TK-OPS 的本地 Runtime，技术栈主线为 `Python + FastAPI + SQLite`。

## 当前职责

- 提供 FastAPI 应用工厂和启动入口
- 提供统一配置服务 `SettingsService`
- 提供统一许可证服务 `LicenseService`
- 提供统一项目域服务 `DashboardService`
- 提供统一 AI 能力配置服务 `AICapabilityService`
- 提供统一文本生成服务 `AITextGenerationService`
- 提供统一脚本服务 `ScriptService`
- 提供统一分镜服务 `StoryboardService`
- 使用 SQLite 持久化 `system_config`
- 使用 SQLite 持久化 `license_grant`
- 使用 SQLite 持久化 `projects`、`session_context`
- 使用 SQLite 持久化 `ai_capability_configs`、`ai_provider_settings`
- 使用 SQLite 持久化 `ai_job_records`、`script_versions`、`storyboard_versions`
- 输出结构化日志文件 `runtime.jsonl`
- 为请求分配 `requestId`
- 将异常与验证失败统一包装为 JSON 错误信封

## 已落地接口

- `GET /api/dashboard/summary`
  - 返回最近项目列表与当前项目上下文
- `POST /api/dashboard/projects`
  - 创建项目并设置为当前项目
- `GET /api/dashboard/context`
  - 返回当前项目上下文
- `PUT /api/dashboard/context`
  - 切换当前项目上下文
- `GET /api/settings/health`
  - 返回服务状态、版本、当前时间和运行模式
- `GET /api/settings/config`
  - 返回完整配置文档与 revision
- `PUT /api/settings/config`
  - 写入完整配置文档并递增 revision
- `GET /api/settings/diagnostics`
  - 返回数据库路径、日志目录、revision、模式和健康状态
- `GET /api/settings/ai-capabilities`
  - 返回 7 个能力配置和 4 个 provider 的当前状态
- `PUT /api/settings/ai-capabilities`
  - 覆盖写入完整能力配置集合
- `PUT /api/settings/ai-capabilities/providers/{provider}/secret`
  - 写入 provider 密钥到本地安全存储
- `POST /api/settings/ai-capabilities/providers/{provider}/health-check`
  - 返回 provider 是否具备当前阶段的文本生成能力
- `GET /api/license/status`
  - 返回当前授权状态、受限模式、机器标识和绑定状态
- `POST /api/license/activate`
  - 使用本地占位适配器激活许可证并绑定当前 `machineId`
- `GET /api/scripts/projects/{projectId}/document`
  - 返回项目脚本文档、版本列表和最近 AI 作业
- `PUT /api/scripts/projects/{projectId}/document`
  - 手工保存脚本版本
- `POST /api/scripts/projects/{projectId}/generate`
  - 用能力中心配置生成脚本版本
- `POST /api/scripts/projects/{projectId}/rewrite`
  - 用能力中心配置改写当前脚本版本
- `GET /api/storyboards/projects/{projectId}/document`
  - 返回项目分镜文档、版本列表和最近 AI 作业
- `PUT /api/storyboards/projects/{projectId}/document`
  - 手工保存分镜版本
- `POST /api/storyboards/projects/{projectId}/generate`
  - 根据当前脚本版本生成分镜版本

## 本地运行

- 安装依赖：`python -m pip install -e "./apps/py-runtime[dev]"`
- 启动 Runtime：`python -m uvicorn main:app --app-dir apps/py-runtime/src --host 127.0.0.1 --port 8000 --reload`
- 运行 Runtime 测试：`python -m pytest tests/runtime -q`
- 运行契约测试：`python -m pytest tests/contracts -q`

## 目录说明

- `src/api/routes/`
  - `/api/dashboard`、`/api/settings`、`/api/license`、`/api/scripts`、`/api/storyboards` 路由组
- `src/app/`
  - 应用启动、配置、日志和异常处理
- `src/services/`
  - 业务编排服务，当前包括项目、AI 能力、许可证、脚本和分镜服务
- `src/repositories/`
  - SQLite 数据访问封装
- `src/persistence/`
  - 数据库初始化、迁移与连接基础设施
- `src/schemas/`
  - 请求/响应 DTO 与信封定义

## 环境与数据目录

- 默认数据目录：仓库根 `.runtime-data/`
- 可覆盖：`TK_OPS_RUNTIME_DATA_DIR`
- 可单独覆盖数据库路径：`TK_OPS_RUNTIME_DB_PATH`
- 默认模式来自 `TK_OPS_RUNTIME_MODE`，未设置时为 `development`

## 当前边界

- 当前许可证激活通过本地占位适配器完成，尚未接入远端授权服务
- 当前只打通创作主链最小闭环，尚未接入任务队列、媒体流水线和 WebSocket
- 尚未接入 API Key 安全存储、许可证撤销和多设备迁移，只预留后续扩展空间
- 日志当前写入文件，不写入数据库表
