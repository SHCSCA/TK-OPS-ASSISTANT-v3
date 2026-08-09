const mirrorScript = `开场：提示词越堆越长，通常不是信息不够，而是结构失控。\n\n方法一：先写清目标，只保留一个最终交付物。\n方法二：把约束拆成格式、语气和禁区。\n方法三：用一个可验证的例子收尾。\n\n结尾：先整理结构，再继续加内容。`;

const focusScript = `Open with the finished desktop.\n\nRemove the second task list, keep one focus window, and close with a ten-minute weekly reset.`;

export const accountContentWorkflows = {
  mirror: {
    selectedContentItemId: "m-c4",
    selectedSceneId: "m-c4-sc1",
    contentItems: [
      createSeedItem({
        accountId: "mirror",
        id: "m-c1",
        title: "三步整理混乱提示词",
        pillar: "工具拆解",
        stage: "completed",
        adoptedScriptVersionId: "m-s1-v3",
        confirmedStoryboardVersionId: "m-board-1-v2",
        productionReferences: [{ batchId: "m-b1", batchEntryId: "m-be1", status: "completed" }],
        assetIds: ["m-a1", "m-a2", "m-a3"],
      }),
      createSeedItem({
        accountId: "mirror",
        id: "m-c2",
        title: "一周自动化复盘",
        pillar: "真实复盘",
        stage: "review",
        adoptedScriptVersionId: "m-s2-v2",
        confirmedStoryboardVersionId: "m-board-2-v1",
        productionReferences: [{ batchId: "m-b1", batchEntryId: "m-be2", status: "review" }],
      }),
      createSeedItem({
        accountId: "mirror",
        id: "m-c3",
        title: "桌面端批量生成流程",
        pillar: "效率实验",
        stage: "producing",
        adoptedScriptVersionId: "m-s3-v1",
        confirmedStoryboardVersionId: "m-board-3-v1",
        productionReferences: [{ batchId: "m-b1", batchEntryId: "m-be3", status: "running" }],
      }),
      createSeedItem({
        accountId: "mirror",
        id: "m-c4",
        title: "知识库为什么会串号",
        pillar: "工具拆解",
        stage: "storyboard_draft",
        adoptedScriptVersionId: "m-s4-v2",
      }),
    ],
    scripts: [
      createScript({ id: "m-s1", contentItemId: "m-c1", title: "三步整理混乱提示词", revision: 3, raw: mirrorScript, status: "adopted" }),
      createScript({ id: "m-s2", contentItemId: "m-c2", title: "一周自动化复盘", revision: 2, raw: "先展示一周结束后的复盘面板，再拆解收集、归类和回写三个自动化动作。", status: "adopted" }),
      createScript({ id: "m-s3", contentItemId: "m-c3", title: "桌面端批量生成流程", revision: 1, raw: "从三个已确认选题开始，展示脚本、分镜与生产队列如何保持同一对象。", status: "adopted" }),
      createScript({ id: "m-s4", contentItemId: "m-c4", title: "知识库为什么会串号", revision: 2, raw: "先展示账号切换后的错误引用，再解释账号范围、知识快照和缓存键三个边界。", status: "adopted" }),
    ],
    storyboards: [
      createStoryboard({ id: "m-board-1", contentItemId: "m-c1", scriptId: "m-s1", revision: 2, sourceScriptRevision: 3, status: "confirmed", scenes: mirrorScenes("m-c1") }),
      createStoryboard({ id: "m-board-2", contentItemId: "m-c2", scriptId: "m-s2", revision: 1, sourceScriptRevision: 2, status: "confirmed", scenes: compactScenes("m-c2", "复盘结果", "三个自动化动作", "保存复盘证据") }),
      createStoryboard({ id: "m-board-3", contentItemId: "m-c3", scriptId: "m-s3", revision: 1, sourceScriptRevision: 1, status: "confirmed", scenes: compactScenes("m-c3", "已确认内容", "批次队列", "输出归档") }),
      createStoryboard({ id: "m-board-4", contentItemId: "m-c4", scriptId: "m-s4", revision: 1, sourceScriptRevision: 2, status: "review", scenes: compactScenes("m-c4", "错误引用", "账号边界", "切换验证") }),
    ],
  },
  focus: {
    selectedContentItemId: "f-c1",
    selectedSceneId: null,
    contentItems: [
      createSeedItem({ accountId: "focus", id: "f-c1", title: "A 10-minute weekly desktop reset", pillar: "Weekly reset", stage: "script_draft" }),
      createSeedItem({ accountId: "focus", id: "f-c2", title: "One-screen deep work setup", pillar: "Deep work", stage: "topic_ready" }),
      createSeedItem({ accountId: "focus", id: "f-c3", title: "Calmer file naming in three rules", pillar: "Desk systems", stage: "completed", adoptedScriptVersionId: "f-s3-v1", confirmedStoryboardVersionId: "f-board-3-v1", productionReferences: [{ batchId: "f-b1", batchEntryId: "f-be1", status: "completed" }], assetIds: ["f-a1"] }),
    ],
    scripts: [
      createScript({ id: "f-s1", contentItemId: "f-c1", title: "A 10-minute weekly desktop reset", revision: 2, raw: focusScript, status: "draft" }),
      createScript({ id: "f-s3", contentItemId: "f-c3", title: "Calmer file naming in three rules", revision: 1, raw: "Show three calmer file naming rules and finish with one before-and-after folder.", status: "adopted" }),
    ],
    storyboards: [
      createStoryboard({ id: "f-board-3", contentItemId: "f-c3", scriptId: "f-s3", revision: 1, sourceScriptRevision: 1, status: "confirmed", scenes: compactScenes("f-c3", "Folder before", "Three rules", "Folder after") }),
    ],
  },
};

export const contentStageLabels = {
  blocked: "需要处理",
  completed: "已完成",
  producing: "生产中",
  queued: "已入批次",
  review: "待确认",
  script_adopted: "脚本已采用",
  script_draft: "脚本草稿",
  storyboard_confirmed: "分镜已确认",
  storyboard_draft: "分镜规划",
  topic_ready: "仅选题",
};

export function cloneContentWorkflows() {
  return structuredClone(accountContentWorkflows);
}

export function createContentItem({ accountId, id, title, pillar, audience = "继承账号定位", angle = "", targetDuration = 45, sourceType = "manual", sourceLabel = "手动创建", tags = [] }) {
  return createSeedItem({
    accountId,
    id,
    title,
    pillar,
    stage: "topic_ready",
    audience,
    angle,
    targetDuration,
    sourceReferences: [{ id: `${id}-source`, type: sourceType, label: sourceLabel }],
    tags,
  });
}

function createSeedItem({ accountId, id, title, pillar, stage, adoptedScriptVersionId = null, confirmedStoryboardVersionId = null, productionReferences = [], assetIds = [], audience = "当前账号目标受众", angle = "", targetDuration = 45, sourceReferences = [], tags = [] }) {
  return {
    accountId,
    adoptedScriptVersionId,
    assetIds,
    confirmedStoryboardVersionId,
    demo: true,
    id,
    productionReferences,
    sourceReferences,
    stage,
    storyboardVersionIds: confirmedStoryboardVersionId ? [confirmedStoryboardVersionId] : [],
    scriptVersionIds: adoptedScriptVersionId ? [adoptedScriptVersionId] : [],
    title,
    topicBrief: { angle, audience, pillar, sourceLabel: sourceReferences[0]?.label || "账号选题池", sourceType: sourceReferences[0]?.type || "ai_suggestion", tags, targetDuration, title },
    updatedAt: "刚刚",
  };
}

function createScript({ id, contentItemId, title, revision, raw, status }) {
  const labels = ["钩子", "主体", "收束"];
  const sentences = raw.split(/[。\n]+/).map((item) => item.trim()).filter(Boolean);
  return {
    adoptedRevision: status === "adopted" ? revision : null,
    contentItemId,
    id,
    raw,
    revision,
    sections: labels.map((label, index) => ({ label, value: sentences[index] || "等待补充" })),
    status,
    title,
    updated: "刚刚",
    versions: Array.from({ length: revision }, (_, index) => {
      const value = revision - index;
      return { id: `${id}-v${value}`, label: `v${value}`, note: value === revision ? "当前版本" : "历史版本", source: value === 1 ? "选题生成" : "人工与 AI 调整", status: value === revision && status === "adopted" ? "adopted" : value === revision ? "review" : "history" };
    }),
  };
}

function createStoryboard({ id, contentItemId, scriptId, revision, sourceScriptRevision, status, scenes }) {
  return { contentItemId, id, revision, scenes, scriptId, sourceScriptRevision, status };
}

function mirrorScenes(prefix) {
  return [
    { id: `${prefix}-sc1`, order: 1, title: "混乱提示词对比", duration: "00:04", shot: "桌面录屏 · 快速推近", narration: "提示词越堆越长，通常不是信息不够。", status: "ready" },
    { id: `${prefix}-sc2`, order: 2, title: "目标与约束拆分", duration: "00:12", shot: "左右对照 · 字段高亮", narration: "先写目标，再拆格式、语气和禁区。", status: "ready" },
    { id: `${prefix}-sc3`, order: 3, title: "示例验证", duration: "00:10", shot: "结果卡片 · 平稳停留", narration: "最后放入一个能直接检查的例子。", status: "ready" },
    { id: `${prefix}-sc4`, order: 4, title: "结尾收束", duration: "00:06", shot: "人物口播 · 轻微拉远", narration: "先整理结构，再继续加内容。", status: "ready" },
  ];
}

function compactScenes(prefix, first, second, third) {
  return [
    { id: `${prefix}-sc1`, order: 1, title: first, duration: "00:04", shot: "结果前置 · 近景", narration: first, status: "ready" },
    { id: `${prefix}-sc2`, order: 2, title: second, duration: "00:12", shot: "步骤拆解 · 中景", narration: second, status: "ready" },
    { id: `${prefix}-sc3`, order: 3, title: third, duration: "00:08", shot: "证据收束 · 定镜", narration: third, status: "ready" },
  ];
}
