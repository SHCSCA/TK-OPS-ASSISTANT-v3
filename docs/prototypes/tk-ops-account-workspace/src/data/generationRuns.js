const nodeBlueprints = [
  ["source", "主题 / 固定脚本", "输入解析"],
  ["script", "脚本", "GPT-5.4 mini"],
  ["storyboard", "分镜", "Storyboard JSON"],
  ["visual-plan", "视觉规划", "素材匹配与生成决策"],
  ["visual", "图片 / 视频", "Wan I2V"],
  ["tts", "TTS", "Voice Local"],
  ["subtitle", "字幕", "Whisper Align"],
  ["compose", "合成 / BGM", "FFmpeg Template"],
  ["preview", "预览 / 发布", "质量预检"],
];

export function buildGenerationSteps(mode = "topic", failedVisual = false) {
  return nodeBlueprints.map(([id, name, model], index) => {
    const skipScript = mode === "script" && id === "script";
    const status = skipScript ? "skipped" : failedVisual && id === "visual" ? "failed" : index < 4 ? "completed" : !failedVisual && id === "visual" ? "running" : "queued";
    return {
      id,
      name,
      model,
      status,
      progress: status === "completed" || status === "skipped" ? 100 : status === "running" ? 58 : 0,
      duration: status === "completed" ? `${18 + index * 7} 秒` : status === "failed" ? "2 分 14 秒" : "--",
      provider: id === "visual" ? "ComfyUI Local" : ["script", "storyboard", "visual-plan"].includes(id) ? "OpenAI Compatible" : "本机 Runtime",
      version: "演示 v1",
      attempts: status === "failed" ? 2 : 0,
      error: status === "failed" ? "图生视频任务超时，已保留脚本与分镜产物。" : null,
      logId: `DEMO-${id.toUpperCase()}-0719`,
      skipReason: skipScript ? "已使用固定脚本" : null,
      action: id === "visual-plan" ? "分析账号素材并决定复用、生成或补充" : null,
      itemCurrent: id === "visual-plan" ? 3 : null,
      itemTotal: id === "visual-plan" ? 8 : null,
    };
  });
}

export const initialGenerationRuns = {
  "m-b1": { batchId: "m-b1", mode: "topic", recipe: "清晰口播", knowledgeSnapshot: "镜头 A · 知识快照 v12", positioningVersion: "定位 v4", steps: buildGenerationSteps("topic", true) },
  "f-b1": { batchId: "f-b1", mode: "assets", recipe: "安静桌面", knowledgeSnapshot: "Focus Lab · Snapshot v6", positioningVersion: "Positioning v2", steps: buildGenerationSteps("assets", false) },
};

export function cloneGenerationRuns() {
  return structuredClone(initialGenerationRuns);
}
