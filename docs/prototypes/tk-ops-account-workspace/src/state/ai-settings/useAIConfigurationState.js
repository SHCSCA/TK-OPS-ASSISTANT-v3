import { useMemo, useState } from "react";
import { cloneCapabilityRoutes, cloneCompositionTemplates, cloneModelProfiles, clonePromptProfiles } from "../../data/aiCapabilities.js";
import { prototypeLogger } from "../../utils/logger.js";

export function useAIConfigurationState(notify) {
  const [models, setModels] = useState(cloneModelProfiles);
  const [routes, setRoutes] = useState(cloneCapabilityRoutes);
  const [prompts, setPrompts] = useState(clonePromptProfiles);
  const [templates] = useState(cloneCompositionTemplates);
  const [selectedModelId, setSelectedModelId] = useState(null);
  const [selectedPromptId, setSelectedPromptId] = useState("prompt-script-1");
  const [promptDraft, setPromptDraft] = useState(() => structuredClone(clonePromptProfiles()[0]));
  const [promptDirty, setPromptDirty] = useState(false);
  const [pendingPromptId, setPendingPromptId] = useState(null);
  const [promptGuardOpen, setPromptGuardOpen] = useState(false);
  const selectedModel = useMemo(() => models.find((model) => model.id === selectedModelId) || null, [models, selectedModelId]);
  const selectedPrompt = useMemo(() => prompts.find((prompt) => prompt.id === selectedPromptId) || null, [prompts, selectedPromptId]);
  const routeStatuses = useMemo(() => Object.fromEntries(routes.map((route) => [route.id, getRouteStatus(route, models, prompts)])), [models, prompts, routes]);
  const readyRouteCount = Object.values(routeStatuses).filter((status) => status.ready).length;

  function addModels(providerId, discoveredModels) {
    try {
      const next = discoveredModels.map((model) => ({
        ...model,
        id: model.id || `${providerId}-${Date.now()}`,
        providerProfileId: providerId,
      }));
      setModels((current) => [...next, ...current.filter((model) => !next.some((candidate) => candidate.id === model.id))]);
      return next.map((model) => model.id);
    } catch (error) {
      prototypeLogger.error("保存 Provider 模型失败", error, { providerId });
      notify("模型保存失败，请在模型页重试", "danger");
      return [];
    }
  }

  function toggleModel(modelId) {
    try {
      setModels((current) => current.map((model) => model.id === modelId ? { ...model, enabled: !model.enabled } : model));
      prototypeLogger.info("模型启用状态已更新", { modelId });
      notify("模型状态已更新，能力就绪度已刷新", "info");
    } catch (error) {
      prototypeLogger.error("更新模型状态失败", error, { modelId });
      notify("模型状态更新失败", "danger");
    }
  }

  function updateRoute(routeId, field, value) {
    try {
      setRoutes((current) => current.map((route) => route.id === routeId ? { ...route, [field]: value || null, source: "系统默认" } : route));
      prototypeLogger.info("能力路由已更新", { field, routeId });
      notify("能力路由已更新", "info");
    } catch (error) {
      prototypeLogger.error("能力路由更新失败", error, { routeId });
      notify("能力路由更新失败", "danger");
    }
  }

  function updatePromptDraft(field, value) {
    setPromptDraft((current) => ({ ...current, [field]: value }));
    setPromptDirty(true);
  }

  function requestPromptSelection(promptId) {
    if (promptId === selectedPromptId) return;
    if (promptDirty) {
      setPendingPromptId(promptId);
      setPromptGuardOpen(true);
      return;
    }
    selectPrompt(promptId);
  }

  function selectPrompt(promptId) {
    const prompt = prompts.find((item) => item.id === promptId);
    if (!prompt) return;
    setSelectedPromptId(promptId);
    setPromptDraft(structuredClone(prompt));
    setPromptDirty(false);
  }

  function createPrompt() {
    if (promptDirty) {
      setPendingPromptId("__create__");
      setPromptGuardOpen(true);
      return;
    }
    createPromptImmediately();
  }

  function createPromptImmediately() {
    const id = `prompt-draft-${Date.now()}`;
    const prompt = { id, name: "未命名 Prompt", capabilityId: "script-generate", systemPrompt: "", taskTemplate: "", variables: [], outputSchema: "", visualStylePrefix: "", safetyConstraints: "", version: 0, status: "draft", referencedBy: [] };
    setPrompts((current) => [prompt, ...current]);
    setSelectedPromptId(id);
    setPromptDraft(structuredClone(prompt));
    setPromptDirty(true);
  }

  function savePromptVersion() {
    const error = validatePrompt(promptDraft);
    if (error) {
      notify(error, "danger");
      return false;
    }
    try {
      const next = { ...promptDraft, version: Math.max(1, Number(promptDraft.version || 0) + 1), status: "active" };
      setPrompts((current) => current.map((prompt) => prompt.id === next.id ? next : prompt));
      setPromptDraft(next);
      setPromptDirty(false);
      prototypeLogger.info("Prompt 新版本已保存", { promptId: next.id, version: next.version });
      notify(`Prompt v${next.version} 已保存`);
      return true;
    } catch (saveError) {
      prototypeLogger.error("保存 Prompt 版本失败", saveError, { promptId: promptDraft.id });
      notify("Prompt 保存失败，请重试", "danger");
      return false;
    }
  }

  function resolvePromptGuard(action) {
    if (action === "cancel") {
      setPromptGuardOpen(false);
      setPendingPromptId(null);
      return;
    }
    if (action === "save" && !savePromptVersion()) return;
    const nextId = pendingPromptId;
    setPromptGuardOpen(false);
    setPendingPromptId(null);
    if (nextId === "__create__") createPromptImmediately();
    else if (nextId) selectPrompt(nextId);
  }

  return {
    addModels,
    createPrompt,
    models,
    pendingPromptId,
    promptDirty,
    promptDraft,
    promptGuardOpen,
    prompts,
    readyRouteCount,
    requestPromptSelection,
    resolvePromptGuard,
    routeStatuses,
    routes,
    savePromptVersion,
    selectedModel,
    selectedModelId,
    selectedPrompt,
    selectedPromptId,
    setSelectedModelId,
    templates,
    toggleModel,
    updatePromptDraft,
    updateRoute,
  };
}

export function getRouteStatus(route, models, prompts) {
  const model = models.find((item) => item.id === route.primaryModelProfileId);
  const prompt = prompts.find((item) => item.id === route.promptProfileId);
  const fallback = models.find((item) => item.id === route.fallbackModelProfileId);
  const requiredAbility = routeAbilityMap[route.id];
  if (!model) return { ready: false, reason: "缺少主模型" };
  if (!model.enabled) return { ready: false, reason: "主模型已停用" };
  if (!model.contractVerified) return { ready: false, reason: "模型契约未验证" };
  if (requiredAbility && !model.adapterAbilities.includes(requiredAbility)) return { ready: false, reason: "适配器能力不匹配" };
  if (!["tts"].includes(route.id) && !prompt) return { ready: false, reason: "缺少 Prompt" };
  if (prompt && prompt.status !== "active") return { ready: false, reason: "Prompt 尚未启用" };
  if (prompt && !isPromptCompatible(route.id, prompt.capabilityId)) return { ready: false, reason: "Prompt 能力不匹配" };
  if (fallback && (!fallback.enabled || !fallback.contractVerified || requiredAbility && !fallback.adapterAbilities.includes(requiredAbility))) return { ready: false, reason: "回退模型不兼容" };
  return { ready: true, reason: "就绪" };
}

function isPromptCompatible(routeId, promptCapabilityId) {
  const groups = {
    "topic-suggest": "script",
    "script-generate": "script",
    "script-improve": "script",
    storyboard: "storyboard",
    deconstruction: "deconstruction",
    "text-to-image": "visual",
    "text-to-video": "visual",
    "image-to-video": "visual",
  };
  const promptGroups = { "script-generate": "script", storyboard: "storyboard", deconstruction: "deconstruction", "text-to-image": "visual" };
  return groups[routeId] === promptGroups[promptCapabilityId];
}

const routeAbilityMap = {
  "topic-suggest": "text-generation",
  "script-generate": "text-generation",
  "script-improve": "text-generation",
  storyboard: "structured-output",
  deconstruction: "vision-analysis",
  transcription: "transcription",
  "text-to-image": "text-to-image",
  "text-to-video": "text-to-video",
  "image-to-video": "image-to-video",
  tts: "tts",
  subtitle: "subtitle-alignment",
  embedding: "embedding",
};

function validatePrompt(prompt) {
  if (!prompt.name.trim()) return "请输入 Prompt 名称";
  if (!prompt.systemPrompt.trim()) return "请填写系统提示词";
  if (!prompt.taskTemplate.trim()) return "请填写任务模板";
  if (!prompt.outputSchema.trim()) return "请填写输出 Schema";
  const variables = [...prompt.taskTemplate.matchAll(/\{\{\s*([\w-]+)\s*\}\}/g)].map((match) => match[1]);
  const missing = variables.filter((variable) => !prompt.variables.includes(variable));
  if (missing.length) return `缺少变量定义：${missing.join("、")}`;
  return "";
}
