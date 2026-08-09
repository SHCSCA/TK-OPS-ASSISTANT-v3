# Runtime Sidecar 与桌面生命周期

本文是 TK-OPS Windows 桌面端管理 Runtime sidecar 的实现与联调说明。产品范围、页面边界和数据模型仍分别以 `docs/PRD.md`、`docs/UI-DESIGN-PRD.md` 与 `docs/ARCHITECTURE-BOOTSTRAP.md` 为准。

## 1. 所有权边界

- Tauri 是生产 Runtime 的唯一进程所有者。
- 正式应用不调用系统 Python，也不从 `PATH` 回退启动 Runtime。
- Runtime 只监听动态分配的 `127.0.0.1` 端口。
- 会话令牌由 Tauri 在内存生成，仅通过子进程环境传递。
- Desktop 只通过 Tauri command 获取当前连接，不保存固定端口或持久令牌。
- Runtime 退出、崩溃、重启和失败都由 Supervisor 统一记录并转换为可见状态。

生产启动链：

```text
单实例边界
→ 解析系统应用数据目录与打包资源
→ 校验 sidecar manifest、版本和 SHA-256
→ 分配动态 loopback 端口与 256-bit 会话令牌
→ 启动 Runtime sidecar
→ 携带 Host 与 Bearer 认证轮询 /api/v1/bootstrap/status
→ 发布不含令牌的 Supervisor 状态
→ Desktop 获取连接并进入 Bootstrap
```

## 2. 制品

固定构建入口：

```powershell
npm run runtime:sidecar:prepare
```

构建配置与输出：

| 对象 | 路径 |
| --- | --- |
| PyInstaller 配置 | `apps/py-runtime/packaging/tk_ops_runtime.spec` |
| Tauri external binary | `apps/desktop/src-tauri/binaries/tk-ops-runtime-x86_64-pc-windows-msvc.exe` |
| 制品清单 | `apps/desktop/src-tauri/resources/runtime/tk-ops-runtime.manifest.json` |
| Runtime 公钥 | `apps/py-runtime/resources/license-public.pem` |

清单至少包含：

```json
{
  "apiVersion": "v1",
  "binary": "tk-ops-runtime.exe",
  "buildId": "<version>-<target>-<hash-prefix>",
  "formatVersion": 1,
  "lifecycleProtocol": 1,
  "schemaReadMin": "0017_p0_enforce_and_cutover",
  "schemaReadMax": "0020_p0e_ai_vertical_chain",
  "sha256": "<SHA-256>",
  "sourceSha256": "<构建输入的确定性 SHA-256>",
  "target": "x86_64-pc-windows-msvc",
  "version": "<package-version>"
}
```

准备脚本会对 Runtime `src`、Alembic 目录与 `alembic.ini`、`pyproject.toml`、资源目录和 PyInstaller spec 计算确定性 `sourceSha256`，并验证平台、版本、源与目标 SHA-256。只有源码指纹、二进制、版本和清单精确匹配时才允许复用现有制品；构建期间输入变化会直接终止构建。

## 3. Supervisor 命令契约

Desktop 使用以下 Tauri command：

| Command | 用途 | 敏感数据 |
| --- | --- | --- |
| `get_runtime_connection` | Runtime 就绪后返回 `baseUrl` 与本次会话 `token` | 仅返回给当前 WebView，不写日志或磁盘 |
| `get_runtime_supervisor_status` | 返回 `starting / ready / offline / failed / stopping` 等安全摘要 | 不含令牌、完整路径和原始 stderr |
| `restart_runtime` | 用户确认后执行有界手动重启 | 返回最新安全状态 |

连接 DTO：

```ts
type RuntimeConnectionDto = {
  baseUrl: string;
  sessionToken: string;
};
```

Supervisor 状态 DTO 只允许包含状态、阶段、尝试次数、稳定错误码、`logId` 与可显示消息。令牌、Provider 凭据、数据库路径、命令行和原始异常禁止进入事件或 DTO。

## 4. Runtime 环境

Supervisor 向 sidecar 注入：

| 环境变量 | 说明 |
| --- | --- |
| `TK_OPS_RUNTIME_MODE=production` | 启用生产安全边界 |
| `TK_OPS_RUNTIME_PORT` | 动态 loopback 端口 |
| `TK_OPS_RUNTIME_EXPECTED_HOST` | 精确 `127.0.0.1:{port}` |
| `TK_OPS_RUNTIME_SESSION_TOKEN` | 256-bit 随机会话令牌 |
| `TK_OPS_RUNTIME_DATA_DIR` | 系统应用数据目录内的 Runtime 根 |
| `TK_OPS_RUNTIME_MANAGED_SIDECAR=1` | 启用 stdin 优雅停机协议 |
| `TK_OPS_RUNTIME_VERSION` | Desktop 与 Runtime 制品版本 |
| `TK_OPS_RUNTIME_ARTIFACT_BUILD_ID` | 已通过 manifest 校验的制品身份 |
| `TK_OPS_RESOURCE_DIR` | Tauri 打包资源根 |
| `TK_OPS_FFPROBE_PATH` | 打包 FFprobe 的精确路径 |
| `PYTHONUTF8=1` | 固定 Python UTF-8 模式 |
| `PYTHONIOENCODING=utf-8` | 固定生命周期管道编码 |

令牌不得出现在参数、磁盘配置、manifest、日志或生命周期消息中。

## 5. 生命周期协议

Runtime stdout 仅以固定前缀输出 Supervisor 可解析的生命周期消息：

```text
TK_OPS_LIFECYCLE {"kind":"runtime_lifecycle","status":"starting","stage":"bootstrap",...}
```

- JSON 使用 ASCII escaped 输出，避免 Windows 控制台编码破坏协议。
- Supervisor 只解析固定前缀，其他 stdout / stderr 仅进入受控诊断日志。
- Tauri 通过 stdin 写入 `shutdown\n` 请求优雅停机。
- 优雅停机超时后，Windows Job Object 负责终止整个进程树。
- Desktop 退出后不得遗留 Runtime、数据库锁或 PyInstaller 子进程。

## 6. 故障与恢复

- 启动超时、制品缺失、版本或哈希错误、端口失败、迁移失败都进入稳定失败态。
- 自动恢复次数、退避和 90 秒冷启动时限由 Supervisor 配置统一管理，禁止无限重启；重启必须先完成旧进程优雅停机与强制清理，再进入退避并启动新世代。
- 崩溃后 Desktop 清除旧连接缓存并显示“重新启动 Runtime”。
- Desktop 冷启动时先挂载启动反馈，并在 `RUNTIME_NOT_READY` 状态下以 250ms 间隔有界等待最多 90 秒；Supervisor ready 后自动取得会话，永久错误不进入轮询。
- 手动重启生成新端口与新令牌，旧连接不得继续使用。
- 数据库迁移完成并验证前写门保持关闭；失败时不启动 HTTP 服务。
- 写门重新开放后禁止自动恢复迁移前备份，回退只能使用兼容当前 Schema 的回退 Runtime 制品。

## 7. 验收入口

P0-F 已于 2026-08-01 统一执行：

```powershell
npm run version:check
npm run typecheck
npm test
npm run test:e2e
npm run test:sidecar-smoke
npm run desktop:tauri -- build --bundles nsis
npm run test:installer-smoke
```

`test:sidecar-smoke` 使用临时数据目录验证动态端口、认证健康检查和优雅退出。`test:installer-smoke` 使用临时安装与数据目录验证无需系统 Python、单实例和进程树清理。两个脚本都不得访问或清理用户真实工作区。

本次验收的 Sidecar build ID 为 `0.4.7-x86_64-pc-windows-msvc-d7538489342f`；NSIS 安装包 smoke 已通过 Supervisor ready、生产数据落点、离线启动、单实例和进程树清理。完整测试与视觉证据见 `docs/PROJECT-STATUS.md`。

本文仅定义实现与验收契约；是否通过以 `docs/PROJECT-STATUS.md` 中最新一次阶段证据为准。
