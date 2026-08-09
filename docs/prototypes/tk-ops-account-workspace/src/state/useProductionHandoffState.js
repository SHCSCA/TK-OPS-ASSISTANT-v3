import { useEffect, useMemo, useState } from "react";
import { prototypeConfig } from "../config/prototypeConfig.js";
import { createContentItem } from "../data/contentItems.js";
import { createProductionEntry, createSingleProductionBatch } from "../data/productionBatches.js";
import { prototypeLogger } from "../utils/logger.js";

const emptyHandoff = { batchId: "", mode: "single", name: "", open: false, submitting: false };

export function useProductionHandoffState({ activeAccountId, content, navigate, notify, updateActiveWorkflow, workflow }) {
  const [handoff, setHandoff] = useState(emptyHandoff);
  useEffect(() => setHandoff(emptyHandoff), [activeAccountId]);
  const selectedBatch = useMemo(
    () => workflow.batches.find((batch) => batch.id === workflow.selectedBatchId) || workflow.batches[0] || null,
    [workflow.batches, workflow.selectedBatchId],
  );
  const batchEntries = useMemo(
    () => workflow.entries.filter((entry) => entry.batchId === selectedBatch?.id),
    [selectedBatch?.id, workflow.entries],
  );
  const appendableBatches = useMemo(() => workflow.batches.filter((batch) => batch.appendable), [workflow.batches]);

  function openHandoff() {
    if (content.selectedStoryboard?.status !== "confirmed") {
      notify("请先确认当前分镜，再进入生产", "danger");
      return false;
    }
    setHandoff({ ...emptyHandoff, batchId: appendableBatches[0]?.id || "", name: `${content.selectedContentItem.title} · 单条生产`, open: true });
    return true;
  }

  function closeHandoff() {
    setHandoff(emptyHandoff);
  }

  function setHandoffField(field, value) {
    setHandoff((current) => ({ ...current, [field]: value }));
  }

  async function submitHandoff() {
    const item = content.selectedContentItem;
    const script = content.selectedScript;
    const storyboard = content.selectedStoryboard;
    if (!item || !script || storyboard?.status !== "confirmed") {
      notify("创作版本尚未准备好，无法进入生产", "danger");
      return false;
    }
    if (handoff.mode === "existing" && !handoff.batchId) {
      notify("请选择可接收内容的批次", "danger");
      return false;
    }
    try {
      setHandoff((current) => ({ ...current, submitting: true }));
      await delay();
      const now = Date.now();
      const scriptVersionId = `${script.id}-v${script.revision}`;
      const storyboardVersionId = `${storyboard.id}-v${storyboard.revision}`;
      let batch;
      let entry;
      if (handoff.mode === "existing") {
        batch = workflow.batches.find((candidate) => candidate.id === handoff.batchId);
        entry = createProductionEntry({ accountId: activeAccountId, batchId: batch.id, contentItem: item, entryId: `${activeAccountId}-entry-${now}`, scriptVersionId, storyboardVersionId });
      } else {
        const created = createSingleProductionBatch({ accountId: activeAccountId, batchId: `${activeAccountId}-batch-${now}`, contentItem: item, entryId: `${activeAccountId}-entry-${now}`, name: handoff.name || undefined, scriptVersionId, storyboardVersionId });
        batch = { ...created.batch, single: handoff.mode === "single" };
        entry = created.entry;
      }
      updateActiveWorkflow((current) => ({
        ...current,
        batches: handoff.mode === "existing"
          ? current.batches.map((candidate) => candidate.id === batch.id ? { ...candidate, items: candidate.items + 1, updated: "刚刚" } : candidate)
          : [batch, ...current.batches],
        contentItems: current.contentItems.map((candidate) => candidate.id === item.id ? { ...candidate, stage: "queued", productionReferences: [...candidate.productionReferences, { batchEntryId: entry.id, batchId: batch.id, status: "queued" }] } : candidate),
        entries: [entry, ...current.entries],
        selectedBatchId: batch.id,
      }));
      prototypeLogger.info("内容已进入生产", { accountId: activeAccountId, batchId: batch.id, contentItemId: item.id, mode: handoff.mode });
      closeHandoff();
      navigate("production");
      notify(handoff.mode === "existing" ? `已加入批次：${batch.name}` : handoff.mode === "single" ? "单条生产已创建，使用统一批次执行链" : `新批次 ${batch.name} 已创建`);
      return { batch, entry };
    } catch (error) {
      prototypeLogger.error("生产交接失败", { accountId: activeAccountId, error, mode: handoff.mode });
      setHandoff((current) => ({ ...current, submitting: false }));
      notify("进入生产失败，请重试并查看日志", "danger");
      return false;
    }
  }

  async function createGenericBatch(form) {
    try {
      await delay();
      const now = Date.now();
      const count = Math.max(1, Number(form.count) || 1);
      const batchId = `${activeAccountId}-batch-${now}`;
      const confirmedItems = form.mode === "confirmed" ? workflow.contentItems.filter((item) => item.adoptedScriptVersionId && item.confirmedStoryboardVersionId).slice(0, count) : [];
      if (form.mode === "confirmed" && !confirmedItems.length) {
        notify("当前账号没有已确认分镜的内容，请先完成创作链", "danger");
        return false;
      }
      const newItems = form.mode === "confirmed" ? [] : Array.from({ length: count }, (_, index) => {
        const fixedScript = form.mode === "script" ? form.scriptSegments?.[index] || "" : "";
        return {
          ...createContentItem({ accountId: activeAccountId, id: `${activeAccountId}-batch-content-${now}-${index}`, pillar: "待确认", sourceLabel: inputModeLabel(form.mode), sourceType: form.mode === "script" ? "imported_script" : form.mode === "asset" || form.mode === "assets" ? "existing_asset" : "ai_suggestion", targetDuration: 45, title: fixedScript ? `${form.name} · 脚本 ${String(index + 1).padStart(2, "0")}` : `${form.name} · 内容 ${String(index + 1).padStart(2, "0")}` }),
          importedScript: fixedScript || null,
          sourceAssetIds: form.mode === "assets" ? [...form.assetIds] : [],
        };
      });
      const items = form.mode === "confirmed" ? confirmedItems : newItems;
      const entries = items.map((item, index) => form.mode === "confirmed"
        ? createProductionEntry({ accountId: activeAccountId, batchId, contentItem: item, entryId: `${activeAccountId}-batch-entry-${now}-${index}`, scriptVersionId: item.adoptedScriptVersionId, storyboardVersionId: item.confirmedStoryboardVersionId })
        : { accountId: activeAccountId, batchId, blocker: form.mode === "script" ? "固定脚本已锁定，等待分镜确认" : form.mode === "assets" ? "素材已选定，等待视觉规划与脚本确认" : "等待选题与创作版本确认", contentItemId: item.id, contentItemReference: { contentItemId: item.id, knowledgeSnapshotId: `${activeAccountId}-knowledge-demo`, positioningVersionId: `${activeAccountId}-positioning-demo`, scriptVersionId: null, storyboardVersionId: null }, id: `${activeAccountId}-batch-entry-${now}-${index}`, inputSnapshot: { assetIds: item.sourceAssetIds, importedScript: item.importedScript, modelParams: form.modelParams || {} }, outputAssetIds: [], progress: 0, sourceMode: form.mode, stage: form.mode === "script" ? "脚本" : form.mode === "assets" ? "视觉规划" : "选题", status: "blocked", title: item.title, updatedAt: "刚刚", variantId: null });
      const initialStage = form.mode === "confirmed" ? "排队" : form.mode === "script" ? "脚本" : form.mode === "assets" ? "视觉规划" : "选题";
      const batch = { accountId: activeAccountId, appendable: true, id: batchId, inputSnapshot: { assetIds: form.assetIds || [], modelParams: form.modelParams || {}, splitMode: form.splitMode || null }, items: entries.length, name: form.name, progress: form.mode === "confirmed" ? 4 : 8, recipe: form.recipe || "账号默认配方", single: entries.length === 1, stage: initialStage, status: "running", updated: "刚刚" };
      updateActiveWorkflow((current) => ({ ...current, batches: [batch, ...current.batches], contentItems: newItems.length ? [...newItems, ...current.contentItems] : current.contentItems, entries: [...entries, ...current.entries], selectedBatchId: batch.id, selectedContentItemId: items[0].id }));
      prototypeLogger.info("演示批次已创建", { accountId: activeAccountId, batchId: batch.id, count });
      navigate("production");
      notify("批次已创建，队列项已关联独立创作对象");
      return { batch, entries, items };
    } catch (error) {
      prototypeLogger.error("创建演示批次失败", { accountId: activeAccountId, error });
      notify("批次创建失败，请检查后重试", "danger");
      return false;
    }
  }

  function selectBatch(batchId) {
    updateActiveWorkflow((current) => ({ ...current, selectedBatchId: batchId }));
  }

  function retryEntry(entryId) {
    try {
      updateActiveWorkflow((current) => ({ ...current, entries: current.entries.map((entry) => entry.id === entryId ? { ...entry, blocker: null, progress: Math.max(entry.progress, 12), status: "running", updatedAt: "刚刚" } : entry) }));
      prototypeLogger.info("批次队列项已重试", { accountId: activeAccountId, entryId });
      notify("队列项已从最小失败范围重新排队", "info");
    } catch (error) {
      prototypeLogger.error("重试批次队列项失败", { accountId: activeAccountId, entryId, error });
      notify("队列项重试失败，请查看日志", "danger");
    }
  }

  return {
    appendableBatches,
    batchEntries,
    batches: workflow.batches,
    closeHandoff,
    createGenericBatch,
    entries: workflow.entries,
    handoff,
    openHandoff,
    retryEntry,
    selectedBatch,
    selectBatch,
    setHandoffField,
    submitHandoff,
    variants: workflow.variants,
  };
}

function inputModeLabel(mode) {
  if (mode === "confirmed") return "已确认内容";
  if (mode === "script") return "固定脚本";
  if (mode === "asset" || mode === "assets") return "已有素材";
  return "AI 主题";
}

function delay() {
  return new Promise((resolve) => window.setTimeout(resolve, prototypeConfig.actionDelay));
}
