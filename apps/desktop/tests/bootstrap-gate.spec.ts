import { flushPromises } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createRouteAwareFetch,
  mountApp,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

describe("Bootstrap gate", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a standalone license bootstrap screen before the workspace shell", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path) => {
        if (path === "/api/license/status") {
          return okJsonResponse(runtimeFixtures.restrictedLicense);
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

        throw new Error(`Unhandled request: ${path}`);
      })
    );

    const { wrapper } = await mountApp("/dashboard");
    await flushPromises();

    expect(wrapper.find('[data-bootstrap-screen="license"]').exists()).toBe(true);
    expect(wrapper.find('[data-field="activationCode"]').exists()).toBe(true);
    expect(wrapper.find(".title-bar").exists()).toBe(false);
    expect(wrapper.find(".sidebar").exists()).toBe(false);
    expect(wrapper.text()).toContain("当前需要完成永久授权");
  });
});

