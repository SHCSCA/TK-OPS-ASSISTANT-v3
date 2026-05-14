# 全局页面布局分型设计

> 对应计划：`docs/superpowers/plans/2026-05-13-global-layout-taxonomy.md`

## 目标

本次改造解决核心工作台页面在宽屏窗口中被内容页最大宽度限制的问题。当前壳层已经能提供全宽内容区，但 M05 AI 剪辑工作台仍复用普通 `.page-container`，导致页面在大窗口居中、左右留白，并且剪辑区域无法像工作台一样铺满。

设计目标不是把所有页面都拉满，而是建立全局页面布局分型：工作流页面减少宽屏留白，管理页使用全宽对象列表 + 详情栅格，设置页放宽外框但保留内部列约束。M05 使用独立全高工作台根容器；其他 `editor / workspace / queue / management` 页面由壳层按 `pageType` 放宽页面容器。

## 布局分型

页面按使用场景分成五类：

| 类型 | 页面示例 | 宽度策略 | 滚动策略 |
| --- | --- | --- | --- |
| 内容页 | 创作总览 | 放宽到 `min(1680px, 100%)` | 页面自然纵向滚动 |
| 编辑流 | 脚本、分镜、配音、字幕 | 全宽，面板自行控制列宽 | 页面或局部滚动 |
| 管理页 | 账号管理、设备管理 | 全宽内容宿主，左侧对象列表 320-420px，右侧详情自适应 | 页面或局部滚动 |
| 设置页 | AI 与系统设置 | 放宽到 `min(1680px, 100%)`，内部设置分区继续控宽 | 页面自然滚动 |
| 队列页 | 自动化、渲染、发布 | 全宽，列表优先 | 列表区域滚动 |
| 工作台页 | M05、视频拆解、资产、复盘 | 全宽，M05 额外全高工作台 | 页面内部滚动，不让内容宿主横向滚动 |

`--density-page-max-width` 继续作为普通页面令牌保留。壳层只按 `pageType` 覆盖通用 `.page-container` 的 `max-width`，不修改令牌本身；M05 额外使用独立根类，避免全高工作台规则影响其他页面。

## 壳层设计

`AppShell` 已经把当前路由类型写入 `data-page-type`。本轮使用该入口下发页面容器宽度策略：

```css
.app-shell[data-page-type="dashboard"] .app-shell__content :deep(.page-container),
.app-shell[data-page-type="settings"] .app-shell__content :deep(.settings-console) {
  max-width: min(1680px, 100%);
}

.app-shell[data-page-type="editor"] .app-shell__content :deep(.page-container),
.app-shell[data-page-type="workspace"] .app-shell__content :deep(.page-container),
.app-shell[data-page-type="queue"] .app-shell__content :deep(.page-container),
.app-shell[data-page-type="management"] .app-shell__content :deep(.page-container) {
  margin-left: 0;
  margin-right: 0;
  max-width: none;
}
```

当前 `pageType="workspace"` 不只覆盖 M05，还覆盖视频拆解、资产中心和复盘页。为了避免全局误伤，本轮不在壳层统一增加 `overflow: hidden` 规则。

M05 的全高滚动和铺满行为全部下沉到 `editing-workspace-page` 页面根容器。后续如果要在壳层增加更细粒度控制，应先把路由类型拆成 `workspace` 与 `workbench`，再迁移 M07/M08。

## M05 页面设计

M05 根容器从：

```vue
<div class="page-container h-full">
```

改为：

```vue
<div class="editing-workspace-page h-full">
```

`editing-workspace-page` 负责：

- 宽度吃满内容宿主。
- 高度吃满内容宿主。
- 顶部工具栏占据自然高度。
- 主编辑区使用剩余高度。
- 隐藏外层横向溢出。
- 通过容器查询按实际内容宽度折叠面板。

## M05 工作区结构

页面保持当前真实数据链路和模块边界：

- `AIEditingWorkspacePage.vue`：页面装配、按钮、状态提示、Detail Context。
- `WorkspaceAssetRail.vue`：素材来源和受管轨道入口。
- `WorkspacePreviewStage.vue`：9:16 手机预览。
- `WorkspaceInspector.vue`：基础属性和预检状态。
- `WorkspaceTimeline.vue`：多轨时间线。

视觉结构调整为：

```text
工作台工具栏：标题 / 当前项目 / 当前选择 / 汇入 / 预检 / 操作按钮
主工作区：
  素材池 | 9:16 播放器 | 基础属性
  基础工具条
  时间线
```

宽屏下三栏铺满可用区域；中屏下基础属性下移；窄屏下素材池、播放器、属性和时间线顺序堆叠。

## 响应式规则

工作台以容器宽度为准，而不是浏览器视口宽度：

- 大于 1180px：三栏布局，素材池约 240-320px，播放器占剩余空间，属性栏约 260-340px。
- 小于等于 1180px：两栏布局，属性栏占整行。
- 小于等于 860px：单列布局，工具栏动作换行。

任何断点都必须满足：

- 根容器 `min-width: 0`。
- 面板容器 `min-width: 0`。
- 外层不产生横向滚动。
- 9:16 预览比例保持稳定。

## 风险控制

本轮不改这些内容：

- 不改全局 `.page-container` 默认样式。
- 不改 `--density-page-max-width`。
- 不把 M07/M08 一次性迁移，避免多个页面同时变形。
- 不改变 Runtime API 和数据契约。
- 不改变普通页面的内容密度。

普通页面保护：

- 创作总览继续使用 `.page-container`。
- AI 设置只放宽根容器，不取消设置页内部列约束。
- 账号、设备进入 `management` 分型，使用统一对象列表 + 详情栅格。
- 自动化、渲染、发布继续按队列页策略由壳层放宽，不新增页面级特例。

## 测试设计

新增 `workspace-layout-contract.spec.ts`：

- 读取 M05 Vue 源码，断言根容器使用 `editing-workspace-page`，不再使用 `page-container`。
- 读取 M05 CSS，断言工作台根容器全宽、全高、`overflow: hidden`、`container-name: editing-workspace`。
- 读取 M05 CSS，断言三栏、两栏、单列断点存在。
- 读取 `AppShell.vue`，断言壳层仍提供 `data-page-type`，并按 `dashboard / editor / workspace / queue / management / settings` 定义宽度策略，但不对所有 `workspace` 页面统一隐藏滚动。
- 读取 `route-manifest.ts`，断言账号和设备为 `management`，AI 设置为 `settings`。
- 读取账号、设备、AI 设置源码，断言管理页栅格和设置页 1680px 根容器策略。

更新 `ai-editing-workspace-page.spec.ts`：

- 页面加载后能找到 `.editing-workspace-page`。
- 页面不再暴露 `.page-container` 作为 M05 根容器。
- 9:16 预览仍存在。

更新 `page-responsive-layout-contract.spec.ts`：

- 把 M05 的旧 `.page-container` 断言改为新工作台根断言。

## 验证

实现后需要运行：

```powershell
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts workspace-layout-contract.spec.ts page-responsive-layout-contract.spec.ts shell-layout-contract.spec.ts
```

再运行：

```powershell
npm --prefix apps/desktop run build
```

最后做浏览器级检查：

- 宽屏下 M05 不再居中留大空白。
- 紧凑窗口下 M05 不产生外层横向滚动。
- 9:16 播放器比例不变。
- 创作总览、AI 设置页仍保持原有内容页宽度。

## 自查

- 设计没有新增页面，没有改变产品 16 页范围。
- 全局布局分型使用现有 `pageType`，符合路由真源。
- M05 使用独立根类，避免误伤其他页面。
- 样式继续使用设计令牌和容器查询。
- 测试覆盖工作台页和普通页两类布局。
