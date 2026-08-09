import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AccountDto } from "@/types/runtime/accounts";

const accountApi = vi.hoisted(() => ({
  archiveAccount: vi.fn(),
  bindAccountConnection: vi.fn(),
  completeAccountWizard: vi.fn(),
  copyAccountConfig: vi.fn(),
  createAccount: vi.fn(),
  getAccount: vi.fn(),
  listAccountConnectionCandidates: vi.fn(),
  listAccounts: vi.fn(),
  restoreAccount: vi.fn(),
  startAccountHealthChecks: vi.fn()
}));
const taskPolling = vi.hoisted(() => ({
  waitForAccountTask: vi.fn()
}));

vi.mock("@/app/runtime-client/accounts", () => accountApi);
vi.mock("@/app/runtime-client/task-polling", () => taskPolling);

import { useP0AccountManagementStore } from "@/modules/accounts/account-management-store";

describe("P0 账号管理 store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    taskPolling.waitForAccountTask.mockImplementation(() => new Promise(() => undefined));
  });

  it("归档持久任务完成后刷新账号目录并清除待处理状态", async () => {
    const active = accountFixture({ revision: 3, status: "attention" });
    const archived = accountFixture({ revision: 5, status: "archived" });
    accountApi.archiveAccount.mockResolvedValueOnce(
      result({
        taskId: "task-archive-completed",
        scope: "account",
        accountId: active.id,
        taskType: "account.archive_cleanup",
        status: "queued",
        cancellable: false,
        createdAt: "2026-08-02T09:00:00Z"
      }, 202)
    );
    taskPolling.waitForAccountTask.mockResolvedValueOnce({
      taskId: "task-archive-completed",
      status: "completed",
      completionKind: "succeeded"
    });
    accountApi.listAccounts.mockResolvedValueOnce(
      result({ items: [archived], totalKnown: 1 })
    );
    const store = useP0AccountManagementStore();
    store.accounts = [active];

    await store.archive(active, "停用");

    await vi.waitFor(() => {
      expect(store.pendingTaskIds[active.id]).toBeUndefined();
      expect(store.accounts[0]?.status).toBe("archived");
      expect(store.feedback?.message).toContain("完成安全清理");
    });
  });

  it("区分系统空态与过滤空态，并把筛选交给 v1 Runtime", async () => {
    accountApi.listAccounts.mockResolvedValueOnce(result({ items: [], totalKnown: 0 }));
    const store = useP0AccountManagementStore();

    await store.loadAccounts();
    expect(store.collectionState).toBe("empty");

    accountApi.listAccounts.mockResolvedValueOnce(result({ items: [], totalKnown: 0 }));
    await store.loadAccounts({ q: "未找到", status: "attention" });

    expect(store.collectionState).toBe("filtered-empty");
    expect(accountApi.listAccounts).toHaveBeenLastCalledWith(
      { q: "未找到", status: "attention", limit: 200 },
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
  });

  it("创建账号时固定 TikTok 平台并保存 Runtime 返回的真实草稿", async () => {
    const created = accountFixture({ id: "account-new", status: "draft" });
    accountApi.createAccount.mockResolvedValueOnce(result(created, 201));
    const store = useP0AccountManagementStore();

    const account = await store.createDraft({
      name: "效率观察",
      username: "efficiency.lab",
      platform: "tiktok"
    });

    expect(account).toEqual(created);
    expect(store.accounts).toEqual([created]);
    expect(accountApi.createAccount).toHaveBeenCalledWith(
      expect.objectContaining({ platform: "tiktok" }),
      expect.objectContaining({ idempotencyKey: expect.stringContaining("account-create") })
    );
  });

  it("归档使用修订锁，恢复只显示真实任务而不直接伪造就绪", async () => {
    const active = accountFixture({ revision: 7, status: "attention" });
    const archived = accountFixture({ revision: 8, status: "archived" });
    accountApi.archiveAccount.mockResolvedValueOnce(
      result({
        taskId: "task-archive",
        scope: "account",
        accountId: active.id,
        taskType: "account.archive_cleanup",
        status: "queued",
        cancellable: false,
        createdAt: "2026-07-26T09:00:00Z"
      }, 202)
    );
    accountApi.restoreAccount.mockResolvedValueOnce(
      result({
        taskId: "task-restore",
        scope: "account",
        accountId: active.id,
        taskType: "account.restore_health_check",
        status: "queued",
        cancellable: true,
        createdAt: "2026-07-26T10:00:00Z"
      }, 202)
    );
    const store = useP0AccountManagementStore();
    store.accounts = [active];

    await store.archive(active, "停用");
    expect(accountApi.archiveAccount).toHaveBeenCalledWith(
      active.id,
      { reason: "停用" },
      expect.objectContaining({ expectedRevision: 7 })
    );
    expect(store.pendingTaskIds[active.id]).toBe("task-archive");
    expect(store.accounts[0]?.status).toBe("attention");

    store.accounts = [archived];
    await store.restore(archived);
    expect(store.accounts[0]?.status).toBe("archived");
    expect(store.pendingTaskIds[active.id]).toBe("task-restore");
    expect(store.feedback?.message).toContain("恢复复检任务已提交");
  });
});

function result<T>(data: T, status = 200) {
  return {
    data,
    meta: null,
    operationId: null,
    requestId: "request-1",
    status
  };
}

function accountFixture(overrides: Partial<AccountDto> = {}): AccountDto {
  const readinessItem = {
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
    username: "efficiency.lab",
    platform: "tiktok",
    status: "draft",
    positioningSummary: null,
    lastUsedAt: null,
    readiness: {
      connection: { ...readinessItem },
      knowledge: { ...readinessItem },
      ai: { ...readinessItem },
      overall: "blocked",
      checkedAt: null,
      suggestedAction: null
    },
    wizardCompletedAt: null,
    revision: 1,
    ...overrides
  };
}
