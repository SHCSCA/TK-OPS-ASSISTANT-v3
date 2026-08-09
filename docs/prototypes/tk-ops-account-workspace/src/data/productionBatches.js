export const accountProductionWorkflows = {
  mirror: {
    selectedBatchId: "m-b1",
    batches: [
      { id: "m-b1", accountId: "mirror", name: "本周 AI 工具拆解", stage: "生成", progress: 68, status: "running", updated: "10 分钟前", items: 3, recipe: "清晰口播 v2", appendable: true },
      { id: "m-b2", accountId: "mirror", name: "效率实验系列", stage: "脚本", progress: 34, status: "running", updated: "1 小时前", items: 0, recipe: "桌面演示 v1", appendable: true },
      { id: "m-b3", accountId: "mirror", name: "复盘内容补充", stage: "待发布", progress: 100, status: "ready", updated: "昨天", items: 0, recipe: "清晰口播 v2", appendable: false },
    ],
    entries: [
      createSeedEntry({ id: "m-be1", batchId: "m-b1", contentItemId: "m-c1", scriptVersionId: "m-s1-v3", storyboardVersionId: "m-board-1-v2", title: "三步整理混乱提示词", sourceMode: "confirmed", stage: "合成", status: "completed", progress: 100, variantId: "m-v1", outputAssetIds: ["m-a1", "m-a2", "m-a3"] }),
      createSeedEntry({ id: "m-be2", batchId: "m-b1", contentItemId: "m-c2", scriptVersionId: "m-s2-v2", storyboardVersionId: "m-board-2-v1", title: "一周自动化复盘", sourceMode: "confirmed", stage: "待确认", status: "review", progress: 86, variantId: "m-v2", blocker: "镜头 04 低置信" }),
      createSeedEntry({ id: "m-be3", batchId: "m-b1", contentItemId: "m-c3", scriptVersionId: "m-s3-v1", storyboardVersionId: "m-board-3-v1", title: "桌面端批量生成流程", sourceMode: "confirmed", stage: "生成", status: "running", progress: 54 }),
    ],
    variants: [
      { id: "m-v1", batchEntryId: "m-be1", contentItemId: "m-c1", title: "三步整理混乱提示词", status: "completed", version: "v3", duration: "00:42", issue: null },
      { id: "m-v2", batchEntryId: "m-be2", contentItemId: "m-c2", title: "一周自动化复盘", status: "review", version: "v2", duration: "00:51", issue: "镜头 04 低置信" },
    ],
  },
  focus: {
    selectedBatchId: "f-b1",
    batches: [
      { id: "f-b1", accountId: "focus", name: "Quiet desktop routines", stage: "合成", progress: 84, status: "running", updated: "18 min ago", items: 1, recipe: "Quiet desk v1", appendable: true },
      { id: "f-b2", accountId: "focus", name: "Weekly reset scripts", stage: "分镜", progress: 46, status: "running", updated: "3 hours ago", items: 0, recipe: "Calm tutorial v2", appendable: true },
    ],
    entries: [
      createSeedEntry({ id: "f-be1", accountId: "focus", batchId: "f-b1", contentItemId: "f-c3", scriptVersionId: "f-s3-v1", storyboardVersionId: "f-board-3-v1", title: "Calmer file naming in three rules", sourceMode: "confirmed", stage: "合成", status: "completed", progress: 100, variantId: "f-v1", outputAssetIds: ["f-a1"] }),
    ],
    variants: [
      { id: "f-v1", batchEntryId: "f-be1", contentItemId: "f-c3", title: "Calmer file naming in three rules", status: "completed", version: "v1", duration: "00:38", issue: null },
    ],
  },
};

export function cloneProductionWorkflows() {
  return structuredClone(accountProductionWorkflows);
}

export function createProductionEntry({ accountId, batchId, contentItem, scriptVersionId, storyboardVersionId, entryId }) {
  return createSeedEntry({
    accountId,
    batchId,
    contentItemId: contentItem.id,
    id: entryId,
    progress: 0,
    scriptVersionId,
    sourceMode: "confirmed",
    stage: "排队",
    status: "queued",
    storyboardVersionId,
    title: contentItem.title,
  });
}

export function createSingleProductionBatch({ accountId, contentItem, scriptVersionId, storyboardVersionId, batchId, entryId, name }) {
  const batch = {
    accountId,
    appendable: true,
    id: batchId,
    items: 1,
    name: name || `${contentItem.title} · 单条生产`,
    progress: 4,
    recipe: "账号默认配方",
    single: true,
    stage: "排队",
    status: "running",
    updated: "刚刚",
  };
  return { batch, entry: createProductionEntry({ accountId, batchId, contentItem, scriptVersionId, storyboardVersionId, entryId }) };
}

export function getEntryReadiness(entry, contentItem, script, storyboard) {
  return {
    output: entry.outputAssetIds.length ? "已归档" : entry.status === "review" ? "待确认" : "尚未生成",
    production: entry.blocker || stageLabel(entry),
    script: script?.status === "adopted" ? `v${script.revision} 已采用` : script ? "待采用" : "缺失",
    storyboard: storyboard?.status === "confirmed" ? `v${storyboard.revision} 已确认` : storyboard?.scenes.some((scene) => scene.status === "failed") ? "存在异常" : storyboard ? "待确认" : "缺失",
    topic: contentItem ? "已就绪" : "缺失",
  };
}

function createSeedEntry({ id, accountId = "mirror", batchId, contentItemId, scriptVersionId, storyboardVersionId, title, sourceMode, stage, status, progress, variantId = null, blocker = null, outputAssetIds = [] }) {
  return {
    accountId,
    batchId,
    blocker,
    contentItemId,
    contentItemReference: { contentItemId, knowledgeSnapshotId: `${accountId}-knowledge-demo`, positioningVersionId: `${accountId}-positioning-demo`, scriptVersionId, storyboardVersionId },
    id,
    outputAssetIds,
    progress,
    sourceMode,
    stage,
    status,
    title,
    updatedAt: "刚刚",
    variantId,
  };
}

function stageLabel(entry) {
  if (entry.status === "completed") return "已完成";
  if (entry.status === "running") return `${entry.stage} ${entry.progress}%`;
  if (entry.status === "review") return "待确认";
  if (entry.status === "failed") return "失败";
  return "排队中";
}
