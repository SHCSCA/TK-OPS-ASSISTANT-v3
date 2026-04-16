import { flushPromises } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createRouteAwareFetch,
  mountApp,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

describe("App shell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("renders all formal routes and shows config bus status after bootstrap is complete", async () => {
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
          return okJsonResponse(runtimeFixtures.emptyDashboardSummary);
        }

        throw new Error(`Unhandled request: ${path}`);
      })
    );

    const { wrapper } = await mountApp("/dashboard");
    await flushPromises();
    await flushPromises();

    expect(wrapper.findAll("[data-route-id]")).toHaveLength(15);
    expect(wrapper.text()).toContain("Runtime 在线");
    // These are now in the detail panel drawer, which is closed by default.
    // We can either open it or just check the status bar which is visible.
    expect(wrapper.find(".shell-status-bar").text()).toContain("Runtime 在线");
    expect(wrapper.text()).toContain("本地 AI 视频创作中枢");
    expect(wrapper.text()).not.toContain("鏈");
    expect(wrapper.text()).not.toContain("鍒");
    expect(wrapper.find(".shell-title-bar").exists()).toBe(true);
    expect(wrapper.find(".shell-sidebar").exists()).toBe(true);
    expect(wrapper.find(".shell-detail-panel").exists()).toBe(true);
    expect(wrapper.find(".shell-status-bar").exists()).toBe(true);
  });

  it("资产中心选择素材后打开全局右侧抽屉并展示资产详情", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/license/status") return okJsonResponse(runtimeFixtures.activeLicense);
        if (path === "/api/settings/health") return okJsonResponse(runtimeFixtures.health);
        if (path === "/api/settings/config") return okJsonResponse(runtimeFixtures.initializedConfig);
        if (path === "/api/settings/diagnostics") return okJsonResponse(runtimeFixtures.initializedDiagnostics);
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "测试项目",
              status: "active"
            }
          });
        }
        if (path === "/api/assets" && method === "GET") return okJsonResponse([asset()]);
        if (path === "/api/assets/asset-1/references" && method === "GET") {
          return okJsonResponse([
            {
              id: "ref-1",
              assetId: "asset-1",
              referenceType: "storyboard",
              referenceId: "scene-1",
              createdAt: "2026-04-16T10:00:00Z"
            }
          ]);
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper } = await mountApp("/assets/library");
    await flushPromises();
    await flushPromises();

    expect(wrapper.find(".detail-panel-container.is-open").exists()).toBe(false);

    await wrapper.get('[data-testid="asset-card-asset-1"]').trigger("click");
    await flushPromises();

    expect(wrapper.find(".detail-panel-container.is-open").exists()).toBe(true);
    expect(wrapper.find(".shell-detail-panel").text()).toContain("资产详情");
    expect(wrapper.find(".shell-detail-panel").text()).toContain("Clip");
    expect(wrapper.find(".shell-detail-panel").text()).toContain("引用影响范围");
    expect(wrapper.find(".shell-detail-panel").text()).toContain("storyboard");
  });
});

function asset() {
  return {
    id: "asset-1",
    name: "Clip",
    type: "video",
    source: "local",
    filePath: "D:/tkops/assets/clip.mp4",
    fileSizeBytes: 2048,
    durationMs: null,
    thumbnailPath: null,
    tags: '["开场"]',
    projectId: "project-1",
    metadataJson: null,
    createdAt: "2026-04-16T10:00:00Z",
    updatedAt: "2026-04-16T10:00:00Z"
  };
}
