# Runtime 页面测试硬化设计

## 决策

本轮采用“契约先行、最小修复”的设计。M09-M15 不进入功能扩展，只补足现有边界的测试，并修复违反 Runtime 信封或 store 错误态的最小问题。

## 前端设计

- Runtime client 测试覆盖 M09-M15 wrapper 的 path、method、query、body 和错误信封转换。
- Store 测试覆盖加载、增删改、刷新、触发、取消、分析等当前已有动作。
- Store 失败路径必须有可断言错误态；M09/M10 如缺少 `error` 字段，补齐为最小状态字段。
- 测试使用 Runtime 契约形状的小型对象，不引入页面假业务指标。

## Runtime 设计

- 所有被前端消费的成功响应继续返回 `{ "ok": true, "data": ... }`。
- M11-M14 DELETE 路由不得返回空 204；统一返回 `{ "deleted": true }` 的成功信封。
- 本轮不更改 M09-M15 的数据模型和 DTO 命名。
- 现有 404/409 等错误继续由 app factory 转换为 `{ "ok": false, "error": ... }`。

## 验收标准

- M09-M15 至少具备前端 client/store 测试与后端契约测试。
- TaskBus/video-import 现有测试继续通过。
- 后端合同测试能证明 DELETE、创建、读取、动作类接口使用统一 JSON 信封。
- 前端 build 与 Vitest 通过；Runtime 与 contracts pytest 通过。
