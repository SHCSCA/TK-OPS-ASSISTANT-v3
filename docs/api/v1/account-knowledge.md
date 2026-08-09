# 账号定位、知识与品牌 API v1

本文件是 P0-C 账号定位版本、知识规则与来源、不可变知识快照、BrandKit 和发布默认值的 HTTP 契约真源。当前实现已注册 17 个接口，并已通过 P0-C 阶段验收。

所有接口均以 `account_id` 为隔离边界，要求 [README.md](README.md) 定义的安全门和 active 许可证。账号必须存在且未归档；跨账号资源按“不存在”处理，不能通过 Body 覆盖 Path 作用域。公共错误见 [errors.md](errors.md)，知识索引任务跟踪见 [tasks-and-events.md](tasks-and-events.md)。

## 1. 共同约束

### 1.1 修订、幂等和分页

- `If-Match` 使用账号聚合修订。客户端应取 `AccountDto.revision`、`workspaceRevision`，或 `PositioningDto` / `KnowledgeDto` / `BrandKitDto` / `PublishDefaultsDto` 顶层 `revision`；不得使用 `PositioningVersionDto.revision` 或 `KnowledgeSourceDto.revision` 等子资源修订。缺少或落后返回 `REVISION_CONFLICT`（412），格式错误返回 `REQUEST_VALIDATION_FAILED`（422）。
- 声明 `Idempotency-Key` 的普通写操作按账号、操作名、键和请求摘要持久幂等；同键不同请求返回 `REQUEST_CONFLICT`。任务提交冲突返回 `TASK_IDEMPOTENCY_CONFLICT`。
- 未声明幂等键的写接口未知结果必须先 GET 对账。
- 列表 Query 统一支持 `cursor` 与 `limit`。默认 50、当前最大 200，由 `api.paginationDefaultLimit` 和 `api.paginationMaxLimit` 控制；响应以 `meta.nextCursor` 返回不透明下一页游标。游标同时绑定 `account_id`、资源类型、筛选摘要与排序位置，不能跨账号、跨来源/快照列表或在改变筛选后复用；错配返回 `invalid_scoped_cursor`，客户端应从当前查询第一页重新加载。

### 1.2 知识来源安全边界

- `kind` 为 `document | image | video | audio | text | reference`，表示持久内容类别。
- `sourceMode` 为 `file | url | text`，且 Body 只能提交与该模式匹配的一种内容。
- `file` 只接受文件选择器生成的 `file_ref_...` 受控引用，不接受绝对路径、相对路径或 `file://` URL。P0-C 可创建这类来源，但 P0-F Tauri 受控文件桥尚未装配；当前索引会明确以 `CONTROLLED_FILE_REF_INVALID` / HTTP 503 失败并保留可重试状态，绝不会伪造读取成功。
- `url` 只接受不含凭据和 fragment 的公共 HTTPS URL；创建时拒绝直接私网地址，索引时重新解析 DNS 并拒绝任一非公网地址，限制 TLS、重定向、超时和读取大小。
- `text` 正文写入账号隔离的受控内容存储；数据库、响应、事件和日志不保存或回显正文。
- text 创建若在持久化幂等竞争中成为重放方，会立即清理本次未采用的正文文件；Runtime 恢复持久任务后还会按数据库来源引用清理崩溃遗留的孤儿正文。软删除墓碑仍保护原正文，不会被误判为孤儿。
- 来源状态为 `pending | indexing | ready | failed | stale | removed`。删除是软移除，不覆盖原文件或外部 URL。

### 1.3 主要 DTO

| DTO | 字段 |
| --- | --- |
| `PositioningDto` | `accountId,activeVersion,versions[],revision` |
| `PositioningVersionDto` | `id,accountId,version,status,summary,createdAt,audience,contentPillars,tone,prohibitedTopics,publishingConstraints,contentHash,activatedAt,revision` |
| `KnowledgeDto` | `accountId,rules,rulesVersion,sourceCounts,latestSnapshotId,readiness,revision` |
| `KnowledgeSourceDto` | `id,accountId,kind,sourceMode,title,status,controlledRef,sourceUrl,contentHash,indexedAt,removedAt,errorCode,logId,revision` |
| `KnowledgeSnapshotDto` | `id,accountId,label,sourceIds,sourceEvidence,rulesVersion,contentHash,createdAt` |
| `BrandKitDto` | `accountId,activeVersion,versions,active,revision` |
| `PublishDefaultsDto` | `accountId,timezone,privacyLevel,allowComments,allowDuet,allowStitch,captionRules,revision` |

`sourceEvidence` 的每项固定为 `{sourceId,contentHash,indexedRevision}`，用于证明快照创建时采用的来源内容与来源修订。快照自身不可编辑。

## 2. 接口总览

| 方法 | 地址 | `If-Match` | `Idempotency-Key` | 成功 |
| --- | --- | --- | --- | ---: |
| `GET` | `/api/v1/accounts/{account_id}/positioning` | 无 | 无 | 200 |
| `GET` | `/api/v1/accounts/{account_id}/positioning/versions/{version}` | 无 | 无 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/positioning/versions` | 必填 | 必填 | 201 |
| `POST` | `/api/v1/accounts/{account_id}/positioning/versions/{version}/activate` | 必填 | 必填 | 200 |
| `GET` | `/api/v1/accounts/{account_id}/knowledge` | 无 | 无 | 200 |
| `PATCH` | `/api/v1/accounts/{account_id}/knowledge` | 必填 | 无 | 200 |
| `GET` | `/api/v1/accounts/{account_id}/knowledge/sources` | 无 | 无 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/knowledge/sources` | 无 | 必填 | 201 |
| `DELETE` | `/api/v1/accounts/{account_id}/knowledge/sources/{source_id}` | 必填 | 必填 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/knowledge/index-jobs` | 无 | 必填 | 202 |
| `GET` | `/api/v1/accounts/{account_id}/knowledge/snapshots` | 无 | 无 | 200 |
| `POST` | `/api/v1/accounts/{account_id}/knowledge/snapshots` | 无 | 必填 | 201 |
| `GET` | `/api/v1/accounts/{account_id}/knowledge/snapshots/{snapshot_id}` | 无 | 无 | 200 |
| `GET` | `/api/v1/accounts/{account_id}/brand-kit` | 无 | 无 | 200 |
| `PUT` | `/api/v1/accounts/{account_id}/brand-kit` | 必填 | 必填 | 200 |
| `GET` | `/api/v1/accounts/{account_id}/publish-defaults` | 无 | 无 | 200 |
| `PUT` | `/api/v1/accounts/{account_id}/publish-defaults` | 必填 | 无 | 200 |

## 3. 定位版本

### GET `/api/v1/accounts/{account_id}/positioning`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query、Body：无。
- 返回：`data=PositioningDto`；未配置时 `activeVersion=null`、`versions=[]`，不伪造定位。
- 错误与恢复：`ACCOUNT_NOT_FOUND`、`ACCOUNT_ARCHIVED` 或公共服务错误；只读可在 Runtime 恢复后重试。
- Revision / 幂等：只读；响应 `revision` 是账号聚合修订。
- Invalidations / 事件：无。
- legacy：旧账号标签、脚本参数或项目设置都不是定位版本，无映射。

### GET `/api/v1/accounts/{account_id}/positioning/versions/{version}`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id` 与正整数 `version`。Query、Body：无。
- 返回：`data=PositioningVersionDto`，包含受众、内容支柱、语气、禁用主题、发布约束、内容哈希与激活时间；`summary` 由已持久化定位内容生成，旧版通用摘要在读取时兼容转换，不修改历史记录。
- 错误与恢复：账号门禁按公共规则处理；版本不存在返回 `POSITIONING_VERSION_NOT_FOUND`（404），客户端刷新版本列表后重试或关闭已失效详情。
- Revision / 幂等：只读；`PositioningVersionDto.revision` 仅用于展示版本证据，不能替代账号聚合 `If-Match` 修订。
- Invalidations / 事件：无；Desktop 应按 `account_id + version` 缓存，并在定位版本创建或激活事件后失效。
- legacy：旧设置没有不可变定位版本，不能映射到该详情接口。

### POST `/api/v1/accounts/{account_id}/positioning/versions`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。
- Body：`{audience,contentPillars,tone,prohibitedTopics,publishingConstraints}`；内容支柱至少一项、各列表不得有空白或重复，受众与语气对象必须有效。
- 返回：HTTP 201，`data=PositioningVersionDto`，新版本状态为 `draft`；`meta={revision,invalidations,idempotentReplay}`。
- 错误与恢复：`POSITIONING_INVALID` 应按 `fieldErrors` 修正；`REVISION_CONFLICT` 重新 GET；`REQUEST_CONFLICT` 修正幂等键复用。
- Revision / 幂等：账号修订锁 + 普通写幂等；内容哈希由规范化配置生成。
- Invalidations / 事件：失效 positioning 与 workspace；原子写入 `positioning.version.created` 到账号 workspace Topic。
- legacy：无映射。

### POST `/api/v1/accounts/{account_id}/positioning/versions/{version}/activate`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key` 必填；`X-Operation-ID` 可选。
- Path：`account_id` 与正整数 `version`。Query、Body：无。
- 返回：`data=PositioningDto`，`activeVersion` 指向已激活版本；`meta={revision,invalidations,idempotentReplay}`。
- 错误与恢复：`POSITIONING_VERSION_NOT_FOUND` 时刷新版本；`REVISION_CONFLICT` 重新对账；账号门禁和 `REQUEST_CONFLICT` 按公共规则处理。
- Revision / 幂等：账号修订锁 + 普通写幂等。
- Invalidations / 事件：失效 positioning、workspace、readiness；写入 `positioning.version.activated`。
- legacy：无映射；不得通过修改历史版本实现激活。

## 4. 知识规则与来源

### GET `/api/v1/accounts/{account_id}/knowledge`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query、Body：无。
- 返回：`data=KnowledgeDto`；新账号真实返回空规则、空计数、无快照和 empty readiness，而不是演示来源。
- 错误与恢复：账号门禁；若知识库初始化证据损坏则 `INTERNAL_ERROR`（500），按 `log_id` 运行数据诊断。
- Revision / 幂等：只读；`rulesVersion`、来源 `revision` 与账号 `revision` 是不同维度。
- Invalidations / 事件：无。
- legacy：旧资产库、项目文档或检索接口均不映射。

### PATCH `/api/v1/accounts/{account_id}/knowledge`

- Headers：`Authorization`、`If-Match`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。
- Body：完整 `{inclusionRules,exclusionRules,citationPolicy}` 对象；不是字段级 JSON Merge Patch。
- 返回：`data=KnowledgeDto`，`meta={revision,invalidations}`。
- 错误与恢复：`KNOWLEDGE_RULES_INVALID` / `REQUEST_VALIDATION_FAILED` 应修正规则；`REVISION_CONFLICT` 先 GET；初始化损坏返回带日志的 500。
- Revision / 幂等：要求账号修订，不使用幂等键，未知结果先 GET。
- Invalidations / 事件：失效 `accounts:list`、`account:{account_id}:knowledge`、`account:{account_id}:knowledge:sources`、`account:{account_id}:workspace`、`account:{account_id}:readiness`；写入 `knowledge.rules.updated` 到 knowledge Topic。
- legacy：无映射。

### GET `/api/v1/accounts/{account_id}/knowledge/sources`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Body：无。
- Query：`kind?`、`status?`、`cursor?`、`limit?`；枚举见共同约束。
- 返回：`KnowledgeSourcePageDto{items,totalKnown}`，`meta.nextCursor` 为游标或 `null`。
- 错误与恢复：`REQUEST_VALIDATION_FAILED` 表示筛选、游标或分页无效；账号门禁及公共错误按索引处理。
- Revision / 幂等：只读。
- Invalidations / 事件：无。
- legacy：旧资产列表不映射。

### POST `/api/v1/accounts/{account_id}/knowledge/sources`

- Headers：`Authorization`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。
- Body：`{kind,sourceMode,title,controlledFileRef?,url?,text?}`；恰好一种摄取内容与 `sourceMode` 对应，`title` 为 1 至 256 字符。
- 返回：HTTP 201，`data=KnowledgeSourceDto`，初始 `status=pending`；`meta={revision,invalidations,idempotentReplay}`。响应不会回显 text。
- 错误与恢复：`CONTROLLED_FILE_REF_INVALID`、`KNOWLEDGE_SOURCE_INVALID`、`REQUEST_VALIDATION_FAILED` 应修正来源；`REQUEST_CONFLICT` 应修正键复用；持久内容写入异常按 `log_id` 诊断。
- Revision / 幂等：不要求客户端提供 `If-Match`；服务在账号写锁内用当前修订原子追加，普通写幂等。
- Invalidations / 事件：失效 `accounts:list`、`account:{account_id}:knowledge`、`account:{account_id}:knowledge:sources`、`account:{account_id}:workspace`、`account:{account_id}:readiness`；写入 `knowledge.source.created`。
- legacy：旧上传、资产导入和 URL 下载接口均不映射。

### DELETE `/api/v1/accounts/{account_id}/knowledge/sources/{source_id}`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key` 必填；`X-Operation-ID` 可选。
- Path：`account_id`、稳定 `source_id`。Query、Body：无。
- 返回：`data=KnowledgeSourceDto`，`status=removed`；首次移除返回新账号修订，已移除来源的相同幂等重放返回原结果。
- 错误与恢复：`KNOWLEDGE_SOURCE_NOT_FOUND` 不区分其他账号资源；`REVISION_CONFLICT` 重新 GET；`REQUEST_CONFLICT` 修正键复用。
- Revision / 幂等：账号修订锁 + 普通写幂等；不删除源文件，也不重写已有快照证据。
- Invalidations / 事件：首次移除失效 `accounts:list`、`account:{account_id}:knowledge`、`account:{account_id}:knowledge:sources`、`account:{account_id}:workspace`、`account:{account_id}:readiness` 并写入 `knowledge.source.removed`；无状态变化时不产生新事件。
- legacy：无映射。

### POST `/api/v1/accounts/{account_id}/knowledge/index-jobs`

- Headers：`Authorization`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。
- Body：`{sourceIds?}`；省略表示当前账号全部可索引来源，显式列表必须非空、无重复、最多 10000 项，且所有来源属于当前账号并未移除。
- 返回：HTTP 202，`TaskAcceptedDto`，`taskType=knowledge.index`；`meta.invalidations` 包含账号 tasks 与 knowledge。
- 错误与恢复：提交期 `KNOWLEDGE_SOURCE_INVALID`、`TASK_IDEMPOTENCY_CONFLICT`、`TASK_ALREADY_RUNNING`、任务装配错误；存在既有任务时按 `meta.taskId` 跟踪。执行期 `KNOWLEDGE_INDEX_FAILED`、`CONTROLLED_FILE_REF_INVALID`、`TASK_STATE_CONFLICT`、`TASK_TIMEOUT` 或取消。file 来源在 P0-F 文件桥落线前会以 503 明确失败；text 与公共 HTTPS 来源走当前真实读取器。修复来源或文件桥后用新业务幂等键重新提交，不伪装成原任务重试。
- Revision / 幂等：任务作用域幂等；创建时冻结来源 ID 与知识索引配置修订、单来源大小、URL 超时和重定向上限。
- Invalidations / 事件：任务状态写入账号 tasks Topic；每个来源的 `indexing/ready/failed/stale` 变化写 `knowledge.index.updated` 到 knowledge Topic，失效 `accounts:list`、`account:{account_id}:knowledge`、`account:{account_id}:knowledge:sources`、`account:{account_id}:workspace`、`account:{account_id}:readiness`，并推进账号聚合修订。
- legacy：无映射；旧视频分析或资产扫描任务不能代替知识索引。

## 5. 不可变知识快照

### GET `/api/v1/accounts/{account_id}/knowledge/snapshots`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：`cursor?`、`limit?`。Body：无。
- 返回：`KnowledgeSnapshotPageDto{items,totalKnown}`，`meta.nextCursor` 为游标或 `null`。
- 错误与恢复：分页/游标无效返回 `REQUEST_VALIDATION_FAILED`；账号门禁及数据损坏按公共错误处理。
- Revision / 幂等：只读。
- Invalidations / 事件：无。
- legacy：无映射。

### POST `/api/v1/accounts/{account_id}/knowledge/snapshots`

- Headers：`Authorization`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。
- Body：`{sourceIds,label?}`；来源列表必须非空、无重复、最多 10000，且每个来源当前为 `ready` 并有内容哈希；`label` 可选、最长 256。
- 返回：HTTP 201，`data=KnowledgeSnapshotDto`，`meta={revision,invalidations,idempotentReplay}`。
- 错误与恢复：`KNOWLEDGE_SNAPSHOT_INVALID` 表示来源缺失、未 ready、重复或跨账号；`REQUEST_CONFLICT` 表示幂等键误复用；内部证据损坏按 `log_id` 诊断。
- Revision / 幂等：服务在账号写锁内读取当前规则、索引修订、激活定位和来源证据后一次提交；普通写幂等。
- Invalidations / 事件：失效 knowledge 与 knowledge:snapshots；写入 `knowledge.snapshot.created`。
- legacy：无映射；不得把可变检索结果当作快照。

### GET `/api/v1/accounts/{account_id}/knowledge/snapshots/{snapshot_id}`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`、稳定 `snapshot_id`。Query、Body：无。
- 返回：`data=KnowledgeSnapshotDto`，不返回来源正文或本地路径。
- 错误与恢复：`KNOWLEDGE_SNAPSHOT_NOT_FOUND` 不区分跨账号资源；账号门禁及公共错误按真源处理。
- Revision / 幂等：只读。
- Invalidations / 事件：无。
- legacy：无映射。

## 6. BrandKit 与发布默认值

### GET `/api/v1/accounts/{account_id}/brand-kit`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query、Body：无。
- 返回：`data=BrandKitDto`；未配置时 `activeVersion=null`、`versions=[]`、`active=null`。
- 错误与恢复：账号门禁或持久 JSON 损坏的 `INTERNAL_ERROR`；按日志修复数据，不在 UI 猜测默认品牌。
- Revision / 幂等：只读。
- Invalidations / 事件：无。
- legacy：旧主题、资产标签或 Prompt 风格字段不映射。

### PUT `/api/v1/accounts/{account_id}/brand-kit`

- Headers：`Authorization`、`If-Match`、`Idempotency-Key`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。
- Body：`{colors,fonts,logoAssetRefs,visualRules,voiceRules}`；列表值不能为空或重复，颜色为 `#RRGGBB` 或 `#RRGGBBAA`，Logo 只用受控资产引用。
- 返回：`data=BrandKitDto`，新版本立即成为 active，旧 active 归档；`meta={revision,invalidations,idempotentReplay}`。
- 错误与恢复：`BRAND_KIT_INVALID` 按 `fieldErrors` 修正；`REVISION_CONFLICT` 对账；`REQUEST_CONFLICT` 修正键复用。
- Revision / 幂等：账号修订锁 + 普通写幂等。
- Invalidations / 事件：失效 brand-kit 与 workspace；写入 `brand-kit.updated` 到 workspace Topic。
- legacy：无映射。

### GET `/api/v1/accounts/{account_id}/publish-defaults`

- Headers：`Authorization` 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query、Body：无。
- 返回：`data=PublishDefaultsDto`。新账号真实初始化为 UTC、private、互动关闭、空 captionRules；这是保守系统默认，不是业务结果。
- 错误与恢复：`PUBLISH_DEFAULTS_INVALID`（409）表示初始化记录缺失，应运行数据修复；另有账号门禁和公共错误。
- Revision / 幂等：只读。
- Invalidations / 事件：无。
- legacy：旧发布表单配置不映射。

### PUT `/api/v1/accounts/{account_id}/publish-defaults`

- Headers：`Authorization`、`If-Match`、JSON 必填；`X-Operation-ID` 可选。
- Path：`account_id`。Query：无。
- Body：`{timezone,privacyLevel,allowComments,allowDuet,allowStitch,captionRules}`；时区必须为有效 IANA 名称，隐私为 `public | friends | private`，合拍和拼接仅允许 public。
- 返回：`data=PublishDefaultsDto`，`meta={revision,invalidations}`。
- 错误与恢复：`PUBLISH_DEFAULTS_INVALID`（422）按 `fieldErrors` 修正；`REVISION_CONFLICT` 重新 GET；服务异常按 `log_id` 对账。
- Revision / 幂等：要求账号修订；不使用幂等键，未知结果先 GET。
- Invalidations / 事件：失效 publish-defaults 与 workspace；写入 `publish.defaults.updated`。
- legacy：无映射；P0-C 只保存默认值，不执行真实发布。

## 7. 索引任务、事件与敏感数据

- 定位、BrandKit、发布默认值事件使用 `account:{account_id}:workspace`；知识规则、来源、索引和快照使用 `account:{account_id}:knowledge`；任务状态使用 `account:{account_id}:tasks`。
- text 与公共 HTTPS 来源按真实字节生成 SHA-256 内容哈希。file 来源在 P0-F Tauri 受控文件桥装配前失败封闭，不能进入 ready。`ready` 只表示当前可用读取器完成读取和哈希，不表示 AI 已理解或内容质量已验证。
- 一个 `knowledge.index` 任务可处理多个来源。单项失败会留下该来源的稳定错误码和安全日志引用，并使任务失败；其他已成功来源不会被伪造回滚。
- 取消中的来源转为 `stale`；Runtime 启动先完成持久任务恢复决策，再读取恢复决策后的非终态 `knowledge.index` 任务快照并只保护其中冻结的 `sourceIds`。同一账号内未被这些活动任务承接的孤立 `indexing` 来源仍会调和为可恢复的 `stale` 并写受控事件。该对账完成前 Runtime 不进入就绪态。
- 响应、任务快照和事件不包含正文、文件路径、任意 Header、Provider 凭据或 traceback。URL 响应正文也不会写入事件。
- 本文件所有 legacy 对应项均为“无映射”。开发/测试模式中的旧资产、脚本、项目和设置接口不构成账号知识契约，生产模式不会据此开放能力。
