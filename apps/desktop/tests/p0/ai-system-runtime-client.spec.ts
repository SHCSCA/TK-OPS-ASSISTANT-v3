import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createModelProfile,
  listCompositionTemplates,
  listPromptProfiles,
  listProviderProfiles,
  updateCapabilityRoute
} from "@/app/runtime-client/ai-system";
import {
  createAccountAIRecipeVersion,
  getAccountAIRecipe
} from "@/app/runtime-client/account-ai-recipe";
import {
  configureRuntimeClientLogger,
  configureStaticRuntimeConnection
} from "@/app/runtime-client/core";

import {
  compositionTemplateFixture,
  modelFixture,
  promptProfileFixture,
  recipeFixture,
  recipeVersionFixture,
  routeFixture
} from "./ai-system-fixtures";

let restoreConnection: (() => void) | null = null;
let restoreLogger: (() => void) | null = null;

afterEach(() => {
  restoreLogger?.();
  restoreLogger = null;
  restoreConnection?.();
  restoreConnection = null;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("P0-E AI Runtime 客户端", () => {
  it("列表请求只访问 v1 本机 Runtime 并携带会话凭据", async () => {
    configureConnection();
    const fetchMock = vi.fn().mockResolvedValue(
      response({ items: [], totalKnown: 0 })
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await listProviderProfiles({
      enabled: true,
      healthStatus: "ready",
      limit: 25
    });

    expect(result.requestId).toBe("request-p0-e");
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(
      "http://127.0.0.1:9137/api/v1/system/providers"
      + "?enabled=true&healthStatus=ready&limit=25"
    );
    const headers = init.headers as Headers;
    expect(init.method).toBe("GET");
    expect(headers.get("Authorization")).toBe("Bearer runtime-session");
    expect(headers.get("Content-Type")).toBeNull();
  });

  it("fresh DB 可手动登记模型并保留幂等键与真实请求体", async () => {
    configureConnection();
    const fetchMock = vi.fn().mockResolvedValue(
      response(modelFixture(), 201)
    );
    vi.stubGlobal("fetch", fetchMock);

    await createModelProfile(
      {
        providerProfileId: "provider-1",
        modelId: "qwen-plus",
        displayName: "Qwen Plus",
        enabled: true
      },
      { idempotencyKey: "manual-model-account-1" }
    );

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(url).toBe("http://127.0.0.1:9137/api/v1/system/models");
    expect(init.method).toBe("POST");
    expect(headers.get("Idempotency-Key")).toBe("manual-model-account-1");
    expect(headers.get("If-Match")).toBeNull();
    expect(JSON.parse(String(init.body))).toEqual({
      providerProfileId: "provider-1",
      modelId: "qwen-plus",
      displayName: "Qwen Plus",
      enabled: true
    });
  });

  it("fresh DB 首条 Route 使用 If-Match 0 且绑定 Prompt 版本行 ID", async () => {
    configureConnection();
    const fetchMock = vi.fn().mockResolvedValue(response(routeFixture()));
    vi.stubGlobal("fetch", fetchMock);

    await updateCapabilityRoute(
      "script_generation",
      {
        primaryModelProfileId: "model-1",
        fallbackModelProfileId: null,
        promptProfileId: "prompt-version-1",
        enabled: true
      },
      {
        expectedRevision: 0,
        idempotencyKey: "route-create-script"
      }
    );

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(url).toBe(
      "http://127.0.0.1:9137/api/v1/system/capability-routes/script_generation"
    );
    expect(init.method).toBe("PUT");
    expect(headers.get("If-Match")).toBe('"0"');
    expect(headers.get("Idempotency-Key")).toBe("route-create-script");
    expect(JSON.parse(String(init.body))).toMatchObject({
      promptProfileId: "prompt-version-1"
    });
  });

  it("Prompt 与合成模板摘要强制激活版本号和版本行 ID 成对出现", async () => {
    configureConnection();
    const logs: unknown[] = [];
    restoreLogger = configureRuntimeClientLogger((event) => logs.push(event));
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({
        items: [promptProfileFixture({ activeVersionId: null })],
        totalKnown: 1
      }))
      .mockResolvedValueOnce(response({
        items: [compositionTemplateFixture({ activeVersion: null })],
        totalKnown: 1
      }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listPromptProfiles()).rejects.toMatchObject({
      errorCode: "INTERNAL_ERROR",
      status: 500
    });
    await expect(listCompositionTemplates()).rejects.toMatchObject({
      errorCode: "INTERNAL_ERROR",
      status: 500
    });
    expect(logs).toHaveLength(2);
  });

  it("Runtime 失败信封保留错误码、字段错误、日志和请求关联 ID", async () => {
    configureConnection();
    const logs: unknown[] = [];
    restoreLogger = configureRuntimeClientLogger((event) => logs.push(event));
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        ok: false,
        error: "配置修订已变化，请刷新后重试。",
        error_code: "REVISION_CONFLICT",
        log_id: "log-p0-e",
        fieldErrors: [{
          field: "If-Match",
          code: "stale_revision",
          message: "当前修订为 4"
        }],
        meta: { currentRevision: 4 }
      }), {
        headers: { "X-Request-ID": "request-conflict" },
        status: 409
      })
    ));

    await expect(listProviderProfiles()).rejects.toMatchObject({
      errorCode: "REVISION_CONFLICT",
      fieldErrors: [{
        field: "If-Match",
        code: "stale_revision",
        message: "当前修订为 4"
      }],
      logId: "log-p0-e",
      requestId: "request-conflict",
      status: 409
    });
    expect(logs).toEqual([
      expect.objectContaining({
        event: "runtime.request.failed",
        errorCode: "REVISION_CONFLICT",
        requestId: "request-conflict"
      })
    ]);
  });

  it("账号 Recipe 客户端绑定账号作用域、修订锁和合成模板版本行 ID", async () => {
    configureConnection();
    const calls: Array<[string, RequestInit]> = [];
    vi.stubGlobal("fetch", vi.fn(async (
      input: RequestInfo | URL,
      init: RequestInit
    ) => {
      calls.push([String(input), init]);
      return init.method === "POST"
        ? response(recipeVersionFixture({ status: "draft", version: 2 }), 201)
        : response(recipeFixture());
    }));

    await getAccountAIRecipe("account-1");
    await createAccountAIRecipeVersion(
      "account-1",
      {
        name: "口播配方",
        routeOverrides: {},
        visualStyle: {},
        voiceProfileRef: null,
        compositionTemplateRef: "composition-version-1",
        costPolicy: {},
        fallbackPolicy: {}
      },
      {
        expectedRevision: 3,
        idempotencyKey: "recipe-create-account-1"
      }
    );

    expect(calls.map(([url]) => url)).toEqual([
      "http://127.0.0.1:9137/api/v1/accounts/account-1/ai-recipe",
      "http://127.0.0.1:9137/api/v1/accounts/account-1/ai-recipe/versions"
    ]);
    const headers = calls[1]?.[1].headers as Headers;
    expect(headers.get("If-Match")).toBe('"3"');
    expect(headers.get("Idempotency-Key")).toBe("recipe-create-account-1");
    expect(JSON.parse(String(calls[1]?.[1].body))).toMatchObject({
      compositionTemplateRef: "composition-version-1"
    });
  });

  it("账号 Recipe 响应越权时在客户端阻止进入当前工作区", async () => {
    configureConnection();
    const logs: unknown[] = [];
    restoreLogger = configureRuntimeClientLogger((event) => logs.push(event));
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(recipeFixture({ accountId: "account-other" }))
      )
    );

    await expect(getAccountAIRecipe("account-1")).rejects.toMatchObject({
      errorCode: "ACCOUNT_SCOPE_MISMATCH",
      status: 403
    });
    expect(logs).toEqual([
      expect.objectContaining({ errorCode: "ACCOUNT_SCOPE_MISMATCH" })
    ]);
  });
});

function configureConnection(): void {
  restoreConnection = configureStaticRuntimeConnection({
    baseUrl: "http://127.0.0.1:9137",
    sessionToken: "runtime-session"
  });
}

function response(data: unknown, status = 200): Response {
  return new Response(JSON.stringify({ ok: true, data }), {
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": "request-p0-e"
    },
    status
  });
}
