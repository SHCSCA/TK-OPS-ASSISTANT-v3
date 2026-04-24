import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory } from "vue-router";
import { openPath } from "@tauri-apps/plugin-opener";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "@/App.vue";
import { createAppRouter } from "@/app/router";

import { createRouteAwareFetch, okJsonResponse, runtimeFixtures } from "./runtime-helpers";

vi.mock("@tauri-apps/plugin-opener", () => ({
  openPath: vi.fn()
}));

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
    vi.mocked(openPath).mockReset();
    vi.unstubAllGlobals();
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
      if (path === "/api/settings/ai-providers/catalog") {
        return okJsonResponse(runtimeFixtures.aiProviderCatalog);
      }
      if (path === "/api/settings/ai-providers/openai/models") {
        return okJsonResponse(runtimeFixtures.openAIModelCatalog);
      }
      if (path === "/api/settings/ai-capabilities/support-matrix") {
        return okJsonResponse(runtimeFixtures.aiCapabilitySupportMatrix);
      }
      if (path === "/api/ai-providers/health") {
        return okJsonResponse(runtimeFixtures.providerHealth);
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    }, { fallbackUnhandledProviderHealth: false });

    vi.stubGlobal("fetch", fetchMock);

    const wrapper = await mountApp("/settings/ai-system");
    await flushPromises();

    expect(wrapper.find('[data-bootstrap-screen="initialization"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("系统总览");
    expect(wrapper.text()).toContain("系统总线");
    expect(wrapper.text()).toContain("Provider 与模型");
    expect(wrapper.text()).toContain("能力矩阵");
    expect(wrapper.text()).toContain("诊断工作台");
    expect(wrapper.find('[data-testid="settings-inline-diagnostics"]').exists()).toBe(true);

    await wrapper.get('[data-section="system"]').trigger("click");
    await flushPromises();

    expect(
      (wrapper.get('select[data-field="runtime.mode"]').element as HTMLSelectElement).value
    ).toBe("development");
    expect(
      (wrapper.get('select[data-field="ai.provider"]').element as HTMLSelectElement).value
    ).toBe("openai");
    expect(
      (wrapper.get('select[data-field="ai.model"]').element as HTMLSelectElement).value
    ).toBe("gpt-5.4");
    expect(wrapper.get('[data-action="pick-workspace-root"]').exists()).toBe(true);
    expect(wrapper.get('[data-action="pick-cache-dir"]').exists()).toBe(true);
    expect(wrapper.get('[data-action="pick-export-dir"]').exists()).toBe(true);
    expect(wrapper.get('[data-action="pick-log-dir"]').exists()).toBe(true);
    vi.mocked(openPath).mockResolvedValue(undefined);
    await wrapper.get('[data-action="pick-log-dir"]').trigger("click");
    await flushPromises();
    expect(openPath).toHaveBeenCalledWith(runtimeFixtures.initializedConfig.paths.logDir);
    expect(wrapper.text()).toContain("已请求系统打开日志目录。");
    // Open detail panel to see masked license code
    await wrapper.find('button[title="切换属性面板"]').trigger("click");
    await flushPromises();

    vi.setSystemTime(new Date("2026-04-11T08:05:00.000Z"));
    await wrapper.get('select[data-field="runtime.mode"]').setValue("production");
    await wrapper.get('select[data-field="logging.level"]').setValue("DEBUG");
    await wrapper.get('select[data-field="ai.model"]').setValue("gpt-5.4-mini");
    await wrapper.get('select[data-field="ai.voice"]').setValue("nova");
    await wrapper.get('select[data-field="ai.subtitleMode"]').setValue("precise");
    expect(wrapper.text()).toContain("待保存变更");
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
    expect(wrapper.text()).toContain("最近同步 2026-04-11");
    expect(wrapper.text()).not.toContain("16:05:00");
    expect(wrapper.text()).not.toContain("Asia/Shanghai");
    expect(wrapper.text()).not.toContain("Z");
  }, 20000);

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
      if (path === "/api/settings/ai-providers/catalog") {
        return okJsonResponse(runtimeFixtures.aiProviderCatalog);
      }
      if (path === "/api/settings/ai-providers/openai/models") {
        return okJsonResponse(runtimeFixtures.openAIModelCatalog);
      }
      if (path === "/api/settings/ai-capabilities/support-matrix") {
        return okJsonResponse(runtimeFixtures.aiCapabilitySupportMatrix);
      }
      if (path === "/api/ai-providers/health") {
        return okJsonResponse(runtimeFixtures.providerHealth);
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    }, { fallbackUnhandledProviderHealth: false });

    vi.stubGlobal("fetch", fetchMock);

    const wrapper = await mountApp("/settings/ai-system");
    await flushPromises();

    await wrapper.get('[data-section="capability"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-capability-id="script_generation"]').trigger("click");
    await flushPromises();

    expect(
      (
        wrapper.get('select[data-field="capability.script_generation.provider"]')
          .element as HTMLSelectElement
      ).value
    ).toBe("openai");
    expect(
      (wrapper.get('select[data-field="capability.script_generation.model"]').element as HTMLSelectElement)
        .value
    ).toBe("gpt-5");

    await wrapper.get('select[data-field="capability.script_generation.model"]').setValue("gpt-5.4");
    expect(wrapper.text()).toContain("待保存变更");
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
  }, 20000);

  it("展示紧凑 Provider 配置，并支持真实连通性测试入口", async () => {
    const fetchMock = createRouteAwareFetch((path, method) => {
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
      if (path === "/api/settings/ai-capabilities") {
        return okJsonResponse(runtimeFixtures.aiCapabilitySettings);
      }
      if (path === "/api/settings/ai-providers/catalog") {
        return okJsonResponse(runtimeFixtures.aiProviderCatalog);
      }
      if (path === "/api/settings/ai-providers/openai/models") {
        return okJsonResponse(runtimeFixtures.openAIModelCatalog);
      }
      if (path === "/api/settings/ai-capabilities/support-matrix") {
        return okJsonResponse(runtimeFixtures.aiCapabilitySupportMatrix);
      }
      if (path === "/api/ai-providers/health") {
        return okJsonResponse(runtimeFixtures.providerHealth);
      }
      if (path === "/api/settings/ai-capabilities/providers/openai/health-check") {
        return okJsonResponse({
          provider: "openai",
          status: "ready",
          message: "OpenAI / GPT-5.4 真实连通性测试通过。",
          model: "gpt-5.4",
          checkedAt: "2026-04-11T10:00:00Z",
          latencyMs: 420
        });
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    }, { fallbackUnhandledProviderHealth: false });

    vi.stubGlobal("fetch", fetchMock);

    const wrapper = await mountApp("/settings/ai-system");
    await flushPromises();

    await wrapper.get('[data-section="provider"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Provider 与模型");
    expect(wrapper.text()).toContain("连接凭据");
    expect(wrapper.find('[data-testid="provider-picker"]').exists()).toBe(true);
    expect(wrapper.findAll(".provider-catalog-card")).toHaveLength(0);

    const providerOptions = wrapper
      .get('select[data-field="provider.selected"]')
      .findAll("option")
      .map((item) => item.text());
    expect(providerOptions).toContain("DeepSeek");
    expect(providerOptions).toContain("Ollama");

    await wrapper.get('select[data-field="provider.health.model"]').setValue("gpt-5.4");
    await wrapper.get('[data-action="check-provider"]').trigger("click");
    await flushPromises();

    const healthCheckCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        String(url).includes("/api/settings/ai-capabilities/providers/openai/health-check") &&
        options?.method === "POST"
    );
    expect(healthCheckCall).toBeTruthy();
    expect(JSON.parse(String(healthCheckCall?.[1]?.body))).toMatchObject({ model: "gpt-5.4" });
    expect(wrapper.get(".detail-panel-container").classes()).toContain("is-open");
    expect(wrapper.text()).toContain("OpenAI / GPT-5.4 真实连通性测试通过。");
  });

  it("在页面右侧保留诊断工作台，并支持通过分区切换打开右侧抽屉", async () => {
    const fetchMock = createRouteAwareFetch((path, method) => {
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
      if (path === "/api/settings/ai-capabilities") {
        return okJsonResponse(runtimeFixtures.aiCapabilitySettings);
      }
      if (path === "/api/settings/ai-providers/catalog") {
        return okJsonResponse(runtimeFixtures.aiProviderCatalog);
      }
      if (path === "/api/settings/ai-providers/openai/models") {
        return okJsonResponse(runtimeFixtures.openAIModelCatalog);
      }
      if (path === "/api/settings/ai-capabilities/support-matrix") {
        return okJsonResponse(runtimeFixtures.aiCapabilitySupportMatrix);
      }
      if (path === "/api/ai-providers/health") {
        return okJsonResponse(runtimeFixtures.providerHealth);
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    }, { fallbackUnhandledProviderHealth: false });

    vi.stubGlobal("fetch", fetchMock);

    const wrapper = await mountApp("/settings/ai-system");
    await flushPromises();

    await wrapper.get('[data-section="diagnostics"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-testid="settings-inline-diagnostics"]').exists()).toBe(true);
    expect(wrapper.get(".detail-panel-container").classes()).toContain("is-open");
    expect(wrapper.text()).toContain("当前运行视图");
    expect(wrapper.text()).toContain("诊断工作台");
  });
});
