import type {
  TimelinePreviewDto,
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackKind,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";
import { resolveRuntimeBaseUrl } from "@/app/runtime-endpoint";

import {
  cleanWorkspaceText,
  formatWorkspaceClipRange,
  formatWorkspaceTime,
  workspaceSourceTypeLabel,
  workspaceStatusLabel,
  workspaceTrackKindLabel
} from "./workspaceTimelineViewModel";

export type WorkspacePreviewContextKind = "empty" | "video" | "audio" | "subtitle";
export type WorkspacePreviewMediaKind = "video" | "audio";
export type WorkspacePreviewMode = "media" | "structure" | "unavailable";

export type WorkspacePreviewManifestTrackSummary = {
  clipCountLabel: string;
  durationLabel: string;
  id: string;
  kindLabel: string;
  name: string;
};

export type WorkspacePreviewManifestSummary = {
  summaryText: string;
  tracks: WorkspacePreviewManifestTrackSummary[];
};

type WorkspacePreviewManifestSummaryResult = {
  errorMessage: string | null;
  summary: WorkspacePreviewManifestSummary | null;
};

const RUNTIME_PREVIEW_MANIFEST_ERROR_MESSAGE = "Runtime 预览清单格式异常，请重新同步预览。";

export type WorkspacePreviewContext = {
  captionText: string;
  clip: WorkspaceTimelineClipDto | null;
  currentTimeLabel: string;
  description: string;
  detailText: string;
  headline: string;
  kind: WorkspacePreviewContextKind;
  manifestSummary: WorkspacePreviewManifestSummary | null;
  mediaInfoText: string | null;
  mediaKind: WorkspacePreviewMediaKind | null;
  mediaUrl: string | null;
  previewMode: WorkspacePreviewMode;
  rangeLabel: string;
  runtimePreviewErrorMessage: string | null;
  runtimePreviewUrl: string | null;
  sourceLabel: string;
  sourceType: string;
  statusLabel: string;
  summaryText: string;
  truthDescription: string;
  truthLabel: string;
  track: WorkspaceTimelineTrackDto | null;
};

type WorkspacePreviewContextInput = {
  playheadMs: number;
  timelinePreview: TimelinePreviewDto | null;
  timelinePreviewErrorMessage: string | null;
  selectedClip: WorkspaceTimelineClipDto | null;
  selectedTrack: WorkspaceTimelineTrackDto | null;
  timeline: WorkspaceTimelineDto | null;
};

export function buildWorkspacePreviewContext(input: WorkspacePreviewContextInput): WorkspacePreviewContext {
  const clip = input.selectedClip ?? resolvePlayheadClip(input);
  const track = clip ? findTrackById(input.timeline, clip.trackId) : input.selectedTrack;
  const sourceLabel = workspaceSourceTypeLabel(clip?.sourceType ?? null);
  const sourceType = clip?.sourceType ?? "none";
  const currentTimeLabel = `当前时间：${formatWorkspaceTime(input.playheadMs)}`;
  const rangeLabel = clip ? formatWorkspaceClipRange(clip.startMs, clip.durationMs) : "未命中片段";
  const statusLabel = workspaceStatusLabel(clip?.status ?? input.timeline?.status);
  const runtimePreviewUrl = resolveRuntimePreviewUrl(input.timelinePreview);
  const manifestSummaryResult = resolveRuntimePreviewManifestSummary(runtimePreviewUrl);
  const manifestSummary = manifestSummaryResult.summary;
  const previewErrorMessage = manifestSummaryResult.errorMessage ?? resolveTimelinePreviewErrorMessage(input);
  const media = resolveRuntimePreviewMedia(input.timelinePreview, clip);
  const mediaUrl = media.url;
  const mediaKind = media.kind;
  const previewMode: WorkspacePreviewMode = mediaUrl && mediaKind
    ? "media"
    : input.timelinePreview?.previewMode === "unavailable"
      ? "unavailable"
      : "structure";
  const mediaInfoText = previewMode === "media" ? formatRuntimePreviewMediaInfo(media) : null;
  const truthLabel = previewMode === "media" ? "素材预览" : "分镜预览";
  const truthDescription =
    previewMode === "media"
      ? "正在播放已导入的本地素材，可用播放器控件检查画面和声音。"
      : previewMode === "unavailable" && previewErrorMessage
        ? `媒体预览不可用：${previewErrorMessage} 可继续查看结构预览。`
      : runtimePreviewUrl
        ? "当前片段还没有可播放素材，先按分镜和字幕检查节奏。"
        : previewErrorMessage
          ? `Runtime 预览同步失败：${previewErrorMessage}`
        : "当前片段还没有可播放素材，先按时间线结构检查上下文。";

  if (!input.timeline) {
    return {
      captionText: "等待时间线草稿",
      clip: null,
      currentTimeLabel,
      description: "先创建空草稿，再把真实片段、音轨和字幕落到同一条时间线。",
      detailText: "时间线未创建",
      headline: "等待时间线草稿",
      kind: "empty",
      manifestSummary: null,
      mediaInfoText: null,
      mediaKind: null,
      mediaUrl: null,
      previewMode: "structure",
      rangeLabel,
      runtimePreviewErrorMessage: null,
      runtimePreviewUrl: null,
      sourceLabel,
      sourceType,
      statusLabel: "未创建草稿",
      summaryText: "暂无可展示片段",
      truthDescription: "创建时间线草稿后，可以在这里检查画面、字幕和节奏。",
      truthLabel: "分镜预览",
      track: null
    };
  }

  if (!clip) {
    const trackLabel = input.selectedTrack
      ? `${workspaceTrackKindLabel(input.selectedTrack.kind)} · ${input.selectedTrack.clips.length} 个片段`
      : "播放头未命中片段";

    return {
      captionText: trackLabel,
      clip: null,
      currentTimeLabel,
      description: input.selectedTrack
        ? `${input.selectedTrack.name} · ${trackLabel}`
        : "移动播放头或选择片段后查看具体上下文。",
      detailText: trackLabel,
      headline: input.selectedTrack?.name ?? "预览舞台",
      kind: "empty",
      manifestSummary,
      mediaInfoText: null,
      mediaKind: null,
      mediaUrl: null,
      previewMode: previewMode === "unavailable" ? "unavailable" : "structure",
      rangeLabel,
      runtimePreviewErrorMessage: previewErrorMessage,
      runtimePreviewUrl,
      sourceLabel,
      sourceType,
      statusLabel,
      summaryText: trackLabel,
      truthDescription: "移动播放头或选择片段后，可以查看对应画面和上下文。",
      truthLabel: "分镜预览",
      track: input.selectedTrack
    };
  }

  if (track?.kind === "audio") {
    return {
      captionText: "仅展示音频状态，不生成伪播放。",
      clip,
      currentTimeLabel,
      description: `${clip.label} · ${rangeLabel} · ${statusLabel}`,
      detailText: `当前片段：${clip.label}`,
      headline: clip.label,
      kind: "audio",
      manifestSummary,
      mediaInfoText,
      mediaKind,
      mediaUrl,
      previewMode,
      rangeLabel,
      runtimePreviewErrorMessage: previewErrorMessage,
      runtimePreviewUrl,
      sourceLabel,
      sourceType,
      statusLabel,
      summaryText: previewMode === "media" ? "音频素材可播放" : `音频状态：${sourceLabel}`,
      truthDescription,
      truthLabel,
      track
    };
  }

  if (track?.kind === "subtitle") {
    const subtitleText = cleanWorkspaceText(clip.metadata?.text, "待确认字幕");

    return {
      captionText: subtitleText,
      clip,
      currentTimeLabel,
      description: `${clip.label} · ${rangeLabel} · ${statusLabel}`,
      detailText: `当前片段：${clip.label}`,
      headline: clip.label,
      kind: "subtitle",
      manifestSummary,
      mediaInfoText: null,
      mediaKind: null,
      mediaUrl: null,
      previewMode: previewMode === "unavailable" ? "unavailable" : "structure",
      rangeLabel,
      runtimePreviewErrorMessage: previewErrorMessage,
      runtimePreviewUrl,
      sourceLabel,
      sourceType,
      statusLabel,
      summaryText: `字幕文本：${subtitleText}`,
      truthDescription: "字幕片段会跟随播放头显示文本和时间位置。",
      truthLabel: "分镜预览",
      track
    };
  }

  const visualText = cleanWorkspaceText(clip.metadata?.text, clip.metadata?.visualPrompt ?? "待确认画面");

  return {
    captionText: visualText,
    clip,
    currentTimeLabel,
    description: `${clip.label} · ${rangeLabel} · ${statusLabel}`,
    detailText: `当前片段：${clip.label}`,
    headline: clip.label,
    kind: "video",
    manifestSummary,
    mediaInfoText,
    mediaKind,
    mediaUrl,
    previewMode,
    rangeLabel,
    runtimePreviewErrorMessage: previewErrorMessage,
    runtimePreviewUrl,
    sourceLabel,
    sourceType,
    statusLabel,
    summaryText: `画面来源：${sourceLabel}`,
    truthDescription,
    truthLabel,
    track
  };
}

function resolvePlayheadClip(input: WorkspacePreviewContextInput): WorkspaceTimelineClipDto | null {
  if (!input.timeline) return null;

  const preferredTrack = input.selectedTrack;
  const preferredClip = preferredTrack ? findClipAtPlayhead([preferredTrack], input.playheadMs) : null;

  return preferredClip ?? findClipAtPlayhead(orderedTracks(input.timeline), input.playheadMs);
}

function findClipAtPlayhead(
  tracks: WorkspaceTimelineTrackDto[],
  playheadMs: number
): WorkspaceTimelineClipDto | null {
  const positionMs = Math.max(0, Math.round(Number.isFinite(playheadMs) ? playheadMs : 0));

  for (const track of tracks) {
    const clip = [...track.clips]
      .sort((left, right) => left.startMs - right.startMs)
      .find((candidate) => positionMs >= candidate.startMs && positionMs < candidate.startMs + candidate.durationMs);

    if (clip) return clip;
  }

  return null;
}

function findTrackById(
  timeline: WorkspaceTimelineDto | null,
  trackId: string
): WorkspaceTimelineTrackDto | null {
  return timeline?.tracks.find((track) => track.id === trackId) ?? null;
}

function orderedTracks(timeline: WorkspaceTimelineDto): WorkspaceTimelineTrackDto[] {
  return [...timeline.tracks].sort((left, right) => left.orderIndex - right.orderIndex);
}

function resolveRuntimePreviewUrl(timelinePreview: TimelinePreviewDto | null): string | null {
  if (
    timelinePreview?.previewMode
    && timelinePreview.previewMode !== "manifest"
    && timelinePreview.previewMode !== "unavailable"
  ) {
    return null;
  }
  const value = timelinePreview?.previewUrl;
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  return normalized.startsWith("data:application/json") ? normalized : null;
}

function resolveRuntimePreviewManifestSummary(runtimePreviewUrl: string | null): WorkspacePreviewManifestSummaryResult {
  if (!runtimePreviewUrl) {
    return {
      errorMessage: null,
      summary: null
    };
  }

  try {
    const manifest = parseRuntimeManifestDataUrl(runtimePreviewUrl);

    const rawTracks = Array.isArray(manifest.tracks) ? manifest.tracks : [];
    const tracks = rawTracks
      .map((track, index) => normalizeManifestTrackSummary(track, index))
      .filter((track): track is WorkspacePreviewManifestTrackSummary => Boolean(track))
      .slice(0, 3);
    const trackCount = readFiniteNumber(manifest.trackCount) ?? rawTracks.length;
    const clipCount = readFiniteNumber(manifest.clipCount) ?? sumTrackClipCount(rawTracks);
    const totalClipDurationMs = resolveManifestTimelineDurationMs(manifest, rawTracks);

    return {
      errorMessage: null,
      summary: {
        summaryText: `${trackCount} 条轨道 · ${clipCount} 个片段 · ${formatWorkspaceTime(totalClipDurationMs)}`,
        tracks
      }
    };
  } catch (error) {
    console.error("[workspace-preview] 解析 Runtime 预览清单失败", error);
    return {
      errorMessage: RUNTIME_PREVIEW_MANIFEST_ERROR_MESSAGE,
      summary: null
    };
  }
}

function parseRuntimeManifestDataUrl(runtimePreviewUrl: string): Record<string, unknown> {
  const separatorIndex = runtimePreviewUrl.indexOf(",");
  if (separatorIndex < 0) throw new Error("Runtime manifest data URL 缺少内容分隔符");

  const metadata = runtimePreviewUrl.slice(0, separatorIndex).toLowerCase();
  if (!metadata.startsWith("data:application/json")) throw new Error("Runtime manifest 不是 JSON data URL");

  const payload = runtimePreviewUrl.slice(separatorIndex + 1);
  const jsonText = metadata.includes(";base64") ? decodeBase64Utf8(payload) : decodeURIComponent(payload);
  const parsed = JSON.parse(jsonText);
  if (!isRecord(parsed)) throw new Error("Runtime manifest 根节点不是对象");
  return parsed;
}

function decodeBase64Utf8(payload: string): string {
  const binaryText = globalThis.atob?.(payload);
  if (typeof binaryText !== "string") throw new Error("当前环境不支持 base64 解码");

  const bytes = Uint8Array.from(binaryText, (char) => char.charCodeAt(0));
  return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
}

function normalizeManifestTrackSummary(
  value: unknown,
  index: number
): WorkspacePreviewManifestTrackSummary | null {
  if (!isRecord(value)) return null;

  const rawClips = Array.isArray(value.clips) ? value.clips : [];
  const kind = normalizeManifestTrackKind(readText(value.kind));
  const clipCount = readFiniteNumber(value.clipCount) ?? rawClips.length;
  const clipDurationMs = readFiniteNumber(value.clipDurationMs) ?? sumClipDuration(rawClips);

  return {
    clipCountLabel: `${clipCount} 个片段`,
    durationLabel: formatWorkspaceTime(clipDurationMs),
    id: readText(value.id) ?? `runtime-track-${index}`,
    kindLabel: workspaceTrackKindLabel(kind),
    name: readText(value.name) ?? "未命名轨道"
  };
}

function normalizeManifestTrackKind(value: string | null): WorkspaceTimelineTrackKind {
  if (value === "audio" || value === "subtitle" || value === "video") return value;
  return "video";
}

function sumTrackClipCount(tracks: unknown[]): number {
  return tracks.reduce((total, track) => {
    if (!isRecord(track)) return total;
    const rawClips = Array.isArray(track.clips) ? track.clips : [];
    return total + (readFiniteNumber(track.clipCount) ?? rawClips.length);
  }, 0);
}

function resolveManifestTimelineDurationMs(manifest: Record<string, unknown>, tracks: unknown[]): number {
  const clipEndMs = maxTrackClipEndMs(tracks);
  if (clipEndMs > 0) return clipEndMs;

  const trackDurationMs = maxTrackDurationMs(tracks);
  if (trackDurationMs > 0) return trackDurationMs;

  const manifestDurationMs = readFiniteNumber(manifest.totalClipDurationMs);
  if (manifestDurationMs !== null) return manifestDurationMs;

  const durationSeconds = readFiniteNumber(manifest.durationSeconds);
  if (durationSeconds !== null && durationSeconds > 0) return durationSeconds * 1000;

  return 0;
}

function maxTrackDurationMs(tracks: unknown[]): number {
  return tracks.reduce((max, track) => {
    if (!isRecord(track)) return max;
    return Math.max(max, readFiniteNumber(track.clipDurationMs) ?? 0);
  }, 0);
}

function maxTrackClipEndMs(tracks: unknown[]): number {
  return tracks.reduce((max, track) => {
    if (!isRecord(track)) return max;
    const rawClips = Array.isArray(track.clips) ? track.clips : [];
    return Math.max(max, maxClipEndMs(rawClips));
  }, 0);
}

function maxClipEndMs(clips: unknown[]): number {
  return clips.reduce((max, clip) => {
    if (!isRecord(clip)) return max;
    const startMs = readFiniteNumber(clip.startMs) ?? 0;
    const durationMs = readFiniteNumber(clip.durationMs) ?? 0;
    return Math.max(max, startMs + durationMs);
  }, 0);
}

function sumClipDuration(clips: unknown[]): number {
  return clips.reduce((total, clip) => {
    if (!isRecord(clip)) return total;
    return total + (readFiniteNumber(clip.durationMs) ?? 0);
  }, 0);
}

function readFiniteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.round(value)) : null;
}

function readText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function resolveRuntimePreviewMedia(
  timelinePreview: TimelinePreviewDto | null,
  clip: WorkspaceTimelineClipDto | null
): {
  durationMs: number | null;
  kind: WorkspacePreviewMediaKind | null;
  mimeType: string | null;
  url: string | null;
} {
  if (!timelinePreview || timelinePreview.previewMode !== "media") {
    return { durationMs: null, kind: null, mimeType: null, url: null };
  }

  if (!mediaSourceMatchesClip(timelinePreview.media?.source, clip)) {
    return { durationMs: null, kind: null, mimeType: null, url: null };
  }

  const kind = timelinePreview.media?.kind;
  if (kind !== "audio" && kind !== "video") {
    return { durationMs: null, kind: null, mimeType: null, url: null };
  }

  const rawUrl = timelinePreview.media?.url?.trim();
  if (!rawUrl) {
    return { durationMs: null, kind: null, mimeType: null, url: null };
  }

  const rawMimeType = timelinePreview.media?.mimeType;
  if (typeof rawMimeType !== "string" || !rawMimeType.trim()) {
    return { durationMs: null, kind: null, mimeType: null, url: null };
  }

  if (!Object.prototype.hasOwnProperty.call(timelinePreview.media, "durationMs")) {
    return { durationMs: null, kind: null, mimeType: null, url: null };
  }

  const rawDurationMs = timelinePreview.media?.durationMs;
  if (rawDurationMs !== null && (typeof rawDurationMs !== "number" || !Number.isFinite(rawDurationMs))) {
    return { durationMs: null, kind: null, mimeType: null, url: null };
  }

  return {
    durationMs: rawDurationMs === null ? null : Math.max(0, Math.round(rawDurationMs)),
    kind,
    mimeType: rawMimeType.trim(),
    url: resolveRuntimeMediaUrl(rawUrl)
  };
}

function mediaSourceMatchesClip(source: string | null | undefined, clip: WorkspaceTimelineClipDto | null): boolean {
  if (!clip || clip.sourceType !== "asset" || !clip.sourceId) return false;
  return source === `asset:${clip.sourceId}`;
}

function formatRuntimePreviewMediaInfo(media: {
  durationMs: number | null;
  mimeType: string | null;
}): string {
  const parts: string[] = [];
  if (media.mimeType) parts.push(`MIME：${media.mimeType}`);
  if (media.durationMs !== null) parts.push(`时长：${formatWorkspaceTime(media.durationMs)}`);
  return parts.length ? parts.join(" · ") : "媒体信息由 Runtime 校验";
}

function resolveRuntimeMediaUrl(rawUrl: string): string {
  if (/^(blob|data|https?):/i.test(rawUrl)) return rawUrl;
  return new URL(rawUrl, resolveRuntimeBaseUrl()).toString();
}

function resolveTimelinePreviewErrorMessage(input: WorkspacePreviewContextInput): string | null {
  if (input.timelinePreview?.error?.code === "preview.media_unavailable") return null;
  const contractMessage = input.timelinePreview?.error?.message;
  if (typeof contractMessage === "string" && contractMessage.trim()) return contractMessage.trim();
  return input.timelinePreviewErrorMessage;
}
