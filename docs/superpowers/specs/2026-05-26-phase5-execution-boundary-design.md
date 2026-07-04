# 阶段 5 执行边界语义纠偏设计

## 背景

阶段 5 的目标是让发布、浏览器实例与自动化中心具备真实边界：能执行的动作必须有证据，暂未接入真实执行器的动作必须明确标注人工处理或待接入状态。当前发布、自动化、浏览器实例都已有本地计划、预检、队列和状态记录，但没有完整的平台提交、浏览器进程或动作执行证据。

本设计先交付最小可用切片：纠正用户可见语义，避免把本地预检、队列写入或摘要生成伪装成真实平台发布和真实自动化完成。

## 文档依据

- `docs/PRD.md`：发布前必须校验账号、设备、工作区、素材等关键条件；发布失败必须支持转人工或重试；必要时提供手动确认模式。
- `docs/UI-DESIGN-PRD.md`：UI 必须优先呈现真实数据、真实任务、真实健康状态和真实错误；高影响操作执行前必须展示对象范围、状态、风险项和恢复路径。
- `docs/ARCHITECTURE-BOOTSTRAP.md`：发布、自动化和设备工作区分别归属 Runtime `/api/publishing`、`/api/automation`、`/api/devices`，页面只消费 Runtime DTO，不直接拼接底层实体规则。

## 本轮范围

### 发布中心

- `submit` 在真实平台执行器未接入时，语义改为“生成人工发布交接”，不得再返回“已提交平台”。
- 回执状态使用 `manual_required`，阶段使用 `manual_handoff`。
- 返回信息必须说明：发布前检查已通过，但需要用户在 TikTok 或绑定浏览器工作区内人工完成提交。
- 下一步动作使用 `manual-publish`，按钮/提示文案为“前往人工发布”。
- 前端发布中心不得把任务总线 `succeeded` 映射成 `published`。

### 自动化执行中心

- 当前无真实动作执行器的自动化任务，运行结果不得标记为 `succeeded`。
- 运行完成预检后必须落为 `blocked`，错误码为 `automation.executor_missing`。
- 摘要和下一步动作必须说明“执行器未接入，需要先完成执行器配置或人工处理”。
- 前端状态文案不得把 `succeeded/success` 统一显示为“已完成真实任务”，应显示“检查完成”。

### 浏览器实例

- 本轮不实现真实浏览器进程启动。
- 浏览器 start/stop 的真实进程证据字段、PID、端口、心跳和恢复逻辑进入下一切片。
- 当前页面与 API 后续必须避免把单纯状态写入称为真实运行；本轮只在规格中固定该边界。

## 非目标

- 不实现 TikTok 自动发布。
- 不实现浏览器进程 launcher。
- 不新增通用执行事件表。
- 不重构 TaskManager。
- 不改动旧壳或创建新产品页面。

## 文件地图

- `apps/py-runtime/src/services/publishing_service.py`
- `apps/py-runtime/src/services/automation_service.py`
- `apps/py-runtime/src/schemas/publishing.py`
- `apps/desktop/src/pages/publishing/PublishingCenterPage.vue`
- `apps/desktop/src/pages/automation/AutomationConsolePage.vue`
- `apps/desktop/src/types/runtime.ts`
- `tests/contracts/test_publishing_runtime_contract.py`
- `tests/runtime/test_publishing_review_service.py`
- `tests/runtime/test_automation_service.py`
- `tests/contracts/test_automation_runtime_contract.py`
- `docs/RUNTIME-API-CALLS.md`

## 验收标准

- 发布 contract：`/api/publishing/plans/{id}/submit` 返回 `manual_required`，且响应、回执摘要中不出现“已提交平台”。
- 发布 runtime：服务层提交结果、计划最新回执和复盘上下文都使用人工交接语义。
- 自动化 runtime：无执行器时运行结果为 `blocked`，并持有 `automation.executor_missing`、中文原因和下一步动作。
- 自动化 contract：运行历史字段能暴露 `errorCode/errorMessage/nextAction`。
- 前端发布中心：过滤、状态标签、按钮文案和阻断语义不再把本地提交/任务成功称为“已发布”。
- 前端自动化中心：`succeeded/success` 只显示“检查完成”，`blocked` 显示为“待接入执行器”或“已阻断”。

## 回退点

如发现影响既有发布或自动化页面主流程，回退本切片仅需恢复上述服务文案、状态映射和测试断言，不涉及数据库迁移。
