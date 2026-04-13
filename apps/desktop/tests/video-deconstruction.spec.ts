import { flushPromises } from "@vue/test-utils";
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
    expect(wrapper.text()).toContain("视频拆解中心");
    expect(wrapper.text()).toContain("source.mp4");
    expect(wrapper.text()).toContain("1920 × 1080");
    expect(wrapper.text()).toContain("62.4 秒");
    expect(wrapper.find('[data-action="import-video"]').exists()).toBe(true);
  });
});
