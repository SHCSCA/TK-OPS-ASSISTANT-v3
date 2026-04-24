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
        if (path === "/api/settings/ai-capabilities") {
          return okJsonResponse(runtimeFixtures.aiCapabilitySettings);
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

  it("健康检查屏蔽无权限模型后刷新模型目录和能力矩阵", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        calls.push({ path, method });
        if (path === "/api/settings/ai-capabilities/providers/volcengine/health-check") {
          return okJsonResponse({
            provider: "volcengine",
            status: "misconfigured",
            message: "远端返回 HTTP 404：模型无权限。已从可选模型中屏蔽。",
            model: "doubao-seed-1.6",
            checkedAt: "2026-04-24T08:00:00Z",
            latencyMs: 32
          });
        }
        if (path === "/api/settings/ai-providers/volcengine/models") {
          return okJsonResponse([
            {
              modelId: "doubao-seedance-1-5-pro-251215",
              displayName: "Doubao-Seedance-1.5-pro 251215",
              provider: "volcengine",
              capabilityTypes: ["video_generation"],
              inputModalities: ["text", "image"],
              outputModalities: ["video"],
              contextWindow: null,
              defaultFor: ["video_generation"],
              enabled: true
            }
          ]);
        }
        if (path === "/api/settings/ai-capabilities/support-matrix") {
          return okJsonResponse({
            capabilities: [
              {
                capabilityId: "video_generation",
                providers: ["volcengine"],
                models: [
                  {
                    provider: "volcengine",
                    modelId: "doubao-seedance-1-5-pro-251215",
                    displayName: "Doubao-Seedance-1.5-pro 251215",
                    capabilityTypes: ["video_generation"]
                  }
                ]
              }
            ]
          });
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const store = useAICapabilityStore();
    await store.checkProvider("volcengine", { model: "doubao-seed-1.6" });

    expect(store.providerHealth.volcengine?.status).toBe("misconfigured");
    expect(store.modelCatalogByProvider.volcengine.map((item) => item.modelId)).toEqual([
      "doubao-seedance-1-5-pro-251215"
    ]);
    expect(store.supportMatrix?.capabilities[0].models[0].modelId).toBe(
      "doubao-seedance-1-5-pro-251215"
    );
    expect(calls).toContainEqual({
      method: "GET",
      path: "/api/settings/ai-providers/volcengine/models"
    });
    expect(calls).toContainEqual({
      method: "GET",
      path: "/api/settings/ai-capabilities/support-matrix"
    });
  });
});
