import { afterEach, describe, expect, it, vi } from "vitest";

import {
  RuntimeRequestError,
  fetchAICapabilitySupportMatrix,
  fetchAIProviderCatalog,
  fetchAIProviderModels,
  fetchProviderHealth,
  refreshAIProviderModels,
  updateRuntimeConfig
} from "@/app/runtime-client";

import {
  createRouteAwareFetch,
  errorJsonResponse,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

describe("AI 与系统设置 Runtime client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("读取 Provider 注册表、模型目录和能力支持矩阵", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        calls.push({ path, method });
        if (path === "/api/settings/ai-providers/catalog") {
          return okJsonResponse(runtimeFixtures.aiProviderCatalog);
        }
        if (path === "/api/settings/ai-providers/openai/models") {
          return okJsonResponse(runtimeFixtures.openAIModelCatalog);
        }
        if (path === "/api/settings/ai-capabilities/support-matrix") {
          return okJsonResponse(runtimeFixtures.aiCapabilitySupportMatrix);
        }
        if (path === "/api/settings/ai-providers/openai/models/refresh") {
          return okJsonResponse({
            provider: "openai",
            status: "static_catalog",
            message: "当前模型目录来自内置注册表，暂未执行远端刷新。"
          });
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const catalog = await fetchAIProviderCatalog();
    const models = await fetchAIProviderModels("openai");
    const matrix = await fetchAICapabilitySupportMatrix();
    const refreshResult = await refreshAIProviderModels("openai");

    expect(catalog.map((item) => item.provider)).toContain("deepseek");
    expect(models[0].modelId).toBe("gpt-5.4");
    expect(matrix.capabilities[0].providers).toContain("ollama");
    expect(refreshResult.status).toBe("static_catalog");
    expect(calls).toEqual([
      { path: "/api/settings/ai-providers/catalog", method: "GET" },
      { path: "/api/settings/ai-providers/openai/models", method: "GET" },
      { path: "/api/settings/ai-capabilities/support-matrix", method: "GET" },
      { path: "/api/settings/ai-providers/openai/models/refresh", method: "POST" }
    ]);
  });

  it("把 Provider 聚合健康 overview 归一为前端 readiness 映射", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/ai-providers/health" && method === "GET") {
          return okJsonResponse(runtimeFixtures.providerHealth);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const health = await fetchProviderHealth();

    expect(health.openai).toMatchObject({
      provider: "openai",
      status: "ready",
      message: "OpenAI",
      checkedAt: "2026-04-11T10:00:00Z",
      latencyMs: null
    });
  });

  it("把英文校验失败文案归一为中文错误", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/settings/config" && method === "PUT") {
          return errorJsonResponse(422, "Request validation failed", "req-settings");
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    await expect(
      updateRuntimeConfig({
        ...runtimeFixtures.config,
        runtime: {
          ...runtimeFixtures.config.runtime,
          workspaceRoot: ""
        }
      })
    ).rejects.toMatchObject({
      name: "RuntimeRequestError",
      message: "请求参数校验失败，请检查输入后重试。",
      requestId: "req-settings",
      status: 422
    } satisfies Partial<RuntimeRequestError>);
  });
});
