# Windows 桌面制品验收

本目录只存放安装包与进程生命周期 smoke，不替代 Runtime、Desktop、E2E 或 Rust 单元测试。

## 可见 GUI smoke

`npm run build:windows-release -- --channel test` 会在 Tauri 构建后把本次免安装 ZIP 解压到全新临时目录，再从该目录自动启动可见桌面窗口并执行 `windows-gui-smoke.ps1`。脚本验证 ZIP 全新解压、根目录单 Desktop EXE、可见主窗口、标准最小化/最大化/关闭样式、窗口状态切换、Runtime ready、单实例、`WM_CLOSE` 优雅退出与重启恢复；冷启动探测会重新解析当前有效窗口句柄，证据同时绑定 Desktop EXE 与 portable ZIP 的 SHA256。许可证激活与 Web 前端内容由同一构建编排中的 active Playwright 首启用例验证，GUI smoke 不读取 Runtime Session 或许可证密钥。

Windows PowerShell 5.1 通过 `windows-gui-smoke-runner.ps1` 显式按 UTF-8
载入主脚本，避免无 BOM 中文源码被系统代码页误解析。

## 安装包 smoke

先构建 NSIS：

```powershell
npm run desktop:tauri -- build --bundles nsis
```

再执行：

```powershell
npm run test:installer-smoke
```

也可显式指定安装包：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File tests/packaging/windows-installer-smoke.ps1 `
  -InstallerPath <absolute-setup-exe>
```

脚本只在系统临时目录创建安装与数据根，验证：

1. 安装后的应用在隐藏 Python `PATH` 后仍能启动 sidecar。
2. 不以 sidecar 进程存在作为就绪结论；等待
   `data/logs/runtime-supervisor.jsonl` 中出现结构化
   `operation=runtime.ready` 证据。
3. production Runtime 的 SQLite 数据库真实位于
   `data/runtime/runtime.db`，并具有 SQLite 文件头。
4. production Runtime 日志真实位于
   `data/runtime/logs/runtime.jsonl`，且包含
   `operation=runtime.started`、`context.mode=production` 和
   `context.databaseReady=true`。
5. 第二个 Desktop 实例不会创建第二个 Runtime。
6. Desktop 退出后 Runtime 进程树被清理。
7. 最后执行静默卸载并清理受控临时目录。

`TK_OPS_INSTALLER_SMOKE_DATA_DIR` 只允许指向系统临时目录内的本次
smoke 数据根。脚本只读取 token-free 的 Supervisor / Runtime 结构化日志，
仅在失败时显示经过字段格式校验的 `operation`、`errorCode` 与 `logId`；
不会读取、解析或打印 Runtime 会话 token。

脚本通过可执行文件路径限制进程范围，并在删除前再次校验临时目录前缀，
不会停止或删除其他 TK-OPS 安装与用户工作区。
