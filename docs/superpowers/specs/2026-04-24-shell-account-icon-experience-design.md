# Shell、账号链路与品牌图标体验改造设计说明

> 对应计划：`docs/superpowers/plans/2026-04-24-shell-account-icon-experience.md`  
> 设计状态：待审批。审批通过后进入实现。

## 1. 设计目标

本设计将用户提出的四项体验问题拆成一个可执行的交付链：

1. 修复账号管理页“查询账号列表失败”的真实 Runtime schema 根因。
2. 移除顶部栏常驻搜索框，改为顶部显式控制右侧 Detail Panel 的按钮。
3. 优化桌面壳层的左中右栏密度、字号和紧凑窗口行为，使主工作区优先。
4. 设计并接入新的 TK-OPS 品牌标记，替换左上与左下现有深蓝/青紫渐变图像。

## 2. 非目标

- 不删除 `/api/search`、`searchGlobal()` 或未来全局搜索能力；本轮只移除顶部栏常驻搜索 UI。
- 不新增正式页面，不改变 16 页页面树。
- 不新增假账号、假统计、假设备、假绑定。
- 不把账号错误变成前端静默空列表。
- 不引入 GSAP、Three.js、WebGL 或新的动效依赖。
- 不直接覆盖根目录 `tkops.ico`；应用级 ico 替换需要在 shell 图标通过后单独确认。

## 3. Runtime 设计：账号表兼容修复

### 3.1 问题复现

当前本地 `.runtime-data/runtime.db` 的 `accounts` 表仍是旧执行域模型：

```text
id, platform, handle, display_name, group_name, status, source, metadata_json, created_at, name, updated_at, last_validated_at
```

当前 `domain.models.account.Account` 与 `AccountRepository.list_accounts()` 需要：

```text
id, name, platform, username, avatar_url, status, auth_expires_at,
follower_count, following_count, video_count, tags, notes,
last_validated_at, created_at, updated_at
```

因此查询阶段抛出 `no such column: accounts.username`。即使补齐缺列，旧表中 `handle / display_name / group_name / source / metadata_json` 是无默认值的 `NOT NULL` 列，也会阻断新账号写入。

### 3.2 修复策略

在 `apps/py-runtime/src/persistence/engine.py` 中升级 `_repair_legacy_account_schema()`：

1. 先通过 `_ensure_table_columns()` 补齐当前模型需要的所有列，保证只缺少 nullable 列的轻度旧库可以直接修复。
2. 回填字段：
   - `name = display_name || handle || id`
   - `username = username || handle`
   - `platform = platform || "tiktok"`
   - `status = status || "active"`
   - `created_at = created_at || fallback_time`
   - `updated_at = updated_at || created_at || fallback_time`
3. 检测阻断型旧列：
   - `handle`
   - `display_name`
   - `group_name`
   - `source`
   - `metadata_json`
4. 如果阻断型旧列存在且会影响当前 ORM 写入，则执行 `_rebuild_legacy_account_table(engine)`。
5. 重建表时禁用外键、创建 `accounts_repaired`、搬运当前字段、删除旧表、重命名新表、恢复外键。

### 3.3 重建后的账号表

重建表保留当前模型字段：

```sql
CREATE TABLE accounts_repaired (
  id VARCHAR PRIMARY KEY,
  name TEXT NOT NULL,
  platform VARCHAR NOT NULL DEFAULT 'tiktok',
  username TEXT,
  avatar_url TEXT,
  status VARCHAR NOT NULL DEFAULT 'active',
  auth_expires_at TEXT,
  follower_count INTEGER,
  following_count INTEGER,
  video_count INTEGER,
  tags TEXT,
  notes TEXT,
  last_validated_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

数据搬运表达式按旧列存在性动态生成，避免引用不存在列：

- `name_expr`: `COALESCE(NULLIF(name, ''), NULLIF(display_name, ''), NULLIF(handle, ''), id)`
- `username_expr`: `COALESCE(NULLIF(username, ''), NULLIF(handle, ''))`
- `platform_expr`: `COALESCE(NULLIF(platform, ''), 'tiktok')`
- `status_expr`: `COALESCE(NULLIF(status, ''), 'active')`
- 其他当前字段不存在时填 `NULL`。

### 3.4 Runtime 错误与日志

- 服务层继续使用 `log.exception("查询账号列表失败")` 捕获不可预期异常。
- 失败响应继续走统一错误信封，不向 UI 暴露 traceback。
- 修复后账号空列表应返回 `{ ok: true, data: [] }`，前端显示账号页空态。

### 3.5 Runtime 测试

新增或扩展测试覆盖：

1. 遗留旧账号表只有旧列时，`initialize_domain_schema(engine)` 后 `AccountRepository.list_accounts()` 可返回旧账号。
2. 旧账号 `display_name / handle` 被回填到 `name / username`。
3. 初始化后 `AccountRepository.create_account()` 可以写入新账号，不被旧 `NOT NULL` 列阻断。
4. `/api/accounts` 契约仍返回 `publishReadiness`。

## 4. 前端设计：顶部栏与右侧抽屉按钮

### 4.1 顶部栏结构

`ShellTitleBar.vue` 改为三段：

```text
左侧：Sidebar toggle + BrandMark + TK-OPS + 当前项目
中间：当前页面标题 / 空闲拖拽区域
右侧：AI 状态 + Runtime 状态 + 授权状态 + 右侧详情按钮 + 主题 + 设置 + 窗口控制
```

移除：

- `.shell-search`
- `.shell-search__input`
- `.shell-search__shortcut`
- 顶部栏中间常驻搜索框相关 DOM 和样式

保留：

- 中间区作为拖拽区域，必要时展示 `pageTitle`，避免顶部栏视觉空洞。
- `pageTitle` 只显示当前页面中文名称，不描述功能或快捷键。

### 4.2 右侧抽屉按钮

新增按钮位置：右侧状态区与主题按钮之间。

按钮规则：

- 图标：`right_panel_open` / `right_panel_close`
- 打开态 title/aria-label：`收起右侧详情`
- 关闭态 title/aria-label：`展开右侧详情`
- `detailPanelMode === "hidden"` 或向导页时隐藏按钮。
- 点击后只触发既有 `emit("toggle-detail")`。
- 不直接操作 store，状态仍由 `AppShell.vue` 与 `shell-ui` store 管理。

`ShellTitleBar.vue` 新增或调整 props：

```ts
detailOpen: boolean
showDetailToggle: boolean
```

`AppShell.vue` 传入：

```vue
:show-detail-toggle="showWorkspaceChrome && detailPanelMode !== 'hidden'"
```

### 4.3 可访问性

- 顶部按钮使用真实 `button`。
- 设置 `type="button"`，避免默认表单行为。
- 保持 `-webkit-app-region: no-drag`，不影响标题栏拖拽。
- `focus-visible` 使用品牌色 outline。

## 5. 前端设计：Codex 式三栏与紧凑窗口策略

### 5.1 壳层断点

沿用现有 token：

- `--sidebar-width-expanded: 280px`
- `--sidebar-width-collapsed: 64px`
- `--detail-panel-width: 360px`
- `--detail-panel-width-wide: 480px`
- `--titlebar-height: 48px`
- `--statusbar-height: 28px`

行为调整：

| 窗口宽度 | Sidebar | Detail Panel | 主工作区 |
| --- | --- | --- | --- |
| `>= 1600px` | 展开 | 可常驻 | 最大化内容密度 |
| `1200px - 1599px` | 展开，Detail 打开时可自动折叠 | 宽度足够才并排，否则收起为窄详情轨 | 优先保留主工作区 |
| `960px - 1199px` | 默认折叠或用户折叠 | 窄详情轨，按需进入详情焦点视图 | 不被详情面板挤压或遮挡 |
| `< 960px` | 左侧浮层导航只在导航时出现 | 窄详情入口，详情用焦点视图承载 | 单列主工作区 |

### 5.2 主窗口工作区优先硬约束

主窗口工作区优先是本轮壳层改造的硬约束，不只是视觉偏好。实现时按以下顺序保护空间：

1. 当横向空间不足时，先压缩顶部栏状态文本和项目名，不压缩窗口控制按钮。
2. 其次折叠 Sidebar 到 `--sidebar-width-collapsed`。
3. 再让 Detail Panel 从 grid 常驻列收起为窄详情轨。
4. 最后才允许页面主内容区在自己的滚动容器内换行或滚动。
5. 禁止 Detail Panel 以常驻列方式把 Content Host 挤压到低于 `--content-min-width`。
6. 禁止默认使用覆盖式右侧浮层遮挡主工作区信息。

实现判定：

- `Content Host` 的最小可用宽度以 `--content-min-width` 为底线。
- 当 `viewportWidth - sidebarWidth - detailWidth < --content-min-width` 时，Detail Panel 必须收起为窄详情轨，而不是覆盖在主工作区上方。
- 当窗口 `< 960px` 时，Content Host 占据主 grid；Detail Panel 只保留入口，详情内容进入非遮挡的焦点视图。
- 详情焦点视图在 Content Host 内切换，不改变当前路由、不清空页面状态，并提供“返回工作区”按钮。
- 未 pin 的详情面板在页面切换、对象取消选中或窗口变窄时自动回到窄详情轨，减少手动关闭负担。
- 页面内时间线、任务队列、账号列表、编辑器等核心区域不得因为右侧详情打开而出现不可用的横向挤压。

### 5.3 主工作区保护

现有 `shouldProtectWorkspace` 逻辑保留并微调：

- 当窗口小于 `1440px` 且右侧详情打开时，Sidebar 使用 `effectiveSidebarCollapsed`。
- 当窗口小于 `1200px` 或计算后 Content Host 会低于 `--content-min-width` 时，Detail Panel 从完整列退化为窄详情轨。
- 详情轨宽度建议为 `44px`，只显示当前上下文图标、状态点和展开入口。
- 右侧完整面板宽度使用：

```css
width: var(--detail-panel-width);
```

完整面板只在满足主工作区最小宽度时并排展开。

### 5.4 字号与密度

不整体重写字体系统，只调整 shell 级密度：

- 顶部品牌名：`var(--font-title-sm)`
- 当前项目：`var(--font-body-sm)` 或 `var(--font-body-md)`
- 页面标题：`var(--font-title-sm)`
- 状态文案：`var(--font-caption)`
- Sidebar 项：`var(--font-body-sm)` 或保留当前 `var(--font-title-sm)`，不使用 display 级别字号
- 新增或修改区域的 `letter-spacing` 使用 `0`

### 5.5 动效

- 使用现有 `var(--motion-fast)` 与 `var(--motion-default)`。
- 面板开合只做位移与透明度。
- `data-reduced-motion="true"` 下由现有 token 降级到近似即时切换。
- 不新增循环背景动画。

## 6. 品牌图标设计

### 6.1 视觉方向

新图标表达“AI 视频创作中枢”，由三类元素组成：

1. 视频帧：代表剪辑与内容创作。
2. 播放三角或时间线切片：代表短视频生产。
3. AI 节点/连接点：代表脚本、分镜、配音、字幕和渲染链路的智能编排。

视觉口径：

- 不再用纯深蓝/紫蓝渐变方块当图像。
- 小尺寸优先，20px 时仍能看清轮廓。
- Light / Dark 下都保持对比。
- 不使用英文 slogan，不在小图标内塞完整文字。

### 6.2 实现方式

新增 `apps/desktop/src/components/brand/TkopsBrandMark.vue`。

组件 props：

```ts
type BrandMarkSize = "sm" | "md" | "lg"
type BrandMarkTone = "brand" | "creator"

defineProps<{
  size?: BrandMarkSize
  tone?: BrandMarkTone
  title?: string
}>()
```

组件输出：

- 使用内联 SVG，保证确定性和小尺寸锐度。
- `sm` 用于顶部栏 20px。
- `md` 用于侧栏底部 32px。
- `lg` 预留给首启页或后续应用图标预览。
- 用 CSS variables 控制色彩，不硬编码深蓝图像。

### 6.3 接入位置

替换：

- `ShellTitleBar.vue` 中 `.shell-brand__logo`
- `ShellSidebar.vue` 中 `.shell-sidebar__avatar`

不在本轮替换：

- 根目录 `tkops.ico`
- Tauri `tauri.conf.json` 的 package icon

后续如果用户确认图标方向，再单独生成应用级 `.ico` 与多尺寸 PNG。

## 7. 数据流与状态流

### 7.1 账号页

```text
AccountManagementPage.vue
  -> useAccountManagementStore.load()
  -> fetchAccounts()
  -> GET /api/accounts
  -> AccountService.list_accounts()
  -> AccountRepository.list_accounts()
  -> SQLite accounts 表
```

修复后：

- Runtime 初始化阶段修复旧表。
- 前端 store 不改变正常路径。
- 如果列表为空，`store.status = "empty"`，页面显示空态。
- 如果 Runtime 仍失败，页面显示 `store.error`，可点击“重新拉取”重试。

### 7.2 右侧详情面板

```text
ShellTitleBar detail button
  -> emit("toggle-detail")
  -> AppShell.handleToggleDetailPanel()
  -> AppShell 判断 docked / rail / focus 模式
  -> shellUiStore.toggleDetailPanel()
  -> AppShell data-detail-open + data-detail-presentation
  -> ShellDetailPanel docked / rail / focus
```

页面上下文仍通过 `route.meta.detailPanelMode` 与 `syncDetailContext()` 注入，不新增第二套详情状态。

详情展示规则：

- `docked`：宽度足够时，右侧详情以常驻列并排显示。
- `rail`：宽度不足时，右侧只显示 44px 详情轨，不展示完整内容。
- `focus`：用户需要查看完整详情且宽度不足时，在 Content Host 内切换到详情焦点视图，顶部提供“返回工作区”；不使用遮挡式右侧浮层。

## 8. 测试设计

### 8.1 Runtime

命令：

```powershell
venv/Scripts/python.exe -m pytest tests/runtime/test_account_device_binding_service.py tests/runtime/test_render_schema_migration.py tests/contracts/test_accounts_runtime_contract.py -q
```

验收：

- 遗留账号表可修复。
- 当前账号 DTO 契约不变。
- `/api/accounts` 返回 `publishReadiness`。
- 新账号可创建，证明旧 `NOT NULL` 列已不再阻断。

### 8.2 前端单测

命令：

```powershell
npm --prefix apps/desktop run test -- app-shell shell-layout-contract account-management
```

如果 Vitest 定向参数与当前配置不匹配，则运行：

```powershell
npm --prefix apps/desktop run test
```

验收：

- 顶部栏不再存在搜索 input。
- 右侧详情按钮按 `detailOpen` 切换 title/aria 和 icon。
- `showDetailToggle=false` 时按钮不渲染。
- 账号页面仍能在 loading / empty / ready / error 下渲染。

### 8.3 Build

命令：

```powershell
npm --prefix apps/desktop run build
```

验收：

- TypeScript 无类型错误。
- Vue 模板无编译错误。

### 8.4 UI 证据

实现后需要提供：

- 宽屏截图：Sidebar 展开、Detail Panel 可打开。
- 紧凑窗口截图：Sidebar 折叠、Detail Panel 退化为窄详情轨，不遮挡主工作区或窗口控制。
- Light / Dark 下 BrandMark 可读性说明。

## 9. 风险与缓解

### 9.1 旧库重建风险

风险：重建 `accounts` 表可能影响 `execution_bindings` 或 `account_group_members` 外键。

缓解：
- 重建期间关闭 SQLite foreign keys。
- 保持账号 `id` 不变。
- 不修改 `execution_bindings` 和 `account_group_members` 表。
- 测试覆盖已有账号读取和新账号写入。

### 9.2 顶部栏空间不足

风险：移除搜索后新增按钮仍可能与状态区、窗口按钮拥挤。

缓解：
- `<760px` 继续隐藏状态文本和许可证 chip。
- 右侧按钮固定 32px，不随文字变化。
- 项目名和状态文本使用 `text-overflow: ellipsis`。

### 9.3 icon 小尺寸辨识度不足

风险：复杂 icon 在 20px 顶栏不可读。

缓解：
- 内联 SVG 使用少量几何元素。
- 顶栏 `sm` 版本隐藏次要节点，只保留视频帧和播放/时间线主体。
- 侧栏 `md` 版本显示完整 AI 节点。

## 10. 验收标准

- 账号管理不再因为旧 `accounts` 表缺列而提示“查询账号列表失败”。
- 顶部栏搜索框被移除。
- 顶部栏出现右侧详情开合按钮，且状态、中文 title、aria-label 正确。
- 右侧详情沿用 `Detail Panel`，没有新增旁路抽屉系统。
- 宽屏和紧凑窗口下主窗口工作区优先：当空间不足时先折叠 Sidebar，再把 Detail Panel 收起为窄详情轨，Content Host 不低于 `--content-min-width`，默认不使用遮挡式右侧浮层。
- 左上品牌图像和左下创作者头像位置不再使用旧渐变方块。
- 新增或修改注释为中文，且只解释必要边界。
- 相关 Runtime 测试、前端测试和前端 build 有执行结果。
