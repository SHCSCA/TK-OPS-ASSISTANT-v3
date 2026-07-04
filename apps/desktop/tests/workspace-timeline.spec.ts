import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WorkspaceTimeline from "../src/modules/workspace/WorkspaceTimeline.vue";
import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto
} from "../src/types/runtime";

describe("M05 工作台时间线", () => {
  let originalScrollIntoView: typeof Element.prototype.scrollIntoView | undefined;

  beforeEach(() => {
    originalScrollIntoView = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();

    if (originalScrollIntoView) {
      Element.prototype.scrollIntoView = originalScrollIntoView;
    } else {
      delete Element.prototype.scrollIntoView;
    }
  });

  it("无受管 AI 轨道时不渲染同步摘要", () => {
    const timeline = workspaceTimeline([
      track({
        id: "manual-video-track",
        name: "手动视频轨",
        clips: [clip({ id: "manual-video-clip", trackId: "manual-video-track", durationMs: 15000 })]
      }),
      track({
        id: "manual-voice-track",
        kind: "audio",
        name: "手动配音轨",
        orderIndex: 1,
        clips: [clip({ id: "manual-voice-clip", trackId: "manual-voice-track", sourceType: "voice_track", durationMs: 15000 })]
      })
    ]);

    const wrapper = mountTimeline(timeline);

    expect(wrapper.find('[data-testid="workspace-timeline-sync-summary"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="workspace-sync-end"]').exists()).toBe(false);
  });

  it("三条受管 AI 轨道等长时渲染已同步摘要和轨道同步标记", () => {
    const timeline = workspaceTimeline(managedTracks({ voiceDurationMs: 15000 }));

    const wrapper = mountTimeline(timeline);
    const summary = wrapper.get('[data-testid="workspace-timeline-sync-summary"]');
    const managedRows = wrapper.findAll(".workspace-track__sync-badge");

    expect(summary.attributes("data-sync")).toBe("synced");
    expect(summary.text()).toContain("三轨统一结束");
    expect(summary.text()).toContain("3 条 AI 受管轨道对齐到 00:15");
    expect(managedRows).toHaveLength(3);
    expect(managedRows.map((row) => row.attributes("data-sync"))).toEqual(["synced", "synced", "synced"]);
    expect(wrapper.findAll(".workspace-track__sync-target")).toHaveLength(3);
    expect(wrapper.findAll(".workspace-track__sync-target").map((item) => item.attributes("style"))).toEqual([
      "width: 100%;",
      "width: 100%;",
      "width: 100%;"
    ]);
    expect(wrapper.get('[data-testid="workspace-sync-end"]').text()).toContain("AI 统一结束");
    expect(wrapper.findAll(".workspace-track__sync-span").map((item) => item.text())).toEqual([
      "统一结束",
      "统一结束",
      "统一结束"
    ]);
    expect(wrapper.find(".workspace-track__sync-gap").exists()).toBe(false);
  });

  it("三条受管 AI 轨道短于声明时长时按统一目标显示缺口", () => {
    const timeline = workspaceTimeline(
      managedTracks({
        videoDurationMs: 5000,
        voiceDurationMs: 5000,
        subtitleDurationMs: 5000
      }),
      12
    );

    const wrapper = mountTimeline(timeline);
    const summary = wrapper.get('[data-testid="workspace-timeline-sync-summary"]');
    const managedRows = wrapper.findAll(".workspace-track__sync-badge");
    const gaps = wrapper.findAll(".workspace-track__sync-gap");

    expect(summary.attributes("data-sync")).toBe("warning");
    expect(summary.text()).toContain("三轨需要同步");
    expect(summary.text()).toContain("3 条 AI 受管轨道未对齐到 00:12");
    expect(managedRows.map((row) => row.attributes("data-sync"))).toEqual(["short", "short", "short"]);
    expect(gaps).toHaveLength(3);
    expect(gaps.map((row) => row.text())).toEqual(["需同步 00:07", "需同步 00:07", "需同步 00:07"]);
    expect(gaps.map((row) => row.attributes("style"))).toEqual([
      "left: 41.667%; width: 58.333%;",
      "left: 41.667%; width: 58.333%;",
      "left: 41.667%; width: 58.333%;"
    ]);
  });

  it("缺少配音轨时不把两条受管轨道误报为三轨统一结束", () => {
    const timeline = workspaceTimeline([
      track({
        id: "managed-video-storyboard",
        name: "分镜视频轨",
        clips: [
          clip({
            id: "managed-video-storyboard-clip",
            trackId: "managed-video-storyboard",
            sourceType: "storyboard",
            durationMs: 15000
          })
        ]
      }),
      track({
        id: "managed-subtitle-track",
        kind: "subtitle",
        name: "字幕轨",
        orderIndex: 1,
        clips: [
          clip({
            id: "managed-subtitle-track-clip",
            trackId: "managed-subtitle-track",
            sourceType: "subtitle_track",
            durationMs: 15000
          })
        ]
      })
    ]);

    const wrapper = mountTimeline(timeline);
    const summary = wrapper.get('[data-testid="workspace-timeline-sync-summary"]');

    expect(summary.attributes("data-sync")).toBe("warning");
    expect(summary.text()).not.toContain("三轨统一结束");
    expect(summary.text()).toContain("2 条轨道已对齐");
    expect(summary.text()).toContain("缺少配音轨");
  });

  it("缺少配音轨且现有受管轨道为空时不显示已对齐", () => {
    const timeline = workspaceTimeline([
      track({
        id: "managed-video-storyboard",
        name: "分镜视频轨",
        clips: []
      }),
      track({
        id: "managed-subtitle-track",
        kind: "subtitle",
        name: "字幕轨",
        orderIndex: 1,
        clips: []
      })
    ]);

    const wrapper = mountTimeline(timeline);
    const summary = wrapper.get('[data-testid="workspace-timeline-sync-summary"]');

    expect(summary.attributes("data-sync")).toBe("warning");
    expect(summary.text()).not.toContain("2 条轨道已对齐");
    expect(summary.text()).toContain("2 条轨道需要同步");
    expect(summary.text()).toContain("缺少配音轨");
  });

  it("配音轨短于视频和字幕轨时渲染需同步摘要和缺口区间", () => {
    const timeline = workspaceTimeline(managedTracks({ voiceDurationMs: 12000 }));

    const wrapper = mountTimeline(timeline);
    const summary = wrapper.get('[data-testid="workspace-timeline-sync-summary"]');
    const gaps = wrapper.findAll(".workspace-track__sync-gap");

    expect(summary.attributes("data-sync")).toBe("warning");
    expect(summary.text()).toContain("三轨需要同步");
    expect(summary.text()).toContain("1 条 AI 受管轨道未对齐到 00:15");
    expect(gaps).toHaveLength(1);
    expect(gaps[0].attributes("data-sync")).toBe("short");
    expect(gaps[0].text()).toContain("需同步 00:03");
    expect(gaps[0].attributes("style")).toContain("left: 80%;");
    expect(gaps[0].attributes("style")).toContain("width: 20%;");
  });

  it("selectedClipId 变化时滚动到对应片段", async () => {
    const timeline = workspaceTimeline(managedTracks({ voiceDurationMs: 15000 }));
    const scrollIntoView = Element.prototype.scrollIntoView as ReturnType<typeof vi.fn>;
    const wrapper = mountTimeline(timeline, {
      attachTo: document.body,
      selectedClipId: null
    });

    await wrapper.setProps({ selectedClipId: "managed-voice-track-clip" });
    await flushPromises();

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "nearest" });
  });

  it("缩放比例驱动统一时间线内容宽度、刻度密度和坐标层", () => {
    const timeline = workspaceTimeline(managedTracks({ voiceDurationMs: 15000 }));

    const wrapper = mountTimeline(timeline, {
      zoomPercent: 150
    });
    const root = wrapper.get('[data-testid="workspace-timeline"]');
    const content = wrapper.get('[data-testid="workspace-timeline-content"]');

    expect(root.attributes("data-zoom-percent")).toBe("150");
    expect(content.attributes("style")).toContain("--workspace-timeline-zoom-scale: 1.5;");
    expect(content.attributes("style")).toContain("--workspace-timeline-content-base-width: 960px;");
    expect(content.attributes("style")).toContain("--workspace-timeline-grid-size: 120px;");
    expect(wrapper.get(".workspace-timeline__ruler").element.parentElement).toBe(content.element);
    expect(wrapper.get(".workspace-timeline__playhead-layer").element.parentElement).toBe(content.element);
    expect(wrapper.get(".workspace-timeline__tracks").element.parentElement).toBe(content.element);
  });
});

function mountTimeline(
  timeline: WorkspaceTimelineDto,
  options: Partial<{
    attachTo: HTMLElement;
    selectedClipId: string | null;
    zoomPercent: number;
  }> = {}
) {
  return mount(WorkspaceTimeline, {
    attachTo: options.attachTo,
    props: {
      selectedClipId: options.selectedClipId ?? null,
      selectedTrackId: null,
      playheadMs: 0,
      status: "ready",
      timeline,
      tracks: timeline.tracks,
      zoomPercent: options.zoomPercent ?? 100
    }
  });
}

function workspaceTimeline(tracks: WorkspaceTimelineTrackDto[], durationSeconds = 15): WorkspaceTimelineDto {
  return {
    id: "timeline-1",
    projectId: "project-1",
    name: "主时间线",
    status: "draft",
    durationSeconds,
    source: "runtime",
    tracks,
    createdAt: now(),
    updatedAt: now()
  };
}

function managedTracks(input: {
  voiceDurationMs: number;
  videoDurationMs?: number;
  subtitleDurationMs?: number;
}): WorkspaceTimelineTrackDto[] {
  return [
    track({
      id: "managed-video-storyboard",
      name: "分镜视频轨",
      clips: [
        clip({
          id: "managed-video-storyboard-clip",
          trackId: "managed-video-storyboard",
          sourceType: "storyboard",
          durationMs: input.videoDurationMs ?? 15000
        })
      ]
    }),
    track({
      id: "managed-voice-track",
      kind: "audio",
      name: "配音轨",
      orderIndex: 1,
      clips: [
        clip({
          id: "managed-voice-track-clip",
          trackId: "managed-voice-track",
          sourceType: "voice_track",
          durationMs: input.voiceDurationMs
        })
      ]
    }),
    track({
      id: "managed-subtitle-track",
      kind: "subtitle",
      name: "字幕轨",
      orderIndex: 2,
      clips: [
        clip({
            id: "managed-subtitle-track-clip",
            trackId: "managed-subtitle-track",
            sourceType: "subtitle_track",
            durationMs: input.subtitleDurationMs ?? 15000,
          metadata: {
            sourceKind: "subtitle_track",
            sourceRevision: 1,
            segmentIndex: 0,
            segmentId: "S01",
            text: "字幕片段",
            visualPrompt: null
          }
        })
      ]
    })
  ];
}

function track(input: Partial<WorkspaceTimelineTrackDto> = {}): WorkspaceTimelineTrackDto {
  return {
    id: input.id ?? "managed-video-storyboard",
    kind: input.kind ?? "video",
    name: input.name ?? "视频轨",
    orderIndex: input.orderIndex ?? 0,
    locked: input.locked ?? false,
    muted: input.muted ?? false,
    clips: input.clips ?? []
  };
}

function clip(input: Partial<WorkspaceTimelineClipDto> & { id: string; trackId: string }): WorkspaceTimelineClipDto {
  return {
    id: input.id,
    trackId: input.trackId,
    sourceType: input.sourceType ?? "asset",
    sourceId: input.sourceId ?? input.id,
    label: input.label ?? input.id,
    startMs: input.startMs ?? 0,
    durationMs: input.durationMs ?? 15000,
    inPointMs: input.inPointMs ?? 0,
    outPointMs: input.outPointMs ?? null,
    status: input.status ?? "ready",
    metadata: input.metadata ?? {
      sourceKind: input.sourceType ?? "asset",
      sourceRevision: 1,
      segmentIndex: 0,
      segmentId: "S01",
      text: "测试片段",
      visualPrompt: null
    }
  };
}

function now() {
  return "2026-04-17T10:00:00Z";
}
