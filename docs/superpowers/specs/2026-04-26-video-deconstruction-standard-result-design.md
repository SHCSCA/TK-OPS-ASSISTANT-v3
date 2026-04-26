# 视频拆解标准结果设计

## 背景

视频拆解中心界面已经稳定为三大板块：脚本文案、视频关键帧、内容结构。当前 Runtime 仍以 `transcript`、`segments`、`structure.scriptJson`、`metadataJson` 等旧字段为主，导致前端需要临时解析和推断展示内容。该设计将结果契约上移到 Runtime，保证后续模型、页面和项目回流使用同一套结构。

## 目标

1. Runtime 对外返回统一标准结构：`script`、`keyframes`、`contentStructure`、`source`。
2. 前端三栏只读标准结构，旧字段仅作为兼容兜底。
3. 多模态模型提示词直接要求输出标准 JSON，减少二次猜测。
4. “应用至项目”继续使用同一结构回流脚本与分镜。

## 标准结构

```json
{
  "script": {
    "title": "",
    "language": "",
    "fullText": "",
    "lines": [
      { "startMs": 0, "endMs": 3000, "text": "", "type": "speech" }
    ]
  },
  "keyframes": [
    {
      "index": 1,
      "startMs": 0,
      "endMs": 3000,
      "visual": "",
      "speech": "",
      "onscreenText": "",
      "shotType": "",
      "camera": "",
      "intent": ""
    }
  ],
  "contentStructure": {
    "topic": "",
    "hook": "",
    "painPoints": [],
    "sellingPoints": [],
    "rhythm": [],
    "cta": "",
    "reusableForScript": [],
    "reusableForStoryboard": [],
    "risks": []
  },
  "source": {
    "provider": "",
    "model": "",
    "promptVersion": "video_deconstruction_result_v1"
  }
}
```

## 数据流

1. 用户导入视频，Runtime 写入视频基础元数据。
2. 用户点击开始拆解，Runtime 调用视频解析模型。
3. 多模态模型返回标准 JSON 或接近标准 JSON。
4. Runtime 解析、校验、归一化，并保存原始 artifact。
5. Runtime 响应标准结果，同时保留旧字段。
6. 前端 store 缓存标准结果。
7. 视频拆解页三栏读取标准字段展示。
8. 应用至项目时，Runtime 使用标准结构生成脚本版本和分镜版本。

## 错误处理

- Provider 返回不可解析内容时，Runtime 记录日志并回退旧转录/分段逻辑。
- 标准结果缺少某个字段时，Runtime 输出空字符串或空数组，不把错误推给前端。
- 前端标准结果为空时显示明确空态，提示重新拆解。

## 兼容策略

- `VideoDeconstructionResultDto` 继续保留 `transcript`、`segments`、`structure`、`stages`。
- 新增 `GET /videos/{video_id}/result`，用于刷新已拆解视频的完整结果。
- 前端保留旧字段兜底，但主路径不再依赖 `metadataJson` 和 `scriptJson`。

## 测试

- Runtime 测试覆盖标准字段返回、标准字段从多模态 artifact 归一化、无 artifact 时旧字段兜底。
- Contract 测试覆盖一键拆解和查询结果接口。
- Frontend 测试覆盖三栏读取标准字段，以及旧 provider 阶段不污染已生成结果。
