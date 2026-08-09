# AI 系统 API v1

本文档是 P0-E Provider、模型、能力契约、Prompt、合成模板、能力路由与账号 AI 配方的接口真源。所有端点使用 `/api/v1` 前缀、统一成功/失败信封、Runtime Session、许可证门和中文错误反馈。

## 公共约定

| 项目 | 约定 |
| --- | --- |
| 乐观锁 | 表中标记 `rev` 的写入必须提供 `If-Match: <revision>`；首次创建 Capability Route 使用 `If-Match: 0` |
| 幂等 | 表中标记 `idem` 的写入必须提供 `Idempotency-Key` |
| 请求关联 | 可传 `X-Request-ID` 与 `X-Operation-ID`；Runtime 校验并在响应 Header 回显 |
| 分页 | `cursor` 为不透明字符串，`limit` 使用公共分页上限 |
| 长任务 | 健康检查、模型发现、能力验证返回 `202 TaskAcceptedDto` |
| 配置修订 | Provider 连接配置、模型/能力语义、Prompt 激活、模板激活和能力路由变更递增系统 AI 配置修订；无变化的健康/发现检查不递增 |
| 账号隔离 | AI Recipe 必须经过账号作用域依赖，不允许跨账号读取、验证或激活 |

写响应中的 `meta.revision` 是下一次 `If-Match` 应使用的聚合修订号，并在幂等
重放时保持不变。账号 AI Recipe 的该值是账号修订号，不等同于
`AIRecipeVersionDto.revision` 的版本对象修订号。

成功响应：

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "revision": 2,
    "invalidations": ["providers", "ai-summary"]
  }
}
```

失败响应：

```json
{
  "ok": false,
  "error": "Provider 配置已被更新，请重新加载后再试",
  "error_code": "REVISION_CONFLICT",
  "meta": {
    "currentRevision": 3,
    "invalidations": ["providers"]
  }
}
```

## Provider Profile

| 方法与地址 | 参数 | 成功 | 主要错误 |
| --- | --- | --- | --- |
| `GET /system/providers` | Query `enabled?`、`healthStatus?`、`cursor?`、`limit?` | `200 ProviderPageDto` | 公共请求错误 |
| `POST /system/providers` | `idem`；`ProviderCreateInput` | `201 ProviderDto` | `PROVIDER_ADAPTER_UNSUPPORTED`、`PROVIDER_BASE_URL_INVALID` |
| `GET /system/providers/{provider_id}` | Path | `200 ProviderDto` | `PROVIDER_NOT_FOUND` |
| `PATCH /system/providers/{provider_id}` | `rev`；`ProviderPatchInput` | `200 ProviderDto` | `PROVIDER_NOT_FOUND`、`REVISION_CONFLICT` |
| `PUT /system/providers/{provider_id}/credential` | `rev`；`ProviderCredentialInput` | `200 CredentialSummaryDto` | `PROVIDER_SECRET_UNAVAILABLE`、`REVISION_CONFLICT` |
| `POST /system/providers/{provider_id}/checks` | `idem`；`{ "force": false }` | `202 TaskAcceptedDto` | `PROVIDER_SECRET_UNAVAILABLE`、`TASK_ALREADY_RUNNING` |
| `POST /system/providers/{provider_id}/model-discovery` | `idem`；`{ "replaceMissing": false }` | `202 TaskAcceptedDto` | `PROVIDER_CONNECTION_FAILED`、`TASK_ALREADY_RUNNING` |

创建示例：

```http
POST /api/v1/system/providers
Authorization: Bearer <runtime-session-token>
Idempotency-Key: provider-create-local-comfy
Content-Type: application/json

{
  "name": "本机 ComfyUI",
  "adapterType": "comfyui",
  "baseUrl": "http://127.0.0.1:8188",
  "region": null,
  "timeoutMs": 30000,
  "maxConcurrency": 1,
  "enabled": true
}
```

Provider DTO 只返回 `credentialSummary.configured` 和可选脱敏摘要。凭据正文只进入系统安全存储，不写数据库、任务快照、事件、日志或页面缓存。远程 Provider 必须使用 HTTPS；只有 loopback 地址允许 HTTP；请求不跟随重定向且响应大小受限。

凭据更新示例：

```http
PUT /api/v1/system/providers/prov_local_comfy/credential
If-Match: 1
Content-Type: application/json

{
  "credential": "<secret>"
}
```

## Model Profile 与能力契约

| 方法与地址 | 参数 | 成功 | 主要错误 |
| --- | --- | --- | --- |
| `GET /system/models` | Query `providerId?`、`enabled?`、`capabilityKey?`、`cursor?`、`limit?` | `200 ModelPageDto` | `PROVIDER_NOT_FOUND` |
| `POST /system/models` | `idem`；`ModelCreateInput` | `201 ModelProfileDto` | `PROVIDER_NOT_FOUND`、`MODEL_ALREADY_EXISTS` |
| `GET /system/models/{model_profile_id}` | Path | `200 ModelProfileDto` | `MODEL_NOT_FOUND` |
| `PATCH /system/models/{model_profile_id}` | `rev`；`ModelPatchInput` | `200 ModelProfileDto` | `MODEL_IN_USE`、`REVISION_CONFLICT` |
| `GET /system/model-capabilities` | Query `providerId?`、`modelProfileId?`、`capabilityKey?`、`availability?`、`cursor?`、`limit?` | `200 ModelCapabilityPageDto` | `PROVIDER_NOT_FOUND`、`MODEL_NOT_FOUND` |
| `GET /system/models/{model_profile_id}/capabilities` | Path | `200 ModelCapabilityDto[]` | `MODEL_NOT_FOUND` |
| `POST /system/models/{model_profile_id}/capability-checks` | `idem`；`CapabilityCheckInput` | `202 TaskAcceptedDto` | `MODEL_NOT_FOUND`、`TASK_ALREADY_RUNNING` |

手动录入模型：

```json
{
  "providerProfileId": "prov_local_comfy",
  "modelId": "video-model-v1",
  "displayName": "视频模型 v1",
  "enabled": true,
  "baseLimits": {}
}
```

模型宣称支持某能力并不等于可用于路由。只有 `declaredSupported`、`adapterSupported` 与 `contractVerified` 同时为真时，`availability` 才为 `available`。能力检查任务类型固定为 `model.capability_check`。

## Capability Route

| 方法与地址 | 参数 | 成功 | 主要错误 |
| --- | --- | --- | --- |
| `GET /system/capability-routes` | Query `capabilityKey?`、`validationStatus?`、`cursor?`、`limit?` | `200 CapabilityRoutePageDto` | 公共请求错误 |
| `PUT /system/capability-routes/{capability_key}` | `rev`、`idem`；`CapabilityRouteInput` | `200 CapabilityRouteDto` | `CAPABILITY_ROUTE_INVALID`、`MODEL_CAPABILITY_UNVERIFIED`、`REVISION_CONFLICT` |
| `POST /system/capability-routes/{capability_key}/validate` | `idem`；无 Body | `200 CapabilityRouteDto` | `CAPABILITY_ROUTE_INVALID` |

路由示例：

```json
{
  "primaryModelProfileId": "model_video_v1",
  "fallbackModelProfileId": null,
  "promptProfileId": "prompt_ver_01JY8M4QXK",
  "enabled": true
}
```

`promptProfileId` 引用 Prompt 的不可变版本 ID，而不是 `profileKey`。Prompt
摘要通过 `activeVersionId` 暴露当前活动版本，供路由编辑器稳定引用。Provider
必须已启用且健康状态为 `ready`；默认不允许 `degraded` Provider 成为新路由。
未启用的模型、未验证的能力、没有活动版本的 Prompt 或不匹配的能力键也会使
路由验证失败。路由读取会按当前 Provider 健康证据重算展示状态，无须修改系统
AI 配置修订；未验证路由不得成为账号 AI Recipe 的有效依赖。

## Prompt Profile

| 方法与地址 | 参数 | 成功 | 主要错误 |
| --- | --- | --- | --- |
| `GET /system/prompt-profiles` | Query `capabilityKey?`、`status?`、`cursor?`、`limit?` | `200 PromptProfilePageDto` | 公共请求错误 |
| `POST /system/prompt-profiles` | `idem`；`PromptProfileInput` | `201 PromptProfileDto` | `PROMPT_PROFILE_INVALID` |
| `GET /system/prompt-profiles/{profile_key}` | Path | `200 PromptProfileDto` | `PROMPT_PROFILE_NOT_FOUND` |
| `GET /system/prompt-profiles/{profile_key}/versions/{version}` | Path | `200 PromptVersionDto` | `PROMPT_VERSION_NOT_FOUND` |
| `POST /system/prompt-profiles/{profile_key}/versions` | `rev`、`idem`；`PromptVersionInput` | `201 PromptVersionDto` | `PROMPT_PROFILE_INVALID`、`REVISION_CONFLICT` |
| `POST /system/prompt-profiles/{profile_key}/versions/{version}/activate` | `rev`、`idem`；无 Body | `200 PromptProfileDto` | `PROMPT_VERSION_NOT_FOUND`、`PROMPT_PROFILE_INVALID`、`REVISION_CONFLICT` |

Prompt 版本输入：

```json
{
  "profileKey": "script_generation",
  "name": "脚本生成",
  "capabilityKey": "script_generation",
  "systemPrompt": "根据账号定位与知识快照生成脚本。",
  "taskTemplate": "主题：{{ topic }}",
  "variablesSchema": {
    "type": "object",
    "properties": {
      "topic": {
        "type": "string"
      }
    },
    "required": ["topic"]
  },
  "outputSchema": {
    "type": "object"
  },
  "visualStylePrefix": "",
  "safetyConstraints": {}
}
```

列表与 Profile 摘要不返回 Prompt 正文；只有指定版本详情返回正文。摘要中的
`activeVersion` 是便于阅读的版本号，`activeVersionId` 是 Route 和 Recipe
覆盖项实际保存的不可变版本外键。版本创建后不可原地覆盖，激活会递增系统 AI
配置修订并使关联路由与账号 Recipe 缓存失效。

## Composition Template

| 方法与地址 | 参数 | 成功 | 主要错误 |
| --- | --- | --- | --- |
| `GET /system/composition-templates` | Query `templateType?`、`status?`、`cursor?`、`limit?` | `200 CompositionTemplatePageDto` | 公共请求错误 |
| `POST /system/composition-templates` | `idem`；`CompositionTemplateInput` | `201 CompositionTemplateDto` | `COMPOSITION_TEMPLATE_INVALID` |
| `GET /system/composition-templates/{template_key}` | Path | `200 CompositionTemplateDto` | `COMPOSITION_TEMPLATE_NOT_FOUND` |
| `GET /system/composition-templates/{template_key}/versions/{version}` | Path | `200 CompositionTemplateVersionDto` | `COMPOSITION_TEMPLATE_VERSION_NOT_FOUND` |
| `POST /system/composition-templates/{template_key}/versions` | `rev`、`idem`；`CompositionTemplateVersionInput` | `201 CompositionTemplateVersionDto` | `COMPOSITION_TEMPLATE_INVALID`、`REVISION_CONFLICT` |
| `POST /system/composition-templates/{template_key}/versions/{version}/validate` | `idem`；无 Body | `200 CompositionTemplateValidationDto` | `COMPOSITION_TEMPLATE_INVALID`、`MODEL_CAPABILITY_UNVERIFIED` |
| `POST /system/composition-templates/{template_key}/versions/{version}/activate` | `rev`、`idem`；无 Body | `200 CompositionTemplateDto` | `COMPOSITION_TEMPLATE_INVALID`、`REVISION_CONFLICT` |

模板定义是不可变版本对象，保存的是受控 `CompositionSpec` 模板，不引入多轨
时间线。摘要同时返回 `activeVersion` 与 `activeVersionId`；Recipe 的
`compositionTemplateRef` 必须保存活动版本 ID，而不是 `templateKey`。模板中的
必需能力会在验证时解析到当前系统路由；含危险协议、外部可执行命令或不受控文件
引用的模板会被拒绝。

## Account AI Recipe

| 方法与地址 | 参数 | 成功 | 主要错误 |
| --- | --- | --- | --- |
| `GET /accounts/{account_id}/ai-recipe` | 账号 Path | `200 AIRecipeDto` | `ACCOUNT_NOT_FOUND` |
| `GET /accounts/{account_id}/ai-recipe/versions` | Query `cursor?`、`limit?` | `200 AIRecipeVersionPageDto` | `ACCOUNT_NOT_FOUND` |
| `POST /accounts/{account_id}/ai-recipe/versions` | `rev`、`idem`；`AccountAIRecipeVersionInput` | `201 AIRecipeVersionDto` | `AI_RECIPE_INVALID`、`REVISION_CONFLICT` |
| `POST /accounts/{account_id}/ai-recipe/versions/{version}/validate` | `idem`；无 Body | `200 AIRecipeValidationDto` | `AI_RECIPE_INVALID`、`MODEL_CAPABILITY_UNVERIFIED` |
| `POST /accounts/{account_id}/ai-recipe/versions/{version}/activate` | `rev`、`idem`；无 Body | `200 AIRecipeDto` | `AI_RECIPE_INVALID`、`REVISION_CONFLICT` |

版本输入：

```json
{
  "name": "默认内容配方",
  "routeOverrides": {},
  "visualStyle": {
    "tone": "clean"
  },
  "voiceProfileRef": null,
  "compositionTemplateRef": "composition_ver_01JY8M5PKC",
  "costPolicy": {
    "mode": "balanced"
  },
  "fallbackPolicy": {
    "allowFallback": true
  }
}
```

Recipe 默认继承系统 Capability Route，只保存明确覆盖，不复制 Provider 凭据。验证会解析脚本、分镜与视频生成等必需能力，记录所采用的系统 AI 配置修订；系统配置变化后旧 Recipe 进入需重新验证状态。激活和版本读取均受 `account_id` 强制隔离。

## 任务、事件与缓存失效

三类任务类型固定为：

- `provider.health_check`
- `provider.model_discovery`
- `model.capability_check`

任务不保存凭据正文，只保存 Provider / Model ID、资源修订、受控能力键和非敏感策略。处理器执行时再通过安全引用读取凭据。Provider 超时、连接失败或响应无效时，任务进入失败终态，Provider / Capability 状态写入可追踪错误码与 `log_id`。

系统 AI 配置事件发布到 `system:ai`；账号 Recipe 事件发布到 `account:{account_id}:ai-recipe`。写响应的 `meta.invalidations` 告知 Desktop 失效 Provider、模型、路由、Prompt、模板、Recipe、就绪摘要或任务缓存。

## 适配器边界

P0-E 支持显式适配器类型：

- `direct_api`：受控通用 HTTP，只做通用连接，不猜测供应商协议。
- `openai_compatible`：按 OpenAI 兼容模型清单与能力族验证。
- `comfyui`：按 ComfyUI 健康与图像/视频能力验证。
- `runninghub`：显式 RunningHub 连接入口；不回退到其它供应商语义。

页面和业务服务只依赖能力接口，不硬编码供应商。需要新增协议时必须增加适配器、契约测试和配置总线项。

## legacy 退出与安全边界

非生产模式仍可读取旧 AI 设置，便于旧 Desktop 过渡；旧聚合写入、旧密钥写入、旧健康刷新、旧模型覆盖和旧 Prompt 原地增删改统一返回 HTTP `410 LEGACY_WRITE_UNSUPPORTED`，并指向版本化 v1 接口。生产模式不注册未迁移的 legacy AI 路由。

禁止：

- 把明文凭据返回给 Desktop 或写入数据库、日志、事件、任务快照和幂等响应。
- 在 Prompt 列表、事件或错误日志中返回 Prompt 正文。
- 将未验证模型或路由作为默认路由。
- 跨账号复制凭据、静默覆盖 Recipe 或绕过账号作用域。
- 自动跟随 Provider 重定向、无限读取响应或允许远程明文 HTTP。

## 路由库存索引

以下标题供文档库存门禁提取；参数、DTO、错误与示例以本文前述分域表为准。

### GET `/api/v1/system/providers`

### POST `/api/v1/system/providers`

### GET `/api/v1/system/providers/{provider_id}`

### PATCH `/api/v1/system/providers/{provider_id}`

### PUT `/api/v1/system/providers/{provider_id}/credential`

### POST `/api/v1/system/providers/{provider_id}/checks`

### POST `/api/v1/system/providers/{provider_id}/model-discovery`

### GET `/api/v1/system/models`

### POST `/api/v1/system/models`

### GET `/api/v1/system/models/{model_profile_id}`

### PATCH `/api/v1/system/models/{model_profile_id}`

### GET `/api/v1/system/model-capabilities`

### GET `/api/v1/system/models/{model_profile_id}/capabilities`

### POST `/api/v1/system/models/{model_profile_id}/capability-checks`

### GET `/api/v1/system/capability-routes`

### PUT `/api/v1/system/capability-routes/{capability_key}`

### POST `/api/v1/system/capability-routes/{capability_key}/validate`

### GET `/api/v1/system/prompt-profiles`

### POST `/api/v1/system/prompt-profiles`

### GET `/api/v1/system/prompt-profiles/{profile_key}`

### GET `/api/v1/system/prompt-profiles/{profile_key}/versions/{version}`

### POST `/api/v1/system/prompt-profiles/{profile_key}/versions`

### POST `/api/v1/system/prompt-profiles/{profile_key}/versions/{version}/activate`

### GET `/api/v1/system/composition-templates`

### POST `/api/v1/system/composition-templates`

### GET `/api/v1/system/composition-templates/{template_key}`

### GET `/api/v1/system/composition-templates/{template_key}/versions/{version}`

### POST `/api/v1/system/composition-templates/{template_key}/versions`

### POST `/api/v1/system/composition-templates/{template_key}/versions/{version}/validate`

### POST `/api/v1/system/composition-templates/{template_key}/versions/{version}/activate`

### GET `/api/v1/accounts/{account_id}/ai-recipe`

### GET `/api/v1/accounts/{account_id}/ai-recipe/versions`

### POST `/api/v1/accounts/{account_id}/ai-recipe/versions`

### POST `/api/v1/accounts/{account_id}/ai-recipe/versions/{version}/validate`

### POST `/api/v1/accounts/{account_id}/ai-recipe/versions/{version}/activate`
