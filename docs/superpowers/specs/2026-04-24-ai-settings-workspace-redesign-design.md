# AI 与系统设置工作区改造设计说明

> 对应计划：`docs/superpowers/plans/2026-04-24-ai-settings-workspace-redesign.md`  
> 设计状态：用户已确认 V1 设计稿。

## 1. Visual thesis

AI 与系统设置应像一个本地优先的配置工作台：克制、密度高、路径和 Provider 状态可信，所有辅助诊断都收敛到右侧上下文，而不是占用主工作区。

## 2. Primary workspace

页面固定为三层：

```text
左侧工作分区：系统总线 / Provider 与模型 / 能力矩阵
中央工作区：当前分区的主要编辑和列表
右侧 Inspector：当前路径、Provider 或能力的细节编辑
```

右上角 Shell Detail Panel 保留为系统级上下文容器，只承载诊断事件、系统边界、当前焦点和错误恢复，不再与主工作区重复。

## 3. 系统目录选择

`pickDirectoryPath(currentValue)` 的行为：

- 使用 `import("@tauri-apps/plugin-dialog")`，让 Vite 正常打包 Tauri dialog 插件。
- 调用 `open({ directory: true, multiple: false, defaultPath })`。
- 用户取消选择时返回空字符串，不修改当前值。
- 插件不可用或调用失败时抛出中文错误：`当前环境无法打开系统目录选择器，请在 TK-OPS 桌面应用中重试。`
- 禁止使用 `window.prompt`。

页面处理：

- `handlePickDirectory()` 捕获错误并写入 `pageBanner`。
- 成功选择目录后只更新表单草稿，仍需底部保存条提交到配置总线。

## 4. 诊断收敛

删除页面内“诊断工作台”分区：

- `SettingsSectionRail` 不再提供 diagnostics 项。
- `AISystemSettingsPage.vue` 不再渲染 `currentSection === "diagnostics"` 分支。
- 路由 query 如果带 `section=diagnostics`，自动落回 `system`，并打开右侧 Detail Panel。

右侧 Detail Panel 上下文：

- 运行态：Runtime、授权、配置、最近同步。
- 系统边界：数据库、缓存目录、日志目录、Provider / 能力。
- 当前焦点：当前分区、选中 Provider、连接状态、检查结果。
- 异常：只在有错误时出现，提供可读中文信息。

## 5. 系统总线布局

系统总线主区分为：

- 运行模式与默认 AI：运行模式、默认 Provider、默认模型、默认配音、字幕模式。
- 本地路径：工作区根目录、缓存目录、导出目录，每行显示路径、状态和“选择”按钮。
- 日志与缓存：日志级别、日志目录打开入口、缓存清理入口。

设计约束：

- 路径行允许长路径换行或中部省略，不撑破页面。
- 选择按钮固定宽度，不因路径长度位移。
- 缓存清理继续使用明确确认，后续真实 Runtime 接口再接入。

## 6. Provider 与模型布局

Provider 页面分为三列：

- Provider 列表：展示注册表 Provider、状态和能力数量。
- 模型目录：展示当前 Provider 的模型、能力类型、默认用途和健康检查模型。
- 凭据 Inspector：API Key、Base URL、保存凭据、连接检查和最近结果。

交互：

- 点击 Provider 列表项切换当前 Provider。
- 刷新模型目录只影响当前 Provider。
- 连接检查成功或失败后打开右侧 Detail Panel，主区 Inspector 同步显示结果。

## 7. 能力矩阵布局

能力页面分为三列：

- 能力列表：能力名称、能力 ID、启用状态、绑定 Provider / 模型。
- 绑定预览：当前能力的 Provider、模型、可选数量和角色摘要。
- 策略 Inspector：Provider、模型、Agent 角色、系统提示词、用户提示词模板。

交互：

- 点击能力列表项切换当前能力。
- 启用状态可直接在列表切换。
- 所有策略编辑仍通过底部保存条一次性提交。

## 8. 状态覆盖

- Loading：保留配置总线与能力配置加载状态。
- Empty：Provider 注册表、模型目录、能力配置为空时显示中性空态。
- Ready：三块布局展示真实 Runtime 数据。
- Busy：保存设置、保存能力、刷新模型和连接检查期间禁用相关按钮。
- Error：页面 banner + 右侧 Detail Panel 异常区。
- Disabled：Runtime 未初始化或当前 Provider 无模型时，按钮保留禁用原因。

## 9. 响应式

- 宽屏：左侧分区 220px，中间主工作区最小 0，右侧 Inspector 280-340px。
- 中等宽度：Provider / 能力页的三列降级为“列表 + Inspector”两列，模型目录或预览放到中间下方。
- 紧凑窗口：三块页面降级为单列，Inspector 跟随当前内容下方，不遮挡主工作区。

## 10. 验收

- 页面内不再出现浏览器 prompt。
- 页面内不再出现“诊断工作台”作为可选分区。
- Provider 与模型不再是上下堆叠的大卡片，而是对象切换 + 模型目录 + 凭据 Inspector。
- 能力矩阵不再出现大面积空白，当前能力编辑区与列表保持关联。
- 测试和构建通过。
