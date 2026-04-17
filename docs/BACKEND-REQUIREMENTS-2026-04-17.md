# TK-OPS 后端开发需求 v2026.04.17

> 本文件是 UI 蓝图（`docs/UI-BLUEPRINT-2026-04-17.md`）的后端对偶物。
> 它回答一个问题：**现在的 `apps/py-runtime` 距离支撑 16 页蓝图还差什么？**
>
> 结构：方法论 → 全局新增需求 → 16 页逐页缺口 → 任务拆分与排期。
> 输出形态：**清单 + 缺口级别**，不重复已有接口的详尽定义（那放在 `docs/RUNTIME-API-CALLS.md`）。
>
> 文档优先级：`docs/PRD.md` > `docs/RUNTIME-API-CALLS.md` > 本文。接口契约真源始终是 `RUNTIME-API-CALLS.md`，本文驱动它的更新。

---

## 目录

- 0 · 方法论与缺口级别
- 1 · 全局新增需求（跨 16 页共用）
- 2 · 16 页逐页缺口矩阵
- 3 · WebSocket 消息协议全量（Task Bus）
- 4 · 数据模型扩展（Schema / 迁移）
- 5 · 任务拆解与排期
- 6 · 验收标准
- 附录 A · 现状清单（Runtime 已有 Router / Service / Schema）
- 附录 B · 前端契约清单（每页一组函数名）

---

## 0 · 方法论与缺口级别

### 0.1 对比方法

把 16 页蓝图逐行扫描，对照 `apps/py-runtime/src/api/routes/` 下每个 Router 的实际实现，按以下三档判定：

| 级别 | 图例 | 判据 | 动作 |
| --- | --- | --- | --- |
| **D1 完整** | ● | Router + Service + Schema + 文档 § 齐备 | 仅做兼容性检查 |
| **D2 骨架就绪 · 需补字段** | ◐ | Router 存在但字段不全 / 与蓝图列需求不匹配 | 扩字段 + 补文档 |
| **D3 有 Router 但无文档** | ◑ | 路由存在但未进入 `RUNTIME-API-CALLS.md` | 补文档（接口契约落档） |
| **D4 需新增** | ○ | 完全缺失 | 新建 Schema/Service/Route + 文档 |

### 0.2 全局硬约束（CLAUDE.md 与 PRD 已规定，本文再次强调）

1. **信封**：全部走 `schemas/envelope.py` 的 `ok_response` / `error_response`。错误 `error` 必须是中文可见、可恢复提示，不暴露 traceback。
2. **分层**：路由 → 服务 → 仓储 → 任务/媒体/AI，单向。路由层不编排业务。
3. **日志**：模块级 `log = logging.getLogger(__name__)`，异常用 `log.exception(...)`。
4. **长任务**：> 2s 的一律走 TaskBus + WebSocket，禁止同步阻塞 HTTP。
5. **WebSocket**：消息带 `schema_version`，字段变更走兼容流程。
6. **配置总线**：新增配置先过 `system_config_repository` + `settings_service`，不能散落在业务 service 内。
7. **前端不得直拼 URL**：所有接口先进 `apps/desktop/src/app/runtime-client.ts`。
8. **文档**：任何接口变更必须同一次提交更新 `docs/RUNTIME-API-CALLS.md`。

---

## 1 · 全局新增需求（跨 16 页共用）

这一节的需求不属于任何单页，但被多页消费，必须先落地。

### 1.1 全局搜索（Cmd+K） — **● D1 已完成（2026-04-17）**

**驱动**：UI 蓝图 § 3.2（Title Bar 全局搜索框）。

**需求**：
- 一次调用聚合返回 `projects` / `scripts` / `tasks` / `assets` / `accounts` / `workspaces` 六类结果，每类 ≤ 5 条
- 支持中文模糊匹配（`LIKE` 即可，V1 无需全文索引）
- 响应时间 ≤ 120ms（本地 SQLite，若超时按类降级）

**接口（新增）**：
```
GET /api/search?q=<keyword>&types=projects,scripts,assets,...&limit=5
→ 200 { ok:true, data: {
    projects: [{ id, name, subtitle, updatedAt }],
    scripts:  [{ id, projectId, title, snippet, updatedAt }],
    tasks:    [{ id, type, label, status, updatedAt }],
    assets:   [{ id, name, type, thumbnailUrl, updatedAt }],
    accounts: [{ id, name, status }],
    workspaces: [{ id, name, status }]
  } }
```

**落地位置**：
- Route：`api/routes/search.py`（新建）
- Service：`services/search_service.py`（新建，调用各 repository）
- Schema：`schemas/search.py`（新建）

### 1.2 Runtime 健康聚合（增强 `/api/settings/health`） — **● D1 已完成（2026-04-17）**

**驱动**：蓝图 § 3.2 Title Bar 状态区、§ 3.6 Status Bar、Dashboard 健康卡。

**现状**：`GET /api/settings/health` 已存在，但字段不足以驱动蓝图三处。

**需补字段**：
```typescript
interface RuntimeHealthSnapshot {
  runtime: { status: 'ok'|'degraded'|'down', port: number, uptimeMs: number, version: string };
  aiProvider: { status, latencyMs: number, providerId: string, providerName: string, lastChecked: string };
  renderQueue: { running: number, queued: number, avgWaitMs: number | null };
  publishingQueue: { pendingToday: number, failedToday: number };
  taskBus: { running: number, queued: number, blocked: number, failed24h: number };
  license: { status: 'active'|'expired'|'grace'|'missing', expiresAt: string | null };
  lastSyncAt: string;  // UI 右下 "最近同步"
}
```

### 1.3 Dashboard 聚合（增强 `/api/dashboard/summary`） — **● D1 已完成（2026-04-17）**

**驱动**：蓝图 § 5.2（Hero + 待办 + 异常 + 健康三卡）。

**现状**：`GET /api/dashboard/summary` 已存在但返回字段不足。

**需补字段**：
```typescript
interface DashboardSummary {
  greeting: { timeOfDay: 'morning'|'afternoon'|'evening'|'night', userLabel: string };
  heroContext: {
    currentProject: { id, name, lastEditedAt, status } | null;
    todayPendingPublish: number;
    todayPendingScripts: number;
    primaryCTA: { label: string, action: 'continue-editing'|'new-project'|'resume-task', targetId?: string };
  };
  recentProjects: ProjectSummaryDto[];        // ≤ 8 条
  todos: TodoItemDto[];                       // ≤ 10 条，按优先级
  exceptions: ExceptionItemDto[];             // ≤ 10 条
  health: {
    aiProvider: { latencyMs, delta24hPct };
    renderQueue: { running, queued, etaMinutes };
    publishingToday: { success, total, successRatePct };
  };
  generatedAt: string;
}
```

### 1.4 任务中心统一接口 — **◐ D2 基础已完成，聚合范围待继续扩展**

**驱动**：蓝图 § 3.6 Status Bar 任务计数、Dashboard 运行统计、工作台底部运行栏、自动化/渲染/发布/AI 任务统一视图。

**现状**：`GET /api/tasks` 已存在，但未统一所有异步任务来源（采集/发布/渲染/AI 生成/视频导入等目前分散在各 service 独立存储）。

**需求**：
- 所有异步任务必须注册到 `task_manager`，通过 `GET /api/tasks` 可统一列出
- 支持筛选：`?type=render|publish|automation|ai-generate|video-import&status=running,queued`
- 响应每项包含：`id / type / label / status / progressPct / startedAt / etaMs / projectId? / ownerRef`

### 1.5 项目上下文（新增） — **● D1 已完成（2026-04-17）**

**驱动**：蓝图 Title Bar "当前项目" 徽章、创作主链所有页面都需要"当前项目" 语义。

**现状**：`GET/PUT /api/dashboard/context` 已存在。

**需补**：
- `PUT` 的 schema 允许清空（`projectId: null` → 进入"未选择项目"态）
- WebSocket 广播 `context.project.changed` 消息，让所有已打开页面刷新

### 1.6 配置总线 WebSocket 广播 — **● D1 已完成（2026-04-17）**

**驱动**：蓝图设置页改动后，其他页面（如工作台、Dashboard）需实时感知主题/AI Provider 变更。

**需求**：
- `PUT /api/settings/config` 和 `PUT /api/settings/ai-capabilities` 成功后广播 `config.changed` / `ai-capability.changed`
- 前端 `config-bus` store 订阅后刷新本地缓存

### 1.7 统一错误码表 — **◐ D2 基础已完成，错误码清单待持续扩充**

**驱动**：蓝图所有错误态都要带 `error_code` 用于前端中文提示路由。

**需求**：在 `schemas/envelope.py` 扩展 `error_response(code=...)`，并在 `docs/RUNTIME-API-CALLS.md` 新增 § 错误码表。**先落地清单，不改既有接口**：

| error_code | 触发场景 | 建议中文提示 |
| --- | --- | --- |
| `license.not-activated` | 未激活访问受限能力 | 许可证未激活，请先完成激活 |
| `license.expired` | 授权过期 | 许可证已过期，请续期 |
| `runtime.port-occupied` | 8000 端口被占 | Runtime 启动失败，请检查端口占用 |
| `runtime.not-ready` | 调用发生在健康检查通过前 | Runtime 正在启动，请稍后重试 |
| `project.not-found` | projectId 不存在 | 项目不存在或已被删除 |
| `project.not-selected` | 未选当前项目调用项目级接口 | 请先选择或创建项目 |
| `ai.provider.not-configured` | 能力对应 Provider 未配置 | 未配置 AI Provider，请先在系统设置中选择 |
| `ai.provider.unreachable` | 外部 Provider 超时 | AI 服务暂时不可用，已切换到备用 |
| `ai.quota.exhausted` | 额度耗尽 | AI 额度已用完，请检查账户 |
| `asset.in-use` | 删除被引用资产 | 资产被项目引用，请先移除引用 |
| `asset.file-missing` | 本地文件丢失 | 资产文件已丢失，请重新导入 |
| `task.blocked-dependency` | 前置任务未完成 | 需要先完成前置任务 |
| `workspace.timeline-missing` | 未创建时间线访问工作台 | 请先创建时间线草稿 |
| `import.ffprobe-failed` | 探测视频元信息失败 | 视频文件损坏或格式不支持 |
| `publish.precheck-failed` | 发布预检未通过 | 预检未通过，请修复冲突后重试 |
| `publish.account-unbound` | 发布账号未绑定设备 | 账号未绑定设备工作区 |
| `device.offline` | 目标设备离线 | 目标设备不在线，请先上线 |
| `device.browser-missing` | 浏览器实例缺失 | 未找到可用的浏览器实例 |

---

## 2 · 16 页逐页缺口矩阵

缺口矩阵采用紧凑表格：**蓝图需求 / 现有代码 / 缺口 / 落地点 / 优先级**。详尽 DTO 与接口定义在接口文档中新增章节（见 § 5 排期）。

### 2.1 `setup_license_wizard` — 首启与许可证向导

| 状态 | 模块 |
| --- | --- |
| ● | License 激活（`/api/license/status`、`/api/license/activate`） |
| ● | Runtime 健康检查（`/api/settings/health`） |
| ● | 首次目录初始化：已补 `POST /api/bootstrap/initialize-directories`，按 settings/config 与 runtime data root 创建并返回权限检查结果 |
| ◑ | 首次 AI Provider 快速配置：复用 `PUT /api/settings/ai-capabilities` 即可，但需文档化"空配置 → 首 Provider 引导"路径 |
| ● | 聚合自检：已补 `POST /api/bootstrap/runtime-selfcheck`，覆盖端口、版本、依赖、数据库可访问性 |

**缺口清单**：
- 首次 AI Provider 快速配置文档化路径 · **D3** · 复用 `PUT /api/settings/ai-capabilities`，补首配引导说明即可。

### 2.2 `creator_dashboard` — 创作总览

| 状态 | 模块 |
| --- | --- |
| ● | `/api/dashboard/summary` 已按 B-S1 扩展为完整聚合（见 `docs/RUNTIME-API-CALLS.md`） |
| ● | `/api/dashboard/context` GET/PUT |
| ● | `POST /api/dashboard/projects` 新建项目 |
| ◑ | `GET /api/projects/{id}` 项目详情（当前分散在 script/storyboard/workspace 中各自 project，需统一） |
| ○ | `GET /api/projects/{id}/quick-jump` — Hero "继续创作" 的智能下一步 action（当前 / 下一个未完成阶段） |

**缺口清单**：
- 扩 `DashboardSummary` 字段（§ 1.3） · **已完成**
- 新增 `GET /api/projects/{id}/quick-jump` · **D4** · 返回 `{ stage: 'script'|'storyboard'|'workspace'|'voice'|'subtitle'|'render'|'publish', targetId, reason }`

### 2.3 `script_topic_center` — 脚本与选题中心

| 状态 | 模块 |
| --- | --- |
| ◑ | `GET/PUT /api/scripts/projects/{id}/document` · 存在但文档未覆盖 |
| ◑ | `POST /api/scripts/projects/{id}/generate` · 存在 |
| ◑ | `POST /api/scripts/projects/{id}/rewrite` · 存在 |
| ○ | 标题变体：`POST /api/scripts/projects/{id}/title-variants` · 缺 |
| ○ | 文案版本：`GET /api/scripts/projects/{id}/versions` / `POST .../versions/{v}/restore` · 缺 |
| ○ | 段落级 AI 改写（带 Prompt 模板）：`POST /api/scripts/projects/{id}/segments/{segId}/rewrite` · 缺 |
| ○ | Prompt 模板管理：`GET/POST/PUT/DELETE /api/prompt-templates` · 缺 |
| ○ | AI 流式输出 WebSocket 协议（`script.ai.stream`） · 缺（蓝图 § 5.3 B 区动效依赖） |

**缺口清单（按优先级）**：
1. `POST /api/scripts/projects/{id}/title-variants`（输入 topic+count → 输出数组）· **D4** · P0
2. `GET /api/scripts/projects/{id}/versions` / `POST .../restore/{versionId}` · **D4** · P0
3. AI 流式输出 WebSocket 事件 `script.ai.stream`（分帧文本 / 进度 / 完成 / 错误）· **D4** · P0
4. `POST /api/scripts/projects/{id}/segments/{segId}/rewrite`（段落级改写）· **D4** · P1
5. Prompt 模板 CRUD · **D4** · P1

### 2.4 `storyboard_planning_center` — 分镜规划中心

| 状态 | 模块 |
| --- | --- |
| ◑ | `GET/PUT /api/storyboards/projects/{id}/document` · 存在 |
| ◑ | `POST /api/storyboards/projects/{id}/generate` · 存在 |
| ○ | 镜头级 CRUD：`POST/PATCH/DELETE /api/storyboards/{id}/shots/{shotId}` · 缺 |
| ○ | 节奏模板：`GET /api/storyboards/templates` · 缺 |
| ○ | 脚本 ↔ 分镜双向引用：`POST /api/storyboards/projects/{id}/sync-from-script` · 缺（脚本变更后同步） |

**缺口清单**：
1. 镜头级 CRUD · **D4** · P0
2. 节奏模板只读接口（内置 + 用户自定义） · **D4** · P1
3. 脚本变更联动分镜刷新 · **D4** · P1

### 2.5 `ai_editing_workspace` — AI 剪辑工作台 ★

| 状态 | 模块 |
| --- | --- |
| ● | 时间线 CRUD（`/api/workspace/.../timeline` GET/POST/PATCH）· 已文档化 |
| ◐ | AI 命令入口已存在但仅返回 `blocked`，需扩展 |
| ○ | 片段详情：`GET /api/workspace/clips/{clipId}` · 缺（蓝图 Detail Panel 依赖） |
| ○ | 片段替换/移动/裁剪原子操作 · 当前仅整表 PATCH |
| ○ | 预览信息：`GET /api/workspace/timelines/{id}/preview` 返回低清代理帧 URL · 缺 |
| ○ | 渲染预检：`POST /api/workspace/timelines/{id}/precheck` · 缺 |

**缺口清单（按优先级）**：
1. `GET /api/workspace/clips/{clipId}` 单片段详情（含来源、Prompt、分辨率、可编辑字段） · **D4** · P0
2. 片段原子操作：`POST .../clips/{id}/move` / `POST .../clips/{id}/trim` / `POST .../clips/{id}/replace` · **D4** · P0
3. AI 命令（生成镜头 / 替换旁白 / 重对齐字幕）落地为真实任务：扩 `workspace_service.ai_command` 到 TaskBus · **D2→D1** · P1
4. 预览代理帧 URL（基于 `media/` 层 FFmpeg） · **D4** · P1
5. 渲染预检接口 · **D4** · P1

### 2.6 `video_deconstruction_center` — 视频拆解中心

| 状态 | 模块 |
| --- | --- |
| ◑ | `POST /api/video-deconstruction/projects/{id}/import` 已存在 |
| ◑ | `GET /api/video-deconstruction/projects/{id}/videos` |
| ◑ | `DELETE /api/video-deconstruction/videos/{id}` |
| ○ | 阶段状态：`GET /api/video-deconstruction/videos/{id}/stages` 返回 4 阶段（转写/切段/镜头识别/脚本抽取）进度 · 缺 |
| ○ | 阶段局部重跑：`POST .../videos/{id}/stages/{stageId}/rerun` · 缺 |
| ○ | 拆解结果浏览：`GET .../videos/{id}/transcript` / `.../segments` / `.../shots` · 缺 |
| ○ | 改写入口：`POST .../videos/{id}/adopt-to-project`（一键回流脚本） · 缺 |
| ○ | WebSocket 阶段事件 `video.import.stage.*` · 文档已提到但需落档 |

**缺口清单**：
1. 阶段状态 & 结果浏览接口 · **D4** · P0
2. 阶段局部重跑 · **D4** · P0
3. 一键回流到脚本/分镜 · **D4** · P1

### 2.7 `voice_studio` — 配音中心

| 状态 | 模块 |
| --- | --- |
| ● | 基本 Voice CRUD 已文档化（`§ 5` in RUNTIME-API-CALLS） |
| ○ | 音色库管理（自定义音色）：`POST /api/voice/profiles` · 缺 |
| ○ | 段落级重生成：`POST /api/voice/tracks/{id}/segments/{segId}/regenerate` · 缺 |
| ○ | 波形数据：`GET /api/voice/tracks/{id}/waveform` · 缺（前端波形图渲染用） |

### 2.8 `subtitle_alignment_center` — 字幕对齐中心

| 状态 | 模块 |
| --- | --- |
| ● | 基本 Subtitle CRUD 已文档化 |
| ○ | 手动对齐接口：`POST /api/subtitles/tracks/{id}/align`（给定时间码覆盖 AI 对齐） · 缺 |
| ○ | 样式模板：`GET /api/subtitles/style-templates` · 缺 |
| ○ | 导出：`POST /api/subtitles/tracks/{id}/export`（SRT/VTT/ASS） · 缺 |

### 2.9 `asset_library` — 资产中心

| 状态 | 模块 |
| --- | --- |
| ● | Asset CRUD + 引用 已文档化 |
| ○ | 缩略图生成：当前无任务；资产导入后需异步生成缩略图 → 走 TaskBus · 缺 |
| ○ | 批量操作：`POST /api/assets/batch-delete` / `batch-move-group` · 缺 |
| ○ | 分组管理：`GET/POST/PATCH/DELETE /api/assets/groups` · 缺 |

### 2.10 `account_management` — 账号管理

| 状态 | 模块 |
| --- | --- |
| ◑ | Account / AccountGroup CRUD 全部有 Router 但未进入 `RUNTIME-API-CALLS.md` |
| ◑ | `POST /api/accounts/{id}/refresh-stats` · 存在 |
| ○ | 账号状态 WebSocket 广播 `account.status.changed` · 缺 |
| ○ | 绑定关系：`PUT /api/accounts/{id}/binding`（工作区+浏览器实例） · 缺 |
| ○ | 敏感信息脱敏（Cookie/Token 只返回 maskedXxx） · 当前需核对 |

### 2.11 `device_workspace_management` — 设备与工作区

| 状态 | 模块 |
| --- | --- |
| ◑ | `/api/devices/workspaces` CRUD 存在 · 未进入文档 |
| ◑ | `POST .../health-check` 存在 |
| ○ | 浏览器实例子资源：`GET/POST/DELETE /api/devices/workspaces/{id}/browsers` · 缺 |
| ○ | 实时运行日志：WebSocket `device.log` 或 `GET .../logs?since=<cursor>` · 缺 |

### 2.12 `automation_console` — 自动化执行中心

| 状态 | 模块 |
| --- | --- |
| ◑ | Automation Tasks CRUD + 手动触发 + 运行历史 · 存在未文档化 |
| ○ | 规则配置：当前作为 `rule` JSON 字段存，需定义结构化 schema（采集/回复/同步/校验四类） · 缺 |
| ○ | 暂停/恢复：`POST .../{id}/pause` / `.../{id}/resume` · 缺 |

### 2.13 `publishing_center` — 发布中心

| 状态 | 模块 |
| --- | --- |
| ◑ | PublishPlan CRUD + precheck + submit + cancel 存在 · 未文档化 |
| ○ | 日历聚合：`GET /api/publishing/calendar?from=YYYY-MM-DD&to=YYYY-MM-DD` · 缺 |
| ○ | 冲突检测：当前在 `precheck` 内，需把冲突项结构化返回 · 缺 |
| ○ | 回执追踪：`GET .../plans/{id}/receipts` · 缺 |

### 2.14 `render_export_center` — 渲染与导出中心

| 状态 | 模块 |
| --- | --- |
| ◑ | Render Tasks CRUD + cancel · 存在未文档化 |
| ○ | 导出模板：`GET /api/renders/templates` · 缺 |
| ○ | 资源占用：`GET /api/renders/resource-usage`（CPU / GPU / disk） · 缺 |
| ○ | 失败重试：`POST /api/renders/tasks/{id}/retry` · 缺 |
| ○ | WebSocket 进度事件 `render.progress` · 缺 |

### 2.15 `review_optimization_center` — 复盘与优化中心

| 状态 | 模块 |
| --- | --- |
| ◑ | `/api/review/projects/{id}/summary` GET/PATCH · 存在未文档化 |
| ◑ | `POST /api/review/projects/{id}/analyze` · 存在未文档化 |
| ○ | AI 建议回流：`POST /api/review/projects/{id}/suggestions/{sid}/adopt` → 新建子项目 · 缺 |

### 2.16 `ai_system_settings` — AI 与系统设置

| 状态 | 模块 |
| --- | --- |
| ● | 全部主要接口已文档化（§ 8） |
| ● | 日志查询：`GET /api/settings/logs?kind=system|business|task|ai|audit&since=<ts>` 已完成，当前读取 `runtime.jsonl` |
| ● | 一键导出诊断包：`POST /api/settings/diagnostics/export` 已完成，返回诊断 zip 路径与条目清单 |

---

## 3 · WebSocket 消息协议全量（Task Bus）

全局单通道：`WS /api/ws`，每条消息 JSON，必须带 `schema_version: 1` + `type` + `payload`。

### 3.1 消息类型总表

| type | 触发 | payload 字段 | 消费方 |
| --- | --- | --- | --- |
| `runtime.health.changed` | Runtime 健康状态变化 | `RuntimeHealthSnapshot` | Title Bar / Status Bar / Dashboard |
| `config.changed` | 系统配置保存 | `{ section: 'general'|'ai'|'directory', changedKeys: [] }` | `config-bus` 全局刷新 |
| `ai-capability.changed` | AI 能力/Provider 变更 | `AICapabilitySettings` | Settings 页、AI 按钮可用性 |
| `context.project.changed` | 当前项目切换 | `{ projectId, projectName }` | 所有页面清理/加载上下文 |
| `task.created` | 新任务入队 | `TaskDto`（见 § 4.3） | Status Bar 计数、任务中心 |
| `task.progress` | 任务进度推进（节流 500ms） | `{ taskId, progressPct, etaMs, message? }` | 进度条、工作台 AI 栏 |
| `task.succeeded` | 任务成功 | `{ taskId, result: unknown }` | Toast + 任务中心 |
| `task.failed` | 任务失败 | `{ taskId, errorCode, errorMessage, retryable }` | Toast + 异常队列 |
| `task.cancelled` | 任务被取消 | `{ taskId }` | 任务中心 |
| `task.blocked` | 任务被前置依赖或配置阻塞 | `{ taskId, reason, hint }` | 工作台提示 |
| `render.progress` | 渲染任务专用（带码率/已输出时长） | `{ taskId, progressPct, bitrateKbps, outputSec }` | 渲染中心 |
| `video.import.stage.started` | 视频导入阶段启动 | `{ videoId, stage, startedAt }` | 拆解中心 |
| `video.import.stage.progress` | 阶段进度 | `{ videoId, stage, progressPct }` | 拆解中心 |
| `video.import.stage.completed` | 阶段完成 | `{ videoId, stage, resultSummary }` | 拆解中心 |
| `video.import.stage.failed` | 阶段失败 | `{ videoId, stage, errorCode, errorMessage }` | 拆解中心 |
| `script.ai.stream.chunk` | 脚本 AI 流式输出 | `{ jobId, sequence, deltaText }` | 脚本编辑器 |
| `script.ai.stream.completed` | 流结束 | `{ jobId, fullText, versionId }` | 脚本编辑器 |
| `script.ai.stream.failed` | 流失败 | `{ jobId, errorCode, errorMessage }` | 脚本编辑器 |
| `voice.generate.progress` | 配音生成段进度 | `{ trackId, segmentIndex, progressPct }` | 配音中心 |
| `subtitle.align.progress` | 字幕对齐进度 | `{ trackId, progressPct, currentSegment }` | 字幕中心 |
| `publish.receipt.updated` | 发布回执更新 | `{ planId, status, platformResponse }` | 发布中心 |
| `device.status.changed` | 设备/工作区状态变更 | `{ workspaceId, status, lastSeenAt }` | 设备页、账号页 |
| `account.status.changed` | 账号状态变更 | `{ accountId, status, lastSyncedAt }` | 账号页、发布预检 |

### 3.2 兼容发布流程

- **新增字段**：向后兼容，直接发布；前端收到未知字段时忽略
- **删除字段**：先发"废弃候选"版本（保留字段 + 日志提示），一个工程版本后才真正移除
- **重命名字段**：等同于"新增 + 删除"，两个版本跨度
- **消息类型重命名**：源类型标 `deprecated:true` 一个版本，之后移除

---

## 4 · 数据模型扩展（Schema / 迁移）

### 4.1 现状（domain/models）

```
account / ai_capability / ai_job / asset / automation / base /
device_workspace / execution / imported_video / license / project /
publishing / render / review / script / storyboard / system_config / timeline
```

主链模型齐备，但以下字段需补：

### 4.2 需新增字段/表

| 模型 | 动作 | 字段 | 用途 |
| --- | --- | --- | --- |
| `script` | 新表 `script_version` | `id / scriptId / version / content / createdAt / source: 'user'|'ai' / aiModel?` | 支持版本列表与回退（§ 2.3） |
| `script` | 新表 `script_title_variant` | `id / projectId / title / tone / createdAt / adopted: bool` | 标题变体（§ 2.3） |
| `prompt_template` | 新表 | `id / kind / name / template / variables(jsonb) / createdAt / updatedAt` | Prompt 模板（§ 2.3） |
| `storyboard` | 新表 `storyboard_shot` | `id / storyboardId / orderIndex / prompt / durationMs / thumbnailAssetId? / scriptSegmentId? / notes` | 镜头级 CRUD（§ 2.4） |
| `timeline` | 现表扩字段 | `previewProxyUrl? / precheckResultJson?` | 工作台预览与预检（§ 2.5） |
| `imported_video` | 现表扩字段 | `stagesJson: {transcription, segmentation, shotDetection, scriptExtraction}` | 阶段状态（§ 2.6） |
| `asset` | 新表 `asset_group` | `id / name / parentId? / createdAt` | 资产分组（§ 2.9） |
| `asset` | 现表扩字段 | `thumbnailPath? / thumbnailGeneratedAt?` | 缩略图（§ 2.9） |
| `publishing` | 新表 `publish_receipt` | `id / planId / platformResponseJson / receivedAt / status` | 回执追踪（§ 2.13） |
| `device_workspace` | 新表 `browser_instance` | `id / workspaceId / kind / cookiesPath? / lastSeenAt` | 浏览器实例（§ 2.11） |
| `review` | 新表 `review_suggestion` | `id / projectId / category / content / adopted: bool / adoptedAsProjectId?` | AI 建议回流（§ 2.15） |
| `log_entry` | 新表 | `id / timestamp / kind / level / message / contextJson` | 日志查询（§ 2.16） |
| `error_code` | 常量表（无需 DB）| 在 `schemas/error_codes.py` 定义 Enum | 全局错误码（§ 1.7） |

### 4.3 统一 TaskDto

```typescript
type TaskKind =
  | 'render' | 'publish' | 'automation'
  | 'ai-script' | 'ai-storyboard' | 'ai-video' | 'ai-voice' | 'ai-subtitle'
  | 'video-import' | 'asset-thumbnail' | 'search-index';

interface TaskDto {
  id: string;
  kind: TaskKind;
  label: string;                         // UI 展示名
  status: 'draft'|'queued'|'running'|'blocked'|'succeeded'|'failed'|'cancelled';
  progressPct: number | null;            // 0-100
  startedAt: string | null;
  finishedAt: string | null;
  etaMs: number | null;
  projectId: string | null;
  ownerRef: {                            // 指向源对象便于跳转
    kind: 'timeline'|'script'|'voice-track'|'subtitle-track'|'imported-video'|'render'|'publish-plan'|'automation-task'|'asset';
    id: string;
  } | null;
  errorCode: string | null;
  errorMessage: string | null;
  retryable: boolean;
  createdAt: string;
  updatedAt: string;
}
```

### 4.4 迁移要求

- 所有扩字段通过 **Alembic 新 revision** 实现，禁止手改表结构
- 迁移必须同时提供 `upgrade` 和 `downgrade`
- 新建表必须在 `domain/models/` 下注册，schema 在 `schemas/` 下暴露 DTO

---

## 5 · 任务拆解与排期

### 5.1 任务分组与里程碑

按里程碑对齐 `docs/PRD.md § 14.2`，后端任务分为 5 个 Sprint：

| Sprint | 时间 | 重点 | 核心交付 |
| --- | --- | --- | --- |
| **B-S1** 全局底座 | Week 1 | § 1 全部 + § 3 WebSocket 消息协议 + § 4.3 TaskDto | 全局搜索 / Health 聚合 / Dashboard 聚合 / TaskBus 统一 / 错误码表 |
| **B-S2** 首启与配置 | Week 2 | § 2.1 + § 2.16 补齐 | 向导目录初始化接口 / 诊断导出 / 日志查询 |
| **B-S3** 创作前置链 | Week 3-4 | § 2.3 + § 2.4 + § 2.6 | 脚本版本/变体/段落改写 / 分镜 Shot CRUD / 视频拆解阶段接口 |
| **B-S4** 创作核心链 | Week 5-7 | § 2.5 + § 2.7 + § 2.8 + § 2.14 | 工作台片段原子操作 / 配音段级重生成 / 字幕手动对齐 / 渲染队列完整 |
| **B-S5** 执行与治理 | Week 8-10 | § 2.10 + § 2.11 + § 2.12 + § 2.13 + § 2.15 + § 2.9 | 账号绑定 / 设备浏览器实例 / 自动化规则 / 发布日历 / 复盘建议回流 / 资产分组 |

> 当前进度（2026-04-17）：**B-S1 已完成搜索、Health 聚合、Dashboard 聚合、TaskDto 基础改造、配置广播、错误码基础能力、文档与契约测试；B-S2 已完成目录初始化、自检、日志查询、诊断包导出与对应 runtime-client/契约测试；`quick-jump` 与“所有异步来源统一注册 TaskBus”仍待继续推进。**

### 5.2 Sprint B-S1 详细任务（示例）

| # | 任务 | 文件 | 估时 |
| --- | --- | --- | --- |
| 1 | 定义 `TaskDto` + `TaskKind` + `TaskStatus` 扩展 | `schemas/tasks.py` | 0.5d |
| 2 | `task_manager` 改造为统一注册中心，支持 kind/ownerRef | `services/task_manager.py` | 1.5d |
| 3 | 扩 `GET /api/tasks` 支持 kind/status 过滤 + ownerRef | `api/routes/tasks.py` | 0.5d |
| 4 | 定义全局错误码 Enum + 扩 `error_response(code=...)` | `schemas/envelope.py` + `schemas/error_codes.py` | 0.5d |
| 5 | 新建 `search_service.py` 聚合六类对象 | `services/search_service.py` | 1d |
| 6 | 新建 `/api/search` Route | `api/routes/search.py` | 0.5d |
| 7 | 扩 `/api/settings/health` 为全量 `RuntimeHealthSnapshot` | `services/settings_service.py` | 0.5d |
| 8 | 扩 `/api/dashboard/summary` 为完整 `DashboardSummary` | `services/dashboard_service.py` | 1d |
| 9 | 新增 `/api/projects/{id}/quick-jump` | `services/dashboard_service.py` + route | 0.5d |
| 10 | 广播 `config.changed` / `ai-capability.changed` / `context.project.changed` | 相关 service 增加 `ws_manager.broadcast` | 0.5d |
| 11 | 文档：更新 `docs/RUNTIME-API-CALLS.md` 全部 S1 内容 | — | 1d |
| 12 | 契约测试：`tests/contracts/test_search.py` / `test_health.py` / `test_dashboard.py` | `tests/contracts/` | 1d |

> 已完成：1、2、3、4、5、6、7、8、10、11、12。  
> 待继续：9，以及 TaskBus 聚合范围从当前基础能力扩展到全部异步来源。

**Sprint B-S1 小计**：约 8.5 个工作日。

### 5.3 整体工时估算

| Sprint | 任务数 | 估时 |
| --- | --- | --- |
| B-S1 | 12 | 8.5d |
| B-S2 | 8 | 5d |
| B-S3 | 18 | 15d |
| B-S4 | 22 | 22d |
| B-S5 | 26 | 22d |
| **合计** | **86** | **~72.5d** |

单人 10 ~ 12 周，三人并行约 4 ~ 5 周。

---

## 6 · 验收标准

### 6.1 每个接口验收

- [ ] 信封：`{ok:true, data}` / `{ok:false, error, error_code}` 严格遵守
- [ ] 中文错误提示：UI 可直接展示，不含英文异常栈
- [ ] 日志：`logger.exception(...)` 覆盖所有 try/except
- [ ] 超时：外部调用设置超时；长任务走 TaskBus
- [ ] 契约测试：`tests/contracts/test_<module>.py` 覆盖成功与错误两条路径
- [ ] 文档：同次提交更新 `docs/RUNTIME-API-CALLS.md` 接口表与 § 9 登记表

### 6.2 WebSocket 消息验收

- [ ] `schema_version` 恒为 `1`
- [ ] 每次广播都能被 `apps/desktop/src/stores/task-bus.ts` 正确解析
- [ ] 高频事件（`task.progress` / `render.progress`）节流 500ms
- [ ] 断开自动重连策略由前端负责，后端无状态

### 6.3 数据迁移验收

- [ ] 新增字段/表有 Alembic 迁移
- [ ] `upgrade` / `downgrade` 均可重放
- [ ] 不影响既有本地数据（兼容旧 SQLite 文件）

### 6.4 前后端对接验收

- [ ] `apps/desktop/src/app/runtime-client.ts` 新函数已登记
- [ ] `apps/desktop/src/types/runtime.ts` 的 DTO 类型与 Python schema 字段名一一对应（`camelCase` ↔ `snake_case` 在 schema 层统一使用 `alias_generator` 处理）
- [ ] Pinia store 订阅 WebSocket 并更新本地状态
- [ ] 契约测试（`tests/contracts/`）与前端 store 测试（`apps/desktop/tests/`）同步

### 6.5 Sprint 出 Sprint Review 标准

每个 Sprint 结束时提交：
- 接口变更清单（diff to `RUNTIME-API-CALLS.md`）
- 新增/修改的测试用例数量
- 演示脚本：用 `curl` 或 `httpie` 跑通每个新接口的主路径

---

## 附录 A · 现状清单（Runtime 已有 Router / Service / Schema）

```
api/routes/
  ├── accounts.py          → M10 已覆盖
  ├── ai_capabilities.py   → M16 已文档化
  ├── ai_providers.py      → M16 已文档化
  ├── assets.py            → M09 已文档化
  ├── automation.py        → M12 骨架
  ├── dashboard.py         → M02 骨架（需扩字段）
  ├── device_workspaces.py → M11 骨架
  ├── license.py           → M01 已文档化
  ├── publishing.py        → M13 骨架
  ├── renders.py           → M14 骨架
  ├── review.py            → M15 骨架
  ├── scripts.py           → M03 骨架
  ├── settings.py          → M16 已文档化
  ├── storyboards.py       → M04 骨架
  ├── subtitles.py         → M08 已文档化
  ├── tasks.py             → 全局，需扩统一 TaskBus
  ├── video_deconstruction.py → M06 骨架
  ├── voice.py             → M07 已文档化
  ├── workspace.py         → M05 已文档化
  └── ws.py                → 全局单通道
```

services/、repositories/、schemas/、domain/models/ 均有对应模块（一一对齐路由）。

---

## 附录 B · 前端契约清单（每页一组函数名）

这是 `apps/desktop/src/app/runtime-client.ts` 即将新增的函数清单（S1-S5 完成后）。前端开发可按此名单先声明类型 stub 并行开发。

```typescript
// § 1 全局
searchGlobal(q: string, types?: string[]): Promise<GlobalSearchResult>;
fetchRuntimeHealth(): Promise<RuntimeHealthSnapshot>;       // 现有，扩字段
fetchDashboardSummary(): Promise<DashboardSummary>;         // 现有，扩字段
fetchProjectQuickJump(projectId: string): Promise<ProjectQuickJump>;
fetchTasks(filter?: TaskFilter): Promise<TaskDto[]>;        // 现有，扩 filter
cancelTask(taskId: string): Promise<void>;                  // 现有

// § 2.1 首启
initializeDirectories(): Promise<BootstrapDirectoryReport>;
runtimeSelfCheck(): Promise<RuntimeSelfCheckReport>;

// § 2.3 脚本
generateScriptTitleVariants(projectId: string, topic: string, count: number): Promise<TitleVariantDto[]>;
listScriptVersions(projectId: string): Promise<ScriptVersionDto[]>;
restoreScriptVersion(projectId: string, versionId: string): Promise<ScriptDocumentDto>;
rewriteScriptSegment(projectId: string, segmentId: string, input: RewriteInput): Promise<ScriptSegmentDto>;
listPromptTemplates(kind?: string): Promise<PromptTemplateDto[]>;
upsertPromptTemplate(input: PromptTemplateInput): Promise<PromptTemplateDto>;

// § 2.4 分镜
createShot(storyboardId: string, input: ShotInput): Promise<ShotDto>;
updateShot(shotId: string, input: Partial<ShotInput>): Promise<ShotDto>;
deleteShot(shotId: string): Promise<void>;
syncStoryboardFromScript(projectId: string): Promise<StoryboardDocumentDto>;
listStoryboardTemplates(): Promise<StoryboardTemplateDto[]>;

// § 2.5 工作台
fetchWorkspaceClip(clipId: string): Promise<WorkspaceClipDetailDto>;
moveWorkspaceClip(clipId: string, input: MoveClipInput): Promise<WorkspaceTimelineResultDto>;
trimWorkspaceClip(clipId: string, input: TrimClipInput): Promise<WorkspaceTimelineResultDto>;
replaceWorkspaceClip(clipId: string, input: ReplaceClipInput): Promise<WorkspaceTimelineResultDto>;
fetchTimelinePreview(timelineId: string): Promise<TimelinePreviewDto>;
precheckTimeline(timelineId: string): Promise<TimelinePrecheckDto>;

// § 2.6 视频拆解
fetchVideoStages(videoId: string): Promise<VideoStageDto[]>;
rerunVideoStage(videoId: string, stageId: string): Promise<TaskDto>;
fetchVideoTranscript(videoId: string): Promise<VideoTranscriptDto>;
fetchVideoSegments(videoId: string): Promise<VideoSegmentDto[]>;
adoptVideoToProject(videoId: string, input: AdoptInput): Promise<ProjectSummaryDto>;

// § 2.7 配音
createVoiceProfile(input: VoiceProfileInput): Promise<VoiceProfileDto>;
regenerateVoiceSegment(trackId: string, segmentId: string, input: RegenerateInput): Promise<TaskDto>;
fetchVoiceWaveform(trackId: string): Promise<VoiceWaveformDto>;

// § 2.8 字幕
alignSubtitleManual(trackId: string, input: ManualAlignInput): Promise<SubtitleTrackDto>;
listSubtitleStyleTemplates(): Promise<SubtitleStyleTemplateDto[]>;
exportSubtitle(trackId: string, format: 'srt'|'vtt'|'ass'): Promise<SubtitleExportDto>;

// § 2.9 资产
listAssetGroups(): Promise<AssetGroupDto[]>;
createAssetGroup(input: AssetGroupInput): Promise<AssetGroupDto>;
batchDeleteAssets(ids: string[]): Promise<BatchDeleteResult>;
batchMoveAssetsToGroup(ids: string[], groupId: string): Promise<void>;

// § 2.10 账号
setAccountBinding(accountId: string, input: AccountBindingInput): Promise<AccountDto>;

// § 2.11 设备
listBrowserInstances(workspaceId: string): Promise<BrowserInstanceDto[]>;
createBrowserInstance(workspaceId: string, input: BrowserInput): Promise<BrowserInstanceDto>;
deleteBrowserInstance(browserId: string): Promise<void>;
fetchWorkspaceLogs(workspaceId: string, cursor?: string): Promise<LogPageDto>;

// § 2.12 自动化
pauseAutomationTask(taskId: string): Promise<void>;
resumeAutomationTask(taskId: string): Promise<void>;

// § 2.13 发布
fetchPublishingCalendar(from: string, to: string): Promise<CalendarDayDto[]>;
fetchPublishReceipts(planId: string): Promise<PublishReceiptDto[]>;

// § 2.14 渲染
listRenderTemplates(): Promise<RenderTemplateDto[]>;
fetchRenderResourceUsage(): Promise<RenderResourceDto>;
retryRenderTask(taskId: string): Promise<TaskDto>;

// § 2.15 复盘
adoptReviewSuggestion(projectId: string, suggestionId: string): Promise<ProjectSummaryDto>;

// § 2.16 设置
fetchRuntimeLogs(filter: LogFilter): Promise<LogPageDto>;
exportDiagnosticsBundle(): Promise<DiagnosticsBundleDto>;
```

以上 **约 50 个新函数**。加上现有 24 个，总契约面约 74 个 HTTP 入口 + 23 种 WebSocket 消息。

---

**文档结束。** 任何新增接口落地前，必须在 `docs/RUNTIME-API-CALLS.md` 添加详尽定义。本文件只做需求驱动与排期。
