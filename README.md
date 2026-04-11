# TK-OPS

TK-OPS 当前处于“创作主链基线已打通”的阶段。产品和设计真源在 `docs/`，代码已经具备桌面壳、Runtime 配置底座、统一错误信封、本地许可证首启闭环、项目上下文总线、AI 能力中心，以及 Dashboard / Script / Storyboard 的最小真实联通链路。

## 版本真源

- 主版本唯一可编辑真源：根 `package.json` 的 `version`
- 镜像版本字段由脚本同步，不手工维护：
  - `apps/desktop/src-tauri/Cargo.toml`
  - `apps/desktop/src-tauri/tauri.conf.json`
  - `apps/py-runtime/pyproject.toml`
- 常用命令：
  - `npm run version:sync`
  - `npm run version:check`

## 当前能力

- `apps/desktop/`
  - Tauri 2 + Vue 3 + Vite 桌面壳
  - 16 个正式路由与导航分组
  - `setup_license_wizard` 已升级为真实首启向导
  - `creator_dashboard` 已升级为真实项目入口
  - `ai_system_settings` 已升级为真实设置页与 AI 能力中心
  - `script_topic_center` 已升级为真实脚本页
  - `storyboard_planning_center` 已升级为真实分镜页
  - 统一 `ConfigBusStore` 管理 Runtime 健康、配置、诊断和保存状态
  - 独立 `LicenseStore` 管理许可证状态、激活和路由门禁
  - 新增 `ProjectStore`、`AICapabilityStore`、`ScriptStudioStore`、`StoryboardStore`
- `apps/py-runtime/`
  - FastAPI Runtime 入口
  - SQLite 持久化 `system_config`
  - SQLite 持久化 `license_grant` 和本地 `machineId`
  - SQLite 持久化 `projects`、`session_context`
  - SQLite 持久化 `ai_capability_configs`、`ai_provider_settings`
  - SQLite 持久化 `ai_job_records`、`script_versions`、`storyboard_versions`
  - 结构化日志文件输出
  - 统一错误信封与 `requestId`
  - 已落地接口：
    - `GET /api/dashboard/summary`
    - `POST /api/dashboard/projects`
    - `GET /api/dashboard/context`
    - `PUT /api/dashboard/context`
    - `GET /api/settings/health`
    - `GET /api/settings/config`
    - `PUT /api/settings/config`
    - `GET /api/settings/diagnostics`
    - `GET /api/settings/ai-capabilities`
    - `PUT /api/settings/ai-capabilities`
    - `PUT /api/settings/ai-capabilities/providers/{provider}/secret`
    - `POST /api/settings/ai-capabilities/providers/{provider}/health-check`
    - `GET /api/license/status`
    - `POST /api/license/activate`
    - `GET /api/scripts/projects/{projectId}/document`
    - `PUT /api/scripts/projects/{projectId}/document`
    - `POST /api/scripts/projects/{projectId}/generate`
    - `POST /api/scripts/projects/{projectId}/rewrite`
    - `GET /api/storyboards/projects/{projectId}/document`
    - `PUT /api/storyboards/projects/{projectId}/document`
    - `POST /api/storyboards/projects/{projectId}/generate`
- `tests/`
  - Desktop 壳层、项目守卫、Dashboard、设置页、脚本页和分镜页测试
  - Runtime 行为测试
  - API 契约测试

## 本地运行

1. 安装前端依赖：`npm install`
2. 安装 Runtime 与测试依赖：`python -m pip install -e "./apps/py-runtime[dev]"`
3. 启动 Runtime：`python -m uvicorn main:app --app-dir apps/py-runtime/src --host 127.0.0.1 --port 8000 --reload`
4. 启动桌面开发服务器：`npm --prefix apps/desktop run dev`
5. 首次进入受保护页面时会自动跳转到 `/setup/license`，完成许可证激活和初始配置后再进入工作台
6. Dashboard 负责创建/选择项目；未建立项目上下文时，脚本、分镜、发布等项目页会被守卫重定向回 Dashboard
7. `AI 与系统设置` 中已经包含能力级 AI 配置中心；脚本和分镜页会消费当前项目上下文和 Runtime 真数据
8. 运行校验：
   - `npm run version:check`
   - `npm --prefix apps/desktop run test`
   - `npm --prefix apps/desktop run build`
   - `python -m pytest tests/runtime -q`
   - `python -m pytest tests/contracts -q`

## Runtime 数据目录

- 默认写入仓库根目录下的 `.runtime-data/`
- 可通过 `TK_OPS_RUNTIME_DATA_DIR` 覆盖数据目录
- SQLite 文件默认位于 `<data-dir>/runtime.db`
- 日志文件默认位于 `<logDir>/runtime.jsonl`

## 当前边界

- 已落地本地许可证首启闭环，但当前仍是本地占位适配器，尚未接远端授权服务
- 真实创作链已覆盖“创建项目 -> 脚本保存/生成/改写 -> 分镜生成/保存”的最小闭环
- 时间线、配音、字幕、渲染、发布等其余 P0/P1 业务能力仍未落地
- 本轮不包含 API Key 编辑、许可证撤销、多设备迁移和具体安全存储接入
- 配置广播目前只做到桌面端进程内状态同步，尚未引入 WebSocket 推送
