import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";

import {
  cleanWorkspaceText,
  formatWorkspaceClipRange,
  formatWorkspaceTime,
  workspaceSourceTypeLabel,
  workspaceStatusLabel,
  workspaceTrackKindLabel
} from "./workspaceTimelineViewModel";

export type WorkspacePreviewContextKind = "empty" | "video" | "audio" | "subtitle";

export type WorkspacePreviewContext = {
  captionText: string;
  clip: WorkspaceTimelineClipDto | null;
  currentTimeLabel: string;
  description: string;
  detailText: string;
  headline: string;
  kind: WorkspacePreviewContextKind;
  rangeLabel: string;
  sourceLabel: string;
  sourceType: string;
  statusLabel: string;
  summaryText: string;
  track: WorkspaceTimelineTrackDto | null;
};

type WorkspacePreviewContextInput = {
  playheadMs: number;
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

  if (!input.timeline) {
    return {
      captionText: "等待时间线草稿",
      clip: null,
      currentTimeLabel,
      description: "先创建空草稿，再把真实片段、音轨和字幕落到同一条时间线。",
      detailText: "时间线未创建",
      headline: "等待时间线草稿",
      kind: "empty",
      rangeLabel,
      sourceLabel,
      sourceType,
      statusLabel: "未创建草稿",
      summaryText: "暂无可展示片段",
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
      headline: input.selectedTrack?.name ?? "主播放器",
      kind: "empty",
      rangeLabel,
      sourceLabel,
      sourceType,
      statusLabel,
      summaryText: trackLabel,
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
      rangeLabel,
      sourceLabel,
      sourceType,
      statusLabel,
      summaryText: `音频状态：${sourceLabel}`,
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
      rangeLabel,
      sourceLabel,
      sourceType,
      statusLabel,
      summaryText: `字幕文本：${subtitleText}`,
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
    rangeLabel,
    sourceLabel,
    sourceType,
    statusLabel,
    summaryText: `画面来源：${sourceLabel}`,
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
