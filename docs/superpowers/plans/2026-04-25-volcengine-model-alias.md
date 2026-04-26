# 2026-04-25 火山方舟旧模型别名修复计划

## 背景

- 当前 Runtime 在火山方舟同步模型目录后，能拿到真实的版本化模型 ID，例如 `doubao-seed-1-6-251015`。
- 系统静态目录里仍保留旧别名 `doubao-seed-1.6`。
- 当用户已有该模型家族权限时，健康检查和文本生成仍可能继续使用旧别名，导致被远端判定为 `404`。

## 目标

- 让旧模型别名在 Runtime 内自动解析到当前真实可用的模型 ID。
- 让 Provider 模型目录优先展示远端真实模型，避免旧静态别名继续误导用户。
- 保持改动最小，只修复模型解析链路，不扩展 Provider 协议和 UI 范围。

## 文件地图

- `apps/py-runtime/src/services/ai_capability_service.py`
- `apps/py-runtime/src/services/ai_text_generation_service.py`
- `tests/runtime/test_ai_capabilities.py`
- `tests/runtime/test_ai_text_generation_service.py`

## 分阶段

### 阶段 1：测试定义

- 增加 Runtime 测试，覆盖火山方舟远端同步后旧别名解析到版本化模型。
- 增加文本生成服务测试，覆盖运行时调用使用解析后的模型 ID。

### 阶段 2：实现修复

- 在 AI Capability Service 中增加统一模型别名解析。
- 在模型目录输出前去掉已被远端真实模型取代的旧静态别名。
- 在健康检查与文本生成链路中统一使用解析后的模型 ID。

### 阶段 3：验证

- 运行相关 Runtime 测试。
- 确认旧别名不再出现在火山方舟模型目录中。
- 确认健康检查和文本生成使用的是解析后的真实模型 ID。

## 边界与回退点

- 不改动前端交互结构。
- 不修改 Provider 基础协议适配层。
- 若别名解析出现误伤，优先回退“静态旧模型去重”逻辑，保留运行时显式解析能力。
