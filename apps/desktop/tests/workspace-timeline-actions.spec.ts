import { describe, expect, it } from "vitest";

import { evaluateTimelineClipActions } from "@/modules/workspace/workspaceTimelineActions";
import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";

describe("M05 时间线操作可用性", () => {
  it("连续相邻片段会提前禁用导致重叠的移动方向", () => {
    const timeline = timelineWithClips([
      clip("clip-1", 0, 5000),
      clip("clip-2", 5000, 4000)
    ]);

    const firstClipActions = evaluateTimelineClipActions({
      timeline,
      selectedClipId: "clip-1",
      playheadMs: 2000,
      stepMs: 500
    });
    const secondClipActions = evaluateTimelineClipActions({
      timeline,
      selectedClipId: "clip-2",
      playheadMs: 6500,
      stepMs: 500
    });

    expect(firstClipActions.canMoveLeft).toBe(false);
    expect(firstClipActions.canMoveRight).toBe(false);
    expect(firstClipActions.reason).toContain("右侧片段");
    expect(secondClipActions.canMoveLeft).toBe(false);
    expect(secondClipActions.canMoveRight).toBe(true);
  });

  it("播放头只有在选中片段内部时才允许分割", () => {
    const timeline = timelineWithClips([clip("clip-1", 1000, 5000)]);

    expect(evaluateTimelineClipActions({
      timeline,
      selectedClipId: "clip-1",
      playheadMs: 1000,
      stepMs: 500
    }).canSplit).toBe(false);
    expect(evaluateTimelineClipActions({
      timeline,
      selectedClipId: "clip-1",
      playheadMs: 3500,
      stepMs: 500
    }).canSplit).toBe(true);
    expect(evaluateTimelineClipActions({
      timeline,
      selectedClipId: "clip-1",
      playheadMs: 6000,
      stepMs: 500
    }).canSplit).toBe(false);
  });
});

function timelineWithClips(clips: WorkspaceTimelineClipDto[]): WorkspaceTimelineDto {
  return {
    id: "timeline-1",
    projectId: "project-1",
    name: "主时间线",
    status: "draft",
    durationSeconds: 12,
    source: "manual",
    tracks: [track(clips)],
    createdAt: "2026-05-17T00:00:00Z",
    updatedAt: "2026-05-17T00:00:00Z"
  };
}

function track(clips: WorkspaceTimelineClipDto[]): WorkspaceTimelineTrackDto {
  return {
    id: "track-video",
    kind: "video",
    name: "主画面",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips
  };
}

function clip(id: string, startMs: number, durationMs: number): WorkspaceTimelineClipDto {
  return {
    id,
    trackId: "track-video",
    sourceType: "storyboard",
    sourceId: `${id}-source`,
    label: id,
    startMs,
    durationMs,
    inPointMs: 0,
    outPointMs: null,
    status: "ready",
    metadata: {
      sourceKind: "storyboard",
      sourceRevision: 1,
      segmentIndex: 0,
      segmentId: id,
      text: null,
      visualPrompt: null
    }
  };
}
