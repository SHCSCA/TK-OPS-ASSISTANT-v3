import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import WorkspacePreviewStage from "../src/modules/workspace/WorkspacePreviewStage.vue";
import { buildWorkspacePreviewContext } from "../src/modules/workspace/workspacePreviewContext";
import type { TimelinePreviewDto, WorkspaceTimelineDto } from "../src/types/runtime";

describe("M05 预览舞台", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("没有媒体 URL 时明确标记为分镜预览", () => {
    const timeline = workspaceTimeline([managedVideoTrack()]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: null,
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    expect(wrapper.get('[data-testid="workspace-preview-truth"]').text()).toContain("分镜预览");
    expect(wrapper.text()).toContain("当前片段还没有可播放素材");
    expect(wrapper.get('[data-testid="workspace-preview-canvas"]').attributes("data-ratio")).toBe("9:16");
    expect(wrapper.find(".workspace-preview-stage__safe-area").exists()).toBe(true);
    expect(wrapper.find('[data-testid="workspace-preview-phone"]').exists()).toBe(false);
    expect(wrapper.find(".workspace-preview-stage__facts").exists()).toBe(false);
    expect(wrapper.find('[data-testid="workspace-preview-video"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="workspace-preview-audio"]').exists()).toBe(false);
  });

  it("浅色主题下仍使用深色监看面，避免结构预览接近白屏", () => {
    const source = readFileSync(
      join(process.cwd(), "src/modules/workspace/WorkspacePreviewStage.css"),
      "utf-8"
    );

    expect(source).toContain(':root[data-theme="light"] .workspace-preview-stage');
    expect(source).toMatch(/--workspace-preview-canvas-bg:\s*#[0-9a-fA-F]{6};/);
    expect(source).toMatch(/--workspace-preview-copy:\s*#[0-9a-fA-F]{6};/);
  });

  it("默认使用 TikTok 9:16 大预览舞台并支持切换到 16:9", async () => {
    const timeline = workspaceTimeline([managedVideoTrack()]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: null,
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    expect(wrapper.get('[data-testid="workspace-preview-canvas"]').attributes("data-ratio")).toBe("9:16");
    expect(wrapper.get('[data-testid="workspace-preview-ratio-9-16"]').attributes("aria-pressed")).toBe("true");

    await wrapper.get('[data-testid="workspace-preview-ratio-16-9"]').trigger("click");

    expect(wrapper.get('[data-testid="workspace-preview-canvas"]').attributes("data-ratio")).toBe("16:9");
    expect(wrapper.get('[data-testid="workspace-preview-ratio-16-9"]').attributes("aria-pressed")).toBe("true");
  });

  it("预览舞台样式不再把 9:16 限制成手机窄框", () => {
    const source = readFileSync(
      join(process.cwd(), "src/modules/workspace/WorkspacePreviewStage.css"),
      "utf-8"
    );

    expect(source).toMatch(/\.workspace-preview-stage__viewer\s*{[\s\S]*min-height:\s*clamp\(340px,\s*44vh,\s*620px\);/);
    expect(source).toMatch(/\.workspace-preview-stage__canvas\[data-ratio="9:16"\]\s*{[\s\S]*max-width:\s*min\(100%,\s*560px\);/);
    expect(source).toMatch(/\.workspace-preview-stage__canvas\[data-ratio="16:9"\]\s*{[\s\S]*height:\s*min\(100%,\s*620px\);/);
    expect(source).toMatch(/\.workspace-preview-stage__canvas\[data-ratio="16:9"\]\s*{[\s\S]*width:\s*auto;/);
    expect(source).not.toContain("max-width: min(100%, 420px);");
  });

  it("使用 Runtime 时间线预览契约，不从片段 metadata 猜视频 URL", () => {
    const timeline = workspaceTimeline([
      managedVideoTrack([
        managedClip("managed-video-media-01", "managed-video-storyboard", "asset", "真实视频片段", {
          metadata: {
            sourceKind: "asset",
            sourceRevision: 1,
            segmentIndex: 0,
            segmentId: "S01",
            text: "真实视频预览",
            visualPrompt: "真实视频预览",
            mediaUrl: "http://127.0.0.1:8000/media/preview.mp4"
          },
          status: "ready"
        })
      ])
    ]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: timelinePreview(),
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    expect(wrapper.get('[data-testid="workspace-preview-truth"]').text()).toContain("分镜预览");
    expect(wrapper.text()).toContain("先按分镜和字幕检查节奏");
    expect(previewContext.runtimePreviewUrl).toContain("data:application/json");
    expect(wrapper.find('[data-testid="workspace-preview-video"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="workspace-preview-transport"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="workspace-preview-compact-status"]').text()).toContain("播放头");
  });

  it("结构预览进度条可直接定位播放头", async () => {
    const timeline = workspaceTimeline([managedVideoTrack()]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: null,
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    const scrubber = wrapper.get('[data-testid="workspace-preview-scrubber"]');
    expect(scrubber.attributes("aria-label")).toBe("预览播放头");

    await scrubber.setValue("6500");

    expect(wrapper.emitted("seek")).toEqual([[6500]]);
  });

  it("结构预览展示 Runtime 清单里的轨道和片段摘要", () => {
    const timeline = workspaceTimeline([managedVideoTrack(), managedAudioTrack()]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: timelinePreview({
        manifest: {
          timelineId: "timeline-1",
          timelineName: "主时间线",
          trackCount: 2,
          clipCount: 2,
          totalClipDurationMs: 10000,
          tracks: [
            {
              id: "managed-video-storyboard",
              kind: "video",
              name: "分镜视频轨",
              clipCount: 1,
              clipDurationMs: 5000,
              clips: [
                {
                  id: "managed-video-storyboard-01",
                  label: "S01 · 分镜画面",
                  startMs: 0,
                  durationMs: 5000,
                  status: "pending",
                  sourceType: "storyboard"
                }
              ]
            },
            {
              id: "managed-audio-voice",
              kind: "audio",
              name: "配音轨",
              clipCount: 1,
              clipDurationMs: 5000,
              clips: [
                {
                  id: "managed-audio-voice-01",
                  label: "S01 · 配音",
                  startMs: 0,
                  durationMs: 5000,
                  status: "ready",
                  sourceType: "voice_track"
                }
              ]
            }
          ]
        }
      }),
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    const summary = wrapper.get('[data-testid="workspace-preview-manifest-summary"]');
    const rows = wrapper.findAll('[data-testid="workspace-preview-manifest-track"]');

    expect(summary.text()).toContain("2 条轨道");
    expect(summary.text()).toContain("2 个片段");
    expect(summary.text()).toContain("00:05");
    expect(rows.map((row) => row.text())).toEqual([
      "分镜视频轨 视频轨 1 个片段 00:05",
      "配音轨 音频轨 1 个片段 00:05"
    ]);
  });

  it("结构预览清单总时长按并行轨道最大结束点计算，不累加轨道时长", () => {
    const timeline = workspaceTimeline([managedVideoTrack(), managedSubtitleTrack()]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: timelinePreview({
        manifest: {
          timelineId: "timeline-1",
          timelineName: "主时间线",
          trackCount: 2,
          clipCount: 6,
          totalClipDurationMs: 24000,
          tracks: [
            manifestTrack("managed-video-storyboard", "video", "分镜视频轨"),
            manifestTrack("managed-subtitle-track", "subtitle", "字幕轨")
          ]
        }
      }),
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    const summary = wrapper.get('[data-testid="workspace-preview-manifest-summary"]');

    expect(previewContext.manifestSummary?.summaryText).toBe("2 条轨道 · 6 个片段 · 00:12");
    expect(summary.text()).toContain("2 条轨道");
    expect(summary.text()).toContain("6 个片段");
    expect(summary.text()).toContain("00:12");
    expect(summary.text()).not.toContain("00:24");
  });

  it("结构预览清单总时长支持非零起点的最大结束点", () => {
    const timeline = workspaceTimeline([managedVideoTrack(), managedSubtitleTrack()]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: timelinePreview({
        manifest: {
          timelineId: "timeline-1",
          timelineName: "主时间线",
          durationSeconds: 20,
          trackCount: 2,
          clipCount: 2,
          totalClipDurationMs: 14000,
          tracks: [
            {
              id: "managed-video-storyboard",
              kind: "video",
              name: "分镜视频轨",
              clipCount: 1,
              clipDurationMs: 4000,
              clips: [{ id: "video-offset", startMs: 8000, durationMs: 4000 }]
            },
            {
              id: "managed-subtitle-track",
              kind: "subtitle",
              name: "字幕轨",
              clipCount: 1,
              clipDurationMs: 6000,
              clips: [{ id: "subtitle-offset", startMs: 8000, durationMs: 6000 }]
            }
          ]
        }
      }),
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    expect(previewContext.manifestSummary?.summaryText).toBe("2 条轨道 · 2 个片段 · 00:14");
  });

  it("结构预览清单为空时不使用声明时长伪造片段总时长", () => {
    const timeline = workspaceTimeline([]);
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: timelinePreview({
        manifest: {
          timelineId: "timeline-1",
          timelineName: "主时间线",
          durationSeconds: 12,
          trackCount: 1,
          clipCount: 0,
          totalClipDurationMs: 0,
          tracks: [
            {
              id: "managed-video-storyboard",
              kind: "video",
              name: "分镜视频轨",
              clipCount: 0,
              clipDurationMs: 0,
              clips: []
            }
          ]
        }
      }),
      timelinePreviewErrorMessage: null,
      selectedClip: null,
      selectedTrack: null,
      timeline
    });

    expect(previewContext.manifestSummary?.summaryText).toBe("1 条轨道 · 0 个片段 · 00:00");
  });

  it("结构预览支持 Runtime base64 清单", () => {
    const timeline = workspaceTimeline([
      managedVideoTrack([
        managedClip("managed-video-asset-01", "managed-video-storyboard", "asset", "真实视频片段", {
          sourceId: "asset-video-1",
          status: "ready"
        })
      ])
    ]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: timelinePreview({
        manifest: {
          timelineId: "timeline-1",
          trackCount: 1,
          clipCount: 1,
          totalClipDurationMs: 5000,
          tracks: [
            {
              id: "managed-video-storyboard",
              kind: "video",
              name: "分镜视频轨",
              clipCount: 1,
              clipDurationMs: 5000,
              clips: []
            }
          ]
        },
        useBase64Manifest: true
      }),
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    expect(previewContext.manifestSummary?.summaryText).toBe("1 条轨道 · 1 个片段 · 00:05");
    expect(previewContext.manifestSummary?.tracks[0].name).toBe("分镜视频轨");
    expect(previewContext.runtimePreviewErrorMessage).toBeNull();
  });

  it("结构预览清单格式异常时显示 Runtime 错误与重试入口", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const timeline = workspaceTimeline([managedVideoTrack()]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: {
        timelineId: "timeline-1",
        status: "ready",
        message: "时间线本地预览已生成。",
        previewMode: "manifest",
        previewUrl: "data:application/json;charset=utf-8,%7Bbroken",
        media: null,
        error: null
      },
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    expect(previewContext.manifestSummary).toBeNull();
    expect(previewContext.runtimePreviewErrorMessage).toBe("Runtime 预览清单格式异常，请重新同步预览。");
    expect(consoleError).toHaveBeenCalledWith("[workspace-preview] 解析 Runtime 预览清单失败", expect.any(Error));
    expect(wrapper.get('[data-testid="workspace-preview-runtime-error"]').text()).toContain(
      "Runtime 预览清单格式异常"
    );

    await wrapper.get('[data-testid="workspace-preview-retry"]').trigger("click");

    expect(wrapper.emitted("retry-preview")).toHaveLength(1);
  });

  it("同步失败时在预览舞台提供重试入口", async () => {
    const timeline = workspaceTimeline([managedVideoTrack()]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: {
        timelineId: "timeline-1",
        status: "error",
        message: "预览同步失败",
        previewMode: "manifest",
        previewUrl: null,
        media: null,
        error: {
          code: "preview.sync_failed",
          message: "Runtime 时间线清单读取失败，请稍后重试。"
        }
      },
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    expect(previewContext.runtimePreviewErrorMessage).toBe("Runtime 时间线清单读取失败，请稍后重试。");
    expect(wrapper.get('[data-testid="workspace-preview-runtime-error"]').text()).toContain("Runtime 预览同步失败");
    expect(wrapper.get('[data-testid="workspace-preview-runtime-error"]').text()).toContain("Runtime 时间线清单读取失败");

    await wrapper.get('[data-testid="workspace-preview-retry"]').trigger("click");

    expect(wrapper.emitted("retry-preview")).toHaveLength(1);
  });

  it("媒体不可用时仍解析 Runtime manifest 摘要并提供重试入口", async () => {
    const timeline = workspaceTimeline([managedVideoTrack()]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: timelinePreview({
        status: "unavailable",
        message: "时间线包含资产片段，但源文件不可用，已保留结构预览。",
        previewMode: "unavailable",
        manifest: {
          timelineId: "timeline-1",
          timelineName: "主时间线",
          trackCount: 1,
          clipCount: 1,
          totalClipDurationMs: 5000,
          tracks: [
            {
              id: "managed-video-storyboard",
              kind: "video",
              name: "分镜视频轨",
              clipCount: 1,
              clipDurationMs: 5000,
              clips: [{ id: "managed-video-storyboard-01", startMs: 0, durationMs: 5000 }]
            }
          ]
        },
        media: null,
        error: {
          code: "preview.asset_file_missing",
          message: "时间线包含资产片段，但源文件不可用，已保留结构预览。"
        }
      }),
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    expect(previewContext.previewMode).toBe("unavailable");
    expect(previewContext.manifestSummary?.summaryText).toBe("1 条轨道 · 1 个片段 · 00:05");
    expect(wrapper.get('[data-testid="workspace-preview-manifest-summary"]').text()).toContain("1 条轨道");
    expect(wrapper.get('[data-testid="workspace-preview-runtime-error"]').text()).toContain("媒体预览不可用");
    expect(wrapper.get('[data-testid="workspace-preview-runtime-error"]').text()).toContain("源文件不可用");

    await wrapper.get('[data-testid="workspace-preview-retry"]').trigger("click");

    expect(wrapper.emitted("retry-preview")).toHaveLength(1);
  });

  it("只在 Runtime 明确返回 media 契约时播放真实视频", () => {
    const timeline = workspaceTimeline([
      managedVideoTrack([
        managedClip("managed-video-asset-01", "managed-video-storyboard", "asset", "真实视频片段", {
          sourceId: "asset-video-1",
          status: "ready"
        })
      ])
    ]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: {
        timelineId: "timeline-1",
        status: "ready",
        message: "真实媒体预览已准备",
        previewMode: "media",
        previewUrl: "data:application/json;charset=utf-8,%7B%7D",
        media: {
          kind: "video",
          url: "/api/assets/asset-video-1/media?token=preview-token",
          source: "asset:asset-video-1",
          mimeType: "video/mp4",
          durationMs: 1800
        },
        error: null
      },
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    expect(previewContext.runtimePreviewUrl).toBeNull();
    expect(previewContext.previewMode).toBe("media");
    expect(previewContext.mediaKind).toBe("video");
    expect(previewContext.mediaUrl).toBe(
      "http://127.0.0.1:8000/api/assets/asset-video-1/media?token=preview-token"
    );
    expect(wrapper.get('[data-testid="workspace-preview-truth"]').text()).toContain("素材预览");
    expect(wrapper.get('[data-testid="workspace-preview-video"]').attributes("src")).toBe(
      "http://127.0.0.1:8000/api/assets/asset-video-1/media?token=preview-token"
    );
    expect(wrapper.get('[data-testid="workspace-preview-media-note"]').text()).toContain("video/mp4");
    expect(wrapper.get('[data-testid="workspace-preview-media-note"]').text()).toContain("00:01");
    expect(wrapper.find('[data-testid="workspace-preview-audio"]').exists()).toBe(false);
  });

  it("Runtime 返回的媒体不属于当前片段时回退结构预览", () => {
    const timeline = workspaceTimeline([
      managedVideoTrack([
        managedClip("managed-video-asset-02", "managed-video-storyboard", "asset", "第二个视频片段", {
          sourceId: "asset-video-2",
          status: "ready"
        })
      ])
    ]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: {
        timelineId: "timeline-1",
        status: "ready",
        message: "真实媒体预览已准备",
        previewMode: "media",
        previewUrl: "data:application/json;charset=utf-8,%7B%7D",
        media: {
          kind: "video",
          url: "/api/assets/asset-video-1/media?token=preview-token",
          source: "asset:asset-video-1",
          mimeType: "video/mp4",
          durationMs: 1800
        },
        error: null
      },
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    expect(previewContext.previewMode).toBe("structure");
    expect(previewContext.mediaUrl).toBeNull();
    expect(wrapper.find('[data-testid="workspace-preview-video"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="workspace-preview-truth"]').text()).toContain("分镜预览");
  });

  it("只在 Runtime 明确返回 media 契约时播放真实音频", () => {
    const timeline = workspaceTimeline([
      {
        ...managedAudioTrack(),
        clips: [
          managedClip("managed-audio-asset-01", "managed-audio-voice", "asset", "真实音频片段", {
            sourceId: "asset-audio-1",
            status: "ready"
          })
        ]
      }
    ]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: {
        timelineId: "timeline-1",
        status: "ready",
        message: "真实音频预览已准备",
        previewMode: "media",
        previewUrl: "data:application/json;charset=utf-8,%7B%7D",
        media: {
          kind: "audio",
          url: "/api/assets/asset-audio-1/media?token=preview-token",
          source: "asset:asset-audio-1",
          mimeType: "audio/mpeg",
          durationMs: 2400
        },
        error: null
      },
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    expect(previewContext.previewMode).toBe("media");
    expect(previewContext.mediaKind).toBe("audio");
    expect(wrapper.get('[data-testid="workspace-preview-truth"]').text()).toContain("素材预览");
    expect(wrapper.get('[data-testid="workspace-preview-audio"]').attributes("src")).toBe(
      "http://127.0.0.1:8000/api/assets/asset-audio-1/media?token=preview-token"
    );
    expect(wrapper.get('[data-testid="workspace-preview-media-note"]').text()).toContain("audio/mpeg");
    expect(wrapper.get('[data-testid="workspace-preview-media-note"]').text()).toContain("00:02");
    expect(wrapper.find('[data-testid="workspace-preview-video"]').exists()).toBe(false);
  });

  it("Runtime media 契约缺少 MIME 或时长字段时不渲染真实播放器", () => {
    const timeline = workspaceTimeline([managedVideoTrack()]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: {
        timelineId: "timeline-1",
        status: "ready",
        message: "真实媒体预览字段不完整",
        previewMode: "media",
        previewUrl: "data:application/json;charset=utf-8,%7B%7D",
        media: {
          kind: "video",
          url: "/api/assets/asset-video-1/media?token=preview-token",
          source: "asset:asset-video-1",
          mimeType: ""
        } as never,
        error: null
      },
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    expect(previewContext.previewMode).toBe("structure");
    expect(previewContext.mediaUrl).toBeNull();
    expect(wrapper.find('[data-testid="workspace-preview-video"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="workspace-preview-audio"]').exists()).toBe(false);
  });

  it("不会把未声明的 metadata.mediaUrl 当作真实音频链路", () => {
    const timeline = workspaceTimeline([
      {
        ...managedAudioTrack(),
        clips: [
          managedClip("managed-audio-media-01", "managed-audio-voice", "voice_track", "真实配音片段", {
            metadata: {
              sourceKind: "voice_track",
              sourceRevision: 1,
              segmentIndex: 0,
              segmentId: "S01",
              text: "音频素材预览",
              visualPrompt: null,
              mediaUrl: "http://127.0.0.1:8000/media/voice.mp3"
            },
            status: "ready"
          })
        ]
      }
    ]);
    const track = timeline.tracks[0];
    const clip = track.clips[0];
    const previewContext = buildWorkspacePreviewContext({
      playheadMs: 0,
      timelinePreview: timelinePreview(),
      timelinePreviewErrorMessage: null,
      selectedClip: clip,
      selectedTrack: track,
      timeline
    });

    const wrapper = mount(WorkspacePreviewStage, {
      props: {
        previewContext,
        timeline
      }
    });

    expect(wrapper.text()).toContain("音频状态：配音片段");
    expect(wrapper.text()).toContain("先按分镜和字幕检查节奏");
    expect(wrapper.find('[data-testid="workspace-preview-audio"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="workspace-preview-video"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="workspace-preview-transport"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="workspace-preview-compact-status"]').text()).toContain("播放头");
  });
});

function workspaceTimeline(tracks = [managedVideoTrack()]): WorkspaceTimelineDto {
  return {
    id: "timeline-1",
    projectId: "project-1",
    name: "主时间线",
    status: "draft",
    durationSeconds: 12,
    source: "manual",
    tracks,
    createdAt: now(),
    updatedAt: now()
  };
}

function managedVideoTrack(clips = [
  managedClip("managed-video-storyboard-01", "managed-video-storyboard", "storyboard", "S01 · 分镜画面")
]) {
  return {
    id: "managed-video-storyboard",
    kind: "video",
    name: "分镜视频轨",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips
  };
}

function managedAudioTrack() {
  return {
    id: "managed-audio-voice",
    kind: "audio",
    name: "配音轨",
    orderIndex: 1,
    locked: false,
    muted: false,
    clips: [
      managedClip("managed-audio-voice-01", "managed-audio-voice", "voice_track", "S01 · 配音")
    ]
  };
}

function managedSubtitleTrack() {
  return {
    id: "managed-subtitle-track",
    kind: "subtitle",
    name: "字幕轨",
    orderIndex: 1,
    locked: false,
    muted: false,
    clips: [
      managedClip("managed-subtitle-track-01", "managed-subtitle-track", "subtitle_track", "S01 · 字幕")
    ]
  };
}

function manifestTrack(id: string, kind: string, name: string) {
  return {
    id,
    kind,
    name,
    clipCount: 3,
    clipDurationMs: 12000,
    clips: [
      { id: `${id}-01`, startMs: 0, durationMs: 4000 },
      { id: `${id}-02`, startMs: 4000, durationMs: 4000 },
      { id: `${id}-03`, startMs: 8000, durationMs: 4000 }
    ]
  };
}

function managedClip(
  id: string,
  trackId: string,
  sourceType: string,
  label: string,
  overrides: Partial<{
    durationMs: number;
    metadata: Record<string, unknown>;
    status: string;
    sourceId: string;
  }> = {}
) {
  return {
    id,
    trackId,
    sourceType,
    sourceId: overrides.sourceId ?? `${sourceType}-1`,
    label,
    startMs: 0,
    durationMs: overrides.durationMs ?? 5000,
    inPointMs: 0,
    outPointMs: null,
    status: overrides.status ?? (sourceType === "storyboard" ? "pending" : "ready"),
    metadata: overrides.metadata ?? {
      sourceKind: sourceType,
      sourceRevision: 1,
      segmentIndex: 0,
      segmentId: "S01",
      text: "This lamp made me cancel my dinner plan.",
      visualPrompt: "墙灯亮起，房间从冷光转暖光。"
    }
  };
}

function timelinePreview(
  options: Partial<TimelinePreviewDto> & {
    manifest?: Record<string, unknown>;
    useBase64Manifest?: boolean;
  } = {}
): TimelinePreviewDto {
  const { manifest, useBase64Manifest, ...overrides } = options;
  return {
    timelineId: "timeline-1",
    status: "ready",
    message: "时间线本地预览已生成，包含真实轨道与片段摘要。",
    previewUrl: encodeManifestDataUrl(manifest ?? { timelineId: "timeline-1" }, Boolean(useBase64Manifest)),
    previewMode: "manifest",
    media: null,
    error: null,
    ...overrides
  };
}

function encodeManifestDataUrl(payload: Record<string, unknown>, useBase64 = false): string {
  const json = JSON.stringify(payload);
  if (useBase64) return `data:application/json;base64,${Buffer.from(json, "utf-8").toString("base64")}`;
  return `data:application/json;charset=utf-8,${encodeURIComponent(json)}`;
}

function now() {
  return "2026-04-17T10:00:00Z";
}
