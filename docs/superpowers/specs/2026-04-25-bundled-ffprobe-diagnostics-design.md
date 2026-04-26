# 内置 FFprobe 与检测中心设计

## 1. 目标

为 TK-OPS 提供稳定、可打包、可诊断的媒体基础工具能力，并在 `AI 与系统设置` 页面内提供“检测中心”，让用户能一键确认系统运行所必需的配置是否完整。

设计必须满足：

- 不提交大型二进制文件。
- 不新增正式页面。
- 不绕过配置总线和 Runtime 服务层。
- 所有检测结果由 Runtime 返回，前端只负责展示和触发。
- 所有失败路径有中文提示、日志和修复建议。

## 2. 资源交付设计

### 2.1 资源目录

开发态目标路径：

```text
apps/desktop/src-tauri/resources/bin/ffprobe/windows-x64/ffprobe.exe
```

随包资源路径：

```text
bin/ffprobe/windows-x64/ffprobe.exe
```

Git 只提交：

- 下载脚本
- 版本配置
- checksum
- license 说明
- 空目录占位或说明文件

Git 不提交：

- `ffprobe.exe`
- `ffmpeg.exe`
- 下载压缩包
- 解压临时目录

### 2.2 下载脚本

新增脚本：

```text
apps/desktop/scripts/prepare-media-tools.mjs
```

职责：

1. 读取固定版本配置。
2. 检查目标 `ffprobe.exe` 是否存在。
3. 计算 checksum。
4. checksum 匹配时跳过下载。
5. checksum 缺失或不匹配时下载压缩包到临时目录。
6. 解压出 `ffprobe.exe`。
7. 校验 checksum。
8. 写入资源目录。
9. 输出中文结果。

脚本失败时必须退出非 0 状态码，并清理临时文件。

### 2.3 package 命令

新增命令：

```json
{
  "prepare:media-tools": "node scripts/prepare-media-tools.mjs"
}
```

后续打包命令可以显式串联：

```text
npm run prepare:media-tools && npm run tauri build
```

本阶段不强制修改所有 build 命令，避免开发态每次前端构建都触发媒体工具准备。

## 3. Runtime 路径发现设计

### 3.1 新增服务

新增：

```text
apps/py-runtime/src/services/media_tool_resolver.py
```

职责：

- 解析 FFprobe 可执行文件路径。
- 标记路径来源。
- 提供版本探测。
- 将异常记录到统一日志。

### 3.2 查找顺序

FFprobe 查找顺序固定为：

1. 显式配置：`TK_OPS_FFPROBE_PATH`
2. 内置资源路径：
   - `TK_OPS_RESOURCE_DIR/bin/ffprobe/windows-x64/ffprobe.exe`
   - Runtime 当前目录向上推断的 `apps/desktop/src-tauri/resources/bin/ffprobe/windows-x64/ffprobe.exe`
3. 系统 PATH：`shutil.which("ffprobe")`
4. 未找到时交给 MP4 基础降级解析

### 3.3 路径结果模型

Runtime 内部模型：

```python
@dataclass(frozen=True, slots=True)
class MediaToolResolution:
    status: str
    tool: str
    path: str | None
    source: str
    version: str | None
    error_code: str | None
    error_message: str | None
```

字段约定：

- `status`: `ready | unavailable | incompatible`
- `source`: `configured | bundled | path | fallback`
- `error_code`: 使用 `media.ffprobe_unavailable`、`media.ffprobe_incompatible` 等稳定错误码

## 4. FFprobe 服务设计

`apps/py-runtime/src/services/ffprobe.py` 不再直接管理所有路径规则，只依赖 `media_tool_resolver.py` 获取命令。

行为：

- `get_ffprobe_availability()` 返回实际路径、来源、版本与错误信息。
- `probe_video()` 优先调用真实 FFprobe。
- FFprobe 不可用、执行失败、返回异常 JSON 时，继续尝试 MP4 基础降级解析。
- 降级解析只接受识别到 MP4/MOV 容器签名的文件，避免伪成功。

## 5. 检测中心接口设计

### 5.1 接口

扩展现有设置接口：

```text
GET /api/settings/diagnostics
```

返回仍走统一 JSON 信封。

### 5.2 DTO

Runtime 返回：

```json
{
  "checkedAt": "2026-04-25T20:00:00Z",
  "overallStatus": "warning",
  "items": [
    {
      "id": "media.ffprobe",
      "label": "FFprobe 媒体探针",
      "group": "媒体工具",
      "status": "ready",
      "summary": "已检测到内置 FFprobe。",
      "impact": "可解析视频时长、分辨率、编码格式等元数据。",
      "detail": "来源：bundled；路径：bin/ffprobe/windows-x64/ffprobe.exe；版本：ffprobe version ...",
      "actionLabel": "重新检测",
      "actionTarget": "settings.diagnostics.rescan"
    }
  ]
}
```

字段说明：

- `overallStatus`: `ready | warning | failed`
- `items[].status`: `ready | warning | failed`
- `items[].group`: 用于 UI 分组
- `items[].actionTarget`: 前端只作为动作标识，不直接执行业务规则

### 5.3 检测项

首期固定检测项：

| ID | 名称 | 失败影响 |
| --- | --- | --- |
| `license.status` | 许可证 | 授权受限，核心功能可能不可用 |
| `runtime.health` | Runtime | 前端无法调用本地服务 |
| `database.sqlite` | 数据库 | 项目、任务、配置无法持久化 |
| `directory.workspace` | 工作目录 | 项目资产无法落盘 |
| `directory.cache` | 缓存目录 | 生成和预览缓存不可用 |
| `directory.logs` | 日志目录 | 异常无法追踪 |
| `media.ffprobe` | FFprobe 媒体探针 | 视频元数据解析降级或不可用 |
| `ai.provider` | AI Provider | AI 生成、改写、分镜等能力不可用 |
| `websocket.task_bus` | WebSocket 任务通道 | 长任务进度无法实时同步 |

### 5.4 状态汇总规则

- 任一检测项 `failed`：`overallStatus = failed`
- 无 `failed` 但存在 `warning`：`overallStatus = warning`
- 全部 `ready`：`overallStatus = ready`

## 6. 前端 UI 设计

### 6.1 位置

落在：

```text
apps/desktop/src/pages/settings/components/SettingsDiagnosticsCenter.vue
```

并集成到：

```text
apps/desktop/src/pages/settings/AISystemSettingsPage.vue
```

不新增路由，不新增 Sidebar 项。

### 6.2 交互

页面提供：

- “一键检测”主按钮
- 上次检测时间
- 总体状态卡
- 按组展示检测项
- 每项展示状态、影响范围、详情和动作建议
- 检测失败时显示重试入口

状态要求：

- 加载中：展示检测中状态与禁用按钮
- 空状态：提示尚未执行检测
- 正常：展示全部 ready
- 警告：展示 warning 项和修复建议
- 失败：展示 failed 项和重试入口

### 6.3 前端类型

新增或扩展：

```ts
export type RuntimeDiagnosticStatus = "ready" | "warning" | "failed";

export type RuntimeDiagnosticItem = {
  id: string;
  label: string;
  group: string;
  status: RuntimeDiagnosticStatus;
  summary: string;
  impact: string;
  detail: string | null;
  actionLabel: string | null;
  actionTarget: string | null;
};

export type RuntimeDiagnosticsReport = {
  checkedAt: string;
  overallStatus: RuntimeDiagnosticStatus;
  items: RuntimeDiagnosticItem[];
};
```

## 7. 错误与日志

- 媒体工具下载脚本输出中文错误，不吞异常。
- Runtime 检测服务捕获每个检测项异常，并将单项标记为 `failed`，不让一个检测项拖垮整份报告。
- 所有 Runtime 异常使用 `log.exception(...)`。
- 前端接口失败展示中文错误，不静默失败。

## 8. 测试设计

### 8.1 Runtime 测试

新增：

```text
tests/runtime/test_media_tool_resolver.py
tests/runtime/test_settings_diagnostics.py
```

覆盖：

- 显式配置路径优先。
- 内置资源路径次优先。
- PATH 路径可用。
- 未找到时返回 unavailable。
- 检测报告能汇总 warning / failed。
- 单项检测异常不会导致接口整体失败。

### 8.2 契约测试

新增或扩展：

```text
tests/contracts/test_settings_diagnostics_api.py
```

覆盖：

- `/api/settings/diagnostics` 返回统一信封。
- `items` 字段存在且字段名与前端类型一致。
- 错误码和状态枚举稳定。

### 8.3 前端测试

新增或扩展：

```text
apps/desktop/tests/ai-system-settings.spec.ts
```

覆盖：

- 设置页展示检测中心。
- 点击“一键检测”调用 Runtime。
- 检测中禁用按钮。
- warning / failed 项显示修复建议。

### 8.4 构建脚本测试

首期用脚本自检覆盖：

- 已存在且 checksum 正确时跳过下载。
- checksum 错误时失败。
- 下载源不可用时失败并清理临时文件。

## 9. 验收标准

- `ffprobe.exe` 不进入 Git。
- `npm --prefix apps/desktop run prepare:media-tools` 可按需准备资源。
- FFprobe 可用性返回来源：`configured | bundled | path | fallback`。
- 视频拆解元数据优先使用真实 FFprobe。
- 设置中心能一键检测关键配置。
- 前端和 Runtime 测试通过。
- `npm --prefix apps/desktop run build` 通过。
