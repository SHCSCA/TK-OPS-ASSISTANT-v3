# TK-OPS UI 工程蓝图 v2026.04.17

> 本文是对 `docs/PRD.md` 与 `docs/UI-DESIGN-PRD.md` 的**工程落地补充**，不替代两者的产品真源地位。
> 冲突时的优先级：`docs/PRD.md` > `docs/UI-DESIGN-PRD.md` > 本文件。
> 本文解决的唯一问题：把"好看"和"高级手感"翻译成**精确的 CSS 坐标、五态属性表、贝塞尔曲线参数**，让任何实现者都能复刻同一视觉。

---

## 目录

- 0 · 文档元信息
- 1 · 设计策略（状态驱动视觉）
- 2 · 全量设计令牌（Design Tokens）
- 3 · 壳层坐标化布局（AppShell）
- 4 · 原子组件五态表
- 5 · 16 页逐页线框与坐标
- 6 · 状态驱动动效库（B 模式触发表）
- 7 · 前端模块化任务矩阵
- 8 · 验收清单
- 9 · React Bits / Unicorn Studio 取舍对照
- 附录 A · 实施顺序建议
- 附录 B · 文件清单

---

## 0 · 文档元信息

| 字段 | 内容 |
| --- | --- |
| 文档名称 | TK-OPS UI 工程蓝图 |
| 版本 | v2026.04.17 |
| 文档状态 | 可直接落地 |
| 维护者 | Claude（基于用户拍板的视觉策略） |
| 适用模块 | `apps/desktop` 全部 16 页 + AppShell |
| 基准参考 | Linear / Vercel（Dark）、Stripe / Figma（Light） |
| 品牌主色 | `#00BCD4`（青蓝，AI 数据流） |
| 品牌辅助色 | `#7000FF`（深紫，双色渐变科技感） |
| 字体栈 | `Inter` + `HarmonyOS Sans SC` |
| 图标栈 | `Material Symbols Outlined` |
| 动效栈 | CSS transform / opacity / background-position（禁用 JS 动画循环） |
| 目标帧率 | 60 fps（桌面）/ 30 fps 以上（紧凑窗口） |

---

## 1 · 设计策略

### 1.1 状态驱动视觉策略（核心原则）

UI 被划分为两类区域，采用完全不同的视觉权重：

**A 区 · 生产力底噪**（长期驻留）：
- 剪辑时间线、参数面板、表格、表单、列表
- 视觉特征：高对比度文字、1 px 半透明分割线、留白代替装饰、无持续动效
- 目标：阅读零压力、操作零干扰

**B 区 · 情绪张力**（状态触发）：
- 首启向导、创作总览 Hero、AI 任务启动/完成瞬间、授权成功、渲染完成
- 视觉特征：渐变流光、粒子喷溅、呼吸灯、动态背景
- 目标：在关键节点建立仪式感，任务结束后立即回归 A 区

**硬规则**：
1. B 区动效**必须有明确的生命周期**（起始/结束），禁止无限循环背景。
2. 任意页面 B 区占屏幕总面积不得超过 **30%**，剪辑工作台不得超过 **10%**。
3. 用户可在设置中一键关闭所有 B 区动效（降级到 A 区），用于低配机器或用户审美疲劳。

### 1.2 双主题基准

| 维度 | Dark 模式（Linear / Vercel 取向） | Light 模式（Stripe / Figma 取向） |
| --- | --- | --- |
| 底色基调 | 极深非纯黑（`#0A0B0F`） | 微冷浅灰非纯白（`#F7F8FA`） |
| 层级区分 | 依赖发光与极细半透明边框 | 依赖精致投影，禁用粗边框 |
| 点睛色 | 青蓝 `#00BCD4` 可发光、可流动 | 青蓝 `#0097A7` 压色版，清晰护眼 |
| 渐变使用 | AI 相关处用 青→紫 渐变带发光 | AI 相关处用淡色渐变，不带发光 |
| 阴影 | 仅用于悬浮卡片，极弱 | 主要层级区分手段 |
| 边框 | 0.5 ~ 1 px，透明度 0.06 ~ 0.12 | 几乎不用，仅输入框聚焦态 |

### 1.3 性能底线（硬约束）

1. **只允许**使用 `transform` / `opacity` / `filter` / `background-position` 驱动动画，禁止动画 `width` / `height` / `top` / `left`（会触发 layout）。
2. 长时动画必须加 `will-change`，结束立即移除。
3. 单页同时运行的动画元素 ≤ 6 个。
4. 主 AppShell 布局切换（展开/折叠侧栏、切换主题）必须在 **240 ms** 内完成，全程 60 fps。
5. 首屏 LCP 目标 < **1.2 s**（Tauri 本地资源，几乎零网络）。
6. 低配模式（`prefers-reduced-motion: reduce` 或设置关闭）下，所有 B 区动效替换为即时状态切换。

---

## 2 · 全量设计令牌

所有令牌统一通过 CSS Variables 暴露，`:root` 写 Light，`[data-theme="dark"]` 写 Dark。

### 2.1 色彩令牌

#### 2.1.1 基础色板（Neutral）

| 令牌名 | Dark | Light | 用途 |
| --- | --- | --- | --- |
| `--color-bg-canvas` | `#0A0B0F` | `#F7F8FA` | App 最底层背景 |
| `--color-bg-surface` | `#12141A` | `#FFFFFF` | 卡片/面板底色 |
| `--color-bg-elevated` | `#1A1D26` | `#FFFFFF` | 悬浮层（弹窗、下拉） |
| `--color-bg-overlay` | `rgba(10,11,15,0.72)` | `rgba(15,18,28,0.48)` | 遮罩层 |
| `--color-bg-muted` | `#16181F` | `#F0F2F5` | 次级容器 |
| `--color-bg-hover` | `rgba(255,255,255,0.04)` | `rgba(15,18,28,0.04)` | 通用 hover 底色 |
| `--color-bg-active` | `rgba(0,188,212,0.10)` | `rgba(0,151,167,0.08)` | 激活态底色 |
| `--color-border-subtle` | `rgba(255,255,255,0.06)` | `rgba(15,18,28,0.06)` | 最弱分割线 |
| `--color-border-default` | `rgba(255,255,255,0.10)` | `rgba(15,18,28,0.10)` | 常规边框 |
| `--color-border-strong` | `rgba(255,255,255,0.18)` | `rgba(15,18,28,0.16)` | 聚焦/强调边框 |

#### 2.1.2 文字色

| 令牌名 | Dark | Light | 用途 |
| --- | --- | --- | --- |
| `--color-text-primary` | `#EDEFF5` | `#0B0D14` | 主要文字（标题、正文） |
| `--color-text-secondary` | `#A8ADBA` | `#4A5166` | 次级文字（说明、元信息） |
| `--color-text-tertiary` | `#6B7183` | `#7D8497` | 辅助文字（占位、禁用） |
| `--color-text-on-brand` | `#FFFFFF` | `#FFFFFF` | 品牌色按钮上的文字 |
| `--color-text-inverse` | `#0B0D14` | `#FFFFFF` | 反色底上的文字 |

#### 2.1.3 品牌与状态色

| 令牌名 | Dark | Light | 用途 |
| --- | --- | --- | --- |
| `--color-brand-primary` | `#00BCD4` | `#0097A7` | 主品牌色（按钮、链接、激活） |
| `--color-brand-primary-hover` | `#26D0E0` | `#00ACC1` | 悬停亮化 |
| `--color-brand-primary-active` | `#00A5BC` | `#00838F` | 按下压色 |
| `--color-brand-glow` | `rgba(0,188,212,0.38)` | `rgba(0,151,167,0.22)` | 发光光晕 |
| `--color-brand-secondary` | `#7000FF` | `#5E17EB` | 辅助色（AI 渐变终点） |
| `--color-success` | `#22D39A` | `#12A670` | 成功 |
| `--color-warning` | `#F5B740` | `#D98E00` | 警告 |
| `--color-danger` | `#FF5A63` | `#D63B45` | 危险/错误 |
| `--color-info` | `#5B8CFF` | `#2E63EB` | 信息 |

#### 2.1.4 语义渐变

| 令牌名 | Dark | Light | 用途 |
| --- | --- | --- | --- |
| `--gradient-ai-primary` | `linear-gradient(135deg, #00BCD4 0%, #7000FF 100%)` | `linear-gradient(135deg, #0097A7 0%, #5E17EB 100%)` | AI 按钮、AI 进度条、Hero 点缀 |
| `--gradient-ai-subtle` | `linear-gradient(135deg, rgba(0,188,212,0.12) 0%, rgba(112,0,255,0.12) 100%)` | `linear-gradient(135deg, rgba(0,151,167,0.06) 0%, rgba(94,23,235,0.06) 100%)` | AI 区域底色（淡化版） |
| `--gradient-aurora` | `conic-gradient(from 180deg at 50% 50%, #00BCD4 0deg, #7000FF 120deg, #0B0D14 240deg, #00BCD4 360deg)` | `conic-gradient(from 180deg at 50% 50%, #0097A7 0deg, #5E17EB 120deg, #F7F8FA 240deg, #0097A7 360deg)` | 首启/Dashboard Hero 极光背景 |
| `--gradient-status-bar` | `linear-gradient(90deg, rgba(0,188,212,0.04) 0%, transparent 50%, rgba(112,0,255,0.04) 100%)` | `linear-gradient(90deg, rgba(0,151,167,0.03) 0%, transparent 50%, rgba(94,23,235,0.03) 100%)` | Status Bar 顶部微渐变 |

### 2.2 字体系统

```css
--font-family-sans: 'Inter', 'HarmonyOS Sans SC', 'PingFang SC', -apple-system, BlinkMacSystemFont, sans-serif;
--font-family-mono: 'JetBrains Mono', 'SF Mono', 'Cascadia Code', Consolas, monospace;
```

| 令牌名 | size | weight | line-height | letter-spacing | 用途 |
| --- | --- | --- | --- | --- | --- |
| `--font-display-xl` | 40px | 700 | 48px | -0.8px | 首启/Hero 超大标题 |
| `--font-display-lg` | 32px | 700 | 40px | -0.5px | 页面一级标题 |
| `--font-display-md` | 24px | 600 | 32px | -0.3px | 区块标题 |
| `--font-title-lg` | 20px | 600 | 28px | -0.2px | 卡片标题、弹窗标题 |
| `--font-title-md` | 16px | 600 | 24px | -0.1px | 列表项主标题 |
| `--font-title-sm` | 14px | 600 | 20px | 0 | 按钮、Tab |
| `--font-body-lg` | 15px | 400 | 24px | 0 | 长文本（脚本、文案） |
| `--font-body-md` | 14px | 400 | 22px | 0 | 默认正文 |
| `--font-body-sm` | 13px | 400 | 20px | 0 | 元信息、说明 |
| `--font-caption` | 12px | 500 | 16px | 0.2px | 标签、时间戳 |
| `--font-mono-md` | 13px | 500 | 20px | 0 | 代码、时间码、ID |
| `--font-numeric-lg` | 28px | 700 | 32px | -0.5px | Dashboard 大数字（Inter 等宽数字） |

**字距硬规则**：中文段落 `letter-spacing: 0`；中英混排允许 `letter-spacing: 0` 但中文前后需加半角空格。

### 2.3 间距尺度（4 的倍数基准）

```css
--space-0: 0;
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
--space-20: 80px;
--space-24: 96px;
```

**使用硬规则**：
- 卡片内边距：`--space-6`（24px）
- 卡片之间：`--space-4`（16px）
- 表单字段间距：`--space-5`（20px）
- 页面主内容最大宽度：`1440px`，左右内边距 `--space-8`
- 侧栏图标与文字间距：`--space-3`

### 2.4 圆角尺度

```css
--radius-none: 0;
--radius-xs: 4px;    /* Chip / Tag */
--radius-sm: 6px;    /* Input / 小按钮 */
--radius-md: 8px;    /* 按钮 / 卡片（默认） */
--radius-lg: 12px;   /* 大卡片 / 弹窗 */
--radius-xl: 16px;   /* Hero 容器 */
--radius-2xl: 24px;  /* 特殊容器（首启向导卡） */
--radius-full: 9999px; /* 胶囊 / 头像 */
```

### 2.5 阴影体系

```css
/* Dark 模式：仅悬浮层用，避免"浑浊" */
--shadow-sm-dark: 0 1px 2px 0 rgba(0, 0, 0, 0.4);
--shadow-md-dark: 0 4px 12px 0 rgba(0, 0, 0, 0.5);
--shadow-lg-dark: 0 12px 32px 0 rgba(0, 0, 0, 0.6);
--shadow-glow-brand-dark: 0 0 24px 0 rgba(0, 188, 212, 0.32);
--shadow-glow-ai-dark: 0 0 32px 0 rgba(112, 0, 255, 0.28);

/* Light 模式：层级主导手段 */
--shadow-sm-light: 0 1px 2px 0 rgba(15, 18, 28, 0.04), 0 1px 1px 0 rgba(15, 18, 28, 0.06);
--shadow-md-light: 0 4px 8px -2px rgba(15, 18, 28, 0.06), 0 2px 4px -2px rgba(15, 18, 28, 0.04);
--shadow-lg-light: 0 12px 24px -6px rgba(15, 18, 28, 0.10), 0 4px 8px -4px rgba(15, 18, 28, 0.06);
--shadow-glow-brand-light: 0 0 16px 0 rgba(0, 151, 167, 0.24);
```

### 2.6 动效曲线与时长

```css
/* 时长梯度 */
--motion-instant: 80ms;    /* 按钮按下回弹前半段 */
--motion-fast: 160ms;      /* 悬停、颜色过渡 */
--motion-default: 240ms;   /* 主题切换、侧栏展开 */
--motion-slow: 400ms;      /* 弹窗入场、卡片入场 */
--motion-lazy: 600ms;      /* Hero 渐显 */

/* 贝塞尔曲线（核心 4 条） */
--ease-standard: cubic-bezier(0.4, 0.0, 0.2, 1);       /* 默认，Material 标准 */
--ease-decelerate: cubic-bezier(0.0, 0.0, 0.2, 1);     /* 入场，强调终点 */
--ease-accelerate: cubic-bezier(0.4, 0.0, 1.0, 1);     /* 离场，强调起始 */
--ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);      /* 按钮回弹、物理感 */
--ease-spring: cubic-bezier(0.22, 1, 0.36, 1);         /* 高级手感（Vercel 常用） */
```

**使用映射**：
- 按钮 hover / active：`--motion-instant` + `--ease-bounce`
- 卡片 hover 上浮：`--motion-fast` + `--ease-spring`
- 主题切换：`--motion-default` + `--ease-standard`
- 侧栏展开/折叠：`--motion-default` + `--ease-spring`
- 弹窗入场：`--motion-slow` + `--ease-decelerate`
- 弹窗离场：`--motion-fast` + `--ease-accelerate`

### 2.7 z-index 分层

```css
--z-base: 0;
--z-sticky: 10;       /* Sticky 表头、粘顶工具条 */
--z-sidebar: 20;
--z-titlebar: 30;
--z-statusbar: 30;
--z-dropdown: 100;
--z-tooltip: 200;
--z-modal-backdrop: 900;
--z-modal: 1000;
--z-toast: 1100;
--z-command-palette: 1200;  /* Cmd+K 搜索 */
```

---

## 3 · 壳层坐标化布局（AppShell）

### 3.1 整体骨架（桌面宽屏，≥ 1440px）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Title Bar                                                         48px 高   │
├──────────┬──────────────────────────────────────────────────┬───────────────┤
│          │                                                  │               │
│ Sidebar  │                 Content Host                     │ Detail Panel  │
│  280px   │             flex: 1（最小 640px）                │   360px       │
│          │                                                  │               │
│          │                                                  │               │
├──────────┴──────────────────────────────────────────────────┴───────────────┤
│ Status Bar                                                        28px 高   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Title Bar（固定顶部）

```
height: 48px;
background: var(--color-bg-surface);
border-bottom: 1px solid var(--color-border-subtle);
padding: 0 var(--space-4);
display: flex;
align-items: center;
justify-content: space-between;
-webkit-app-region: drag;  /* Tauri 拖动区 */
```

**左侧区**（`gap: 12px`，宽约 280px）：
- Logo：20 × 20 px，渐变方块 `--gradient-ai-primary`
- 产品名：`font-title-sm`，`--color-text-primary`
- 分隔符：`|` 14 × 14 px，`--color-border-default`
- 当前项目名：`font-body-md`，`--color-text-secondary`，超长省略

**中间区**（`flex: 1`，最大 560px 居中）：
- 全局搜索框（Cmd+K 触发）
- 高度 32px，圆角 `--radius-md`
- 背景 `--color-bg-muted`，聚焦边框 `--color-border-strong`
- 占位符："搜索项目 / 脚本 / 任务 / 资产"

**右侧区**（`gap: 8px`）：
- AI 状态圆点（8px）+ 文字 "AI 正常"（`font-caption`）
- Runtime 状态圆点
- 授权状态 Chip
- 主题切换按钮（32 × 32px）
- 设置图标按钮（32 × 32px）

### 3.3 Sidebar

**展开态**（280px）：
```
width: 280px;
background: var(--color-bg-canvas);
border-right: 1px solid var(--color-border-subtle);
padding: var(--space-4) var(--space-3);
display: flex;
flex-direction: column;
gap: var(--space-2);
transition: width var(--motion-default) var(--ease-spring);
```

**折叠态**（64px）：
```
width: 64px;
padding: var(--space-4) var(--space-2);
```

**分组标题**：
- 高 24px，`font-caption`，`--color-text-tertiary`
- 文字 UPPERCASE，`letter-spacing: 0.8px`
- 折叠态隐藏（`opacity: 0`）

**导航项**（单行 40px）：
- 内边距：展开 `padding: 0 12px`；折叠 `padding: 0; justify-content: center`
- 图标 20 × 20 px，Material Symbols
- 图标与文字间距 `--space-3`
- 圆角 `--radius-md`
- 五态详见 § 4.1

**底部固定区**（`margin-top: auto`）：
- 当前用户/授权卡片（72px 高）
- 折叠按钮（32 × 32px）

### 3.4 Content Host

```
flex: 1;
min-width: 640px;
background: var(--color-bg-canvas);
overflow-y: auto;
```

**页面内部结构**（所有 16 页强制统一）：

```
┌─────────────────────────────────────────────────────┐
│ 页面头（Page Header）            高 72px            │
│  - 面包屑（12px，--color-text-tertiary）            │
│  - 页面标题（font-display-lg）                      │
│  - 页面副标题（font-body-sm, --color-text-secondary)│
│  - 右侧工具区（按钮组 / 视图切换）                  │
├─────────────────────────────────────────────────────┤
│ 页面工具条（可选，Sticky 高 52px）                  │
│  - 筛选 / Tab / 快捷操作                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│ 主内容区                                            │
│  - 最大宽度 1440px，左右 padding --space-8          │
│  - 上 padding --space-6，下 padding --space-12      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 3.5 Detail Panel

**可收起**，三种宽度状态：
- 关闭：`width: 0`
- 常规：`width: 360px`
- 拓宽（时间线场景）：`width: 480px`

```
border-left: 1px solid var(--color-border-subtle);
background: var(--color-bg-surface);
padding: var(--space-6);
overflow-y: auto;
transition: width var(--motion-default) var(--ease-spring);
```

**内部结构**：
- 头部：关闭按钮 + 标题（高 48px）
- Tab 条（可选，高 40px）
- 内容区（滚动）
- 底部固定操作区（可选，高 56px，`border-top: 1px solid var(--color-border-subtle)`）

### 3.6 Status Bar

```
height: 28px;
background: var(--color-bg-surface);
border-top: 1px solid var(--color-border-subtle);
padding: 0 var(--space-4);
display: flex;
align-items: center;
justify-content: space-between;
font: var(--font-caption);
color: var(--color-text-secondary);
```

**左侧**（`gap: 16px`）：
- Runtime 状态 · "Runtime 8000 · 正常"
- 任务队列 · "3 运行中 / 2 排队"
- AI Provider · "OpenAI · 128ms"

**右侧**（`gap: 16px`）：
- 最近同步时间
- 当前主题
- 日志快捷打开图标

**顶部发光线**（任务运行时出现）：
```css
Status Bar::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: var(--gradient-status-bar);
  opacity: 0;
  transition: opacity var(--motion-default) var(--ease-standard);
}
[data-has-running-task="true"] Status Bar::before {
  opacity: 1;
  animation: status-flow 2.4s linear infinite;
}
@keyframes status-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}
```

### 3.7 响应式断点

| 断点 | 范围 | 布局调整 |
| --- | --- | --- |
| `xl` | ≥ 1440px | 默认（Sidebar 280 + Detail 360） |
| `lg` | 1200 ~ 1439px | Detail Panel 默认收起 |
| `md` | 960 ~ 1199px | Sidebar 自动折叠到 64px，Detail 仅按需弹出为 Drawer |
| `sm` | 720 ~ 959px | Sidebar 改为 Drawer（点击 Logo 弹出），单列主内容 |
| `xs` | < 720px（不支持，但需优雅降级） | 仅保留 Title + 单页主内容，提示"窗口过窄" |

**所有断点切换必须走** CSS 媒体查询，禁止 JS 监听 resize 重新渲染。

---

## 4 · 原子组件五态表

五态定义：`Normal` / `Hover` / `Active` / `Focus`（键盘） / `Disabled`。
所有属性以 CSS 声明形式给出，可直接抄入 `styles/` 目录。

### 4.1 Button · Primary

**基础尺寸**：
- `sm`：高 28px，padding `0 12px`，`font-title-sm`
- `md`（默认）：高 36px，padding `0 16px`，`font-title-sm`
- `lg`：高 44px，padding `0 20px`，`font-title-md`

```css
/* Normal */
.btn-primary {
  background: var(--color-brand-primary);
  color: var(--color-text-on-brand);
  border: none;
  border-radius: var(--radius-md);
  font: var(--font-title-sm);
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce),
    box-shadow var(--motion-fast) var(--ease-standard);
  will-change: transform;
}
/* Hover */
.btn-primary:hover {
  background: var(--color-brand-primary-hover);
  box-shadow: var(--shadow-glow-brand-dark);  /* Light 模式用 var(--shadow-glow-brand-light) */
}
/* Active（按下） */
.btn-primary:active {
  background: var(--color-brand-primary-active);
  transform: scale(0.98);
  transition-duration: var(--motion-instant);
}
/* Focus */
.btn-primary:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
/* Disabled */
.btn-primary:disabled {
  background: var(--color-bg-muted);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}
```

### 4.2 Button · Secondary（Ghost 边框）

```css
.btn-secondary {
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  /* 其他同上 */
}
.btn-secondary:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-strong);
}
.btn-secondary:active {
  transform: scale(0.98);
  background: var(--color-bg-active);
}
.btn-secondary:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
.btn-secondary:disabled {
  color: var(--color-text-tertiary);
  border-color: var(--color-border-subtle);
  cursor: not-allowed;
}
```

### 4.3 Button · AI（双色渐变，B 区触发器）

```css
.btn-ai {
  background: var(--gradient-ai-primary);
  background-size: 200% 200%;
  background-position: 0% 50%;
  color: #FFFFFF;
  border: none;
  border-radius: var(--radius-md);
  position: relative;
  overflow: hidden;
  transition:
    background-position var(--motion-default) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce);
}
.btn-ai:hover {
  background-position: 100% 50%;
  box-shadow: var(--shadow-glow-ai-dark);
}
.btn-ai:active {
  transform: scale(0.98);
}
/* 任务运行态：流光常驻 */
.btn-ai[data-state="running"] {
  animation: ai-flow 2.4s linear infinite;
}
@keyframes ai-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}
```

### 4.4 Button · Danger

```css
.btn-danger {
  background: var(--color-danger);
  color: #FFFFFF;
  /* 其他同 Primary */
}
.btn-danger:hover { filter: brightness(1.1); }
.btn-danger:active { transform: scale(0.98); filter: brightness(0.95); }
```

### 4.5 Input

```css
/* Normal */
.input {
  height: 36px;
  padding: 0 12px;
  background: var(--color-bg-muted);
  color: var(--color-text-primary);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font: var(--font-body-md);
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard);
}
.input::placeholder { color: var(--color-text-tertiary); }
/* Hover */
.input:hover { background: var(--color-bg-surface); }
/* Focus */
.input:focus {
  background: var(--color-bg-surface);
  border-color: var(--color-brand-primary);
  outline: none;
  box-shadow: 0 0 0 3px var(--color-brand-glow);
}
/* Error */
.input[data-error="true"] {
  border-color: var(--color-danger);
  box-shadow: 0 0 0 3px rgba(255, 90, 99, 0.18);
}
/* Disabled */
.input:disabled {
  background: var(--color-bg-muted);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}
```

### 4.6 Card

```css
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  transition:
    transform var(--motion-fast) var(--ease-spring),
    box-shadow var(--motion-fast) var(--ease-spring),
    border-color var(--motion-fast) var(--ease-standard);
}
/* Hover（可交互卡片才启用） */
.card[data-interactive="true"]:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md-dark);  /* Light 用 -light */
  border-color: var(--color-border-default);
}
/* Active */
.card[data-interactive="true"]:active {
  transform: translateY(0);
  transition-duration: var(--motion-instant);
}
/* Selected */
.card[data-selected="true"] {
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 1px var(--color-brand-primary), var(--shadow-md-dark);
}
```

### 4.7 Tab

```css
.tab {
  height: 40px;
  padding: 0 16px;
  color: var(--color-text-secondary);
  font: var(--font-title-sm);
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color var(--motion-fast) var(--ease-standard);
  position: relative;
}
.tab:hover { color: var(--color-text-primary); }
.tab[aria-selected="true"] {
  color: var(--color-brand-primary);
  border-bottom-color: var(--color-brand-primary);
}
/* 滑动下划线动效（B 区点睛） */
.tab-list { position: relative; }
.tab-list::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0;
  height: 2px;
  width: var(--indicator-width, 0);
  transform: translateX(var(--indicator-x, 0));
  background: var(--color-brand-primary);
  transition: transform var(--motion-default) var(--ease-spring), width var(--motion-default) var(--ease-spring);
}
```

### 4.8 Chip / Badge

```css
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 22px;
  padding: 0 8px;
  border-radius: var(--radius-full);
  font: var(--font-caption);
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}
.chip[data-variant="brand"] { background: var(--color-bg-active); color: var(--color-brand-primary); }
.chip[data-variant="success"] { background: rgba(34, 211, 154, 0.12); color: var(--color-success); }
.chip[data-variant="warning"] { background: rgba(245, 183, 64, 0.12); color: var(--color-warning); }
.chip[data-variant="danger"] { background: rgba(255, 90, 99, 0.12); color: var(--color-danger); }
```

### 4.9 Modal / Drawer

**Modal 基础**：
```css
.modal-backdrop {
  position: fixed; inset: 0;
  background: var(--color-bg-overlay);
  backdrop-filter: blur(8px);
  z-index: var(--z-modal-backdrop);
  opacity: 0;
  transition: opacity var(--motion-default) var(--ease-standard);
}
.modal-backdrop[data-open="true"] { opacity: 1; }

.modal {
  position: fixed;
  top: 50%; left: 50%;
  transform: translate(-50%, -48%) scale(0.96);
  opacity: 0;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg-dark);
  z-index: var(--z-modal);
  transition:
    transform var(--motion-slow) var(--ease-spring),
    opacity var(--motion-slow) var(--ease-spring);
}
.modal[data-open="true"] {
  transform: translate(-50%, -50%) scale(1);
  opacity: 1;
}
```

### 4.10 Toast

```css
.toast {
  display: flex; align-items: flex-start; gap: 12px;
  min-width: 320px; max-width: 480px;
  padding: 12px 16px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-subtle);
  border-left: 3px solid var(--color-brand-primary);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg-dark);
  transform: translateY(16px);
  opacity: 0;
  transition:
    transform var(--motion-default) var(--ease-spring),
    opacity var(--motion-default) var(--ease-standard);
}
.toast[data-open="true"] { transform: translateY(0); opacity: 1; }
.toast[data-variant="success"] { border-left-color: var(--color-success); }
.toast[data-variant="warning"] { border-left-color: var(--color-warning); }
.toast[data-variant="danger"] { border-left-color: var(--color-danger); }
```

### 4.11 Progress / Task 卡片

```css
.progress-track {
  height: 6px;
  background: var(--color-bg-muted);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--gradient-ai-primary);
  background-size: 200% 100%;
  border-radius: var(--radius-full);
  transition: width var(--motion-default) var(--ease-standard);
  /* 运行中流光 */
  animation: progress-flow 1.6s linear infinite;
}
@keyframes progress-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}
/* 暂停态关闭流光 */
.progress-fill[data-state="paused"] { animation: none; }
```

### 4.12 Timeline Track（A 区极简）

```css
.timeline-track {
  height: 56px;
  background: var(--color-bg-surface);
  border-top: 1px solid var(--color-border-subtle);
  position: relative;
}
.timeline-clip {
  position: absolute;
  top: 8px; bottom: 8px;
  background: linear-gradient(180deg, rgba(0,188,212,0.24), rgba(0,188,212,0.12));
  border: 1px solid var(--color-brand-primary);
  border-radius: var(--radius-sm);
  cursor: grab;
  transition: transform var(--motion-fast) var(--ease-spring);
}
.timeline-clip:hover { transform: translateY(-1px); }
.timeline-clip[data-selected="true"] {
  box-shadow: 0 0 0 2px var(--color-brand-primary), 0 0 16px var(--color-brand-glow);
}
```

---

## 5 · 16 页逐页线框与坐标

每页采用固定五段式规格：**页面目标 → 布局 → 组件清单 → 状态覆盖 → 关键动效（B 区触发点）**。
ASCII 线框仅示意区域划分，实际尺寸以右侧标注为准。

---

### 5.1 `setup_license_wizard` · 首启与许可证向导

**页面目标**：完成一机一码激活 + 本地目录初始化 + Runtime 健康检查 + 首个配置引导。

**布局**：全屏沉浸式，**不挂载 AppShell**。

```
┌───────────────────────────────────────────────────────────┐
│                                                           │
│  ╭─ Aurora 背景（B 区 · conic-gradient + 慢旋转） ─╮      │
│  │                                                │      │
│  │         ┌───── 向导卡片 640 × 560 ─────┐      │      │
│  │         │  [Logo 发光]                 │      │      │
│  │         │  TK-OPS                     │      │      │
│  │         │  AI 视频创作中枢              │      │      │
│  │         │                             │      │      │
│  │         │  ●●●○○  步骤指示器          │      │      │
│  │         │                             │      │      │
│  │         │  [当前步骤内容区]            │      │      │
│  │         │                             │      │      │
│  │         │  [上一步]        [下一步]   │      │      │
│  │         └─────────────────────────────┘      │      │
│  ╰────────────────────────────────────────────────╯      │
│                                                           │
│                        [跳过引导（受限模式）]              │
└───────────────────────────────────────────────────────────┘
```

**尺寸**：
- 卡片 `640 × 560 px`，居中，圆角 `--radius-2xl`
- 卡片背景 `var(--color-bg-surface)`，边框 `1px solid var(--color-border-default)`
- 卡片内边距 `--space-12`（48px）
- Aurora 背景 `conic-gradient(--gradient-aurora)`，20s 线性旋转，`filter: blur(80px)`，`opacity: 0.28`

**步骤**：
1. 欢迎页（带 Logo 发光 + 产品主张）
2. 许可证激活（输入 Key + 机器指纹展示 + 激活按钮）
3. 目录初始化（选择根目录 + 权限检查结果表）
4. Runtime 健康检查（自动轮询，展示进度条 + 端口、版本、依赖三项）
5. 首次 AI Provider 配置（选默认 Provider + API Key 输入）
6. 完成（粒子喷溅 + "进入创作总览"按钮）

**组件清单**：
- `SetupStepIndicator`（步骤点 + 连线）
- `SetupStepWelcome` / `SetupStepLicense` / `SetupStepDirectory` / `SetupStepRuntime` / `SetupStepAIProvider` / `SetupStepComplete`
- `AuroraBackground`（纯 CSS）

**五态**：加载中（Runtime 检查）/ 空（未输入 Key）/ 正常 / 错误（Key 失败、端口占用）/ 受限模式（用户选跳过）

**B 区触发点**：
1. **Aurora 背景**：整个向导期间慢速旋转，`@keyframes aurora-rotate { to { transform: rotate(360deg); } }`，20s 周期。
2. **激活成功粒子喷溅**：4 ~ 6 个 CSS 圆点从中心向外扩散，200ms 内完成，伴随卡片发光 `box-shadow: 0 0 64px var(--color-brand-glow)` 300ms 后回落。
3. **步骤切换**：内容区 `transform: translateX(16px) → 0` + `opacity: 0 → 1`，曲线 `--ease-spring`，时长 `--motion-default`。

---

### 5.2 `creator_dashboard` · 创作总览

**页面目标**：作为所有项目与任务的统一入口，不堆叠经营后台图表。

**布局**：

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 创作总览                                   [+ 新建项目]    │
│ 继续创作，追踪运行状态                                      │
├─ Hero Area (B 区 · 高 240px) ─────────────────────────────┤
│  ╭─ 动态渐变背景 ─╮                                        │
│  │ 上午好，创作者 │  当前项目：xxx                          │
│  │ 今日 3 条待发布 │  [快速进入]                            │
│  ╰───────────────╯                                         │
├─ 区块 1 · 最近工程（卡片横向滚动） ────────────────────────┤
│ [Card] [Card] [Card] [Card] [Card] →                        │
├─ 区块 2 · 待办与异常（二分栏） ────────────────────────────┤
│ ┌─ 待办（紧急）────┐  ┌─ 异常任务 ────────┐                │
│ │ · 渲染队列...    │  │ ⚠ AI Provider...  │                │
│ │ · 发布预检...    │  │ ⚠ 设备离线...     │                │
│ └──────────────────┘  └────────────────────┘                │
├─ 区块 3 · 健康面板（三列） ─────────────────────────────────┤
│ ┌─ AI 健康 ────┐ ┌─ 渲染队列 ───┐ ┌─ 发布状态 ──┐          │
│ │ 正常 · 128ms │ │ 3 运行 / 2   │ │ 今日 5 条成功│          │
│ └──────────────┘ └──────────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

**尺寸**：
- Hero 高 `240px`，圆角 `--radius-xl`，背景 `--gradient-ai-subtle` + 极微极光 overlay
- 最近工程卡片：`240 × 180 px`，横向滚动，`gap: 16px`
- 健康面板卡片：等宽三栏，`gap: 16px`，每卡 `160px` 高

**组件清单**：
- `DashboardHero`（问候语 + 当前项目快捷进入）
- `ProjectRecentCard`（缩略图 + 标题 + 时间戳 + 进度圆环）
- `TodoQueueCard` / `ExceptionQueueCard`
- `HealthPanelCard`（数字大字 + 副标签 + Sparkline 迷你图）

**B 区触发点**：
1. **Hero 动态渐变**：`background-position` 90s 周期循环，幅度极小（`0% 50% ↔ 20% 50%`），纯装饰。
2. **数字翻滚**：Dashboard 大数字（今日发布数、队列数）首次进入时从 0 计数到目标值，300ms，`--ease-decelerate`。用 CSS counter（非 JS）实现。
3. **异常卡呼吸边框**：当有异常时，`border-color` 在 `--color-danger` 和 `rgba(danger, 0.4)` 之间呼吸，2s 周期，`--ease-standard`。

---

### 5.3 `script_topic_center` · 脚本与选题中心

**页面目标**：主题、标题、脚本、文案的 AI 生成与改写，所有结果支持版本化。

**布局**：三栏（左：Prompt / 中：编辑器 / 右：版本与变体）

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 脚本与选题中心                [AI 生成] [风格预设 ▾]       │
├─ 三栏工作区 ──────────────────────────────────────────────┤
│ ┌─ Prompt 面板 ──┐ ┌─ 脚本编辑器 ──┐ ┌─ 版本与变体 ─┐      │
│ │ 320px          │ │ flex: 1        │ │ 320px        │      │
│ │                │ │                │ │              │      │
│ │ 主题           │ │ # 引子         │ │ ▸ v3（当前） │      │
│ │ 目标人群       │ │ ...            │ │ ▸ v2         │      │
│ │ 时长           │ │                │ │ ▸ v1         │      │
│ │ 风格           │ │ # 核心段       │ │              │      │
│ │ 参考链接       │ │ ...            │ │ 标题变体     │      │
│ │                │ │                │ │ ● 标题A      │      │
│ │ [生成脚本 AI]  │ │                │ │ ● 标题B      │      │
│ └────────────────┘ └────────────────┘ └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

**组件清单**：
- `PromptPanel`（字段组 + AI 按钮）
- `ScriptEditor`（分段编辑器，每段可独立"AI 改写此段"）
- `ScriptVersionList` / `TitleVariantList`
- `StylePresetPicker`

**B 区触发点**：
1. **AI 流式输出**：生成时编辑器顶部出现 2px 高渐变流光条，持续到流结束。
2. **新版本入场**：版本列表新增项从右侧 `translateX(16px) → 0` 滑入。
3. **AI 按钮运行态**：`.btn-ai[data-state="running"]` 持续流光（见 § 4.3）。

---

### 5.4 `storyboard_planning_center` · 分镜规划中心

**页面目标**：把脚本结构转为可执行分镜与镜头节奏。

**布局**：左脚本段落 + 右分镜卡片瀑布流

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 分镜规划中心                   [AI 生成分镜] [节奏模板 ▾]  │
├─ 工具条：视图切换 [卡片瀑布] [时间线节奏] [结构对比] ──────┤
├─ 两栏 ─────────────────────────────────────────────────────┤
│ ┌─ 脚本段落（280px） ─┐ ┌─ 分镜卡片区 flex:1 ─────────────┐ │
│ │ ▸ 引子             │ │ ┌─ 镜头 1 ─┐ ┌─ 镜头 2 ─┐       │ │
│ │ ▸ 核心 1           │ │ │ [缩略]   │ │ [缩略]   │       │ │
│ │ ▸ 核心 2           │ │ │ 提示词   │ │ 提示词   │       │ │
│ │ ▸ 结尾             │ │ │ 时长 4s  │ │ 时长 3s  │       │ │
│ │                    │ │ └──────────┘ └──────────┘       │ │
│ │                    │ │ ┌─ 镜头 3 ─┐ + 添加             │ │
│ │                    │ │ │ ...      │                     │ │
│ │                    │ │ └──────────┘                     │ │
│ └────────────────────┘ └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**分镜卡片尺寸**：`220 × 280 px`，`gap: 16px`，瀑布流 auto-fit。

**B 区触发点**：
1. **卡片拖拽重排**：拖起 `transform: scale(1.04) rotate(-1.5deg)` + 阴影升级；放下时其他卡片用 `--ease-spring` 填充空位。
2. **AI 生成分镜**：镜头卡片依次入场（stagger 60ms），每张从 `scale(0.96) opacity 0` → `scale(1) opacity 1`。

---

### 5.5 `ai_editing_workspace` · AI 剪辑工作台 ★核心页

**页面目标**：视频、音轨、字幕、AI 输出的统一时间线工作台。

**布局**：三区（顶部预览 + 中间多轨时间线 + 右侧属性面板）

```
┌─ Page Header（精简，高 48px） ─────────────────────────────┐
│ [项目名]  保存: 刚刚        [渲染] [预览] [导出]            │
├─ 预览区（高 360px） ───────────────────────────────────────┤
│ ┌─ 片段库 240px ─┐ ┌─ 预览窗口 flex:1 ─┐ ┌─ 工具栏 160px ┐│
│ │ [缩略] [缩略]  │ │                     │ │ 播放控制       ││
│ │ [缩略] [缩略]  │ │    [视频预览]       │ │ 时长 00:45     ││
│ └────────────────┘ └─────────────────────┘ └───────────────┘│
├─ 时间线区（flex: 1） ──────────────────────────────────────┤
│ 00:00  00:05  00:10  00:15  00:20  00:25  [时间刻度]       │
│ [Video]  [===片段1===][==片段2==]   [==片段3==]              │
│ [Audio]  [====================旁白音轨===================]   │
│ [Voice]  [==TTS1==]     [==TTS2==]          [==TTS3==]       │
│ [Subt ]  [==字幕段 A=====][==字幕段 B======]                │
├─ AI 工具条（浮动底部，28px） ──────────────────────────────┤
│ [AI 生成镜头] [AI 替换旁白] [AI 重对齐字幕]  运行 2          │
└─────────────────────────────────────────────────────────────┘
```

**Detail Panel（480px 宽）** 展示选中片段属性。

**关键约束**：
- 时间线区必须是 A 区（高密度、极简），禁止背景动画。
- AI 工具条按钮是 B 区，运行时流光。
- 拖拽片段必须 60fps，使用 `transform: translateX()` 而非 `left`。

**B 区触发点**：
1. **AI 生成新片段**：时间线片段位置入场：`transform: scaleX(0) → 1`，transform-origin 左，400ms + `--ease-decelerate`，同时轮廓发光 1s 后消退。
2. **片段拖拽**：hover 时轮廓亮化，拖起 `transform: scale(1.02) translateY(-1px)` + 阴影升级。
3. **渲染开始**：Status Bar 顶部发光线出现（见 § 3.6）。

---

### 5.6 `video_deconstruction_center` · 视频拆解中心

**页面目标**：把导入视频转为可重制项目。

**布局**：顶部导入队列 + 中间阶段流水线 + 底部拆解结果预览

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 视频拆解中心                            [+ 导入视频]        │
├─ 导入队列（高 72px，水平滚动） ────────────────────────────┤
│ [视频1 · 转写中 45%] [视频2 · 完成] [视频3 · 等待]          │
├─ 阶段流水线（高 120px） ───────────────────────────────────┤
│ 转写 ●───── 切段 ●───── 镜头识别 ○───── 脚本抽取 ○        │
├─ 拆解结果预览（二栏） ─────────────────────────────────────┤
│ ┌─ 原视频 + 时间线 ─┐ ┌─ 改写草稿 ─┐                        │
│ │ [播放器]          │ │ 脚本正文...  │                        │
│ │ 00:12 · 段落 1    │ │             │                        │
│ │ 00:28 · 段落 2    │ │             │                        │
│ └───────────────────┘ └─────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

**B 区触发点**：
1. **阶段节点点亮**：每个阶段完成时节点从 `--color-bg-muted` 变为 `--color-brand-primary`，伴随 8px glow 脉冲 1 次。
2. **流水线连线**：连线采用 `background-position` 流光，运行中的阶段间流光持续。

---

### 5.7 `voice_studio` · 配音中心

**布局**：左角色音色库 + 中 TTS 参数 + 下段落列表

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 配音中心                            [生成配音 AI]           │
├────────────────────────────────────────────────────────────┤
│ ┌─ 音色库 280px ──┐ ┌─ 参数面板 flex:1 ─┐ ┌─ 版本 320px ─┐│
│ │ [女声·温柔]      │ │ 文本 [编辑区]      │ │ v3 当前      ││
│ │ [女声·商务]      │ │                   │ │ v2           ││
│ │ [男声·低沉]      │ │ 语速 [====O===]   │ │ v1           ││
│ │ + 自定义         │ │ 情绪 [列表]        │ │              ││
│ │                  │ │ 停顿 [自动]        │ │              ││
│ │                  │ │ [试听]             │ │              ││
│ └──────────────────┘ └───────────────────┘ └──────────────┘│
├─ 段落列表（底部高 200px） ─────────────────────────────────┤
│ 段 1: "xxxx"  00:03 [播放] [重新生成]                      │
│ 段 2: "xxxx"  00:05 [播放] [重新生成]                      │
└─────────────────────────────────────────────────────────────┘
```

**B 区触发点**：
1. **试听波形**：正在播放的段落出现 CSS 波形动画（5 ~ 7 根竖条，`animation-delay` 阶梯错开）。
2. **AI 生成中**：段落卡片左边框渐变流光。

---

### 5.8 `subtitle_alignment_center` · 字幕对齐中心

**布局**：左音频波形 + 右字幕段列表，时间轴贯通

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 字幕对齐中心                 [AI 对齐] [样式模板 ▾] [导出] │
├─ 二栏 ─────────────────────────────────────────────────────┤
│ ┌─ 波形 + 时间轴（60%） ─┐ ┌─ 字幕段列表（40%）─┐          │
│ │ [~~~波形~~~~~~~~~~~~]  │ │ 00:00-00:03         │          │
│ │ 00:00      00:30       │ │ "第一段文字"         │          │
│ │                        │ │ ──                   │          │
│ │                        │ │ 00:03-00:07         │          │
│ │                        │ │ "第二段文字"         │          │
│ └────────────────────────┘ └──────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

**B 区触发点**：
1. **AI 对齐进度**：波形上出现游标扫过动画，完成后每段字幕边框脉冲 1 次。
2. **段选中**：列表项和波形对应区块同步高亮（双向联动，仅 color / background，无位移）。

---

### 5.9 `asset_library` · 资产中心

**布局**：侧栏分组 + 主区网格瀑布流 + Detail Panel 属性

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 资产中心              [视图 □▦]  [上传] [新建分组]          │
├────────────────────────────────────────────────────────────┤
│ ┌─ 分组 240 ─┐ ┌─ 资产网格 flex:1 ────────────────────────┐│
│ │ 全部       │ │ [缩] [缩] [缩] [缩] [缩] [缩]             ││
│ │ 视频片段   │ │ [缩] [缩] [缩] [缩] [缩] [缩]             ││
│ │ 图片       │ │ [缩] [缩] [缩] [缩] [缩] [缩]             ││
│ │ 音频       │ │                                           ││
│ │ 字幕模板   │ │                                           ││
│ │ 封面       │ │                                           ││
│ │ 工程版本   │ │                                           ││
│ └────────────┘ └───────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**资产卡尺寸**：`160 × 160 px`（图标视图）或 `240 × 180 px`（预览视图）。

**B 区触发点**：
- 卡片 hover 上浮 2px + 显示悬浮标签（来源、引用项目、体积）。
- 选中卡片品牌色描边 + 微发光。

---

### 5.10 `account_management` · 账号管理

**布局**：顶部工具条 + 表格式列表 + Detail Panel（选中账号详情）

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 账号管理                         [+ 新增账号] [分组 ▾]      │
├─ 筛选条：[搜索] [状态: 全部 ▾] [分组: 全部 ▾] ─────────────┤
├─ 表格 ─────────────────────────────────────────────────────┤
│ □ 头像 名称 分组 绑定设备 状态 发布目标 最后同步 操作        │
│ □ 🧑 user1 A组   PC-01    正常 TikTok   2h 前   [详情]      │
│ □ 🧑 user2 B组   PC-02    警告 TikTok   1d 前   [详情]      │
└─────────────────────────────────────────────────────────────┘
```

**状态 Chip**：正常（success）/ 警告（warning）/ 离线（danger）/ 未绑定（muted）。

---

### 5.11 `device_workspace_management` · 设备与工作区管理

**布局**：卡片网格（每工作区一张卡）+ Detail Panel 日志

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 设备与工作区管理               [+ 新建工作区] [健康检查]    │
├─ 工作区卡片网格（3 列） ───────────────────────────────────┤
│ ┌─ PC-01 ────┐ ┌─ PC-02 ────┐ ┌─ PC-03 ────┐              │
│ │ ● 正常     │ │ ⚠ 警告     │ │ ○ 离线     │              │
│ │ 浏览器 2   │ │ 浏览器 1   │ │ 浏览器 0   │              │
│ │ 账号 3     │ │ 账号 1     │ │ 账号 0     │              │
│ │ 最后: 5m   │ │ 最后: 2h   │ │ 最后: 1d   │              │
│ │ [诊断]     │ │ [诊断]     │ │ [重连]     │              │
│ └────────────┘ └────────────┘ └────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

**B 区触发点**：正常状态的圆点做呼吸光（opacity 0.6 ↔ 1，2s，极缓）。

---

### 5.12 `automation_console` · 自动化执行中心

**布局**：Tab 切换任务类型 + 表格式任务列表

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 自动化执行中心                       [+ 新建任务]           │
├─ Tab: [采集] [回复] [同步] [校验] [全部] ──────────────────┤
├─ 表格 ─────────────────────────────────────────────────────┤
│ 状态 任务名 类型 绑定账号 规则 下次执行 最后结果 操作         │
│ ●    xxxx  采集 user1    每日 2h 后   成功     [日志]       │
│ ⚠    xxxx  回复 user2    关键词 --    失败     [重试]       │
└─────────────────────────────────────────────────────────────┘
```

**运行中任务**：状态列显示旋转 loader（`animation: spin 1s linear infinite`，仅当前行，不超过 6 个）。

---

### 5.13 `publishing_center` · 发布中心

**布局**：顶部日历 Tab / 列表 Tab + 预检清单抽屉

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 发布中心                             [+ 新建发布计划]       │
├─ Tab: [日历视图] [列表视图] [预检] ───────────────────────┤
├─ 日历视图（月历） ─────────────────────────────────────────┤
│ 周一 周二 周三 周四 周五 周六 周日                          │
│  1    2    3    4    5    6    7                            │
│       [x]       [x2]                                        │
│  8    9   10   11   12   13   14                            │
│ [x3]                                                        │
└─────────────────────────────────────────────────────────────┘
```

**日期格子中的发布数量** `[xN]` 是品牌色胶囊。

**B 区触发点**：发布成功时对应格子短暂 glow（1s）。

---

### 5.14 `render_export_center` · 渲染与导出中心

**布局**：顶部队列 + 底部导出配置模板

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 渲染与导出中心              [+ 新建渲染] [资源占用: 42%]    │
├─ 队列 ─────────────────────────────────────────────────────┤
│ ▶ 渲染任务 1   项目A  1080p  ▓▓▓▓░░ 67%  预计 2m            │
│ ⏸ 渲染任务 2   项目B  720p   ░░░░░░ 等待中                  │
│ ✓ 渲染任务 3   项目C  1080p  完成  导出路径...              │
├─ 导出配置模板（卡片组） ───────────────────────────────────┤
│ [1080p @30fps] [720p @60fps] [4K 高码率] [自定义]          │
└─────────────────────────────────────────────────────────────┘
```

**B 区触发点**：运行中进度条走流光；完成时整行短暂 glow + 打勾图标 scale 入场。

---

### 5.15 `review_optimization_center` · 复盘与优化中心

**布局**：左项目选择 + 主区三栏卡片（结果 / 异常 / 建议）

```
┌─ Page Header ──────────────────────────────────────────────┐
│ 复盘与优化中心       项目: [xxx ▾] 版本: [v2 ▾]            │
├────────────────────────────────────────────────────────────┤
│ ┌─ 结果摘要 ───┐ ┌─ 异常记录 ──┐ ┌─ AI 优化建议 ────────┐ │
│ │ 总时长 0:45  │ │ 渲染失败 1  │ │ 1. 前 3 秒节奏过慢    │ │
│ │ 发布 5 平台  │ │ 发布超时 2  │ │ 2. 字幕位置可优化     │ │
│ │ 表现分 82    │ │ ...         │ │ 3. BGM 音量偏小       │ │
│ │ 复用资产 3   │ │             │ │ [回流新项目]          │ │
│ └──────────────┘ └─────────────┘ └──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

### 5.16 `ai_system_settings` · AI 与系统设置

**布局**：左侧设置分组 + 右主内容区

```
┌─ Page Header ──────────────────────────────────────────────┐
│ AI 与系统设置                                              │
├────────────────────────────────────────────────────────────┤
│ ┌─ 设置分组 240 ─┐ ┌─ 主内容区 flex:1 ──────────────────┐ │
│ │ Provider       │ │                                     │ │
│ │ 模型           │ │ [Provider 管理 · 列表 + 新增]       │ │
│ │ 音色           │ │                                     │ │
│ │ 字幕策略       │ │                                     │ │
│ │ 目录           │ │                                     │ │
│ │ 缓存           │ │                                     │ │
│ │ 日志           │ │                                     │ │
│ │ 诊断           │ │                                     │ │
│ └────────────────┘ └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**B 区触发点**：Provider 测试成功短暂 glow；测试失败 shake 1 次（`transform: translateX(-2px) ↔ 2px`，3 次，总时长 240ms）。

---

## 6 · 状态驱动动效库（B 区触发表）

| 动效 ID | 触发时机 | 实现 | 时长 | 曲线 | 页面 |
| --- | --- | --- | --- | --- | --- |
| `aurora-rotate` | 首启向导期间 | `conic-gradient` + `transform: rotate()` 20s 循环 | 20s × N | `linear` | 5.1 |
| `activation-burst` | 许可证激活成功 | 4-6 个圆点 `transform: scale(0) → 3` + `opacity 1 → 0` | 400ms | `--ease-decelerate` | 5.1 |
| `card-hover-lift` | 可交互卡片悬停 | `translateY(-2px)` + 阴影升级 | 160ms | `--ease-spring` | 全局 |
| `button-press-damp` | 按钮按下 | `scale(0.98)` + 瞬间回弹 | 80ms | `--ease-bounce` | 全局 |
| `ai-flow` | AI 按钮 hover / 运行中 | `background-position` 2.4s 循环 | 2.4s × N | `linear` | 全局 AI 按钮 |
| `progress-flow` | 进度条运行中 | `background-position` 1.6s 循环 | 1.6s × N | `linear` | 全局进度条 |
| `status-flow` | Status Bar 有运行任务 | 顶部 1px 发光线 `background-position` | 2.4s × N | `linear` | AppShell |
| `tab-indicator-slide` | Tab 切换 | 下划线 transform 滑动 | 240ms | `--ease-spring` | 全局 Tab |
| `number-count-up` | Dashboard 数字入场 | CSS counter + `@property` 过渡 | 300ms | `--ease-decelerate` | 5.2 |
| `exception-breathe` | 异常卡存在时 | `border-color` 呼吸 2s | 2s × N | `--ease-standard` | 5.2 |
| `sidebar-toggle` | 侧栏展开/折叠 | `width` 过渡 + 文字 opacity | 240ms | `--ease-spring` | AppShell |
| `theme-switch` | 主题切换 | 全局 CSS Variables 过渡 | 240ms | `--ease-standard` | AppShell |
| `modal-enter` | 弹窗入场 | `scale(0.96) → 1` + opacity | 400ms | `--ease-spring` | 全局 |
| `toast-slide-up` | Toast 入场 | `translateY(16px) → 0` + opacity | 240ms | `--ease-spring` | 全局 |
| `clip-gen-grow` | AI 生成时间线片段 | `scaleX(0) → 1` + 轮廓发光 | 400ms + 1s | `--ease-decelerate` | 5.5 |
| `pipeline-node-pulse` | 拆解阶段完成 | `box-shadow` 脉冲 1 次 | 600ms | `--ease-standard` | 5.6 |
| `voice-wave-play` | 配音播放 | 5-7 根竖条 `scaleY` 阶梯 | 持续 | `ease-in-out` 循环 | 5.7 |
| `subtitle-align-scan` | 字幕对齐时 | 游标 `translateX` 扫过波形 | 按时长 | `linear` | 5.8 |
| `device-heartbeat` | 正常设备圆点 | `opacity 0.6 ↔ 1` | 2s × N | `--ease-standard` | 5.11 |
| `render-complete-glow` | 渲染任务完成 | 行 `box-shadow` glow 1s | 1s | `--ease-standard` | 5.14 |
| `provider-test-shake` | Provider 测试失败 | `translateX(-2px ↔ 2px)` 3 次 | 240ms | `linear` | 5.16 |

**统一降级规则**：
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 7 · 前端模块化任务矩阵

所有任务按 16 页 × 五层（`page / composable / helpers / types / styles`）+ 共享层（`shell / design-tokens / ui-kit / motion`）拆分。

### 7.0 共享层（先做完）

| 模块 | 文件路径 | 内容 | 预计工作量 |
| --- | --- | --- | --- |
| 设计令牌 | `apps/desktop/src/styles/tokens/colors.css` | § 2.1 全部色彩令牌，Light/Dark 双版本 | 0.5d |
| 设计令牌 | `apps/desktop/src/styles/tokens/typography.css` | § 2.2 字体令牌 + `@font-face` | 0.5d |
| 设计令牌 | `apps/desktop/src/styles/tokens/spacing.css` | § 2.3 ~ 2.7 间距/圆角/阴影/动效/z-index | 0.5d |
| 设计令牌 | `apps/desktop/src/styles/tokens/index.css` | 聚合入口 | 0.1d |
| 主题控制 | `apps/desktop/src/stores/shell-ui.ts`（已存在）| 增加 `theme` / `reducedMotion` / `sidebarCollapsed` 状态 + 持久化 | 0.5d |
| UI Kit | `apps/desktop/src/components/ui/Button/` | Primary / Secondary / AI / Danger / Ghost 五态 | 1d |
| UI Kit | `apps/desktop/src/components/ui/Input/` | 文本 / 密码 / 数字 / Textarea 五态 | 1d |
| UI Kit | `apps/desktop/src/components/ui/Card/` | 含 Interactive / Selected 变体 | 0.5d |
| UI Kit | `apps/desktop/src/components/ui/Chip/` | 5 个变体 | 0.3d |
| UI Kit | `apps/desktop/src/components/ui/Modal/` | 入离场动效 | 1d |
| UI Kit | `apps/desktop/src/components/ui/Toast/` | 结合 `task-bus.ts` | 1d |
| UI Kit | `apps/desktop/src/components/ui/Progress/` | 含流光变体 | 0.3d |
| UI Kit | `apps/desktop/src/components/ui/Tab/` | 含滑动下划线 | 0.5d |
| UI Kit | `apps/desktop/src/components/ui/Dropdown/` | Select / Menu | 1d |
| 动效库 | `apps/desktop/src/styles/motion/keyframes.css` | § 6 全部 @keyframes 定义 | 0.5d |
| 动效库 | `apps/desktop/src/composables/useMotion.ts` | 按需启用/禁用动效 | 0.3d |
| AppShell | `apps/desktop/src/layouts/AppShell.vue`（已存在）| 按 § 3 重写坐标与响应式 | 2d |
| AppShell | `apps/desktop/src/layouts/parts/TitleBar.vue` | § 3.2 | 1d |
| AppShell | `apps/desktop/src/layouts/parts/Sidebar.vue` | § 3.3 | 1d |
| AppShell | `apps/desktop/src/layouts/parts/StatusBar.vue` | § 3.6 + 任务流光 | 0.5d |
| AppShell | `apps/desktop/src/layouts/parts/DetailPanel.vue` | § 3.5 | 0.5d |

**共享层小计**：约 13 个工作日。

### 7.1 ~ 7.16 · 逐页任务矩阵

每页统一拆分为五类文件，命名约定：
- `page` → `pages/<slug>/<PageName>.vue`
- `composable` → `pages/<slug>/use-<feature>.ts`
- `helpers` → `pages/<slug>/helpers/*.ts`
- `types` → `pages/<slug>/types.ts`
- `styles` → `pages/<slug>/<PageName>.module.css`
- `runtime-adapter` → `modules/<slug>-api/*.ts`（统一走 Runtime 适配层）

#### 7.1 · `setup_license_wizard`

| 层级 | 文件 | 内容 |
| --- | --- | --- |
| page | `pages/setup/SetupWizardPage.vue` | 全屏布局 + Aurora 背景 + 步骤切换 |
| composable | `pages/setup/use-license-activation.ts` | 激活流程状态机 |
| composable | `pages/setup/use-runtime-healthcheck.ts` | Runtime 轮询 |
| helpers | `pages/setup/helpers/fingerprint.ts` | 机器指纹格式化 |
| types | `pages/setup/types.ts` | `SetupStep` / `LicenseActivationState` |
| styles | `pages/setup/SetupWizard.module.css` | Aurora + 卡片 + 粒子 |
| runtime | `modules/license-api/activate.ts` | POST `/api/license/activate` |
| 已有依赖 | `stores/license.ts`、`stores/bootstrap.ts` | 已存在 |

#### 7.2 · `creator_dashboard`

| 层级 | 文件 | 内容 |
| --- | --- | --- |
| page | `pages/dashboard/DashboardPage.vue` | Hero + 三区块组合 |
| composable | `pages/dashboard/use-dashboard-data.ts` | 聚合最近项目 / 任务 / 健康数据 |
| component | `pages/dashboard/components/DashboardHero.vue` | B 区 Hero |
| component | `pages/dashboard/components/ProjectRecentCard.vue` | 项目缩略卡 |
| component | `pages/dashboard/components/HealthPanelCard.vue` | 健康数字卡 + CountUp |
| component | `pages/dashboard/components/ExceptionQueueCard.vue` | 异常卡 + 呼吸边框 |
| composable | `pages/dashboard/use-count-up.ts` | CSS counter 数字翻滚 |
| styles | `pages/dashboard/Dashboard.module.css` | |
| runtime | `modules/dashboard-api/aggregate.ts` | GET `/api/dashboard/overview` |

#### 7.3 · `script_topic_center`

| 层级 | 文件 | 内容 |
| --- | --- | --- |
| page | `pages/scripts/ScriptTopicPage.vue` | 三栏 |
| component | `pages/scripts/components/PromptPanel.vue` | Prompt 字段组 |
| component | `pages/scripts/components/ScriptEditor.vue` | 分段编辑器（每段有 AI 改写按钮） |
| component | `pages/scripts/components/ScriptVersionList.vue` | 版本列表 |
| component | `pages/scripts/components/TitleVariantList.vue` | 标题变体 |
| composable | `pages/scripts/use-ai-stream.ts` | 流式 AI 输出订阅（WebSocket） |
| composable | `pages/scripts/use-script-versions.ts` | 版本快照与回退 |
| runtime | `modules/script-api/*.ts` | 脚本 CRUD、AI 生成、变体 |

#### 7.4 · `storyboard_planning_center`

| 层级 | 文件 | 内容 |
| --- | --- | --- |
| page | `pages/storyboards/StoryboardPage.vue` | 左脚本段落 + 右分镜瀑布流 |
| component | `pages/storyboards/components/StoryboardCard.vue` | 单个镜头卡 |
| component | `pages/storyboards/components/ScriptSegmentNav.vue` | 脚本段落锚点 |
| composable | `pages/storyboards/use-storyboard-reorder.ts` | 拖拽重排（使用 HTML5 DnD + transform） |
| composable | `pages/storyboards/use-script-storyboard-sync.ts` | 脚本/分镜双向引用同步 |
| runtime | `modules/storyboard-api/*.ts` | |

#### 7.5 · `ai_editing_workspace` ★

| 层级 | 文件 | 内容 |
| --- | --- | --- |
| page | `pages/workspace/EditingWorkspacePage.vue` | 三区布局 |
| component | `pages/workspace/components/PreviewPanel.vue` | 预览播放器 |
| component | `pages/workspace/components/ClipLibrary.vue` | 左片段库 |
| component | `pages/workspace/components/Timeline.vue` | 多轨时间线容器 |
| component | `pages/workspace/components/TimelineTrack.vue` | 单轨 |
| component | `pages/workspace/components/TimelineClip.vue` | 单片段 |
| component | `pages/workspace/components/TimelineRuler.vue` | 时间刻度 |
| component | `pages/workspace/components/AIToolbar.vue` | 底部 AI 工具条 |
| composable | `pages/workspace/use-timeline-drag.ts` | 拖拽 + 吸附（仅 transform） |
| composable | `pages/workspace/use-timeline-zoom.ts` | 缩放（CSS transform） |
| composable | `pages/workspace/use-clip-selection.ts` | 选区状态 |
| composable | `pages/workspace/use-preview-sync.ts` | 预览与时间线同步 |
| helpers | `pages/workspace/helpers/time-format.ts` | 秒 ↔ 时:分:秒.毫秒 |
| helpers | `pages/workspace/helpers/snap-points.ts` | 吸附点计算 |
| 已有依赖 | `stores/editing-workspace.ts` | 已存在 |

#### 7.6 ~ 7.16 · 其余页面

为避免冗长，以下页面采用同样五层拆分模板，只列关键模块：

| 页面 | 关键组件 | 关键 composable | Runtime 模块 |
| --- | --- | --- | --- |
| 5.6 视频拆解 | `ImportQueue` / `PipelineStages` / `DeconstructionResult` | `use-import-pipeline` / `use-stage-polling` | `modules/video-import-api` |
| 5.7 配音 | `VoiceLibrary` / `TTSParamPanel` / `VoiceSegmentList` | `use-tts-generation` / `use-voice-preview` | `modules/voice-api` |
| 5.8 字幕 | `WaveformViewer` / `SubtitleSegmentList` / `SubtitleStyleEditor` | `use-subtitle-align` / `use-waveform-sync` | `modules/subtitle-api` |
| 5.9 资产 | `AssetGrid` / `AssetFilter` / `AssetDetailPanel` | `use-asset-search` / `use-asset-upload` | `modules/asset-api` |
| 5.10 账号 | `AccountTable` / `AccountDetailPanel` / `AccountBindingDialog` | `use-account-status` | `modules/account-api` |
| 5.11 设备 | `WorkspaceCard` / `WorkspaceLog` / `BrowserInstanceList` | `use-workspace-health` | `modules/device-api` |
| 5.12 自动化 | `AutomationTaskTable` / `AutomationRuleEditor` | `use-automation-schedule` | `modules/automation-api` |
| 5.13 发布 | `PublishCalendar` / `PublishList` / `PrecheckDrawer` | `use-publish-precheck` / `use-calendar-grid` | `modules/publishing-api` |
| 5.14 渲染 | `RenderQueue` / `ExportTemplateGrid` | `use-render-queue` / `use-resource-monitor` | `modules/render-api` |
| 5.15 复盘 | `ReviewSummaryCard` / `ExceptionListCard` / `AISuggestionCard` | `use-review-flow` | `modules/review-api` |
| 5.16 系统设置 | `ProviderList` / `ModelPicker` / `VoicePresetList` / `LogViewer` | `use-provider-test` / `use-settings-section` | `modules/settings-api` |

**逐页预计工作量**：每页 3 ~ 5 个工作日（已扣除共享层）。16 页合计约 **60 ~ 80 个工作日**。

### 7.2 现有 plans 对齐

| 已有 plan | 对应页面 | 本文衔接 |
| --- | --- | --- |
| `m05-ai-editing-workspace-runtime-ui.md` | 5.5 | 本文为视觉补充，plan 为 Runtime 契约 |
| `m07-voice-studio-runtime-ui.md` | 5.7 | 同上 |
| `m08-subtitle-alignment-runtime-ui.md` | 5.8 | 同上 |
| `m09-asset-center-ui-runtime.md` | 5.9 | 同上 |
| `ai-system-settings-ui-runtime.md` | 5.16 | 同上 |
| `video-deconstruction-center.md` | 5.6 | 同上 |
| `shell-dashboard-redesign.md` | AppShell + 5.2 | 本文细化到坐标 |

---

## 8 · 验收清单

### 8.1 设计令牌验收（共享层完成后）

- [ ] `:root` 与 `[data-theme="dark"]` 两套完整令牌已落地
- [ ] 切换主题全程 60 fps，过渡流畅无闪烁
- [ ] `prefers-reduced-motion: reduce` 下所有动画降级
- [ ] Inter + HarmonyOS Sans SC 中英混排正确，数字等宽
- [ ] 8 个按钮变体（Primary/Secondary/AI/Danger × sm/md/lg）五态全覆盖
- [ ] Input / Card / Tab / Chip / Modal / Toast / Progress 五态全覆盖

### 8.2 AppShell 验收

- [ ] Title Bar 48px 精确，拖动区生效，搜索 Cmd+K 可触发
- [ ] Sidebar 展开 280 / 折叠 64 过渡 240ms 内
- [ ] Detail Panel 可完全收起（width: 0），展开 360 / 480
- [ ] Status Bar 28px，任务运行时顶部流光出现
- [ ] 响应式断点 lg / md / sm 行为符合 § 3.7

### 8.3 逐页五态 + 三端验收（16 页 × 5 × 2 = 160 项）

每页必须覆盖：
- 加载中 · Skeleton 或 `.loading` 样式
- 空状态 · 有插图/文案/主操作引导（禁止纯空白）
- 正常状态 · 真实 Runtime 数据
- 错误状态 · 明确错误原因 + 重试入口 + 日志跳转
- 运行中状态（异步页）· Progress / 流光 / Status Bar 联动

每页必须在：
- 桌面宽屏（≥ 1440px）
- 紧凑窗口（960 ~ 1199px）

两档尺寸下都通过视觉检查。

### 8.4 动效与性能

- [ ] § 6 全部动效清单已实现或明确标为 P1 推迟
- [ ] DevTools Performance 录制，关键页面主线程空闲 > 60%
- [ ] 所有动画元素在结束后移除 `will-change`
- [ ] 一次渲染中活跃动画元素 ≤ 6 个

### 8.5 可访问性（A11y）

- [ ] 所有按钮/输入有 `:focus-visible` 样式
- [ ] Tab 可键盘切换，下划线指示器同步
- [ ] 所有图标按钮有 `aria-label`
- [ ] 对比度 WCAG AA（文字 4.5:1 / 大标题 3:1）

---

## 9 · React Bits / Unicorn Studio 取舍对照

> 注：TK-OPS 是 **Vue 3** 项目，React Bits 不能直接引入。本表仅作**视觉灵感映射**，实现时用纯 CSS 或 Vue 组件等价复刻。

| React Bits 灵感 | TK-OPS 对应位置 | 实现方式 | 决策 |
| --- | --- | --- | --- |
| Aurora Background | 5.1 首启向导 | CSS `conic-gradient` + `blur` + `transform: rotate` | ✅ 采用 |
| Particles Burst | 5.1 激活成功 | 4-6 个 CSS 圆点 `transform: scale + opacity` | ✅ 采用 |
| Animated Counter | 5.2 Dashboard 数字 | CSS `@property` + `counter()` | ✅ 采用 |
| Gradient Border | 全局 AI 按钮 | `background` 双色渐变 + `background-position` 流动 | ✅ 采用 |
| Shiny Text | 首启 Hero 标题 | `background-clip: text` + `background-position` 动画 | ✅ 采用（仅 1 处） |
| Spotlight Card | 5.9 资产卡 hover | `radial-gradient` 跟随鼠标（CSS Variable 更新） | ⚠️ P1 优先级，先做简单 hover |
| Meteors | 首启背景 | 5-8 根 `linear-gradient` 线条 `translateY` | ❌ 与 Aurora 冲突，不采用 |
| 3D Card Tilt | 任意卡片 | `transform: perspective + rotateX/Y` 跟随鼠标 | ❌ 过度动效，违反 A 区原则 |
| Infinite Moving Cards | 5.2 最近工程 | 纯横向滚动 + snap | ⚠️ 不循环，改为 `scroll-snap` |
| Background Beams | 全局背景 | — | ❌ 与"专业不浮夸"冲突 |

| Unicorn Studio 灵感 | TK-OPS 对应位置 | 实现方式 | 决策 |
| --- | --- | --- | --- |
| 液态玻璃 / WebGL 流体 | — | — | ❌ 性能成本高，Tauri WebView GPU 占用不可控 |
| 极简线性品牌动画 | 首启 Logo 发光 | CSS `box-shadow` 呼吸 | ✅ 采用 |
| 渐变数据流 | Status Bar 任务流光 | CSS `background-position` | ✅ 采用 |

**统一原则**：任何动效必须能用 CSS transform/opacity/filter/background-position 四项实现，否则列入 P2 评审。

---

## 10 · Detail Panel 交互规格（§3.5 补充）

> 补充 §3.5 缺失的 Detail Panel 内部结构、5 种内容模式、页面联动规则与组件坐标。

### 10.1 页面 → Detail Panel 模式映射表（route meta 真源）

| 页面 | `detailPanelMode` | `statusBarMode` | 默认展开 | 说明 |
| --- | --- | --- | --- | --- |
| `setup_license_wizard` | `hidden` | `setup` | — | 向导全屏，不挂载 Detail Panel |
| `creator_dashboard` | `contextual` | `overview` | 否 | 展示项目上下文与运行状态 |
| `script_topic_center` | `contextual` | `editing` | 否 | 显示 Prompt 参数与版本摘要 |
| `storyboard_planning_center` | `contextual` | `editing` | 否 | 显示镜头参数与脚本映射 |
| `ai_editing_workspace` | `asset` | `editing` | 是（选中片段时） | 选中片段/资产的属性、生成参数 |
| `video_deconstruction_center` | `logs` | `review` | 否 | 拆解阶段日志与原始素材信息 |
| `voice_studio` | `contextual` | `editing` | 否 | 当前音色、模型、生成状态 |
| `subtitle_alignment_center` | `contextual` | `editing` | 否 | 字幕样式、时间码诊断 |
| `asset_library` | `asset` | `overview` | 是（选中资产时） | 资产元数据、标签、引用关系 |
| `account_management` | `binding` | `system` | 否 | 账号健康、绑定设备、发布目标 |
| `device_workspace_management` | `binding` | `system` | 否 | 设备运行信息与异常记录 |
| `automation_console` | `logs` | `tasks` | 否 | 任务日志与规则详情 |
| `publishing_center` | `binding` | `publishing` | 否 | 目标账号、设备、冲突与回执 |
| `render_export_center` | `logs` | `rendering` | 否 | 渲染日志与资源占用 |
| `review_optimization_center` | `logs` | `review` | 否 | 复盘日志与建议详情 |
| `ai_system_settings` | `settings` | `system` | 是 | 测试结果、诊断信息、系统状态 |

### 10.2 Detail Panel 内部通用结构

所有模式共享同一骨架，由 5 个可选区块组成：

```
┌─ Detail Panel 360px / 480px ──────────────────────┐
│ ┌─ 头部 48px ──────────────────────────────────┐  │
│ │ [关闭 ×]   [图标] 标题      [Badge 状态]     │  │
│ │            眉批（eyebrow）                   │  │
│ └──────────────────────────────────────────────┘  │
│ ┌─ Metric 条 56px（可选）──────────────────────┐  │
│ │ [指标1 值]   [指标2 值]   [指标3 值]         │  │
│ └──────────────────────────────────────────────┘  │
│ ┌─ Tab 条 40px（可选）─────────────────────────┐  │
│ │ [属性] [日志] [版本]  ——滑动下划线           │  │
│ └──────────────────────────────────────────────┘  │
│                                                    │
│   Section 标题                                     │
│   ┌─ Field ─────────────────────────────────────┐ │
│   │ 标签          值                            │ │
│   │ 标签          值                            │ │
│   └─────────────────────────────────────────────┘ │
│                                                    │
│   Section 标题                                     │
│   ┌─ Item 列表 ────────────────────────────────┐  │
│   │ [icon] 标题           meta                 │  │
│   │        说明文字                            │  │
│   │ [icon] 标题           meta                 │  │
│   └────────────────────────────────────────────┘  │
│                                                    │
│ ┌─ 底部操作区 56px（可选）─────────────────────┐  │
│ │ [次要操作]                     [主操作 ▶]    │  │
│ └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

### 10.3 内部组件 CSS 坐标

**头部**：
```css
.detail-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 48px;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
}
.detail-header__icon {
  font-size: 20px;
  color: var(--color-brand-primary);
}
.detail-header__title {
  font: var(--font-title-md);
  color: var(--color-text-primary);
  flex: 1;
}
.detail-header__eyebrow {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.detail-header__close {
  width: 28px; height: 28px;
  /* icon-button 五态 */
}
```

**Metric 条**：
```css
.detail-metrics {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
}
.detail-metric {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.detail-metric__value {
  font: var(--font-title-lg);
  color: var(--color-text-primary);
}
.detail-metric__label {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}
```

**Section**：
```css
.detail-section {
  padding: var(--space-4) var(--space-4) 0;
}
.detail-section__title {
  font: var(--font-title-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-3);
  letter-spacing: 0.3px;
}
.detail-section__description {
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-3);
}
```

**Field 行**：
```css
.detail-field {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border-subtle);
}
.detail-field:last-child { border-bottom: none; }
.detail-field__label {
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
  flex-shrink: 0;
  width: 100px;
}
.detail-field__value {
  font: var(--font-body-md);
  color: var(--color-text-primary);
  text-align: right;
  word-break: break-all;
}
.detail-field__value[data-mono="true"] {
  font-family: var(--font-family-mono);
  font-size: 12px;
}
```

**Item 行**：
```css
.detail-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border-subtle);
}
.detail-item:last-child { border-bottom: none; }
.detail-item__icon {
  font-size: 18px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
  margin-top: 1px;
}
.detail-item__icon[data-tone="brand"] { color: var(--color-brand-primary); }
.detail-item__icon[data-tone="success"] { color: var(--color-success); }
.detail-item__icon[data-tone="danger"] { color: var(--color-danger); }
.detail-item__body { flex: 1; min-width: 0; }
.detail-item__title {
  font: var(--font-body-md);
  color: var(--color-text-primary);
}
.detail-item__description {
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}
.detail-item__meta {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}
```

**空态**：
```css
.detail-empty {
  text-align: center;
  padding: var(--space-10) var(--space-6);
  color: var(--color-text-tertiary);
  font: var(--font-body-sm);
}
.detail-empty__icon {
  font-size: 40px;
  margin-bottom: var(--space-4);
  opacity: 0.4;
}
```

**底部操作区**：
```css
.detail-actions {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  height: 56px;
  padding: 0 var(--space-4);
  background: var(--color-bg-surface);
  border-top: 1px solid var(--color-border-subtle);
}
```

### 10.4 五种模式内容规格

#### 10.4.1 `contextual` — 上下文模式（默认）

**用途**：通用页面工作上下文展示。

```
头部：[页面图标] 页面名称 上下文 · [Runtime 状态 Badge]
       眉批：页面类型
Metrics：页面类型 | 项目上下文 | AI Provider
Section 1 "工作上下文"：
  Field: 当前页面 / 项目 / Runtime / 授权
Section 2 "共享层约定"：
  Items: detailPanelMode / statusBarMode / pageType
```

#### 10.4.2 `asset` — 资产模式

**用途**：选中资产的完整属性视图。

```
未选中：
  空态图标 + "在资产中心或工作台选中真实资产后查看详情"

已选中：
  头部：[inventory_2] 资产详情 · [类型 Badge]
  Metrics：资产名称 | 标签数 | 引用数
  Section 1 "属性与元数据"：
    Fields: 类型 / 来源 / 大小 / 路径(mono) / 创建时间 / 更新时间
  Section 2 "真实标签"：
    Items: Tag 列表（brand tone）
  Section 3 "引用影响范围"：
    Items: 引用项列表（link icon + referenceType + referenceId）
  操作区：[检查引用并删除]（disabled if references > 0）
```

#### 10.4.3 `logs` — 日志模式

**用途**：任务日志流与阶段信息。面板宽 480px。

```
头部：[receipt_long] 页面名称 日志 · [statusBarMode Badge]
Section 1 "日志通道"：
  Items: Runtime 状态 / 项目上下文（各带 tone + icon）
Section 2 "日志内容"：
  空态: "当前没有可展示的实时日志。接入 WebSocket 后日志会出现在这里。"
  接入后：逆序日志条目（时间戳 + level + message）
```

#### 10.4.4 `binding` — 绑定模式

**用途**：账号、设备、发布对象的绑定关系与状态。

```
头部：[link] 页面名称 绑定信息 · [许可证状态 Badge]
Section 1 "当前绑定链路"：
  Fields: 项目 / 许可证 / Runtime
Section 2 "接入说明"：
  Items:
  - [manage_accounts] 账号绑定需要真实对象
  - [desktop_windows] 工作区绑定需要真实目录
```

#### 10.4.5 `settings` — 系统诊断模式

**用途**：系统级状态、版本、路径、AI 配置。面板宽 480px。

```
头部：[settings] 系统与 AI 可用性 · [配置总线状态 Badge]
Metrics：Runtime 版本 | AI Provider | 主题
Section 1 "系统状态"：
  Fields: Runtime / 许可证 / 配置总线 / 当前项目
Section 2 "目录与边界"：
  Fields: 工作区 / 缓存目录 / 导出目录 / 日志目录
```

### 10.5 Detail Panel 动效

| 交互 | 动效 | 时长 | 曲线 |
| --- | --- | --- | --- |
| 面板展开 | `width: 0 → 360/480` + `opacity 0 → 1` + `translateX(16px) → 0` | `--motion-default` | `--ease-spring` |
| 面板收起 | 反向 | `--motion-fast` | `--ease-accelerate` |
| 内容模式切换 | `opacity 0 → 1` + `translateX(8px) → 0` | `--motion-fast` | `--ease-standard` |
| Item 入场 | stagger 30ms，`opacity 0 → 1` + `translateY(4px) → 0` | `--motion-fast` | `--ease-decelerate` |

---

## 11 · `ai_system_settings` 多 AI 配置中心完整设计（§5.16 重写）

> 覆盖原 §5.16 极简线框。本节定义多 AI Provider 配置中心的完整交互规格，支持 24+ Provider、动态模型获取、连通性测试、7 个能力绑定。

### 11.1 页面目标

让用户能**自由接入任意 AI 模型商**、配置 API Key 与 Base URL、动态拉取可用模型列表、测试连通性，并将 7 个创作能力分别绑定到不同 Provider + Model 组合。同时管理 TTS 音色、字幕策略、系统目录、缓存与日志。

**核心原则**：
- **不写死模型列表**：支持 `supportsModelDiscovery` 的 Provider 从远端实时拉取模型，其余用内置注册表 + 手动输入
- **Provider 配置即测即用**：Key 填入 → 测试 → 通过后 Capability 绑定即可选择
- **错误前置**：API Key 无效、Base URL 错误、模型不可用在配置阶段就暴露，不等到生成时才报错

### 11.2 页面布局

```
┌─ Page Header ──────────────────────────────────────────────┐
│ AI 与系统设置                                              │
├────────────────────────────────────────────────────────────┤
│ ┌─ 设置导航 220px ─┐ ┌─ 主内容区 flex:1 ──────────────────┐│
│ │                  │ │                                    ││
│ │ ⬤ Provider 管理  │ │ ┌──────────────────────────────┐   ││
│ │   能力绑定       │ │ │   当前选中设置分组的内容区   │   ││
│ │   Prompt 模板    │ │ │                              │   ││
│ │ ── 分割线 ──     │ │ │                              │   ││
│ │   音色管理       │ │ │                              │   ││
│ │   字幕策略       │ │ │                              │   ││
│ │ ── 分割线 ──     │ │ │                              │   ││
│ │   目录           │ │ │                              │   ││
│ │   缓存           │ │ └──────────────────────────────┘   ││
│ │   日志           │ │                                    ││
│ │   诊断           │ │                                    ││
│ └──────────────────┘ └────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘
```

**设置导航**：
- 宽 220px（非 240px，给主区更多空间）
- 导航项高 36px，圆角 `--radius-sm`，激活态 `--color-bg-active` + `--color-brand-primary` 文字
- 分组间用 1px `--color-border-subtle` 分割线 + `--space-3` 间距
- **分组结构**：AI 配置（Provider 管理 / 能力绑定 / Prompt 模板）→ 媒体（音色管理 / 字幕策略）→ 系统（目录 / 缓存 / 日志 / 诊断）

### 11.3 Provider 管理

#### 11.3.1 Provider 列表视图

```
┌─ Provider 管理 ────────────────────────────────────────────┐
│                                                            │
│ 搜索 [____________🔍]    筛选 [全部 ▾]  [+ 自定义 Provider] │
│                                                            │
│ ┌─ 商业服务 ───────────────────────────────────────────────┐│
│ │                                                          ││
│ │ ┌─ Provider 卡片 ─────────────────────────────────────┐  ││
│ │ │ ┌──┐                                                │  ││
│ │ │ │OA│  OpenAI                    ● 就绪 · 128ms      │  ││
│ │ │ └──┘  gpt-5, gpt-5.4 等 3 个模型                    │  ││
│ │ │       API Key: sk-xx****xxxx                         │  ││
│ │ │       文本生成 ✓  视觉 ✓  TTS ✓                     │  ││
│ │ │                         [测试] [配置 →]              │  ││
│ │ └──────────────────────────────────────────────────────┘  ││
│ │                                                          ││
│ │ ┌─ Provider 卡片 ─────────────────────────────────────┐  ││
│ │ │ ┌──┐                                                │  ││
│ │ │ │An│  Anthropic                 ○ 未配置             │  ││
│ │ │ └──┘  claude-sonnet                                  │  ││
│ │ │       API Key: 未设置                                │  ││
│ │ │       文本生成 ✓  视觉 ✓                            │  ││
│ │ │                         [测试] [配置 →]              │  ││
│ │ └──────────────────────────────────────────────────────┘  ││
│ │ ...                                                      ││
│ └──────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌─ 本地推理 ───────────────────────────────────────────────┐│
│ │ Ollama (就绪)  ·  LM Studio (离线)  ·  vLLM (离线)      ││
│ └──────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌─ 聚合路由 ───────────────────────────────────────────────┐│
│ │ OpenRouter (未配置)                                      ││
│ └──────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘
```

**Provider 卡片规格**：
```css
.provider-card {
  display: grid;
  grid-template-columns: 40px 1fr auto;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-spring);
}
.provider-card:hover {
  border-color: var(--color-border-default);
}
.provider-card[data-status="ready"] {
  border-left: 3px solid var(--color-success);
}
.provider-card[data-status="misconfigured"] {
  border-left: 3px solid var(--color-warning);
}
.provider-card[data-status="missing_secret"] {
  border-left: 3px solid var(--color-border-subtle);
}
.provider-card[data-status="offline"] {
  border-left: 3px solid var(--color-danger);
}
```

**Provider 图标**：40 × 40px，圆角 `--radius-md`，背景 `--color-bg-muted`，内部 2 字母缩写居中，`font-title-sm`，`--color-text-secondary`。

**状态指示器**：
| 状态 | 圆点颜色 | 文字 | 含义 |
| --- | --- | --- | --- |
| `ready` | `--color-success` + glow | "就绪 · {latency}ms" | Key 有效 + 连通 |
| `misconfigured` | `--color-warning` | "配置异常" | Key 存在但测试失败 |
| `missing_secret` | `--color-text-tertiary` | "未配置" | 无 API Key |
| `offline` | `--color-danger` | "离线" | 无法连接（本地推理未启动等） |
| `testing` | `--color-info` + 旋转 | "测试中..." | 正在探针 |

**能力标签**：`font-caption`，行内 Chip 列表，已支持显示 ✓，未支持不显示。

**分组筛选**：
- 全部 / 商业服务(`commercial`) / 本地推理(`local`) / 聚合路由(`aggregator`) / 媒体(`media`)
- 搜索框：按 label / provider_id 模糊匹配

#### 11.3.2 Provider 配置抽屉（点击"配置 →"展开）

不使用弹窗，使用 **右侧内联展开** 或 **抽屉** 避免上下文丢失：

```
┌─ 配置 · OpenAI ────────────────────────────────────────────┐
│ [← 返回列表]                                     [关闭 ×] │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ API Key                                                    │
│ ┌──────────────────────────────────────────────┐           │
│ │ sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx       [👁] │           │
│ └──────────────────────────────────────────────┘           │
│ 来源：安全存储    环境变量：TK_OPS_OPENAI_API_KEY           │
│                                                            │
│ Base URL                                                   │
│ ┌──────────────────────────────────────────────┐           │
│ │ https://api.openai.com/v1/responses          │           │
│ └──────────────────────────────────────────────┘           │
│ 默认值，留空使用官方地址                                     │
│                                                            │
│ ── 连通性测试 ─────────────────────────────────────────── │
│                                                            │
│ 测试模型  [gpt-5            ▾]   [▶ 测试连通性]            │
│                                                            │
│ ┌─ 测试结果 ───────────────────────────────────┐           │
│ │ ● 就绪 · 延迟 128ms · gpt-5                 │           │
│ │ 测试时间 2026-04-18 14:32:05                 │           │
│ └──────────────────────────────────────────────┘           │
│                                                            │
│ ── 可用模型 ──────────────────────────────────────────── │
│                                                            │
│ [刷新模型列表 ↻]                  共 3 个模型               │
│                                                            │
│ ┌─────────────────────────────────────────────┐            │
│ │ gpt-5            文本生成 · 视觉            │            │
│ │ gpt-5.4          文本生成 · 视觉            │            │
│ │ gpt-5.4-mini     文本生成                   │            │
│ │ gpt-4o-mini-tts  TTS                        │            │
│ └─────────────────────────────────────────────┘            │
│                                                            │
│                              [保存] [取消]                  │
└────────────────────────────────────────────────────────────┘
```

**交互要点**：

1. **API Key 输入**：
   - 默认 mask 显示（`sk-xx****xxxx`），点击眼睛图标切换可见
   - 输入后自动检测来源标签（`安全存储` / `环境变量` / `未设置`）
   - 保存时调用 `PUT /api/settings/ai-providers/{provider_id}/secret`

2. **Base URL**：
   - 显示当前生效的 URL（可能来自用户设置 / 环境变量 / 默认值）
   - `requires_base_url == true` 的 Provider（如 `openai_compatible`、`azure_speech`）：**必填**，空值时显示错误态
   - 其余 Provider：可选，显示"默认值，留空使用官方地址"

3. **连通性测试**：
   - 测试模型下拉：从模型列表中选择一个模型
   - 点击"测试连通性"→ 按钮进入 `data-state="running"` 流光态
   - 调用 `POST /api/settings/ai-providers/{provider_id}/health`，`body: { model }`
   - 成功：`● 就绪 · 延迟 128ms`，结果卡片左边框 `--color-success`，短暂 glow
   - 失败：`✕ 连接失败 · 错误信息`，结果卡片左边框 `--color-danger`，shake 动效（§6 `provider-test-shake`）

4. **可用模型列表**：
   - 初始从 `GET /api/settings/ai-providers/{provider_id}/models` 加载
   - `supportsModelDiscovery == true` 的 Provider（Ollama、OpenRouter、LM Studio、vLLM、LocalAI）：
     - 显示"刷新模型列表 ↻"按钮
     - 点击调用 `POST /api/settings/ai-providers/{provider_id}/models/refresh`
     - 刷新期间按钮旋转，列表显示 skeleton
     - 刷新完成后列表更新，新模型入场 `opacity 0 → 1`
   - `supportsModelDiscovery == false` 的 Provider：
     - 显示内置注册表模型
     - 底部显示"手动添加"入口：用户可输入自定义 `model_id`（如新版本发布但注册表未更新时）
   - 每个模型行：模型名 + 能力标签（Chip: 文本生成 / 视觉 / TTS 等）

### 11.4 能力绑定矩阵

```
┌─ 能力绑定 ─────────────────────────────────────────────────┐
│                                                            │
│ 将 7 项 AI 能力分别绑定到 Provider 与模型                    │
│                                                            │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ 能力              启用  Provider        模型        状态│   │
│ ├──────────────────────────────────────────────────────┤   │
│ │ 脚本生成           ✓   [OpenAI    ▾]  [gpt-5    ▾]  ●  │   │
│ │ 脚本改写           ✓   [Anthropic ▾]  [claude   ▾]  ●  │   │
│ │ 分镜生成           ✓   [Gemini   ▾]  [gemini-p ▾]  ●  │   │
│ │ 配音生成           ○   [OpenAI    ▾]  [gpt-4o-t ▾]  ○  │   │
│ │ 字幕对齐           ○   [--       ▾]  [--       ▾]  ○  │   │
│ │ 视频生成           ○   [--       ▾]  [--       ▾]  ○  │   │
│ │ 素材分析           ○   [Gemini   ▾]  [gemini-p ▾]  ○  │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                            │
│ 提示：Provider 下拉只显示支持对应能力类型的 Provider         │
│                                                            │
│                               [保存绑定] [恢复默认]         │
└────────────────────────────────────────────────────────────┘
```

**交互规格**：

1. **启用开关**：Toggle Switch（28 × 16px），开启 `--color-brand-primary`，关闭 `--color-bg-muted`
2. **Provider 下拉**：
   - **动态过滤**：只显示 `capabilities` 包含对应 `capability_type` 的 Provider
   - 如 `tts_generation` 行只显示 capabilities 含 `tts` 的 Provider（openai / azure_speech / elevenlabs / volcengine_speech / minimax_speech / minimax / doubao / localai）
   - 未配置的 Provider 在下拉中灰色 + "(未配置)" 后缀
   - 已配置且 `ready` 的 Provider 显示绿色圆点
   - 数据源：`GET /api/settings/ai-capabilities/support-matrix`
3. **模型下拉**：
   - Provider 变更后自动刷新模型列表
   - 调用 `GET /api/settings/ai-providers/{provider_id}/models`
   - 模型列表按 `defaultFor` 包含当前 `capability_id` 的排在前面
   - `supportsModelDiscovery` 的 Provider：下拉底部显示"刷新远端模型"快捷操作
   - 用户也可手动输入任意 model_id（下拉支持 combobox 模式）
4. **状态圆点**：
   - 绿色 `--color-success`：Provider 已配置且 ready + 模型已选
   - 灰色 `--color-text-tertiary`：未启用或未配置
   - 黄色 `--color-warning`：Provider 配置了但测试未通过
5. **保存**：调用 `PUT /api/settings/ai-capabilities`，提交完整的 7 项配置
6. **恢复默认**：重置为内置默认（全部绑 OpenAI + 默认模型）

### 11.5 Prompt 模板编辑

```
┌─ Prompt 模板 ──────────────────────────────────────────────┐
│                                                            │
│ 为每项 AI 能力配置角色设定、系统 Prompt 和用户 Prompt 模板    │
│                                                            │
│ ┌─ 脚本生成 ───────────────────────────────────── [展开] ─┐│
│ │ 角色：资深短视频脚本策划                                 ││
│ │ Provider：OpenAI / gpt-5                                ││
│ └──────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌─ 脚本改写 ───────────────────────────────────── [展开] ─┐│
│ │ 角色：短视频脚本改写编辑                                 ││
│ │ Provider：Anthropic / claude-sonnet                     ││
│ └──────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌─ 分镜生成 ─────────────────────────── [展开] ▼ 已展开 ──┐│
│ │                                                          ││
│ │ 角色设定（Agent Role）                                   ││
│ │ ┌────────────────────────────────────────────┐           ││
│ │ │ 分镜规划导演                               │           ││
│ │ └────────────────────────────────────────────┘           ││
│ │                                                          ││
│ │ 系统 Prompt                                              ││
│ │ ┌────────────────────────────────────────────┐           ││
│ │ │ 把脚本文本拆解为清晰的镜头与视觉提示。     │           ││
│ │ │                                            │           ││
│ │ └────────────────────────────────────────────┘           ││
│ │                                                          ││
│ │ 用户 Prompt 模板                                         ││
│ │ ┌────────────────────────────────────────────┐           ││
│ │ │ 脚本内容：                                 │           ││
│ │ │ {{script}}                                 │           ││
│ │ │                                            │           ││
│ │ └────────────────────────────────────────────┘           ││
│ │ 可用变量：{{script}}                                     ││
│ │                                                          ││
│ │              [恢复默认]  [保存]                            ││
│ └──────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘
```

**交互要点**：
- **手风琴展开**：一次只展开一个，展开高度 `auto`（CSS `max-height` 过渡），折叠态显示角色 + Provider 摘要
- **变量高亮**：`{{variable}}` 在编辑器内用 `--color-brand-primary` 背景 + `--color-text-on-brand` 文字高亮
- **可用变量提示**：每个 capability 有不同变量（`script_generation: {{topic}}`、`script_rewrite: {{script}}, {{instructions}}` 等），自动显示在编辑器下方
- **保存**：调用 `PUT /api/settings/ai-capabilities`
- **恢复默认**：从后端获取内置默认值填入

### 11.6 音色管理（TTS Provider 联动）

```
┌─ 音色管理 ─────────────────────────────────────────────────┐
│                                                            │
│ TTS Provider  [OpenAI    ▾]              [+ 添加自定义音色] │
│                                                            │
│ ┌─ 音色卡片网格（3 列）──────────────────────────────────┐ │
│ │                                                        │ │
│ │ ┌─ 清晰女声 ──────┐ ┌─ 温柔讲述 ──────┐ ┌─ 沉稳男声 ─┐│ │
│ │ │ ◉ alloy         │ │ ◉ nova          │ │ ◉ echo     ││ │
│ │ │ Provider: OpenAI│ │ Provider: OpenAI│ │ Provider:  ││ │
│ │ │ 标签: 清晰 旁白 │ │ 标签: 温柔 生活 │ │ 标签: 沉稳 ││ │
│ │ │ zh-CN            │ │ zh-CN            │ │ zh-CN      ││ │
│ │ │                  │ │                  │ │            ││ │
│ │ │ [▶ 试听] [编辑] │ │ [▶ 试听] [编辑] │ │ [▶][编辑]  ││ │
│ │ └──────────────────┘ └──────────────────┘ └────────────┘│ │
│ └────────────────────────────────────────────────────────┘ │
│                                                            │
│ 提示：音色来源由 Provider 决定。更换 TTS Provider 后        │
│ 需要重新选择或配置音色。                                    │
└────────────────────────────────────────────────────────────┘
```

**交互要点**：
- **TTS Provider 下拉**：只显示 `capabilities` 含 `tts` 的 Provider，切换后音色列表刷新
- **试听**：点击后通过 TTS API 生成一段示例音频（3-5 秒），播放期间显示 CSS 波形动画
- **自定义音色**：填写 `voice_id`、`display_name`、`locale`、`tags`，Provider 从下拉继承
- **音色卡片**：`180 × 200 px`，圆角 `--radius-lg`，hover 上浮 2px
- **当前 `pending_provider` 的音色**：用警告 Chip 标注"待绑定 Provider"

### 11.7 系统分组（目录 / 缓存 / 日志 / 诊断）

沿用原始 Settings 模板，表单式布局：

**目录**：
- 工作区根目录：路径输入 + 浏览按钮（调用 Tauri file dialog）
- 缓存目录 / 导出目录 / 日志目录：同上
- 每个路径显示 `容量 / 可用空间`（如果 Runtime 返回）

**缓存**：
- 模型缓存 / 资产缓存 / 渲染缓存：各显示大小 + "清除"按钮
- "全部清除"按钮（danger 风格）
- 清除确认弹窗

**日志**：
- 日志级别下拉：`DEBUG / INFO / WARNING / ERROR`
- 日志保留天数：数字输入
- "打开日志目录"按钮
- 最近日志文件列表（只读）

**诊断**：
- Runtime 版本 / 运行时长 / 内存占用 / 端口
- "导出诊断包"按钮 → 调用 `POST /api/settings/maintenance/diagnostics/export`
- "导出后自动复制路径"开关

### 11.8 Detail Panel 联动（settings 模式）

AI 与系统设置页面的 Detail Panel（480px 宽）实时反映当前操作的上下文：

| 左侧选中分组 | Detail Panel 内容 |
| --- | --- |
| Provider 管理 | 当前选中 Provider 的健康探针历史、最近 3 次测试结果、错误日志 |
| 能力绑定 | 当前选中能力行的 Provider 支持矩阵（哪些 Provider 支持、推荐模型） |
| Prompt 模板 | 当前展开的模板预览渲染效果（用示例变量填充后的完整 prompt） |
| 音色管理 | 选中音色的详情 + 波形预览区域 |
| 目录 / 缓存 | 目录大小统计 + 磁盘空间可视化 |
| 日志 | 最近日志实时流 |
| 诊断 | Runtime 健康检查实时结果 |

### 11.9 数据流与 API 调用映射

| 交互 | API 调用 | 方法 |
| --- | --- | --- |
| 进入页面 | `GET /api/settings/ai-providers/catalog` | 加载 Provider 列表 + 状态 |
| 进入页面 | `GET /api/settings/ai-capabilities` | 加载 7 项能力绑定 |
| 进入页面 | `GET /api/settings/ai-capabilities/support-matrix` | 加载能力支持矩阵 |
| 配置 API Key | `PUT /api/settings/ai-providers/{id}/secret` | 保存密钥 |
| 测试连通性 | `POST /api/settings/ai-providers/{id}/health` | 健康探针 |
| 加载模型列表 | `GET /api/settings/ai-providers/{id}/models` | 拉取模型 |
| 刷新远端模型 | `POST /api/settings/ai-providers/{id}/models/refresh` | 动态发现 |
| 保存能力绑定 | `PUT /api/settings/ai-capabilities` | 更新 7 项配置 |
| 保存 Prompt | `PUT /api/settings/ai-capabilities` | 同上（含 Prompt 字段） |
| 音色列表 | `GET /api/voice/profiles` | 加载音色 |
| 添加音色 | `POST /api/voice/profiles` | 创建自定义音色 |
| TTS 试听 | `POST /api/voice/{project_id}/generate` | 生成试听音频 |

### 11.10 五态覆盖

| 状态 | 表现 |
| --- | --- |
| **加载中** | 设置导航 Skeleton（9 个 36px 条形）+ 主内容区 3 张 Provider 卡片 Skeleton |
| **空态** | Provider 列表全部 `missing_secret` 时：顶部引导卡"开始配置你的第一个 AI Provider"，品牌色边框 + 箭头指向卡片 |
| **正常** | Provider 卡片列表 + 状态圆点 + 能力标签 |
| **错误** | API 请求失败时：内容区顶部 Toast "加载失败：{error_code}"；单 Provider 测试失败：卡片内联错误信息 + shake |
| **运行中** | 连通性测试按钮流光 + 模型刷新旋转 + 保存按钮 loading |

### 11.11 B 区触发点

| 触发 | 动效 | 实现 |
| --- | --- | --- |
| Provider 测试成功 | 结果卡片左边框 `--color-success` + 短暂 glow 1s | `box-shadow: 0 0 24px var(--color-success)` → fade |
| Provider 测试失败 | 结果卡片 shake | `translateX(-2px ↔ 2px)` 3 次，240ms |
| 模型刷新完成 | 新模型行 stagger 入场 | `opacity 0 → 1`，stagger 40ms |
| 能力保存成功 | 保存按钮短暂变为 ✓ | 图标 `scale(0) → 1.2 → 1`，300ms |
| 音色试听播放 | 卡片底部 3 根竖条波形 | `scaleY` 阶梯循环（同配音中心 §5.7） |

### 11.12 组件清单

| 层级 | 文件 | 内容 |
| --- | --- | --- |
| page | `pages/settings/AISystemSettingsPage.vue` | 左导航 + 右内容区布局 |
| component | `pages/settings/components/SettingsNav.vue` | 左侧设置导航 |
| component | `pages/settings/components/ProviderList.vue` | Provider 卡片列表 + 搜索 + 筛选 |
| component | `pages/settings/components/ProviderCard.vue` | 单 Provider 卡片 |
| component | `pages/settings/components/ProviderConfigDrawer.vue` | Provider 配置抽屉（Key / URL / 测试 / 模型） |
| component | `pages/settings/components/ProviderHealthResult.vue` | 连通性测试结果卡片 |
| component | `pages/settings/components/ModelList.vue` | 可用模型列表（支持动态刷新 + 手动输入） |
| component | `pages/settings/components/CapabilityMatrix.vue` | 7 行能力绑定表 |
| component | `pages/settings/components/CapabilityRow.vue` | 单行：开关 + Provider 下拉 + Model 下拉 + 状态 |
| component | `pages/settings/components/PromptTemplateList.vue` | 手风琴式模板列表 |
| component | `pages/settings/components/PromptTemplateEditor.vue` | 单模板展开编辑器 |
| component | `pages/settings/components/VoiceProfileGrid.vue` | 音色卡片网格 |
| component | `pages/settings/components/VoiceProfileCard.vue` | 单音色卡片 |
| composable | `pages/settings/use-provider-management.ts` | Provider CRUD + 测试 + 状态 |
| composable | `pages/settings/use-capability-binding.ts` | 能力绑定读写 + 矩阵过滤 |
| composable | `pages/settings/use-model-discovery.ts` | 模型列表 + 动态刷新 |
| composable | `pages/settings/use-prompt-editing.ts` | Prompt 模板编辑 + 变量高亮 |
| composable | `pages/settings/use-voice-profiles.ts` | 音色管理 + 试听 |
| types | `pages/settings/types.ts` | `ProviderCardState` / `CapabilityBindingRow` / `PromptEditorState` 等 |
| styles | `pages/settings/AISystemSettings.module.css` | Provider 卡片 / 能力矩阵 / 手风琴 |
| runtime | `modules/settings-api/providers.ts` | Provider 相关 API 适配 |
| runtime | `modules/settings-api/capabilities.ts` | 能力绑定 API 适配 |
| runtime | `modules/settings-api/models.ts` | 模型发现 API 适配 |

### 11.13 模型发现流程图

```
用户打开 Provider 配置抽屉
       │
       ▼
GET /ai-providers/{id}/models  ──→  返回模型列表
       │
       ├─ supportsModelDiscovery == true?
       │     │
       │     ├─ 是 → 显示 [刷新模型列表 ↻] 按钮
       │     │         │
       │     │         ▼ (用户点击)
       │     │   POST /ai-providers/{id}/models/refresh
       │     │         │
       │     │         ├─ status: "refreshed" → 更新列表 + "已从远端获取 N 个模型"
       │     │         └─ status: "static_catalog" → Toast "当前使用内置注册表"
       │     │
       │     └─ 否 → 显示内置模型 + [手动添加] 入口
       │                │
       │                ▼ (用户输入自定义 model_id)
       │           追加到本地列表，标记 "(自定义)"
       │
       ▼
用户在 能力绑定 或 连通性测试 中选择模型
```

---

## 附录 A · 实施顺序建议

1. **Week 1 · 共享底座**（共享层任务矩阵）
   - 设计令牌全量落地
   - UI Kit 原子组件（Button / Input / Card / Chip / Modal / Toast / Progress / Tab）
   - AppShell 按坐标重写
2. **Week 2 · 首启 + Dashboard + 设置**（P0 底座）
   - 5.1 / 5.2 / 5.16
3. **Week 3-4 · 创作前置链**
   - 5.3 / 5.4 / 5.6
4. **Week 5-7 · 创作核心链**
   - 5.5 / 5.7 / 5.8 / 5.14
5. **Week 8-9 · 执行与治理**
   - 5.10 / 5.11 / 5.13
6. **Week 10 · 扫尾**
   - 5.9 / 5.12 / 5.15

总周期约 10 周（单人），可按多人并行压缩到 5 ~ 6 周。

## 附录 B · 本次交付文件清单

| 文件 | 内容 |
| --- | --- |
| `docs/UI-BLUEPRINT-2026-04-17.md` | 本文件（工程级设计蓝图） |
| `docs/ui-preview/index.html` | 单文件可交互原型（AppShell + Dashboard + AI 剪辑工作台） |

> 原型用于视觉对齐；**非最终实现**。正式实现必须按 § 7 的五层拆分写入 `apps/desktop/src`。

---

**文档结束。** 任何改动请遵循 `docs/PRD.md` § 5 的 16 页口径与本文 § 1 的状态驱动视觉策略。
