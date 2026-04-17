import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAICapabilityStore } from "@/stores/ai-capability";

import { createRouteAwareFetch, okJsonResponse, runtimeFixtures } from "./runtime-helpers";

describe("AI 能力 store 多 Provider 行为", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("加载 Provider 注册表、模型目录、支持矩阵并保存 Provider secret", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });
        if (path === "/api/settings/ai-providers/catalog") {
          return okJsonResponse(runtimeFixtures.aiProviderCatalog);
        }
        if (path === "/api/settings/ai-providers/openai/models") {
          return okJsonResponse(runtimeFixtures.openAIModelCatalog);
        }
        if (path === "/api/settings/ai-capabilities/support-matrix") {
          return okJsonResponse(runtimeFixtures.aiCapabilitySupportMatrix);
        }
        if (path === "/api/settings/ai-capabilities/providers/openai/secret") {
          return okJsonResponse({
            ...runtimeFixtures.aiProviderCatalog[0],
            maskedSecret: "sk-c************3456"
          });
        }
        if (path === "/api/settings/ai-capabilities/providers/openai/health-check") {
          return okJsonResponse({
            provider: "openai",
            status: "ready",
            message: "Provider 已可用于文本生成。"
          });
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const store = useAICapabilityStore();
    await store.loadProviderCatalog();
    await store.loadProviderModels("openai");
    await store.loadSupportMatrix();
    await store.saveProviderSecret("openai", {
      apiKey: "sk-client-secret",
      baseUrl: "https://api.openai.com/v1/responses"
    });
    await store.checkProvider("openai");

    expect(store.providerCatalog.map((item) => item.provider)).toContain("ollama");
    expect(store.modelCatalogByProvider.openai[0].modelId).toBe("gpt-5.4");
    expect(store.supportMatrix?.capabilities[0].providers).toContain("deepseek");
    expect(store.providerHealth.openai?.status).toBe("ready");
    expect(store.status).toBe("ready");
    expect(calls).toContainEqual({
      path: "/api/settings/ai-capabilities/providers/openai/secret",
      method: "PUT",
      body: {
        apiKey: "sk-client-secret",
        baseUrl: "https://api.openai.com/v1/responses"
      }
    });
  });
});
