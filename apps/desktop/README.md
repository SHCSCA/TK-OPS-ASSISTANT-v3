# Desktop Skeleton

`apps/desktop` 是 TK-OPS 的桌面壳入口，技术主线固定为 `Tauri 2 + Vue 3 + TypeScript + Vite`。

## 当前职责

- 预留 App Shell、16 个正式路由、状态管理和设计系统落点。
- 固定 `src/` 与 `src-tauri/` 的目录边界。
- 为下一轮“可运行桌面壳”提供入口配置位置。

## 本轮未做

- 未创建实际页面组件。
- 未实现真实路由表。
- 未接入 UI 框架代码或运行链路。

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

