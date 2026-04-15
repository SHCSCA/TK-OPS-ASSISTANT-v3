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
});
