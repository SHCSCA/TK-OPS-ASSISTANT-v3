import { flushPromises } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { mountApp, okJsonResponse, runtimeFixtures } from "./runtime-helpers";

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

function createDeferredResponse() {
  let resolve!: (value: unknown) => void;
  const promise = new Promise((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

describe("Setup bootstrap flow", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("shows a standalone loading screen while bootstrap requests are pending", async () => {
    const healthResponse = createDeferredResponse();
    const configResponse = createDeferredResponse();
    const diagnosticsResponse = createDeferredResponse();

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const path = new URL(String(input)).pathname;
        if (path === "/api/license/status") {
          return Promise.resolve(okJsonResponse(runtimeFixtures.restrictedLicense));
        }
        if (path === "/api/settings/health") {
          return healthResponse.promise;
        }
        if (path === "/api/settings/config") {
          return configResponse.promise;
        }
        if (path === "/api/settings/diagnostics") {
          return diagnosticsResponse.promise;
        }

        throw new Error(`Unhandled request: ${path}`);
      })
    );

    const { wrapper } = await mountApp("/setup/license");
    await flushPromises();

    expect(wrapper.get('[data-bootstrap-screen="loading"]').text()).toContain("正在准备首启环境");
    expect(wrapper.find(".title-bar").exists()).toBe(false);

    healthResponse.resolve(okJsonResponse(runtimeFixtures.health));
    configResponse.resolve(okJsonResponse(runtimeFixtures.config));
    diagnosticsResponse.resolve(okJsonResponse(runtimeFixtures.diagnostics));
    await flushPromises();
    await flushPromises();

    expect(wrapper.find('[data-bootstrap-screen="loading"]').exists()).toBe(false);
    expect(wrapper.find('[data-bootstrap-screen="license"]').exists()).toBe(true);
  });

  it("activates the license, switches to initialization, saves settings, and enters the dashboard", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(okJsonResponse(runtimeFixtures.restrictedLicense))
      .mockResolvedValueOnce(okJsonResponse(runtimeFixtures.health))
      .mockResolvedValueOnce(okJsonResponse(runtimeFixtures.config))
      .mockResolvedValueOnce(okJsonResponse(runtimeFixtures.diagnostics))
      .mockResolvedValueOnce(
        okJsonResponse({
          ...runtimeFixtures.activeLicense,
          maskedCode: "eyJh****************WJjZA",
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
          ...runtimeFixtures.health,
          mode: "production",
          now: "2026-04-11T09:12:00Z"
        })
      )
      .mockResolvedValueOnce(
        okJsonResponse({
          ...runtimeFixtures.diagnostics,
          revision: 2,
          mode: "production"
        })
      )
      .mockResolvedValueOnce(okJsonResponse(runtimeFixtures.emptyDashboardSummary));

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper, router } = await mountApp("/setup/license?redirect=%2Fdashboard");
    await flushPromises();

    expect(wrapper.find('[data-bootstrap-screen="license"]').exists()).toBe(true);

    await wrapper.get('[data-field="activationCode"]').setValue("signed-license-code");
    await wrapper.get('[data-action="activate-license"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-bootstrap-screen="initialization"]').exists()).toBe(true);

    await wrapper.get('[data-field="runtime.mode"]').setValue("production");
    await wrapper.get('[data-field="logging.level"]').setValue("DEBUG");
    await wrapper.get('[data-field="ai.model"]').setValue("gpt-5.4-mini");
    await wrapper.get('[data-field="ai.voice"]').setValue("nova");
    await wrapper.get('[data-field="ai.subtitleMode"]').setValue("precise");
    await wrapper.get('[data-action="save-bootstrap"]').trigger("click");
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
      activationCode: "signed-license-code"
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
      expect(wrapper.find(".title-bar").exists()).toBe(true);
    });
  });

  it("shows activation errors with the request id on the standalone license screen", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(okJsonResponse(runtimeFixtures.restrictedLicense))
        .mockResolvedValueOnce(okJsonResponse(runtimeFixtures.health))
        .mockResolvedValueOnce(okJsonResponse(runtimeFixtures.config))
        .mockResolvedValueOnce(okJsonResponse(runtimeFixtures.diagnostics))
        .mockResolvedValueOnce(
          errorJsonResponse(400, "授权码签名校验失败。", "req-license-400")
        )
    );

    const { wrapper } = await mountApp("/setup/license");
    await flushPromises();

    await wrapper.get('[data-field="activationCode"]').setValue("bad-code");
    await wrapper.get('[data-action="activate-license"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("授权码签名校验失败。");
    expect(wrapper.text()).toContain("req-license-400");
    expect(wrapper.find('[data-bootstrap-screen="license"]').exists()).toBe(true);
  });
});

