# AI 与系统设置工作区改造计划

> 计划状态：已由用户在 2026-04-24 确认 V1 设计稿。  
> 对应设计稿：`docs/design-drafts/2026-04-24-ai-settings-layout-redesign-v1.svg`

## 1. 目标

围绕 AI 与系统设置页的三个体验问题做一次收敛式改造：

1. 目录选择必须调用系统目录选择器，不再回退到浏览器 `prompt`。
2. 诊断工作台不再与系统总线、Provider 状态和右侧抽屉重复。
3. 系统总线、Provider 与模型、能力矩阵改成“左侧分区 + 中央工作区 + 当前对象 Inspector”的一致布局。

## 2. 边界

- 不新增正式页面，不改变 16 页页面树。
- 不新增假状态、假成功率或假 Provider 数据。
- 不绕过 Runtime 配置总线；保存仍走 `/api/settings/config` 和 `/api/settings/ai-capabilities`。
- 不引入新 UI 依赖或动效库。
- 不把右侧抽屉做成覆盖主工作区的常驻浮层。

## 3. 文件地图

- 修改：`apps/desktop/src/pages/settings/ai-system-settings-page-helpers.ts`
- 修改：`apps/desktop/src/pages/settings/AISystemSettingsPage.vue`
- 修改：`apps/desktop/src/pages/settings/AISystemSettingsPage.css`
- 修改：`apps/desktop/src/modules/settings/components/SettingsSystemFormPanel.vue`
- 修改：`apps/desktop/src/modules/settings/components/ProviderCatalogPanel.vue`
- 修改：`apps/desktop/src/modules/settings/components/AICapabilityMatrix.vue`
- 修改：`apps/desktop/src/modules/settings/components/AICapabilityInspector.vue`
- 测试：`apps/desktop/tests/ai-system-settings.spec.ts`
- 测试：`apps/desktop/tests/ai-settings-layout-contract.spec.ts`

## 4. 阶段

### 阶段一：系统目录选择

- 修复 `@tauri-apps/plugin-dialog` 的导入方式。
- 删除 `window.prompt` 兜底。
- 非 Tauri 浏览器预览环境给出中文错误反馈，提示需要在桌面壳中选择目录。
- 测试覆盖：源码不再包含 `window.prompt`，目录选择失败时页面显示可见错误。

### 阶段二：诊断收敛

- 左侧工作分区移除“诊断工作台”。
- 主区不再展示诊断页面。
- 右上角 Detail Panel 继续承载系统边界、当前焦点、异常信息和导出诊断入口。
- 测试覆盖：页面分区不再包含 `data-section="diagnostics"`，源码不再包含“诊断工作台”主区文案。

### 阶段三：三块设置页布局

- 系统总线：路径、运行模式、默认 AI、日志策略按编辑任务分组，路径行使用系统 picker 操作。
- Provider 与模型：左侧 Provider 列表，中间模型目录，右侧凭据与连接 Inspector。
- 能力矩阵：左侧能力列表，中间绑定预览，右侧策略 Inspector。
- 所有布局使用 CSS variables 和容器查询，宽屏和紧凑窗口都优先保护主工作区。

## 5. 验证

- `npm run test -- ai-system-settings.spec.ts ai-settings-layout-contract.spec.ts`
- `npm run test -- ai-system-settings.spec.ts ai-settings-layout-contract.spec.ts shell-layout-contract.spec.ts app-shell.spec.ts`
- `npm run build`
- `git diff --check`
- 浏览器/桌面预览：确认不再出现 prompt，设置页不再出现重复诊断工作台。

## 6. 回退点

- 如果系统 picker 在 Tauri 环境异常，优先回退目录选择 helper，不回退设置页整体布局。
- 如果三栏设置页影响紧凑窗口可用性，先回退对应组件 CSS，不影响诊断收敛与目录 picker 修复。
