# Shell、账号链路与品牌图标体验改造计划

> 计划状态：待审批。  
> 审批规则：本计划通过后，再生成 `docs/superpowers/specs/2026-04-24-shell-account-icon-experience-design.md`，spec 通过后才进入代码实现。

## 1. 目标

围绕用户提出的四个体验问题，分阶段恢复账号管理真实数据链路，并优化 TK-OPS 桌面壳的顶部栏、右侧抽屉、三栏响应式布局和品牌图标。

## 2. 用户确认的优先级

1. 先修复“账号管理一直提示查询账号列表失败”。
2. 再取消顶部栏搜索，新增右侧抽屉展开/收起按钮。
3. 参考 Codex 应用的左中右栏交互、布局密度、字号和不同尺寸处理，优化 TK-OPS 壳层体验。
4. 设计新的项目 icon，替换左上品牌标识和左下创作者头像位置的深蓝渐变图像。

## 3. Council roles

- Project Leader：当前主线程，负责范围拆分、计划审批、最终整合。
- Product Manager：确认仍围绕 AI 视频创作中枢，不扩展旧后台范围。
- TK Operations：确认账号、设备、工作区仍是真实对象，不做假绑定。
- Creative Director：定义壳层与 icon 的视觉方向，避免泛后台和深蓝渐变占位感。
- Interaction Designer：定义顶部栏、右侧抽屉、紧凑窗口下的交互状态。
- Frontend Lead：负责 Vue/Tauri 壳层、Pinia 状态、CSS token、桌面测试。
- Backend Runtime Lead：负责账号 schema 修复、服务层日志、错误信封。
- Data & Contract Agent：负责账号 DTO、迁移修复、契约测试。
- QA & Verification Agent：负责复现路径、自动化测试、宽屏/紧凑布局验收。
- Independent Reviewer：实现完成前按决策 rubric 做最终阻断项检查。

本轮不使用真实 subagents；当前会在主线程内模拟角色结论。

## 4. Facts found

- 产品真源仍为 `docs/PRD.md`，正式页面固定 16 页。
- UI 真源要求壳层稳定为 `Title Bar + Sidebar + Content Host + Detail Panel + Status Bar`。
- 右侧抽屉应落在 `Detail Panel` 的开合与紧凑窗口 drawer 逻辑中，而不是新增第 17 个页面或旁路面板。
- 当前 `ShellTitleBar.vue` 中间区存在全局搜索输入；用户要求取消它。
- 当前 `AppShell.vue` 已有 `@toggle-detail` 事件、`isDetailPanelOpen` 状态和 `ShellDetailPanel.vue`，但顶部栏没有显式右侧抽屉按钮。
- 当前顶部左上品牌块和左下创作者头像都使用 `var(--gradient-ai-primary)`，观感接近深蓝/青紫渐变占位。
- 账号错误已复现到 Runtime 根因：本地 `.runtime-data/runtime.db` 的遗留 `accounts` 表仍保留旧列 `handle / display_name / group_name / source / metadata_json`，缺少当前模型查询需要的 `username / avatar_url / auth_expires_at / follower_count / following_count / video_count / tags / notes` 等列。
- 直接调用 `AccountRepository.list_accounts()` 抛出 `sqlite3.OperationalError: no such column: accounts.username`，前端收到服务层中文错误“查询账号列表失败”。
- 当前 `_repair_legacy_account_schema()` 只补 `name / last_validated_at / created_at / updated_at`，不足以修复旧表，也没有重建带阻断 `NOT NULL` 旧列的账号表。
- 工作区已有未归属本任务的改动：`apps/desktop/src/modules/settings/components/AICapabilityMatrix.vue` 与 `apps/desktop/tests/ai-settings-layout-contract.spec.ts`。本计划不得覆盖或回退它们。

## 5. Role consensus

- Product Manager：通过，范围仍在账号管理与创作工作台壳层，不引入订单、商品、CRM 或团队后台。
- TK Operations：条件通过，账号页只能展示真实 Runtime 返回的账号、分组和绑定状态；无数据时用空态，不补假账号。
- Backend Runtime Lead：条件通过，账号修复必须在持久化 schema 修复层解决，不在前端吞错或伪造空列表。
- Data & Contract Agent：条件通过，必须补覆盖遗留 accounts 表的迁移测试，至少验证 `list_accounts()` 和 `create_account()` 都可用。
- Creative Director：条件通过，icon 应是“AI 视频创作中枢”的识别符号，不继续使用泛渐变方块。
- Interaction Designer：条件通过，右侧详情应有明确按钮、aria label、状态文案和紧凑窗口抽屉行为。
- Frontend Lead：通过，优先复用 `shell-ui` store、`ShellDetailPanel`、CSS tokens 与现有 shell 测试。
- QA & Verification Agent：条件通过，必须跑 Runtime 相关测试、桌面壳层测试、前端 build，并提供紧凑/宽屏截图或说明。
- Independent Reviewer：当前计划可进入审批，评分 8.1/10；阻断项是“未审批前不得直接实现”。

## 6. Leader decision

采用“先热修 Runtime，再做壳层体验，再做 icon 资产”的分阶段方案。

不采用一次性大改方案，因为账号页错误是数据层真实故障，必须先恢复真实链路。  
不采用 UI 兜底空列表方案，因为会掩盖 Runtime schema 破损。  
不采用新增独立抽屉系统方案，因为现有 `Detail Panel` 已是 UI 真源定义的右侧上下文容器。

## 7. 阶段计划

### 阶段一：账号列表失败热修

目标：修复遗留 `accounts` 表 schema，恢复 `/api/accounts` 真实列表查询和创建账号能力。

边界：
- 只处理账号 schema 修复、账号服务契约测试和必要文档记录。
- 不改变账号管理页面的信息架构。
- 不新增假账号、假统计或假绑定。

文件地图：
- 修改：`apps/py-runtime/src/persistence/engine.py`
- 测试：`tests/runtime/test_render_schema_migration.py` 或新增 `tests/runtime/test_account_schema_repair.py`
- 测试：`tests/contracts/test_accounts_runtime_contract.py`

验证方式：
- 先新增遗留账号表测试，复现缺列与旧 `NOT NULL` 列阻断。
- 修复后验证 `AccountRepository.list_accounts()` 不再抛错。
- 修复后验证 `AccountRepository.create_account()` 可以写入当前模型字段。
- 运行 `venv/Scripts/python.exe -m pytest tests/runtime/test_account_device_binding_service.py tests/runtime/test_render_schema_migration.py tests/contracts/test_accounts_runtime_contract.py -q`。

回退点：
- 若新迁移影响旧库，回退 `engine.py` 中账号表重建逻辑，保留测试失败证据，不触碰前端。

### 阶段二：顶部栏与右侧抽屉入口

目标：取消顶部栏搜索输入，在顶部栏右侧新增 Detail Panel 展开/收起按钮。

边界：
- 不删除 Runtime 搜索接口，不删除未来全局搜索能力，只从顶部常驻栏移除搜索 UI。
- 不新增独立右侧抽屉状态，复用 `shell-ui` 的 `detailPanelOpen`。
- `detailPanelMode === "hidden"` 时按钮禁用或隐藏，并给出可访问标签。

文件地图：
- 修改：`apps/desktop/src/layouts/shell/ShellTitleBar.vue`
- 修改：`apps/desktop/src/layouts/AppShell.vue`
- 可能修改：`apps/desktop/src/styles/shell.css` 或 shell scoped styles
- 测试：`apps/desktop/tests/app-shell.spec.ts`
- 测试：`apps/desktop/tests/shell-layout-contract.spec.ts`

验证方式：
- 顶部栏不再渲染搜索 input。
- 有可点击按钮触发 `toggle-detail`。
- 右侧面板开启和关闭状态在 DOM data 属性中可验证。
- 运行 `npm --prefix apps/desktop run test -- app-shell shell-layout-contract`；若当前脚本不支持定向参数，则运行对应项目测试命令并说明。

回退点：
- 若按钮破坏标题栏拖拽或窗口控制，回退 `ShellTitleBar.vue` 的按钮布局，保留 AppShell 现有状态。

### 阶段三：Codex 式左中右栏体验优化

目标：参考 Codex 应用的左侧导航、中间主工作区、右侧上下文面板的密度与响应式行为，优化 TK-OPS 壳层。

设计原则：
- 仍然保持 TK-OPS 的 `AI 视频创作中枢` 定位，不复制 Codex 品牌或视觉。
- 字号更接近桌面工作台：顶部栏、侧栏、状态栏以 12-14px 为主，页面标题不过度放大。
- 宽屏保留 Sidebar + Content + Detail Panel。
- 标准桌面按需打开 Detail Panel。
- 紧凑窗口优先折叠 Sidebar，Detail Panel 默认收起为窄详情轨；只有宽度足够时才并排展开，禁止用覆盖式浮层遮挡主工作区。

文件地图：
- 修改：`apps/desktop/src/layouts/AppShell.vue`
- 修改：`apps/desktop/src/layouts/shell/ShellSidebar.vue`
- 修改：`apps/desktop/src/layouts/shell/ShellTitleBar.vue`
- 修改：`apps/desktop/src/layouts/shell/ShellDetailPanel.vue`
- 可能修改：`apps/desktop/src/styles/tokens/typography.css`
- 可能修改：`apps/desktop/src/styles/tokens/spacing.css`
- 测试：`apps/desktop/tests/page-responsive-layout-contract.spec.ts`
- 测试：`apps/desktop/tests/shell-layout-contract.spec.ts`

验证方式：
- 宽屏与紧凑断点都有明确布局契约。
- 关键文本不溢出、不遮挡窗口按钮、不压缩主工作区。
- 支持 `prefers-reduced-motion` 或当前 `reducedMotion` 状态。
- 通过 Playwright 或现有前端测试截图验证宽屏与紧凑窗口。

回退点：
- 保留现有 shell 宽度 token，若新布局影响核心页面，先回退断点策略，不回退账号热修。

### 阶段四：品牌 icon 与壳层替换

目标：设计新的 TK-OPS icon，并替换左上品牌标识和左下创作者头像位置的深蓝渐变图像。

视觉方向：
- 图标应表达“AI 视频创作中枢”：视频帧、时间线、生成节点或播放形态可以作为抽象元素。
- 避免深蓝/紫蓝渐变方块继续作为唯一识别。
- 需要同时适配 20px 顶栏、32px 侧栏底部、应用图标尺寸。

资产策略：
- 优先用确定性 SVG / CSS / icon 组件承载壳层小尺寸标识。
- 如需要应用级 bitmap/ico，可用 image generation 先做候选，再转为项目资产。
- 不覆盖根目录 `tkops.ico`，除非用户明确批准最终替换；先生成新版本文件。

文件地图：
- 可能新增：`apps/desktop/src/components/brand/TkopsBrandMark.vue`
- 可能新增：`apps/desktop/src/assets/brand/`
- 修改：`apps/desktop/src/layouts/shell/ShellTitleBar.vue`
- 修改：`apps/desktop/src/layouts/shell/ShellSidebar.vue`
- 可能修改：`apps/desktop/src-tauri/tauri.conf.json`
- 测试：`apps/desktop/tests/shell-layout-contract.spec.ts`

验证方式：
- 左上和左下均替换旧渐变方块。
- Light / Dark 主题下保持清晰。
- 20px、32px、小窗口下不糊、不压缩、不遮挡。
- 若生成 bitmap，最终资产必须保存到 workspace，不能只留在 `$CODEX_HOME/generated_images`。

回退点：
- 壳层组件先接入新 BrandMark；应用 ico 替换单独提交，避免影响打包。

## 8. Runtime contract notes

API boundary:
- `/api/accounts` 继续返回统一信封 `{ ok: true, data: AccountDto[] }`。
- 失败仍通过 FastAPI exception handler 返回 `{ ok: false, error: "中文错误" }`。

Data contract:
- `AccountDto` 当前字段不变。
- 修复重点在旧 SQLite 表到当前 `domain.models.account.Account` 的兼容。
- 不新增前端独有字段。

Task/event flow:
- 本轮账号列表修复不是长任务，不新增 TaskBus 或 WebSocket 事件。

Frontend integration:
- 账号页面继续通过 `fetchAccounts()` 和 `useAccountManagementStore.load()` 消费 Runtime。
- 前端不新增假空列表兜底。

Error/logging behavior:
- 保留服务层 `log.exception("查询账号列表失败")`。
- 修复后如果仍失败，UI 显示真实中文错误，不显示 traceback。

Verification:
- Runtime schema 修复测试。
- Account service/contract 测试。
- 账号页面现有前端测试回归。

Blockers:
- 未通过计划审批前不进入实现。
- 未通过 spec 审批前不替换 icon 或改壳层体验代码。

## 9. UI council notes

Visual thesis:
- TK-OPS 壳层应像一个克制、密度高、状态清晰的 AI 视频创作工作台，通过稳定三栏、真实状态和可识别品牌标记建立信任。

Primary workspace:
- 主工作区永远优先于装饰；右侧 Detail Panel 只作为上下文、日志、属性和预览辅助。

Core interaction:
- 顶部栏按钮控制右侧详情开合。
- Sidebar 优先折叠，Detail Panel 在紧凑窗口退化为窄详情轨；需要长读时进入非遮挡的详情焦点视图。
- 状态栏继续承担 Runtime、AI、任务和同步状态反馈。

Motion purpose:
- 仅用于面板开合、状态确认和上下文切换。
- 不新增 GSAP、Three.js 或重动效依赖。

State coverage:
- 顶部栏按钮覆盖 enabled、disabled、open、closed、hover、focus-visible。
- Detail Panel 覆盖 hidden、contextual、asset、logs、binding、settings。
- 账号页覆盖 loading、empty、ready、error。

Performance/fallback:
- 用 CSS transition 和已有 `reducedMotion` 状态；紧凑窗口不用昂贵动画。

Review verdict:
- 可进入计划审批；实现前需要 spec 固化具体布局尺寸、按钮位置和 icon 方向。

## 10. Acceptance gates

- 不回退旧 PySide6 壳。
- 不新增正式第 17 页。
- 不新增假账号、假统计、假设备绑定。
- 账号列表失败在当前 `.runtime-data/runtime.db` 上可通过 schema 初始化修复。
- 所有 Runtime 响应继续使用统一 JSON 信封。
- 前端所有数据请求继续通过 Runtime client。
- 顶部搜索 UI 被移除，但搜索接口和未来能力不被删除。
- 右侧抽屉按钮具备中文 title / aria-label。
- 主窗口工作区优先：空间不足时先折叠 Sidebar，再把 Detail Panel 收起为窄详情轨，禁止右侧面板遮挡或把 Content Host 挤压到不可用。
- 宽屏和紧凑窗口布局都有测试或截图证据。
- Light / Dark 主题下新 icon 与壳层元素可读。
- 不覆盖用户未归属本任务的现有改动。

## 11. Implementation checklist

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this checklist task-by-task. 本次用户未要求 subagents，默认由主线程内联执行。  
> **Branch:** `codex/shell-account-icon-experience`

### Task 1: Runtime 账号旧表修复

**Files:**
- Modify: `apps/py-runtime/src/persistence/engine.py`
- Test: `tests/runtime/test_render_schema_migration.py`
- Test: `tests/contracts/test_accounts_runtime_contract.py`

- [ ] 写一个遗留 `accounts` 表测试：旧表只有 `handle / display_name / group_name / source / metadata_json` 等旧列时，初始化后 `AccountRepository.list_accounts()` 能返回账号。
- [ ] 运行该测试，确认先失败，失败原因是 `accounts.username` 缺列或旧表写入阻断。
- [ ] 在 `engine.py` 补齐当前账号列、字段回填、阻断旧列检测与 `_rebuild_legacy_account_table()`。
- [ ] 再运行账号迁移与账号契约测试，确认旧库可读、新账号可写、`publishReadiness` 契约不变。

### Task 2: 顶部栏搜索移除与详情按钮

**Files:**
- Modify: `apps/desktop/src/layouts/shell/ShellTitleBar.vue`
- Modify: `apps/desktop/src/layouts/AppShell.vue`
- Test: `apps/desktop/tests/app-shell.spec.ts`
- Test: `apps/desktop/tests/shell-layout-contract.spec.ts`

- [ ] 先更新 shell 测试，要求顶部搜索 input 不存在，并要求右侧详情按钮按 `detailOpen` 切换文案和图标。
- [ ] 运行前端定向测试，确认先失败。
- [ ] 移除 `.shell-search` DOM 与样式，把中间区改为当前页面标题和拖拽空间。
- [ ] 增加 `showDetailToggle` prop，并让按钮只 emit `toggle-detail`。
- [ ] 在 `AppShell.vue` 传入 `showWorkspaceChrome && detailPanelMode !== "hidden"`。

### Task 3: 主工作区优先的 Detail Panel 表现

**Files:**
- Modify: `apps/desktop/src/layouts/AppShell.vue`
- Modify: `apps/desktop/src/layouts/shell/ShellDetailPanel.vue`
- Test: `apps/desktop/tests/shell-layout-contract.spec.ts`

- [ ] 先更新布局契约测试：空间不足时 Detail Panel 使用窄详情轨，不允许默认 absolute 覆盖主工作区。
- [ ] 运行测试确认失败。
- [ ] 增加 `detailPresentation`：`docked | rail | focus`。
- [ ] 为 `AppShell` 增加 `data-detail-presentation`，在 CSS 中实现 docked 完整列、rail 44px 窄轨、focus 非遮挡视图入口。
- [ ] 保留 `--content-min-width`，确保空间不足时不会把 Content Host 挤压到不可用。

### Task 4: BrandMark 接入

**Files:**
- Create: `apps/desktop/src/components/brand/TkopsBrandMark.vue`
- Modify: `apps/desktop/src/layouts/shell/ShellTitleBar.vue`
- Modify: `apps/desktop/src/layouts/shell/ShellSidebar.vue`
- Test: `apps/desktop/tests/shell-layout-contract.spec.ts`

- [ ] 先补测试，要求旧渐变 logo/avatar 类不再作为图像，壳层引用 `TkopsBrandMark`。
- [ ] 运行测试确认失败。
- [ ] 新建内联 SVG BrandMark，支持 `sm/md/lg` 和中文 `title`。
- [ ] 替换左上品牌块和左下创作者头像位置。
- [ ] 保持 Light / Dark 通过 CSS variables 控制。

### Task 5: Verification

**Commands:**
- `venv/Scripts/python.exe -m pytest tests/runtime/test_account_device_binding_service.py tests/runtime/test_render_schema_migration.py tests/contracts/test_accounts_runtime_contract.py -q`
- `npm --prefix apps/desktop run test -- app-shell shell-layout-contract account-management`
- `npm --prefix apps/desktop run build`

- [ ] 运行 Runtime 相关测试。
- [ ] 运行前端相关测试。
- [ ] 运行前端 build。
- [ ] 用浏览器或测试截图确认宽屏与紧凑窗口的主工作区优先行为。
