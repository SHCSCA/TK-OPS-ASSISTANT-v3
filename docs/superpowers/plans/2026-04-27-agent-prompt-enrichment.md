# Agent 提示词补强计划

## 背景

用户提供 `TK-OPS_Agent_Prompts_Markdown_Config.xlsx`，其中脚本生成、脚本改写、分镜生成的角色职责和链路规则比当前运行时默认提示词更完整。当前 Runtime 已经改为脚本与分镜 JSON 真源，不能直接回退到 Markdown 输出，否则会破坏脚本解析、分镜解析和前端结构化渲染。

## 目标

- 保留 `script_document_v1` 与 `storyboard_document_v1` 的严格 JSON 输出契约。
- 吸收 Excel 中脚本生成的高留存结构、前 3 秒强钩子、可拍摄要求、CTA 和合规约束。
- 吸收 Excel 中脚本改写的主题一致、段落映射、下游刷新和变更交接规则。
- 吸收 Excel 中分镜生成的 `segmentId -> shotId` 映射、真实实拍 / AI 视频区分、竖屏拍摄和镜头节奏规则。
- 保持视频拆解与素材分析使用当前更完整的 JSON 拆解契约，不被旧版素材分析 Markdown 覆盖。

## 文件地图

- `apps/py-runtime/src/services/ai_default_prompts.py`
  - 补强默认 Agent 系统提示词与用户模板。
- `tests/runtime/test_ai_capabilities.py`
  - 增加默认提示词必须包含关键规则且仍保持严格 JSON 契约的回归断言。

## 验证方式

- 运行 AI 能力默认配置相关测试。
- 运行脚本与分镜 JSON 链路相关回归测试。
- 运行 `git diff --check` 做文本级检查。

## 边界

- 不开放用户编辑角色提示词。
- 不改变 Provider、模型、能力矩阵和 UI 布局。
- 不把 Excel 的 Markdown 输出格式作为运行时默认输出格式。
