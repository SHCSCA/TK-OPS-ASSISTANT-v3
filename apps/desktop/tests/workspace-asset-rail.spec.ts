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

  it("资产 tab 用真实缩略图组件展示视频图片，并为音频显示波形", () => {
    const wrapper = mountRail({
      assets: [
        asset({
          id: "asset-video",
          name: "当前项目视频.mp4",
          thumbnailPath: "G:/assets/thumb-video.jpg"
        }),
        asset({
          id: "asset-image",
          name: "当前项目图片.png",
          type: "image",
          thumbnailPath: "G:/assets/thumb-image.jpg"
        }),
        asset({
          id: "asset-audio",
          name: "当前项目音频.wav",
          type: "audio"
        })
      ]
    });

    expect(wrapper.get('[data-testid="workspace-asset-thumbnail-asset-video"]').find('[data-testid="preview"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="workspace-asset-thumbnail-asset-image"]').find('[data-testid="preview"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="workspace-asset-thumbnail-asset-audio"]').find(".workspace-asset-card__waveform").exists()).toBe(true);
  });

  it("可用资产且存在时间线时点击加入时间线会发出资产入轨事件", async () => {
    const wrapper = mountRail({
      assets: [asset({ id: "asset-video", name: "可入轨视频.mp4", availabilityStatus: "ready" })]
    });

    const insertButton = buttonByText(wrapper, "加入轨道");
    expect(insertButton.element.disabled).toBe(false);

    await insertButton.trigger("click");

    expect(wrapper.emitted("asset-insert")).toEqual([["asset-video"]]);
  });

  it("需转码资产显示检查主操作且不会触发入轨或替换", async () => {
    const wrapper = mountRail({
      assets: [
        asset({
          id: "asset-transcode",
          name: "需转码素材.mov",
          availability: {
            status: "needs_transcode",
            errorCode: "asset.needs_transcode",
            errorMessage: "素材编码需要处理后才能使用。",
            nextAction: null
          }
        })
      ],
      selectedClip: clip({ id: "clip-video", trackId: "track-video" })
    });

    const primaryButton = actionButton(wrapper, "需转码素材.mov", "重新检查");
    expect(primaryButton.element.disabled).toBe(false);
    expect(actionButton(wrapper, "需转码素材.mov", "替换片段").element.disabled).toBe(true);

    await primaryButton.trigger("click");

    expect(wrapper.emitted("sync-assets")).toEqual([[]]);
    expect(wrapper.emitted("asset-insert")).toBeUndefined();
    expect(wrapper.emitted("asset-replace")).toBeUndefined();
  });

  it("路径缺失资产只提示重新检查状态而不承诺重新定位", async () => {
    const wrapper = mountRail({
      assets: [
        asset({
          id: "asset-missing-file",
          name: "路径缺失素材.mp4",
          availability: {
            status: "missing_file",
            errorCode: "asset.file_missing",
            errorMessage: "资产文件已丢失，请重新导入。",
            nextAction: null
          }
        })
      ],
      selectedClip: clip({ id: "clip-video", trackId: "track-video" })
    });

    expect(wrapper.text()).not.toContain("重新定位");
    const primaryButton = actionButton(wrapper, "路径缺失素材.mp4", "重新检查");
    expect(primaryButton.element.disabled).toBe(false);
    expect(actionButton(wrapper, "路径缺失素材.mp4", "替换片段").element.disabled).toBe(true);

    await primaryButton.trigger("click");

    expect(wrapper.emitted("sync-assets")).toEqual([[]]);
    expect(wrapper.emitted("asset-insert")).toBeUndefined();
    expect(wrapper.emitted("asset-replace")).toBeUndefined();
  });

  it("可用资产按资产类型和选中上下文显示加入或替换意图", () => {
    const wrapper = mountRail({
      assets: [
        asset({ id: "asset-video", name: "可入轨视频.mp4", type: "video" }),
        asset({ id: "asset-audio", name: "可入轨音频.wav", type: "audio" }),
        asset({ id: "asset-on-timeline", name: "已入轨视频.mp4", type: "video" })
      ],
      timeline: timeline({
        tracks: [
          track("track-video", "video", [
            clip({ id: "clip-existing", sourceType: "asset", sourceId: "asset-on-timeline", trackId: "track-video" })
          ]),
          track("track-audio", "audio")
        ]
      }),
      selectedClip: clip({ id: "clip-video", trackId: "track-video" })
    });

    expect(actionButton(wrapper, "可入轨视频.mp4", "加入轨道").element.disabled).toBe(false);
    expect(actionButton(wrapper, "可入轨音频.wav", "加入音轨").element.disabled).toBe(false);
    expect(actionButton(wrapper, "已入轨视频.mp4", "加入轨道").element.disabled).toBe(false);
    expect(actionButton(wrapper, "已入轨视频.mp4", "替换片段").element.disabled).toBe(false);
  });

  it("已入轨资产未选中兼容片段时仍可再次加入时间线", async () => {
    const wrapper = mountRail({
      assets: [asset({ id: "asset-on-timeline", name: "已入轨视频.mp4", type: "video" })],
      timeline: timeline({
        tracks: [
          track("track-video", "video", [
            clip({ id: "clip-existing", sourceType: "asset", sourceId: "asset-on-timeline", trackId: "track-video" })
          ])
        ]
      }),
      selectedClip: null
    });

    const insertButton = actionButton(wrapper, "已入轨视频.mp4", "加入轨道");
    expect(insertButton.element.disabled).toBe(false);
    expect(actionButton(wrapper, "已入轨视频.mp4", "替换片段").element.disabled).toBe(true);

    await insertButton.trigger("click");

    expect(wrapper.emitted("asset-insert")).toEqual([["asset-on-timeline"]]);
    expect(wrapper.emitted("asset-replace")).toBeUndefined();
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

  it("不可用资产显示中文原因和恢复主操作", () => {
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
    expect(wrapper.text()).not.toContain("重新定位");
    expect(actionButton(wrapper, "缺失素材.mp4", "重新检查").element.disabled).toBe(false);
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

    expect(wrapper.get('[data-testid="workspace-asset-tab-storyboard"]').attributes("aria-selected")).toBe("true");
    expect(wrapper.get('[data-testid="workspace-asset-tab-assets"]').attributes("aria-selected")).toBe("false");
    expect(wrapper.text()).toContain("S01 · 分镜画面");
    expect(wrapper.text()).not.toContain("暂无项目资产");
    expect(wrapper.get(".workspace-asset-rail__list").classes()).toContain("workspace-asset-rail__list--sources");

    await wrapper.get('[data-testid="workspace-asset-tab-assets"]').trigger("click");
    expect(wrapper.get('[data-testid="workspace-asset-tab-assets"]').attributes("aria-selected")).toBe("true");
    expect(wrapper.text()).toContain("暂无项目资产");
    expect(wrapper.text()).toContain("当前项目还没有可展示资产。");

    await wrapper.get('[data-testid="workspace-asset-tab-storyboard"]').trigger("click");

    await wrapper.get('[data-testid="workspace-asset-tab-voice_track"]').trigger("click");
    expect(wrapper.get('[data-testid="workspace-asset-tab-voice_track"]').attributes("aria-selected")).toBe("true");
    expect(wrapper.text()).toContain("S01 · 配音");

    await wrapper.get('[data-testid="workspace-asset-tab-subtitle_track"]').trigger("click");
    expect(wrapper.get('[data-testid="workspace-asset-tab-subtitle_track"]').attributes("aria-selected")).toBe("true");
    expect(wrapper.text()).toContain("S01 · 字幕");
  });

  it("来源 tab 展示真实片段范围并保持来源点击载荷", async () => {
    const wrapper = mountRail({
      assets: [],
      timeline: timeline({
        durationSeconds: 12,
        tracks: [
          track("managed-video-storyboard", "video", [
            clip({
              id: "clip-storyboard",
              label: "S01 · 分镜画面",
              sourceType: "storyboard",
              trackId: "managed-video-storyboard",
              durationMs: 5000
            })
          ]),
          track("managed-voice-track", "audio", [
            clip({
              id: "clip-voice",
              label: "S01 · 配音",
              sourceType: "voice_track",
              trackId: "managed-voice-track",
              durationMs: 5000
            })
          ]),
          track("managed-subtitle-track", "subtitle", [
            clip({
              id: "clip-subtitle",
              label: "S01 · 字幕",
              sourceType: "subtitle_track",
              trackId: "managed-subtitle-track",
              durationMs: 5000
            })
          ])
        ]
      })
    });

    await wrapper.get('[data-testid="workspace-asset-tab-storyboard"]').trigger("click");
    expect(wrapper.get(".workspace-asset-rail__source-list").text()).toContain("00:00-00:05");
    expect(wrapper.get(".workspace-asset-rail__source-list").text()).not.toContain("00:12");
    await wrapper.get(".workspace-asset-rail__item-card").trigger("click");

    await wrapper.get('[data-testid="workspace-asset-tab-voice_track"]').trigger("click");
    expect(wrapper.get(".workspace-asset-rail__source-list").text()).toContain("00:00-00:05");
    expect(wrapper.get(".workspace-asset-rail__source-list").text()).not.toContain("00:12");
    await wrapper.get(".workspace-asset-rail__item-card").trigger("click");

    await wrapper.get('[data-testid="workspace-asset-tab-subtitle_track"]').trigger("click");
    expect(wrapper.get(".workspace-asset-rail__source-list").text()).toContain("00:00-00:05");
    expect(wrapper.get(".workspace-asset-rail__source-list").text()).not.toContain("00:12");
    await wrapper.get(".workspace-asset-rail__item-card").trigger("click");

    expect(wrapper.emitted("select-source-clip")).toEqual([
      [{ clipId: "clip-storyboard", trackId: "managed-video-storyboard" }],
      [{ clipId: "clip-voice", trackId: "managed-voice-track" }],
      [{ clipId: "clip-subtitle", trackId: "managed-subtitle-track" }]
    ]);
  });

  it("选中时间线片段时素材池自动切到对应来源并高亮同一片段", async () => {
    const testTimeline = timeline({
      tracks: [
        track("managed-video-storyboard", "video", [
          clip({
            id: "clip-storyboard",
            label: "S01 · 分镜画面",
            sourceType: "storyboard",
            trackId: "managed-video-storyboard"
          })
        ]),
        track("managed-audio-voice", "audio", [
          clip({
            id: "clip-voice",
            label: "S01 · 配音",
            sourceType: "voice_track",
            trackId: "managed-audio-voice"
          })
        ]),
        track("managed-subtitle-track", "subtitle", [
          clip({
            id: "clip-subtitle",
            label: "S01 · 字幕",
            sourceType: "subtitle_track",
            trackId: "managed-subtitle-track"
          })
        ])
      ]
    });
    const wrapper = mountRail({
      assets: [],
      timeline: testTimeline,
      selectedClip: clip({
        id: "clip-voice",
        label: "S01 · 配音",
        sourceType: "voice_track",
        trackId: "managed-audio-voice"
      })
    });

    expect(wrapper.get('[data-testid="workspace-asset-tab-voice_track"]').attributes("aria-selected")).toBe("true");
    expect(wrapper.text()).toContain("S01 · 配音");
    expect(wrapper.find(".workspace-asset-rail__item--active").text()).toContain("S01 · 配音");

    await wrapper.setProps({
      selectedClip: clip({
        id: "clip-subtitle",
        label: "S01 · 字幕",
        sourceType: "subtitle_track",
        trackId: "managed-subtitle-track"
      })
    });

    expect(wrapper.get('[data-testid="workspace-asset-tab-subtitle_track"]').attributes("aria-selected")).toBe("true");
    expect(wrapper.text()).toContain("S01 · 字幕");
    expect(wrapper.find(".workspace-asset-rail__item--active").text()).toContain("S01 · 字幕");
  });

  it("用户手动切到资产空态后 Runtime 刷新不会自动跳回来源 tab", async () => {
    const sourceTimeline = timeline({
      tracks: [
        track("managed-video-storyboard", "video", [
          clip({
            id: "clip-storyboard",
            label: "S01 · 分镜画面",
            sourceType: "storyboard",
            trackId: "managed-video-storyboard"
          })
        ])
      ]
    });
    const wrapper = mountRail({
      assets: [],
      timeline: sourceTimeline
    });

    expect(wrapper.get('[data-testid="workspace-asset-tab-storyboard"]').attributes("aria-selected")).toBe("true");

    await wrapper.get('[data-testid="workspace-asset-tab-assets"]').trigger("click");
    expect(wrapper.get('[data-testid="workspace-asset-tab-assets"]').attributes("aria-selected")).toBe("true");

    await wrapper.setProps({
      assets: [],
      timeline: {
        ...sourceTimeline,
        updatedAt: "2026-04-17T10:01:00Z"
      }
    });

    expect(wrapper.get('[data-testid="workspace-asset-tab-assets"]').attributes("aria-selected")).toBe("true");
    expect(wrapper.text()).toContain("当前项目还没有可展示资产。");
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
