import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  describeAccountWorkspaceRoot,
  pickAccountWorkspaceRoot,
  WorkspaceRootBridgeError
} from "@/app/workspace-roots";

const invokeMock = vi.hoisted(() => vi.fn());

vi.mock("@tauri-apps/api/core", () => ({
  invoke: invokeMock
}));

describe("P0-G 账号工作目录桥", () => {
  beforeEach(() => {
    invokeMock.mockReset();
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {},
      writable: true
    });
  });

  it("用户取消原生目录选择时返回 null", async () => {
    invokeMock.mockResolvedValueOnce(null);

    await expect(
      pickAccountWorkspaceRoot("account-a", "账号 A")
    ).resolves.toBeNull();
    expect(invokeMock).toHaveBeenCalledWith(
      "pick_account_workspace_root",
      { accountId: "account-a", suggestedName: "账号 A" }
    );
  });

  it("只向 Tauri 传账号和 rootRef，不向 Runtime 发送绝对路径", async () => {
    invokeMock.mockResolvedValueOnce({
      displayName: "account-a",
      displayPath: "D:\\TK-OPS\\account-a",
      revision: 1,
      rootRef: "wr_0123456789abcdef0123456789abcdef",
      status: "active"
    });

    const result = await describeAccountWorkspaceRoot(
      "account-a",
      "wr_0123456789abcdef0123456789abcdef"
    );

    expect(result.displayName).toBe("account-a");
    expect(invokeMock).toHaveBeenCalledWith(
      "describe_account_workspace_root",
      {
        accountId: "account-a",
        rootRef: "wr_0123456789abcdef0123456789abcdef"
      }
    );
  });

  it("保留稳定错误码和日志引用", async () => {
    invokeMock.mockRejectedValueOnce({
      errorCode: "WORKSPACE_ROOT_DANGEROUS",
      logId: "wrl-1",
      message: "不能选择系统目录。"
    });

    const error = await pickAccountWorkspaceRoot("account-a")
      .catch((value: unknown) => value);

    expect(error).toBeInstanceOf(WorkspaceRootBridgeError);
    expect(error).toMatchObject({
      errorCode: "WORKSPACE_ROOT_DANGEROUS",
      logId: "wrl-1",
      message: "不能选择系统目录。"
    });
  });
});
