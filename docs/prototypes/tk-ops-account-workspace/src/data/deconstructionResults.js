export const accountDeconstructionWorkflows = {
  mirror: {
    selectedDeconstructionId: "m-d1",
    deconstructions: [
      {
        id: "m-d1",
        accountId: "mirror",
        title: "对标口播 · 三段式讲解",
        source: "本地文件 · benchmark-01.mp4",
        status: "completed",
        currentStage: "confirmation",
        appliedTargets: ["knowledge"],
        demo: true,
        stages: buildStages("confirmation"),
        result: {
          scriptSegments: [
            { id: "m-seg-1", start: "00:00", end: "00:04", text: "提示词越堆越长，通常不是信息不够，而是结构失控。", role: "Hook", confidence: "高" },
            { id: "m-seg-2", start: "00:05", end: "00:18", text: "先写目标，再把约束拆成格式、语气和禁区。", role: "方法", confidence: "高" },
            { id: "m-seg-3", start: "00:19", end: "00:31", text: "最后放入一个能直接验证结果的例子。", role: "证据", confidence: "高" },
            { id: "m-seg-4", start: "00:32", end: "00:36", text: "先整理结构，再继续加内容。", role: "CTA", confidence: "中" },
          ],
          keywords: [
            { id: "m-key-1", group: "主题", label: "提示词整理", weight: 0.94, hits: 2, evidence: ["00:01", "00:33"] },
            { id: "m-key-2", group: "人物 / 对象", label: "目标与约束", weight: 0.88, hits: 2, evidence: ["00:07", "00:12"] },
            { id: "m-key-3", group: "视觉元素", label: "前后对比", weight: 0.82, hits: 2, evidence: ["00:20", "00:27"] },
            { id: "m-key-4", group: "动作", label: "拆分", weight: 0.79, hits: 1, evidence: ["00:09"] },
            { id: "m-key-5", group: "语气", label: "直接、教学", weight: 0.76, hits: 4, evidence: ["全段"] },
          ],
          keyframes: [
            { id: "m-frame-1", time: "00:02", label: "结果前置", note: "最终界面先出现，再进入方法拆解", reuse: "封面 / 分镜参考", imageRef: null },
            { id: "m-frame-2", time: "00:09", label: "步骤切换", note: "字段高亮承接目标与约束", reuse: "分镜参考", imageRef: null },
            { id: "m-frame-3", time: "00:24", label: "对比验证", note: "前后状态并置验证结果", reuse: "图片资产", imageRef: null },
          ],
          structureSummary: {
            description: "前 4 秒先暴露问题并给出结果预期，随后用目标、约束和实例完成教学闭环。",
            duration: "36 秒",
            narrativeType: "结果前置教学",
            tags: ["结果前置", "步骤教学", "证据闭环", "短 CTA", "快节奏口播"],
          },
          structureSegments: [
            { id: "m-struct-1", label: "Hook", start: "00:00", end: "00:04", percent: 11, purpose: "先暴露问题并承诺结构化结果", copy: "提示词越堆越长，通常不是信息不够，而是结构失控。", evidenceKeywords: ["提示词整理"], evidenceIds: ["m-seg-1", "m-key-1"] },
            { id: "m-struct-2", label: "方法", start: "00:05", end: "00:18", percent: 39, purpose: "拆成目标与约束两个动作", copy: "先写目标，再把约束拆成格式、语气和禁区。", evidenceKeywords: ["目标与约束", "拆分"], evidenceIds: ["m-seg-2", "m-key-2"] },
            { id: "m-struct-3", label: "证据", start: "00:19", end: "00:31", percent: 36, purpose: "使用前后对比验证方法", copy: "最后放入一个能直接验证结果的例子。", evidenceKeywords: ["前后对比"], evidenceIds: ["m-seg-3", "m-key-3"] },
            { id: "m-struct-4", label: "CTA", start: "00:32", end: "00:36", percent: 14, purpose: "收束为一个可执行动作", copy: "先整理结构，再继续加内容。", evidenceKeywords: ["直接、教学"], evidenceIds: ["m-seg-4", "m-key-5"] },
          ],
        },
      },
      {
        id: "m-d2",
        accountId: "mirror",
        title: "产品操作录屏 · 待恢复",
        source: "已授权链接 · 演示来源",
        status: "failed",
        currentStage: "analysis",
        failureType: "provider",
        error: "转写 Provider 暂不可用，媒体文件与识别结果已保留。",
        appliedTargets: [],
        demo: true,
        stages: buildStages("analysis", "analysis"),
        result: emptyResult(),
      },
    ],
  },
  focus: {
    selectedDeconstructionId: "f-d1",
    deconstructions: [
      {
        id: "f-d1",
        accountId: "focus",
        title: "Quiet desk reference",
        source: "Local file · quiet-desk.mov",
        status: "failed",
        currentStage: "metadata",
        failureType: "ffprobe",
        error: "FFprobe is unavailable. Choose a local executable and retry.",
        appliedTargets: [],
        demo: true,
        stages: buildStages("metadata", "metadata"),
        result: emptyResult(),
      },
    ],
  },
};

export function cloneDeconstructionWorkflows() {
  return structuredClone(accountDeconstructionWorkflows);
}

export function markDeconstructionApplied(workflow, deconstructionId, target) {
  return {
    ...workflow,
    deconstructions: workflow.deconstructions.map((item) => item.id === deconstructionId
      ? { ...item, appliedTargets: [...new Set([...item.appliedTargets, target])] }
      : item),
  };
}

export function buildDeconstructionTopic(item, selection, accountId, id) {
  const structure = item.result.structureSegments.find((segment) => selection.structureIds?.includes(segment.id));
  const keywords = item.result.keywords.filter((keyword) => selection.keywordIds?.includes(keyword.id));
  return {
    accountId,
    angle: structure?.purpose || "复用拆解结构生成新角度",
    id,
    pillar: "工具拆解",
    sourceLabel: `${item.title} · ${structure?.start || "00:00"}–${structure?.end || "00:36"}`,
    sourceType: "deconstruction",
    tags: keywords.map((keyword) => keyword.label),
    targetDuration: 45,
    title: keywords[0] ? `${keywords[0].label}的三段式讲解` : `${item.title} · 新选题`,
  };
}

function buildStages(activeStage, failedStage = null) {
  const stages = [
    { id: "metadata", label: "媒体识别" },
    { id: "analysis", label: "分析与转写" },
    { id: "segmentation", label: "镜头切分" },
    { id: "structure", label: "结构提取" },
    { id: "confirmation", label: "确认回流" },
  ];
  const activeIndex = stages.findIndex((stage) => stage.id === activeStage);
  return stages.map((stage, index) => ({ ...stage, status: stage.id === failedStage ? "failed" : index < activeIndex ? "completed" : index === activeIndex ? "active" : "queued" }));
}

function emptyResult() {
  return { keyframes: [], keywords: [], scriptSegments: [], structureSegments: [], structureSummary: null };
}
