import { afterEach, describe, expect, it, vi } from "vitest";

import {
  activateAccountPositioningVersion,
  createAccountKnowledgeSource,
  getAccountPositioning,
  getAccountPositioningVersion,
  listAccountKnowledgeSources
} from "@/app/runtime-client/account-knowledge";
import {
  configureRuntimeClientLogger,
  configureStaticRuntimeConnection
} from "@/app/runtime-client/core";

let restoreConnection: (() => void) | null = null;
let restoreLogger: (() => void) | null = null;

afterEach(() => {
  restoreLogger?.();
  restoreLogger = null;
  restoreConnection?.();
  restoreConnection = null;
  vi.unstubAllGlobals();
});

describe("P0 定位与知识 Runtime 客户端", () => {
  it("严格映射账号作用域、分页筛选、修订与幂等请求头", async () => {
    restoreConnection = configureStaticRuntimeConnection({
      baseUrl: "http://127.0.0.1:9137",
      sessionToken: "runtime-session"
    });
    const calls: Array<{ url: string; init: RequestInit }> = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init: RequestInit) => {
      calls.push({ url: String(input), init });
      const path = new URL(String(input)).pathname;
      if (path.endsWith("/positioning/versions/2/activate")) {
        return response(positioningFixture({ activeVersion: 2, revision: 5 }));
      }
      if (path.endsWith("/knowledge/sources") && init.method === "POST") {
        return response(sourceFixture(), 201, { revision: 5 });
      }
      if (path.endsWith("/knowledge/sources")) {
        return response({ items: [sourceFixture()], totalKnown: 1 });
      }
      return response(positioningFixture());
    }));

    await getAccountPositioning("account-1");
    await listAccountKnowledgeSources("account-1", {
      kind: "reference",
      status: "ready",
      limit: 20
    });
    await createAccountKnowledgeSource(
      "account-1",
      {
        kind: "reference",
        sourceMode: "url",
        title: "公开文档",
        url: "https://example.com/guide"
      },
      { idempotencyKey: "source-create-1" }
    );
    await activateAccountPositioningVersion("account-1", 2, {
      expectedRevision: 4,
      idempotencyKey: "positioning-activate-2"
    });

    expect(calls.map((item) => item.url)).toEqual([
      "http://127.0.0.1:9137/api/v1/accounts/account-1/positioning",
      "http://127.0.0.1:9137/api/v1/accounts/account-1/knowledge/sources?limit=20&kind=reference&status=ready",
      "http://127.0.0.1:9137/api/v1/accounts/account-1/knowledge/sources",
      "http://127.0.0.1:9137/api/v1/accounts/account-1/positioning/versions/2/activate"
    ]);
    const sourceHeaders = calls[2]?.init.headers as Headers;
    const activateHeaders = calls[3]?.init.headers as Headers;
    expect(sourceHeaders.get("Idempotency-Key")).toBe("source-create-1");
    expect(JSON.parse(String(calls[2]?.init.body))).toEqual({
      kind: "reference",
      sourceMode: "url",
      title: "公开文档",
      url: "https://example.com/guide"
    });
    expect(activateHeaders.get("If-Match")).toBe('"4"');
    expect(activateHeaders.get("Idempotency-Key")).toBe("positioning-activate-2");
  });

  it("阻止其他账号的响应进入当前账号缓存", async () => {
    const logs: unknown[] = [];
    restoreLogger = configureRuntimeClientLogger((event) => logs.push(event));
    restoreConnection = configureStaticRuntimeConnection({
      baseUrl: "http://127.0.0.1:9137",
      sessionToken: "runtime-session"
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(positioningFixture({ accountId: "account-other" }))
      )
    );

    await expect(getAccountPositioning("account-1")).rejects.toMatchObject({
      errorCode: "ACCOUNT_SCOPE_MISMATCH",
      status: 403
    });
    expect(logs).toEqual([
      expect.objectContaining({ errorCode: "ACCOUNT_SCOPE_MISMATCH" })
    ]);
  });

  it("读取账号定位版本详情并拒绝响应版本漂移", async () => {
    const logs: unknown[] = [];
    restoreLogger = configureRuntimeClientLogger((event) => logs.push(event));
    restoreConnection = configureStaticRuntimeConnection({
      baseUrl: "http://127.0.0.1:9137",
      sessionToken: "runtime-session"
    });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(positioningVersionFixture()))
      .mockResolvedValueOnce(response(positioningVersionFixture({ version: 3 })));
    vi.stubGlobal("fetch", fetchMock);

    const detail = await getAccountPositioningVersion("account-1", 2);

    expect(detail.data.audience).toEqual({ description: "独立开发者" });
    expect(fetchMock.mock.calls[0]?.[0].toString()).toBe(
      "http://127.0.0.1:9137/api/v1/accounts/account-1/positioning/versions/2"
    );
    await expect(
      getAccountPositioningVersion("account-1", 2)
    ).rejects.toMatchObject({
      errorCode: "INTERNAL_ERROR",
      status: 500
    });
    expect(logs).toEqual([
      expect.objectContaining({ errorCode: "INTERNAL_ERROR" })
    ]);
  });
});

function response(
  data: unknown,
  status = 200,
  meta?: Record<string, unknown>
): Response {
  return new Response(JSON.stringify({ ok: true, data, meta }), {
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": "request-1"
    },
    status
  });
}

function positioningFixture(overrides: Record<string, unknown> = {}) {
  return {
    accountId: "account-1",
    activeVersion: null,
    versions: [],
    revision: 4,
    ...overrides
  };
}

function positioningVersionFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: "positioning-2",
    accountId: "account-1",
    version: 2,
    status: "active",
    summary: "面向独立开发者 · 产品拆解 / 增长实验",
    createdAt: "2026-08-02T10:00:00Z",
    audience: { description: "独立开发者" },
    contentPillars: ["产品拆解", "增长实验"],
    tone: { description: "直接、克制、有证据" },
    prohibitedTopics: ["收益承诺"],
    publishingConstraints: { description: "结论附带来源" },
    contentHash: "a".repeat(64),
    activatedAt: "2026-08-02T11:00:00Z",
    revision: 2,
    ...overrides
  };
}

function sourceFixture() {
  return {
    id: "source-1",
    accountId: "account-1",
    kind: "reference",
    sourceMode: "url",
    title: "公开文档",
    status: "ready",
    controlledRef: null,
    sourceUrl: "https://example.com/guide",
    contentHash: "a".repeat(64),
    indexedAt: "2026-07-26T10:00:00Z",
    removedAt: null,
    errorCode: null,
    logId: null,
    revision: 1
  };
}
