import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "@/App.vue";
import { createAppRouter } from "@/app/router";

import { createRouteAwareFetch, okJsonResponse, runtimeFixtures } from "./runtime-helpers";

async function mountApp(path: string) {
  const pinia = createPinia();
  const router = createAppRouter(pinia, createMemoryHistory());
  router.push(path);
  await router.isReady();

  return mount(App, {
    global: {
      plugins: [pinia, router]
    }
  });
}

describe("AI 与系统设置页", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("使用已初始化配置进入主界面，并通过配置总线保存设置", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-11T08:00:00.000Z"));

    let configResponse = {
      ...runtimeFixtures.initializedConfig
    };

    const fetchMock = createRouteAwareFetch((path, method, init) => {
      if (path === "/api/license/status") {
        return okJsonResponse({
          ...runtimeFixtures.activeLicense,
          activatedAt: "2026-04-11T08:00:00Z"
        });
      }
      if (path === "/api/settings/health") {
        return okJsonResponse({
          ...runtimeFixtures.health,
          now: configResponse.revision === 2 ? "2026-04-11T08:00:00Z" : "2026-04-11T08:05:00Z",
          mode: configResponse.runtime.mode
        });
      }
      if (path === "/api/settings/config" && method === "GET") {
        return okJsonResponse(configResponse);
      }
      if (path === "/api/settings/config" && method === "PUT") {
        configResponse = {
          revision: 3,
          ...JSON.parse(String(init?.body ?? "{}"))
        };
        return okJsonResponse(configResponse);
      }
      if (path === "/api/settings/diagnostics") {
        return okJsonResponse({
          ...runtimeFixtures.initializedDiagnostics,
          revision: configResponse.revision,
          mode: configResponse.runtime.mode
        });
      }
      if (path === "/api/settings/ai-capabilities") {
        return okJsonResponse(runtimeFixtures.aiCapabilitySettings);
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const wrapper = await mountApp("/settings/ai-system");
    await flushPromises();

    expect(wrapper.find('[data-bootstrap-screen="initialization"]').exists()).toBe(false);
    expect(
      (wrapper.get('[data-field="ai.model"]').element as HTMLInputElement).value
    ).toBe("gpt-5.4");
    expect(wrapper.text()).toContain("TK-O****************0001");

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
    expect(wrapper.text()).toContain("配置已就绪");
    expect(wrapper.text()).toContain("最近同步 2026-04-11T08:05:00.000Z");
  });

  it("加载集中式 AI 能力配置，并通过能力总线保存更新", async () => {
    const fetchMock = createRouteAwareFetch((path, method, init) => {
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
      if (path === "/api/settings/ai-capabilities" && method === "GET") {
        return okJsonResponse(runtimeFixtures.aiCapabilitySettings);
      }
      if (path === "/api/settings/ai-capabilities" && method === "PUT") {
        return okJsonResponse(JSON.parse(String(init?.body)));
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const wrapper = await mountApp("/settings/ai-system");
    await flushPromises();

    expect(
      (wrapper.get('[data-field="capability.script_generation.model"]').element as HTMLInputElement)
        .value
    ).toBe("gpt-5");

    await wrapper.get('[data-field="capability.script_generation.model"]').setValue("gpt-5.4");
    await wrapper.get('[data-action="save-capabilities"]').trigger("click");
    await flushPromises();

    const saveCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        String(url).includes("/api/settings/ai-capabilities") && options?.method === "PUT"
    );

    expect(saveCall).toBeTruthy();
    const payload = JSON.parse(String(saveCall?.[1]?.body)) as {
      capabilities: Array<{ capabilityId: string; model: string }>;
    };
    expect(payload.capabilities).toHaveLength(7);
    expect(payload.capabilities.find((item) => item.capabilityId === "script_generation")?.model).toBe(
      "gpt-5.4"
    );
  });
});
