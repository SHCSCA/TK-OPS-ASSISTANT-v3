# TK-OPS 后端开发需求 v2026.04.17
> **历史定位说明**：本文是 2026-04-17 的后端差口快照，用于保留当时的缺口判断，不再作为唯一后端需求入口。
> 
> 后续 V2 收口请优先参考：
> - `docs/V2-BACKEND-REQUIREMENTS-2026-04-20.md`
> - `docs/V2-PRODUCT-REQUIREMENTS-2026-04-20.md`

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

### 0.1.1 状态图例(本次新增)

> 现有四档（D1-D4）描述"距离 100% 还差什么"。本次再叠加一组"当前实施进度"标注，回答"已经做到哪里"。

| 标记 | 含义 | 判据 |
| --- | --- | --- |
| ✅ | **已完成** | Route + Service + Repository + Schema 已落地,且已写入 `docs/RUNTIME-API-CALLS.md`,且至少有一处前端调用与一条 contract test |
| 🚧 | **开发中 / 部分完成** | Route 已存在但字段不全 / 文档未登记 / 测试未覆盖 / 前端未对接,任一缺失即归类为开发中 |
| 📋 | **待开发** | 完全缺失,与 D4 等价 |

### 0.1.2 当前进度总览(2026-04-17 快照)

| 模块 | 真实路由数 | ✅ 已完成 | 🚧 开发中 | 📋 待开发 | 备注 |
| --- | ---: | ---: | ---: | ---: | --- |
| M01 License | 2 | 2 | 0 | 3 | 状态/激活已完成；指纹/受限模式/选择性禁用未做 |
| M02 Dashboard | 4 | 0 | 4 | 3 | 字段不足以驱动蓝图;sparkline/quick-jump 未做 |
| M03 Scripts | 4 | 0 | 4 | 5 | Document/Generate/Rewrite 已实现但未文档化;变体/版本/段级改写未做 |
| M04 Storyboards | 3 | 0 | 3 | 4 | Document/Generate 已实现;Shot CRUD/模板未做 |
| M05 Workspace | 4 | 4 | 0 | 8 | 时间线 CRUD + AI 命令已文档化;clip 详情/原子操作/导出/预览未做 |
| M06 Video Decon | 3 | 0 | 3 | 7 | 仅 import/list/delete;阶段/转写/切段/回流未做 |
| M07 Voice | 5 | 5 | 0 | 5 | CRUD + generate 已文档化;profiles 写入/段级/波形/试听/停顿未做 |
| M08 Subtitles | 5 | 5 | 0 | 4 | CRUD + generate 已文档化;手动对齐/模板/导出/源波形未做 |
| M09 Assets | 10 | 8 | 2 | 6 | CRUD/import/references 已完成;refs/{id} 子接口与 references 接口待文档对齐;缩略图/批量/分组未做 |
| M10 Accounts | 13 | 0 | 13 | 3 | 全部 13 个端点存在但未文档化;状态广播/绑定/脱敏未做 |
| M11 Devices | 6 | 0 | 6 | 4 | workspaces CRUD + health-check 存在未文档化;浏览器实例/日志/绑定未做 |
| M12 Automation | 7 | 0 | 7 | 4 | tasks CRUD + trigger + runs 存在未文档化;暂停/恢复/取消运行/日志未做 |
| M13 Publishing | 8 | 0 | 8 | 4 | plans CRUD + precheck/submit/cancel 存在未文档化;日历/回执未做 |
| M14 Renders | 6 | 0 | 6 | 5 | tasks CRUD + cancel 存在未文档化;模板/重试/资源/进度未做 |
| M15 Review | 3 | 0 | 3 | 4 | summary/analyze 存在未文档化;建议列表/回流未做 |
| M16 Settings | 9 | 9 | 0 | 4 | 全部主接口已文档化;诊断导出/日志查询/迁移上报未做 |
| Tasks/WS | 4 | 1 | 3 | 0 | tasks 列表/cancel 已实现但未统一 TaskBus;ws 通道存在 |
| **§1 跨页基础设施** | 0 | 0 | 0 | **30+** | 搜索/Health 扩展/Dashboard 扩展/TaskDto/错误码/草稿/上传/分页/撤销/个人化/审计/备份/迁移 全部未做 |
| **合计** | **96** | **34 (35%)** | **62 (65%)** | **96+ 待新增** | 文档化只覆盖了 M05/M07/M08/M09/M16 |

> **解读**：96 个真实路由中,只有 34 个走完了"实现 + 文档 + 前端 + 测试"四步。62 个是"代码已写但未登记/未对接",这才是当前最大的债。新增需求(§1.8 ~ §1.13 + 各页缺口)还有 96+ 待开发。

---

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

### 1.1 全局搜索（Cmd+K） — **○ D4 需新增**

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

### 1.2 Runtime 健康聚合（增强 `/api/settings/health`） — **◐ D2 补字段**

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

### 1.3 Dashboard 聚合（增强 `/api/dashboard/summary`） — **◐ D2 补字段**

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

### 1.4 任务中心统一接口 — **◐ D2 补聚合**

**驱动**：蓝图 § 3.6 Status Bar 任务计数、Dashboard 运行统计、工作台底部运行栏、自动化/渲染/发布/AI 任务统一视图。

**现状**：`GET /api/tasks` 已存在，但未统一所有异步任务来源（采集/发布/渲染/AI 生成/视频导入等目前分散在各 service 独立存储）。

**需求**：
- 所有异步任务必须注册到 `task_manager`，通过 `GET /api/tasks` 可统一列出
- 支持筛选：`?type=render|publish|automation|ai-generate|video-import&status=running,queued`
- 响应每项包含：`id / type / label / status / progressPct / startedAt / etaMs / projectId? / ownerRef`

### 1.5 项目上下文（新增） — **○ D4 需新增**

**驱动**：蓝图 Title Bar "当前项目" 徽章、创作主链所有页面都需要"当前项目" 语义。

**现状**：`GET/PUT /api/dashboard/context` 已存在。

**需补**：
- `PUT` 的 schema 允许清空（`projectId: null` → 进入"未选择项目"态）
- WebSocket 广播 `context.project.changed` 消息，让所有已打开页面刷新

### 1.6 配置总线 WebSocket 广播 — **◐ D2 补广播**

**驱动**：蓝图设置页改动后，其他页面（如工作台、Dashboard）需实时感知主题/AI Provider 变更。

**需求**：
- `PUT /api/settings/config` 和 `PUT /api/settings/ai-capabilities` 成功后广播 `config.changed` / `ai-capability.changed`
- 前端 `config-bus` store 订阅后刷新本地缓存

### 1.7 统一错误码表 — **◐ D2 补约定**

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
| `autosave.conflict` | 后端 `updatedAt` 与前端 `baseUpdatedAt` 不一致 | 文档已被另一端修改，请刷新后再保存 |
| `autosave.outdated` | 草稿 `version` 落后于服务端 | 当前草稿已过期，已为你恢复最新版本 |
| `upload.checksum-mismatch` | 分片 sha256 校验失败 | 上传分片校验失败，正在自动重传 |
| `upload.session-expired` | 上传会话超时 | 上传超时，请重新选择文件 |
| `range.unsupported` | 媒体源不支持 Range 请求 | 媒体文件不支持流式播放，请重新导入 |
| `fingerprint.changed` | 机器指纹与激活时不一致 | 设备特征已变化，请重新激活许可证 |
| `pagination.cursor-invalid` | 游标解析失败或已失效 | 列表已更新，请刷新后重试 |
| `undo.stack-empty` | 撤销栈无可恢复操作 | 没有可撤销的操作 |
| `undo.snapshot-missing` | 历史快照已被回收 | 历史记录已超出保留期 |
| `backup.restore-conflict` | 还原文件版本与当前 schema 不兼容 | 备份版本不兼容，请升级后再还原 |
| `migration.required` | 启动时检测到待执行迁移 | 数据需要升级，请稍候 |
| `audit.scope-denied` | 调用方无权限访问该审计范围 | 当前账号无权查看该日志范围 |

> 本表 18 行(原)+ 13 行(本次新增)= **31 个错误码**。落地优先级见 §1.7、§1.8 ~ §1.13。

---

## 1.8 · 自动保存与草稿恢复 — **○ D4 需新增**

**驱动**：UI 蓝图 §5.5 工作台 Header "保存：刚刚"、§5.3 脚本编辑器、§5.4 分镜、§5.7 配音、§5.8 字幕。所有可编辑实体都需要"自动保存 + 崩溃后草稿恢复"。

**需求**：
- 服务端为可编辑实体引入 `updatedAt` + `version` 双字段(`version` 单调递增整数)
- 前端每次提交携带 `baseUpdatedAt` 或 `baseVersion`,服务端比对失败返回 `autosave.conflict`
- 引入"未提交草稿"侧表 `editor_draft`：`{ id, ownerKind, ownerId, content, savedAt, dirty }`,Runtime 崩溃恢复后页面读取草稿
- 自动保存广播 WebSocket `autosave.saved` 事件,带 `{ ownerKind, ownerId, savedAt, version }`

**接口(新增)**：
```
PUT /api/drafts/{kind}/{id}                 -> 增量保存(每 3 ~ 5s 节流)
GET /api/drafts/{kind}/{id}                 -> 拉取最近草稿(用于崩溃后恢复)
DELETE /api/drafts/{kind}/{id}              -> 用户主动放弃草稿
```

**`kind` 枚举**：`script | storyboard | timeline | voice-track | subtitle-track | review-summary`

**落地位置**：
- Route：`api/routes/drafts.py`(新建)
- Service：`services/draft_service.py`(新建)
- Schema：`schemas/drafts.py`(新建)
- Domain：新表 `editor_draft`(Alembic 迁移)

---

## 1.9 · 大文件分片上传与流式播放 — **○ D4 需新增**

**驱动**：UI 蓝图 §5.6 视频导入(几十 MB ~ 数 GB)、§5.9 资产中心(本地素材入库)、§5.5 预览窗口(必须支持 Range)。

### 1.9.1 分片上传协议

```
POST /api/uploads/sessions
  body: { filename, sizeBytes, mimeType, sha256, chunkSizeBytes? }
  -> { sessionId, chunkSizeBytes, expiresAt }

PUT  /api/uploads/sessions/{sessionId}/chunks/{chunkIndex}
  body: 二进制分片
  headers: X-Chunk-Sha256, Content-Length
  -> { received: chunkIndex, nextExpected, ackedSha256 }

POST /api/uploads/sessions/{sessionId}/complete
  body: { fullSha256 }
  -> { assetId? | importedVideoId?, finalPath }

DELETE /api/uploads/sessions/{sessionId}      -> 用户取消
```

**WebSocket**：`upload.chunk.acked` / `upload.session.failed`(节流 250ms)

**约束**：
- 默认 `chunkSizeBytes = 4 MiB`,最小 256 KiB,最大 16 MiB
- 会话保留 15 分钟,过期返回 `upload.session-expired`
- 完成后由调用上下文决定挂载到 `assets` 还是 `imported_video`,通过 query 参数 `?target=asset|video`

### 1.9.2 流式播放(Range)

```
GET /api/media/{kind}/{id}/stream
  headers: Range: bytes=<start>-<end>
  -> 206 Partial Content + Content-Range
```

`kind ∈ {asset, voice-track, render, preview-frame}`。源文件不支持 Range 时返回 `range.unsupported`。

**落地位置**：
- Route：`api/routes/uploads.py` + `api/routes/media.py`(新建)
- Service：`services/upload_session_service.py` + `services/media_stream_service.py`
- Domain：新表 `upload_session`

---

## 1.10 · 分页与游标协议 — **○ D4 需新增**

**驱动**：UI 蓝图 §5.9 资产中心(数千资产)、§5.10 账号、§5.13 发布日历、Status Bar 任务列表(§3.6)。

**统一约定**：所有可能 ≥ 50 条的 list 接口都改为游标分页,响应信封扩展为：

```typescript
interface CursorPage<T> {
  items: T[];
  nextCursor: string | null;
  pageSize: number;
  totalEstimate: number | null;  // 大数据集时为 null
}
```

请求：`?cursor=<opaque>&limit=<n>`(`limit` 默认 50,最大 200)。

**适用接口(覆写)**：`/api/assets`、`/api/accounts`、`/api/publishing/plans`、`/api/renders/tasks`、`/api/automation/tasks`、`/api/tasks`(全局任务)、`/api/scripts/projects/{id}/versions`、`/api/devices/workspaces/{id}/logs`。

**兼容**：
- 老调用方未传 `cursor` 时返回首页
- `nextCursor=null` 表示已到末尾
- 游标失效返回 `pagination.cursor-invalid`,前端必须丢弃缓存重新拉首页

**落地位置**：
- Schema：`schemas/pagination.py`(新建,提供 `CursorPage[T]` 泛型与 `encode_cursor / decode_cursor` 工具)
- Repository：所有上述 list 方法增加 `cursor / limit` 参数

---

## 1.11 · 撤销/重做与并发冲突 — **○ D4 需新增**

**驱动**：UI 蓝图 §5.5 时间线(片段拖拽/裁剪)、§5.3 脚本编辑器(段落改写)、§5.4 分镜镜头编辑。所有可编辑链路必须可恢复。

**协议**：

```
POST /api/history/{kind}/{id}/snapshot
  body: { reason: 'autosave'|'user-save'|'pre-ai-action' }
  -> { snapshotId, version, createdAt }

GET  /api/history/{kind}/{id}                -> 列出最近 N 条快照
POST /api/history/{kind}/{id}/restore/{snapshotId}
  -> { restoredVersion, content }
```

**保留策略**：
- 每个实体最多 50 条快照,FIFO 淘汰
- `pre-ai-action` 保护性快照不计入 50 条上限,单独保留 10 条
- 超出范围返回 `undo.snapshot-missing`

**并发冲突**：基于 §1.8 的 `version` 字段乐观锁。冲突时返回 `autosave.conflict` + 服务端最新内容,前端做 3-way merge UI 提示。

**落地位置**：
- Route：`api/routes/history.py`(新建)
- Service：`services/history_service.py`
- Domain：新表 `entity_snapshot`(`entityKind, entityId, snapshotId, version, content, reason, createdAt`)

---

## 1.12 · 窗口与个人化状态 — **○ D4 需新增**

**驱动**：UI 蓝图 §3.3 Sidebar 折叠、§3.5 Detail Panel 三档宽度、§5.5 时间线缩放级别。这些状态必须跨会话保留。

**接口(新增)**：

```
GET /api/personalization                                        -> UserPersonalization
PUT /api/personalization                                        -> 增量保存
PUT /api/personalization/sections/{sectionKey}                  -> 单 section 增量
```

**Schema**：

```typescript
interface UserPersonalization {
  shell: {
    sidebarCollapsed: boolean;
    detailPanelWidth: 0 | 360 | 480;
    theme: 'light' | 'dark' | 'auto';
    lastRoute: string | null;
  };
  workspace: {
    timelineZoomLevel: number;     // 0.25 ~ 4.0
    snapToGrid: boolean;
    showWaveform: boolean;
  };
  search: {
    recentQueries: string[];       // ≤ 10 条
  };
  updatedAt: string;
}
```

**落地位置**：
- Route：`api/routes/personalization.py`
- Service：`services/personalization_service.py`
- Domain：新表 `user_personalization`(单行)

---

## 1.13 · 审计日志、备份与迁移诊断 — **○ D4 需新增**

**驱动**：CLAUDE.md "全局异常处理与日志记录"、本文 §2.16 已提及但未落地、本地优先架构刚需备份/恢复。

### 1.13.1 审计日志查询

```
GET /api/audit/logs?kind=<kind>&since=<iso>&until=<iso>&actor=<id>&cursor=
  -> CursorPage<AuditLogEntry>

interface AuditLogEntry {
  id: string;
  occurredAt: string;
  kind: 'config'|'license'|'project'|'task'|'asset'|'publish'|'ai'|'auth';
  actor: { kind: 'user'|'system'|'task', id: string };
  action: string;            // 'create'|'update'|'delete'|'invoke'|'fail'
  targetRef: { kind: string, id: string };
  payloadDigest: string;     // 不存原文,只存 sha256
  resultCode: string | null; // 错误码或 'ok'
}
```

权限不足返回 `audit.scope-denied`(本地单机模式默认全开,预留多用户扩展)。

### 1.13.2 备份与恢复

```
POST /api/backup/snapshots                  -> { backupId, path, sizeBytes, createdAt }
GET  /api/backup/snapshots                  -> BackupSnapshot[]
POST /api/backup/snapshots/{id}/restore     -> { restoredAt, restartRequired }
DELETE /api/backup/snapshots/{id}
```

备份包含：SQLite 主库、`secret_store`、`personalization`、`editor_draft`。不含媒体二进制(媒体走 §1.9 重新导入)。
不兼容版本返回 `backup.restore-conflict`。

### 1.13.3 迁移诊断

扩展 `GET /api/settings/health` 字段：

```typescript
migration: {
  required: boolean;
  currentRevision: string;
  targetRevision: string;
  pendingSteps: number;
}
```

迁移期间任何业务接口返回 `migration.required`。前端 `BootstrapGate` 需识别该错误码并展示进度。

**落地位置**：
- Route：`api/routes/audit.py` + `api/routes/backup.py`(新建)
- Service：`services/audit_service.py` + `services/backup_service.py`
- Domain：新表 `audit_log`、`backup_snapshot`

---

## 2 · 16 页逐页缺口矩阵

缺口矩阵采用紧凑表格：**蓝图需求 / 现有代码 / 缺口 / 落地点 / 优先级**。详尽 DTO 与接口定义在接口文档中新增章节（见 § 5 排期）。

### 2.1 `setup_license_wizard` — 首启与许可证向导

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| ✅ | ● | License 激活（`/api/license/status`、`/api/license/activate`） |
| ✅ | ● | Runtime 健康检查（`/api/settings/health`） |
| 🚧 | ◐ | 首次目录初始化：当前通过 bootstrap 脚本，需暴露 `POST /api/bootstrap/initialize-directories` 供向导调用 |
| 🚧 | ◑ | 首次 AI Provider 快速配置：复用 `PUT /api/settings/ai-capabilities` 即可，但需文档化"空配置 → 首 Provider 引导"路径 |
| 📋 | ○ | 机器指纹展示 / 跳过引导(受限模式) / 受限模式状态查询 |

**缺口清单**：
- `POST /api/bootstrap/initialize-directories` · **D4** · 身份：生成默认 `%APPDATA%/TK-OPS-ASSISTANT/{db,projects,assets,renders,logs,cache,licenses}`，返回权限检查结果。
- `POST /api/bootstrap/runtime-selfcheck` · **D4** · 运行一次聚合自检（端口、版本、依赖、数据库可写），返回结构化报告（向导 UI 展示）。
- `GET /api/license/fingerprint` · **D4** · 计算并返回当前机器指纹(UI §5.1 第 2 步显示),含 `{ fingerprint, algorithm, components: { cpu, mac, diskSerial } }`。变化触发 `fingerprint.changed`。
- `POST /api/bootstrap/skip-wizard` · **D4** · 用户选"跳过引导(受限模式)"时记录标记,激活前禁用受限能力清单(发布、AI、渲染),响应 `{ limitedMode: true, blockedFeatures: [...] }`。
- `GET /api/bootstrap/limited-mode` · **D4** · 各页面根据返回判断当前是否处于受限模式。

### 2.2 `creator_dashboard` — 创作总览

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| 🚧 | ◐ | `/api/dashboard/summary` 已存在但字段不全（见 § 1.3） |
| 🚧 | ● | `/api/dashboard/context` GET/PUT(已实现,未对接 WebSocket 广播) |
| 🚧 | ● | `POST /api/dashboard/projects` 新建项目(已实现,未文档化) |
| 📋 | ◑ | `GET /api/projects/{id}` 项目详情（当前分散在 script/storyboard/workspace 中各自 project，需统一） |
| 📋 | ○ | `GET /api/projects/{id}/quick-jump` — Hero "继续创作" 的智能下一步 action |
| 📋 | ○ | `GET /api/dashboard/sparklines` 时序数据(健康卡迷你图) |

**缺口清单**：
- 扩 `DashboardSummary` 字段（§ 1.3） · **D2**
- 新增 `GET /api/projects/{id}/quick-jump` · **D4** · 返回 `{ stage: 'script'|'storyboard'|'workspace'|'voice'|'subtitle'|'render'|'publish', targetId, reason }`
- 新增 `GET /api/dashboard/sparklines?metrics=ai-latency,render-throughput,publish-success&windowHours=24` · **D4** · 返回时序点 `{ metric, points: [{ ts, value }], unit }[]`,驱动 §5.2 健康卡迷你 sparkline。

### 2.3 `script_topic_center` — 脚本与选题中心

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| 🚧 | ◑ | `GET/PUT /api/scripts/projects/{id}/document` · 存在但文档未覆盖 |
| 🚧 | ◑ | `POST /api/scripts/projects/{id}/generate` · 存在 |
| 🚧 | ◑ | `POST /api/scripts/projects/{id}/rewrite` · 存在 |
| 📋 | ○ | 标题变体：`POST /api/scripts/projects/{id}/title-variants` · 缺 |
| 📋 | ○ | 文案版本：`GET /api/scripts/projects/{id}/versions` / `POST .../versions/{v}/restore` · 缺 |
| 📋 | ○ | 段落级 AI 改写（带 Prompt 模板）：`POST /api/scripts/projects/{id}/segments/{segId}/rewrite` · 缺 |
| 📋 | ○ | Prompt 模板管理：`GET/POST/PUT/DELETE /api/prompt-templates` · 缺 |
| 📋 | ○ | AI 流式输出 WebSocket 协议（`script.ai.stream`） · 缺（蓝图 § 5.3 B 区动效依赖） |

**缺口清单（按优先级）**：
1. `POST /api/scripts/projects/{id}/title-variants`（输入 topic+count → 输出数组）· **D4** · P0
2. `GET /api/scripts/projects/{id}/versions` / `POST .../restore/{versionId}` · **D4** · P0
3. AI 流式输出 WebSocket 事件 `script.ai.stream`（分帧文本 / 进度 / 完成 / 错误）· **D4** · P0
4. `POST /api/scripts/projects/{id}/segments/{segId}/rewrite`（段落级改写）· **D4** · P1
5. Prompt 模板 CRUD · **D4** · P1

### 2.4 `storyboard_planning_center` — 分镜规划中心

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| 🚧 | ◑ | `GET/PUT /api/storyboards/projects/{id}/document` · 存在 |
| 🚧 | ◑ | `POST /api/storyboards/projects/{id}/generate` · 存在 |
| 📋 | ○ | 镜头级 CRUD：`POST/PATCH/DELETE /api/storyboards/{id}/shots/{shotId}` · 缺 |
| 📋 | ○ | 节奏模板：`GET /api/storyboards/templates` · 缺 |
| 📋 | ○ | 脚本 ↔ 分镜双向引用：`POST /api/storyboards/projects/{id}/sync-from-script` · 缺（脚本变更后同步） |

**缺口清单**：
1. 镜头级 CRUD · **D4** · P0
2. 节奏模板只读接口（内置 + 用户自定义） · **D4** · P1
3. 脚本变更联动分镜刷新 · **D4** · P1

### 2.5 `ai_editing_workspace` — AI 剪辑工作台 ★

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| ✅ | ● | 时间线 CRUD（`/api/workspace/.../timeline` GET/POST/PATCH）· 已文档化 |
| 🚧 | ◐ | AI 命令入口已存在但仅返回 `blocked`，需扩展 |
| 📋 | ○ | 片段详情：`GET /api/workspace/clips/{clipId}` · 缺（蓝图 Detail Panel 依赖） |
| 📋 | ○ | 片段替换/移动/裁剪原子操作 · 当前仅整表 PATCH |
| 📋 | ○ | 预览信息：`GET /api/workspace/timelines/{id}/preview` 返回低清代理帧 URL · 缺 |
| 📋 | ○ | 渲染预检：`POST /api/workspace/timelines/{id}/precheck` · 缺 |
| 📋 | ○ | 工作台自动保存 / 时间线导出(EDL/FCPXML/Premiere) · 缺(依赖 §1.8、§2.5 新增项) |

**缺口清单（按优先级）**：
1. `GET /api/workspace/clips/{clipId}` 单片段详情(`WorkspaceClipDetailDto = { id, kind:'video|audio|voice|subtitle', sourceAssetId, sourcePrompt?, sourceTaskId?, durationMs, inMs, outMs, resolution?, frameRate?, channels?, sampleRateHz?, editable: { trim, move, replace, regenerate, delete }, aiOrigin?: { provider, model, runAt } }`) · **D4** · P0
2. 片段原子操作：`POST .../clips/{id}/move` / `POST .../clips/{id}/trim` / `POST .../clips/{id}/replace` · **D4** · P0
3. AI 命令（生成镜头 / 替换旁白 / 重对齐字幕）落地为真实任务：扩 `workspace_service.ai_command` 到 TaskBus · **D2→D1** · P1
4. 预览代理帧 URL（基于 `media/` 层 FFmpeg） · **D4** · P1
5. 渲染预检接口 · **D4** · P1
6. 工作台 Header 自动保存协议(走 §1.8 `PUT /api/drafts/timeline/{id}`) · **D4** · P0
7. 时间线导出(区别于渲染,导出 EDL/XML/项目工程文件)：`POST /api/workspace/timelines/{id}/export?format=edl|fcpxml|premiere` · **D4** · P1
8. 时间线流式预览：复用 §1.9.2 `/api/media/preview-frame/{timelineId}/stream` · **D4** · P1

### 2.6 `video_deconstruction_center` — 视频拆解中心

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| 🚧 | ◑ | `POST /api/video-deconstruction/projects/{id}/import` 已存在 |
| 🚧 | ◑ | `GET /api/video-deconstruction/projects/{id}/videos` |
| 🚧 | ◑ | `DELETE /api/video-deconstruction/videos/{id}` |
| 📋 | ○ | 阶段状态：`GET /api/video-deconstruction/videos/{id}/stages` 返回 4 阶段（转写/切段/镜头识别/脚本抽取）进度 · 缺 |
| 📋 | ○ | 阶段局部重跑：`POST .../videos/{id}/stages/{stageId}/rerun` · 缺 |
| 📋 | ○ | 拆解结果浏览：`GET .../videos/{id}/transcript` / `.../segments` / `.../shots` · 缺 |
| 📋 | ○ | 改写入口：`POST .../videos/{id}/adopt-to-project`（一键回流脚本） · 缺 |
| 📋 | ○ | WebSocket 阶段事件 `video.import.stage.*` · 文档已提到但需落档 |

**缺口清单**：
1. 阶段状态 & 结果浏览接口 · **D4** · P0
2. 阶段局部重跑 · **D4** · P0
3. 一键回流到脚本/分镜 · **D4** · P1

### 2.7 `voice_studio` — 配音中心

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| ✅ | ● | 基本 Voice CRUD 已文档化（`§ 5` in RUNTIME-API-CALLS） |
| 📋 | ○ | 音色库管理（自定义音色）：`POST /api/voice/profiles` · 缺 |
| 📋 | ○ | 段落级重生成：`POST /api/voice/tracks/{id}/segments/{segId}/regenerate` · 缺 |
| 📋 | ○ | 波形数据：`GET /api/voice/tracks/{id}/waveform` · 缺（前端波形图渲染用） |
| 📋 | ○ | 不写库的预览试听：`POST /api/voice/preview` · 缺 |
| 📋 | ○ | 段落停顿/呼吸参数 schema · 缺 |

### 2.8 `subtitle_alignment_center` — 字幕对齐中心

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| ✅ | ● | 基本 Subtitle CRUD 已文档化 |
| 📋 | ○ | 手动对齐接口：`POST /api/subtitles/tracks/{id}/align`（给定时间码覆盖 AI 对齐） · 缺 |
| 📋 | ○ | 样式模板：`GET /api/subtitles/style-templates` · 缺 |
| 📋 | ○ | 导出：`POST /api/subtitles/tracks/{id}/export`（SRT/VTT/ASS） · 缺 |
| 📋 | ○ | 字幕页源音频波形：`GET /api/subtitles/tracks/{id}/source-waveform` · 缺 |

### 2.9 `asset_library` — 资产中心

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| ✅ | ● | Asset CRUD + 引用 已文档化 |
| 📋 | ○ | 缩略图生成：当前无任务；资产导入后需异步生成缩略图 → 走 TaskBus · 缺 |
| 📋 | ○ | 批量操作：`POST /api/assets/batch-delete` / `batch-move-group` · 缺 |
| 📋 | ○ | 分组管理：`GET/POST/PATCH/DELETE /api/assets/groups` · 缺 |

### 2.10 `account_management` — 账号管理

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| 🚧 | ◑ | Account / AccountGroup CRUD 全部有 Router 但未进入 `RUNTIME-API-CALLS.md` |
| 🚧 | ◑ | `POST /api/accounts/{id}/refresh-stats` · 存在 |
| 📋 | ○ | 账号状态 WebSocket 广播 `account.status.changed` · 缺 |
| 📋 | ○ | 绑定关系：`PUT /api/accounts/{id}/binding`（工作区+浏览器实例） · 缺 |
| 📋 | ○ | 敏感信息脱敏（Cookie/Token 只返回 maskedXxx） · 当前需核对 |

### 2.11 `device_workspace_management` — 设备与工作区

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| 🚧 | ◑ | `/api/devices/workspaces` CRUD 存在 · 未进入文档 |
| 🚧 | ◑ | `POST .../health-check` 存在 |
| 📋 | ○ | 浏览器实例子资源：`GET/POST/DELETE /api/devices/workspaces/{id}/browsers` · 缺 |
| 📋 | ○ | 实时运行日志：WebSocket `device.log` 或 `GET .../logs?since=<cursor>` · 缺 |

### 2.12 `automation_console` — 自动化执行中心

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| 🚧 | ◑ | Automation Tasks CRUD + 手动触发 + 运行历史 · 存在未文档化 |
| 📋 | ○ | 规则配置：当前作为 `rule` JSON 字段存，需定义结构化 schema（采集/回复/同步/校验四类） · 缺 |
| 📋 | ○ | 暂停/恢复：`POST .../{id}/pause` / `.../{id}/resume` · 缺 |

### 2.13 `publishing_center` — 发布中心

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| 🚧 | ◑ | PublishPlan CRUD + precheck + submit + cancel 存在 · 未文档化 |
| 📋 | ○ | 日历聚合：`GET /api/publishing/calendar?from=YYYY-MM-DD&to=YYYY-MM-DD` · 缺 |
| 📋 | ○ | 冲突检测：当前在 `precheck` 内，需把冲突项结构化返回 · 缺 |
| 📋 | ○ | 回执追踪：`GET .../plans/{id}/receipts` · 缺 |

### 2.14 `render_export_center` — 渲染与导出中心

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| 🚧 | ◑ | Render Tasks CRUD + cancel · 存在未文档化 |
| 📋 | ○ | 导出模板：`GET /api/renders/templates` · 缺 |
| 📋 | ○ | 资源占用：`GET /api/renders/resource-usage`（CPU / GPU / disk） · 缺 |
| 📋 | ○ | 失败重试：`POST /api/renders/tasks/{id}/retry` · 缺 |
| 📋 | ○ | WebSocket 进度事件 `render.progress` · 缺 |

### 2.15 `review_optimization_center` — 复盘与优化中心

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| 🚧 | ◑ | `/api/review/projects/{id}/summary` GET/PATCH · 存在未文档化 |
| 🚧 | ◑ | `POST /api/review/projects/{id}/analyze` · 存在未文档化 |
| 📋 | ○ | AI 建议回流：`POST /api/review/projects/{id}/suggestions/{sid}/adopt` → 新建子项目 · 缺 |

### 2.16 `ai_system_settings` — AI 与系统设置

| 进度 | 状态 | 模块 |
| --- | --- | --- |
| ✅ | ● | 全部主要接口已文档化（§ 8） |
| 📋 | ○ | 日志查询：`GET /api/settings/logs?kind=system|business|task|ai|audit&since=<ts>` · 缺 |
| 📋 | ○ | 一键导出诊断包：`POST /api/settings/diagnostics/export` → 返回 zip 路径 · 缺 |
| 📋 | ○ | 迁移诊断字段(扩展 health) · 缺(见 §1.13.3) |

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
| `autosave.saved` | 草稿自动保存成功(节流 1s) | `{ ownerKind, ownerId, savedAt, version }` | 工作台/脚本/分镜 Header "保存：刚刚" |
| `autosave.conflict` | 服务端检测到版本冲突 | `{ ownerKind, ownerId, serverVersion, serverContent }` | 编辑器冲突提示 + 3-way merge |
| `draft.outdated` | 检测到草稿落后(自动恢复后通知) | `{ ownerKind, ownerId, restoredVersion }` | 编辑器 Toast 提示 |
| `upload.chunk.acked` | 上传分片确认(节流 250ms) | `{ sessionId, chunkIndex, receivedBytes, totalBytes }` | 资产/视频导入进度条 |
| `upload.session.failed` | 上传会话失败 | `{ sessionId, errorCode, errorMessage }` | 上传卡片错误态 |
| `preview.frame.ready` | 工作台预览代理帧生成完毕 | `{ timelineId, framePath, atSec }` | 工作台预览窗口 |
| `personalization.changed` | 个人化偏好变更(其他窗口同步) | `{ section, updatedAt }` | Shell 主题/侧栏宽度 |
| `migration.progress` | Alembic 迁移进度 | `{ pendingSteps, currentStep, message }` | BootstrapGate 启动屏 |
| `migration.completed` | 迁移完成 | `{ revision, durationMs }` | BootstrapGate |
| `backup.started` / `backup.completed` / `backup.failed` | 备份任务生命周期 | `{ backupId, ... }` | 设置页备份卡 |
| `audit.entry.appended` | 实时追加审计日志(可选订阅) | `AuditLogEntry` | 调试面板,默认不订阅 |

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

// § 1.8 自动保存与草稿
saveDraft(kind: DraftKind, id: string, input: DraftSaveInput): Promise<DraftSaveResult>;
fetchDraft(kind: DraftKind, id: string): Promise<DraftDto | null>;
discardDraft(kind: DraftKind, id: string): Promise<void>;

// § 1.9 大文件分片上传与流式播放
createUploadSession(input: UploadSessionInput): Promise<UploadSessionDto>;
uploadChunk(sessionId: string, chunkIndex: number, blob: Blob, sha256: string): Promise<UploadChunkAck>;
completeUpload(sessionId: string, fullSha256: string, target: 'asset'|'video'): Promise<UploadCompleteResult>;
cancelUploadSession(sessionId: string): Promise<void>;
buildMediaStreamUrl(kind: MediaKind, id: string): string;   // 仅生成 URL,真正播放交给 <video>/<audio>

// § 1.10 分页(类型工具,非具体函数)
// 所有 list 函数签名都改为 (filter & { cursor?: string, limit?: number }) => Promise<CursorPage<T>>

// § 1.11 撤销/重做
createSnapshot(kind: HistoryKind, id: string, reason: SnapshotReason): Promise<SnapshotDto>;
listSnapshots(kind: HistoryKind, id: string): Promise<SnapshotDto[]>;
restoreSnapshot(kind: HistoryKind, id: string, snapshotId: string): Promise<RestoreResult>;

// § 1.12 个人化
fetchPersonalization(): Promise<UserPersonalization>;
updatePersonalization(patch: Partial<UserPersonalization>): Promise<UserPersonalization>;
updatePersonalizationSection<K extends keyof UserPersonalization>(key: K, value: UserPersonalization[K]): Promise<void>;

// § 1.13 审计/备份/迁移
fetchAuditLogs(filter: AuditFilter & { cursor?: string }): Promise<CursorPage<AuditLogEntry>>;
createBackup(): Promise<BackupSnapshotDto>;
listBackups(): Promise<BackupSnapshotDto[]>;
restoreBackup(backupId: string): Promise<RestoreReport>;
deleteBackup(backupId: string): Promise<void>;

// § 2.1 补充
fetchLicenseFingerprint(): Promise<LicenseFingerprintDto>;
skipBootstrapWizard(): Promise<LimitedModeStatus>;
fetchLimitedModeStatus(): Promise<LimitedModeStatus>;

// § 2.2 补充
fetchDashboardSparklines(metrics: SparklineMetric[], windowHours: number): Promise<SparklineSeries[]>;

// § 2.5 补充
exportTimeline(timelineId: string, format: 'edl'|'fcpxml'|'premiere'): Promise<TimelineExportDto>;

// § 2.7 补充
previewVoice(input: VoicePreviewInput): Promise<VoicePreviewDto>;

// § 2.8 补充
fetchSubtitleSourceWaveform(trackId: string): Promise<WaveformDto>;
```

以上 **约 50 个新函数(原)+ 28 个补充 = 约 78 个新函数**。加上现有 24 个，总契约面约 102 个 HTTP 入口 + 35 种 WebSocket 消息。

---

**文档结束。** 任何新增接口落地前，必须在 `docs/RUNTIME-API-CALLS.md` 添加详尽定义。本文件只做需求驱动与排期。
