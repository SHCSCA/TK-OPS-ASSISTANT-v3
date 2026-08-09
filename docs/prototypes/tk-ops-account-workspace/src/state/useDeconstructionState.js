import { useEffect, useMemo, useState } from "react";
import { prototypeConfig } from "../config/prototypeConfig.js";
import { applyDeconstructionResult } from "../data/creativeWorkflow.js";
import { buildDeconstructionTopic } from "../data/deconstructionResults.js";
import { prototypeLogger } from "../utils/logger.js";

const emptyApply = { action: "topic", keyframeIds: [], keywordIds: [], open: false, scriptSegmentIds: [], structureIds: [], submitting: false, targetContentItemId: "" };

export function useDeconstructionState({ activeAccountId, content, navigate, notify, updateActiveWorkflow, workflow }) {
  const [applyDialog, setApplyDialog] = useState(emptyApply);
  const selectedDeconstruction = useMemo(
    () => workflow.deconstructions.find((item) => item.id === workflow.selectedDeconstructionId) || workflow.deconstructions[0] || null,
    [workflow.deconstructions, workflow.selectedDeconstructionId],
  );

  useEffect(() => setApplyDialog(emptyApply), [activeAccountId]);

  function selectDeconstruction(id) {
    updateActiveWorkflow((current) => ({ ...current, selectedDeconstructionId: id }));
  }

  function openApplyDialog(selection = {}) {
    const item = selectedDeconstruction;
    setApplyDialog({
      ...emptyApply,
      keywordIds: selection.keywordIds || item?.result.keywords.slice(0, 2).map((keyword) => keyword.id) || [],
      keyframeIds: selection.keyframeIds || item?.result.keyframes.filter((frame) => frame.imageRef).map((frame) => frame.id) || [],
      open: true,
      scriptSegmentIds: selection.scriptSegmentIds || item?.result.scriptSegments.map((segment) => segment.id) || [],
      structureIds: selection.structureIds || item?.result.structureSegments.slice(0, 1).map((segment) => segment.id) || [],
      targetContentItemId: content.selectedContentItem?.id || "",
    });
  }

  function closeApplyDialog() {
    setApplyDialog(emptyApply);
  }

  function setApplyField(field, value) {
    setApplyDialog((current) => ({ ...current, [field]: value }));
  }

  function toggleApplySelection(field, id) {
    setApplyDialog((current) => ({ ...current, [field]: current[field].includes(id) ? current[field].filter((item) => item !== id) : [...current[field], id] }));
  }

  async function submitApply() {
    const item = selectedDeconstruction;
    if (!item || item.status !== "completed") return false;
    try {
      setApplyDialog((current) => ({ ...current, submitting: true }));
      await delay();
      const target = applyDialog.action;
      if (target === "topic") {
        const draft = buildDeconstructionTopic(item, applyDialog, activeAccountId, `${activeAccountId}-content-${Date.now()}`);
        content.createContentItemFromDraft(draft);
      } else if (target === "script") {
        applyToScript(item);
        navigate("scripts");
      } else if (target === "storyboard") {
        applyToStoryboard(item);
        navigate("storyboard");
      } else if (target === "asset") {
        applyToAsset(item);
        navigate("library");
      }
      updateActiveWorkflow((current) => applyDeconstructionResult(current, item.id, target));
      prototypeLogger.info("拆解结果已应用", { accountId: activeAccountId, action: target, deconstructionId: item.id });
      closeApplyDialog();
      notify(applySuccessMessage(target));
      return true;
    } catch (error) {
      prototypeLogger.error("拆解结果应用失败", { accountId: activeAccountId, deconstructionId: item.id, error });
      setApplyDialog((current) => ({ ...current, submitting: false }));
      notify("拆解结果应用失败，请重试并查看日志", "danger");
      return false;
    }
  }

  async function retryDeconstruction(deconstructionId) {
    try {
      updateActiveWorkflow((current) => ({ ...current, deconstructions: current.deconstructions.map((item) => item.id === deconstructionId ? { ...item, error: null, status: "running", stages: item.stages.map((stage) => stage.status === "failed" ? { ...stage, status: "active" } : stage) } : item) }));
      notify("拆解任务已从失败阶段继续", "info");
      await delay();
      updateActiveWorkflow((current) => ({ ...current, deconstructions: current.deconstructions.map((item) => item.id === deconstructionId ? { ...item, currentStage: "confirmation", result: recoveryResult(), status: "completed", stages: item.stages.map((stage) => ({ ...stage, status: stage.id === "confirmation" ? "active" : "completed" })) } : item) }));
      notify("拆解任务已恢复并进入确认阶段");
      return true;
    } catch (error) {
      prototypeLogger.error("拆解任务重试失败", { accountId: activeAccountId, deconstructionId, error });
      notify("拆解任务重试失败，请查看日志", "danger");
      return false;
    }
  }

  function applyToScript(item) {
    const targetId = applyDialog.targetContentItemId || content.selectedContentItem?.id;
    const targetScript = workflow.scripts.find((script) => script.contentItemId === targetId);
    if (!targetScript) throw new Error("目标内容还没有脚本，请先创建脚本或改用新建选题");
    const selectedSegments = item.result.scriptSegments.filter((segment) => applyDialog.scriptSegmentIds.includes(segment.id));
    const raw = selectedSegments.map((segment) => `${segment.start}–${segment.end} ${segment.text}`).join("\n\n");
    const revision = targetScript.revision + 1;
    updateActiveWorkflow((current) => ({
      ...current,
      contentItems: current.contentItems.map((candidate) => candidate.id === targetId ? { ...candidate, stage: "script_draft", scriptVersionIds: [`${targetScript.id}-v${revision}`, ...candidate.scriptVersionIds] } : candidate),
      scripts: current.scripts.map((script) => script.id === targetScript.id ? { ...script, adoptedRevision: null, raw, revision, status: "draft", updated: "刚刚", versions: [{ id: `${script.id}-v${revision}`, label: `v${revision}`, source: `视频拆解 · ${item.title}`, status: "review", note: "默认新建版本" }, ...script.versions] } : script),
    }));
  }

  function applyToStoryboard(item) {
    const targetId = applyDialog.targetContentItemId || content.selectedContentItem?.id;
    const targetScript = workflow.scripts.find((script) => script.contentItemId === targetId && script.status === "adopted");
    if (!targetScript) throw new Error("目标内容没有已采用脚本");
    const segments = item.result.structureSegments.filter((segment) => applyDialog.structureIds.includes(segment.id));
    const structure = segments.length ? segments : item.result.structureSegments;
    const boardId = `${targetId}-board-deconstruction-${Date.now()}`;
    const board = { contentItemId: targetId, id: boardId, revision: 1, scenes: structure.map((segment, index) => ({ id: `${boardId}-sc${index + 1}`, order: index + 1, title: segment.label, duration: `${segment.start}–${segment.end}`, narration: segment.purpose, shot: "拆解结构参考 · 待补充真实素材", status: "ready" })), scriptId: targetScript.id, sourceScriptRevision: targetScript.revision, status: "review" };
    updateActiveWorkflow((current) => ({ ...current, contentItems: current.contentItems.map((candidate) => candidate.id === targetId ? { ...candidate, stage: "storyboard_draft", storyboardVersionIds: [`${boardId}-v1`, ...candidate.storyboardVersionIds] } : candidate), storyboards: [board, ...current.storyboards.filter((candidate) => candidate.contentItemId !== targetId)] }));
  }

  function applyToAsset(item) {
    const assetId = `${activeAccountId}-asset-${Date.now()}`;
    updateActiveWorkflow((current) => ({ ...current, assets: [{ accountId: activeAccountId, batchEntryId: null, batchId: null, contentItemId: null, demo: true, filePath: `演示工作区/document/${item.title}`, id: assetId, metadata: { documentType: "时间码转写", format: "JSON" }, mime: "application/json", previewUrl: null, purpose: "脚本", source: "视频拆解", sourceTaskId: item.id, status: "ready", subtype: "transcript", tags: item.result.keywords.filter((keyword) => applyDialog.keywordIds.includes(keyword.id)).map((keyword) => keyword.label), title: `${item.title} · 拆解记录`, type: "document", updatedAt: "刚刚", version: "v1" }, ...current.assets] }));
  }

  return {
    applyDialog,
    closeApplyDialog,
    deconstructions: workflow.deconstructions,
    openApplyDialog,
    retryDeconstruction,
    selectDeconstruction,
    selectedDeconstruction,
    setApplyField,
    submitApply,
    toggleApplySelection,
  };
}

function recoveryResult() {
  return {
    keyframes: [],
    keywords: [{ id: "recovery-key-1", group: "主题", label: "桌面工作流", weight: 0.84, hits: 2, evidence: ["00:03", "00:18"] }],
    scriptSegments: [{ id: "recovery-seg-1", start: "00:00", end: "00:05", text: "先展示完成后的桌面。", role: "Hook", confidence: "中" }, { id: "recovery-seg-2", start: "00:06", end: "00:20", text: "再拆解减少、聚焦和复位三个动作。", role: "方法", confidence: "中" }],
    structureSegments: [{ id: "recovery-struct-1", label: "Hook", start: "00:00", end: "00:05", percent: 25, purpose: "结果前置", copy: "先展示完成后的桌面。", evidenceKeywords: ["桌面工作流"], evidenceIds: ["recovery-seg-1"] }, { id: "recovery-struct-2", label: "方法", start: "00:06", end: "00:20", percent: 75, purpose: "步骤拆解", copy: "再拆解减少、聚焦和复位三个动作。", evidenceKeywords: ["桌面工作流"], evidenceIds: ["recovery-seg-2"] }],
    structureSummary: { description: "先给出完成状态，再用三个动作拆解安静桌面工作流。", duration: "20 秒", narrativeType: "结果前置教学", tags: ["结果前置", "步骤拆解", "安静节奏"] },
  };
}

function applySuccessMessage(target) {
  if (target === "topic") return "已创建新选题，并保留拆解证据";
  if (target === "script") return "已创建脚本新版本，不覆盖原版本";
  if (target === "storyboard") return "已创建分镜新版本，请逐镜确认";
  if (target === "asset") return "拆解记录已作为文档资产写入内容库";
  return "关键词与结构证据已写入当前账号知识库";
}

function delay() {
  return new Promise((resolve) => window.setTimeout(resolve, prototypeConfig.actionDelay));
}
