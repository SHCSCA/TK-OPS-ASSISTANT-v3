import {
  IconAspectRatio,
  IconDownload,
  IconFileMusic,
  IconPhotoScan,
  IconRefresh,
  IconSparkles,
} from "@tabler/icons-react";

export const mediaTools = [
  { id: "download", name: "视频下载", description: "保存公开、已获授权的视频来源", icon: IconDownload, rightsRequired: true, inputLabel: "公开链接" },
  { id: "watermark", name: "去水印", description: "处理自有或已获授权素材的水印区域", icon: IconSparkles, rightsRequired: true, inputLabel: "本地视频" },
  { id: "transcode", name: "转码与压缩", description: "统一格式、编码和目标体积", icon: IconRefresh, rightsRequired: false, inputLabel: "本地媒体" },
  { id: "audio", name: "提取音频", description: "导出 WAV、MP3 或无损音轨", icon: IconFileMusic, rightsRequired: false, inputLabel: "本地视频" },
  { id: "keyframes", name: "封面与关键帧", description: "按时间点提取封面候选", icon: IconPhotoScan, rightsRequired: false, inputLabel: "本地视频" },
  { id: "crop", name: "比例裁切", description: "输出 9:16、1:1 或 16:9 版本", icon: IconAspectRatio, rightsRequired: false, inputLabel: "本地视频" },
];

export const accountMediaTasks = {
  mirror: [
    { id: "m-tool-1", toolId: "keyframes", title: "benchmark-01.mp4", status: "completed", progress: 100, updated: "8 分钟前", output: "3 张关键帧", outputPath: "内容库 / 工具输出 / benchmark-01" },
    { id: "m-tool-2", toolId: "transcode", title: "screen-recording.mov", status: "running", progress: 62, updated: "刚刚", output: null, outputPath: null },
    { id: "m-tool-3", toolId: "audio", title: "voice-reference.mp4", status: "failed", progress: 24, updated: "15 分钟前", error: "音轨读取失败，源文件仍可用。", output: null, outputPath: null },
  ],
  focus: [
    { id: "f-tool-1", toolId: "crop", title: "quiet-desk.mov", status: "queued", progress: 0, updated: "Just now", output: null, outputPath: null },
  ],
};

export function cloneAccountMediaTasks() {
  return structuredClone(accountMediaTasks);
}

export function getMediaTool(toolId) {
  return mediaTools.find((tool) => tool.id === toolId) || null;
}

export function canStartMediaTask({ input, rightsConfirmed, toolId }) {
  const tool = getMediaTool(toolId);
  if (!tool || !String(input || "").trim()) return false;
  return !tool.rightsRequired || rightsConfirmed === true;
}

export function mediaTaskToLibraryItem(task) {
  if (task.status !== "completed") return null;
  const tool = getMediaTool(task.toolId);
  return {
    id: `library-${task.id}`,
    title: task.title,
    kind: task.toolId === "audio" ? "音频" : task.toolId === "keyframes" ? "素材" : "成片",
    source: `媒体工具箱 · ${tool?.name || "工具任务"}`,
    version: "工具输出",
    status: "ready",
  };
}
