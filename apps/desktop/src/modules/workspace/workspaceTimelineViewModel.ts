import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineTrackDto,
  WorkspaceTimelineTrackKind
} from "@/types/runtime";

export type TimelineClipJoinClass = "single" | "start" | "middle" | "end";

export type TimelineTrackVisualClass = "video" | "voice" | "bgm" | "subtitle";

export type TimelineRowHeightClass = "tall" | "medium" | "compact";

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
  clips: TimelineClipView[];
  track: WorkspaceTimelineTrackDto;
};

export function buildTimelineRows(tracks: WorkspaceTimelineTrackDto[], durationMs: number): TimelineRowView[] {
  return [...tracks]
    .sort((left, right) => left.orderIndex - right.orderIndex)
    .map((track) => {
      const clips = [...track.clips].sort((left, right) => left.startMs - right.startMs);

      return {
        id: track.id,
        name: track.name,
        kind: track.kind,
        orderIndex: track.orderIndex,
        locked: track.locked,
        muted: track.muted,
        heightClass: trackHeightClass(track.kind),
        visualClass: trackVisualClass(track.kind, track.name),
        clips: clips.map((clip, index) => {
          const leftPercent = safePercent(clip.startMs, durationMs);

          return {
            id: clip.id,
            trackId: clip.trackId,
            label: clip.label,
            leftPercent,
            widthPercent: clippedWidthPercent(clip.durationMs, durationMs, leftPercent),
            joinClass: clipJoinClass(clips, index),
            clip
          };
        }),
        track
      };
    });
}

export function computePlayheadPercent(positionMs: number, durationMs: number): number {
  return safePercent(positionMs, durationMs);
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
