import { cloneAccountAssets } from "./assets.js";
import { cloneContentWorkflows } from "./contentItems.js";
import { cloneDeconstructionWorkflows, markDeconstructionApplied } from "./deconstructionResults.js";
import { cloneProductionWorkflows } from "./productionBatches.js";

export const creativeStageOrder = ["topic", "script", "storyboard", "production", "asset"];

export function cloneCreativeWorkflows() {
  const content = cloneContentWorkflows();
  const production = cloneProductionWorkflows();
  const deconstruction = cloneDeconstructionWorkflows();
  const assets = cloneAccountAssets();
  return Object.fromEntries(Object.keys(content).map((accountId) => [accountId, {
    ...content[accountId],
    ...deconstruction[accountId],
    assets: assets[accountId] || [],
    batches: production[accountId]?.batches || [],
    entries: production[accountId]?.entries || [],
    selectedBatchId: production[accountId]?.selectedBatchId || null,
    variants: production[accountId]?.variants || [],
  }]));
}

export function canEnterStoryboard(script) {
  return Boolean(script && script.status === "adopted" && script.adoptedRevision === script.revision);
}

export function canConfirmStoryboard(storyboard) {
  return Boolean(storyboard && storyboard.status !== "confirmed" && storyboard.scenes.length > 0 && storyboard.scenes.every((scene) => scene.status === "ready"));
}

export function hasStoryboardRevisionMismatch(script, storyboard) {
  return Boolean(script && storyboard && storyboard.sourceScriptRevision !== script.revision);
}

export function updateStoryboardScene(storyboard, sceneId, updater) {
  return { ...storyboard, scenes: storyboard.scenes.map((scene) => scene.id === sceneId ? updater(scene) : scene) };
}

export function applyDeconstructionResult(workflow, deconstructionId, target) {
  return markDeconstructionApplied(workflow, deconstructionId, target);
}

export function getCreativeStageStates(contentItem, script, storyboard, entries, assets) {
  const entry = entries.find((item) => item.contentItemId === contentItem?.id) || null;
  const outputAssets = assets.filter((asset) => asset.contentItemId === contentItem?.id && asset.purpose === "成片");
  return [
    { id: "topic", label: "选题", status: contentItem ? "confirmed" : "not_started" },
    { id: "script", label: "脚本", status: !script ? "not_started" : script.status === "adopted" ? "confirmed" : script.status === "running" ? "active" : "review" },
    { id: "storyboard", label: "分镜", status: !storyboard ? "not_started" : storyboard.scenes.some((scene) => scene.status === "failed") ? "blocked" : storyboard.status === "confirmed" ? "confirmed" : "review" },
    { id: "production", label: "生产", status: !entry ? "not_started" : entry.status === "failed" || entry.status === "blocked" ? "blocked" : entry.status === "completed" ? "confirmed" : entry.status === "review" ? "review" : "active" },
    { id: "asset", label: "成片", status: outputAssets.length ? "completed" : "not_started" },
  ];
}

export function buildGeneratedScript(contentItem, scriptId) {
  const title = contentItem.title;
  const angle = contentItem.topicBrief.angle || "把复杂问题拆成三个可验证动作";
  const raw = `开场：${title}，先展示最终结果。\n\n主体：${angle}。第一步明确目标，第二步拆解动作，第三步用结果验证。\n\n结尾：保存这套结构，下次直接复用。`;
  return {
    adoptedRevision: null,
    contentItemId: contentItem.id,
    id: scriptId,
    raw,
    revision: 1,
    sections: [
      { label: "钩子", value: `${title}，先展示最终结果。` },
      { label: "主体", value: `${angle}，并拆成三个可验证动作。` },
      { label: "收束", value: "保存这套结构，下次直接复用。" },
    ],
    status: "draft",
    title,
    updated: "刚刚",
    versions: [{ id: `${scriptId}-v1`, label: "v1", source: "选题生成", status: "review", note: "等待人工采用" }],
  };
}

export function buildGeneratedStoryboard(script, storyboardId) {
  return {
    contentItemId: script.contentItemId,
    id: storyboardId,
    revision: 1,
    scenes: [
      { id: `${storyboardId}-sc1`, order: 1, title: "结果画面", duration: "00:04", shot: "屏幕录制 · 结果前置", narration: script.sections[0]?.value || "先展示结果。", status: "ready" },
      { id: `${storyboardId}-sc2`, order: 2, title: "步骤拆解", duration: "00:12", shot: "操作近景 · 字段高亮", narration: script.sections[1]?.value || "拆解核心步骤。", status: "ready" },
      { id: `${storyboardId}-sc3`, order: 3, title: "结尾收束", duration: "00:06", shot: "静态结果 · 行动提示", narration: script.sections[2]?.value || "完成收束。", status: "ready" },
    ],
    scriptId: script.id,
    sourceScriptRevision: script.revision,
    status: "review",
  };
}
