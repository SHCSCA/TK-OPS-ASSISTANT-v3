import { defineStore } from "pinia";

import {
  isRuntimeRequestAborted,
  RuntimeError
} from "@/app/runtime-client/core";
import { listAccounts } from "@/app/runtime-client/accounts";
import type { AccountDto } from "@/types/runtime/accounts";

import { consoleAccountContextLogger } from "./unsaved-guard-registry";

export type AccountDirectoryError = {
  message: string;
  logId: string | null;
  requestId: string | null;
  retryable: boolean;
};

type AccountDirectoryState = {
  accounts: AccountDto[];
  status: "idle" | "loading" | "ready" | "empty" | "error";
  totalKnown: number | null;
  error: AccountDirectoryError | null;
};

let requestSequence = 0;
let requestController: AbortController | null = null;

export const useAccountDirectoryStore = defineStore("account-directory", {
  state: (): AccountDirectoryState => ({
    accounts: [],
    status: "idle",
    totalKnown: null,
    error: null
  }),
  actions: {
    async load(): Promise<void> {
      const sequence = ++requestSequence;
      requestController?.abort();
      const controller = new AbortController();
      requestController = controller;
      this.status = "loading";
      this.error = null;
      try {
        const result = await listAccounts(
          { limit: 200 },
          { signal: controller.signal }
        );
        if (sequence !== requestSequence) return;
        this.accounts = result.data.items;
        this.totalKnown = result.data.totalKnown;
        this.status = this.accounts.length > 0 ? "ready" : "empty";
      } catch (error) {
        if (isRuntimeRequestAborted(error) || sequence !== requestSequence) {
          return;
        }
        consoleAccountContextLogger.error(
          "[account-directory] 加载账号目录失败",
          error
        );
        this.status = "error";
        this.error = normalizeDirectoryError(error);
      } finally {
        if (requestController === controller) {
          requestController = null;
        }
      }
    },

    merge(account: AccountDto): void {
      const index = this.accounts.findIndex((item) => item.id === account.id);
      if (index >= 0) this.accounts.splice(index, 1, account);
      else this.accounts.unshift(account);
      this.status = "ready";
    }
  }
});

function normalizeDirectoryError(error: unknown): AccountDirectoryError {
  if (error instanceof RuntimeError) {
    return {
      message: error.message || "账号目录加载失败，请稍后重试。",
      logId: error.logId,
      requestId: error.requestId,
      retryable: error.status >= 500 || error.status === 409
    };
  }
  return {
    message: "账号目录加载失败，请稍后重试。",
    logId: null,
    requestId: null,
    retryable: true
  };
}
