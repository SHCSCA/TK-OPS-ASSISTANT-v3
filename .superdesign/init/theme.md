# Superdesign 主题与设计令牌上下文

> 2026-07-19 原型覆盖：本轮以 `.superdesign/design-system.md` 和 `docs/prototypes/tk-ops-account-workspace/src/styles/tokens.css` 为唯一视觉令牌真源。继续使用深海军蓝 Sidebar、浅灰 Canvas、白色 Surface、青色阶段语义与紫色唯一 AI 主动作，并同时覆盖 Light / Dark。

## 设计系统摘要

- 主题：Light / Dark，共享结构与语义状态。
- 视觉：中性深浅表面，青色主品牌，紫色 AI 辅色，克制阴影与 AI 渐变。
- 字体：Inter / HarmonyOS Sans SC / PingFang SC；代码与时间码使用 JetBrains Mono 系。
- 间距：4px 基础网格，桌面密度在 1440 / 1199 / 960px 分档收紧。
- 圆角：4-24px；主要面板 8-16px。
- 壳层：Title Bar 48px、Sidebar 280 / 64px、Detail Panel 360px、Status Bar 28px。
- 动效：Haptic / Instant / Content / Scene / Celebration 五级，并提供 Reduced Motion 降级。
- CSS 体系：原生 CSS + CSS Variables + Vue scoped CSS；项目不使用 Tailwind。

## 完整全局样式与令牌源码

### apps/desktop/src/styles/index.css

```css
@import "./tokens/index.css";
@import "./motion/keyframes.css";
@import "./icons.css";
@import "./base.css";
@import "./bootstrap.css";
@import "./shell.css";
@import "./dashboard.css";
@import "./video.css";
@import "./workspace.css";

```

### apps/desktop/src/styles/tokens.css

```css
@import "./tokens/index.css";

```

### apps/desktop/src/styles/tokens/index.css

```css
/* apps/desktop/src/styles/tokens/index.css */
@import './colors.css';
@import './typography.css';
@import './motion.css';
@import './spacing.css';

```

### apps/desktop/src/styles/tokens/colors.css

```css
/* apps/desktop/src/styles/tokens/colors.css */

:root,
:root[data-theme="light"] {
  /* 2.1.1 基础色板 (Neutral) */
  --color-bg-canvas: #F7F8FA;
  --color-bg-surface: #FFFFFF;
  --color-bg-elevated: #FFFFFF;
  --color-bg-overlay: rgba(15,18,28,0.48);
  --color-bg-muted: #F0F2F5;
  --color-bg-hover: rgba(15,18,28,0.04);
  --color-bg-active: rgba(0,151,167,0.08);
  --color-border-subtle: rgba(15,18,28,0.06);
  --color-border-default: rgba(15,18,28,0.10);
  --color-border-strong: rgba(15,18,28,0.16);

  /* 2.1.2 文字色 */
  --color-text-primary: #0B0D14;
  --color-text-secondary: #4A5166;
  --color-text-tertiary: #7D8497;
  --color-text-on-brand: #FFFFFF;
  --color-text-inverse: #FFFFFF;

  /* 2.1.3 品牌与状态色 */
  --color-brand-primary: #0097A7;
  --color-brand-primary-hover: #00ACC1;
  --color-brand-primary-active: #00838F;
  --color-brand-glow: rgba(0,151,167,0.22);
  --color-brand-secondary: #5E17EB;
  --color-success: #12A670;
  --color-warning: #D98E00;
  --color-danger: #D63B45;
  --color-info: #2E63EB;

  /* 2.1.4 语义渐变 */
  --gradient-ai-primary: linear-gradient(135deg, #0097A7 0%, #5E17EB 100%);
  --gradient-ai-subtle: linear-gradient(135deg, rgba(0,151,167,0.06) 0%, rgba(94,23,235,0.06) 100%);
  --gradient-aurora: conic-gradient(from 180deg at 50% 50%, #0097A7 0deg, #5E17EB 120deg, #F7F8FA 240deg, #0097A7 360deg);
  --gradient-status-bar: linear-gradient(90deg, rgba(0,151,167,0.03) 0%, transparent 50%, rgba(94,23,235,0.03) 100%);

  /* 兼容旧变量 */
  --surface-primary: var(--color-bg-canvas);
  --surface-secondary: var(--color-bg-surface);
  --surface-tertiary: var(--color-bg-muted);
  --surface-sunken: color-mix(in srgb, var(--color-bg-muted) 88%, var(--color-bg-surface));
  --surface-elevated: var(--color-bg-elevated);
  --glass-bg: color-mix(in srgb, var(--color-bg-surface) 88%, transparent);
  --glass-border: var(--color-border-subtle);
  --text-primary: var(--color-text-primary);
  --text-secondary: var(--color-text-secondary);
  --text-tertiary: var(--color-text-tertiary);
  --brand-primary: var(--color-brand-primary);
  --brand-secondary: var(--color-brand-secondary);
  --brand-ink: #06363b;
  --status-success: var(--color-success);
  --status-warning: var(--color-warning);
  --status-error: var(--color-danger);
  --status-info: var(--color-info);
  --border-default: var(--color-border-default);
  --border-strong: var(--color-border-strong);
}

:root[data-theme="dark"] {
  /* 2.1.1 基础色板 (Neutral) */
  --color-bg-canvas: #0A0B0F;
  --color-bg-surface: #12141A;
  --color-bg-elevated: #1A1D26;
  --color-bg-overlay: rgba(10,11,15,0.72);
  --color-bg-muted: #16181F;
  --color-bg-hover: rgba(255,255,255,0.04);
  --color-bg-active: rgba(0,188,212,0.10);
  --color-border-subtle: rgba(255,255,255,0.06);
  --color-border-default: rgba(255,255,255,0.10);
  --color-border-strong: rgba(255,255,255,0.18);

  /* 2.1.2 文字色 */
  --color-text-primary: #EDEFF5;
  --color-text-secondary: #A8ADBA;
  --color-text-tertiary: #6B7183;
  --color-text-on-brand: #FFFFFF;
  --color-text-inverse: #0B0D14;

  /* 2.1.3 品牌与状态色 */
  --color-brand-primary: #00BCD4;
  --color-brand-primary-hover: #26D0E0;
  --color-brand-primary-active: #00A5BC;
  --color-brand-glow: rgba(0,188,212,0.38);
  --color-brand-secondary: #7000FF;
  --color-success: #22D39A;
  --color-warning: #F5B740;
  --color-danger: #FF5A63;
  --color-info: #5B8CFF;

  /* 2.1.4 语义渐变 */
  --gradient-ai-primary: linear-gradient(135deg, #00BCD4 0%, #7000FF 100%);
  --gradient-ai-subtle: linear-gradient(135deg, rgba(0,188,212,0.12) 0%, rgba(112,0,255,0.12) 100%);
  --gradient-aurora: conic-gradient(from 180deg at 50% 50%, #00BCD4 0deg, #7000FF 120deg, #0B0D14 240deg, #00BCD4 360deg);
  --gradient-status-bar: linear-gradient(90deg, rgba(0,188,212,0.04) 0%, transparent 50%, rgba(112,0,255,0.04) 100%);

  /* 兼容旧变量 */
  --surface-primary: var(--color-bg-canvas);
  --surface-secondary: var(--color-bg-surface);
  --surface-tertiary: var(--color-bg-muted);
  --surface-sunken: color-mix(in srgb, var(--color-bg-muted) 84%, var(--color-bg-surface));
  --surface-elevated: var(--color-bg-elevated);
  --glass-bg: color-mix(in srgb, var(--color-bg-surface) 88%, transparent);
  --glass-border: var(--color-border-subtle);
  --text-primary: var(--color-text-primary);
  --text-secondary: var(--color-text-secondary);
  --text-tertiary: var(--color-text-tertiary);
  --brand-primary: var(--color-brand-primary);
  --brand-secondary: var(--color-brand-secondary);
  --brand-ink: #d9feff;
  --status-success: var(--color-success);
  --status-warning: var(--color-warning);
  --status-error: var(--color-danger);
  --status-info: var(--color-info);
  --border-default: var(--color-border-default);
  --border-strong: var(--color-border-strong);
}

```

### apps/desktop/src/styles/tokens/typography.css

```css
/* apps/desktop/src/styles/tokens/typography.css */

:root {
  /* 2.2 字体族 */
  --font-family-sans: 'Inter', 'HarmonyOS Sans SC', 'PingFang SC', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-family-mono: 'JetBrains Mono', 'SF Mono', 'Cascadia Code', Consolas, monospace;

  /* 字号、字重、行高与字距 
   * 使用方式: font: var(--font-title-sm); letter-spacing: var(--ls-title-sm);
   */
  --font-display-xl: 700 40px/48px var(--font-family-sans);
  --ls-display-xl: -0.8px;

  --font-display-lg: 700 32px/40px var(--font-family-sans);
  --ls-display-lg: -0.5px;

  --font-display-md: 600 24px/32px var(--font-family-sans);
  --ls-display-md: -0.3px;
  
  --font-title-lg: 600 20px/28px var(--font-family-sans);
  --ls-title-lg: -0.2px;

  --font-title-md: 600 16px/24px var(--font-family-sans);
  --ls-title-md: -0.1px;

  --font-title-sm: 600 14px/20px var(--font-family-sans);
  --ls-title-sm: 0;
  
  --font-body-lg: 400 15px/24px var(--font-family-sans);
  --ls-body-lg: 0;

  --font-body-md: 400 14px/22px var(--font-family-sans);
  --ls-body-md: 0;

  --font-body-sm: 400 13px/20px var(--font-family-sans);
  --ls-body-sm: 0;
  
  --font-caption: 500 12px/16px var(--font-family-sans);
  --ls-caption: 0.2px;

  --font-mono-md: 500 13px/20px var(--font-family-mono);
  --ls-mono-md: 0;

  --font-numeric-lg: 700 28px/32px var(--font-family-sans);
  --ls-numeric-lg: -0.5px;

  /* 兼容旧变量 */
  --font-base: var(--font-family-sans);
  --font-mono: var(--font-family-mono);
  --line-display-xl: 48px;
  --line-display-lg: 40px;
  --line-display-md: 32px;
  --line-title-lg: 28px;
  --line-title-md: 24px;
  --line-title-sm: 20px;
  --line-body-lg: 24px;
  --line-body-md: 22px;
  --line-body-sm: 20px;
  --line-caption: 16px;
}

```

### apps/desktop/src/styles/tokens/spacing.css

```css
/* apps/desktop/src/styles/tokens/spacing.css */

:root {
  /* 2.3 间距尺度 */
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

  /* 2.4 圆角尺度 */
  --radius-none: 0;
  --radius-xs: 4px;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-2xl: 24px;
  --radius-full: 9999px;

  /* AppShell 布局常量 */
  --titlebar-height: 48px;
  --sidebar-width-expanded: 280px;
  --sidebar-width-collapsed: 64px;
  --detail-panel-width: 360px;
  --detail-panel-width-wide: 480px;
  --detail-rail-width: 44px;
  --statusbar-height: 28px;
  --content-min-width: 640px;

  /* 桌面密度令牌：窗口变窄时优先收紧间距，不缩放正文 */
  --density-page-max-width: 1360px;
  --density-page-padding-x: var(--space-8);
  --density-page-padding-y: var(--space-6);
  --density-page-padding-bottom: var(--space-8);
  --density-panel-gap: var(--space-4);
  --density-card-padding: var(--space-4);
  --density-control-height: 36px;

  /* 轨道颜色令牌 */
  --color-track-video: #38bdf8;
  --color-track-voice: #22c55e;
  --color-track-bgm: #a78bfa;
  --color-track-subtitle: #fb7185;

  /* 2.7 z-index 分层 */
  --z-base: 0;
  --z-sticky: 10;
  --z-sidebar: 20;
  --z-titlebar: 30;
  --z-statusbar: 30;
  --z-dropdown: 100;
  --z-tooltip: 200;
  --z-modal-backdrop: 900;
  --z-modal: 1000;
  --z-toast: 1100;
  --z-command-palette: 1200;
}

/* 动效 token 已迁移至 tokens/motion.css */
/* Reduced Motion 降级已迁移至 tokens/motion.css */

@media (max-width: 1440px) {
  :root {
    --detail-panel-width: 340px;
    --detail-panel-width-wide: 420px;
    --density-page-max-width: 1240px;
    --density-page-padding-x: var(--space-6);
    --density-page-padding-y: var(--space-5);
    --density-page-padding-bottom: var(--space-6);
    --density-panel-gap: var(--space-3);
  }
}

@media (max-width: 1199px) {
  :root {
    --detail-panel-width: 320px;
    --detail-panel-width-wide: 360px;
    --density-page-padding-x: var(--space-4);
    --density-page-padding-y: var(--space-4);
    --density-page-padding-bottom: var(--space-5);
    --density-panel-gap: var(--space-3);
  }
}

/* 2.5 阴影体系 */
:root,
:root[data-theme="light"] {
  --shadow-sm: 0 1px 2px 0 rgba(15, 18, 28, 0.04), 0 1px 1px 0 rgba(15, 18, 28, 0.06);
  --shadow-md: 0 4px 8px -2px rgba(15, 18, 28, 0.06), 0 2px 4px -2px rgba(15, 18, 28, 0.04);
  --shadow-lg: 0 12px 24px -6px rgba(15, 18, 28, 0.10), 0 4px 8px -4px rgba(15, 18, 28, 0.06);
  --shadow-glow-brand: 0 0 16px 0 rgba(0, 151, 167, 0.24);
  --shadow-glow-ai: 0 0 24px 0 rgba(94, 23, 235, 0.16);
}

:root[data-theme="dark"] {
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.4);
  --shadow-md: 0 4px 12px 0 rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 12px 32px 0 rgba(0, 0, 0, 0.6);
  --shadow-glow-brand: 0 0 24px 0 rgba(0, 188, 212, 0.32);
  --shadow-glow-ai: 0 0 32px 0 rgba(112, 0, 255, 0.28);
}

/* 960px 以下：收紧密度令牌，适配紧凑窗口 */
@media (max-width: 960px) {
  :root {
    --density-page-padding-x: var(--space-3);
    --density-page-padding-y: var(--space-3);
    --density-page-padding-bottom: var(--space-4);
    --density-panel-gap: var(--space-2);
    --density-control-height: 32px;
  }
}

```

### apps/desktop/src/styles/tokens/motion.css

```css
/* apps/desktop/src/styles/tokens/motion.css
 * 动效设计令牌 —— 5 级速度系统 + 缓动曲线
 *
 * 层级体系（由快到慢）：
 *   Tier 1 — Haptic(150ms):      触觉反馈，click/active/press
 *   Tier 2 — Instant(280ms):     即时过渡，hover/focus/tooltip
 *   Tier 3 — Content(500ms):     内容过渡，panel/modal/list enter
 *   Tier 4 — Scene(900ms):       场景过渡，page/sidebar/detail panel
 *   Tier 5 — Celebration(1500ms): 庆祝反馈，badge/toast/progress complete
 */

:root {
  /* ── 5 级速度系统 ── */
  --motion-haptic: 150ms;
  --motion-instant: 280ms;
  --motion-content: 500ms;
  --motion-scene: 900ms;
  --motion-celebration: 1500ms;

  /* ── 长周期循环动效（不参与 5 级体系） ── */
  --motion-flow: 3.6s;
  --motion-rotate-slow: 45s;
  --motion-rotate-med: 30s;
  --motion-breathe: 4.5s;
  --motion-pulse: 1.8s;
  --motion-spinner: 2400ms;
  --motion-spin: 3s;

  /* ── 缓动曲线 ── */
  --ease-standard: cubic-bezier(0.4, 0.0, 0.2, 1);
  --ease-decelerate: cubic-bezier(0.0, 0.0, 0.2, 1);
  --ease-accelerate: cubic-bezier(0.4, 0.0, 1.0, 1);
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-spring: cubic-bezier(0.22, 1, 0.36, 1);

  /* ── 向后兼容别名（旧 token 名继续可用，值已对应新体系） ── */
  --motion-fast: var(--motion-instant);
  --motion-default: var(--motion-content);
  --motion-base: var(--motion-content);
  --motion-slow: var(--motion-scene);
  --motion-lazy: var(--motion-scene);
}

/* Reduced Motion —— 一次性过渡降级，循环动效改为更慢节奏，避免 1ms 导致极速闪动 */
:root[data-reduced-motion="true"] {
  --motion-haptic: 1ms;
  --motion-instant: 1ms;
  --motion-content: 1ms;
  --motion-scene: 1ms;
  --motion-celebration: 1ms;
  --motion-flow: 12s;
  --motion-rotate-slow: 120s;
  --motion-rotate-med: 90s;
  --motion-breathe: 8s;
  --motion-pulse: 4s;
  --motion-spinner: 8s;
  --motion-spin: 6s;
}

```

### apps/desktop/src/styles/motion/keyframes.css

```css
/* apps/desktop/src/styles/motion/keyframes.css
 * 全局 @keyframes 仓库
 *
 * 治理规则：
 *   1. 有明确消费者的 keyframes 保留
 *   2. 孤立 keyframes 有未来用途的保留并标注用途，否则删除
 *   3. 新增 keyframes 必须有对应消费者
 */

@property --num {
  syntax: "<integer>";
  initial-value: 0;
  inherits: false;
}

/* ── 首启引导 ── */

/* 极光背景慢旋转 */
@keyframes aurora-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 激活成功粒子扩散 */
@keyframes activation-burst {
  0% { opacity: 1; transform: scale(0); }
  100% { opacity: 0; transform: scale(3); }
}

/* ── 加载与进度 ── */

/* 统一旋转加载图标 */
@keyframes spin {
  100% { transform: rotate(360deg); }
}

/* AI 按钮流光 / 运行中流光 */
@keyframes ai-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

/* 进度条运行中流光 */
@keyframes progress-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

/* Status Bar 顶部发光线 */
@keyframes status-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

/* ── 反馈与状态 ── */

/* 异常卡边框呼吸 */
@keyframes exception-breathe {
  0%, 100% { border-color: var(--color-danger); }
  50% { border-color: color-mix(in srgb, var(--color-danger) 40%, transparent); }
}

/* Toast 入场 */
@keyframes toast-slide-up {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 设备在线指示圆点呼吸 */
@keyframes device-heartbeat {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* 基础呼吸（通用） */
@keyframes subtle-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.72; transform: scale(0.96); }
}

/* ── 新增：动效体系 Layer 1 keyframes ── */

/* 骨架屏脉冲 */
@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 页面入场 */
@keyframes page-enter {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 页面离场 */
@keyframes page-leave {
  from { opacity: 1; transform: translateY(0); }
  to { opacity: 0; transform: translateY(-8px); }
}

/* 列表项入场 */
@keyframes list-item-enter {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}

/* 列表项离场 */
@keyframes list-item-leave {
  from { opacity: 1; transform: translateX(0); }
  to { opacity: 0; transform: translateX(8px); }
}

/* 徽标数字变化 */
@keyframes badge-count-change {
  from { transform: scale(1); }
  50% { transform: scale(1.3); }
  to { transform: scale(1); }
}

/* ========================================
 * 孤立 keyframes —— 保留（有未来用途）
 * ======================================== */

/* Dashboard 大数字过渡（搭配 @property --num） */
@keyframes number-count-up {
  from { --num: 0; }
  to { --num: var(--target-num, 100); }
}

/* AI 生成时间线片段入场（clip-gen-grow） */
@keyframes clip-gen-grow {
  0% { transform: scaleX(0); box-shadow: 0 0 16px var(--color-brand-glow); }
  100% { transform: scaleX(1); box-shadow: 0 0 0 transparent; }
}

/* 拆解阶段节点点亮脉冲（pipeline-node-pulse） */
@keyframes pipeline-node-pulse {
  0% { box-shadow: 0 0 0 0 var(--color-brand-glow); }
  100% { box-shadow: 0 0 0 8px transparent; }
}

/* 配音播放竖条波形（voice-wave-play） */
@keyframes voice-wave-play {
  0%, 100% { transform: scaleY(0.4); }
  50% { transform: scaleY(1); }
}

/* 字幕对齐扫过游标（subtitle-align-scan） */
@keyframes subtitle-align-scan {
  from { transform: translateX(0); }
  to { transform: translateX(100%); }
}

/* 渲染完成行发光（render-complete-glow） */
@keyframes render-complete-glow {
  0% { box-shadow: 0 0 0 0 var(--color-brand-glow); }
  50% { box-shadow: 0 0 16px 2px var(--color-brand-glow); }
  100% { box-shadow: 0 0 0 0 transparent; }
}

/* API 测试失败左右抖动（provider-test-shake） */
@keyframes provider-test-shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}

/*
 * Reduced Motion 降级统一由 tokens/motion.css 控制。
 * 用户主动切换 :root[data-reduced-motion="true"] 时 animation 时长降至 1ms，
 * 循环动效（pulse/spin/flow）应使用 --motion-pulse / --motion-spinner / --motion-spin / --motion-flow 等变量，
 * 不建议直接写 animation-duration: 1s 硬编码。
 */

```

### apps/desktop/src/styles/base.css

```css
/* base.css - Central styles with V2 Standard Feedback Components */
/* 状态色由 tokens/colors.css 统一管理，此处不再重复定义 */

.text-success { color: var(--color-success) !important; }
.text-warning { color: var(--color-warning) !important; }
.text-danger { color: var(--color-danger) !important; }

/* 全局文本溢出保护 */
.page-header__subtitle,
.page-header__title {
  overflow-wrap: break-word;
  word-break: break-word;
  min-width: 0;
}
.text-mono { font-family: var(--font-mono) !important; }
.spinning { animation: spin var(--motion-spinner) linear infinite; }
:root[data-reduced-motion="true"] .spinning { animation-play-state: paused; }

/* --- Global Feedback Components (V2 Standard) --- */

.dashboard-alert {
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font: var(--font-body-sm);
  line-height: 1.6;
  margin-bottom: var(--space-4);
  transition: all var(--motion-fast) var(--ease-standard);
}

.dashboard-alert[data-tone="danger"] {
  background: color-mix(in srgb, var(--color-danger) 10%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-danger) 25%, var(--color-border-default));
  color: var(--color-danger);
}

.dashboard-alert[data-tone="warning"] {
  background: color-mix(in srgb, var(--color-warning) 10%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-warning) 25%, var(--color-border-default));
  color: var(--color-warning);
}

.dashboard-alert[data-tone="brand"] {
  background: color-mix(in srgb, var(--color-brand-primary) 10%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-brand-primary) 25%, var(--color-border-default));
  color: var(--color-brand-primary);
}

.dashboard-alert[data-tone="success"] {
  background: color-mix(in srgb, var(--color-success) 10%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-success) 25%, var(--color-border-default));
  color: var(--color-success);
}

/* Guiding Banner used in detail panels */
.guiding-banner {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-6);
  border: 1px solid var(--color-border-subtle);
}

.guiding-banner[data-tone="warning"] {
  background: color-mix(in srgb, var(--color-warning) 12%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-warning) 30%, var(--color-border-default));
}

.guiding-banner[data-tone="danger"] {
  background: color-mix(in srgb, var(--color-danger) 12%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-danger) 30%, var(--color-border-default));
}

.guiding-banner .gb-content {
  flex: 1;
}

.guiding-banner .gb-content strong {
  display: block;
  font: var(--font-title-sm);
  margin-bottom: 2px;
}

.guiding-banner .gb-content p {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
}

/* Rest of base styles (Original Content restored) */
.provider-card h3,
.capability-card h3,
.scene-card h3 {
  margin: 0 0 4px;
}

.dashboard-list__item p,
.provider-card p,
.capability-card p,
.scene-card p {
  margin: 0;
}

.dashboard-list__action,
.settings-page__button {
  align-items: center;
  border-radius: 999px;
  cursor: pointer;
  display: inline-flex;
  font: inherit;
  font-weight: 700;
  justify-content: center;
  line-height: 1;
  min-height: 42px;
  padding: 12px 18px;
  transition: transform var(--motion-fast) ease, box-shadow var(--motion-fast) ease, border-color var(--motion-fast) ease;
}

.settings-page__button {
  background: linear-gradient(135deg, var(--brand-primary), #9cffdf);
  border: 0;
  box-shadow: 0 14px 30px rgba(0, 242, 234, 0.2);
  color: #042a2a;
}

.settings-page__button--secondary,
.dashboard-list__action {
  background: color-mix(in srgb, var(--surface-secondary) 90%, transparent);
  border: 1px solid var(--border-default);
  box-shadow: none;
  color: var(--text-primary);
}

.settings-page__button:hover,
.dashboard-list__action:hover {
  transform: translateY(-1px);
}

.settings-page__button:disabled,
.dashboard-list__action:disabled,
.settings-field input:disabled,
.settings-field select:disabled,
.settings-field textarea:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
}

.chain-rail {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
}

.chain-step {
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  display: grid;
  gap: var(--space-2);
  min-height: 164px;
  padding: var(--space-4);
  transition: border-color var(--motion-instant) var(--ease-standard), transform var(--motion-instant) var(--ease-spring);
}

.chain-step:hover {
  border-color: color-mix(in srgb, var(--brand-primary) 44%, var(--border-default));
  transform: translateY(-2px);
}

.chain-step span {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: 12px;
}

.chain-step p {
  margin: 0;
}

.settings-page__header--hero {
  background:
    radial-gradient(circle at top right, rgba(0, 242, 234, 0.16), transparent 32%),
    color-mix(in srgb, var(--surface-secondary) 88%, transparent);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
}

.settings-card {
  display: grid;
  gap: var(--space-4);
  min-height: auto;
}

.settings-field {
  color: var(--text-secondary);
  display: grid;
  font-size: 13px;
  gap: var(--space-2);
}

.settings-field input,
.settings-field select,
.settings-field textarea,
.editor-textarea {
  background: color-mix(in srgb, var(--surface-tertiary) 94%, transparent);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font: inherit;
  outline: none;
  padding: 12px 14px;
  transition: border-color var(--motion-fast) ease, box-shadow var(--motion-fast) ease;
}

.settings-field input:focus,
.settings-field select:focus,
.settings-field textarea:focus,
.editor-textarea:focus {
  border-color: color-mix(in srgb, var(--brand-primary) 58%, var(--border-default));
  box-shadow: 0 0 0 4px rgba(0, 242, 234, 0.12);
}

.editor-textarea {
  min-height: 220px;
  resize: vertical;
}

.editor-textarea--compact {
  min-height: 96px;
}

.settings-page__error {
  background: color-mix(in srgb, var(--status-error) 11%, var(--surface-secondary));
  border: 1px solid color-mix(in srgb, var(--status-error) 40%, var(--border-default));
  border-radius: var(--radius-lg);
  color: var(--status-error);
  margin: 0;
  padding: 13px 15px;
}

.empty-state {
  border-style: dashed;
  box-shadow: none;
  color: var(--text-secondary);
}

.capability-card,
.provider-card,
.scene-card {
  box-shadow: none;
  display: grid;
  gap: var(--space-4);
}

.capability-card__toggle {
  align-items: center;
  color: var(--text-secondary);
  display: inline-flex;
  font-size: 12px;
  gap: var(--space-2);
}

.workspace-page__header,
.editor-card__header,
.editor-card__actions {
  align-items: flex-start;
}

fieldset {
  border: 0;
  margin: 0;
}

@keyframes pulse-dot {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }

  50% {
    opacity: 0.55;
    transform: scale(0.82);
  }
}

@media (max-width: 1365px) {
  .app-shell__body {
    grid-template-columns: 240px minmax(0, 1fr);
  }

  .detail-panel {
    grid-column: 1 / -1;
  }

  .dashboard-hero,
  .chain-rail {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 959px) {
  .title-bar,
  .status-bar,
  .bootstrap-screen__actions,
  .settings-page__header,
  .settings-page__actions,
  .workspace-page__header,
  .editor-card__header,
  .editor-card__actions,
  .dashboard-list__item,
  .dashboard-metric,
  .capability-card__header {
    align-items: flex-start;
    flex-direction: column;
    gap: var(--space-3);
  }

  .app-shell__body,
  .placeholder-page__body,
  .settings-page__grid,
  .workspace-grid,
  .capability-grid,
  .provider-grid,
  .scene-grid,
  .dashboard-command-grid,
  .dashboard-hero,
  .chain-rail,
  .initialization-grid {
    grid-template-columns: 1fr;
  }

  .app-shell__body {
    padding: var(--space-3);
  }

  .dashboard-hero__orb {
    max-width: 240px;
  }

  .status-bar {
    align-items: flex-start;
  }
}

```

### apps/desktop/src/styles/icons.css

```css
@font-face {
  font-family: 'Material Symbols Outlined';
  font-style: normal;
  font-weight: 400;
  font-display: block;
  src:
    url('../assets/fonts/material-symbols.ttf') format('truetype'),
    local('Material Symbols Outlined'),
    local('MaterialSymbolsOutlined');
}

.material-symbols-outlined {
  font-family: 'Material Symbols Outlined', 'Material Icons Outlined', sans-serif;
  font-weight: normal;
  font-style: normal;
  font-size: 24px;
  line-height: 1;
  letter-spacing: normal;
  text-transform: none;
  display: inline-block;
  white-space: nowrap;
  word-wrap: normal;
  direction: ltr;
  -webkit-font-feature-settings: 'liga';
  -webkit-font-smoothing: antialiased;
}

```

### apps/desktop/src/styles/shell.css

```css
html,
body,
#app {
  height: 100%;
  margin: 0;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  width: 100%;
}

body {
  background: var(--color-bg-canvas);
  color: var(--color-text-primary);
}

.command-shell,
.command-shell * {
  box-sizing: border-box;
}

.command-content-host {
  min-width: 0;
  overflow-x: hidden;
  scrollbar-gutter: stable;
}

.command-content-host > * {
  min-height: 100%;
  min-width: 0;
  width: 100%;
}

::-webkit-scrollbar {
  height: 8px;
  width: 8px;
}

::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--text-tertiary) 48%, transparent);
  border-radius: var(--radius-full);
}

::-webkit-scrollbar-track {
  background: transparent;
}

```

