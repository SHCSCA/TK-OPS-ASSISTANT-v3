export const compositionTemplates = [
  { id: "template-static", name: "静态摘录", templateType: "static", aspectRatio: "9:16", parameterSummary: "强调色 · 字幕位置", previewAssetId: null, compatibleAbilities: ["text-generation"], version: 1, enabled: true },
  { id: "template-image", name: "清晰讲解", templateType: "image", aspectRatio: "9:16", parameterSummary: "背景 · 强调色 · 字幕", previewAssetId: null, compatibleAbilities: ["text-to-image"], version: 3, enabled: true },
  { id: "template-video", name: "动态工具演示", templateType: "video", aspectRatio: "9:16", parameterSummary: "安全区 · 转场 · 字幕", previewAssetId: null, compatibleAbilities: ["text-to-video", "image-to-video"], version: 2, enabled: true },
];

export function cloneCompositionTemplates() {
  return structuredClone(compositionTemplates);
}
