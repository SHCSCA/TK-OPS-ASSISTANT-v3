# M16 AI 与系统设置多 Provider 设计 Spec

> 日期：2026-04-16
> 来源计划：`docs/superpowers/plans/2026-04-16-ai-system-settings-ui-runtime.md`
> 本批目标：完成多 Provider / 多模型选择的第一批真实 Runtime 契约、真实模型连通性诊断和前端控制台式体验重构。

## 1. 目标

`AI 与系统设置` 必须从单一表单页升级为 TK-OPS 的 AI Provider 与模型编排中心。第一批实现不追求真实内容生成调用，而是先把可扩展 Provider 注册表、模型目录、能力支持矩阵、Provider 凭据状态、真实模型连通性测试和页面选择入口打通，同时把页面重构为更适合桌面工作台的控制台式布局。

验收时用户应能看到：

1. Runtime 当前支持哪些 Provider。
2. 每个 Provider 当前状态、凭据来源、Base URL、支持能力。
3. 每个 Provider 下有哪些可选模型，并且可以针对指定模型做真实连通性测试。
4. 每个 TK-OPS AI 能力可以选择哪些 Provider 和模型。
5. 页面不是只围绕 OpenAI，而是面向主流商业模型、OpenAI-compatible、本地模型和专用媒体 Provider 扩展。
6. 页面不再表现为卡片堆叠的后台表单，而是具备清晰状态总览、分区导航、主编辑区和诊断区的系统控制台。

## 2. 非目标

- 不发起真实远端模型列表拉取。
- 不调用真实 OpenAI、Anthropic、Gemini、DeepSeek 等模型生成内容。
- 不实现真实 TTS、视频生成、字幕对齐 Provider。
- 不在页面硬编码模型选项。
- 不展示 API Key 明文。
- 不把设置页做成营销页、仪表盘或纯卡片堆叠。
- 不继续把 Runtime、Provider、能力配置和提示词编辑堆在一个超大页面组件里。

## 3. Runtime 契约

新增同步接口：

| 方法 | 路径 | 返回 |
| --- | --- | --- |
| `GET` | `/api/settings/ai-providers/catalog` | `AIProviderCatalogItem[]` |
| `GET` | `/api/settings/ai-providers/{provider_id}/models` | `AIModelCatalogItem[]` |
| `GET` | `/api/settings/ai-capabilities/support-matrix` | `AICapabilitySupportMatrix` |
| `POST` | `/api/settings/ai-providers/{provider_id}/models/refresh` | `AIModelCatalogRefreshResult` |
| `POST` | `/api/settings/ai-capabilities/providers/{provider_id}/health-check` | `AIProviderHealth` |

当前实现使用内置注册表，不访问远端拉取模型目录。`models/refresh` 返回中文说明，表示当前使用内置目录，后续远端刷新再升级 TaskBus。`health-check` 会针对指定模型发起真实 HTTP 探测，用于验证当前 Provider 与模型是否可达。

未知 Provider 必须返回统一错误信封：

```json
{
  "ok": false,
  "error": "未找到 AI Provider。"
}
```

## 4. DTO

`AIProviderCatalogItem`

```json
{
  "provider": "openai",
  "label": "OpenAI",
  "kind": "commercial",
  "configured": false,
  "baseUrl": "https://api.openai.com/v1/responses",
  "secretSource": "none",
  "capabilities": ["text_generation", "vision"],
  "requiresBaseUrl": false,
  "supportsModelDiscovery": false,
  "status": "missing_secret"
}
```

`AIModelCatalogItem`

```json
{
  "modelId": "gpt-5.4",
  "displayName": "GPT-5.4",
  "provider": "openai",
  "capabilityTypes": ["text_generation", "vision"],
  "inputModalities": ["text", "image"],
  "outputModalities": ["text"],
  "contextWindow": null,
  "defaultFor": ["script_generation", "script_rewrite", "storyboard_generation"],
  "enabled": true
}
```

`AICapabilitySupportMatrix`

```json
{
  "capabilities": [
    {
      "capabilityId": "script_generation",
      "providers": ["openai", "anthropic", "gemini", "deepseek"],
      "models": [
        {
          "provider": "openai",
          "modelId": "gpt-5.4",
          "displayName": "GPT-5.4",
          "capabilityTypes": ["text_generation", "vision"]
        }
      ]
    }
  ]
}
```

## 5. Provider 初始注册表

第一批内置注册表覆盖主流方向，但仍以 Runtime 数据输出为准：

- `openai`
- `openai_compatible`
- `anthropic`
- `gemini`
- `deepseek`
- `qwen`
- `kimi`
- `zhipu`
- `minimax`
- `doubao`
- `baidu_qianfan`
- `hunyuan`
- `xai`
- `mistral`
- `cohere`
- `openrouter`
- `ollama`
- `lm_studio`
- `vllm`
- `localai`

专用媒体 Provider 先以能力类型预留，不接入真实服务：

- `azure_speech`
- `elevenlabs`
- `volcengine_speech`
- `minimax_speech`
- `video_generation_provider`
- `asset_analysis_provider`

## 6. 前端数据流

新增 Runtime client：

- `fetchAIProviderCatalog()`
- `fetchAIProviderModels(providerId)`
- `fetchAICapabilitySupportMatrix()`
- `refreshAIProviderModels(providerId)`

扩展 `ai-capability` store：

- `providerCatalog`
- `modelCatalogByProvider`
- `supportMatrix`
- `providerHealth`
- `loadProviderCatalog()`
- `loadProviderModels(providerId)`
- `loadSupportMatrix()`
- `saveProviderSecret(providerId, input)`
- `checkProvider(providerId, model?)`

页面进入时：

1. 读取 settings/config/diagnostics。
2. 读取 AI capabilities。
3. 读取 provider catalog。
4. 读取 support matrix。
5. 默认选择第一个 Provider，并懒加载对应模型目录。

## 7. UI 结构

视觉与交互采用 `状态总览条 + 分区导航 + 主编辑区 + 诊断台 + 固定保存条` 的桌面控制台模板。

### 7.1 视觉结论

Visual thesis:
这个界面应该像一个安静、精密、可信的 AI 控制台，通过稳定的层级、少量高价值强调色和贴近任务的反馈，让用户快速知道“当前能不能创作，缺什么，下一步该处理什么”。

Primary workspace:
主编辑区不做营销 Hero，也不做后台表单墙。进入页面后先看到系统健康，再进入目标分区处理具体设置。

Core interaction:

1. 顶部状态总览条显示 Runtime、授权、已配置 Provider、已启用能力和最近同步时间。
2. 左侧分区导航在 `系统总线`、`Provider 与模型`、`能力策略`、`诊断台` 间切换主工作区。
3. `系统总线` 禁止纯手输目录和默认模型，必须优先使用选择器、目录选择按钮和结构化字段。
4. `Provider 与模型` 先选 Provider，再显示模型目录、凭据和测试入口，避免把全部 Provider 一次性铺满页面。
5. 用户改动表单后，页面底部出现稳定的“待保存变更”操作条，而不是依赖用户自己记忆哪里改过。

Motion purpose:

- 分区切换使用轻量位移与透明度过渡，强调上下文切换。
- Provider 选中、能力选中、保存成功和检查连接仅使用短时反馈动画。
- 必须支持 `prefers-reduced-motion`，降低重复动画。

### 7.2 布局要求

- 顶部：`SettingsStatusDock`
- 左侧：`SettingsSectionRail`
- 中央：按当前分区渲染系统配置、Provider 注册表/模型目录、能力矩阵/Inspector
- 右侧：Shell 级 `SystemStatusDetail` 抽屉，负责系统诊断和最近一次模型测试结果
- 底部：`SettingsSaveBar`

### 7.3 组件边界

本批必须拆分，不允许继续把页面维持为单文件巨型实现：

- `apps/desktop/src/modules/settings/components/SettingsStatusDock.vue`
- `apps/desktop/src/modules/settings/components/SettingsSectionRail.vue`
- `apps/desktop/src/modules/settings/components/SettingsSaveBar.vue`
- `apps/desktop/src/modules/settings/components/SettingsSystemFormPanel.vue`
- `apps/desktop/src/modules/settings/components/ProviderCatalogPanel.vue`
- `apps/desktop/src/modules/settings/components/AICapabilityMatrix.vue`
- `apps/desktop/src/modules/settings/components/AICapabilityInspector.vue`
- `apps/desktop/src/components/shell/details/SystemStatusDetail.vue`

`AISystemSettingsPage.vue` 只保留路由级编排、分区状态、草稿状态、目录选择和 store 协调，不再内嵌重复诊断台。

## 8. 状态矩阵

| 状态 | UI 行为 |
| --- | --- |
| `loading` | 状态总览显示读取中，主区保留稳定骨架 |
| `ready` | 展示能力、Provider、模型目录 |
| `saving` | 保存按钮禁用，草稿不丢失 |
| `checking` | Provider 行展示检查中 |
| `error` | 中文错误靠近失败区域展示 |
| `disabled` | 未配置密钥、Provider 不支持能力、模型不可选时显示原因 |
| `dirty` | 底部保存条出现，显示待保存变更数量与保存入口 |

## 9. 测试要求

后端先写失败测试：

- Provider catalog 返回多 Provider 注册表。
- Provider models 返回指定 Provider 的模型目录。
- support matrix 返回每个能力的可选模型。
- 未知 Provider 返回中文错误信封。

前端先写失败测试：

- Runtime client 可以调用 catalog/models/support-matrix。
- `ai-capability` store 能加载 catalog、models、support matrix。
- 设置页展示状态总览条、分区导航、诊断台和固定保存条。
- 设置页展示多 Provider 目录和模型目录，而不是只展示 OpenAI。
- 设置页在字段变化后显示待保存变更提示，不要求用户自己推断页面是否处于草稿态。

## 10. 验收命令

```powershell
venv\Scripts\python.exe -m pytest tests\contracts\test_ai_capabilities_contract.py tests\runtime\test_ai_capabilities.py -q
npm --prefix apps/desktop run test -- ai-system-settings
npm --prefix apps/desktop run test
git diff --check
```

## 11. 风险

- Provider 和模型清单会变化，因此实现必须集中在 Runtime 注册表，不能分散在页面。
- 模型目录第一批是内置目录，不代表远端实时可用。
- Provider health-check 已升级为真实 HTTP 探测，但媒体类 Provider 的专用探测策略仍需后续补齐。
- 浏览器级截图验收受首启/授权前置守卫影响，需要使用稳定 mock 或专用视觉验收脚本。
