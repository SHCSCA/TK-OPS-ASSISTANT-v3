export const assetTypeOptions = [
  { label: "全部", value: "all" },
  { label: "视频", value: "video" },
  { label: "图片", value: "image" },
  { label: "音频", value: "audio" },
  { label: "文档", value: "document" },
];

export const assetPurposeOptions = ["成片", "创作素材", "脚本", "字幕", "模板"];
export const assetSourceOptions = ["本地导入", "AI 生产", "视频拆解", "媒体工具"];
export const assetStatusOptions = ["ready", "running", "missing", "failed"];

export const accountAssets = {
  mirror: [
    createAsset({ id: "m-a1", accountId: "mirror", type: "video", purpose: "成片", source: "AI 生产", title: "三步整理混乱提示词 · v3", version: "v3", status: "ready", contentItemId: "m-c1", batchId: "m-b1", batchEntryId: "m-be1", metadata: { duration: "00:42", resolution: "1080 × 1920", format: "MP4" } }),
    createAsset({ id: "m-a2", accountId: "mirror", type: "audio", purpose: "创作素材", source: "AI 生产", title: "三步整理口播", version: "v2", status: "ready", contentItemId: "m-c1", batchId: "m-b1", batchEntryId: "m-be1", metadata: { duration: "00:38", format: "WAV" } }),
    createAsset({ id: "m-a3", accountId: "mirror", type: "document", subtype: "script", purpose: "脚本", source: "AI 生产", title: "三步整理混乱提示词 · 脚本 v3", version: "v3", status: "ready", contentItemId: "m-c1", metadata: { documentType: "脚本", format: "Markdown" } }),
    createAsset({ id: "m-a4", accountId: "mirror", type: "document", subtype: "template", purpose: "模板", source: "本地导入", title: "清晰口播结构", version: "v4", status: "ready", metadata: { documentType: "结构模板", format: "JSON" } }),
    createAsset({ id: "m-a5", accountId: "mirror", type: "image", purpose: "创作素材", source: "视频拆解", title: "结果前置参考帧", version: "00:02", status: "ready", sourceTaskId: "m-d1", metadata: { dimensions: "1080 × 1920", format: "PNG", previewState: "not-generated" } }),
    createAsset({ id: "m-a6", accountId: "mirror", type: "video", purpose: "创作素材", source: "本地导入", title: "桌面端录屏素材", version: "原始文件", status: "missing", metadata: { duration: "--:--", resolution: "未知", format: "MOV" } }),
    createAsset({ id: "m-a7", accountId: "mirror", type: "document", subtype: "transcript", purpose: "脚本", source: "视频拆解", title: "benchmark-01 · 转写", version: "v1", status: "ready", sourceTaskId: "m-d1", metadata: { documentType: "时间码转写", format: "JSON" } }),
  ],
  focus: [
    createAsset({ id: "f-a1", accountId: "focus", type: "video", purpose: "成片", source: "AI 生产", title: "Calmer file naming in three rules", version: "v1", status: "ready", contentItemId: "f-c3", batchId: "f-b1", batchEntryId: "f-be1", metadata: { duration: "00:38", resolution: "1080 × 1920", format: "MP4" } }),
    createAsset({ id: "f-a2", accountId: "focus", type: "document", subtype: "template", purpose: "模板", source: "本地导入", title: "Quiet workflow template", version: "v2", status: "ready", metadata: { documentType: "Structure template", format: "JSON" } }),
  ],
};

export function cloneAccountAssets() {
  return structuredClone(accountAssets);
}

export function filterAssets(assets, filters) {
  const query = String(filters.query || "").trim().toLocaleLowerCase();
  return assets.filter((asset) => {
    if (filters.type && filters.type !== "all" && asset.type !== filters.type) return false;
    if (filters.purpose && asset.purpose !== filters.purpose) return false;
    if (filters.source && asset.source !== filters.source) return false;
    if (filters.status && asset.status !== filters.status) return false;
    if (query && !`${asset.title} ${asset.purpose} ${asset.source} ${asset.tags.join(" ")}`.toLocaleLowerCase().includes(query)) return false;
    return true;
  });
}

export function normalizeMediaOutput(item, accountId) {
  const kind = item.kind || "视频";
  const type = kind === "音频" ? "audio" : kind === "图片" || kind === "素材" ? "image" : kind === "文档" ? "document" : "video";
  return createAsset({
    accountId,
    id: item.id,
    metadata: item.metadata || { format: type === "image" ? "PNG" : "MP4" },
    purpose: type === "video" ? "成片" : "创作素材",
    source: "媒体工具",
    sourceTaskId: item.taskId,
    status: item.status === "ready" ? "ready" : item.status,
    title: item.title,
    type,
    version: item.version || "工具输出",
  });
}

function createAsset({ id, accountId, type, subtype = null, purpose, source, title, version, status, metadata, contentItemId = null, batchId = null, batchEntryId = null, sourceTaskId = null, tags = [] }) {
  return {
    accountId,
    batchEntryId,
    batchId,
    contentItemId,
    demo: true,
    filePath: status === "missing" ? null : `演示工作区/${type}/${title}`,
    id,
    metadata,
    mime: mimeFor(type, metadata?.format),
    previewUrl: null,
    purpose,
    source,
    sourceTaskId,
    status,
    subtype,
    tags,
    title,
    type,
    updatedAt: "刚刚",
    version,
  };
}

function mimeFor(type, format) {
  const normalized = String(format || "").toLowerCase();
  if (type === "video") return `video/${normalized === "mov" ? "quicktime" : "mp4"}`;
  if (type === "image") return `image/${normalized || "png"}`;
  if (type === "audio") return `audio/${normalized || "wav"}`;
  return "text/plain";
}
