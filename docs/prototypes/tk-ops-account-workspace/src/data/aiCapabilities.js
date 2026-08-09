export { providerProfiles, cloneProviderProfiles } from "./ai/providerProfiles.js";
export { modelProfiles, cloneModelProfiles } from "./ai/modelProfiles.js";
export { promptProfiles, clonePromptProfiles } from "./ai/promptProfiles.js";
export { capabilityRoutes, cloneCapabilityRoutes } from "./ai/capabilityRoutes.js";
export { compositionTemplates, cloneCompositionTemplates } from "./ai/compositionTemplates.js";

export const aiRecipes = [
  { id: "recipe-talk", name: "清晰口播", mode: "AI 主题", providerHealth: "ready", videoCapability: "text-to-video", summary: "脚本 + 快速图 + 短视频 + TTS" },
  { id: "recipe-image", name: "素材增强", mode: "已有素材", providerHealth: "warning", videoCapability: "image-to-video", summary: "参考图 + 图生视频 + 自动字幕" },
  { id: "recipe-calm", name: "安静桌面", mode: "固定脚本", providerHealth: "ready", videoCapability: "image-to-video", summary: "固定脚本 + 素材增强 + Calm Voice" },
];
