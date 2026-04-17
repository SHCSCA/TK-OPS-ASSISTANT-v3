# TK-OPS 前端模块开发计划总览

**当前状态（2026-04-17）**: 11 个业务模块页均已落地到 `apps/desktop/src/pages/`，其中 M05 / M07 / M08 / M09 已完成首轮闭环，其余模块已有基础待扩展。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**生成日期**: 2026-04-14  
**工作目录**: `apps/desktop/src/pages/`

---

## 开发范围

11 个业务模块页均已创建并接入当前壳层、路由与 Runtime 客户端；状态以“已完成 / 已有基础待扩展 / 待开发”为准。

---

## 优先级与模块清单

| 序号 | 模块文档 | Route ID | 文件路径 | 优先级 | 状态 |
|------|---------|----------|---------|--------|------|
| 1 | [M05-ai-editing-workspace.md](./modules/M05-ai-editing-workspace.md) | `ai_editing_workspace` | `pages/workspace/` | P0 | 已完成 |
| 2 | [M06-video-deconstruction-center.md](./modules/M06-video-deconstruction-center.md) | `video_deconstruction_center` | `pages/video/` | P1（扩展） | 已有基础待扩展 |
| 3 | [M07-voice-studio.md](./modules/M07-voice-studio.md) | `voice_studio` | `pages/voice/` | P1 | 已完成 |
| 4 | [M08-subtitle-alignment-center.md](./modules/M08-subtitle-alignment-center.md) | `subtitle_alignment_center` | `pages/subtitles/` | P1 | 已完成 |
| 5 | [M09-asset-library.md](./modules/M09-asset-library.md) | `asset_library` | `pages/assets/` | P1 | 已完成 |
| 6 | [M14-render-export-center.md](./modules/M14-render-export-center.md) | `render_export_center` | `pages/renders/` | P1 | 已有基础待扩展 |
| 7 | [M10-account-management.md](./modules/M10-account-management.md) | `account_management` | `pages/accounts/` | P2 | 已有基础待扩展 |
| 8 | [M11-device-workspace-management.md](./modules/M11-device-workspace-management.md) | `device_workspace_management` | `pages/devices/` | P2 | 已有基础待扩展 |
| 9 | [M12-automation-console.md](./modules/M12-automation-console.md) | `automation_console` | `pages/automation/` | P2 | 已有基础待扩展 |
| 10 | [M13-publishing-center.md](./modules/M13-publishing-center.md) | `publishing_center` | `pages/publishing/` | P2 | 已有基础待扩展 |
| 11 | [M15-review-optimization-center.md](./modules/M15-review-optimization-center.md) | `review_optimization_center` | `pages/review/` | P3 | 已有基础待扩展 |

---

## 设计系统快查

```css
/* 品牌色 */
--brand-primary: #00F2EA;

/* Surface */
--surface-primary: #F5F8F8;     /* Dark: #0F2323 */
--surface-secondary: #FFFFFF;   /* Dark: #0F172A */
--surface-tertiary: #F8FAFC;    /* Dark: #1E293B */
--surface-sunken: #F1F5F9;      /* Dark: #16212F */

/* Text */
--text-primary: #0F172A;        /* Dark: #F1F5F9 */
--text-secondary: #64748B;      /* Dark: #94A3B8 */

/* Status */
--status-success: #10B981;
--status-warning: #F59E0B;
--status-error: #EF4444;

/* Motion */
--motion-fast: 160ms;
--motion-base: 220ms;
--motion-slow: 320ms;
--ease-out: cubic-bezier(0.2, 0.8, 0.2, 1);
```

---

## Gemini 设计建议摘要

来源：2026-04-14 Gemini 设计咨询（Session: 97d555bd）

### 全局建议
- AI 处理中使用 `brand.primary` 呼吸/扫描线动效
- Dark 模式下 `brand.primary` 增加 `drop-shadow(0 0 8px #00F2EA4D)` 发光效果
- 所有面板开合使用 `transition: all var(--motion-base) var(--ease-out)`

### 页面特有建议（Gemini 精华）
- **AI 剪辑工作台**：拖拽素材磁吸效果 + 波形同轴显示
- **配音中心**：TTS 生成时文字下方波形生长动画
- **字幕对齐**：双向锚定（点文字→预览跳转，反向亦然）
- **资产中心**：悬浮静默预览（hover 500ms 延迟）
- **渲染中心**：进度条 shimmer + 完成瞬间绿色 pulse
- **账号管理**：在线账号头像呼吸圈 + 同步卡片3D翻转
- **复盘中心**：Bento Grid + AI 建议卡毛玻璃效果

---

## Gemini 执行策略

按模块优先级逐一派发 Gemini 执行，建议顺序：

1. **批次一（P0）**：M05 AI 剪辑工作台
2. **批次二（P1 并行）**：M07 配音中心 + M08 字幕对齐中心
3. **批次三（P1 并行）**：M09 资产中心 + M14 渲染导出中心
4. **批次四（P1 扩展）**：M06 视频拆解中心扩展
5. **批次五（P2 并行）**：M10 账号管理 + M11 设备工作区
6. **批次六（P2 并行）**：M12 自动化中心 + M13 发布中心
7. **批次七（P3）**：M15 复盘与优化中心

---

## 共用 CSS 类约定

| 类名 | 用途 |
|------|------|
| `.workspace-page` | 页面根容器 |
| `.workspace-page__header` | 页头（标题+芯片） |
| `.workspace-grid` | 双栏或多栏网格 |
| `.editor-card` | 内容区块卡片 |
| `.editor-card__header` | 卡片头（标题+操作） |
| `.command-panel` | 命令/操作面板 |
| `.page-chip` | 页面状态芯片 |
| `.settings-page__button` | 主要操作按钮 |
| `.settings-page__error` | 错误提示文本 |
