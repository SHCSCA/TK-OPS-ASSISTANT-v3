import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAICapabilityStore } from "@/stores/ai-capability";
import { useBootstrapStore } from "@/stores/bootstrap";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";
import { useTaskBusStore } from "@/stores/task-bus";

import {
  createRouteAwareFetch,
  errorJsonResponse,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

describe("核心 Runtime store 状态语义", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("config-bus、project、license store 通过 viewState 暴露 ready / empty / blocked", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/settings/health" && method === "GET") {
          return okJsonResponse(runtimeFixtures.health);
        }
        if (path === "/api/settings/config" && method === "GET") {
          return okJsonResponse(runtimeFixtures.config);
        }
        if (path === "/api/settings/diagnostics" && method === "GET") {
          return okJsonResponse(runtimeFixtures.diagnostics);
        }
        if (path === "/api/bootstrap/readiness" && method === "GET") {
          return okJsonResponse(runtimeFixtures.bootstrapReadiness);
        }
        if (path === "/api/dashboard/summary" && method === "GET") {
          return okJsonResponse(runtimeFixtures.emptyDashboardSummary);
        }
        if (path === "/api/license/status" && method === "GET") {
          return okJsonResponse(runtimeFixtures.restrictedLicense);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const configStore = useConfigBusStore();
    const projectStore = useProjectStore();
    const licenseStore = useLicenseStore();

    await configStore.load();
    await projectStore.load();
    await licenseStore.loadStatus();

    expect(configStore.viewState).toBe("ready");
    expect(configStore.bootstrapReadiness?.canContinue).toBe(true);
    expect(projectStore.viewState).toBe("empty");
    expect(licenseStore.viewState).toBe("blocked");
  });

  it("config-bus 通过 bootstrap 链路初始化目录、自检和 readiness", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        calls.push({ path, method });
        if (path === "/api/bootstrap/initialize-directories" && method === "POST") {
          return okJsonResponse(runtimeFixtures.bootstrapDirectoryReport);
        }
        if (path === "/api/bootstrap/runtime-selfcheck" && method === "POST") {
          return okJsonResponse(runtimeFixtures.runtimeSelfCheckReport);
        }
        if (path === "/api/bootstrap/readiness" && method === "GET") {
          return okJsonResponse(runtimeFixtures.bootstrapReadiness);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const configStore = useConfigBusStore();
    await configStore.initializeBootstrap();

    expect(calls).toEqual([
      { path: "/api/bootstrap/initialize-directories", method: "POST" },
      { path: "/api/bootstrap/runtime-selfcheck", method: "POST" },
      { path: "/api/bootstrap/readiness", method: "GET" }
    ]);
    expect(configStore.status).toBe("ready");
    expect(configStore.bootstrapDirectoryReport?.status).toBe("ok");
    expect(configStore.runtimeSelfCheckReport?.items[0]?.key).toBe("port");
    expect(configStore.bootstrapReadiness?.canContinue).toBe(true);
  });

  it("config-bus 保存成功后重新同步 Runtime 配置和 readiness", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    const savedConfig = {
      ...runtimeFixtures.config,
      revision: 7
    };
    const syncedConfig = {
      ...runtimeFixtures.initializedConfig,
      revision: 8
    };
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        calls.push({ path, method });
        if (path === "/api/settings/config" && method === "PUT") {
          return okJsonResponse(savedConfig);
        }
        if (path === "/api/settings/health" && method === "GET") {
          return okJsonResponse(runtimeFixtures.health);
        }
        if (path === "/api/settings/config" && method === "GET") {
          return okJsonResponse(syncedConfig);
        }
        if (path === "/api/settings/diagnostics" && method === "GET") {
          return okJsonResponse(runtimeFixtures.initializedDiagnostics);
        }
        if (path === "/api/bootstrap/readiness" && method === "GET") {
          return okJsonResponse(runtimeFixtures.bootstrapReadiness);
        }
        if (path === "/api/ai-providers/health" && method === "GET") {
          return okJsonResponse(runtimeFixtures.providerHealth);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const configStore = useConfigBusStore();
    await configStore.save(savedConfig);

    expect(calls).toEqual([
      { path: "/api/settings/config", method: "PUT" },
      { path: "/api/settings/health", method: "GET" },
      { path: "/api/settings/config", method: "GET" },
      { path: "/api/settings/diagnostics", method: "GET" },
      { path: "/api/bootstrap/readiness", method: "GET" },
      { path: "/api/ai-providers/health", method: "GET" }
    ]);
    expect(configStore.settings?.revision).toBe(8);
    expect(configStore.bootstrapReadiness?.canContinue).toBe(true);
  });

  it("config-bus bootstrap 初始化先完成目录初始化再执行自检", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    const directoryResponse = createDeferredResponse();
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        calls.push({ path, method });
        if (path === "/api/bootstrap/initialize-directories" && method === "POST") {
          return directoryResponse.promise;
        }
        if (path === "/api/bootstrap/runtime-selfcheck" && method === "POST") {
          return okJsonResponse(runtimeFixtures.runtimeSelfCheckReport);
        }
        if (path === "/api/bootstrap/readiness" && method === "GET") {
          return okJsonResponse(runtimeFixtures.bootstrapReadiness);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const configStore = useConfigBusStore();
    const pending = configStore.initializeBootstrap();
    await Promise.resolve();

    expect(calls).toEqual([{ path: "/api/bootstrap/initialize-directories", method: "POST" }]);

    directoryResponse.resolve(okJsonResponse(runtimeFixtures.bootstrapDirectoryReport));
    await pending;

    expect(calls).toEqual([
      { path: "/api/bootstrap/initialize-directories", method: "POST" },
      { path: "/api/bootstrap/runtime-selfcheck", method: "POST" },
      { path: "/api/bootstrap/readiness", method: "GET" }
    ]);
  });

  it("config-bus 复用正在进行的 bootstrap 初始化并只记录一组请求", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    const directoryResponse = createDeferredResponse();
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        calls.push({ path, method });
        if (path === "/api/bootstrap/initialize-directories" && method === "POST") {
          return directoryResponse.promise;
        }
        if (path === "/api/bootstrap/runtime-selfcheck" && method === "POST") {
          return okJsonResponse(runtimeFixtures.runtimeSelfCheckReport);
        }
        if (path === "/api/bootstrap/readiness" && method === "GET") {
          return okJsonResponse(runtimeFixtures.bootstrapReadiness);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const configStore = useConfigBusStore();
    const first = configStore.initializeBootstrap();
    const second = configStore.initializeBootstrap();
    await Promise.resolve();

    directoryResponse.resolve(okJsonResponse(runtimeFixtures.bootstrapDirectoryReport));
    await Promise.all([first, second]);

    expect(calls).toEqual([
      { path: "/api/bootstrap/initialize-directories", method: "POST" },
      { path: "/api/bootstrap/runtime-selfcheck", method: "POST" },
      { path: "/api/bootstrap/readiness", method: "GET" }
    ]);
  });

  it("config-bus 记录保存、初始化和加载失败日志", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/settings/config" && method === "PUT") {
          return errorJsonResponse(500, "保存配置失败", "req-save");
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );
    const saveStore = useConfigBusStore();
    await saveStore.save(runtimeFixtures.config);
    expect(errorSpy).toHaveBeenCalledWith("[config-bus] 保存 Runtime 配置失败", expect.any(Error));

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/bootstrap/initialize-directories" && method === "POST") {
          return errorJsonResponse(500, "目录初始化失败", "req-init");
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );
    await saveStore.initializeBootstrap();
    expect(errorSpy).toHaveBeenCalledWith("[config-bus] Runtime 首启初始化失败", expect.any(Error));

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/settings/health" && method === "GET") {
          return errorJsonResponse(500, "健康检查失败", "req-load");
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );
    await saveStore.load();
    expect(errorSpy).toHaveBeenCalledWith("[config-bus] Runtime 配置加载失败", expect.any(Error));
  });

  it("config.changed 重新同步 readiness 失败时进入统一错误态", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/settings/health" && method === "GET") {
          return okJsonResponse(runtimeFixtures.health);
        }
        if (path === "/api/settings/config" && method === "GET") {
          return okJsonResponse(runtimeFixtures.initializedConfig);
        }
        if (path === "/api/settings/diagnostics" && method === "GET") {
          return okJsonResponse(runtimeFixtures.initializedDiagnostics);
        }
        if (path === "/api/bootstrap/readiness" && method === "GET") {
          return errorJsonResponse(500, "Runtime readiness 检查失败", "req-readiness");
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const configStore = useConfigBusStore();
    configStore.settings = runtimeFixtures.config;
    configStore.status = "ready";
    configStore.runtimeStatus = "online";
    configStore.bootstrapReadiness = runtimeFixtures.bootstrapReadiness;
    configStore.initializeEventSubscription();

    useTaskBusStore().handleIncomingMessage(
      JSON.stringify({
        schema_version: 1,
        type: "config.changed",
        revision: 3
      })
    );
    await vi.waitFor(() => expect(configStore.status).toBe("error"));
    expect(configStore.runtimeStatus).toBe("offline");
    expect(configStore.error?.message).toBe("Runtime readiness 检查失败");
    expect(configStore.bootstrapReadiness).toBeNull();
    expect(errorSpy).toHaveBeenCalledWith(
      "[config-bus] 配置变更后重新同步失败",
      expect.any(Error)
    );
  });

  it("config.changed 让 readiness 变为阻断时同步全局首启阶段", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/settings/config" && method === "GET") {
          return okJsonResponse(runtimeFixtures.initializedConfig);
        }
        if (path === "/api/settings/diagnostics" && method === "GET") {
          return okJsonResponse(runtimeFixtures.initializedDiagnostics);
        }
        if (path === "/api/bootstrap/readiness" && method === "GET") {
          return okJsonResponse(runtimeFixtures.blockedBootstrapReadiness);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const configStore = useConfigBusStore();
    const licenseStore = useLicenseStore();
    const bootstrapStore = useBootstrapStore();
    licenseStore.applyLicenseStatus(runtimeFixtures.activeLicense);
    licenseStore.status = "ready";
    configStore.settings = runtimeFixtures.initializedConfig;
    configStore.status = "ready";
    configStore.runtimeStatus = "online";
    configStore.bootstrapReadiness = runtimeFixtures.bootstrapReadiness;
    bootstrapStore.phase = "ready";
    configStore.initializeEventSubscription();

    useTaskBusStore().handleIncomingMessage(
      JSON.stringify({
        schema_version: 1,
        type: "config.changed",
        revision: 3
      })
    );

    await vi.waitFor(() => expect(configStore.bootstrapReadiness?.canContinue).toBe(false));
    expect(bootstrapStore.phase).toBe("initialization_required");
  });

  it("ai-capability store 支持刷新 Provider 模型目录并保留 ready 视图态", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/settings/ai-capabilities" && method === "GET") {
          return okJsonResponse(runtimeFixtures.aiCapabilitySettings);
        }
        if (path === "/api/settings/ai-providers/catalog" && method === "GET") {
          return okJsonResponse(runtimeFixtures.aiProviderCatalog);
        }
        if (path === "/api/settings/ai-capabilities/support-matrix" && method === "GET") {
          return okJsonResponse(runtimeFixtures.aiCapabilitySupportMatrix);
        }
        if (path === "/api/settings/ai-providers/openai/models/refresh" && method === "POST") {
          return okJsonResponse({
            provider: "openai",
            status: "static_catalog",
            message: "当前模型目录来自内置注册表，暂未执行远端刷新。"
          });
        }
        if (path === "/api/settings/ai-providers/openai/models" && method === "GET") {
          return okJsonResponse(runtimeFixtures.openAIModelCatalog);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const store = useAICapabilityStore();
    await Promise.all([store.load(), store.loadProviderCatalog(), store.loadSupportMatrix()]);
    await store.refreshProviderModels("openai");

    expect(store.viewState).toBe("ready");
    expect(store.refreshResultByProvider.openai?.status).toBe("static_catalog");
    expect(store.modelCatalogByProvider.openai[0]?.modelId).toBe("gpt-5.4");
  });

  it("config-bus 请求失败时保留中文错误文案", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/settings/config" && method === "PUT") {
          return errorJsonResponse(422, "Request validation failed", "req-config");
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const store = useConfigBusStore();
    await store.save({
      ...runtimeFixtures.config,
      runtime: {
        ...runtimeFixtures.config.runtime,
        workspaceRoot: ""
      }
    });

    expect(store.status).toBe("error");
    expect(store.error?.message).toBe("请求参数校验失败，请检查输入后重试。");
    expect(store.viewState).toBe("error");
  });
});

function createDeferredResponse() {
  let resolve!: (value: unknown) => void;
  const promise = new Promise((promiseResolve) => {
    resolve = promiseResolve;
  });

  return { promise, resolve };
}
