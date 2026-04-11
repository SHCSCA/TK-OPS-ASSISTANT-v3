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

function errorJsonResponse(status: number, error: string, requestId = "req-license") {
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
  const router = createAppRouter(pinia, createMemoryHistory());
  router.push(path);
  await router.isReady();

  const wrapper = mount(App, {
    global: {
      plugins: [pinia, router]
    }
  });

  return { wrapper, router };
}

describe("Setup license wizard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("redirects protected routes to the wizard and hides the normal workspace chrome", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          okJsonResponse({
            active: false,
            restrictedMode: true,
            machineId: "machine-001",
            machineBound: false,
            activationMode: "placeholder",
            maskedCode: "",
            activatedAt: null
          })
        )
        .mockResolvedValueOnce(
          okJsonResponse({
            service: "online",
            version: "0.1.1",
            now: "2026-04-11T09:00:00Z",
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
            logging: { level: "INFO" },
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

    const { wrapper, router } = await mountApp("/dashboard");
    await flushPromises();

    expect(router.currentRoute.value.fullPath).toBe("/setup/license?redirect=/dashboard");
    expect(wrapper.find(".sidebar").exists()).toBe(false);
    expect(wrapper.find(".detail-panel").exists()).toBe(false);
    expect(wrapper.text()).toContain("License restricted");
  });

  it("activates the license, saves initial settings, and returns to the target route", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        okJsonResponse({
          active: false,
          restrictedMode: true,
          machineId: "machine-001",
          machineBound: false,
          activationMode: "placeholder",
          maskedCode: "",
          activatedAt: null
        })
      )
      .mockResolvedValueOnce(
        okJsonResponse({
          service: "online",
          version: "0.1.1",
          now: "2026-04-11T09:10:00Z",
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
          logging: { level: "INFO" },
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
          active: true,
          restrictedMode: false,
          machineId: "machine-001",
          machineBound: true,
          activationMode: "placeholder",
          maskedCode: "TK-O****************0001",
          activatedAt: "2026-04-11T09:10:00Z"
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
          logging: { level: "DEBUG" },
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
          now: "2026-04-11T09:12:00Z",
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

    const { wrapper, router } = await mountApp("/setup/license?redirect=%2Fdashboard");
    await flushPromises();

    await wrapper.get('[data-field="activationCode"]').setValue("TK-OPS-2026-ALPHA-0001");
    await wrapper.get('[data-field="runtime.mode"]').setValue("production");
    await wrapper.get('[data-field="logging.level"]').setValue("DEBUG");
    await wrapper.get('[data-field="ai.model"]').setValue("gpt-5.4-mini");
    await wrapper.get('[data-field="ai.voice"]').setValue("nova");
    await wrapper.get('[data-field="ai.subtitleMode"]').setValue("precise");
    await wrapper.get('[data-action="activate-license"]').trigger("click");
    await flushPromises();
    await flushPromises();

    const activateCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        String(url).includes("/api/license/activate") && options?.method === "POST"
    );
    const settingsSaveCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        String(url).includes("/api/settings/config") && options?.method === "PUT"
    );

    expect(activateCall).toBeTruthy();
    expect(JSON.parse(String(activateCall?.[1]?.body))).toEqual({
      activationCode: "TK-OPS-2026-ALPHA-0001"
    });
    expect(settingsSaveCall).toBeTruthy();
    expect(JSON.parse(String(settingsSaveCall?.[1]?.body))).toMatchObject({
      runtime: { mode: "production" },
      logging: { level: "DEBUG" },
      ai: {
        model: "gpt-5.4-mini",
        voice: "nova",
        subtitleMode: "precise"
      }
    });
    await vi.waitFor(() => {
      expect(router.currentRoute.value.fullPath).toBe("/dashboard");
    });
  });

  it("shows activation errors with the request id when license activation fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          okJsonResponse({
            active: false,
            restrictedMode: true,
            machineId: "machine-001",
            machineBound: false,
            activationMode: "placeholder",
            maskedCode: "",
            activatedAt: null
          })
        )
        .mockResolvedValueOnce(
          okJsonResponse({
            service: "online",
            version: "0.1.1",
            now: "2026-04-11T09:00:00Z",
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
            logging: { level: "INFO" },
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
          errorJsonResponse(400, "Activation rejected", "req-license-400")
        )
    );

    const { wrapper } = await mountApp("/setup/license");
    await flushPromises();

    await wrapper.get('[data-field="activationCode"]').setValue("bad-code");
    await wrapper.get('[data-action="activate-license"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Activation rejected");
    expect(wrapper.text()).toContain("req-license-400");
  });
});
