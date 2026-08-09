# P0-G 补丁：未保存决策与定位版本可读性修复规格

> 日期：2026-08-02  
> 状态：已完成，0.4.8 测试制品已验收  
> 对应计划：`docs/superpowers/plans/2026-08-02-unsaved-dialog-positioning-version-ux-fix.md`  
> 目标版本：`0.4.8`  
> 适用边界：Desktop、Runtime API v1、账号定位版本、测试与 Windows 测试制品

> 2026-08-08 验收补充：`0.4.8` 免安装包根目录的第二个 Runtime EXE 不是用户入口。补丁版本升为 `0.4.9`，Desktop 从 `resources/runtime/tk-ops-runtime.exe` 的受控资源路径启动 Runtime；GUI smoke 必须断言根目录只有一个 EXE，且内部 Runtime 仍能 ready、单实例运行并随 Desktop 退出。

## 1. 规格目标

本规格只解决以下两个已复现缺陷，并完成对应版本交付：

1. 未保存内容弹窗的“取消”“放弃并继续”“保存并继续”点击后没有反应。
2. 定位版本只显示 `v1` 和“已配置 N 个内容支柱”，用户无法理解内容、查看详情或继续修改。

完成后，用户可以可靠处理未保存内容，并在同一“定位与知识”页面内完成：

```text
查看当前定位摘要
→ 查看任意版本完整详情
→ 基于该版本修改
→ 保存为新的不可变草稿版本
→ 显式激活新版本
```

## 2. 已锁定的设计决策

### 2.1 不改变定位版本不可变规则

- `PositioningProfile` 仍是不可覆盖版本对象。
- 不新增 `PATCH /positioning/versions/{version}`。
- “基于此版本修改”只负责加载旧版本并预填表单。
- 提交继续调用既有 `POST /positioning/versions`，由 Runtime 分配下一版本号。
- 历史脚本、分镜、批次和内容任务对旧版本的引用保持不变。

### 2.2 不新增页面

- 当前定位摘要、版本列表、编辑器仍位于“定位与知识”页。
- 版本详情使用页内右侧 Detail Panel，不进入新路由，不增加主导航。
- 宽屏显示右侧抽屉；紧凑窗口使用覆盖式抽屉，页面不得产生横向滚动。

### 2.3 不修改账号切换事务

- 现有 `UnsavedGuardRegistry` 的检查、保存、放弃和错误归一化继续复用。
- 只修复 Layout 到 `AccountUnsavedDecisionController` 的事件接线，并增加重复点击保护。
- 保存或放弃执行时继续使用现有 `guarding` / 工作区切换遮罩和状态反馈。
- 保存失败时保留当前账号、当前路由和编辑内容，显示统一错误；已完成选择的确认弹窗关闭，不自动重复弹窗。

这一点是对计划中“保留弹窗”的实现细化：保留的是用户工作区和编辑数据，避免失败后弹窗遮挡需要修正的表单。

### 2.4 不伪改构建产物

- 源版本已经统一为 `0.4.8`。
- 当前 `0.4.7` Runtime manifest 继续绑定原二进制及 SHA-256。
- 两个缺陷完成并通过测试后，才运行正式构建链生成 `0.4.8` Runtime manifest、build ID、安装包与免安装包。

## 3. 当前根因

### 3.1 未保存弹窗

当前 Layout 使用：

```vue
@decide="application.unsavedDecision.resolve"
```

`resolve()` 读取类实例的私有 `resolver`。Vue 将方法作为事件回调执行时，方法可能脱离 `AccountUnsavedDecisionController` 实例，导致 `this` 丢失。弹窗已经发出事件，但待处理决策 Promise 没有正常完成。

现有测试直接调用：

```ts
application.unsavedDecision.resolve("save")
```

因此绕过了真实模板事件接线，没有捕获缺陷。

### 3.2 定位版本不可读

- `PositioningVersionSummaryDto` 只包含版本、状态、摘要和时间。
- Runtime 创建时将摘要固定为“已配置 N 个内容支柱”。
- Runtime 已有完整 `PositioningVersionDto` 和仓储 `get_positioning_version()`，但没有公开详情服务与 GET 路由。
- Desktop 没有详情请求、详情状态、详情面板或 DTO 到编辑草稿的反向映射。
- `openPositioningEditor()` 每次清空草稿，只能从空白新建。

## 4. Runtime 契约

### 4.1 新增详情接口

```http
GET /api/v1/accounts/{account_id}/positioning/versions/{version}
Authorization: Bearer <runtime-session>
X-Operation-ID: <optional>
```

约束：

- `account_id` 继续由账号作用域依赖校验。
- `version` 必须是大于等于 1 的整数。
- 无 `If-Match`、无 `Idempotency-Key`、无 Body。
- 账号不存在返回 `ACCOUNT_NOT_FOUND`。
- 账号已归档返回 `ACCOUNT_ARCHIVED`。
- 当前账号下没有该版本时返回 `POSITIONING_VERSION_NOT_FOUND`，不得暴露其他账号是否存在相同版本。

成功响应：

```json
{
  "ok": true,
  "data": {
    "id": "pos_01J...",
    "accountId": "acc_01J...",
    "version": 1,
    "status": "active",
    "summary": "面向准备出海的独立开发者 · 产品拆解 / 增长实验",
    "createdAt": "2026-08-02T12:00:00Z",
    "audience": {
      "description": "准备出海的独立开发者"
    },
    "contentPillars": [
      "产品拆解",
      "增长实验"
    ],
    "tone": {
      "description": "直接、克制、有证据"
    },
    "prohibitedTopics": [
      "未经验证的收益承诺"
    ],
    "publishingConstraints": {
      "description": "结论必须附带来源"
    },
    "contentHash": "<64-char-sha256>",
    "activatedAt": "2026-08-02T12:10:00Z",
    "revision": 2
  }
}
```

不存在响应：

```json
{
  "ok": false,
  "error": "定位版本不存在或已归档",
  "error_code": "POSITIONING_VERSION_NOT_FOUND",
  "retryable": false,
  "log_id": null
}
```

### 4.2 服务层

`AccountPositioningService` 新增：

```python
def get_version(
    self,
    account_id: str,
    version: int,
) -> PositioningVersionDto:
    ...
```

执行顺序固定为：

1. 打开只读 Unit of Work。
2. `require_account()` 校验账号与归档状态。
3. 调用现有 `configuration.get_positioning_version(account_id, version)`。
4. 不存在时抛出 `POSITIONING_VERSION_NOT_FOUND` / 404。
5. 使用现有 `_positioning_version_to_dto()` 解码并计算 `contentHash`。

不新增 Repository 方法，不新增数据库表或 Alembic 迁移。

### 4.3 可读摘要规则

新增纯函数负责生成摘要，创建与读取统一使用同一算法：

```text
面向{目标受众} · {内容支柱 1} / {内容支柱 2} / {内容支柱 3}
```

规则：

1. 优先读取 `audience.description` 的非空字符串。
2. 如果历史数据没有 `description`，使用受众对象中第一个稳定排序后的非空字符串值。
3. 仍无法得到受众时显示“目标受众已配置”，不得显示空字符串或 `undefined`。
4. 内容支柱去除首尾空白，最多展示前三项；超过三项在末尾追加“等 N 个方向”。
5. 单项展示文本最多 36 个 Unicode 字符，超出使用省略号；完整值只在详情中显示。
6. 摘要最多 160 个字符，不写入用户未配置的信息。

新版本创建时将该摘要写入 `PositioningProfile.summary`。读取列表与详情时重新从真实 JSON 字段派生展示摘要，因此现有数据库里的“已配置 N 个内容支柱”无需迁移即可立即改善，也不写回历史记录。

### 4.4 DTO 保持兼容

- `PositioningVersionSummaryDto` 字段不增加、不删除。
- `PositioningVersionDto` 字段不增加、不删除。
- `PositioningDto` 字段不增加、不删除。
- 本次只有新增 GET 路由和既有 `summary` 值语义改善，保持 API v1 向后兼容。

### 4.5 路由和接口库存

`account-knowledge.md` 的账号定位/知识接口数量从 16 增加到 17；Runtime v1 全局库存测试同步增加一个 GET 路由。接口文档必须补齐方法、地址、Path、Headers、成功示例、错误码、重试规则和版本语义。

## 5. Desktop Runtime Client

新增：

```ts
export function getAccountPositioningVersion(
  accountId: string,
  version: number,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<PositioningVersionDto>>
```

实现要求：

- 先通过 `assertPositiveInteger(version, "version")`。
- 请求路径为当前账号详情路径，不允许组件拼接 URL。
- 复用 `validatePositioningVersion(accountId)`。
- 校验响应 `version` 与请求版本相同；不一致抛出可记录的 Runtime 契约错误。
- 账号不一致继续抛出 `ACCOUNT_SCOPE_MISMATCH`，不得进入 store。
- 支持 `AbortSignal`，关闭详情、切换版本或切换账号时取消过期请求。

## 6. Desktop 状态模型

### 6.1 新增类型

```ts
export type PositioningDetailState =
  | "idle"
  | "loading"
  | "ready"
  | "error";

export type PositioningEditorMode =
  | { kind: "create" }
  | { kind: "fork"; sourceVersion: number };
```

`AccountKnowledgeCache` 新增：

```ts
positioningDetailOpen: boolean;
positioningDetailVersion: number | null;
positioningDetailState: PositioningDetailState;
positioningDetail: PositioningVersionDto | null;
positioningDetailError: KnowledgeUiError | null;
positioningEditorMode: PositioningEditorMode;
```

定位详情错误与页面级 `error` 分开：详情读取失败不能把整个“定位与知识”页面替换成错误页。

### 6.2 账号隔离与迟到响应

- 详情请求控制器按 `accountId` 保存，新的详情请求先取消旧请求。
- 每个账号使用独立 cache；禁止复用其他账号的选中版本或详情 DTO。
- 响应提交前同时检查账号请求序号、当前选择版本和 `response.accountId`。
- 切换账号时旧请求可以完成网络层收尾，但不得覆盖新账号 cache。
- 关闭详情面板时取消该账号当前详情请求并清空临时错误；已缓存 DTO 可保留在该账号 cache 中供同页复用。

### 6.3 Store 动作

新增或调整以下动作：

```ts
openPositioningEditor(accountId: string): void
openPositioningDetail(accountId: string, version: number): Promise<void>
closePositioningDetail(accountId: string): void
editFromPositioningVersion(accountId: string, version: number): Promise<void>
createPositioning(accountId: string): Promise<boolean>
```

行为：

- `openPositioningEditor()` 进入 `{kind:"create"}` 并使用空草稿。
- `openPositioningDetail()` 先打开 loading 面板，再请求详情；失败只更新详情错误。
- `editFromPositioningVersion()` 复用已加载 DTO；没有详情时先请求，成功后执行 `toPositioningDraft()`。
- 基于版本编辑时 `positioningDirty=false`，只有用户实际修改字段后才进入未保存状态。
- `createPositioning()` 成功后读取返回的 `PositioningVersionDto`，关闭编辑器、刷新集合并打开新版本详情。
- 新版本保持 `draft`；不自动激活。
- 激活成功后刷新集合；如果详情面板打开，重新加载选中版本以同步状态和 `activatedAt`。

### 6.4 DTO 到表单的反向映射

新增纯函数：

```ts
toPositioningDraft(dto: PositioningVersionDto): PositioningDraft
```

映射规则：

- `audience.description` 是字符串时写入目标受众，否则使用空字符串。
- `contentPillars` 使用换行连接。
- `tone.description` 是字符串时写入表达风格，否则使用空字符串。
- `prohibitedTopics` 使用换行连接。
- `publishingConstraints.description` 是字符串时写入发布约束，否则使用稳定格式化 JSON，不能变成 `[object Object]`。
- 反向映射不得修改原 DTO。

## 7. 未保存决策交互

### 7.1 Layout 事件接线

禁止继续把类方法直接交给模板。Layout 增加具名包装函数：

```ts
function resolveUnsavedDecision(
  decision: UnsavedGuardDecision
): void {
  application.unsavedDecision.resolve(decision);
}
```

模板使用：

```vue
@decide="resolveUnsavedDecision"
```

该函数必须通过实例访问 `resolve`，保证 `this` 正确。

### 7.2 Dialog 重复点击保护

`AccountUnsavedChangesDialog` 增加本地 `submittingDecision`：

- 第一次选择后立即记录决策并禁用三个按钮。
- `save` 显示“正在保存…”，`discard` 显示“正在放弃…”。
- 提交后忽略 backdrop、Escape 和重复点击。
- `pending.id` 变化或变为 `null` 时重置本地状态。
- 对话框继续保持焦点圈、Escape 取消和 Tab 循环；忙碌时不允许通过 Escape 改变已经提交的决策。

### 7.3 三个决策的结果

| 决策 | 结果 |
|---|---|
| 取消 | Promise 返回 `cancelled`，账号和路由保持不变，编辑内容保留 |
| 放弃并继续 | 依次执行所有脏 guard 的 `discard()`；全部不再 dirty 后继续原操作 |
| 保存并继续 | 依次执行所有脏 guard 的 `save()`；全部不再 dirty 后继续原操作 |

任一 guard 失败：

- 当前账号和当前路由不变。
- 未成功保存的编辑内容保留。
- 统一记录 `[account-context] 处理未保存内容失败`，包含 guard ID、阶段和异常。
- UI 使用现有 `AccountStatusFeedback` 展示中文错误、`logId` 和可用的重试入口。
- 不吞掉异常，不只输出到控制台。

## 8. 定位页面交互

### 8.1 当前定位卡片

存在激活版本时显示：

```text
当前定位                          v2 使用中
面向准备出海的独立开发者
产品拆解   增长实验   AI 工作流
#直接   #克制   #有证据
[查看详情] [编辑定位]
```

来源：

- 第一行摘要来自列表 `summary`。
- 内容支柱和风格标签来自激活版本详情。
- 页面加载集合后，如果有激活版本但本账号尚未缓存详情，静默加载该详情；卡片局部显示骨架，不阻塞知识来源等其他区域。
- `tone.description` 按 `、`、中文/英文逗号、分号和换行拆分，去重后最多显示 5 个标签。

无激活版本但存在草稿时显示“尚未选择使用中的定位”，提供“查看草稿”和“设为使用中”；无版本时保留中性首次使用空态。

### 8.2 版本列表

每行显示：

- `vN`、状态、可读摘要、创建时间。
- 显式“查看详情”按钮；整行可点击，但不能吞掉“激活”按钮事件。
- 草稿显示“设为使用中”，不使用含义模糊的单字“激活”。
- 当前使用版本不重复显示激活按钮。
- 键盘可聚焦和 Enter 打开详情。

### 8.3 详情面板

详情分为：

1. 版本信息：版本、状态、创建时间、激活时间。
2. 目标受众。
3. 内容支柱，以标签/列表展示完整内容。
4. 表达语气。
5. 禁用主题。
6. 发布约束。
7. 追溯信息：缩短展示的内容哈希和完整复制能力。

状态：

- `loading`：局部骨架和“正在读取 vN”。
- `ready`：真实 DTO。
- `error`：中文错误、可选日志编号、“重新加载”和“关闭”。
- 字段为空：显示“未配置”，不隐藏整个分组。

底部操作：

- “基于此版本修改”。
- 草稿可“设为使用中”。
- 关闭。

### 8.4 编辑器

新建模式：

- 标题“新建定位版本”。
- 说明“保存后生成新的草稿版本，不会自动启用”。
- 主按钮“保存草稿版本”。

基于版本修改模式：

- 标题“基于 vN 修改”。
- 说明“原版本保持不变，保存后生成新的草稿版本”。
- 主按钮“保存为新版本”。

保存期间禁用取消和提交，显示“正在保存…”。失败时表单和脏状态保留，页面反馈展示错误与日志引用。

## 9. 组件与文件职责

### 9.1 Desktop

| 文件 | 职责 |
|---|---|
| `AccountWorkspaceLayout.vue` | 使用具名函数接收未保存决策 |
| `AccountUnsavedChangesDialog.vue` | 决策按钮、重复点击保护、焦点与无障碍 |
| `account-unsaved-dialog.css` | busy、disabled、Light / Dark 状态 |
| `PositioningPanel.vue` | 当前摘要、版本列表与事件，不承载详情请求 |
| `PositioningEditor.vue` | 从 Panel 拆出的新建/基于版本编辑表单 |
| `PositioningVersionDetailPanel.vue` | 完整详情、局部状态、重试和操作 |
| `positioning-view-helpers.ts` | DTO 到草稿、标签与展示文本纯函数 |
| `account-knowledge-types.ts` | 详情与编辑器模式类型 |
| `account-knowledge-cache.ts` | 默认详情状态 |
| `account-knowledge-store.ts` | 请求编排、隔离、迟到响应和缓存刷新 |
| `account-knowledge-operations.ts` | 返回创建结果，不拼 UI 规则 |
| `account-knowledge.ts` Runtime Client | 新详情 GET 和响应校验 |
| `positioning-detail.css` | 新详情/编辑器样式，避免继续扩大 408 行主样式文件 |

### 9.2 Runtime

| 文件 | 职责 |
|---|---|
| `services/accounts/positioning.py` | 详情查询与语义摘要纯函数 |
| `api/routes/v1/account_configuration.py` | 新增只读 GET 路由 |
| `schemas/v1/account_configuration.py` | 复用现有 DTO，不新增字段 |
| `repositories/account_configuration_v1_repository.py` | 复用现有账号+版本查询，不修改 |

新增 Python 注释如确有必要必须使用中文；异常使用统一 `DomainError`，不可暴露 traceback。

## 10. 缓存、事件和刷新

- 创建成功继续发出 `positioning.version.created`，激活继续发出 `positioning.version.activated`。
- invalidations 保持现有 positioning / workspace / readiness 规则，不新增第二套事件。
- 当前页面监听 `workspaceContext.account.revision` 变化；同账号修订上升时有界刷新定位集合，解决其他入口修改后页面不更新。
- Store 自己发起创建/激活时先完成当前 mutation，再执行一次集合刷新；相同修订的事件刷新必须去重，避免双请求闪烁。
- 详情数据按账号和版本校验。集合刷新后如果选中版本仍存在，重新拉取详情；如果不存在则关闭面板并提示“该版本已不可用”。

## 11. 错误和日志

| 场景 | 错误/反馈 | 恢复 |
|---|---|---|
| 详情版本不存在 | `POSITIONING_VERSION_NOT_FOUND` | 刷新集合并关闭或选择其他版本 |
| 账号归档 | `ACCOUNT_ARCHIVED` | 返回账号管理恢复账号 |
| 账号作用域不一致 | `ACCOUNT_SCOPE_MISMATCH` | 拒绝写缓存并记录客户端契约错误 |
| Runtime 未就绪 | `RUNTIME_NOT_READY` | 详情局部重试 |
| 创建修订冲突 | `REVISION_CONFLICT` | 保留表单，刷新集合后再次确认提交 |
| 定位字段无效 | `POSITIONING_INVALID` | 根据 `fieldErrors` 修正，不关闭编辑器 |
| 未保存 guard 保存失败 | `UNSAVED_GUARD_FAILED` 归一化 | 保留当前页面和内容，展示日志与重试 |

客户端日志不记录受众全文、禁用主题全文或发布约束全文，只记录账号 ID、版本号、错误码、request ID 和 log ID。

## 12. 测试矩阵

### 12.1 Desktop 未保存链路

1. Dialog 分别点击取消、放弃、保存，只发出一次正确决策。
2. 第一次点击后全部按钮禁用，Escape 和 backdrop 不再发出第二次决策。
3. Layout 使用真实控制器创建 pending Promise，再通过真实按钮完成 Promise，防止再次出现脱离实例回调。
4. 账号切换：取消停留、放弃继续、保存继续。
5. 路由离开：取消停留、保存成功进入目标、保存失败留在原页并有错误反馈。

### 12.2 Desktop 定位链路

1. Runtime Client 请求正确详情 URL，并校验账号与版本。
2. 其他账号响应被 `ACCOUNT_SCOPE_MISMATCH` 拒绝。
3. 当前定位卡片显示可读摘要、支柱和风格标签。
4. 点击版本打开 loading → ready 详情。
5. 详情失败只影响面板，支持重试并展示日志编号。
6. “基于 v1 修改”正确预填五组字段，初始不 dirty。
7. 修改任一字段后进入未保存守卫。
8. 保存返回 v2，v1 DTO 未变，v2 为 draft，并打开 v2 详情。
9. 激活 v2 后集合和详情同步显示“使用中”。
10. 账号切换或连续选择版本时，迟到响应不能污染当前账号。
11. Light / Dark、1440×900 与 1024×768 下无裁切和页面级横向滚动。

### 12.3 Runtime

1. `get_version()` 返回完整 DTO 与稳定 `contentHash`。
2. 不存在版本返回 `POSITIONING_VERSION_NOT_FOUND` / 404。
3. 账号不存在和已归档保持既有错误。
4. 相同版本号在不同账号下只返回 Path 账号自己的对象。
5. 新创建摘要包含真实受众和最多三个支柱。
6. 旧“已配置 N 个内容支柱”记录读取时获得新摘要且数据库原值不被写回。
7. 列表和详情使用相同摘要。
8. 路由库存新增一个 GET，信封、许可证、Host/Origin 与 Runtime Session 门保持一致。

### 12.4 版本与制品

1. `npm run version:sync` 无漂移。
2. `npm run version:check` 通过并验证 `package.json`、Cargo.toml、Cargo.lock、Tauri 和 pyproject 均为 `0.4.8`。
3. 相关 Desktop 测试、Runtime 测试、TypeScript 类型检查通过。
4. 执行账号定位主链 E2E。
5. 构建重新生成 `0.4.8` Runtime manifest，二进制 `--version`、manifest、Tauri 和 release manifest 一致。
6. 免安装 EXE 启动、Runtime ready、详情与未保存决策 GUI smoke 通过。

## 13. API 文档更新

必须同步更新：

- `docs/api/v1/account-knowledge.md`
- `docs/api/v1/README.md` 的接口库存
- `docs/RUNTIME-API-CALLS.md`

文档内容包括：接口地址、请求方法、Path、Headers、返回结果、错误码、示例、恢复方式、版本不可变规则和 Desktop 调用函数名。

## 14. 实施顺序

规格批准后按以下顺序执行，不跨阶段宣称完成：

1. 增加失败测试：真实按钮接线、详情 API、摘要兼容和编辑预填。
2. 修复未保存决策接线与 Dialog 重复点击状态。
3. 实现 Runtime 详情查询、路由和语义摘要。
4. 实现 Desktop Client、详情状态与迟到响应隔离。
5. 拆分 Positioning Editor，增加 Detail Panel 和新交互。
6. 更新 API 文档、接口库存和 Changelog 的真实完成项。
7. 集中执行相关测试、主链回归、类型检查和差异检查。
8. 构建 `0.4.8` Runtime 与 Windows 测试制品，完成 GUI smoke 后交付。

## 15. 回退方案

- 新详情 GET 是加法接口，可独立回退，不影响既有创建与激活接口。
- 无数据库迁移，无需回滚 Schema 或历史数据。
- 摘要读取时派生，不写回旧记录；回退不会产生数据恢复任务。
- Desktop Detail Panel 可独立回退到旧列表，但不能回退未保存按钮接线修复。
- `0.4.8` 制品独立目录保存，不覆盖 `0.4.7` 制品与 manifest。
- 若构建或 smoke 失败，只保留失败证据，不交付不完整 EXE。

## 16. 验收标准

- 三个未保存按钮均通过真实组件点击完成正确决策。
- 用户不打开编辑器也能理解当前定位的受众、方向和风格。
- 任意版本均可查看五组完整配置和追溯信息。
- 基于 v1 修改产生 v2，v1 内容与哈希保持不变。
- 详情、编辑和激活始终绑定当前账号，跨账号响应无法进入缓存。
- 加载、空、正常、错误、重试和未保存状态完整。
- API 文档、Desktop Client 与 Runtime 实现一致。
- 源版本、Runtime、Tauri、manifest 和测试 EXE 最终一致为 `0.4.8`。
- 未新增超大文件，新增样式、组件和 helper 按职责拆分。
- `0.4.8` 免安装 EXE 经真实 GUI smoke 后交付用户测试。

## 17. 审批门

本规格批准前，不修改上述两个缺陷的生产源码和测试。批准后按第 14 节实施；若实现过程中需要改变 API 字段、版本不可变规则或页面容器边界，必须先修订本规格并重新批准。
