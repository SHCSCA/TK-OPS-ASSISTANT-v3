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
    vi.useRealTimers();
  });

  it("renders all formal routes and shows config bus status", async () => {
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
          return okJsonResponse(runtimeFixtures.config);
        }
        if (path === "/api/settings/diagnostics") {
          return okJsonResponse(runtimeFixtures.diagnostics);
        }
        if (path === "/api/dashboard/summary") {
          return okJsonResponse(runtimeFixtures.emptyDashboardSummary);
        }

        throw new Error(`Unhandled request: ${path}`);
      })
    );

    const { wrapper } = await mountApp("/dashboard");
    await flushPromises();

    expect(wrapper.findAll("[data-route-id]")).toHaveLength(16);
    expect(wrapper.text()).toContain("Runtime online");
    expect(wrapper.text()).toContain("Config ready");
    expect(wrapper.text()).toContain("License active");
  });
});
