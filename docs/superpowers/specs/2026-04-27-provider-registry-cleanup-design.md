# Provider 注册表清理设计说明

## 背景

当前 AI 与系统设置页直接平铺 Runtime 返回的完整 Provider 注册表。这个注册表同时包含通用模型平台、TTS、ASR、视频生成、资产分析和自定义 Provider，导致用户在脚本生成、分镜生成等能力里看到大量不相关厂商。

## 设计原则

1. Provider 是“接入账号/服务端点”，不是每一个能力的平铺菜单项。
2. 模型、音色、视频端点、转写端点属于 Provider 下的能力目录。
3. 能力绑定只展示当前能力可用的 Provider，不能让 TTS/ASR/视频专项 Provider 混入文本能力。
4. Provider Hub 保留完整注册表，但用分组解释它们是什么，避免误解为同一种模型供应商。
5. 不删除 Runtime 支持项，避免破坏国内厂商、自定义接入、语音和视频链路。

## Provider 分组

| 分组 | 含义 | 示例 |
| --- | --- | --- |
| 模型平台 | 文本、视觉、多模态、OpenAI 兼容网关、本地模型 | OpenAI、DeepSeek、通义千问、火山方舟、百度千帆、Ollama、OpenRouter |
| 媒体专项 | TTS、ASR、视频生成、资产分析等非通用 LLM 接入 | 火山豆包语音、Azure Speech、ElevenLabs、可灵、即梦、Vidu |
| 自定义接入 | 用户自己维护 Base URL、密钥和模型目录的专项适配 | 自定义 OpenAI 兼容、自定义视频生成、自定义语音合成、自定义转写 |

## 能力绑定规则

- 读取 Runtime support matrix。
- Provider 下拉只显示 `supportItem.providers` 内的 Provider。
- 当前已绑定 Provider 如果不在推荐列表中，仍保留在下拉里，便于用户看到旧配置并切换。
- 模型下拉优先展示已同步模型目录，未同步时展示 support matrix 推荐模型。

## 交互结果

- 用户在 “脚本生成” 里不会看到“火山豆包语音、阿里云语音识别、视频生成 Provider”。
- 用户在 Provider Hub 里仍能找到 TTS、ASR、视频厂商，并能配置凭据、同步目录或进入后续专项链路。
- 自定义能力不再像一堆占位 Provider 平铺，而是统一归入“自定义接入”。

## 验证

- Vitest 覆盖能力 Provider 过滤。
- Vitest 覆盖 Provider Hub optgroup 分组。
- 前端构建验证 TypeScript 和模板编译。
