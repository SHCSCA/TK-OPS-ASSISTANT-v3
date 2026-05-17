import { describe, expect, it } from "vitest";

import {
  useWorkspaceTimelineDrag,
  type WorkspaceTimelineDragClip,
  type WorkspaceTimelineDragRect
} from "@/modules/workspace/useWorkspaceTimelineDrag";

describe("useWorkspaceTimelineDrag", () => {
  it("为片段移动产出预览和提交载荷", () => {
    const drag = useWorkspaceTimelineDrag({
      durationMs: 10_000,
      snapCandidates: [0, 3_000, 5_000],
      snapThresholdMs: 120
    });

    const preview = drag.startMoveDrag({
      clip: clip({ startMs: 1_000, durationMs: 2_000 }),
      clientX: 100,
      rect: timelineRect()
    });

    expect(preview).toMatchObject({
      gesture: "move",
      clipId: "clip-1",
      trackId: "track-video",
      startMs: 1_000,
      durationMs: 2_000
    });

    const updated = drag.updateDrag({ clientX: 4_040, rect: timelineRect() });

    expect(updated).toMatchObject({
      gesture: "move",
      clipId: "clip-1",
      startMs: 5_000,
      durationMs: 2_000
    });
    expect(drag.dragPreview.value).toEqual(updated);

    const commit = drag.finishDrag();

    expect(commit).toEqual(updated);
    expect(drag.dragPreview.value).toBeNull();
  });

  it("移动取消时清空预览且不返回提交载荷", () => {
    const drag = useWorkspaceTimelineDrag({
      durationMs: 10_000,
      snapCandidates: []
    });

    drag.startMoveDrag({
      clip: clip({ startMs: 1_000, durationMs: 2_000 }),
      clientX: 100,
      rect: timelineRect()
    });
    drag.updateDrag({ clientX: 2_000, rect: timelineRect() });

    const cancelled = drag.cancelDrag();

    expect(cancelled).toMatchObject({ gesture: "move", clipId: "clip-1" });
    expect(drag.dragPreview.value).toBeNull();
    expect(drag.finishDrag()).toBeNull();
  });

  it("为左侧裁剪产出最小时长和入点调整后的载荷", () => {
    const drag = useWorkspaceTimelineDrag({
      durationMs: 10_000,
      minDurationMs: 600,
      snapCandidates: []
    });

    drag.startTrimDrag({
      clip: clip({ startMs: 1_000, durationMs: 2_000, inPointMs: 300 }),
      edge: "left",
      clientX: 1_000,
      rect: timelineRect()
    });

    const updated = drag.updateDrag({ clientX: 2_700, rect: timelineRect() });

    expect(updated).toMatchObject({
      gesture: "trim",
      edge: "left",
      clipId: "clip-1",
      startMs: 2_400,
      durationMs: 600,
      inPointMs: 1_700
    });
    expect(drag.finishDrag()).toEqual(updated);
  });

  it("为右侧裁剪产出磁吸后的提交载荷", () => {
    const drag = useWorkspaceTimelineDrag({
      durationMs: 10_000,
      minDurationMs: 500,
      snapCandidates: [4_000],
      snapThresholdMs: 100
    });

    drag.startTrimDrag({
      clip: clip({ startMs: 1_000, durationMs: 2_000 }),
      edge: "right",
      clientX: 3_000,
      rect: timelineRect()
    });

    const updated = drag.updateDrag({ clientX: 3_940, rect: timelineRect() });

    expect(updated).toMatchObject({
      gesture: "trim",
      edge: "right",
      clipId: "clip-1",
      startMs: 1_000,
      durationMs: 3_000,
      inPointMs: 0
    });
    expect(drag.finishDrag()).toEqual(updated);
  });
});

function timelineRect(): WorkspaceTimelineDragRect {
  return {
    left: 0,
    width: 10_000
  };
}

function clip(input: Partial<WorkspaceTimelineDragClip> = {}): WorkspaceTimelineDragClip {
  return {
    id: input.id ?? "clip-1",
    trackId: input.trackId ?? "track-video",
    startMs: input.startMs ?? 1_000,
    durationMs: input.durationMs ?? 2_000,
    inPointMs: input.inPointMs ?? 0
  };
}
