import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "@/App.vue";
import { createAppRouter } from "@/app/router";

function okJsonResponse(data: unknown) {
  return {
    ok: true,
    json: async () => ({
      ok: true,
      data
    })
  };
}

function mountApp(path: string) {
  const pinia = createPinia();
  const router = createAppRouter(createMemoryHistory());
  router.push(path);

  return router.isReady().then(() =>
    mount(App, {
      global: {
        plugins: [pinia, router]
      }
    })
  );
}

describe("App shell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("renders all formal routes and shows config bus status", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          okJsonResponse({
            service: "online",
            version: "0.1.1",
            now: "2026-04-11T00:00:00Z",
            mode: "development"
          })
        )
        .mockResolvedValueOnce(
          okJsonResponse({
            revision: 1,
            runtime: {
              mode: "development",
              workspaceRoot: "G:/AI/TK-OPS-ASSISTANT-V3"
            },
            paths: {
              cacheDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/cache",
              exportDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/exports",
              logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs"
            },
            logging: {
              level: "INFO"
            },
            ai: {
              provider: "openai",
              model: "gpt-5.4",
              voice: "alloy",
              subtitleMode: "balanced"
            }
          })
        )
        .mockResolvedValueOnce(
          okJsonResponse({
            databasePath: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/runtime.db",
            logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs",
            revision: 1,
            mode: "development",
            healthStatus: "online"
          })
        )
    );

    const wrapper = await mountApp("/dashboard");
    await flushPromises();

    expect(wrapper.findAll("[data-route-id]")).toHaveLength(16);
    expect(wrapper.text()).toContain("Runtime online");
    expect(wrapper.text()).toContain("Config ready");
  });
});
