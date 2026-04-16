import { flushPromises } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createRouteAwareFetch,
  mountApp,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

describe("Project context guard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("stays on the requested route but shows empty state when no current project is selected", async () => {
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
        if (path === "/api/dashboard/context") {
          return okJsonResponse(null);
        }
        if (path === "/api/dashboard/summary") {
          return okJsonResponse(runtimeFixtures.emptyDashboardSummary);
        }

        throw new Error(`Unhandled request: ${path}`);
      })
    );

    const { wrapper, router } = await mountApp("/scripts/topics");
    await flushPromises();

    // Behavior changed: we stay on the page
    expect(router.currentRoute.value.path).toBe("/scripts/topics");

    // Check if the ProjectContextGuard rendered the empty state
    expect(wrapper.find(".empty-state-container").exists()).toBe(true);
    expect(wrapper.text()).toContain("需要选择项目");
  });
});
