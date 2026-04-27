# 当前可用 Provider 收敛 Design

## Decision

当前版本只暴露真实接入的 Provider：

- `openai`
- `deepseek`
- `volcengine`
- `volcengine_tts`

其中 `volcengine_tts` 是火山豆包语音的专项 Provider，仍作为单独运行时配置项保存，因为它使用豆包语音 API Key、Base URL 和 TTS 协议，不与火山方舟 OpenAI 兼容接口混用。

## Provider Catalog

Runtime 在服务层增加支持 Provider 白名单，`get_provider_catalog()`、模型目录、支持矩阵都基于该白名单过滤。这样前端、能力绑定和右侧上下文不会再看到未连通厂商。

## Voice

配音中心只展示 `volcengine_tts` 音色：

- 内置种子音色改为豆包语音音色。
- `refresh_provider_profiles("volcengine_tts")` 在没有 OpenAPI AK/SK 时，从官方音色文档维护的内置目录写入本地音色。
- 有 AK/SK 时继续调用 `ListSpeakers` 获取账号可用音色。

## UI

前端继续做防御性过滤，但支持白名单从隐藏自定义 Provider 改成只允许当前支持 Provider。系统表单、Provider Hub、能力 Inspector 使用同一份 `visibleProviderCatalog`。

## Risks

- 旧数据库里可能已有其他 Provider 配置和音色。当前策略不删除旧数据，只是不展示、不参与选择。
- 官方音色列表会更新。内置目录只作为无 AK/SK 的回退，账号真实全量仍以 `ListSpeakers` 为准。
