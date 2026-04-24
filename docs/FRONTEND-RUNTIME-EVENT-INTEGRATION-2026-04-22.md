# 前端联动改造任务单（Runtime 事件回流与配置总线）

## 1. 文档目的

本文件用于把已落地的 Runtime 后端事件能力，整理成一份可直接交给前端开发执行的模块化任务单。

当前后端已具备以下事件与链路：

- `config.changed`
- `ai-capability.changed`
- `POST /api/settings/ai-providers/{provider_id}/models/refresh`
- `POST /api/ai-providers/health/refresh`

但前端目前仍以“页面主动拉取 + 局部刷新”为主，尚未形成统一的 Runtime 事件消费层，因此设置页中的 Provider、模型刷新、配置同步和状态回流并未真正打通。

本文目标：

- 明确前端需要改哪些模块
- 明确每个模块的职责边界
- 明确每个模块的输入输出和验收标准
- 避免把状态同步逻辑继续堆在页面层

---

## 2. 总体实施原则

### 2.1 核心原则

- 先补事件层，再补 store，最后改页面
- 不在页面层拼接 Runtime 业务规则
- 不新增假状态或本地伪结果
- 所有配置和 Provider 状态回流必须进入统一 store
- WebSocket 连接必须统一初始化，不由页面各自管理

### 2.2 后端已提供的最小事件契约

#### `config.changed`

- `type`
- `scope`
- `revision`
- `updatedAt`
- `changedKeys`

#### `ai-capability.changed`

- `type`
- `scope`
- `configVersion`
- `reason`
- `providerIds`
- `capabilityIds`

### 2.3 已约定的 `reason`

- `capability_config_updated`
- `provider_secret_updated`
- `provider_model_upserted`
- `provider_models_refreshed`
- `provider_health_refreshed`

---

## 3. 模块拆分

### 模块 A：Runtime 类型真源对齐

#### 目标

先把前端类型定义补齐到当前后端真实契约，避免 store 和页面继续基于旧字段或 `any` 开发。

#### 涉及文件

- `apps/desktop/src/types/runtime.ts`
- `apps/desktop/src/types/task-events.ts`
- `apps/desktop/src/pages/settings/types.ts`

#### 必做项

- 补齐 `AppSettings.scope`
- 补齐 `RuntimeDiagnostics.configScope`
- 补齐 `AICapabilitySettings.configVersion`
- 补齐 `AICapabilitySettings.scope`
- 补齐 `AICapabilitySettings.diagnosticSummary`
- 补齐 `AIProviderSecretStatus.readiness`
- 补齐 `AIProviderSecretStatus.lastCheckedAt`
- 补齐 `AIProviderSecretStatus.errorCode`
- 补齐 `AIProviderSecretStatus.errorMessage`
- 补齐 `AIProviderSecretStatus.scope`
- 为 WebSocket 事件新增前端类型：
  - `ConfigChangedEvent`
  - `AICapabilityChangedEvent`

#### 验收标准

- 前端类型文件中不再缺少后端已返回字段
- `ProviderCardState` 不再依赖 `any`
- 设置模块不再需要为后端已存在字段写额外兜底类型

---

### 模块 B：统一 Runtime 事件消费层

#### 目标

把 `config.changed` 和 `ai-capability.changed` 纳入统一 WebSocket 消费层，避免事件到达后因没有业务 key 而被丢弃。

#### 涉及文件

- `apps/desktop/src/stores/task-bus.ts`
- `apps/desktop/src/types/task-events.ts`

#### 当前问题

现有 `task-bus` 主要按以下 key 分发：

- `taskId`
- `projectId`
- `workspaceId`
- `planId`
- `videoId`

但：

- `config.changed`
- `ai-capability.changed`

都不是 task 型事件，没有这些 key，因此虽然能收到消息，但不会进入有效订阅回调。

#### 必做项

- 为 `task-bus` 增加“按事件类型订阅”能力
- 推荐新增：
  - `subscribeToEventType(type, callback)`
- 保留现有 `subscribe(key, callback)`，不要破坏 task 型页面
- 在事件解析层识别：
  - `config.changed`
  - `ai-capability.changed`

#### 不建议的做法

- 不要在设置页组件内直接开第二条 WebSocket
- 不要把非任务事件硬塞进 task-only 逻辑里

#### 验收标准

- 非 task 事件能被统一消费
- 页面不直接处理 socket 原始消息
- 现有 task 类页面行为不回归

---

### 模块 C：配置总线 `config-bus` 真正总线化

#### 目标

让 `config-bus` 不只是“主动拉配置”，而是能在 Runtime 配置变化后自动回流。

#### 涉及文件

- `apps/desktop/src/stores/config-bus.ts`
- `apps/desktop/src/app/runtime-client.ts`

#### 当前问题

- `providerReadiness` 类型过宽，使用 `Record<string, any>`
- `save()` 后只做本地再拉一次
- 没有消费 `config.changed`
- 其他来源引发的配置变化不会自动回流

#### 必做项

- 订阅 `config.changed`
- 根据 `revision` 处理事件
- 当收到新 revision 时，重新同步：
  - `fetchRuntimeConfig()`
  - `fetchRuntimeDiagnostics()`
  - 必要时 `fetchRuntimeHealth()`
- `providerReadiness` 改成明确类型

#### 推荐策略

配置对象体量不大，建议采用“revision 驱动的全量同步”，不要在前端做复杂 patch。

#### 验收标准

- `config.changed` 到达后，`config-bus.settings` 自动更新
- `diagnostics.configScope` 可见
- `settings.scope` 可见
- revision 倒退事件会被忽略

---

### 模块 D：AI Capability Store 事件回流

#### 目标

让 `ai-capability` store 真正接住：

- capability 配置更新
- provider secret 更新
- provider model upsert
- provider model refresh
- provider health refresh

#### 涉及文件

- `apps/desktop/src/stores/ai-capability.ts`
- `apps/desktop/src/app/runtime-client.ts`

#### 当前问题

- `saveCapabilities()` 会把 `settings` 裁成残缺对象
- `refreshProviderModels()` 只处理当前页面触发，不处理后端广播
- `saveProviderSecret()` 和 `saveProviderModel()` 只做局部 patch
- 没有 `configVersion` 和 `diagnosticSummary` 的完整维护

#### 必做项

- 订阅 `ai-capability.changed`
- 完整维护 `settings`
- 按 `reason` 执行最小刷新

#### 推荐的刷新映射

##### `capability_config_updated`

- reload `settings`
- reload `supportMatrix`

##### `provider_secret_updated`

- reload `settings`
- reload `providerCatalog`

##### `provider_model_upserted`

- reload `modelCatalogByProvider[providerId]`
- 视情况 reload `supportMatrix`

##### `provider_models_refreshed`

- reload `modelCatalogByProvider[providerId]`
- reload `providerCatalog`
- reload `supportMatrix`

##### `provider_health_refreshed`

- reload `settings.providers`
- 必要时更新全局 provider readiness 视图

#### 验收标准

- `AICapabilitySettings` 在 store 中保持完整
- refresh 结束后模型列表和 provider 状态同步更新
- 页面不再手工维护刷新后的模型 patch

---

### 模块 E：Provider UI 状态机统一

#### 目标

统一 Provider 卡片、抽屉和列表的状态来源，避免多个状态字段互相打架。

#### 涉及文件

- `apps/desktop/src/pages/settings/components/ProviderCard.vue`
- `apps/desktop/src/pages/settings/components/ProviderConfigDrawer.vue`
- `apps/desktop/src/pages/settings/types.ts`

#### 当前问题

UI 同时依赖：

- `provider.status`
- `provider.health.status`
- `provider.readiness`
- `refreshResultByProvider[providerId]`

这些状态并不来自同一层级，导致刷新后容易出现：

- 按钮状态更新但卡片没更新
- 模型列表更新但 readiness 没更新
- 测试结果与刷新结果语义混杂

#### 必做项

- 统一“卡片主状态”来源
  - 建议主状态使用 `provider.readiness`
- “测试结果”单独显示
  - 使用 `provider.health`
- “刷新结果提示”单独显示
  - 使用 `refreshResultByProvider`

#### 至少要支持的状态反馈

- `refreshed`
- `static_catalog`
- `provider.model.refresh_missing_secret`
- `provider.model.refresh_failed`

#### 验收标准

- 卡片与抽屉的状态解释一致
- 刷新结果在 UI 中可见
- 不再依赖多个相互冲突的状态字段做拼接判断

---

### 模块 F：设置页 composable 去业务化

#### 目标

把设置页 composable 从“状态同步控制器”降为“纯 UI 交互层”。

#### 涉及文件

- `apps/desktop/src/pages/settings/use-provider-management.ts`
- `apps/desktop/src/pages/settings/ai-system-settings-page-helpers.ts`
- `apps/desktop/src/pages/settings/AISystemSettingsPage.vue`

#### 当前问题

- 页面和 composable 仍然负责：
  - 刷新模型后 reload 什么
  - 保存 provider 后 patch 什么
  - 保存系统设置后认为本地状态已是最终状态

这些逻辑本应由 store 和总线处理。

#### 必做项

- composable 仅负责：
  - 抽屉开关
  - loading flag
  - 表单编辑态
  - UI 层动作转发
- store 负责：
  - 所有状态回流
  - reload 逻辑
  - revision / version 比较
  - 事件驱动更新

#### 验收标准

- 页面不再承担 Runtime 状态同步职责
- 设置页关闭时，后台事件仍可正常更新 store
- 打开设置页时只消费现成状态，不重新发明同步逻辑

---

### 模块 G：初始化入口统一

#### 目标

把 WebSocket 的初始化入口收口到应用壳层，不让设置页自己承担连接管理。

#### 涉及文件

- `apps/desktop/src/layouts/AppShell.vue`
- `apps/desktop/src/stores/task-bus.ts`

#### 当前问题

多个页面模块存在自己 `initializeWebSocket()` 的模式。  
对于设置模块，这种方式不适合承接全局配置事件。

#### 必做项

- 统一在壳层或启动入口执行一次 `taskBus.connect()`
- 设置相关 store 在内部注册事件订阅
- 设置页只读 store，不自己控制 socket 生命周期

#### 验收标准

- 设置页未打开时，配置事件也能正常回流
- WebSocket 不会因设置页切换重复建立

---

### 模块 H：设置模块乱码清理

#### 目标

把设置模块当前明显的错码和乱码收口，避免联调时状态与文案混淆。

#### 涉及文件

- `apps/desktop/src/pages/settings/AISystemSettingsPage.vue`
- `apps/desktop/src/pages/settings/components/ProviderCard.vue`
- `apps/desktop/src/pages/settings/components/ProviderConfigDrawer.vue`
- `apps/desktop/src/pages/settings/ai-system-settings-page-helpers.ts`

#### 必做项

- 全部转为 UTF-8 无 BOM
- 修复中文文案错码
- 统一错误提示和状态文案

#### 验收标准

- 页面中不再出现乱码
- 设置页状态文案与 Runtime 错误语义一致

---

## 4. 推荐实施顺序

1. 模块 A：类型真源对齐
2. 模块 B：统一 Runtime 事件消费层
3. 模块 C：配置总线 `config-bus`
4. 模块 D：`ai-capability` store
5. 模块 E：Provider UI 状态机统一
6. 模块 F：设置页 composable 去业务化
7. 模块 G：初始化入口统一
8. 模块 H：乱码清理

---

## 5. 测试建议

### 5.1 事件层测试

- `config.changed` 可被统一事件层识别
- `ai-capability.changed` 可被统一事件层识别

### 5.2 Store 测试

- `config-bus` 收到更高 revision 的 `config.changed` 后会重新同步
- `ai-capability` 收到不同 `reason` 后会触发对应 reload

### 5.3 页面联动测试

- 刷新模型后，卡片、抽屉、模型列表同步更新
- 未打开设置页时，事件仍能回流到 store
- 重新进入设置页时能看到最新状态

---

## 6. 交付标准

- 前端已消费 `config.changed`
- 前端已消费 `ai-capability.changed`
- 设置页不依赖页面级手动刷新保持一致性
- Provider refresh 成功/失败/静态目录状态可见
- `config-bus` 与 `ai-capability` store 状态完整
- 类型与后端契约一致
- 设置模块无乱码

---

## 7. 结论

这次前端联动改造的关键，不是继续在设置页里加 `refresh()`，而是先补一层统一的 Runtime 事件消费机制。

如果跳过这一步，后续会持续出现以下问题：

- 页面打开时能同步，页面关闭时不同步
- store 和页面各自维护一套状态
- provider refresh 成功了，但卡片、抽屉、配置总线不同步
- 新的后端事件继续无法回流

因此建议前端开发严格按本文的模块顺序推进，不要从页面组件直接开工。
