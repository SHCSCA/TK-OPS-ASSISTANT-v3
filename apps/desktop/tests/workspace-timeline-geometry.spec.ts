import { describe, expect, it } from "vitest";

import {
  clampTimelineMs,
  clientXToTimelineMs,
  normalizeTimelineZoomPercent,
  timelineContentBaseWidthPx,
  timelineZoomGridSizePx,
  timelineZoomScale,
  msToPercent,
  percentToMs
} from "@/modules/workspace/workspaceTimelineGeometry";
import {
  buildSnapCandidates,
  resolveTimelineSnap
} from "@/modules/workspace/workspaceTimelineSnap";
import type { WorkspaceTimelineClipDto } from "@/types/runtime";

describe("workspace timeline geometry", () => {
  it("将毫秒值限制在时间线范围内", () => {
    expect(clampTimelineMs(-100, 1000)).toBe(0);
    expect(clampTimelineMs(500, 1000)).toBe(500);
    expect(clampTimelineMs(1200, 1000)).toBe(1000);
    expect(clampTimelineMs(Number.NaN, 1000)).toBe(0);
    expect(clampTimelineMs(500, Number.POSITIVE_INFINITY)).toBe(0);
  });

  it("在毫秒和百分比之间转换时处理越界与非有限数字", () => {
    expect(msToPercent(0, 1000)).toBe(0);
    expect(msToPercent(250, 1000)).toBe(25);
    expect(msToPercent(1000, 1000)).toBe(100);
    expect(msToPercent(1200, 1000)).toBe(100);
    expect(msToPercent(Number.NaN, 1000)).toBe(0);

    expect(percentToMs(-10, 2000)).toBe(0);
    expect(percentToMs(25, 2000)).toBe(500);
    expect(percentToMs(100, 2000)).toBe(2000);
    expect(percentToMs(120, 2000)).toBe(2000);
    expect(percentToMs(Number.NaN, 2000)).toBe(0);
  });

  it("从 rect-like 对象换算鼠标位置对应的时间线毫秒值", () => {
    const rect = { left: 100, width: 400 };

    expect(clientXToTimelineMs(100, rect, 2000)).toBe(0);
    expect(clientXToTimelineMs(300, rect, 2000)).toBe(1000);
    expect(clientXToTimelineMs(500, rect, 2000)).toBe(2000);
    expect(clientXToTimelineMs(50, rect, 2000)).toBe(0);
    expect(clientXToTimelineMs(600, rect, 2000)).toBe(2000);
    expect(clientXToTimelineMs(Number.NaN, rect, 2000)).toBe(0);
    expect(clientXToTimelineMs(300, { left: 100, width: 0 }, 2000)).toBe(0);
  });

  it("将时间线缩放限制到统一档位并换算密度变量", () => {
    expect(normalizeTimelineZoomPercent(Number.NaN)).toBe(100);
    expect(normalizeTimelineZoomPercent(10)).toBe(50);
    expect(normalizeTimelineZoomPercent(76)).toBe(75);
    expect(normalizeTimelineZoomPercent(124)).toBe(100);
    expect(normalizeTimelineZoomPercent(126)).toBe(150);
    expect(normalizeTimelineZoomPercent(260)).toBe(300);

    expect(timelineZoomScale(50)).toBe(0.5);
    expect(timelineZoomScale(150)).toBe(1.5);
    expect(timelineZoomGridSizePx(150)).toBe(120);
    expect(timelineContentBaseWidthPx(15000)).toBe(960);
    expect(timelineContentBaseWidthPx(30000)).toBe(1920);
  });
});

describe("workspace timeline snap", () => {
  it("从片段边界、播放头、零点和时间线终点构建磁吸候选", () => {
    const candidates = buildSnapCandidates(
      [
        clip({ id: "left", startMs: 0, durationMs: 3000 }),
        clip({ id: "moving", startMs: 3200, durationMs: 1000 }),
        clip({ id: "right", startMs: 6000, durationMs: 2000 })
      ],
      {
        movingClipId: "moving",
        playheadMs: 4500,
        timelineEndMs: 9000
      }
    );

    expect(candidates).toEqual([0, 3000, 4500, 6000, 8000, 9000]);
  });

  it("在阈值内吸附最近候选，阈值外保留原值", () => {
    const candidates = [0, 3000, 4500, 6000, 8000];

    expect(resolveTimelineSnap(3020, candidates, 120)).toBe(3000);
    expect(resolveTimelineSnap(5920, candidates, 120)).toBe(6000);
    expect(resolveTimelineSnap(4200, candidates, 120)).toBe(4200);
    expect(resolveTimelineSnap(Number.NaN, candidates, 120)).toBe(0);
  });
});

function clip(input: {
  id: string;
  startMs: number;
  durationMs: number;
}): WorkspaceTimelineClipDto {
  return {
    id: input.id,
    trackId: "track-video",
    sourceType: "asset",
    sourceId: input.id,
    label: input.id,
    startMs: input.startMs,
    durationMs: input.durationMs,
    inPointMs: 0,
    outPointMs: null,
    status: "ready"
  };
}
