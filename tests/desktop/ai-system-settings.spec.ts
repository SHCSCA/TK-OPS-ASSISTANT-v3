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

function errorJsonResponse(status: number, error: string, requestId = "req-offline") {
  return {
    ok: false,
    status,
    json: async () => ({
      ok: false,
      error,
      requestId
    })
  };
}

async function mountApp(path: string) {
  const pinia = createPinia();
  const router = createAppRouter(createMemoryHistory());
  router.push(path);
  await router.isReady();

  return mount(App, {
    global: {
      plugins: [pinia, router]
    }
  });
}

describe("AI system settings", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("loads settings from config bus and saves updates through the runtime API", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-11T08:00:00.000Z"));

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        okJsonResponse({
          service: "online",
          version: "0.1.1",
          now: "2026-04-11T08:00:00Z",
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
      .mockResolvedValueOnce(
        okJsonResponse({
          revision: 2,
          runtime: {
            mode: "production",
            workspaceRoot: "G:/AI/TK-OPS-ASSISTANT-V3"
          },
          paths: {
            cacheDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/cache",
            exportDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/exports",
            logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs"
          },
          logging: {
            level: "DEBUG"
          },
          ai: {
            provider: "openai",
            model: "gpt-5.4-mini",
            voice: "nova",
            subtitleMode: "precise"
          }
        })
      )
      .mockResolvedValueOnce(
        okJsonResponse({
          service: "online",
          version: "0.1.1",
          now: "2026-04-11T08:05:00Z",
          mode: "production"
        })
      )
      .mockResolvedValueOnce(
        okJsonResponse({
          databasePath: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/runtime.db",
          logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs",
          revision: 2,
          mode: "production",
          healthStatus: "online"
        })
      );

    vi.stubGlobal("fetch", fetchMock);

    const wrapper = await mountApp("/settings/ai-system");
    await flushPromises();

    expect(
      (wrapper.get('[data-field="ai.model"]').element as HTMLInputElement).value
    ).toBe("gpt-5.4");

    vi.setSystemTime(new Date("2026-04-11T08:05:00.000Z"));
    await wrapper.get('[data-field="runtime.mode"]').setValue("production");
    await wrapper.get('[data-field="logging.level"]').setValue("DEBUG");
    await wrapper.get('[data-field="ai.model"]').setValue("gpt-5.4-mini");
    await wrapper.get('[data-field="ai.voice"]').setValue("nova");
    await wrapper.get('[data-field="ai.subtitleMode"]').setValue("precise");
    await wrapper.get('[data-action="save-settings"]').trigger("click");
    await flushPromises();

    const saveCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        String(url).includes("/api/settings/config") && options?.method === "PUT"
    );

    expect(saveCall).toBeTruthy();
    expect(JSON.parse(String(saveCall?.[1]?.body))).toMatchObject({
      runtime: {
        mode: "production"
      },
      logging: {
        level: "DEBUG"
      },
      ai: {
        model: "gpt-5.4-mini",
        voice: "nova",
        subtitleMode: "precise"
      }
    });
    expect(wrapper.text()).toContain("Config ready");
    expect(wrapper.text()).toContain("Last sync 2026-04-11T08:05:00.000Z");
  });

  it("shows runtime offline state and error summary when runtime requests fail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(errorJsonResponse(503, "Runtime unavailable", "req-503"))
    );

    const wrapper = await mountApp("/settings/ai-system");
    await flushPromises();

    expect(wrapper.text()).toContain("Runtime offline");
    expect(wrapper.text()).toContain("Runtime unavailable");
    expect(wrapper.text()).toContain("req-503");
  });
});
