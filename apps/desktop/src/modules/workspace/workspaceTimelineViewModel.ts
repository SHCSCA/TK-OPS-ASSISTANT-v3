import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineTrackDto,
  WorkspaceTimelineTrackKind
} from "@/types/runtime";

import { buildSnapCandidates, resolveTimelineSnap } from "./workspaceTimelineSnap";

export type TimelineClipJoinClass = "single" | "start" | "middle" | "end";

export type TimelineTrackVisualClass = "video" | "voice" | "bgm" | "subtitle";

export type TimelineRowHeightClass = "tall" | "medium" | "compact";
export type TimelineTrackSyncStatus = "empty" | "overflow" | "short" | "synced";

export type ManagedTrackSyncSummary = {
  managedCount: number;
  targetDurationMs: number;
  unsyncedCount: number;
  visible: boolean;
};

export type TimelineClipView = {
  id: string;
  trackId: string;
  label: string;
  leftPercent: number;
  widthPercent: number;
  joinClass: TimelineClipJoinClass;
  clip: WorkspaceTimelineClipDto;
};

export type TimelineRowView = {
  id: string;
  name: string;
  kind: WorkspaceTimelineTrackKind;
  orderIndex: number;
  locked: boolean;
  muted: boolean;
  heightClass: TimelineRowHeightClass;
  visualClass: TimelineTrackVisualClass;
  isManagedAITrack: boolean;
  syncEndPercent: number;
  syncGapLeftPercent: number;
  syncGapWidthPercent: number;
  syncTargetPercent: number;
  syncGapMs: number;
  syncLabel: string;
  syncStatus: TimelineTrackSyncStatus;
  clips: TimelineClipView[];
  track: WorkspaceTimelineTrackDto;
};

type TrackMetaInput = {
  id: string;
  kind: WorkspaceTimelineTrackKind;
  name: string;
  clipCount: number;
};

const STATUS_LABELS: Record<string, string> = {
  blocked: "已阻断",
  cancelled: "已取消",
  draft: "草稿",
  empty: "空态",
  error: "失败",
  failed: "失败",
  idle: "待加载",
  loading: "加载中",
  missing: "缺失",
  missing_source: "缺少来源",
  pending: "待处理",
  queued: "排队中",
  ready: "已就绪",
  running: "运行中",
  saving: "保存中",
  succeeded: "已完成"
};

export function buildTimelineRows(
  tracks: WorkspaceTimelineTrackDto[],
  viewportDurationMs: number,
  syncTargetDurationMs = viewportDurationMs
): TimelineRowView[] {
  return [...tracks]
    .sort((left, right) => left.orderIndex - right.orderIndex)
    .map((track) => {
      const clips = [...track.clips].sort((left, right) => left.startMs - right.startMs);
      const trackEndMs = clips.reduce((max, clip) => Math.max(max, clip.startMs + clip.durationMs), 0);
      const isManagedTrack = isManagedAITrack(track);
      const syncState = buildTrackSyncState(track, trackEndMs, syncTargetDurationMs, isManagedTrack);
      const syncEndPercent = safePercent(trackEndMs, viewportDurationMs);
      const syncTargetPercent = safePercent(syncTargetDurationMs, viewportDurationMs);
      const syncGapLeftPercent = safePercent(Math.min(trackEndMs, syncTargetDurationMs), viewportDurationMs);

      return {
        id: track.id,
        name: track.name,
        kind: track.kind,
        orderIndex: track.orderIndex,
        locked: track.locked,
        muted: track.muted,
        heightClass: trackHeightClass(track.kind),
        visualClass: trackVisualClass(track.kind, track.name),
        isManagedAITrack: isManagedTrack,
        syncEndPercent,
        syncGapLeftPercent,
        syncGapWidthPercent: clippedWidthPercent(Math.max(0, syncTargetDurationMs - trackEndMs), viewportDurationMs, syncGapLeftPercent),
        syncTargetPercent,
        syncGapMs: syncState.gapMs,
        syncLabel: syncState.label,
        syncStatus: syncState.status,
        clips: clips.map((clip, index) => {
          const leftPercent = safePercent(clip.startMs, viewportDurationMs);

          return {
            id: clip.id,
            trackId: clip.trackId,
            label: clip.label,
            leftPercent,
            widthPercent: clippedWidthPercent(clip.durationMs, viewportDurationMs, leftPercent),
            joinClass: clipJoinClass(clips, index),
            clip
          };
        }),
        track
      };
    });
}

export function summarizeManagedTrackSync(
  tracks: WorkspaceTimelineTrackDto[],
  fallbackDurationMs: number,
  targetDurationMs?: number
): ManagedTrackSyncSummary {
  const managedTracks = tracks.filter(isManagedAITrack);
  const managedTrackEnds = managedTracks.map(trackEndMs);
  const managedTargetDurationMs = managedTrackEnds.reduce((max, value) => Math.max(max, value), 0);
  const explicitTargetDurationMs = normalizeOptionalDuration(targetDurationMs);
  const resolvedTargetDurationMs = resolveManagedTargetDuration(
    managedTracks,
    managedTargetDurationMs,
    fallbackDurationMs,
    explicitTargetDurationMs
  );
  const rows = buildTimelineRows(
    tracks,
    Math.max(normalizeDuration(fallbackDurationMs), resolvedTargetDurationMs),
    resolvedTargetDurationMs
  );
  const managedRows = rows.filter((row) => row.isManagedAITrack);

  return {
    managedCount: managedRows.length,
    targetDurationMs: resolvedTargetDurationMs,
    unsyncedCount: managedRows.filter((row) => row.syncStatus !== "synced").length,
    visible: managedRows.length > 0
  };
}

function buildTrackSyncState(
  track: WorkspaceTimelineTrackDto,
  trackEndMs: number,
  durationMs: number,
  isManagedTrack = isManagedAITrack(track)
): { gapMs: number; label: string; status: TimelineTrackSyncStatus } {
  if (!isManagedTrack) {
    return { gapMs: 0, label: "手动轨道", status: "synced" };
  }

  if (track.clips.length === 0) {
    return { gapMs: durationMs, label: "待生成", status: "empty" };
  }

  const normalizedDuration = normalizeDuration(durationMs);
  const gapMs = Math.round(normalizedDuration - trackEndMs);
  if (Math.abs(gapMs) <= 250) {
    return { gapMs: 0, label: "统一结束", status: "synced" };
  }

  if (gapMs > 0) {
    return { gapMs, label: `需同步 ${formatWorkspaceTime(gapMs)}`, status: "short" };
  }

  return { gapMs, label: `超出 ${formatWorkspaceTime(Math.abs(gapMs))}`, status: "overflow" };
}

function isManagedAITrack(track: WorkspaceTimelineTrackDto): boolean {
  return track.id.startsWith("managed-");
}

function trackEndMs(track: WorkspaceTimelineTrackDto): number {
  return track.clips.reduce((max, clip) => Math.max(max, clip.startMs + clip.durationMs), 0);
}

export function computePlayheadPercent(positionMs: number, durationMs: number): number {
  return safePercent(positionMs, durationMs);
}

export function resolveSnapStartMs(
  clips: WorkspaceTimelineClipDto[],
  movingClipId: string,
  desiredStartMs: number,
  thresholdMs = 120
): number {
  return resolveTimelineSnap(
    desiredStartMs,
    buildSnapCandidates(clips, {
      movingClipId
    }),
    thresholdMs
  );
}

export function workspaceStatusLabel(status: string | null | undefined): string {
  if (!status) return "未选择";

  return STATUS_LABELS[status] ?? "未标注";
}

export function cleanWorkspaceText(value: string | null | undefined, fallback = "待确认"): string {
  const cleaned = stripContinuationPlaceholder(value);
  if (cleaned) return cleaned;

  return stripContinuationPlaceholder(fallback) || "待确认";
}

export function workspaceTrackMetaLabel(input: TrackMetaInput): string {
  const labels: string[] = [];
  const kindLabel = workspaceTrackKindLabel(input.kind);

  if (!trackNameContainsKind(input.name, kindLabel)) {
    labels.push(kindLabel);
  }

  labels.push(workspaceTrackPolicyLabel(input.id), `${input.clipCount} 个片段`);

  return labels.join(" · ");
}

export function workspaceTrackKindLabel(kind: WorkspaceTimelineTrackKind): string {
  if (kind === "audio") return "音频轨";
  if (kind === "subtitle") return "字幕轨";
  return "视频轨";
}

export function workspaceTrackPolicyLabel(trackId: string): string {
  return trackId.startsWith("managed-") ? "AI 受管轨道" : "手动轨道";
}

export function workspaceSourceTypeLabel(sourceType: string | null | undefined): string {
  if (sourceType === "asset") return "资产中心素材";
  if (sourceType === "storyboard") return "分镜占位";
  if (sourceType === "imported_video") return "视频拆解";
  if (sourceType === "voice_track") return "配音片段";
  if (sourceType === "subtitle_track") return "字幕片段";
  if (!sourceType) return "暂无媒体";
  return "手动片段";
}

export function formatWorkspaceTime(value: number): string {
  const totalSeconds = Math.max(0, Math.floor(value / 1000));
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");

  return `${minutes}:${seconds}`;
}

export function formatWorkspaceClipRange(startMs: number, durationMs: number): string {
  return `${formatWorkspaceTime(startMs)}-${formatWorkspaceTime(startMs + durationMs)}`;
}

export function trackVisualClass(kind: WorkspaceTimelineTrackKind, name: string): TimelineTrackVisualClass {
  if (kind === "subtitle") return "subtitle";
  if (kind === "video") return "video";

  const normalizedName = name.toLowerCase();

  if (normalizedName.includes("bgm") || normalizedName.includes("音乐") || normalizedName.includes("环境")) {
    return "bgm";
  }

  return "voice";
}

function trackNameContainsKind(name: string, kindLabel: string): boolean {
  const normalizedName = name.toLowerCase();

  if (normalizedName.includes(kindLabel.toLowerCase())) return true;
  if (/(轨|轨道)$/.test(name)) return true;
  if (normalizedName.includes("bgm")) return true;

  return false;
}

function stripContinuationPlaceholder(value: string | null | undefined): string {
  const normalized = (value ?? "").replace(/\s+/g, " ").trim();

  if (!normalized) return "";

  const withoutPlaceholder = normalized.replace(
    /[（(【\[]?\s*(?:延续(?:上(?:一)?句|上一段|上段|前文)?(?:口播|字幕|文案)?|沿用(?:上(?:一)?句|上一段|上段|前文)?(?:口播|字幕|文案)?|同上|same\s*as\s*above|continue\s*previous)\s*[）)】\]]?/gi,
    ""
  );

  if (withoutPlaceholder === normalized) return withoutPlaceholder.trim();

  return withoutPlaceholder
    .replace(/\s+/g, " ")
    .replace(/^[,，。.;；:：\-\s]+|[,，。.;；:：\-\s]+$/g, "")
    .trim();
}

function trackHeightClass(kind: WorkspaceTimelineTrackKind): TimelineRowHeightClass {
  if (kind === "video") return "tall";
  if (kind === "subtitle") return "compact";
  return "medium";
}

function clipJoinClass(clips: WorkspaceTimelineClipDto[], index: number): TimelineClipJoinClass {
  const clip = clips[index];
  const hasPrevious = index > 0 && clips[index - 1].startMs + clips[index - 1].durationMs === clip.startMs;
  const hasNext = index < clips.length - 1 && clip.startMs + clip.durationMs === clips[index + 1].startMs;

  if (hasPrevious && hasNext) return "middle";
  if (hasPrevious) return "end";
  if (hasNext) return "start";
  return "single";
}

function normalizeDuration(durationMs: number): number {
  if (!Number.isFinite(durationMs)) return 1000;

  return Math.max(1000, durationMs);
}

function normalizeOptionalDuration(durationMs: number | null | undefined): number | null {
  if (!Number.isFinite(durationMs) || (durationMs ?? 0) <= 0) return null;

  return normalizeDuration(durationMs as number);
}

function resolveManagedTargetDuration(
  managedTracks: WorkspaceTimelineTrackDto[],
  managedTargetDurationMs: number,
  fallbackDurationMs: number,
  explicitTargetDurationMs: number | null
): number {
  if (explicitTargetDurationMs !== null) {
    return explicitTargetDurationMs;
  }

  const commonGeneratedEndMs = resolveCommonGeneratedManagedEnd(managedTracks);

  if (commonGeneratedEndMs !== null) {
    return commonGeneratedEndMs;
  }

  return managedTargetDurationMs || normalizeDuration(fallbackDurationMs);
}

function resolveCommonGeneratedManagedEnd(managedTracks: WorkspaceTimelineTrackDto[]): number | null {
  const requiredKinds = new Set<WorkspaceTimelineTrackKind>(["video", "audio", "subtitle"]);
  const existingKinds = new Set(managedTracks.map((track) => track.kind));

  if ([...requiredKinds].some((kind) => !existingKinds.has(kind))) return null;
  if (managedTracks.some((track) => track.clips.length === 0)) return null;

  const [firstEnd, ...otherEnds] = managedTracks.map(trackEndMs);
  if (!firstEnd || !otherEnds.every((value) => Math.abs(value - firstEnd) <= 250)) return null;

  return firstEnd;
}

function safePercent(value: number, durationMs: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(durationMs)) return 0;

  const percent = (Math.max(0, value) / normalizeDuration(durationMs)) * 100;
  const clampedPercent = Math.min(100, Math.max(0, percent));

  return Number(clampedPercent.toFixed(3));
}

function clippedWidthPercent(durationMs: number, timelineDurationMs: number, leftPercent: number): number {
  const widthPercent = safePercent(durationMs, timelineDurationMs);
  const remainingPercent = Math.max(0, 100 - leftPercent);

  return Number(Math.min(widthPercent, remainingPercent).toFixed(3));
}
