# Desktop Creative Chain Baseline

`apps/desktop` 是 TK-OPS 的桌面端入口，技术栈固定为 `Tauri 2 + Vue 3 + TypeScript + Vite`。

## 当前职责

- 提供最小可运行 App Shell
- 固定 16 个正式路由与导航分组
- 通过全局 Store 管理 Runtime、许可证、项目上下文、AI 能力、脚本与分镜状态
- 已落地或已接线页面覆盖许可证向导、Dashboard、AI 设置、脚本中心、分镜中心、AI 剪辑工作台 M05-A、配音中心、资产中心，以及 M10-M15 Runtime 页面基线
- 首启阶段包含启动加载层、永久授权说明、机器码复制与离线授权码激活

## 开发态启动（推荐从仓库根目录）

1. `npm --prefix apps/desktop install`
2. `python -m venv venv`
3. `venv\\Scripts\\python.exe -m pip install -e "./apps/py-runtime[dev]"`
4. `npm run app:dev`

`npm run app:dev` 会自动：
- 启动 Runtime
- 等待 `/api/settings/health`
- 启动 `tauri dev`
- 检测已运行的 Runtime 或前端开发服务器并优先复用
- 在桌面窗口退出后回收 Runtime

Windows 下也可双击根目录 `start-desktop-dev.cmd`。

## 仅调试桌面端

- 前端开发服务器：`npm run dev`
- Tauri 开发态：`npm run tauri dev`
- 测试：`npm run test`
- 构建：`npm run build`

## 目录说明

- `src/app/`：Router 与 Runtime API 客户端
- `src/layouts/`：App Shell
- `src/pages/`：16 个页面根组件
- `src/stores/`：Pinia 全局状态
- `src/types/`：UI DTO 与 Runtime 协议类型
- `src/styles/`：全局样式与设计令牌
- `src-tauri/`：Tauri 原生壳配置与 Rust 入口

## 当前边界

- 已落地真实闭环页面：许可证向导、Dashboard、AI 设置、脚本中心、分镜中心、配音中心、资产中心
- 已接线页面：AI 剪辑工作台 M05-A、视频拆解、账号管理、设备与工作区、自动化执行、发布、渲染导出、复盘优化
- 待深化页面：字幕对齐，以及已接线页面中的真实 AI、渲染、执行层能力
- 许可证激活已改为本地离线签名校验，不接远端授权
- 当前模块状态以 `docs/PROJECT-STATUS.md` 为准
