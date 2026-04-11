# TK-OPS

TK-OPS 当前处于 M0 可运行基线阶段。产品和设计真源在 `docs/`，代码已经具备桌面壳、Runtime 配置底座、统一错误信封、本地许可证首启闭环和最小联通链路。

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
  - 16 个正式路由占位页
  - `setup_license_wizard` 已升级为真实首启向导
  - `ai_system_settings` 已升级为真实设置页
  - 统一 `ConfigBusStore` 管理 Runtime 健康、配置、诊断和保存状态
  - 独立 `LicenseStore` 管理许可证状态、激活和路由门禁
- `apps/py-runtime/`
  - FastAPI Runtime 入口
  - SQLite 持久化 `system_config`
  - SQLite 持久化 `license_grant` 和本地 `machineId`
  - 结构化日志文件输出
  - 统一错误信封与 `requestId`
  - 已落地接口：
    - `GET /api/settings/health`
    - `GET /api/settings/config`
    - `PUT /api/settings/config`
    - `GET /api/settings/diagnostics`
    - `GET /api/license/status`
    - `POST /api/license/activate`
- `tests/`
  - Desktop 壳层、首启向导与设置页测试
  - Runtime 行为测试
  - API 契约测试

## 本地运行

1. 安装前端依赖：`npm install`
2. 安装 Runtime 与测试依赖：`python -m pip install -e "./apps/py-runtime[dev]"`
3. 启动 Runtime：`python -m uvicorn main:app --app-dir apps/py-runtime/src --host 127.0.0.1 --port 8000 --reload`
4. 启动桌面开发服务器：`npm --prefix apps/desktop run dev`
5. 首次进入受保护页面时会自动跳转到 `/setup/license`，完成许可证激活和初始配置后再进入工作台
6. 运行校验：
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
- 脚本生成、分镜、时间线、发布等其余 P0 业务能力还未落地
- 本轮不包含 API Key 编辑、许可证撤销、多设备迁移和具体安全存储接入
- 配置广播目前只做到桌面端进程内状态同步，尚未引入 WebSocket 推送
