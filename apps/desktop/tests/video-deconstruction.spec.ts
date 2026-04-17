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

  it("renders imported video metadata and the blocked roadmap", async () => {
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
    expect(wrapper.text()).toContain("导入真实视频，拆出可回流的素材基线。");
    expect(wrapper.text()).toContain("导入列表");
    expect(wrapper.text()).toContain("后续拆解仍需真实链路接入");
    expect(wrapper.text()).toContain("source.mp4");
    expect(wrapper.text()).toContain("1920 × 1080");
    expect(wrapper.text()).toContain("62.4 秒");
    expect(wrapper.text()).toContain("已就绪");
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

  it("disables import entry when no project context is available", async () => {
    vi.resetModules();
    vi.doMock("@/components/common/ProjectContextGuard.vue", () => ({
      default: {
        template: "<slot />"
      }
    }));

    const pinia = createPinia();
    setActivePinia(pinia);
    const { default: VideoDeconstructionCenterPage } = await import(
      "@/pages/video/VideoDeconstructionCenterPage.vue"
    );
    const { useProjectStore } = await import("@/stores/project");

    useProjectStore().currentProject = null;

    const wrapper = mount(VideoDeconstructionCenterPage, {
      global: {
        plugins: [pinia]
      }
    });

    await flushPromises();

    expect(wrapper.text()).toContain("导入入口已阻断");
    expect(wrapper.text()).toContain("当前项目尚未就绪，导入入口被阻断。");
    expect(wrapper.get('[data-action="import-video"]').attributes("disabled")).toBeDefined();
  });
});
