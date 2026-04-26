# 2026-04-25 脚本策划工作台与 Markdown 预览计划

## 背景

- 当前脚本正文来自 AI，主体是 Markdown 格式。
- 策划工作台需要从单一“主题/改写要求”升级为短视频脚本策划字段模板。
- 脚本工作面需要提供 Markdown 原文和预览双模式，并优先使用成熟 Markdown 解析能力。
- 左侧结构锚点与分镜规划中心仍需基于同一份正文建立结构导航。

## 目标

- 策划工作台提供视频主题、产品/服务、目标用户、视频目的、视频时长、账号定位、视频风格、拍摄条件、语言要求、禁止内容等字段。
- 将策划字段组合为统一脚本生成/改写提示词，继续复用现有 Runtime 脚本接口。
- 脚本工作面提供 Markdown 预览与原文编辑双模式。
- 预览层集成 `markdown-it`，保留代码围栏清洗和安全配置。
- 让左侧结构锚点和分镜规划中心复用同一份清洗后的正文，保证结构映射一致。

## 文件地图

- `apps/desktop/src/pages/scripts/ScriptTopicCenterPage.vue`
- `apps/desktop/src/pages/storyboards/StoryboardPlanningCenterPage.vue`
- `apps/desktop/src/pages/scripts/` 下新增 markdown / planning / helpers / components / types
- `apps/desktop/tests/script-topic-center.spec.ts`
- `apps/desktop/tests/script-planning-brief.spec.ts`
- `apps/desktop/tests/script-markdown-preview.spec.ts`
- `apps/desktop/tests/storyboard-planning-center.spec.ts`
- `apps/desktop/tests/script-segment-helpers.spec.ts`
- `apps/desktop/tests/page-responsive-layout-contract.spec.ts`
- `apps/desktop/package.json`
- `apps/desktop/package-lock.json`

## 分阶段

### 阶段 1：字段与预览规则测试

- 先定义策划字段模板、提示词组合和 Markdown 预览规则。
- 补测试覆盖：
  - 策划字段完整展示；
  - 生成脚本请求包含结构化策划字段；
  - 忽略外围代码围栏；
  - Markdown 表格渲染为真实表格；
  - 脚本页保留原文编辑和预览切换；
  - 左侧锚点与分镜页使用同一规则；
  - 工作面容器承担纵向滚动。

### 阶段 2：页面收口

- 抽出共享 helper / types。
- 策划工作台改为字段化输入区。
- 生成与改写动作使用统一策划提示词。
- 脚本工作面接入 `markdown-it` 预览组件。
- 左侧结构锚点与分镜页共用同一份清洗后的正文。
- 保留保存链路，正文继续以原始 Markdown 字符串写回。

### 阶段 3：回归验证

- 跑脚本页相关测试。
- 跑分镜页相关测试。
- 跑布局契约与构建回归。

## 边界与回退点

- 不改 Runtime 脚本接口。
- 不引入富文本编辑器，只集成 Markdown 解析/预览能力。
- 不把策划字段持久化为新后端模型，本阶段只用于生成/改写提示词。
