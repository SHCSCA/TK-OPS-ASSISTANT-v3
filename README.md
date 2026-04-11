# TK-OPS

TK-OPS 当前处于工程骨架阶段，产品与设计真源位于 `docs/`，实现入口统一收敛到根级工作区。

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
  Tauri 2 + Vue 3 桌面壳入口，当前仅保留目录、入口配置和职责说明。
- `apps/py-runtime/`
  Python Runtime 入口，当前仅保留目录、入口配置和职责说明。
- `tests/`
  预留前端、Runtime 和契约测试落点。

## 当前边界

- 本轮不包含可运行页面、不包含真实 Runtime 接口、不包含数据库模型实现。
- 目录命名、路由归属和模型落点以 `docs/ARCHITECTURE-BOOTSTRAP.md` 为准。
- 旧 `desktop_app/` 或旧 Qt 主线不进入新骨架。
