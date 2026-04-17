> ?????2026-04-17????????????????????????????????????

# 后端模块开发计划总览

**当前状态（2026-04-17）**: M05-M15 后端 V1 接口已全部落地，当前接口真源已统一到 `docs/RUNTIME-API-CALLS.md`。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**生成日期**: 2026-04-14  
**Codex 架构建议来源**: Session 019d8b55  
**工作目录**: `apps/py-runtime/src/`

---

## 后端技术约束（所有模块必须遵守）

```python
# 标准后端分层
routes/ → services/ → repositories/ → domain/models/
# 返回格式
{"ok": True, "data": ...}
{"ok": False, "error": "...", "error_code": "..."}
# 文件头
from __future__ import annotations
# 日志
log = logging.getLogger(__name__)
log.exception(...)  # 异常，不用 log.error(str(e))
# SQLite 优化
PRAGMA journal_mode=WAL
busy_timeout 配置
长任务进度 → WebSocket，不写高频 DB
```

---

## 长任务 vs 纯 CRUD 分类

### 🔄 必须长任务 + WebSocket
| 模块 | 长任务类型 |
|------|-----------|
| voice_studio | TTS 配音生成 |
| subtitle_alignment_center | 字幕生成 / 对齐 |
| render_export_center | FFmpeg 渲染 |
| publishing_center | 发布提交 |
| automation_console | 采集/回复/同步 |
| review_optimization_center | AI 建议生成 |
| video_deconstruction_center | 转写 / 切段 / 结构抽取 |
| ai_editing_workspace | AI 命令执行 |

### ✅ V1 可纯 CRUD
| 模块 | 简化方案 |
|------|---------|
| asset_library | 纯 CRUD + 文件存在性检查 |
| account_management | 纯 CRUD + 手工状态维护 |
| device_workspace_management | 目录检查 + 绑定 CRUD |

---

## WebSocket 事件格式标准

```json
{
  "type": "task.progress",
  "taskId": "xxx",
  "taskType": "tts_generation",
  "projectId": "xxx",
  "status": "running",
  "progress": 45,
  "message": "正在生成第 3/8 段..."
}
```

事件类型：`task.started` / `task.progress` / `task.log` / `task.completed` / `task.failed`

---

## 模块文档索引

| # | 模块 | 文档 | 优先级 | 当前状态（2026-04-17） |
|---|------|------|--------|------------------------|
| 1 | AI 剪辑工作台 | [B-M05-ai-editing-workspace.md](./B-M05-ai-editing-workspace.md) | P0 | 已完成（V1 时间线与 AI 命令闭环） |
| 2 | 视频拆解中心扩展 | [B-M06-video-deconstruction.md](./B-M06-video-deconstruction.md) | P1 | 已完成（V1 导入/转写/切段/结构抽取/脚本落地闭环） |
| 3 | 配音中心 | [B-M07-voice-studio.md](./B-M07-voice-studio.md) | P1 | 已完成（V1 配音轨与 blocked 生成闭环） |
| 4 | 字幕对齐中心 | [B-M08-subtitle-alignment.md](./B-M08-subtitle-alignment.md) | P1 | 已完成（V1 字幕生成与编辑闭环） |
| 5 | 资产中心 | [B-M09-asset-library.md](./B-M09-asset-library.md) | P1 | 已完成（V1 资产导入与引用闭环） |
| 6 | 渲染导出中心 | [B-M14-render-export.md](./B-M14-render-export.md) | P1 | 已完成（V1 渲染任务与导出配置闭环） |
| 7 | 账号管理 | [B-M10-account-management.md](./B-M10-account-management.md) | P2 | 已完成（V1 账号、分组、状态刷新闭环） |
| 8 | 设备工作区 | [B-M11-device-workspace.md](./B-M11-device-workspace.md) | P2 | 已完成（V1 工作区、浏览器实例、绑定闭环） |
| 9 | 自动化中心 | [B-M12-automation-console.md](./B-M12-automation-console.md) | P2 | 已完成（V1 自动化任务、运行记录、日志闭环） |
| 10 | 发布中心 | [B-M13-publishing-center.md](./B-M13-publishing-center.md) | P2 | 已完成（V1 发布计划、预检、提交、回执闭环） |
| 11 | 复盘中心 | [B-M15-review-optimization.md](./B-M15-review-optimization.md) | P3 | 已完成（V1 摘要、建议、脚本应用闭环） |
