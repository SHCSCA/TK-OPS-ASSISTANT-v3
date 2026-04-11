# TK-OPS

TK-OPS 当前处于 M0 可运行基线阶段，产品与设计真源位于 `docs/`，实现入口统一收敛到根级工作区。

## 版本真源

- TK-OPS 主版本唯一可编辑真源：根 `package.json` 的 `version`。
- 必需镜像版本字段（自动同步，不手工多点维护）：
  - `apps/desktop/src-tauri/Cargo.toml`
  - `apps/py-runtime/pyproject.toml`
  - `apps/desktop/src-tauri/tauri.conf.json`
- 常用命令：
  - `npm run version:sync`
  - `npm run version:check`

## 仓库结构

- `docs/`
  当前产品真源、UI 真源和实现骨架真源。
- `apps/desktop/`
  Tauri 2 + Vue 3 桌面壳入口，已落地最小 App Shell、16 个正式路由占位页和 Runtime 健康状态接入。
- `apps/py-runtime/`
  Python Runtime 入口，已落地最小 FastAPI 应用和 `/api/settings/health` 健康检查接口。
- `tests/`
  前端壳层装配测试、Runtime 测试和契约测试落点。

## 本地运行

- 安装前端依赖：`npm install`
- 安装 Runtime 与测试依赖：`python -m pip install -e "./apps/py-runtime[dev]"`
- 启动 Runtime：`python -m uvicorn main:app --app-dir apps/py-runtime/src --host 127.0.0.1 --port 8000 --reload`
- 启动桌面壳开发服务器：`npm --prefix apps/desktop run dev`
- 执行版本一致性检查：`npm run version:check`

## 当前边界

- 当前已包含可运行桌面壳、16 个正式路由占位页和真实 Runtime 健康接口。
- 当前仍不包含许可证、脚本生成、分镜、时间线、发布等业务能力的完整实现。
- 目录命名、路由归属和模型落点以 `docs/ARCHITECTURE-BOOTSTRAP.md` 为准。
- 旧 `desktop_app/` 或旧 Qt 主线不进入新骨架。
