import { mount, flushPromises } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import SetupLicenseWizardPage from "@/pages/setup/SetupLicenseWizardPage.vue";

import { createRouteAwareFetch, okJsonResponse, runtimeFixtures } from "./runtime-helpers";

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

function createSetupFetch(options: {
  license?: unknown;
  config?: unknown;
  diagnostics?: unknown;
  configError?: ReturnType<typeof errorJsonResponse>;
}) {
  return createRouteAwareFetch((path, method) => {
    if (path === "/api/license/status" && method === "GET") {
      return okJsonResponse(options.license ?? runtimeFixtures.activeLicense);
    }
    if (path === "/api/settings/health" && method === "GET") {
      return okJsonResponse(runtimeFixtures.health);
    }
    if (path === "/api/settings/config" && method === "GET") {
      return options.configError ?? okJsonResponse(options.config ?? runtimeFixtures.config);
    }
    if (path === "/api/settings/diagnostics" && method === "GET") {
      return okJsonResponse(options.diagnostics ?? runtimeFixtures.diagnostics);
    }

    throw new Error(`Unhandled request: ${method} ${path}`);
  });
}

async function mountSetupPage() {
  const pinia = createPinia();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: SetupLicenseWizardPage },
      { path: "/dashboard", component: { template: "<div />" } },
      { path: "/settings/ai-system", component: { template: "<div />" } }
    ]
  });

  router.push("/");
  await router.isReady();

  const wrapper = mount(SetupLicenseWizardPage, {
    global: {
      plugins: [pinia, router]
    }
  });

  return { router, wrapper };
}

describe("SetupLicenseWizardPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("在 Runtime 尚未返回时保持加载状态", async () => {
    const licenseResponse = createDeferredResponse();
    const healthResponse = createDeferredResponse();
    const configResponse = createDeferredResponse();
    const diagnosticsResponse = createDeferredResponse();

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const path = new URL(String(input)).pathname;
        if (path === "/api/license/status") {
          return Promise.resolve(licenseResponse.promise);
        }
        if (path === "/api/settings/health") {
          return Promise.resolve(healthResponse.promise);
        }
        if (path === "/api/settings/config") {
          return Promise.resolve(configResponse.promise);
        }
        if (path === "/api/settings/diagnostics") {
          return Promise.resolve(diagnosticsResponse.promise);
        }

        throw new Error(`Unhandled request: ${path}`);
      })
    );

    const { wrapper } = await mountSetupPage();
    await flushPromises();

    expect(wrapper.get('[data-setup-state="loading"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("首启");
  });

  it("在未授权时展示阻断态并保留本机机器码", async () => {
    vi.stubGlobal("fetch", createSetupFetch({ license: runtimeFixtures.restrictedLicense }));

    const { wrapper } = await mountSetupPage();
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-setup-state="blocked"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("待授权");
    expect(wrapper.text()).toContain(runtimeFixtures.restrictedLicense.machineCode);
    expect(wrapper.get('[data-field="activationCode"]').attributes("disabled")).toBeUndefined();
  });

  it("在授权但初始化未完成时展示空态", async () => {
    vi.stubGlobal("fetch", createSetupFetch({ config: runtimeFixtures.config }));

    const { wrapper } = await mountSetupPage();
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-setup-state="empty"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("初始化");
    expect(wrapper.text()).toContain("继续初始化");
  });

  it("在授权且初始化完成后展示就绪态", async () => {
    vi.stubGlobal(
      "fetch",
      createSetupFetch({
        config: runtimeFixtures.initializedConfig,
        diagnostics: runtimeFixtures.initializedDiagnostics
      })
    );

    const { wrapper } = await mountSetupPage();
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-setup-state="ready"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("Runtime");
    expect(wrapper.get('[data-field="activationCode"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-action="open-dashboard"]').exists()).toBe(true);
  });

  it("在配置读取失败时展示错误态和请求号", async () => {
    vi.stubGlobal(
      "fetch",
      createSetupFetch({
        configError: errorJsonResponse(500, "初始化配置读取失败。", "req-config-500")
      })
    );

    const { wrapper } = await mountSetupPage();
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-setup-state="error"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("初始化配置读取失败。");
    expect(wrapper.text()).toContain("req-config-500");
  });
});
