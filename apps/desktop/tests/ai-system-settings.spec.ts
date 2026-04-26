import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory } from "vue-router";
import { open } from "@tauri-apps/plugin-dialog";
import { openPath } from "@tauri-apps/plugin-opener";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "@/App.vue";
import { createAppRouter } from "@/app/router";

import { createRouteAwareFetch, okJsonResponse, runtimeFixtures } from "./runtime-helpers";

vi.mock("@tauri-apps/plugin-opener", () => ({
  openPath: vi.fn()
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: vi.fn()
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

function createLargeModelCatalog(count: number) {
  return Array.from({ length: count }, (_, index) => {
    const number = index + 1;
    return {
      modelId: `bulk-model-${String(number).padStart(2, "0")}`,
      displayName: `批量模型 ${number}`,
      provider: "openai",
      capabilityTypes: number % 3 === 0 ? ["text_generation", "vision"] : ["text_generation"],
      inputModalities: number % 3 === 0 ? ["text", "image"] : ["text"],
      outputModalities: ["text"],
      contextWindow: null,
      defaultFor: [],
      enabled: true
    };
  });
}

describe("AI 与系统设置页", () => {
  afterEach(() => {
    vi.mocked(open).mockReset();
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
    expect(wrapper.text()).toContain("检测中心");
    expect(wrapper.find('[data-section="diagnostics"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="settings-inline-diagnostics"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("打开右侧抽屉");
    expect(wrapper.find('button[title="切换属性面板"]').exists()).toBe(false);

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
    expect(wrapper.get('[data-action="pick-ffprobe-path"]').exists()).toBe(true);
    vi.mocked(open).mockResolvedValue("C:\\TK-OPS\\workspace");
    await wrapper.get('[data-action="pick-workspace-root"]').trigger("click");
    await flushPromises();
    expect(open).toHaveBeenCalledWith({
      defaultPath: runtimeFixtures.initializedConfig.runtime.workspaceRoot,
      directory: true,
      multiple: false
    });

    vi.mocked(open).mockResolvedValue("C:\\TK-OPS\\tools\\ffprobe.exe");
    await wrapper.get('[data-action="pick-ffprobe-path"]').trigger("click");
    await flushPromises();
    expect(open).toHaveBeenCalledWith({
      defaultPath: runtimeFixtures.initializedConfig.media.ffprobePath || undefined,
      directory: false,
      filters: [{ extensions: ["exe"], name: "FFprobe" }],
      multiple: false
    });

    vi.mocked(openPath).mockResolvedValue(undefined);
    await wrapper.get('[data-action="pick-log-dir"]').trigger("click");
    await flushPromises();
    expect(openPath).toHaveBeenCalledWith(runtimeFixtures.initializedConfig.paths.logDir);
    expect(wrapper.text()).toContain("已请求系统打开日志目录。");
    await wrapper.get(".shell-title-bar__detail-toggle").trigger("click");
    await flushPromises();
    expect(wrapper.get(".detail-panel-container").classes()).toContain("is-open");
    expect(wrapper.get(".shell-detail-panel").text()).toContain("系统边界");
    expect(wrapper.get(".shell-detail-panel").text()).toContain("当前焦点");

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
        mode: "production",
        workspaceRoot: "C:\\TK-OPS\\workspace"
      },
      logging: {
        level: "DEBUG"
      },
      ai: {
        model: "gpt-5.4-mini",
        voice: "nova",
        subtitleMode: "precise"
      },
      media: {
        ffprobePath: "C:\\TK-OPS\\tools\\ffprobe.exe"
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
    const providerSelect = wrapper.get('select[data-field="capability.script_generation.provider"]')
      .element as HTMLSelectElement;
    const providerOptions = Array.from(providerSelect.options);
    expect(providerOptions.map((option) => option.value)).toEqual(
      expect.arrayContaining(["openai", "deepseek", "qwen", "volcengine", "ollama", "custom_openai_compatible"])
    );
    expect(providerOptions.find((option) => option.value === "qwen")?.disabled).toBe(false);
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
      capabilities: Array<{
        capabilityId: string;
        model: string;
        systemPrompt?: string;
        userPromptTemplate?: string;
      }>;
    };
    expect(payload.capabilities).toHaveLength(7);
    expect(payload.capabilities.find((item) => item.capabilityId === "script_generation")?.model).toBe(
      "gpt-5.4"
    );
    expect(payload.capabilities[0]).not.toHaveProperty("systemPrompt");
    expect(payload.capabilities[0]).not.toHaveProperty("userPromptTemplate");
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
    expect(wrapper.find(".provider-hub-layout").exists()).toBe(true);
    expect(wrapper.find(".provider-connected-list").exists()).toBe(true);
    expect(wrapper.find(".provider-template-library").exists()).toBe(true);
    expect(wrapper.find(".provider-model-directory").exists()).toBe(true);
    expect(wrapper.find(".provider-credential-inspector").exists()).toBe(true);
    expect(wrapper.text()).toContain("连接凭据");
    expect(wrapper.text()).toContain("厂商模板库");
    expect(wrapper.text()).toContain("新增自定义");
    expect(wrapper.find('[data-testid="provider-picker"]').exists()).toBe(true);
    expect(wrapper.findAll(".provider-catalog-card")).toHaveLength(0);
    expect(wrapper.findAll(".provider-connected-list__item").length).toBeLessThan(
      runtimeFixtures.aiProviderCatalog.length
    );

    const providerOptions = wrapper
      .get('select[data-field="provider.selected"]')
      .findAll("option")
      .map((item) => item.text());
    expect(providerOptions).toContain("DeepSeek");
    expect(providerOptions).toContain("Ollama");
    expect(wrapper.text()).toContain("文本");
    expect(wrapper.text()).toContain("视觉");

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

  it("模型目录最多同时显示 10 条，并支持分页与筛选", async () => {
    const largeModelCatalog = createLargeModelCatalog(25);
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
        return okJsonResponse(largeModelCatalog);
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

    await wrapper.get('[data-section="provider"]').trigger("click");
    await flushPromises();

    let modelListText = wrapper.get(".provider-model-list").text();
    expect(wrapper.findAll(".provider-model-list__item")).toHaveLength(10);
    expect(wrapper.text()).toContain("1-10 / 25");
    expect(modelListText).toContain("批量模型 1");
    expect(modelListText).not.toContain("批量模型 25");

    await wrapper.get('[data-action="provider.model.next-page"]').trigger("click");
    await flushPromises();

    modelListText = wrapper.get(".provider-model-list").text();
    expect(wrapper.findAll(".provider-model-list__item")).toHaveLength(10);
    expect(wrapper.text()).toContain("11-20 / 25");
    expect(wrapper.findAll(".provider-model-list__item")[0].text()).toContain("批量模型 11");
    expect(modelListText).not.toContain("批量模型 25");

    await wrapper.get('input[data-field="provider.model.search"]').setValue("批量模型 25");
    await flushPromises();

    modelListText = wrapper.get(".provider-model-list").text();
    expect(wrapper.findAll(".provider-model-list__item")).toHaveLength(1);
    expect(wrapper.text()).toContain("1-1 / 1");
    expect(modelListText).toContain("批量模型 25");
  });

  it("在检测中心一键检测系统运行必需配置", async () => {
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
    expect(wrapper.text()).toContain("检测中心");
    expect(wrapper.text()).toContain("FFprobe 媒体探针");
    expect(wrapper.text()).toContain("准备媒体工具");

    await wrapper.get('[data-action="run-system-diagnostics"]').trigger("click");
    await flushPromises();

    const diagnosticsCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url).includes("/api/settings/diagnostics")
    );
    expect(diagnosticsCalls.length).toBeGreaterThanOrEqual(2);
  });

  it("目录选择失败时不回退 prompt，并给出桌面壳提示", async () => {
    const promptSpy = vi.fn();
    vi.stubGlobal("prompt", promptSpy);
    vi.mocked(open).mockRejectedValue(new Error("dialog unavailable"));

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

    await wrapper.get('[data-section="system"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-action="pick-cache-dir"]').trigger("click");
    await flushPromises();

    expect(promptSpy).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("当前环境无法打开系统目录选择器");
  });
});
