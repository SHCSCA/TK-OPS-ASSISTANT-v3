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

  it("redirects project-scoped routes to dashboard when no current project is selected", async () => {
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

    expect(router.currentRoute.value.fullPath).toBe(
      "/dashboard?redirect=/scripts/topics&reason=missing-project"
    );
    expect(wrapper.text()).toContain("Project context required");
  });
});
