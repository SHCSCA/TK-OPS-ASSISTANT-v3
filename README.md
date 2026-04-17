# TK-OPS

TK-OPS 当前处于“创作主链基线已打通”阶段，代码具备：桌面壳、Runtime 配置总线、真实离线授权首启链路、项目上下文总线，以及 Dashboard / Script / Storyboard / Workspace M05-A 最小联通链路。

## 版本真源

- 唯一可编辑版本：根 `package.json` 的 `version`
- 镜像版本由脚本维护：
  - `apps/desktop/src-tauri/Cargo.toml`
  - `apps/desktop/src-tauri/tauri.conf.json`
  - `apps/py-runtime/pyproject.toml`
- 命令：
  - `npm run version:sync`
  - `npm run version:check`
- 发布记录：`CHANGELOG.md`

## 开发环境初始化（Windows）

1. 安装 Node.js、Rust（含 `cargo`）、Python
2. 安装前端依赖：`npm --prefix apps/desktop install`
3. 创建虚拟环境：`python -m venv venv`
4. 安装 Runtime 依赖：`venv\\Scripts\\python.exe -m pip install -e "./apps/py-runtime[dev]"`

## 开发态一键启动桌面应用

- 主入口：`npm run app:dev`
- Windows 双击入口：`start-desktop-dev.cmd`

启动器行为：
- 优先使用 `venv\\Scripts\\python.exe`（不存在时回退系统 `python`）
- 启动 Runtime 并轮询 `GET /api/settings/health`
- 如 8000 Runtime 或 1420 前端开发服务器已存在，则优先复用现有服务
- Runtime 就绪后启动 `tauri dev`
- 关闭桌面应用后回收 Runtime 子进程

## 常用命令

- 仅启动 Runtime：`npm run runtime:dev`
- 仅启动 Tauri 开发态：`npm run desktop:tauri:dev`
- Desktop 测试：`npm --prefix apps/desktop run test`
- Desktop 构建：`npm --prefix apps/desktop run build`
- Runtime 测试：`venv\\Scripts\\python.exe -m pytest tests/runtime -q`
- Contract 测试：`venv\\Scripts\\python.exe -m pytest tests/contracts -q`

## 离线授权工具

- 客户机启动后会显示启动加载层和首启授权向导
- 向导会展示本机机器码，用户可复制后发给授权人员
- 授权机工具目录：`apps/py-runtime/tools/license-issuer`
- 生成密钥对：
  - `venv\\Scripts\\python.exe apps/py-runtime/tools/license-issuer/generate_keypair.py --output-dir .runtime-data/licenses`
- 签发授权码：
  - `venv\\Scripts\\python.exe apps/py-runtime/tools/license-issuer/issue_license.py --machine-code <机器码>`
- Windows 授权机也可直接双击：
  - `apps\\py-runtime\\tools\\license-issuer\\issue-license.bat`

## Stitch CLI 设计流程

- UI 设计输入默认使用 Stitch CLI，不依赖当前会话内的 Stitch MCP 握手。
- 固定流程见：`docs/STITCH-CLI-UI-WORKFLOW.md`
- 设计稿与参考物料目录：`design-drafts/`
- 辅助脚本位于 `scripts/stitch-connect.js` 与 `scripts/stitch-generate-dashboard.js`
- Stitch 输出只作为设计参考，最终实现仍落回 Vue、Pinia、Runtime client 与 CSS token 架构。

## 当前边界

- 许可证激活已改为本地离线签名校验，不接入远端授权服务
- 桌面壳、TaskBus、视频导入、AI 剪辑工作台 M05-A、配音中心、资产中心和 M10-M15 Runtime 页面接线已进入阶段性基线
- Provider Secret UI、真实 OpenAI 调用链路、真实 TTS Provider、字幕对齐、时间线、渲染与发布执行层仍需按计划继续落地
- 当前模块状态以 `docs/PROJECT-STATUS.md` 为准；接口调用关系以 `docs/RUNTIME-API-CALLS.md` 为唯一真源
