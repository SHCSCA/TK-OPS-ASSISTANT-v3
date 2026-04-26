import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createRouteAwareFetch,
  mountApp,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

describe("Video deconstruction center", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it("loads imported videos for the current project and renders metadata cards", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path) => {
        if (path === "/api/license/status") {
          return okJsonResponse(runtimeFixtures.activeLicense);
        }
        if (path === "/api/settings/health") {
          return okJsonResponse(runtimeFixtures.health);
        }
        if (path === "/api/settings/config") {
          return okJsonResponse(runtimeFixtures.initializedConfig);
        }
        if (path === "/api/settings/diagnostics") {
          return okJsonResponse(runtimeFixtures.initializedDiagnostics);
        }
        if (path === "/api/settings/diagnostics/media") {
          return okJsonResponse({
            ffprobe: {
              status: "ready",
              path: "C:/tools/ffprobe.exe",
              source: "config",
              version: "ffprobe version test",
              errorCode: null,
              errorMessage: null
            },
            checkedAt: "2026-04-25T13:00:00Z"
          });
        }
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-video",
              projectName: "Video Project",
              status: "active"
            }
          });
        }
        if (path === "/api/video-deconstruction/projects/project-video/videos") {
          return okJsonResponse([
            {
              id: "video-1",
              projectId: "project-video",
              filePath: "C:/media/source.mp4",
              fileName: "source.mp4",
              fileSizeBytes: 4096,
              durationSeconds: 62.4,
              width: 1920,
              height: 1080,
              frameRate: 30,
              codec: "h264",
              status: "ready",
              errorMessage: null,
              createdAt: "2026-04-13T00:00:00Z"
            }
          ]);
        }

        throw new Error(`Unhandled request: ${path}`);
      })
    );

    const { wrapper } = await mountApp("/video/deconstruction");
    await flushPromises();
    await flushPromises();

    expect(wrapper.find('[data-video-page="deconstruction"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("source.mp4");
    expect(wrapper.text()).toContain("1920");
    expect(wrapper.text()).toContain("1080");
    expect(wrapper.find('[data-action="import-video"]').exists()).toBe(true);
  });

  it("routes video import task updates through TaskBus", async () => {
    vi.resetModules();

    const connect = vi.fn();
    const subscribe = vi.fn(() => vi.fn());
    const taskBus = {
      connect,
      subscribe,
      tasks: new Map()
    };
    const importedVideo = {
      id: "video-task-1",
      projectId: "project-video",
      filePath: "C:/media/task.mp4",
      fileName: "task.mp4",
      fileSizeBytes: 2048,
      durationSeconds: null,
      width: null,
      height: null,
      frameRate: null,
      codec: null,
      status: "imported",
      errorMessage: null,
      createdAt: "2026-04-13T00:00:00Z"
    };
    const importVideo = vi.fn(async () => importedVideo);
    const fetchImportedVideos = vi.fn(async () => [importedVideo]);

    vi.doMock("@/stores/task-bus", () => ({
      useTaskBusStore: () => taskBus
    }));
    vi.doMock("@/app/runtime-client", () => ({
      RuntimeRequestError: class RuntimeRequestError extends Error {
        details = null;
        requestId = undefined;
        status = undefined;
      },
      deleteImportedVideo: vi.fn(),
      fetchImportedVideos,
      importVideo
    }));

    const { useVideoImportStore } = await import("@/stores/video-import");
    setActivePinia(createPinia());
    const store = useVideoImportStore();

    store.initializeWebSocket();
    const video = await store.importVideoFile("project-video", "C:/media/task.mp4");

    expect(video?.id).toBe("video-task-1");
    expect(connect).toHaveBeenCalledTimes(1);
    expect(subscribe).toHaveBeenCalledWith("video-task-1", expect.any(Function));

    const taskCallback = subscribe.mock.calls[0][1];
    taskCallback({
      schema_version: 1,
      type: "task.completed",
      taskId: "video-task-1",
      taskType: "video_import",
      projectId: "project-video",
      status: "succeeded",
      progress: 100,
      message: "任务已完成"
    });
    await flushPromises();

    expect(fetchImportedVideos).toHaveBeenCalledWith("project-video");
  });

  it("routes video import stage events through TaskBus", async () => {
    vi.resetModules();

    const connect = vi.fn();
    const subscribe = vi.fn(() => vi.fn());
    const taskBus = {
      connect,
      subscribe,
      tasks: new Map(),
      lastEvents: new Map()
    };
    const importedVideo = {
      id: "video-task-2",
      projectId: "project-video",
      filePath: "C:/media/stage.mp4",
      fileName: "stage.mp4",
      fileSizeBytes: 2048,
      durationSeconds: null,
      width: null,
      height: null,
      frameRate: null,
      codec: null,
      status: "imported",
      errorMessage: null,
      createdAt: "2026-04-13T00:00:00Z"
    };
    const importVideo = vi.fn(async () => importedVideo);
    const fetchImportedVideos = vi.fn(async () => [importedVideo]);

    vi.doMock("@/stores/task-bus", () => ({
      useTaskBusStore: () => taskBus
    }));
    vi.doMock("@/app/runtime-client", () => ({
      RuntimeRequestError: class RuntimeRequestError extends Error {
        details = null;
        requestId = undefined;
        status = undefined;
      },
      deleteImportedVideo: vi.fn(),
      fetchImportedVideos,
      importVideo
    }));

    const { useVideoImportStore } = await import("@/stores/video-import");
    setActivePinia(createPinia());
    const store = useVideoImportStore();

    await store.importVideoFile("project-video", "C:/media/stage.mp4");
    const eventCallback = subscribe.mock.calls[0][1];

    eventCallback({
      schema_version: 1,
      type: "video.import.stage.completed",
      videoId: "video-task-2",
      stage: "extract_structure",
      resultSummary: "结构抽取完成"
    });
    await flushPromises();

    expect(fetchImportedVideos).toHaveBeenCalledWith("project-video");
  });

  it("exposes TaskBus progress for imported videos through the store", async () => {
    vi.resetModules();
    vi.doMock("@/components/common/ProjectContextGuard.vue", () => ({
      default: {
        template: "<slot />"
      }
    }));
    vi.doMock("@/app/runtime-client", () => ({
      fetchRuntimeMediaDiagnostics: vi.fn(async () => ({
        ffprobe: {
          status: "ready",
          path: "C:/tools/ffprobe.exe",
          source: "config",
          version: "ffprobe version test",
          errorCode: null,
          errorMessage: null
        },
        checkedAt: "2026-04-25T13:00:00Z"
      }))
    }));
    vi.stubGlobal(
      "WebSocket",
      class {
        static OPEN = 1;
        readyState = 1;
        onopen: (() => void) | null = null;
        constructor() {
          setTimeout(() => this.onopen?.(), 0);
        }
        close() {}
        send() {}
      }
    );

    const pinia = createPinia();
    setActivePinia(pinia);
    const { default: VideoDeconstructionCenterPage } = await import(
      "@/pages/video/VideoDeconstructionCenterPage.vue"
    );
    const { useProjectStore } = await import("@/stores/project");
    const { useTaskBusStore } = await import("@/stores/task-bus");
    const { useVideoImportStore } = await import("@/stores/video-import");

    useProjectStore().currentProject = {
      projectId: "project-video",
      projectName: "Video Project",
      status: "active"
    };
    useVideoImportStore().videos = [
      {
        id: "video-task-1",
        projectId: "project-video",
        filePath: "C:/media/task.mp4",
        fileName: "task.mp4",
        fileSizeBytes: 2048,
        durationSeconds: null,
        width: null,
        height: null,
        frameRate: null,
        codec: null,
        status: "imported",
        errorMessage: null,
        createdAt: "2026-04-13T00:00:00Z"
      }
    ];
    useTaskBusStore().tasks.set("video-task-1", {
      id: "video-task-1",
      task_type: "video_import",
      project_id: "project-video",
      status: "running",
      progress: 40,
      message: "正在解析视频元信息",
      created_at: "2026-04-13T00:00:00Z",
      updated_at: "2026-04-13T00:00:01Z"
    });

    const wrapper = mount(VideoDeconstructionCenterPage, {
      global: {
        plugins: [pinia]
      }
    });

    await flushPromises();

    expect(useVideoImportStore().taskForVideo("video-task-1")).toEqual(
      expect.objectContaining({
        id: "video-task-1",
        progress: 40,
        message: "正在解析视频元信息",
        status: "running"
      })
    );
    expect(wrapper.find('[data-video-page="deconstruction"]').exists()).toBe(true);
  });

  it("falls back to a file selector instead of a manual path prompt", async () => {
    vi.resetModules();
    vi.doMock("@/components/common/ProjectContextGuard.vue", () => ({
      default: {
        template: "<slot />"
      }
    }));
    vi.doMock("@/app/runtime-client", () => ({
      RuntimeRequestError: class RuntimeRequestError extends Error {
        details = null;
        requestId = undefined;
        status = undefined;
      },
      applyVideoExtractionToProject: vi.fn(),
      deleteImportedVideo: vi.fn(),
      fetchImportedVideos: vi.fn(async () => []),
      fetchRuntimeMediaDiagnostics: vi.fn(async () => ({
        ffprobe: {
          status: "ready",
          path: "C:/tools/ffprobe.exe",
          source: "config",
          version: "ffprobe version test",
          errorCode: null,
          errorMessage: null
        },
        checkedAt: "2026-04-25T13:00:00Z"
      })),
      fetchVideoSegments: vi.fn(async () => []),
      fetchVideoResult: vi.fn(async () => {
        throw new Error("legacy result unavailable");
      }),
      fetchVideoStages: vi.fn(async () => []),
      fetchVideoStructure: vi.fn(async () => ({
        id: "extraction-video-ready",
        videoId: "video-ready",
        status: "pending",
        scriptJson: null,
        storyboardJson: null,
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      })),
      fetchVideoTranscript: vi.fn(async () => ({
        id: "transcript-video-ready",
        videoId: "video-ready",
        language: null,
        text: null,
        status: "pending",
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      })),
      importVideo: vi.fn(),
      rerunVideoStage: vi.fn()
    }));
    vi.stubGlobal(
      "WebSocket",
      class {
        static OPEN = 1;
        readyState = 1;
        onopen: (() => void) | null = null;
        constructor() {
          setTimeout(() => this.onopen?.(), 0);
        }
        close() {}
        send() {}
      }
    );
    const promptSpy = vi.fn();
    const clickSpy = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => {});
    vi.stubGlobal("prompt", promptSpy);

    const pinia = createPinia();
    setActivePinia(pinia);
    const { default: VideoDeconstructionCenterPage } = await import(
      "@/pages/video/VideoDeconstructionCenterPage.vue"
    );
    const { useProjectStore } = await import("@/stores/project");

    useProjectStore().currentProject = {
      projectId: "project-video",
      projectName: "Video Project",
      status: "active"
    };

    const wrapper = mount(VideoDeconstructionCenterPage, {
      global: {
        plugins: [pinia]
      }
    });

    await flushPromises();
    await wrapper.find('[data-action="import-video"]').trigger("click");
    await vi.waitFor(() => {
      expect(clickSpy).toHaveBeenCalledTimes(1);
    });

    expect(promptSpy).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid="video-file-picker"]').exists()).toBe(true);
  });

  it("imports the full local path returned by the native desktop file selector", async () => {
    vi.resetModules();
    vi.doMock("@/components/common/ProjectContextGuard.vue", () => ({
      default: {
        template: "<slot />"
      }
    }));
    const importVideoSpy = vi.fn(async () => ({
      id: "video-native",
      projectId: "project-video",
      filePath: "C:/media/native.mp4",
      fileName: "native.mp4",
      fileSizeBytes: 4096,
      durationSeconds: null,
      width: null,
      height: null,
      frameRate: null,
      codec: null,
      status: "imported",
      errorMessage: null,
      createdAt: "2026-04-26T00:00:00Z"
    }));
    vi.doMock("@tauri-apps/plugin-dialog", () => ({
      open: vi.fn(async () => "C:/media/native.mp4")
    }));
    vi.doMock("@/app/runtime-client", () => ({
      RuntimeRequestError: class RuntimeRequestError extends Error {
        details = null;
        requestId = undefined;
        status = undefined;
      },
      applyVideoExtractionToProject: vi.fn(),
      deleteImportedVideo: vi.fn(),
      fetchImportedVideos: vi.fn(async () => []),
      fetchRuntimeMediaDiagnostics: vi.fn(async () => ({
        ffprobe: {
          status: "ready",
          path: "C:/tools/ffprobe.exe",
          source: "config",
          version: "ffprobe version test",
          errorCode: null,
          errorMessage: null
        },
        checkedAt: "2026-04-26T00:00:00Z"
      })),
      fetchVideoResult: vi.fn(async () => {
        throw new Error("legacy result unavailable");
      }),
      fetchVideoStages: vi.fn(async () => []),
      importVideo: importVideoSpy,
      rerunVideoStage: vi.fn()
    }));
    vi.stubGlobal(
      "WebSocket",
      class {
        static OPEN = 1;
        readyState = 1;
        onopen: (() => void) | null = null;
        constructor() {
          setTimeout(() => this.onopen?.(), 0);
        }
        close() {}
        send() {}
      }
    );

    const pinia = createPinia();
    setActivePinia(pinia);
    const { default: VideoDeconstructionCenterPage } = await import(
      "@/pages/video/VideoDeconstructionCenterPage.vue"
    );
    const { useProjectStore } = await import("@/stores/project");

    useProjectStore().currentProject = {
      projectId: "project-video",
      projectName: "Video Project",
      status: "active"
    };

    const wrapper = mount(VideoDeconstructionCenterPage, {
      global: {
        plugins: [pinia]
      }
    });

    await flushPromises();
    await wrapper.find('[data-action="import-video"]').trigger("click");
    await flushPromises();

    expect(importVideoSpy).toHaveBeenCalledWith("project-video", "C:/media/native.mp4");
    expect(wrapper.text()).not.toContain("没有返回完整本地路径");
  });

  it("runs one-click deconstruction and renders result tabs", async () => {
    vi.resetModules();
    vi.doMock("@/components/common/ProjectContextGuard.vue", () => ({
      default: {
        template: "<slot />"
      }
    }));
    const deconstructVideoSpy = vi.fn(async () => ({
      videoId: "video-ready",
      transcript: {
        id: "transcript-video-ready",
        videoId: "video-ready",
        language: "zh",
          text: null,
          status: "skipped",
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      },
      segments: [
        {
          id: "segment-video-ready-1",
          videoId: "video-ready",
          segmentIndex: 1,
          startMs: 0,
          endMs: 7000,
          label: "开头钩子",
          transcriptText: "This cup stays cold all day.",
          metadataJson: JSON.stringify({ visual: "手持冰霸杯特写", intent: "开头钩子" }),
          createdAt: "2026-04-26T00:00:00Z"
        }
      ],
      structure: {
        id: "extraction-video-ready",
        videoId: "video-ready",
        status: "succeeded",
        scriptJson: JSON.stringify({
          summary: { fileName: "ready.mp4" },
          segments: [{ label: "开头钩子", transcriptText: "This cup stays cold all day." }]
        }),
        storyboardJson: "{}",
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      },
      stages: [
        {
          stageId: "segment",
          label: "分段",
          status: "succeeded",
          progressPct: 100,
          resultSummary: "已生成 1 个画面语音对齐片段",
          errorMessage: null,
          errorCode: null,
          nextAction: null,
          blockedByStageId: null,
          updatedAt: "2026-04-26T00:00:00Z",
          isCurrent: false,
          activeTaskId: null,
          activeTaskStatus: null,
          activeTaskProgress: null,
          activeTaskMessage: null,
          canCancel: false,
          canRetry: false,
          canRerun: true
        }
      ]
    }));
    vi.doMock("@/app/runtime-client", () => ({
      RuntimeRequestError: class RuntimeRequestError extends Error {
        details = null;
        requestId = undefined;
        status = undefined;
      },
      applyVideoExtractionToProject: vi.fn(),
      deconstructVideo: deconstructVideoSpy,
      deleteImportedVideo: vi.fn(),
      fetchImportedVideos: vi.fn(async () => []),
      fetchRuntimeMediaDiagnostics: vi.fn(async () => ({
        ffprobe: {
          status: "ready",
          path: "C:/tools/ffprobe.exe",
          source: "config",
          version: "ffprobe version test",
          errorCode: null,
          errorMessage: null
        },
        checkedAt: "2026-04-26T00:00:00Z"
      })),
      fetchVideoResult: vi.fn(async () => {
        throw new Error("legacy result unavailable");
      }),
      fetchVideoStages: vi.fn(async () => []),
      fetchVideoSegments: vi.fn(async () => []),
      fetchVideoStructure: vi.fn(async () => ({
        id: "extraction-video-ready",
        videoId: "video-ready",
        status: "pending",
        scriptJson: null,
        storyboardJson: null,
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      })),
      fetchVideoTranscript: vi.fn(async () => ({
        id: "transcript-video-ready",
        videoId: "video-ready",
        language: null,
        text: null,
        status: "pending",
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      })),
      importVideo: vi.fn(),
      rerunVideoStage: vi.fn()
    }));
    vi.stubGlobal(
      "WebSocket",
      class {
        static OPEN = 1;
        readyState = 1;
        onopen: (() => void) | null = null;
        constructor() {
          setTimeout(() => this.onopen?.(), 0);
        }
        close() {}
        send() {}
      }
    );

    const pinia = createPinia();
    setActivePinia(pinia);
    const { default: VideoDeconstructionCenterPage } = await import(
      "@/pages/video/VideoDeconstructionCenterPage.vue"
    );
    const { useProjectStore } = await import("@/stores/project");
    const { useVideoImportStore } = await import("@/stores/video-import");

    useProjectStore().currentProject = {
      projectId: "project-video",
      projectName: "Video Project",
      status: "active"
    };
    useVideoImportStore().videos = [
      {
        id: "video-ready",
        projectId: "project-video",
        filePath: "C:/media/ready.mp4",
        fileName: "ready.mp4",
        fileSizeBytes: 4096,
        durationSeconds: 7,
        width: 1080,
        height: 1920,
        frameRate: 30,
        codec: "h264",
        status: "ready",
        errorMessage: null,
        createdAt: "2026-04-26T00:00:00Z"
      }
    ];

    const wrapper = mount(VideoDeconstructionCenterPage, {
      global: {
        plugins: [pinia]
      }
    });

    await flushPromises();
    await wrapper.find('[data-action="import-video"]').exists();
    await wrapper.get(".video-card").trigger("click");
    await wrapper.findAll("button").find((button) => button.text().includes("开始拆解"))?.trigger("click");
    await flushPromises();

    expect(deconstructVideoSpy).toHaveBeenCalledWith("video-ready");
    expect(wrapper.text()).toContain("脚本文案");
    expect(wrapper.text()).toContain("视频关键帧");
    expect(wrapper.text()).toContain("内容结构");
    expect(wrapper.text()).toContain("This cup stays cold all day.");
    expect(wrapper.text()).not.toContain("配置转录 Provider");
  });

  it("shows start hint instead of provider configuration before deconstruction", async () => {
    vi.resetModules();
    vi.doMock("@/components/common/ProjectContextGuard.vue", () => ({
      default: {
        template: "<slot />"
      }
    }));
    vi.doMock("@/app/runtime-client", () => ({
      RuntimeRequestError: class RuntimeRequestError extends Error {
        details = null;
        requestId = undefined;
        status = undefined;
      },
      applyVideoExtractionToProject: vi.fn(),
      deconstructVideo: vi.fn(),
      deleteImportedVideo: vi.fn(),
      fetchImportedVideos: vi.fn(async () => []),
      fetchRuntimeMediaDiagnostics: vi.fn(async () => ({
        ffprobe: {
          status: "ready",
          path: "C:/tools/ffprobe.exe",
          source: "config",
          version: "ffprobe version test",
          errorCode: null,
          errorMessage: null
        },
        checkedAt: "2026-04-26T00:00:00Z"
      })),
      fetchVideoSegments: vi.fn(async () => []),
      fetchVideoResult: vi.fn(async () => {
        throw new Error("legacy result unavailable");
      }),
      fetchVideoStages: vi.fn(async () => [
        {
          stageId: "transcribe",
          label: "视频解析",
          status: "provider_required",
          progressPct: 0,
          resultSummary: "历史配置缺失",
          errorMessage: "历史配置缺失",
          errorCode: "provider.required",
          nextAction: "请先配置可用视频解析模型后重试。",
          blockedByStageId: null,
          updatedAt: "2026-04-26T00:00:00Z",
          isCurrent: false,
          activeTaskId: null,
          activeTaskStatus: null,
          activeTaskProgress: null,
          activeTaskMessage: null,
          canCancel: false,
          canRetry: false,
          canRerun: true
        }
      ]),
      fetchVideoStructure: vi.fn(async () => ({
        id: "extraction-video-pending",
        videoId: "video-pending",
        status: "pending",
        scriptJson: null,
        storyboardJson: null,
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      })),
      fetchVideoTranscript: vi.fn(async () => ({
        id: "transcript-video-pending",
        videoId: "video-pending",
        language: null,
        text: null,
        status: "pending",
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      })),
      importVideo: vi.fn(),
      rerunVideoStage: vi.fn()
    }));
    vi.stubGlobal(
      "WebSocket",
      class {
        static OPEN = 1;
        readyState = 1;
        onopen: (() => void) | null = null;
        constructor() {
          setTimeout(() => this.onopen?.(), 0);
        }
        close() {}
        send() {}
      }
    );

    const pinia = createPinia();
    setActivePinia(pinia);
    const { default: VideoDeconstructionCenterPage } = await import(
      "@/pages/video/VideoDeconstructionCenterPage.vue"
    );
    const { useProjectStore } = await import("@/stores/project");
    const { useVideoImportStore } = await import("@/stores/video-import");

    useProjectStore().currentProject = {
      projectId: "project-video",
      projectName: "Video Project",
      status: "active"
    };
    useVideoImportStore().videos = [
      {
        id: "video-pending",
        projectId: "project-video",
        filePath: "C:/media/pending.mp4",
        fileName: "pending.mp4",
        fileSizeBytes: 4096,
        durationSeconds: 7,
        width: 1080,
        height: 1920,
        frameRate: 30,
        codec: "h264",
        status: "ready",
        errorMessage: null,
        createdAt: "2026-04-26T00:00:00Z"
      }
    ];

    const wrapper = mount(VideoDeconstructionCenterPage, {
      global: {
        plugins: [pinia]
      }
    });

    await flushPromises();
    await wrapper.get(".video-card").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("等待开始拆解");
    expect(wrapper.text()).toContain("点击“开始拆解”后");
    expect(wrapper.text()).not.toContain("请先配置一个支持视频输入的多模态视频解析模型");
    expect(wrapper.text()).not.toContain("视频解析模型未就绪");
  });

  it("renders the standardized script, keyframe and structure result sections", async () => {
    vi.resetModules();
    vi.doMock("@/components/common/ProjectContextGuard.vue", () => ({
      default: {
        template: "<slot />"
      }
    }));
    const standardResult = {
      videoId: "video-standard",
      transcript: {
        id: "transcript-video-standard",
        videoId: "video-standard",
        language: null,
        text: null,
        status: "skipped",
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      },
      segments: [],
      structure: {
        id: "extraction-video-standard",
        videoId: "video-standard",
        status: "succeeded",
        scriptJson: null,
        storyboardJson: null,
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      },
      stages: [],
      script: {
        title: "标准脚本文案",
        language: "zh",
        fullText: "第一句标准口播。\n第二句标准口播。",
        lines: [
          { startMs: 0, endMs: 3000, text: "第一句标准口播。", type: "speech" },
          { startMs: 3000, endMs: 6000, text: "第二句标准口播。", type: "speech" }
        ]
      },
      keyframes: [
        {
          index: 1,
          startMs: 0,
          endMs: 3000,
          visual: "标准关键帧画面",
          speech: "第一句标准口播。",
          onscreenText: "第一句标准口播。",
          shotType: "近景",
          camera: "手持正面",
          intent: "开头钩子"
        }
      ],
      contentStructure: {
        topic: "标准内容主题",
        hook: "标准开头钩子",
        painPoints: ["标准痛点"],
        sellingPoints: ["标准卖点"],
        rhythm: ["0-3秒强钩子"],
        cta: "标准 CTA",
        reusableForScript: ["可复用脚本点"],
        reusableForStoryboard: ["可复用分镜点"],
        risks: ["标准风险"]
      },
      source: {
        provider: "volcengine",
        model: "doubao-seed-2.0-pro-260215",
        promptVersion: "video_deconstruction_result_v1"
      }
    };
    const deconstructVideoSpy = vi.fn(async () => standardResult);
    vi.doMock("@/app/runtime-client", () => ({
      RuntimeRequestError: class RuntimeRequestError extends Error {
        details = null;
        requestId = undefined;
        status = undefined;
      },
      applyVideoExtractionToProject: vi.fn(),
      deconstructVideo: deconstructVideoSpy,
      deleteImportedVideo: vi.fn(),
      fetchImportedVideos: vi.fn(async () => []),
      fetchRuntimeMediaDiagnostics: vi.fn(async () => ({
        ffprobe: {
          status: "ready",
          path: "C:/tools/ffprobe.exe",
          source: "config",
          version: "ffprobe version test",
          errorCode: null,
          errorMessage: null
        },
        checkedAt: "2026-04-26T00:00:00Z"
      })),
      fetchVideoResult: vi.fn(async () => {
        throw new Error("legacy result unavailable");
      }),
      fetchVideoSegments: vi.fn(async () => []),
      fetchVideoStages: vi.fn(async () => []),
      fetchVideoStructure: vi.fn(async () => standardResult.structure),
      fetchVideoTranscript: vi.fn(async () => standardResult.transcript),
      importVideo: vi.fn(),
      rerunVideoStage: vi.fn()
    }));
    vi.stubGlobal(
      "WebSocket",
      class {
        static OPEN = 1;
        readyState = 1;
        onopen: (() => void) | null = null;
        constructor() {
          setTimeout(() => this.onopen?.(), 0);
        }
        close() {}
        send() {}
      }
    );

    const pinia = createPinia();
    setActivePinia(pinia);
    const { default: VideoDeconstructionCenterPage } = await import(
      "@/pages/video/VideoDeconstructionCenterPage.vue"
    );
    const { useProjectStore } = await import("@/stores/project");
    const { useVideoImportStore } = await import("@/stores/video-import");

    useProjectStore().currentProject = {
      projectId: "project-video",
      projectName: "Video Project",
      status: "active"
    };
    useVideoImportStore().videos = [
      {
        id: "video-standard",
        projectId: "project-video",
        filePath: "C:/media/standard.mp4",
        fileName: "standard.mp4",
        fileSizeBytes: 4096,
        durationSeconds: 6,
        width: 1080,
        height: 1920,
        frameRate: 30,
        codec: "h264",
        status: "ready",
        errorMessage: null,
        createdAt: "2026-04-26T00:00:00Z"
      }
    ];

    const wrapper = mount(VideoDeconstructionCenterPage, {
      global: {
        plugins: [pinia]
      }
    });

    await flushPromises();
    await wrapper.get(".video-card").trigger("click");
    await wrapper.findAll("button").find((button) => /开始拆解|重新拆解/.test(button.text()))?.trigger("click");
    await flushPromises();

    expect(deconstructVideoSpy).toHaveBeenCalledWith("video-standard");
    expect(wrapper.text()).toContain("0:00-0:03");
    expect(wrapper.text()).toContain("第一句标准口播。");

    await wrapper.findAll(".result-tabs button").find((button) => button.text().includes("视频关键帧"))?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("标准关键帧画面");
    expect(wrapper.text()).toContain("第一句标准口播。");
    expect(wrapper.text()).not.toContain("第一句标准口播。 / 第一句标准口播。");

    await wrapper.findAll(".result-tabs button").find((button) => button.text().includes("内容结构"))?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("话术结构");
    expect(wrapper.text()).toContain("开场钩子");
    expect(wrapper.text()).toContain("结构作用");
    expect(wrapper.text()).toContain("标准内容主题");
    expect(wrapper.text()).toContain("标准开头钩子");
    expect(wrapper.text()).toContain("标准卖点");
    expect(wrapper.text()).toContain("复制结构");
  });

  it("shows an incomplete-result state instead of placeholder structure blocks", async () => {
    vi.resetModules();
    vi.doMock("@/components/common/ProjectContextGuard.vue", () => ({
      default: {
        template: "<slot />"
      }
    }));
    const emptyResult = {
      videoId: "video-empty-standard",
      transcript: {
        id: "transcript-video-empty-standard",
        videoId: "video-empty-standard",
        language: null,
        text: null,
        status: "provider_required",
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      },
      segments: [],
      structure: {
        id: "extraction-video-empty-standard",
        videoId: "video-empty-standard",
        status: "succeeded",
        scriptJson: null,
        storyboardJson: null,
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      },
      stages: [],
      script: {
        title: "",
        language: "",
        fullText: "",
        lines: []
      },
      keyframes: [],
      contentStructure: {
        topic: "",
        hook: "",
        painPoints: [],
        sellingPoints: [],
        rhythm: [],
        cta: "",
        reusableForScript: [],
        reusableForStoryboard: [],
        risks: []
      },
      source: {
        provider: "local",
        model: "fallback",
        promptVersion: "video_deconstruction_result_v1"
      }
    };
    vi.doMock("@/app/runtime-client", () => ({
      RuntimeRequestError: class RuntimeRequestError extends Error {
        details = null;
        requestId = undefined;
        status = undefined;
      },
      applyVideoExtractionToProject: vi.fn(),
      deconstructVideo: vi.fn(async () => emptyResult),
      deleteImportedVideo: vi.fn(),
      fetchImportedVideos: vi.fn(async () => []),
      fetchRuntimeMediaDiagnostics: vi.fn(async () => ({
        ffprobe: {
          status: "ready",
          path: "C:/tools/ffprobe.exe",
          source: "config",
          version: "ffprobe version test",
          errorCode: null,
          errorMessage: null
        },
        checkedAt: "2026-04-26T00:00:00Z"
      })),
      fetchVideoResult: vi.fn(async () => emptyResult),
      fetchVideoSegments: vi.fn(async () => []),
      fetchVideoStages: vi.fn(async () => []),
      fetchVideoStructure: vi.fn(async () => emptyResult.structure),
      fetchVideoTranscript: vi.fn(async () => emptyResult.transcript),
      importVideo: vi.fn(),
      rerunVideoStage: vi.fn()
    }));
    vi.stubGlobal(
      "WebSocket",
      class {
        static OPEN = 1;
        readyState = 1;
        onopen: (() => void) | null = null;
        constructor() {
          setTimeout(() => this.onopen?.(), 0);
        }
        close() {}
        send() {}
      }
    );

    const pinia = createPinia();
    setActivePinia(pinia);
    const { default: VideoDeconstructionCenterPage } = await import(
      "@/pages/video/VideoDeconstructionCenterPage.vue"
    );
    const { useProjectStore } = await import("@/stores/project");
    const { useVideoImportStore } = await import("@/stores/video-import");

    useProjectStore().currentProject = {
      projectId: "project-video",
      projectName: "Video Project",
      status: "active"
    };
    useVideoImportStore().videos = [
      {
        id: "video-empty-standard",
        projectId: "project-video",
        filePath: "C:/media/Download.mp4",
        fileName: "Download.mp4",
        fileSizeBytes: 4096,
        durationSeconds: 39,
        width: 576,
        height: 1024,
        frameRate: 30,
        codec: "h264",
        status: "ready",
        errorMessage: null,
        createdAt: "2026-04-26T00:00:00Z"
      }
    ];

    const wrapper = mount(VideoDeconstructionCenterPage, {
      global: {
        plugins: [pinia]
      }
    });

    await flushPromises();
    await wrapper.get(".video-card").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("解析结果不完整");
    expect(wrapper.text()).not.toContain("当前结果暂无脚本文案");

    await wrapper.findAll(".result-tabs button").find((button) => button.text().includes("内容结构"))?.trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("还没有内容结构");
    expect(wrapper.text()).not.toContain("暂未识别主题");
  });

  it("does not show provider configuration when stale provider stage remains after structure exists", async () => {
    vi.resetModules();
    vi.doMock("@/components/common/ProjectContextGuard.vue", () => ({
      default: {
        template: "<slot />"
      }
    }));
    vi.doMock("@/app/runtime-client", () => ({
      RuntimeRequestError: class RuntimeRequestError extends Error {
        details = null;
        requestId = undefined;
        status = undefined;
      },
      applyVideoExtractionToProject: vi.fn(),
      deconstructVideo: vi.fn(),
      deleteImportedVideo: vi.fn(),
      fetchImportedVideos: vi.fn(async () => []),
      fetchRuntimeMediaDiagnostics: vi.fn(async () => ({
        ffprobe: {
          status: "ready",
          path: "C:/tools/ffprobe.exe",
          source: "config",
          version: "ffprobe version test",
          errorCode: null,
          errorMessage: null
        },
        checkedAt: "2026-04-26T00:00:00Z"
      })),
      fetchVideoSegments: vi.fn(async () => []),
      fetchVideoResult: vi.fn(async () => {
        throw new Error("legacy result unavailable");
      }),
      fetchVideoStages: vi.fn(async () => [
        {
          stageId: "transcribe",
          label: "视频解析",
          status: "provider_required",
          progressPct: 0,
          resultSummary: "历史配置缺失",
          errorMessage: "历史配置缺失",
          errorCode: "provider.required",
          nextAction: "请先配置可用视频解析模型后重试。",
          blockedByStageId: null,
          updatedAt: "2026-04-26T00:00:00Z",
          isCurrent: false,
          activeTaskId: null,
          activeTaskStatus: null,
          activeTaskProgress: null,
          activeTaskMessage: null,
          canCancel: false,
          canRetry: true,
          canRerun: true
        },
        {
          stageId: "extract_structure",
          label: "结构提取",
          status: "succeeded",
          progressPct: 100,
          resultSummary: "已生成结构",
          errorMessage: null,
          errorCode: null,
          nextAction: null,
          blockedByStageId: null,
          updatedAt: "2026-04-26T00:00:00Z",
          isCurrent: true,
          activeTaskId: null,
          activeTaskStatus: null,
          activeTaskProgress: null,
          activeTaskMessage: null,
          canCancel: false,
          canRetry: false,
          canRerun: true
        }
      ]),
      fetchVideoStructure: vi.fn(async () => ({
        id: "extraction-video-stale-provider",
        videoId: "video-stale-provider",
        status: "succeeded",
        scriptJson: JSON.stringify({ summary: { fileName: "stale-provider.mp4" }, segments: [] }),
        storyboardJson: "{}",
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      })),
      fetchVideoTranscript: vi.fn(async () => ({
        id: "transcript-video-stale-provider",
        videoId: "video-stale-provider",
        language: null,
        text: null,
        status: "provider_required",
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      })),
      importVideo: vi.fn(),
      rerunVideoStage: vi.fn()
    }));
    vi.stubGlobal(
      "WebSocket",
      class {
        static OPEN = 1;
        readyState = 1;
        onopen: (() => void) | null = null;
        constructor() {
          setTimeout(() => this.onopen?.(), 0);
        }
        close() {}
        send() {}
      }
    );

    const pinia = createPinia();
    setActivePinia(pinia);
    const { default: VideoDeconstructionCenterPage } = await import(
      "@/pages/video/VideoDeconstructionCenterPage.vue"
    );
    const { useProjectStore } = await import("@/stores/project");
    const { useVideoImportStore } = await import("@/stores/video-import");

    useProjectStore().currentProject = {
      projectId: "project-video",
      projectName: "Video Project",
      status: "active"
    };
    useVideoImportStore().videos = [
      {
        id: "video-stale-provider",
        projectId: "project-video",
        filePath: "C:/media/stale-provider.mp4",
        fileName: "stale-provider.mp4",
        fileSizeBytes: 4096,
        durationSeconds: 7,
        width: 1080,
        height: 1920,
        frameRate: 30,
        codec: "h264",
        status: "ready",
        errorMessage: null,
        createdAt: "2026-04-26T00:00:00Z"
      }
    ];

    const wrapper = mount(VideoDeconstructionCenterPage, {
      global: {
        plugins: [pinia]
      }
    });

    await flushPromises();
    await wrapper.get(".video-card").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("当前结果暂无脚本文案");
    expect(wrapper.text()).toContain("可点击“重新拆解”刷新视频解析结果");
    expect(wrapper.text()).not.toContain("视频解析模型未就绪");
    expect(wrapper.text()).not.toContain("配置视频解析模型");
  });

  it("uses live media diagnostics instead of stale stage errors for the global FFprobe banner", async () => {
    vi.resetModules();
    vi.doMock("@/components/common/ProjectContextGuard.vue", () => ({
      default: {
        template: "<slot />"
      }
    }));
    vi.doMock("@/app/runtime-client", () => ({
      RuntimeRequestError: class RuntimeRequestError extends Error {
        details = null;
        requestId = undefined;
        status = undefined;
      },
      applyVideoExtractionToProject: vi.fn(),
      deleteImportedVideo: vi.fn(),
      fetchImportedVideos: vi.fn(async () => []),
      fetchRuntimeMediaDiagnostics: vi.fn(async () => ({
        ffprobe: {
          status: "ready",
          path: "C:/tools/ffprobe.exe",
          source: "config",
          version: "ffprobe version test",
          errorCode: null,
          errorMessage: null
        },
        checkedAt: "2026-04-25T13:00:00Z"
      })),
      fetchVideoResult: vi.fn(async () => {
        throw new Error("legacy result unavailable");
      }),
      fetchVideoStages: vi.fn(async () => [
        {
          stageId: "import",
          label: "导入",
          status: "failed",
          progressPct: 80,
          errorCode: "media.ffprobe_unavailable",
          errorMessage: "FFprobe 不可用，视频元数据解析已降级失败。",
          nextAction: "请先修复 FFprobe 后重试。",
          canRerun: true
        }
      ]),
      fetchVideoSegments: vi.fn(async () => []),
      fetchVideoStructure: vi.fn(async () => ({
        id: "extraction-video-stale",
        videoId: "video-stale",
        status: "pending",
        scriptJson: null,
        storyboardJson: null,
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      })),
      fetchVideoTranscript: vi.fn(async () => ({
        id: "transcript-video-stale",
        videoId: "video-stale",
        language: null,
        text: null,
        status: "pending",
        createdAt: "2026-04-26T00:00:00Z",
        updatedAt: "2026-04-26T00:00:00Z"
      })),
      importVideo: vi.fn(),
      rerunVideoStage: vi.fn()
    }));
    vi.stubGlobal(
      "WebSocket",
      class {
        static OPEN = 1;
        readyState = 1;
        onopen: (() => void) | null = null;
        constructor() {
          setTimeout(() => this.onopen?.(), 0);
        }
        close() {}
        send() {}
      }
    );

    const pinia = createPinia();
    setActivePinia(pinia);
    const { default: VideoDeconstructionCenterPage } = await import(
      "@/pages/video/VideoDeconstructionCenterPage.vue"
    );
    const { useProjectStore } = await import("@/stores/project");
    const { useVideoImportStore } = await import("@/stores/video-import");

    useProjectStore().currentProject = {
      projectId: "project-video",
      projectName: "Video Project",
      status: "active"
    };
    useVideoImportStore().videos = [
      {
        id: "video-stale",
        projectId: "project-video",
        filePath: "C:/media/stale.mp4",
        fileName: "stale.mp4",
        fileSizeBytes: 4096,
        durationSeconds: null,
        width: null,
        height: null,
        frameRate: null,
        codec: null,
        status: "failed_degraded",
        errorMessage: "FFprobe 不可用，视频元数据解析已降级失败。",
        createdAt: "2026-04-13T00:00:00Z"
      }
    ];

    const wrapper = mount(VideoDeconstructionCenterPage, {
      global: {
        plugins: [pinia]
      }
    });
    await flushPromises();
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("stale.mp4");
    });
    await wrapper.get(".video-card").trigger("click");
    await flushPromises();

    expect(wrapper.text()).not.toContain("未检测到 FFprobe 可执行文件");
    expect(wrapper.text()).toContain("上次导入时 FFprobe 不可用。当前检测已正常");
    expect(wrapper.text()).not.toContain("请先修复 FFprobe 后重试。");
  });
});
