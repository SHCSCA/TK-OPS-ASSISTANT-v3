import type { AccountControlledFile, ControlledFileFilters } from "./types";
import { ControlledFileBridgeError } from "./types";

type CommandErrorShape = {
  errorCode: string;
  logId?: string | null;
  message: string;
};

export async function pickAccountControlledFile(
  accountId: string,
  rootRef: string,
  filters?: ControlledFileFilters
): Promise<AccountControlledFile | null> {
  return invokeControlledFile<AccountControlledFile | null>(
    "pick_account_controlled_file",
    { accountId, rootRef, filters: filters ?? null },
    "无法选择知识文件，请重新启动桌面应用。"
  );
}

export async function describeAccountControlledFile(
  accountId: string,
  fileRef: string
): Promise<AccountControlledFile> {
  return invokeControlledFile<AccountControlledFile>(
    "describe_account_controlled_file",
    { accountId, fileRef },
    "无法读取文件授权，请重新选择文件。"
  );
}

export async function revokeAccountControlledFile(
  accountId: string,
  fileRef: string
): Promise<AccountControlledFile> {
  return invokeControlledFile<AccountControlledFile>(
    "revoke_account_controlled_file",
    { accountId, fileRef },
    "无法撤销文件授权，请稍后重试。"
  );
}

async function invokeControlledFile<T>(
  command: string,
  args: Record<string, unknown>,
  fallbackMessage: string
): Promise<T> {
  if (!isTauriRuntime()) {
    throw new ControlledFileBridgeError(
      "知识文件只能在 TK-OPS 桌面应用中选择。",
      { errorCode: "CONTROLLED_FILE_BRIDGE_UNAVAILABLE" }
    );
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke<T>(command, args);
  } catch (error) {
    const commandError = readCommandError(error);
    throw new ControlledFileBridgeError(
      commandError?.message ?? fallbackMessage,
      {
        cause: error,
        errorCode: commandError?.errorCode ?? "CONTROLLED_FILE_COMMAND_FAILED",
        logId: commandError?.logId ?? null
      }
    );
  }
}

function readCommandError(value: unknown): CommandErrorShape | null {
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
