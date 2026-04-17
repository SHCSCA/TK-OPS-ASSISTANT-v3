# TK-OPS 前端 UI 全量重构与 Runtime 接线 Design Spec

> 计划来源：`docs/superpowers/plans/2026-04-17-frontend-ui-full-refactor.md`
> 接口真源：`docs/RUNTIME-API-CALLS.md`
> 状态：Implemented and verified on 2026-04-17

## 1. 设计目标

本轮目标是把 `apps/desktop` 从当前“部分页面已接线、但共享视觉层仍未统一”的状态，重构为符合 `docs/UI-BLUEPRINT-2026-04-17.md` 的桌面工作台。

必须同时满足三条硬约束：

1. 视觉统一：共享 tokens、AppShell 坐标、组件五态、页面层次与蓝图一致。
2. 数据真实：页面只消费既有 Runtime 契约，空态和 `blocked` 态必须如实表达，不制造假数据。
3. 边界清晰：前端只负责 UI 与前端 API 接线，不越界到 Runtime 改造。

## 2. 共享层设计

### 2.1 Design Tokens

- 采用 `styles/tokens/` 拆分颜色、字体、间距、圆角、阴影、动效与层级。
- `:root` 为 Light，`[data-theme="dark"]` 为 Dark。
- 支持 `prefers-reduced-motion: reduce`，所有 B 区动效降级为即时状态切换。
- 现有 `tokens.css` 迁移为聚合入口，不再继续承载全部变量。

### 2.2 AppShell

- Title Bar 高度固定 48px，Sidebar 展开 280px / 折叠 64px，Status Bar 高度 28px。
- Detail Panel 支持桌面宽屏固定侧栏和紧凑窗口抽屉化。
- Shell 状态统一进入 `shell-ui` store，页面不再各自维护主题、侧栏和细节面板开关。

### 2.3 UI Kit

- 提供 Button、Input、Card、Chip、Progress、Tab、Dropdown 基础组件。
- 五态至少覆盖默认、hover、active、disabled、focus-visible。
- 页面只做业务组合，不重复实现基础控件外观。

## 3. 页面设计

### 3.1 分组原则

- 页面按四组并行推进，写集不重叠。
- 每页继续遵守 `page / composable / helpers / types / styles` 分层。
- 共享层冻结后，页面组不得再改公共样式接口。

### 3.2 数据约束

- 页面只通过 Pinia store 消费 Runtime。
- 已有 store 继续沿用；缺少前端封装但接口已存在时，仅补前端 `runtime-client.ts` 与 store，不补后端。
- 对未接通后端的细项，使用中文空态、禁用态或 `blocked` 态，不伪造完成数据。

### 3.3 状态矩阵

- 所有页面至少要覆盖 `loading / empty / ready / error`。
- M05、M07、M08、M16 等异步或配置型页面额外覆盖 `saving / blocked / checking / disabled`。
- 错误信息必须是中文、就近展示、可恢复。

## 4. 具体页面要求

### 4.1 创作前置组

- `setup`：首启向导采用蓝图中的仪式化 B 区，但动效必须可降级。
- `dashboard`：Hero、最近项目、健康面板与异常卡片按蓝图重排。
- `scripts`、`storyboards`：页面结构从单块内容升级为创作工作区结构，维持真实 store 数据来源。

### 4.2 创作核心组

- `workspace`：保持真实时间线草稿与 AI `blocked` 语义，不回退成静态假轨。
- `video`：继续消费视频导入与任务状态，不伪造拆解结果。
- `voice`、`subtitles`：保持 `blocked` 语义与真实轨道版本列表。

### 4.3 资源与执行上下文组

- `assets`、`accounts`、`devices`：强调资源浏览、绑定关系和健康状态。
- 不能为了视觉完整增加假统计卡或假运行数据。

### 4.4 执行链路与设置组

- `automation`、`publishing`、`renders`、`review`：表现任务流、计划流和结果流。
- `settings`：采用状态总览条 + 左侧分区 + 中央编辑区 + 右侧诊断区的设置工作台结构。

## 5. 测试与验收

- 子代理只补测试，不做多轮回归。
- 主代理在所有实现合并后统一执行一轮：
  - `npm --prefix apps/desktop run test`
  - `npm --prefix apps/desktop run build`
- 验收重点：
  - AppShell、首启、Dashboard、Workspace、Settings 五个关键入口。
  - Light / Dark 双主题。
  - 桌面宽屏与紧凑窗口无明显溢出、错位或静默失败。

## 6. 不做的事

- 不修改 Python Runtime。
- 不调整 `docs/RUNTIME-API-CALLS.md` 的后端接口语义。
- 不用假数据补齐尚未实现的后端能力。
- 不引入重型动效依赖。

## 7. 实施验收记录

### 7.1 实际落地结果

- 共享层按母版重建为统一壳层：`topbar / sidebar / content / detail-panel / status-bar` 已统一到 `AppShell` 与 `shell-ui`。
- `apps/desktop/src/components/ui/` 已补齐本轮基础组件，页面层改为消费统一 UI Kit 与全局样式令牌。
- `workspace` 作为中枢页已按母版重写骨架，并把 Detail Panel 机制回流为全局上下文容器。
- 16 个正式页面均已切回真实 store / Runtime 数据路径；接口未落地处使用中文空态、禁用态或 `blocked` 态表达。

### 7.2 验证结果

- `npm --prefix apps/desktop run test`
  - 结果：通过
  - 摘要：28 个测试文件，83 项测试全部通过。
- `npm --prefix apps/desktop run build`
  - 结果：通过
  - 摘要：Vite 构建完成；存在 1 条运行时字体资源提示，不阻塞产物生成。

### 7.3 结论

- 本 spec 覆盖的前端 0-1 重构范围已落地。
- 本轮验收结论为 `pass`，未发现阻塞交付的 P0 / P1 问题。
