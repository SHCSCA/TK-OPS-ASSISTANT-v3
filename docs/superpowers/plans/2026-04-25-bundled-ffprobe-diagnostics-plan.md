# 内置 FFprobe 与检测中心改造计划

## 目标

在不提交大型二进制文件的前提下，为项目提供可打包的内置 FFprobe 能力，并在 `AI 与系统设置` 页面内新增“检测中心”，支持一键检测系统运行所必须的配置与依赖。

## 背景

当前视频拆解链路依赖 FFprobe 获取视频元数据。若本机未安装 FFprobe，Runtime 已具备 MP4 基础降级解析能力，但完整媒体诊断仍会提示缺失。用户期望应用内置 FFprobe，并在配置中心集中检测系统运行必需项。

## 范围

- 前端范围：`apps/desktop`
  - 新增媒体工具准备脚本入口。
  - 更新 Tauri 资源打包配置。
  - 设置中心新增“检测中心”分区与一键检测交互。
  - Runtime Client 增加检测中心接口类型与调用方法。

- Runtime 范围：`apps/py-runtime`
  - FFprobe 路径发现改为：配置总线指定路径 -> 内置资源路径 -> 系统 PATH -> MP4 降级解析。
  - 新增系统检测服务，统一输出许可证、Runtime、数据库、目录、日志、缓存、FFprobe、AI Provider、WebSocket 等状态。
  - 保持统一 JSON 信封与中文错误反馈。

- 文档与测试范围：`docs`、`tests`
  - 补充接口契约与资源准备说明。
  - 补齐 Runtime 服务测试、契约测试、前端设置页交互测试。

## 不做

- 不把 `ffprobe.exe`、`ffmpeg.exe` 或压缩包提交到 Git。
- 不新增第 17 个页面，检测中心落在现有 `AI 与系统设置` 页面内。
- 不引入自动更新器，不在应用运行时后台静默下载媒体工具。
- 不扩大视频处理范围到完整 FFmpeg 转码流水线，本阶段只保证 FFprobe 诊断和元数据解析。

## 方案

### 1. 媒体工具获取与缓存

- 新增资源准备脚本，例如 `apps/desktop/scripts/prepare-media-tools.mjs`。
- 固定 FFprobe 来源、版本、文件名和 checksum。
- 构建前检查目标路径：
  - `apps/desktop/src-tauri/resources/bin/ffprobe/windows-x64/ffprobe.exe`
- 若文件存在且 checksum 匹配，直接复用。
- 若文件不存在或 checksum 不匹配，下载、解压、校验并写入资源目录。
- 将资源目录中的二进制文件加入 `.gitignore`，只提交脚本、版本配置和 license 说明。

### 2. Tauri 资源打包

- 更新 `apps/desktop/src-tauri/tauri.conf.json` 的 bundle resources。
- 确保打包后 FFprobe 能被 Runtime 通过稳定路径发现。
- 开发态允许从仓库资源目录读取，打包态允许从 Tauri resource 目录读取。

### 3. Runtime 工具路径发现

- 新增媒体工具解析模块，避免把路径规则堆在 `ffprobe.py`。
- 查找顺序：
  1. 配置总线或环境变量指定的 `TK_OPS_FFPROBE_PATH`
  2. Tauri 传入或 Runtime 推断的内置资源路径
  3. 系统 PATH 中的 `ffprobe`
  4. MP4 基础降级解析
- 每次诊断返回实际使用路径、来源、版本、错误码和修复建议。

### 4. 检测中心

- 在 `AI 与系统设置` 页面新增“检测中心”分区。
- 一键检测输出统一列表：
  - 许可证状态
  - Runtime 在线状态
  - 数据库可读写
  - 工作目录可读写
  - 缓存目录可读写
  - 日志目录可写
  - FFprobe 可用性
  - AI Provider 基础配置
  - WebSocket 可连接
- 每项包含：
  - `id`
  - `label`
  - `status`: `ready | warning | failed`
  - `summary`
  - `impact`
  - `detail`
  - `actionLabel`
  - `actionTarget`
- UI 必须覆盖加载中、正常、警告、失败和重试状态。

### 5. 接口契约

- 新增或扩展 `/api/settings/diagnostics`。
- 返回结构保持统一 JSON 信封。
- 不在前端硬编码检测规则，前端只渲染 Runtime 返回的检测项。

## 文件地图

- 新增：`apps/desktop/scripts/prepare-media-tools.mjs`
- 修改：`apps/desktop/package.json`
- 修改：`apps/desktop/src-tauri/tauri.conf.json`
- 新增或修改：`apps/desktop/src/pages/settings/components/SettingsDiagnosticsCenter.vue`
- 修改：`apps/desktop/src/pages/settings/AISystemSettingsPage.vue`
- 修改：`apps/desktop/src/app/runtime-client.ts`
- 修改：`apps/desktop/src/types/runtime.ts`
- 新增：`apps/py-runtime/src/services/media_tool_resolver.py`
- 修改：`apps/py-runtime/src/services/ffprobe.py`
- 修改：`apps/py-runtime/src/services/settings_service.py`
- 修改：`apps/py-runtime/src/api/routes/settings.py`
- 新增或修改：`tests/runtime/test_settings_diagnostics.py`
- 新增或修改：`tests/runtime/test_media_tool_resolver.py`
- 新增或修改：`tests/contracts/test_settings_diagnostics_api.py`
- 新增或修改：`apps/desktop/tests/ai-system-settings.spec.ts`
- 新增：`docs/media-tools.md`

## 验证方式

- Runtime：
  - FFprobe 配置路径优先级测试。
  - 内置资源路径发现测试。
  - FFprobe 不存在时降级解析仍可用测试。
  - `/api/settings/diagnostics` 契约测试。

- 前端：
  - 设置中心能展示检测中心。
  - 点击“一键检测”会调用 Runtime 接口。
  - 检测中、成功、警告、失败状态都可见。

- 构建：
  - 媒体工具准备脚本首次缺失时下载并校验。
  - 媒体工具已存在且 checksum 匹配时跳过下载。
  - `npm --prefix apps/desktop run build` 通过。

## 风险与回退

- 下载源不可用：脚本必须失败并给出中文原因，不得生成半成品工具。
- checksum 不匹配：必须删除临时文件并停止构建。
- Tauri 资源路径差异：Runtime 保留系统 PATH 和显式配置作为回退。
- 许可证风险：优先选择 LGPL 构建来源，并在文档中记录来源、版本、license。

## 阶段

1. 设计文档：固定接口结构、资源路径策略和 UI 信息结构。
2. Runtime：实现媒体工具解析与诊断服务。
3. 前端：实现设置中心检测中心。
4. 构建：实现媒体工具下载缓存与 Tauri 资源打包。
5. 验证：补齐测试、构建和文档。

## 验收标准

- 没有新增二进制大文件进入 Git。
- 新机器首次构建可以按需准备 FFprobe。
- 本机重复构建不会重复下载已校验的 FFprobe。
- 视频拆解中心能使用内置 FFprobe 获取元数据。
- 设置中心能一键检测关键运行依赖，并给出中文修复建议。
- 所有新增异常路径有日志记录和可见反馈。
