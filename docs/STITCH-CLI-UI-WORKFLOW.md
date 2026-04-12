# Stitch CLI UI 生成流程

## 目标

后续 TK-OPS 的 UI 设计输入默认走 Stitch CLI，不再依赖当前不稳定的 Stitch MCP 会话。Stitch 产物只作为设计参考，最终实现必须落回现有 Vue、Pinia、Runtime client 与 CSS token 架构。

## 当前可用状态

- CLI 包：`@_davideast/stitch-mcp`
- 健康检查：`npx -y @_davideast/stitch-mcp doctor --json`
- 设计项目：`projects/7613239389915091327`
- 项目标题：`TK-OPS UI Lab`
- 首页与全局壳层屏幕：`projects/7613239389915091327/screens/932a58209b4c4fbdbf63c3b30753eada`
- 本地设计稿目录：`design-drafts/`

## 固定流程

1. 先执行健康检查：

```powershell
npx -y @_davideast/stitch-mcp doctor --json
```

2. 创建或复用设计项目：

```cmd
npx -y @_davideast/stitch-mcp tool create_project -d "{\"title\":\"TK-OPS UI Lab\"}" -o json
```

3. 生成单页设计稿，`deviceType` 固定使用 `DESKTOP`：

```cmd
npx -y @_davideast/stitch-mcp tool generate_screen_from_text -d "{\"projectId\":\"7613239389915091327\",\"deviceType\":\"DESKTOP\",\"prompt\":\"<中文产品级 UI 提示词>\"}" -o json
```

4. 拉取 HTML 设计参考：

```cmd
npx -y @_davideast/stitch-mcp tool get_screen_code -d "{\"projectId\":\"7613239389915091327\",\"screenId\":\"<screenId>\"}" -o json
```

5. 可选拉取截图参考：

```cmd
npx -y @_davideast/stitch-mcp tool get_screen_image -d "{\"projectId\":\"7613239389915091327\",\"screenId\":\"<screenId>\"}" -o json
```

## Windows 调用约束

- PowerShell 容易破坏复杂 JSON 引号，推荐使用 Node 包一层 `cmd /c` 调用 CLI，并通过 `JSON.stringify(...)` 传入 `-d`。
- 暂时不要使用 `-f/--data-file`；当前 CLI 的该路径会调用 `Bun.file(...)`，在未安装 Bun 的 Node 环境下会报 `Bun is not defined`。
- `projectId` 传纯数字 ID，例如 `7613239389915091327`；`screenId` 传纯屏幕 ID，例如 `932a58209b4c4fbdbf63c3b30753eada`。

推荐 PowerShell 调用模板：

```powershell
# 将下面这段 JavaScript 传给 node 执行，避免 PowerShell 改写 JSON 引号。
const { spawnSync } = require("node:child_process");
const data = { projectId: "7613239389915091327", deviceType: "DESKTOP", prompt: "<中文产品级 UI 提示词>" };
const args = ["/d", "/s", "/c", "npx", "-y", "@_davideast/stitch-mcp", "tool", "generate_screen_from_text", "-d", JSON.stringify(data), "-o", "json"];
const result = spawnSync(process.env.ComSpec || "cmd.exe", args, { encoding: "utf8", maxBuffer: 1024 * 1024 * 20 });
process.stdout.write(result.stdout || "");
process.stderr.write(result.stderr || "");
process.exit(result.status ?? 1);
```

## 提示词规范

- 必须明确页面属于 TK-OPS 的 16 页范围之一。
- 必须使用中文用户文案，保留必要技术词：Runtime、Provider、OpenAI。
- 必须说明真实数据边界：不生成假业务数字；无数据时使用空态、引导态或状态说明。
- 必须说明桌面端结构：Title Bar、Sidebar、Content Host、Detail Panel、Status Bar。
- 必须说明视觉方向：本地 AI 视频创作指挥舱、低噪声、高层级、少量玻璃/磨砂层次、清晰状态反馈。

## 落地规则

- 不直接复制 Stitch 生成 HTML、Tailwind class 或外链资源到生产 Vue 文件。
- 只提炼布局层级、视觉节奏、色彩意图、状态表达和动效意图。
- 实现时必须继续通过现有 Runtime client、Pinia store、配置总线和 CSS variables。
- 落地后按项目实际改动运行前端测试与构建；需要联调时再运行 `npm run app:dev`。
