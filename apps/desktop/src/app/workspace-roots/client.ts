import type { AccountWorkspaceRoot } from "./types";
import { WorkspaceRootBridgeError } from "./types";

type WorkspaceRootCommandErrorShape = {
  errorCode: string;
  logId?: string | null;
  message: string;
};

export async function pickAccountWorkspaceRoot(
  accountId: string,
  suggestedName?: string
): Promise<AccountWorkspaceRoot | null> {
  return invokeWorkspaceRoot<AccountWorkspaceRoot | null>(
    "pick_account_workspace_root",
    { accountId, suggestedName: suggestedName || null },
    "无法选择账号工作目录，请重新启动桌面应用。"
  );
}

export async function describeAccountWorkspaceRoot(
  accountId: string,
  rootRef: string
): Promise<AccountWorkspaceRoot> {
  return invokeWorkspaceRoot<AccountWorkspaceRoot>(
    "describe_account_workspace_root",
    { accountId, rootRef },
    "无法读取账号工作目录，请重新授权。"
  );
}

export async function reauthorizeAccountWorkspaceRoot(
  accountId: string,
  rootRef: string
): Promise<AccountWorkspaceRoot | null> {
  return invokeWorkspaceRoot<AccountWorkspaceRoot | null>(
    "reauthorize_account_workspace_root",
    { accountId, rootRef },
    "无法重新授权账号工作目录，请稍后重试。"
  );
}

export async function revokeAccountWorkspaceRoot(
  accountId: string,
  rootRef: string
): Promise<AccountWorkspaceRoot> {
  return invokeWorkspaceRoot<AccountWorkspaceRoot>(
    "revoke_account_workspace_root",
    { accountId, rootRef },
    "无法撤销账号工作目录授权，请稍后重试。"
  );
}

async function invokeWorkspaceRoot<T>(
  command: string,
  args: Record<string, unknown>,
  fallbackMessage: string
): Promise<T> {
  if (!isTauriRuntime()) {
    throw new WorkspaceRootBridgeError(
      "工作目录只能在 TK-OPS 桌面应用中选择。",
      { errorCode: "WORKSPACE_ROOT_BRIDGE_UNAVAILABLE" }
    );
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke<T>(command, args);
  } catch (error) {
    const commandError = readCommandError(error);
    throw new WorkspaceRootBridgeError(
      commandError?.message ?? fallbackMessage,
      {
        cause: error,
        errorCode: commandError?.errorCode ?? "WORKSPACE_ROOT_COMMAND_FAILED",
        logId: commandError?.logId ?? null
      }
    );
  }
}

function readCommandError(value: unknown): WorkspaceRootCommandErrorShape | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const candidate = value as Record<string, unknown>;
  if (
    typeof candidate.errorCode !== "string"
    || typeof candidate.message !== "string"
    || (
      candidate.logId !== undefined
      && candidate.logId !== null
      && typeof candidate.logId !== "string"
    )
  ) {
    return null;
  }
  return {
    errorCode: candidate.errorCode,
    logId: candidate.logId as string | null | undefined,
    message: candidate.message
  };
}

function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}
