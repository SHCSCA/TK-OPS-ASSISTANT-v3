import { describe, expect, it } from "vitest";

import {
  buildTimelineRows,
  cleanWorkspaceText,
  computePlayheadPercent,
  formatWorkspaceClipRange,
  resolveSnapStartMs,
  summarizeManagedTrackSync,
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

  it("为 AI 受管轨道标记统一结束点与需同步状态", () => {
    const rows = buildTimelineRows(
      [
        track({
          id: "managed-video-storyboard",
          clips: [clip({ id: "video", trackId: "managed-video-storyboard", startMs: 0, durationMs: 15000 })]
        }),
        track({
          id: "managed-voice-track",
          kind: "audio",
          name: "配音轨",
          orderIndex: 1,
          clips: [clip({ id: "voice", trackId: "managed-voice-track", startMs: 0, durationMs: 12000 })]
        }),
        track({
          id: "managed-subtitle-track",
          kind: "subtitle",
          name: "字幕轨",
          orderIndex: 2,
          clips: [clip({ id: "subtitle", trackId: "managed-subtitle-track", startMs: 0, durationMs: 15000 })]
        })
      ],
      15000
    );

    expect(rows.map((row) => row.syncStatus)).toEqual(["synced", "short", "synced"]);
    expect(rows.map((row) => row.syncEndPercent)).toEqual([100, 80, 100]);
    expect(rows.map((row) => row.syncTargetPercent)).toEqual([100, 100, 100]);
    expect(rows.map((row) => row.syncGapWidthPercent)).toEqual([0, 20, 0]);
    expect(rows[1].syncGapLeftPercent).toBe(80);
    expect(rows[0].syncLabel).toBe("统一结束");
    expect(rows[1].syncLabel).toBe("需同步 00:03");
  });

  it("手动轨道即使包含 AI 来源片段也不标记为受管轨道", () => {
    const [row] = buildTimelineRows(
      [
        track({
          id: "manual-storyboard-reference",
          clips: [
            clip({
              id: "manual-storyboard-clip",
              sourceType: "storyboard",
              startMs: 0,
              durationMs: 10000
            })
          ]
        })
      ],
      10000
    );

    expect(row.isManagedAITrack).toBe(false);
    expect(row.syncStatus).toBe("synced");
    expect(row.syncLabel).toBe("手动轨道");
  });

  it("AI 三轨同步目标只按受管轨道计算，不被更长手动轨道带偏", () => {
    const tracks = [
      track({
        id: "managed-video-storyboard",
        clips: [clip({ id: "video", trackId: "managed-video-storyboard", startMs: 0, durationMs: 15000 })]
      }),
      track({
        id: "managed-voice-track",
        kind: "audio",
        name: "配音轨",
        orderIndex: 1,
        clips: [clip({ id: "voice", trackId: "managed-voice-track", startMs: 0, durationMs: 15000 })]
      }),
      track({
        id: "managed-subtitle-track",
        kind: "subtitle",
        name: "字幕轨",
        orderIndex: 2,
        clips: [clip({ id: "subtitle", trackId: "managed-subtitle-track", startMs: 0, durationMs: 15000 })]
      }),
      track({
        id: "manual-bgm-track",
        kind: "audio",
        name: "手动 BGM",
        orderIndex: 3,
        clips: [clip({ id: "manual-bgm", trackId: "manual-bgm-track", startMs: 0, durationMs: 30000 })]
      })
    ];

    const summary = summarizeManagedTrackSync(tracks, 30000);
    const rows = buildTimelineRows(tracks, 30000, summary.targetDurationMs);

    expect(summary).toMatchObject({
      managedCount: 3,
      targetDurationMs: 15000,
      unsyncedCount: 0,
      visible: true
    });
    expect(rows.filter((row) => row.isManagedAITrack).map((row) => row.syncStatus)).toEqual([
      "synced",
      "synced",
      "synced"
    ]);
  });

  it("声明时长存在时作为 AI 三轨规范目标，过长受管轨道标记超出", () => {
    const tracks = [
      track({
        id: "managed-video-storyboard",
        clips: [clip({ id: "video", trackId: "managed-video-storyboard", startMs: 0, durationMs: 18000 })]
      }),
      track({
        id: "managed-voice-track",
        kind: "audio",
        name: "配音轨",
        orderIndex: 1,
        clips: [clip({ id: "voice", trackId: "managed-voice-track", startMs: 0, durationMs: 15000 })]
      }),
      track({
        id: "manual-bgm-track",
        kind: "audio",
        name: "手动 BGM",
        orderIndex: 2,
        clips: [clip({ id: "manual-bgm", trackId: "manual-bgm-track", startMs: 0, durationMs: 30000 })]
      })
    ];

    const summary = summarizeManagedTrackSync(tracks, 30000, 15000);
    const rows = buildTimelineRows(tracks, 30000, summary.targetDurationMs);

    expect(summary).toMatchObject({
      managedCount: 2,
      targetDurationMs: 15000,
      unsyncedCount: 1,
      visible: true
    });
    expect(rows.filter((row) => row.isManagedAITrack).map((row) => row.syncStatus)).toEqual([
      "overflow",
      "synced"
    ]);
  });

  it("声明时长超过受管轨道范围时作为 AI 三轨对齐目标", () => {
    const tracks = [
      track({
        id: "managed-video-storyboard",
        clips: [clip({ id: "video", trackId: "managed-video-storyboard", startMs: 0, durationMs: 5000 })]
      }),
      track({
        id: "managed-voice-track",
        kind: "audio",
        name: "配音轨",
        orderIndex: 1,
        clips: [clip({ id: "voice", trackId: "managed-voice-track", startMs: 0, durationMs: 3000 })]
      }),
      track({
        id: "manual-bgm-track",
        kind: "audio",
        name: "手动 BGM",
        orderIndex: 2,
        clips: [clip({ id: "manual-bgm", trackId: "manual-bgm-track", startMs: 0, durationMs: 12000 })]
      })
    ];

    const summary = summarizeManagedTrackSync(tracks, 12000, 12000);
    const rows = buildTimelineRows(tracks, 12000, summary.targetDurationMs);

    expect(summary).toMatchObject({
      managedCount: 2,
      targetDurationMs: 12000,
      unsyncedCount: 2,
      visible: true
    });
    expect(rows.filter((row) => row.isManagedAITrack).map((row) => row.syncStatus)).toEqual([
      "short",
      "short"
    ]);
    expect(rows.filter((row) => row.isManagedAITrack).map((row) => row.syncTargetPercent)).toEqual([100, 100]);
  });

  it("声明时长存在时优先作为三条受管轨道的同步目标", () => {
    const tracks = [
      track({
        id: "managed-video-storyboard",
        clips: [clip({ id: "video", trackId: "managed-video-storyboard", sourceType: "storyboard", startMs: 0, durationMs: 5000 })]
      }),
      track({
        id: "managed-voice-track",
        kind: "audio",
        name: "配音轨",
        orderIndex: 1,
        clips: [clip({ id: "voice", trackId: "managed-voice-track", sourceType: "voice_track", startMs: 0, durationMs: 5000 })]
      }),
      track({
        id: "managed-subtitle-track",
        kind: "subtitle",
        name: "字幕轨",
        orderIndex: 2,
        clips: [clip({ id: "subtitle", trackId: "managed-subtitle-track", sourceType: "subtitle_track", startMs: 0, durationMs: 5000 })]
      }),
      track({
        id: "manual-bgm-track",
        kind: "audio",
        name: "手动 BGM",
        orderIndex: 3,
        clips: [clip({ id: "manual-bgm", trackId: "manual-bgm-track", startMs: 0, durationMs: 12000 })]
      })
    ];

    const summary = summarizeManagedTrackSync(tracks, 12000, 12000);
    const rows = buildTimelineRows(tracks, 12000, summary.targetDurationMs);
    const managedRows = rows.filter((row) => row.isManagedAITrack);

    expect(summary).toMatchObject({
      managedCount: 3,
      targetDurationMs: 12000,
      unsyncedCount: 3,
      visible: true
    });
    expect(managedRows.map((row) => row.syncStatus)).toEqual(["short", "short", "short"]);
    expect(managedRows.map((row) => row.syncLabel)).toEqual(["需同步 00:07", "需同步 00:07", "需同步 00:07"]);
    expect(managedRows.flatMap((row) => row.clips.map((item) => formatWorkspaceClipRange(item.clip.startMs, item.clip.durationMs)))).toEqual([
      "00:00-00:05",
      "00:00-00:05",
      "00:00-00:05"
    ]);
  });

  it("没有声明时长时才使用三条受管轨道共同结束点", () => {
    const tracks = [
      track({
        id: "managed-video-storyboard",
        clips: [clip({ id: "video", trackId: "managed-video-storyboard", sourceType: "storyboard", startMs: 0, durationMs: 5000 })]
      }),
      track({
        id: "managed-voice-track",
        kind: "audio",
        name: "配音轨",
        orderIndex: 1,
        clips: [clip({ id: "voice", trackId: "managed-voice-track", sourceType: "voice_track", startMs: 0, durationMs: 5000 })]
      }),
      track({
        id: "managed-subtitle-track",
        kind: "subtitle",
        name: "字幕轨",
        orderIndex: 2,
        clips: [clip({ id: "subtitle", trackId: "managed-subtitle-track", sourceType: "subtitle_track", startMs: 0, durationMs: 5000 })]
      })
    ];

    const summary = summarizeManagedTrackSync(tracks, 5000, 0);
    const rows = buildTimelineRows(tracks, 5000, summary.targetDurationMs);

    expect(summary).toMatchObject({
      managedCount: 3,
      targetDurationMs: 5000,
      unsyncedCount: 0,
      visible: true
    });
    expect(rows.filter((row) => row.isManagedAITrack).map((row) => row.syncStatus)).toEqual([
      "synced",
      "synced",
      "synced"
    ]);
  });

  it("AI 轨道超过声明时长时按同步目标标记超出，不被画布时长吞掉", () => {
    const rows = buildTimelineRows(
      [
        track({
          id: "managed-video-storyboard",
          clips: [clip({ id: "video", trackId: "managed-video-storyboard", startMs: 0, durationMs: 18000 })]
        }),
        track({
          id: "managed-voice-track",
          kind: "audio",
          name: "配音轨",
          orderIndex: 1,
          clips: [clip({ id: "voice", trackId: "managed-voice-track", startMs: 0, durationMs: 15000 })]
        })
      ],
      18000,
      15000
    );

    expect(rows.map((row) => row.syncStatus)).toEqual(["overflow", "synced"]);
    expect(rows[0].syncLabel).toBe("超出 00:03");
    expect(rows[0].syncEndPercent).toBe(100);
    expect(rows[0].syncTargetPercent).toBe(83.333);
    expect(rows[0].syncGapWidthPercent).toBe(0);
    expect(rows[1].syncEndPercent).toBe(83.333);
  });

  it("播放头百分比 clamp 到 0-100", () => {
    expect(computePlayheadPercent(-1000, 15000)).toBe(0);
    expect(computePlayheadPercent(7500, 15000)).toBe(50);
    expect(computePlayheadPercent(20000, 15000)).toBe(100);
    expect(computePlayheadPercent(500, 0)).toBe(50);
  });

  it("从片段边界计算最近磁吸起点", () => {
    const clips = [
      clip({ id: "left", startMs: 0, durationMs: 3000 }),
      clip({ id: "target", startMs: 3500, durationMs: 2000 }),
      clip({ id: "right", startMs: 6000, durationMs: 2000 })
    ];

    expect(resolveSnapStartMs(clips, "target", 3020, 120)).toBe(3000);
    expect(resolveSnapStartMs(clips, "target", 5980, 120)).toBe(6000);
    expect(resolveSnapStartMs(clips, "target", 4200, 120)).toBe(4200);
  });

  it("兼容磁吸入口会排除正在移动的片段边界", () => {
    const clips = [
      clip({ id: "left", startMs: 0, durationMs: 3000 }),
      clip({ id: "target", startMs: 3500, durationMs: 2000 }),
      clip({ id: "right", startMs: 6000, durationMs: 2000 })
    ];

    expect(resolveSnapStartMs(clips, "target", 3520, 120)).toBe(3520);
    expect(resolveSnapStartMs(clips, "target", Number.NaN, 120)).toBe(0);
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
    ).toBe("AI 受管轨道 · 5 个片段");
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
  sourceType?: WorkspaceTimelineTrackDto["clips"][number]["sourceType"];
  startMs: number;
  durationMs: number;
}): WorkspaceTimelineTrackDto["clips"][number] {
  return {
    id: input.id,
    trackId: input.trackId ?? "track-video",
    sourceType: input.sourceType ?? "asset",
    sourceId: input.id,
    label: input.id,
    startMs: input.startMs,
    durationMs: input.durationMs,
    inPointMs: 0,
    outPointMs: null,
    status: "ready"
  };
}
