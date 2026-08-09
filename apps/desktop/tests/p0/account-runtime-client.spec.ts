import { afterEach, describe, expect, it, vi } from "vitest";

import {
  activateAccountWorkspace,
  listAccountConnectionCandidates
} from "@/app/runtime-client/accounts";
import { configureStaticRuntimeConnection } from "@/app/runtime-client/core";
import type { AccountDto } from "@/types/runtime/accounts";

let restoreConnection: (() => void) | null = null;

afterEach(() => {
  restoreConnection?.();
  restoreConnection = null;
  vi.unstubAllGlobals();
});

describe("P0 账号 Runtime 客户端补口", () => {
  it("工作区激活携带修订与幂等键，并读取更新后的最近使用时间", async () => {
    restoreConnection = configureStaticRuntimeConnection({
      baseUrl: "http://127.0.0.1:9137",
      sessionToken: "runtime-session"
    });
    const fetchMock = vi.fn().mockResolvedValue(
      response(accountFixture({
        lastUsedAt: "2026-07-26T10:00:00Z",
        revision: 3
      }))
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await activateAccountWorkspace("account-1", {
      expectedRevision: 2,
      idempotencyKey: "activate-account-1"
    });

    expect(result.data.lastUsedAt).toBe("2026-07-26T10:00:00Z");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:9137/api/v1/accounts/account-1/workspace-activation",
      expect.objectContaining({
        method: "POST",
        headers: expect.any(Headers)
      })
    );
    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get("If-Match")).toBe('"2"');
    expect(headers.get("Idempotency-Key")).toBe("activate-account-1");
  });

  it("连接候选只接受工作区、浏览器和执行绑定一致的真实组合", async () => {
    restoreConnection = configureStaticRuntimeConnection({
      baseUrl: "http://127.0.0.1:9137",
      sessionToken: "runtime-session"
    });
    const fetchMock = vi.fn().mockResolvedValue(
      response({
        items: [
          {
            environmentId: "binding-1",
            eligibilityRevision: 8,
            deviceWorkspace: { id: "workspace-1", name: "主工作区", status: "ready" },
            browserInstance: {
              id: "browser-1",
              name: "TikTok 浏览器",
              status: "ready",
              lastCheckedAt: null
            },
            executionBinding: {
              id: "binding-1",
              status: "ready",
              deviceWorkspaceId: "workspace-1",
              browserInstanceId: "browser-1"
            }
          }
        ]
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await listAccountConnectionCandidates("account-1");

    expect(result.data.items).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:9137/api/v1/accounts/account-1/connection/candidates",
      expect.objectContaining({ method: "GET" })
    );
  });
});

function response(data: unknown): Response {
  return new Response(JSON.stringify({ ok: true, data }), {
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": "request-1"
    },
    status: 200
  });
}

function accountFixture(overrides: Partial<AccountDto> = {}): AccountDto {
  const missing = {
    status: "missing" as const,
    label: "未配置",
    errorCode: null,
    logId: null,
    checkedAt: null,
    suggestedAction: null
  };
  return {
    id: "account-1",
    name: "效率观察",
    username: null,
    platform: "tiktok",
    status: "draft",
    positioningSummary: null,
    lastUsedAt: null,
    readiness: {
      connection: { ...missing },
      knowledge: { ...missing },
      ai: { ...missing },
      overall: "blocked",
      checkedAt: null,
      suggestedAction: null
    },
    wizardCompletedAt: null,
    revision: 2,
    ...overrides
  };
}
