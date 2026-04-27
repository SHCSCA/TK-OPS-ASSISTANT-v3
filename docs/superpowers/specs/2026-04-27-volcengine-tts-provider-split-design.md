# 2026-04-27 火山豆包语音 Provider 分离设计

## API Boundary

- `POST /api/voice/providers/{provider_id}/profiles/refresh`
- 成功返回统一信封：

```json
{
  "ok": true,
  "data": {
    "provider": "volcengine_tts",
    "status": "refreshed",
    "message": "已同步 2 个音色。",
    "savedCount": 2,
    "profiles": []
  }
}
```

- 不支持的 Provider 返回 400，错误文案为中文。
- 同步失败返回 502 或 500，不暴露 traceback。

## Data Contract

- `VoiceProfileDto` 继续复用现有字段：`id/provider/voiceId/displayName/locale/tags/enabled`。
- 新增 `VoiceProfileRefreshResultDto`，只描述刷新结果，不新增持久化字段。
- 火山豆包语音音色的 Provider 固定为 `volcengine_tts`。
- 历史 `volcengine` 音色在配音链路中归一化为 `volcengine_tts`，避免调用方舟配置。

## Provider Boundary

- `volcengine`：只保留方舟模型能力，如文本、视觉、资产分析、视频生成。
- `volcengine_tts`：只负责 TTS，默认 Base URL 指向豆包语音 V3 SSE 接口。
- TTS 调度器按 Runtime provider id 匹配适配器，`volcengine_tts` 使用 `VolcengineTTSAdapter`。
- 火山 TTS 响应的 provider 标识返回 `volcengine_tts`，用于轨道审计。

## Task Flow

- 生成整片配音与片段重生成都先解析音色，再归一化 Provider，再取对应 Runtime 配置。
- Runtime 不可用时继续返回阻断草稿。
- Runtime 可用时 TaskBus 状态保持原有 `ai-voice` 任务形态，失败信息写入 track config 的 `lastOperation.errorMessage`。

## Frontend Integration

- Runtime client 增加 `refreshVoiceProfiles(providerId)`。
- Pinia store 增加 `refreshProfiles(providerId)`，同步后刷新音色列表并保留可用选择。
- 配音中心音色栏增加“同步音色”按钮，默认同步 `volcengine_tts`。

## Verification

- Runtime 单测覆盖 Provider 分离、音色刷新 upsert、配音调用 `volcengine_tts`。
- Contract 测试覆盖新增 Voice API 返回信封。
- Frontend 构建验证 Runtime client/type/UI 改动。
