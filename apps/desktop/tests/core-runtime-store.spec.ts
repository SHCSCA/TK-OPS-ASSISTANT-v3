import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAICapabilityStore } from "@/stores/ai-capability";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";

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
    expect(projectStore.viewState).toBe("empty");
    expect(licenseStore.viewState).toBe("blocked");
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
