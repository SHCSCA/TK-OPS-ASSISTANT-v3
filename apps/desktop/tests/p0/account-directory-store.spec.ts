import { createPinia, setActivePinia } from "pinia";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi
} from "vitest";

const accountApi = vi.hoisted(() => ({
  listAccounts: vi.fn()
}));

vi.mock("@/app/runtime-client/accounts", () => accountApi);

import {
  RuntimeError
} from "@/app/runtime-client/core";
import { useAccountDirectoryStore } from "@/app/account-context/account-directory-store";

describe("P0 账号目录状态", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("Runtime 失败时保留可见错误、日志编号和可重试标记", async () => {
    accountApi.listAccounts.mockRejectedValueOnce(
      new RuntimeError("账号目录加载失败，请稍后重试。", {
        errorCode: "RUNTIME_NOT_READY",
        logId: "log-directory",
        requestId: "request-directory",
        status: 503
      })
    );
    const store = useAccountDirectoryStore();

    await store.load();

    expect(store.status).toBe("error");
    expect(store.error).toEqual({
      message: "账号目录加载失败，请稍后重试。",
      logId: "log-directory",
      requestId: "request-directory",
      retryable: true
    });
  });

  it("重试成功后清除错误并进入真实空态", async () => {
    accountApi.listAccounts
      .mockRejectedValueOnce(
        new RuntimeError("账号目录暂不可用。", {
          errorCode: "RUNTIME_NOT_READY",
          status: 503
        })
      )
      .mockResolvedValueOnce({
        data: {
          items: [],
          totalKnown: 0
        },
        meta: null,
        operationId: null,
        requestId: "request-directory-retry",
        status: 200
      });
    const store = useAccountDirectoryStore();

    await store.load();
    expect(store.status).toBe("error");

    await store.load();
    expect(store.status).toBe("empty");
    expect(store.accounts).toEqual([]);
    expect(store.error).toBeNull();
  });
});
