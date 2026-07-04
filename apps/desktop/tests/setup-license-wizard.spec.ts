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
  activatedLicense?: unknown;
  config?: unknown;
  diagnostics?: unknown;
  readiness?: unknown;
  readinessSequence?: unknown[];
  readinessRequestId?: string;
  directoryReport?: unknown;
  selfCheckReport?: unknown;
  configError?: ReturnType<typeof errorJsonResponse>;
  calls?: Array<{ method: string; path: string }>;
}) {
  const readinessSequence = [...(options.readinessSequence ?? [])];
  return createRouteAwareFetch((path, method) => {
    options.calls?.push({ path, method });
    if (path === "/api/license/status" && method === "GET") {
      return okJsonResponse(options.license ?? runtimeFixtures.activeLicense);
    }
    if (path === "/api/license/activate" && method === "POST") {
      return okJsonResponse(options.activatedLicense ?? runtimeFixtures.activeLicense);
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
    if (path === "/api/bootstrap/readiness" && method === "GET") {
      if (readinessSequence.length > 0) {
        return okJsonResponse(readinessSequence.shift());
      }
      return {
        ...okJsonResponse(options.readiness ?? runtimeFixtures.bootstrapReadiness),
        headers: new Headers({
          "X-Request-ID": options.readinessRequestId ?? "req-bootstrap-readiness"
        })
      };
    }
    if (path === "/api/bootstrap/initialize-directories" && method === "POST") {
      return okJsonResponse(options.directoryReport ?? runtimeFixtures.bootstrapDirectoryReport);
    }
    if (path === "/api/bootstrap/runtime-selfcheck" && method === "POST") {
      return okJsonResponse(options.selfCheckReport ?? runtimeFixtures.runtimeSelfCheckReport);
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
    const readinessResponse = createDeferredResponse();

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
        if (path === "/api/bootstrap/readiness") {
          return Promise.resolve(readinessResponse.promise);
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

  it("未授权时仍展示 Runtime readiness 阻断详情和请求号", async () => {
    vi.stubGlobal(
      "fetch",
      createSetupFetch({
        license: runtimeFixtures.restrictedLicense,
        readiness: runtimeFixtures.blockedBootstrapReadiness,
        readinessRequestId: "req-readiness-blocked"
      })
    );

    const { wrapper } = await mountSetupPage();
    await flushPromises();
    await flushPromises();

    const blockers = wrapper.get('[data-testid="bootstrap-blockers"]');
    expect(wrapper.get('[data-setup-state="blocked"]').exists()).toBe(true);
    expect(blockers.text()).toContain("当前设备还没有可用许可证。");
    expect(blockers.text()).toContain("影响对象：许可证");
    expect(blockers.text()).toContain("请输入有效激活码并完成许可证激活。");
    expect(blockers.text()).toContain("请求号：req-readiness-blocked");
    expect(wrapper.get('[data-testid="readiness-source-hint"]').text()).toContain(
      "当前阻断项来自 Runtime readiness 报告"
    );
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

  it("首启加载完成后展示 Runtime 自检分项", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createSetupFetch({
        calls,
        config: runtimeFixtures.config
      })
    );

    const { wrapper } = await mountSetupPage();
    await flushPromises();
    await flushPromises();
    await flushPromises();

    expect(calls).toContainEqual({ path: "/api/bootstrap/initialize-directories", method: "POST" });
    expect(calls).toContainEqual({ path: "/api/bootstrap/runtime-selfcheck", method: "POST" });

    const selfCheckList = wrapper.get('[data-testid="runtime-selfcheck-list"]');
    expect(selfCheckList.text()).toContain("端口检查");
    expect(selfCheckList.text()).toContain("数据库检查");
    expect(selfCheckList.text()).toContain("依赖检查");
    expect(selfCheckList.text()).toContain("目录状态");
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
    expect(wrapper.get('[data-testid="bootstrap-readiness-list"]').text()).toContain("目录初始化");
  });

  it("展示 Runtime readiness 阻断原因、影响对象和下一步动作", async () => {
    vi.stubGlobal(
      "fetch",
      createSetupFetch({
        config: runtimeFixtures.initializedConfig,
        diagnostics: runtimeFixtures.initializedDiagnostics,
        readiness: runtimeFixtures.blockedBootstrapReadiness
      })
    );

    const { wrapper } = await mountSetupPage();
    await flushPromises();
    await flushPromises();

    const blockers = wrapper.get('[data-testid="bootstrap-blockers"]');
    expect(wrapper.get('[data-setup-state="empty"]').exists()).toBe(true);
    expect(blockers.text()).toContain("当前设备还没有可用许可证。");
    expect(blockers.text()).toContain("影响对象：许可证");
    expect(blockers.text()).toContain("请输入有效激活码并完成许可证激活。");
    expect(wrapper.get('[data-testid="readiness-source-hint"]').text()).toContain(
      "当前阻断项来自 Runtime readiness 报告"
    );
  });

  it("激活成功后刷新 readiness 并移除旧许可证阻断", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createSetupFetch({
        calls,
        license: runtimeFixtures.restrictedLicense,
        config: runtimeFixtures.initializedConfig,
        diagnostics: runtimeFixtures.initializedDiagnostics,
        readinessSequence: [
          runtimeFixtures.blockedBootstrapReadiness,
          runtimeFixtures.blockedBootstrapReadiness,
          runtimeFixtures.bootstrapReadiness
        ]
      })
    );

    const { wrapper } = await mountSetupPage();
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-setup-state="blocked"]').exists()).toBe(true);
    await wrapper.get('[data-field="activationCode"]').setValue("TK-ACTIVE-CODE");
    await wrapper.get('[data-testid="license-activate"]').trigger("click");
    await flushPromises();
    await flushPromises();

    expect(calls).toContainEqual({ path: "/api/license/activate", method: "POST" });
    expect(calls.filter((call) => call.path === "/api/bootstrap/readiness")).toHaveLength(3);
    expect(wrapper.find('[data-testid="bootstrap-blockers"]').exists()).toBe(false);
    expect(wrapper.get('[data-setup-state="ready"]').exists()).toBe(true);
  });

  it("重新检测初始化时执行目录初始化、Runtime 自检和 readiness 拉取", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createSetupFetch({
        calls,
        config: runtimeFixtures.config,
        readiness: runtimeFixtures.blockedBootstrapReadiness
      })
    );

    const { wrapper } = await mountSetupPage();
    await flushPromises();
    await flushPromises();

    await wrapper.get('[data-testid="bootstrap-retry-init"]').trigger("click");
    await flushPromises();

    expect(calls).toContainEqual({ path: "/api/bootstrap/initialize-directories", method: "POST" });
    expect(calls).toContainEqual({ path: "/api/bootstrap/runtime-selfcheck", method: "POST" });
    expect(calls.filter((call) => call.path === "/api/bootstrap/readiness")).toHaveLength(3);
  });

  it("在配置读取失败时展示错误态和请求号", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
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
