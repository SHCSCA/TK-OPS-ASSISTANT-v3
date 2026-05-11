# 2026-05-11 火山豆包 TTS 2.0 OpenAPI 凭据与音色同步设计

## API Boundary

- 继续复用 AI Provider 配置接口：
  - `PUT /api/settings/ai-capabilities/providers/{provider_id}/secret`
  - `GET /api/settings/ai-capabilities`
  - `GET /api/settings/ai-providers/{provider_id}/models`
- 继续复用配音中心音色同步接口：
  - `POST /api/voice/providers/{provider_id}/profiles/refresh`
- 所有返回值保持 Runtime 统一信封：

```json
{ "ok": true, "data": {} }
```

```json
{ "ok": false, "error": "中文错误说明" }
```

## Provider Secret Contract

`AIProviderSecretInput` 保持兼容旧字段，并新增 `volcengine_tts` 专用可选字段：

```ts
type AIProviderSecretInput = {
  apiKey?: string
  baseUrl?: string
  accessToken?: string
  appId?: string
  openApiAccessKey?: string
  openApiSecretKey?: string
  openApiRegion?: string
}
```

- 普通 Provider 仍要求 `apiKey` 非空。
- `volcengine_tts` 支持分次保存：
  - 用户先保存合成 Access Token，再补 OpenAPI AK/SK 时，后端合并已有密钥。
  - 用户只补 OpenAPI AK/SK 时，不覆盖已保存的合成 Access Token。
  - 用户填写新的 Access Token 时，才覆盖合成凭据。
- 后端统一把 `volcengine_tts` 密钥归一化为 SecretStore 中的 JSON 字符串，字段为：

```json
{
  "api_key": "合成 Access Token",
  "app_id": "可选 App ID",
  "access_key": "OpenAPI Access Key ID",
  "secret_key": "OpenAPI Secret Access Key",
  "region": "cn-beijing"
}
```

- 配置状态返回不新增明文字段，只继续返回 `maskedSecret`、`configured`、`secretSource` 等脱敏信息。

## Voice Catalog Sync

- `volcengine_tts` 音色同步使用火山 OpenAPI `ListSpeakers`：

```json
{
  "ResourceIDs": ["seed-tts-2.0"],
  "Page": 1,
  "Limit": 100
}
```

- 请求服务固定为 `speech_saas_prod`，默认区域 `cn-beijing`。
- OpenAPI 凭据解析兼容以下字段：
  - `access_key` / `accessKey` / `openApiAccessKey`
  - `secret_key` / `secretKey` / `openApiSecretKey`
  - `region` / `openApiRegion`
- `Categories`、`NormalLabels`、`SpecialLabels` 按递归方式提取标签，兼容官方嵌套结构：

```json
[{ "Categories": ["视频配音", "通用场景"] }]
```

- 本地 VoiceProfile 仍复用现有字段：
  - `provider`
  - `voiceId`
  - `displayName`
  - `locale`
  - `tags`
  - `enabled`
- 音色同步接口失败时返回中文错误，不回写伪造的完整音色库。

## TTS Runtime Contract

- `volcengine_tts` 供应商模型目录只暴露：
  - `seed-tts-2.0`
- `_resolve_resource_id` 默认与最终返回都固定为 `seed-tts-2.0`，不再根据 `mars_bigtts`、`iv_bigtts`、`mars_speech` 推导到 `seed-tts-1.0`。
- `_normalize_tts_model` 不再把 `doubao-tts` 映射到 `seed-tts-1.0`。
- `_model_for_voice_id` 对 `volcengine_tts` 音色统一返回 `seed-tts-2.0`。
- 旧音色如果已存在但不属于官方 `seed-tts-2.0` 同步结果，只能作为历史数据留存或被同步替换，不能触发 1.0 调用。

## Frontend Contract

设置页 `ProviderCatalogPanel` 对 `providerId === "volcengine_tts"` 展示专用凭据字段：

- 合成 Access Token
- App ID（可选）
- OpenAPI Access Key ID
- OpenAPI Secret Access Key
- OpenAPI Region（默认 `cn-beijing`）
- Base URL

其他 Provider 维持现有 `API Key + Base URL` 表单。

`AISystemSettingsPage` 的 `providerDrafts` 扩展为统一草稿结构，保存时将专用字段原样传给 Runtime，不在前端拼接 JSON 密钥。

保存成功后清空所有敏感输入字段，仅保留 Base URL 与 Region 等非密钥字段。

## Testing Strategy

### RED Tests

1. Runtime 配置测试：`volcengine_tts` 可在已有合成 Access Token 后追加 OpenAPI AK/SK，且后端合并为 JSON secret。
2. Runtime 模型目录测试：`volcengine_tts` 模型目录不再包含 `seed-tts-1.0`。
3. Voice source 测试：`ListSpeakers` 请求参数固定为 `ResourceIDs: ["seed-tts-2.0"]`，嵌套分类被提取到 tags。
4. TTS adapter 测试：包含旧 1.0 标记的 voice id 也使用 `seed-tts-2.0`。
5. Voice service 测试：同步音色生成任务不因非 `uranus` voice id 回退到 `seed-tts-1.0`。
6. Frontend store / layout contract 测试：`AIProviderSecretInput` 支持新字段，Provider 设置面板渲染火山 TTS 专用字段。

### Verification Commands

```powershell
pytest tests/runtime/test_ai_capabilities.py tests/runtime/test_ai_providers.py tests/runtime/test_voice_service.py
pytest tests/contracts/test_ai_capabilities_contract.py tests/contracts/test_voice_runtime_contract.py
npm --prefix apps/desktop run test -- ai-capability-store.spec.ts ai-settings-layout-contract.spec.ts
npm --prefix apps/desktop run build
git diff --check
```

## Rollback

- 若前端专用字段引发兼容问题，可只保留后端扩展字段，前端暂时继续通过高级 JSON 形式配置，但仍由后端归一化和校验。
- 若远端音色同步失败，保留已有本地音色并返回同步失败提示，不覆盖已可用的用户配置。
- 若 `seed-tts-1.0` 移除影响历史任务，只允许历史任务展示旧记录，不允许新生成任务继续调用 1.0。

