# 2026-05-25 智能粗剪能力就绪设计规格

## 1. 对应计划

对应计划：`docs/superpowers/plans/2026-05-25-delivery-readiness.md`

本规格覆盖阶段 2 的第二批切片：`magic_cut` 智能粗剪能力启用、配置预检和用户可恢复反馈。

## 2. 背景问题

用户在 AI 剪辑工作台触发“智能粗剪”后，后台任务失败：

```text
ProviderHTTPException: 400: 当前 AI 能力已停用。
```

这说明当前链路允许任务入队后才暴露能力停用问题。对用户来说，这会表现为“点击后进入后台任务，等待一段时间才失败”，不符合交付可用性要求。

## 3. 目标

- `magic_cut` 必须纳入统一 AI 能力配置和 Provider 支持矩阵。
- 后端在任务入队前完成能力启用、Provider、模型和密钥预检。
- 能力停用、Provider 未配置、模型不支持、密钥缺失等错误必须返回中文可恢复提示。
- 前端在发起智能粗剪前展示当前能力状态；不可用时禁用动作或展示明确阻断原因。
- 任务真正入队后才显示“已进入任务队列”，不得把预检失败伪装为后台失败。

## 4. 后端契约

### 4.1 能力配置

`AICapabilityService` 默认能力列表必须包含：

| capabilityId | label | capabilityType | 默认状态 |
| --- | --- | --- | --- |
| `magic_cut` | 智能粗剪 | `text_generation` | 若已有默认文本生成 Provider 可用，则可启用；否则保持禁用但给出明确原因 |

约束：

- 不新增独立 Provider 类型，`magic_cut` 使用文本生成能力。
- 不绕过 `AITextGenerationService` 和 `AICapabilityService`。
- 默认提示词应进入统一默认提示词管理，不在 `workspace_service.py` 内写死大段 Prompt。

### 4.2 命令预检

`workspace_service.py` 在处理 `payload.capabilityId === "magic_cut"` 时：

1. 调用统一能力预检。
2. 能力不可用时不创建后台任务，直接返回统一错误信封。
3. 能力可用时才创建任务并进入异步执行。
4. 异步执行失败必须记录日志，并返回任务失败事件，不把 traceback 暴露给 UI。

错误文案要求：

- 能力关闭：`智能粗剪能力未启用，请先在 AI 与系统设置中启用并保存。`
- Provider 未配置：`智能粗剪 Provider 未配置，请先选择可用文本模型。`
- 密钥缺失：`智能粗剪 Provider 密钥缺失，请先完成密钥配置。`
- 模型不支持：`当前模型不支持智能粗剪所需的文本生成能力，请更换模型。`

## 5. 前端契约

AI 剪辑工作台智能粗剪入口：

- 读取统一能力配置或 Runtime 预检结果，不在页面内硬编码 Provider 规则。
- 能力不可用时，按钮应禁用或点击后立即展示中文阻断提示。
- 顶部提示应区分：
  - 预检失败：`智能粗剪暂不可用：...`
  - 已入队：`AI 命令 magic_cut 已进入任务队列。`
  - 任务失败：展示 Runtime 返回的中文错误。

设置页：

- `magic_cut` 能力名称展示为 `智能粗剪`。
- 支持选择文本生成 Provider / 模型。
- 保存后经配置总线和能力总线刷新，不使用页面本地配置副本作为真源。

## 6. 测试规格

Runtime 测试：

- 能力默认配置包含 `magic_cut`。
- `magic_cut` 关闭时，工作台 AI 命令预检返回中文错误，且不入队。
- Provider 密钥缺失或模型不支持时返回可恢复中文错误。
- 能力可用时才入队，并保留现有任务反馈。

前端测试：

- 设置页展示 `magic_cut` 为 `智能粗剪`。
- 工作台在预检失败时显示“智能粗剪暂不可用”且不显示“已进入任务队列”。
- 工作台在成功入队时继续显示真实 Runtime 入队反馈。

验证命令：

```powershell
python -m pytest tests/runtime/test_ai_capabilities.py tests/runtime/test_workspace_service.py tests/contracts/test_ai_capabilities_contract.py
npm --prefix apps/desktop test -- ai-system-settings-magic-cut ai-editing-workspace-page runtime-client-workspace
npm --prefix apps/desktop test
npm --prefix apps/desktop run build
```

## 7. 子代理分工

- `.codex/agents/engineering-backend-architect.toml`：审计并实现 Runtime 能力配置、预检和错误语义。
- `.codex/agents/engineering-frontend-developer.toml`：审计并实现工作台与设置页用户反馈。
- `.codex/agents/testing-api-tester.toml`：验证 Runtime 契约、错误码和不入队语义。
- `.codex/agents/engineering-code-reviewer.toml`：复核配置总线、能力总线、异常日志和测试覆盖。

主代理负责：

- 控制范围，不把本切片扩展成真实渲染或发布。
- 审核不出现页面内硬编码 Provider 规则。
- 确保禁用能力不会进入后台任务后才失败。

## 8. 非目标

- 不实现真实视频渲染。
- 不实现 TikTok 发布。
- 不新增新的 AI Provider。
- 不重构整个 `workspace_service.py`，只做必要边界收口。
