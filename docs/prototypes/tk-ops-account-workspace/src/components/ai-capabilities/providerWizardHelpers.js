import { prototypeConfig } from "../../config/prototypeConfig.js";

export function createProviderDraft() {
  const adapter = prototypeConfig.ai.adapterTypes[0];
  return {
    adapterType: adapter.id,
    baseUrl: adapter.defaultBaseUrl,
    concurrency: 2,
    credentialRef: "演示安全引用",
    discoveredModels: [],
    name: adapter.label,
    timeoutSeconds: adapter.timeoutSeconds,
  };
}

export function applyAdapterDefaults(draft, adapterType) {
  const adapter = prototypeConfig.ai.adapterTypes.find((item) => item.id === adapterType);
  return adapter ? { ...draft, adapterType, baseUrl: adapter.defaultBaseUrl, name: adapter.label, timeoutSeconds: adapter.timeoutSeconds } : draft;
}

export function discoverDemoModels(adapterType) {
  const definitions = {
    "openai-compatible": [{ modelId: "custom-text-model", displayName: "Custom Text Model", declaredAbilities: ["text-generation", "structured-output"], adapterAbilities: ["text-generation", "structured-output"], inputModalities: ["文本"], adapterInputModalities: ["文本"], contextLimit: "能力待实测", parameterSchema: { temperature: "0–2", structuredOutput: true } }],
    comfyui: [{ modelId: "local-workflow", displayName: "Local Workflow", declaredAbilities: ["text-to-image", "image-to-video"], adapterAbilities: ["text-to-image", "image-to-video"], inputModalities: ["文本", "图片"], adapterInputModalities: ["文本", "图片"], contextLimit: "由工作流定义", parameterSchema: { ratios: ["9:16", "16:9"], resolutions: ["720p"] } }],
    runninghub: [{ modelId: "remote-workflow", displayName: "Remote Workflow", declaredAbilities: ["text-to-video", "image-to-video"], adapterAbilities: ["text-to-video", "image-to-video"], inputModalities: ["文本", "图片"], adapterInputModalities: ["文本", "图片"], contextLimit: "需验证公开契约", parameterSchema: {} }],
  };
  return definitions[adapterType] || [];
}

export function normalizeDiscoveredModels(providerId, models) {
  return models.map((model, index) => ({
    ...model,
    contractIssues: model.parameterSchema && Object.keys(model.parameterSchema).length ? [] : ["公开参数契约尚未验证"],
    contractVerified: Boolean(model.parameterSchema && Object.keys(model.parameterSchema).length),
    discoverySource: "discovered",
    enabled: true,
    id: `${providerId}-${index + 1}`,
    providerProfileId: providerId,
    sourceLabel: "添加 Provider 向导",
    verifiedAt: model.parameterSchema && Object.keys(model.parameterSchema).length ? "2026-07-19" : null,
  }));
}

export function validateProviderStep(step, draft) {
  if (step === 0 && !draft.adapterType) return "请选择连接类型";
  if (step === 1 && !draft.name.trim()) return "请输入 Provider 名称";
  if (step === 1 && !/^https?:\/\//.test(draft.baseUrl.trim())) return "请输入有效的 HTTP 地址";
  if (step === 1 && !draft.credentialRef.trim()) return "请填写安全凭据引用";
  if (step === 2 && (!Number(draft.concurrency) || !Number(draft.timeoutSeconds))) return "并发与超时必须大于 0";
  if (step === 3 && !draft.discoveredModels.length) return "请先发现或添加至少一个模型";
  return "";
}
