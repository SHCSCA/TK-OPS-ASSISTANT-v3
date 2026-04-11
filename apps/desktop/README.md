# Desktop Creative Chain Baseline

`apps/desktop` 是 TK-OPS 的桌面端入口，技术栈固定为 `Tauri 2 + Vue 3 + TypeScript + Vite`。

## 当前职责

- 提供最小可运行 App Shell
- 固定 16 个正式路由和导航分组
- 提供 `ProjectStore` 作为当前项目唯一真源
- 通过 `ConfigBusStore` 统一管理 Runtime：
  - 健康状态
  - 设置文档
  - 诊断信息
  - 保存/加载状态
  - 最近同步时间
- 通过 `LicenseStore` 统一管理许可证：
  - 授权状态
  - 受限模式
  - 本机 `machineId`
  - 激活请求
- 通过 `AICapabilityStore` 统一管理能力级 AI 配置
- 通过 `ScriptStudioStore` 和 `StoryboardStore` 管理项目级创作文档
- 将 `setup_license_wizard` 落地为首启向导页
- 将 `creator_dashboard` 落地为真实项目入口页
- 将 `ai_system_settings` 落地为真实配置页与 AI 能力中心
- 将 `script_topic_center` 落地为真实脚本页
- 将 `storyboard_planning_center` 落地为真实分镜页

## 当前页面能力

- `AppShell.vue`
  - Title Bar 显示 Runtime、配置、许可证和当前项目状态
  - Status Bar 显示最近同步时间或首启状态
  - Wizard 页面下隐藏 Sidebar 与 Detail Panel
  - Detail Panel 在设置页下显示 diagnostics、最近错误摘要和许可证摘要
  - 需要项目上下文的页面通过 Router guard 重定向到 Dashboard
- `CreatorDashboardPage.vue`
  - 展示最近项目与当前项目状态
  - 创建项目并恢复被守卫拦截的目标路由
- `ScriptTopicCenterPage.vue`
  - 读取项目级脚本文档
  - 支持手工保存、AI 生成、AI 改写和版本列表
- `StoryboardPlanningCenterPage.vue`
  - 读取项目级分镜文档
  - 支持 AI 生成分镜和手工保存场景卡片
- `SetupLicenseWizardPage.vue`
  - 输入激活码并触发许可证激活
  - 写入首个系统配置文档
  - 未激活时拦截受保护路由并保留回跳目标
- `AISystemSettingsPage.vue`
  - 读取并保存四段配置：
    - `runtime`
    - `paths`
    - `logging`
    - `ai`
  - 管理 7 个 AI capability 的 provider/model/prompt 配置
  - 显示 provider 密钥状态与支持能力
  - 只能通过统一 store 访问 Runtime，不允许页面直接散落调用配置接口

## 本地运行

- 安装依赖：`npm install`
- 启动开发服务器：`npm --prefix apps/desktop run dev`
- 运行测试：`npm --prefix apps/desktop run test`
- 生产构建：`npm --prefix apps/desktop run build`

## 目录说明

- `src/app/`
  - Router 真源与 Runtime API 客户端
- `src/layouts/`
  - App Shell
- `src/pages/`
  - 16 个页面根组件
- `src/stores/`
  - Pinia 全局状态，包括 `ConfigBusStore`、`LicenseStore`、`ProjectStore`、`AICapabilityStore`、`ScriptStudioStore`、`StoryboardStore`
- `src/types/`
  - UI DTO 与 Runtime 协议类型
- `src/styles/`
  - 全局样式与设计令牌
- `src-tauri/`
  - Tauri 原生壳配置

## 当前边界

- 除 Dashboard、许可证向导、AI 设置、脚本页、分镜页外，其余页面仍为真实空态占位
- 本轮不覆盖 Tauri 原生打包验证
- 不包含时间线、渲染队列、发布队列和 WebSocket 实时推送
- 当前许可证激活为本地占位实现，不接远端授权服务
