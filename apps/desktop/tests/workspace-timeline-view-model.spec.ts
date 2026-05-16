import { describe, expect, it } from "vitest";

import {
  buildTimelineRows,
  cleanWorkspaceText,
  computePlayheadPercent,
  formatWorkspaceClipRange,
  workspaceStatusLabel,
  workspaceTrackMetaLabel,
  trackVisualClass
} from "@/modules/workspace/workspaceTimelineViewModel";
import type { WorkspaceTimelineTrackDto } from "@/types/runtime";

describe("workspace timeline view model", () => {
  it("连续片段布局没有可视间隙", () => {
    const [row] = buildTimelineRows(
      [
        track({
          clips: [
            clip({ id: "clip-3", startMs: 10000, durationMs: 5000 }),
            clip({ id: "clip-1", startMs: 0, durationMs: 5000 }),
            clip({ id: "clip-2", startMs: 5000, durationMs: 5000 })
          ]
        })
      ],
      15000
    );

    expect(row.clips.map((item) => item.id)).toEqual(["clip-1", "clip-2", "clip-3"]);
    expect(row.clips.map((item) => item.leftPercent)).toEqual([0, 33.333, 66.667]);
    expect(row.clips.map((item) => item.widthPercent)).toEqual([33.333, 33.333, 33.333]);
  });

  it("为连续片段输出首中尾 joinClass，单片段输出 single", () => {
    const rows = buildTimelineRows(
      [
        track({
          id: "track-sequence",
          clips: [
            clip({ id: "clip-1", startMs: 0, durationMs: 5000 }),
            clip({ id: "clip-2", startMs: 5000, durationMs: 5000 }),
            clip({ id: "clip-3", startMs: 10000, durationMs: 5000 })
          ]
        }),
        track({
          id: "track-single",
          orderIndex: 1,
          clips: [clip({ id: "clip-single", trackId: "track-single", startMs: 0, durationMs: 15000 })]
        })
      ],
      15000
    );

    expect(rows[0].clips.map((item) => item.joinClass)).toEqual(["start", "middle", "end"]);
    expect(rows[1].clips[0].joinClass).toBe("single");
  });

  it("输出轨道视觉 class 和高度层级", () => {
    const rows = buildTimelineRows(
      [
        track({ id: "track-subtitle", kind: "subtitle", name: "字幕", orderIndex: 3 }),
        track({ id: "track-bgm", kind: "audio", name: "BGM 音乐", orderIndex: 2 }),
        track({ id: "track-voice", kind: "audio", name: "旁白", orderIndex: 1 }),
        track({ id: "track-video", kind: "video", name: "视频", orderIndex: 0 })
      ],
      15000
    );

    expect(rows.map((row) => row.id)).toEqual(["track-video", "track-voice", "track-bgm", "track-subtitle"]);
    expect(rows.map((row) => row.visualClass)).toEqual(["video", "voice", "bgm", "subtitle"]);
    expect(rows.map((row) => row.heightClass)).toEqual(["tall", "medium", "medium", "compact"]);
    expect(trackVisualClass("audio", "环境声")).toBe("bgm");
  });

  it("播放头百分比 clamp 到 0-100", () => {
    expect(computePlayheadPercent(-1000, 15000)).toBe(0);
    expect(computePlayheadPercent(7500, 15000)).toBe(50);
    expect(computePlayheadPercent(20000, 15000)).toBe(100);
    expect(computePlayheadPercent(500, 0)).toBe(50);
  });

  it("片段百分比 clamp 到 0-100", () => {
    const [row] = buildTimelineRows(
      [
        track({
          clips: [
            clip({ id: "clip-start-overflow", startMs: 20000, durationMs: 5000 }),
            clip({ id: "clip-duration-overflow", startMs: 0, durationMs: 20000 })
          ]
        })
      ],
      15000
    );

    expect(row.clips.find((item) => item.id === "clip-start-overflow")).toMatchObject({
      leftPercent: 100,
      widthPercent: 0
    });
    expect(row.clips.find((item) => item.id === "clip-duration-overflow")).toMatchObject({
      leftPercent: 0,
      widthPercent: 100
    });
  });

  it("片段右边界超过时间线时裁剪可渲染宽度", () => {
    const [row] = buildTimelineRows(
      [
        track({
          clips: [clip({ id: "clip-overflow-right", startMs: 9000, durationMs: 5000 })]
        })
      ],
      10000
    );

    expect(row.clips[0]).toMatchObject({
      leftPercent: 90,
      widthPercent: 10
    });
  });

  it("NaN 百分比输入回退到 0", () => {
    const [row] = buildTimelineRows(
      [
        track({
          clips: [
            clip({ id: "clip-start-nan", startMs: Number.NaN, durationMs: 5000 }),
            clip({ id: "clip-duration-nan", startMs: 0, durationMs: Number.NaN })
          ]
        })
      ],
      15000
    );

    expect(row.clips.find((item) => item.id === "clip-start-nan")).toMatchObject({
      leftPercent: 0,
      widthPercent: 33.333
    });
    expect(row.clips.find((item) => item.id === "clip-duration-nan")).toMatchObject({
      leftPercent: 0,
      widthPercent: 0
    });
    expect(computePlayheadPercent(Number.NaN, 15000)).toBe(0);
    expect(computePlayheadPercent(500, Number.NaN)).toBe(0);
  });

  it("时间线显示层输出中文状态和片段时间范围", () => {
    expect(workspaceStatusLabel("draft")).toBe("草稿");
    expect(workspaceStatusLabel("pending")).toBe("待处理");
    expect(workspaceStatusLabel("ready")).toBe("已就绪");
    expect(workspaceStatusLabel("unknown_status")).toBe("未标注");
    expect(formatWorkspaceClipRange(8120, 2000)).toBe("00:08-00:10");
  });

  it("清理延续占位文本并回退到可读文案", () => {
    expect(cleanWorkspaceText("（延续字幕）", "字幕待确认")).toBe("字幕待确认");
    expect(cleanWorkspaceText("(延续上句口播)", "口播待确认")).toBe("口播待确认");
    expect(cleanWorkspaceText("same as above", "字幕待确认")).toBe("字幕待确认");
    expect(cleanWorkspaceText("延续字幕", "same as above")).toBe("待确认");
    expect(cleanWorkspaceText("延续上句口播", "（延续字幕）")).toBe("待确认");
    expect(cleanWorkspaceText("This lamp made me cancel my dinner plan.", "字幕待确认")).toBe(
      "This lamp made me cancel my dinner plan."
    );
  });

  it("轨道辅助信息不重复显示轨道类型", () => {
    expect(
      workspaceTrackMetaLabel({
        id: "managed-storyboard-video",
        kind: "video",
        name: "分镜视频轨",
        clipCount: 5
      })
    ).toBe("受管轨道 · 5 个片段");
    expect(
      workspaceTrackMetaLabel({
        id: "manual-video",
        kind: "video",
        name: "素材",
        clipCount: 1
      })
    ).toBe("视频轨 · 手动轨道 · 1 个片段");
  });
});

function track(input: Partial<WorkspaceTimelineTrackDto> = {}): WorkspaceTimelineTrackDto {
  return {
    id: input.id ?? "track-video",
    kind: input.kind ?? "video",
    name: input.name ?? "视频轨",
    orderIndex: input.orderIndex ?? 0,
    locked: input.locked ?? false,
    muted: input.muted ?? false,
    clips: input.clips ?? []
  };
}

function clip(input: {
  id: string;
  trackId?: string;
  startMs: number;
  durationMs: number;
}): WorkspaceTimelineTrackDto["clips"][number] {
  return {
    id: input.id,
    trackId: input.trackId ?? "track-video",
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
