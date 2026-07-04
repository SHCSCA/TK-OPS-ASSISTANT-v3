import type {
  WorkspaceSaveStateDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineResultDto,
  WorkspaceTimelineUpdateInput
} from "@/types/runtime";

export type WorkspaceTimelineHistorySnapshot = {
  timeline: WorkspaceTimelineDto;
  selectedTrackId: string | null;
  selectedClipId: string | null;
  playheadMs: number;
};

export function cloneWorkspaceTimeline(timeline: WorkspaceTimelineDto): WorkspaceTimelineDto {
  return JSON.parse(JSON.stringify(timeline)) as WorkspaceTimelineDto;
}

export function createWorkspaceTimelineHistorySnapshot(input: {
  timeline: WorkspaceTimelineDto | null;
  selectedTrackId: string | null;
  selectedClipId: string | null;
  playheadMs: number;
}): WorkspaceTimelineHistorySnapshot | null {
  if (!input.timeline) return null;
  return {
    timeline: cloneWorkspaceTimeline(input.timeline),
    selectedTrackId: input.selectedTrackId,
    selectedClipId: input.selectedClipId,
    playheadMs: input.playheadMs
  };
}

export function createWorkspaceTimelineUpdateInput(
  timeline: WorkspaceTimelineDto
): WorkspaceTimelineUpdateInput {
  return {
    name: timeline.name,
    durationSeconds: timeline.durationSeconds,
    tracks: timeline.tracks
  };
}

export function createTimelineHistorySaveState(
  result: WorkspaceTimelineResultDto,
  source: "timeline_undo" | "timeline_redo",
  message: string
): WorkspaceSaveStateDto {
  return {
    saved: result.saveState?.saved ?? true,
    updatedAt: result.saveState?.updatedAt ?? result.timeline?.updatedAt ?? new Date().toISOString(),
    source,
    message
  };
}
