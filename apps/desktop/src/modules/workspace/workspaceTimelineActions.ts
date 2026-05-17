import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";

export type WorkspaceTimelineActionState = {
  canMoveLeft: boolean;
  canMoveRight: boolean;
  canTrim: boolean;
  canSplit: boolean;
  reason: string;
};

export type WorkspaceTimelineActionInput = {
  minDurationMs?: number;
  playheadMs: number;
  selectedClipId: string | null;
  stepMs?: number;
  timeline: WorkspaceTimelineDto | null;
};

const DEFAULT_STEP_MS = 500;
const DEFAULT_MIN_DURATION_MS = 500;

export function evaluateTimelineClipActions(input: WorkspaceTimelineActionInput): WorkspaceTimelineActionState {
  const selected = findSelectedClip(input.timeline, input.selectedClipId);

  if (!selected) {
    return {
      canMoveLeft: false,
      canMoveRight: false,
      canTrim: false,
      canSplit: false,
      reason: "请选择时间线片段"
    };
  }

  const stepMs = Math.max(1, Math.round(input.stepMs ?? DEFAULT_STEP_MS));
  const minDurationMs = Math.max(1, Math.round(input.minDurationMs ?? DEFAULT_MIN_DURATION_MS));
  const clip = selected.clip;
  const canMoveLeft = canMoveBy(selected.track, clip, -stepMs);
  const canMoveRight = canMoveBy(selected.track, clip, stepMs);
  const canSplit = input.playheadMs > clip.startMs && input.playheadMs < clip.startMs + clip.durationMs;
  const canTrim = clip.durationMs > minDurationMs;

  return {
    canMoveLeft,
    canMoveRight,
    canTrim,
    canSplit,
    reason: buildActionReason({ canMoveLeft, canMoveRight, canSplit, clip })
  };
}

function findSelectedClip(
  timeline: WorkspaceTimelineDto | null,
  selectedClipId: string | null
): { clip: WorkspaceTimelineClipDto; track: WorkspaceTimelineTrackDto } | null {
  if (!timeline || !selectedClipId) return null;

  for (const track of timeline.tracks) {
    const clip = track.clips.find((candidate) => candidate.id === selectedClipId);
    if (clip) return { clip, track };
  }

  return null;
}

function canMoveBy(track: WorkspaceTimelineTrackDto, clip: WorkspaceTimelineClipDto, deltaMs: number): boolean {
  const nextStartMs = clip.startMs + deltaMs;
  if (nextStartMs < 0) return false;

  return !track.clips.some((candidate) => {
    if (candidate.id === clip.id) return false;
    return rangesOverlap(nextStartMs, clip.durationMs, candidate.startMs, candidate.durationMs);
  });
}

function rangesOverlap(leftStartMs: number, leftDurationMs: number, rightStartMs: number, rightDurationMs: number): boolean {
  const leftEndMs = leftStartMs + leftDurationMs;
  const rightEndMs = rightStartMs + rightDurationMs;

  return leftStartMs < rightEndMs && leftEndMs > rightStartMs;
}

function buildActionReason(input: {
  canMoveLeft: boolean;
  canMoveRight: boolean;
  canSplit: boolean;
  clip: WorkspaceTimelineClipDto;
}): string {
  if (!input.canSplit) return "播放头需要位于选中片段内部才能分割。";
  if (!input.canMoveLeft && !input.canMoveRight) return "当前片段两侧没有可移动空隙，右侧片段或轨道起点会发生重叠。";
  if (!input.canMoveLeft) return "左移会越过轨道起点或左侧片段。";
  if (!input.canMoveRight) return "右移会与右侧片段重叠。";
  return `${input.clip.label} 可移动、可裁剪、可分割。`;
}
