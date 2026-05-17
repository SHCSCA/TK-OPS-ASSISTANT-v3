import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkspaceAssetRail from "@/modules/workspace/WorkspaceAssetRail.vue";
import type {
  AssetDto,
  WorkspaceAssemblyStateDto,
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";

describe("M05 工作台资产栏", () => {
  it("资产 tab 只渲染当前项目资产", () => {
    const wrapper = mountRail({
      assets: [
        asset({ id: "asset-video", name: "当前项目视频.mp4", projectId: "project-1" }),
        asset({ id: "asset-other", name: "其他项目视频.mp4", projectId: "project-2" })
      ]
    });

    expect(wrapper.text()).toContain("当前项目视频.mp4");
    expect(wrapper.text()).not.toContain("其他项目视频.mp4");
  });

  it("可用资产且存在时间线时点击加入时间线会发出资产入轨事件", async () => {
    const wrapper = mountRail({
      assets: [asset({ id: "asset-video", name: "可入轨视频.mp4", availabilityStatus: "ready" })]
    });

    const insertButton = buttonByText(wrapper, "加入时间线");
    expect(insertButton.element.disabled).toBe(false);

    await insertButton.trigger("click");

    expect(wrapper.emitted("asset-insert")).toEqual([["asset-video"]]);
  });

  it("替换片段只在资产类型与选中片段轨道兼容时启用", () => {
    const wrapper = mountRail({
      assets: [
        asset({ id: "asset-video", name: "可替换视频.mp4", type: "video" }),
        asset({ id: "asset-image", name: "可替换图片.png", type: "image" }),
        asset({ id: "asset-audio", name: "不可替换音频.wav", type: "audio" })
      ],
      selectedClip: clip({ id: "clip-video", trackId: "track-video" })
    });

    expect(actionButton(wrapper, "可替换视频.mp4", "替换片段").element.disabled).toBe(false);
    expect(actionButton(wrapper, "可替换图片.png", "替换片段").element.disabled).toBe(false);
    expect(actionButton(wrapper, "不可替换音频.wav", "替换片段").element.disabled).toBe(true);

    const audioWrapper = mountRail({
      assets: [
        asset({ id: "asset-video", name: "不可替换视频.mp4", type: "video" }),
        asset({ id: "asset-audio", name: "可替换音频.wav", type: "audio" })
      ],
      selectedClip: clip({ id: "clip-audio", trackId: "track-audio" })
    });

    expect(actionButton(audioWrapper, "不可替换视频.mp4", "替换片段").element.disabled).toBe(true);
    expect(actionButton(audioWrapper, "可替换音频.wav", "替换片段").element.disabled).toBe(false);
  });

  it("不可用资产显示中文原因并禁用加入和替换动作", () => {
    const wrapper = mountRail({
      assets: [
        asset({
          id: "asset-missing",
          name: "缺失素材.mp4",
          availability: {
            status: "missing",
            errorCode: "asset.file_missing",
            errorMessage: "资产文件已丢失，请重新导入。",
            nextAction: null
          }
        })
      ],
      selectedClip: clip({ id: "clip-video", trackId: "track-video" })
    });

    expect(wrapper.text()).toContain("资产文件已丢失，请重新导入。");
    expect(actionButton(wrapper, "缺失素材.mp4", "加入时间线").element.disabled).toBe(true);
    expect(actionButton(wrapper, "缺失素材.mp4", "替换片段").element.disabled).toBe(true);
  });

  it("来源 tab 使用稳定测试标识并能切换到真实分镜、配音和字幕片段", async () => {
    const wrapper = mountRail({
      assets: [],
      timeline: timeline({
        tracks: [
          track("track-storyboard", "video", [
            clip({
              id: "clip-storyboard",
              label: "S01 · 分镜画面",
              sourceType: "storyboard",
              trackId: "track-storyboard"
            })
          ]),
          track("track-voice", "audio", [
            clip({
              id: "clip-voice",
              label: "S01 · 配音",
              sourceType: "voice_track",
              trackId: "track-voice"
            })
          ]),
          track("track-subtitle", "subtitle", [
            clip({
              id: "clip-subtitle",
              label: "S01 · 字幕",
              sourceType: "subtitle_track",
              trackId: "track-subtitle"
            })
          ])
        ]
      })
    });

    expect(wrapper.get('[data-testid="workspace-asset-tab-storyboard"]').attributes("aria-selected")).toBe("false");
    expect(wrapper.get('[data-testid="workspace-asset-tab-assets"]').attributes("aria-selected")).toBe("true");

    await wrapper.get('[data-testid="workspace-asset-tab-storyboard"]').trigger("click");
    expect(wrapper.get('[data-testid="workspace-asset-tab-storyboard"]').attributes("aria-selected")).toBe("true");
    expect(wrapper.text()).toContain("S01 · 分镜画面");
    expect(wrapper.text()).not.toContain("暂无项目资产");
    expect(wrapper.get(".workspace-asset-rail__list").classes()).toContain("workspace-asset-rail__list--sources");

    await wrapper.get('[data-testid="workspace-asset-tab-voice_track"]').trigger("click");
    expect(wrapper.get('[data-testid="workspace-asset-tab-voice_track"]').attributes("aria-selected")).toBe("true");
    expect(wrapper.text()).toContain("S01 · 配音");

    await wrapper.get('[data-testid="workspace-asset-tab-subtitle_track"]').trigger("click");
    expect(wrapper.get('[data-testid="workspace-asset-tab-subtitle_track"]').attributes("aria-selected")).toBe("true");
    expect(wrapper.text()).toContain("S01 · 字幕");
  });
});

function mountRail(overrides: Partial<{
  assets: AssetDto[];
  selectedClip: WorkspaceTimelineClipDto | null;
  timeline: WorkspaceTimelineDto | null;
}> = {}) {
  return mount(WorkspaceAssetRail, {
    props: {
      assemblyState: assemblyState(),
      assetError: null,
      assetStatus: "ready",
      assets: overrides.assets ?? [asset({ id: "asset-video" })],
      projectId: "project-1",
      selectedClip: overrides.selectedClip === undefined ? null : overrides.selectedClip,
      timeline: overrides.timeline === undefined ? timeline() : overrides.timeline
    }
  });
}

function buttonByText(wrapper: ReturnType<typeof mount>, text: string) {
  const button = wrapper.findAll("button").find((item) => item.text().includes(text));
  if (!button) throw new Error(`未找到按钮：${text}`);
  return button;
}

function actionButton(wrapper: ReturnType<typeof mount>, cardText: string, actionText: string) {
  const card = wrapper.findAll(".workspace-asset-card").find((item) => item.text().includes(cardText));
  if (!card) throw new Error(`未找到资产卡片：${cardText}`);
  const button = card.findAll("button").find((item) => item.text().includes(actionText));
  if (!button) throw new Error(`未找到资产动作：${actionText}`);
  return button;
}

function timeline(overrides: Partial<WorkspaceTimelineDto> = {}): WorkspaceTimelineDto {
  return {
    id: "timeline-1",
    projectId: "project-1",
    name: "主时间线",
    status: "draft",
    durationSeconds: 12,
    source: "manual",
    tracks: [track("track-video", "video"), track("track-audio", "audio")],
    createdAt: now(),
    updatedAt: now(),
    ...overrides
  };
}

function track(
  id: string,
  kind: WorkspaceTimelineTrackDto["kind"],
  clips: WorkspaceTimelineClipDto[] = [clip({ id: `${id}-clip`, trackId: id })]
): WorkspaceTimelineTrackDto {
  return {
    id,
    kind,
    name: kind === "audio" ? "音频轨" : "视频轨",
    orderIndex: kind === "audio" ? 1 : 0,
    locked: false,
    muted: false,
    clips
  };
}

function clip(overrides: Partial<WorkspaceTimelineClipDto> = {}): WorkspaceTimelineClipDto {
  return {
    id: "clip-video",
    trackId: "track-video",
    sourceType: "manual",
    sourceId: null,
    label: "测试片段",
    startMs: 0,
    durationMs: 5000,
    inPointMs: 0,
    outPointMs: null,
    status: "ready",
    metadata: {
      sourceKind: "manual",
      sourceRevision: null,
      segmentIndex: null,
      segmentId: null,
      text: null,
      visualPrompt: null
    },
    ...overrides
  };
}

function asset(overrides: Partial<AssetDto> = {}): AssetDto {
  const projectId = overrides.projectId === undefined ? "project-1" : overrides.projectId;
  const sourceInfo = overrides.sourceInfo ?? {
    source: "import",
    projectId,
    groupId: null,
    filePath: "G:/assets/test.mp4",
    metadataSummary: {}
  };

  return {
    id: "asset-video",
    name: "测试素材.mp4",
    type: "video",
    source: "local",
    filePath: "G:/assets/test.mp4",
    fileSizeBytes: 1024,
    durationMs: 5000,
    thumbnailPath: null,
    tags: null,
    projectId,
    metadataJson: null,
    sourceInfo,
    availability: {
      status: "ready",
      errorCode: null,
      errorMessage: null,
      nextAction: null
    },
    referenceSummary: {
      total: 0,
      referenceTypes: [],
      blockingDelete: false
    },
    thumbnailStatus: {
      status: "missing",
      path: null,
      generatedAt: null
    },
    createdAt: now(),
    updatedAt: now(),
    ...overrides
  };
}

function assemblyState(): WorkspaceAssemblyStateDto {
  return {
    status: "ready",
    sources: [],
    issues: []
  };
}

function now() {
  return "2026-04-17T10:00:00Z";
}
