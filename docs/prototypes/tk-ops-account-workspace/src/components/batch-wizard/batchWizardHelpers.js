import { prototypeConfig } from "../../config/prototypeConfig.js";

export function createBatchForm(recipeId) {
  return { assetIds: [], count: 6, fixedScript: "", goal: "账号定位内容", mode: "topic", modelParams: {}, name: "", overrides: 0, recipeId, splitMode: "paragraph", useImageToVideo: false };
}

export function splitFixedScript(text, splitMode) {
  const source = String(text || "").trim();
  if (!source) return [];
  if (splitMode === "line") return source.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
  if (splitMode === "sentence") return source.split(/(?<=[。！？!?])\s*/).map((item) => item.trim()).filter(Boolean);
  return source.split(/\n\s*\n+/).map((item) => item.trim()).filter(Boolean);
}

export function getBatchAssets(workspace) {
  return (workspace.library || []).filter((item) => ["素材", "成片", "Video"].includes(item.kind)).slice(0, 4).map((item) => ({ ...item, matchReason: item.kind === "素材" ? "可作为账号视觉参考" : "可提取镜头与构图参考" }));
}

export function resolveRecipeContext(recipe, aiSettings) {
  const route = aiSettings?.routes.find((item) => item.id === recipe.videoCapability) || null;
  const status = route ? aiSettings.routeStatuses[route.id] : { ready: false, reason: "缺少能力路由" };
  const model = aiSettings?.models.find((item) => item.id === route?.primaryModelProfileId) || null;
  return { model, route, status };
}

export function normalizeModelParams(model, current = {}) {
  const schema = model?.parameterSchema || {};
  return {
    duration: current.duration || schema.durations?.[0] || "自动",
    ratio: current.ratio || schema.ratios?.[0] || "9:16",
    resolution: current.resolution || schema.resolutions?.[0] || "自动",
  };
}

export function validateBatchSource(form, assets) {
  if (form.mode === "script" && !form.fixedScript.trim()) return "请粘贴固定脚本";
  if (form.mode === "script" && !splitFixedScript(form.fixedScript, form.splitMode).length) return "当前拆分规则没有得到可用脚本";
  if (form.mode === "assets" && !form.assetIds.length) return assets.length ? "请选择至少一项账号素材" : "当前账号没有可用素材，请先导入内容库";
  return "";
}

export function getSplitModeLabel(splitMode) {
  return prototypeConfig.production.scriptSplitModes.find((item) => item.id === splitMode)?.label || "按段落拆分";
}
