# Provider Hub V2 改造计划

> 计划状态：用户已在 2026-04-24 确认 V2 设计方向。  
> 对应设计稿：`docs/design-drafts/2026-04-24-provider-hub-redesign-v2.svg`

## 1. 目标

把“Provider 与模型”从全量供应商卡片墙改成 Provider Hub：

1. 主工作区优先展示已接入 Provider、当前模型目录和当前凭据 Inspector。
2. 国内厂商以模板库方式收纳，避免所有供应商直接铺满页面。
3. 支持自定义 Provider 模板，包括 OpenAI 兼容、视频生成和 TTS 三类接入。
4. 配置好 Provider 后，仍通过 Runtime 模型目录接口获取真实可用模型，并按文本、视觉、视频、TTS、ASR、字幕等能力标注。

## 2. 边界

- 不新增正式页面，只改 AI 与系统设置页内的 Provider 工作区。
- 不新增假连通、假成功率或伪模型可用状态。
- Provider 模板可以是静态注册表，但模型刷新必须走 Runtime 真实接口和错误信封。
- 自定义 Provider 本阶段先作为可配置模板进入统一注册表，不新增独立路由或弹窗向导。
- 不绕过现有 `/api/settings/ai-providers/*`、`/api/settings/ai-capabilities/*` 和配置总线。

## 3. 文件地图

- 修改：`apps/py-runtime/src/schemas/ai_capabilities.py`
- 修改：`apps/py-runtime/src/services/ai_capability_service.py`
- 修改：`apps/desktop/src/types/runtime.ts`
- 修改：`apps/desktop/src/pages/settings/AISystemSettingsPage.vue`
- 修改：`apps/desktop/src/modules/settings/components/ProviderCatalogPanel.vue`
- 测试：`tests/contracts/test_ai_capabilities_contract.py`
- 测试：`tests/runtime/test_ai_capabilities.py`
- 测试：`apps/desktop/tests/ai-settings-layout-contract.spec.ts`
- 测试：`apps/desktop/tests/ai-system-settings.spec.ts`
- 测试夹具：`apps/desktop/tests/runtime-helpers.ts`

## 4. 阶段

### 阶段一：Runtime 目录契约扩展

- 给 `AIProviderCatalogItemDto` 增加 `region`、`category`、`protocol`、`modelSyncMode`、`tags`。
- Provider metadata 统一补齐这些字段。
- 国内主流厂商纳入模板注册表，覆盖文本、视觉、视频和语音方向。
- 自定义 Provider 纳入注册表，必须要求 Base URL，避免误认为已就绪。

### 阶段二：模型目录与远端刷新

- 静态模型目录补充国内厂商代表模型，按 `capabilityTypes`、`inputModalities`、`outputModalities` 标注。
- 支持 OpenAI 兼容类 Provider 通过 `/models` 刷新模型目录。
- Ollama 与 OpenRouter 保持已有专用刷新逻辑。
- 无密钥、无 Base URL、远端异常必须保持结构化中文错误。

### 阶段三：Provider Hub 前端

- Provider 工作区分为已接入列表、模板库、模型目录、凭据 Inspector。
- 已接入列表只突出 configured 或当前 Provider，不再把所有 Provider 铺成大卡片。
- 模板库按国内、国际、本地、自定义分组，显示能力标签和同步模式。
- 模型目录显示当前 Provider 的模型能力、输入/输出模态和默认用途。
- 模型目录按 10 条一页分页，支持模型名称/ID 搜索和能力筛选，避免几百个远端模型挤占主工作区。
- 凭据 Inspector 继续承载 API Key、Base URL、保存、刷新和连接检查。

## 5. 验证

- Runtime：
  - `venv\Scripts\python.exe -m pytest tests/contracts/test_ai_capabilities_contract.py tests/runtime/test_ai_capabilities.py`
- Frontend：
  - `npm run test -- ai-settings-layout-contract.spec.ts ai-system-settings.spec.ts`
  - `npm run build`
- 静态检查：
  - `git diff --check`
- 浏览器预览：
  - Provider 页不再是全量卡片墙。
  - 模板库可看到国内厂商和自定义 Provider。
  - 当前模型目录可看到文本、视觉、视频、TTS 等能力标签。
  - 当前模型目录同时最多显示 10 个模型，能通过上下页或筛选定位模型。

## 6. 回退点

- 如果远端 `/models` 兼容性不足，先回退 OpenAI 兼容刷新逻辑，不回退注册表字段。
- 如果 Provider Hub 紧凑窗口拥挤，先回退 CSS 网格，不回退 Runtime 契约扩展。
