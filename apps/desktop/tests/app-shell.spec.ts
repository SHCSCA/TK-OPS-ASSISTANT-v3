import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useShellUiStore } from "@/stores/shell-ui";

import {
  createRouteAwareFetch,
  mountApp,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

describe("App shell", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("持久化壳层状态并同步到本地存储", () => {
    localStorage.setItem(
      "tkops-shell-ui",
      JSON.stringify({
        theme: "dark",
        reducedMotion: true,
        sidebarCollapsed: true,
        detailPanelOpen: true,
        detailContext: {
          key: "route:contextual",
          mode: "contextual",
          source: "route",
          title: "测试上下文",
          sections: []
        }
      })
    );

    setActivePinia(createPinia());
    const shellUiStore = useShellUiStore();

    expect(shellUiStore.theme).toBe("dark");
    expect(shellUiStore.reducedMotion).toBe(true);
    expect(shellUiStore.sidebarCollapsed).toBe(true);
    expect(shellUiStore.isDetailPanelOpen).toBe(true);
    expect(shellUiStore.detailContext.title).toBe("测试上下文");

    shellUiStore.setTheme("light");
    shellUiStore.setReducedMotion(false);
    shellUiStore.setSidebarCollapsed(false);
    shellUiStore.closeDetailPanel();

    expect(JSON.parse(localStorage.getItem("tkops-shell-ui") ?? "{}")).toMatchObject({
      theme: "light",
      reducedMotion: false,
      sidebarCollapsed: false,
      detailPanelOpen: false
    });
  });

  it("renders the app shell with persisted theme and workspace chrome state", async () => {
    localStorage.setItem(
      "tkops-shell-ui",
      JSON.stringify({
        theme: "dark",
        reducedMotion: true,
        sidebarCollapsed: true,
        detailPanelOpen: true,
        detailContext: {
          key: "route:contextual",
          mode: "contextual",
          source: "route",
          title: "测试上下文",
          sections: []
        }
      })
    );

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

    const shell = wrapper.get(".app-shell");

    expect(wrapper.findAll("[data-route-id]")).toHaveLength(15);
    expect(wrapper.text()).toContain("Runtime 在线");
    expect(wrapper.find(".app-shell__status").text()).toContain("Runtime 在线");
    expect(wrapper.text()).toContain("本地 AI 视频创作中枢");
    expect(wrapper.text()).not.toContain("鏈");
    expect(wrapper.text()).not.toContain("鍒");
    expect(shell.attributes("data-theme")).toBe("dark");
    expect(shell.attributes("data-reduced-motion")).toBe("true");
    expect(shell.attributes("data-sidebar-collapsed")).toBe("true");
    expect(shell.attributes("data-detail-open")).toBe("true");
    expect(wrapper.find(".app-shell__title-bar").exists()).toBe(true);
    expect(wrapper.find(".shell-search").exists()).toBe(false);
    expect(wrapper.find(".shell-title-bar__detail-toggle").exists()).toBe(true);
    expect(wrapper.find(".app-shell__sidebar").classes()).toContain("is-collapsed");
    expect(wrapper.find(".app-shell__detail").classes()).toContain("is-open");
    expect(wrapper.find(".app-shell__status").exists()).toBe(true);
  });

  it("资产中心选择素材后打开全局右侧详情面板并展示资产详情", async () => {
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

    expect(wrapper.find(".app-shell__detail.is-open").exists()).toBe(false);

    await wrapper.get('[data-testid="asset-card-asset-1"]').trigger("click");
    await flushPromises();

    expect(wrapper.find(".app-shell__detail.is-open").exists()).toBe(true);
    expect(wrapper.find(".shell-detail-panel").text()).toContain("资产详情");
    expect(wrapper.find(".shell-detail-panel").text()).toContain("Clip");
    expect(wrapper.find(".shell-detail-panel").text()).toContain("引用影响");
    expect(wrapper.find(".shell-detail-panel").text()).toContain("当前资产没有被项目链路引用");
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
