# Desktop M0

`apps/desktop` 是 TK-OPS 的桌面壳入口，技术主线固定为 `Tauri 2 + Vue 3 + TypeScript + Vite`。

## 当前职责

- 提供最小可运行 App Shell、16 个正式路由占位页和统一导航分组。
- 接入 Pinia、Vue Router、基础设计令牌和 Runtime 健康状态显示。
- 固定 `src/` 与 `src-tauri/` 的目录边界。
- 为下一轮业务页面落地提供稳定壳层和状态入口。

## 本轮未做

- 未实现业务域页面逻辑与真实项目数据。
- 未接入许可证、脚本、分镜、时间线和发布等核心业务能力。
- 未完成 Tauri 打包链路验证。

## 本地运行

- 安装依赖：`npm install`
- 启动开发服务器：`npm --prefix apps/desktop run dev`
- 运行桌面壳测试：`npm --prefix apps/desktop run test`

## 目录说明

- `src/app/router/`
  路由真源和导航契约。
- `src/layouts/`
  App Shell 与壳层布局。
- `src/pages/`
  16 个正式页面根组件。
- `src/modules/`
  业务模块和页面内复用单元。
- `src/components/`
  通用 UI 组件。
- `src/stores/`
  Pinia 状态与全局上下文。
- `src/styles/`
  全局样式和设计令牌。
- `src/types/`
  UI 类型与 DTO 类型。
- `src-tauri/`
  Tauri 原生壳配置。

