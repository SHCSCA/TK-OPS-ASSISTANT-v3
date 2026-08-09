import { defineStore } from "pinia";
import {
  archiveAccount,
  bindAccountConnection,
  completeAccountWizard,
  copyAccountConfig,
  createAccount,
  getAccount,
  getAccountConnection,
  listAccountConnectionCandidates,
  listAccounts,
  restoreAccount,
  startAccountHealthChecks
} from "@/app/runtime-client/accounts";
import { isRuntimeRequestAborted } from "@/app/runtime-client/core";
import { waitForAccountTask } from "@/app/runtime-client/task-polling";
import type {
  AccountCopyInput,
  AccountCreateInput,
  AccountDto,
  AccountListQuery,
  AccountWizardStep,
  ConnectionCandidatesDto,
  ConnectionDto,
  HealthCheckInput
} from "@/types/runtime/accounts";
import { createOperationKey, toAccountUiError } from "./account-errors";
import { notifyAccountDirectoryChanged } from "./account-directory-events";
import type {
  AccountCollectionState,
  AccountListFilters,
  AccountOperationFeedback,
  AccountUiError
} from "./account-management-types";
type AccountManagementState = {
  accounts: AccountDto[];
  collectionState: AccountCollectionState;
  filters: AccountListFilters;
  selectedAccountId: string | null;
  totalKnown: number | null;
  error: AccountUiError | null;
  feedback: AccountOperationFeedback | null;
  busyKey: string | null;
  pendingTaskIds: Record<string, string>;
};
let listController: AbortController | null = null;
let listSequence = 0;
const archiveTaskControllers = new Map<string, AbortController>();
export const useP0AccountManagementStore = defineStore("p0-account-management", {
  state: (): AccountManagementState => ({
    accounts: [],
    collectionState: "idle",
    filters: { q: "", status: "" },
    selectedAccountId: null,
    totalKnown: null,
    error: null,
    feedback: null,
    busyKey: null,
    pendingTaskIds: {}
  }),
  getters: {
    selectedAccount(state): AccountDto | null {
      return (
        state.accounts.find((item) => item.id === state.selectedAccountId) ?? null
      );
    },
    hasFilters(state): boolean {
      return Boolean(state.filters.q.trim() || state.filters.status);
    }
  },
  actions: {
    async loadAccounts(filters?: AccountListFilters): Promise<void> {
      const resolvedFilters = filters ?? this.filters;
      const sequence = ++listSequence;
      listController?.abort();
      listController = new AbortController();
      this.filters = { ...resolvedFilters };
      this.collectionState = "loading";
      this.error = null;
      try {
        const result = await listAccounts(toListQuery(resolvedFilters), {
          signal: listController.signal
        });
        if (sequence !== listSequence) return;
        this.accounts = result.data.items;
        this.totalKnown = result.data.totalKnown;
        this.collectionState =
          result.data.items.length > 0
            ? "ready"
            : resolvedFilters.q.trim() || resolvedFilters.status
              ? "filtered-empty"
              : "empty";
        if (
          this.selectedAccountId &&
          !result.data.items.some((item) => item.id === this.selectedAccountId)
        ) {
          this.selectedAccountId = null;
        }
      } catch (error) {
        if (isRuntimeRequestAborted(error) || sequence !== listSequence) return;
        this.collectionState = "error";
        this.error = toAccountUiError(error, "账号列表加载失败，请稍后重试。");
      }
    },
    selectAccount(accountId: string | null): void {
      this.selectedAccountId = accountId;
    },

    async refreshAccount(accountId: string): Promise<AccountDto> {
      try {
        const result = await getAccount(accountId);
        this.replaceAccount(result.data);
        return result.data;
      } catch (error) {
        this.fail("账号详情刷新失败，请稍后重试。", "health", accountId, error);
        throw error;
      }
    },
    async createDraft(input: AccountCreateInput): Promise<AccountDto> {
      return this.runMutation("create", null, async () => {
        const result = await createAccount(input, {
          idempotencyKey: createOperationKey("account-create")
        });
        this.replaceAccount(result.data);
        this.selectedAccountId = result.data.id;
        this.feedback = {
          kind: "create",
          tone: "success",
          message: "账号草稿已创建，可继续完成真实连接与配置。",
          accountId: result.data.id,
          taskId: null,
          logId: null
        };
        notifyAccountDirectoryChanged(result.data.id, "created");
        return result.data;
      });
    },
    async archive(account: AccountDto, reason: string): Promise<string> {
      return this.runMutation("archive", account.id, async () => {
        const result = await archiveAccount(
          account.id,
          { reason: reason.trim() || null },
          {
            expectedRevision: account.revision,
            idempotencyKey: createOperationKey("account-archive", account.id)
          }
        );
        this.pendingTaskIds[account.id] = result.data.taskId;
        this.feedback = {
          kind: "archive",
          tone: "info",
          message: "归档清理任务已提交；浏览器、登录与绑定安全收口后才会完成归档。",
          accountId: account.id,
          taskId: result.data.taskId,
          logId: null
        };
        notifyAccountDirectoryChanged(account.id, "archive-submitted");
        void this.watchArchiveTask(account.id, result.data.taskId);
        return result.data.taskId;
      });
    },
    async watchArchiveTask(accountId: string, taskId: string): Promise<void> {
      archiveTaskControllers.get(accountId)?.abort();
      const controller = new AbortController();
      archiveTaskControllers.set(accountId, controller);
      try {
        await waitForAccountTask(accountId, taskId, {
          signal: controller.signal,
          timeoutMs: 10 * 60 * 1000,
          failureMessage: "账号归档清理失败，请检查任务日志后重试。"
        });
        delete this.pendingTaskIds[accountId];
        await this.loadAccounts(this.filters);
        this.feedback = {
          kind: "archive",
          tone: "success",
          message: "账号已完成安全清理并归档。",
          accountId,
          taskId,
          logId: null
        };
        notifyAccountDirectoryChanged(accountId, "archived");
      } catch (error) {
        if (isRuntimeRequestAborted(error)) return;
        delete this.pendingTaskIds[accountId];
        await this.loadAccounts(this.filters);
        this.fail(
          "账号归档清理失败，请检查执行环境与任务日志后重试。",
          "archive",
          accountId,
          error
        );
      } finally {
        if (archiveTaskControllers.get(accountId) === controller) {
          archiveTaskControllers.delete(accountId);
        }
      }
    },
    async restore(account: AccountDto): Promise<string> {
      return this.runMutation("restore", account.id, async () => {
        const result = await restoreAccount(
          account.id,
          {},
          {
            expectedRevision: account.revision,
            idempotencyKey: createOperationKey("account-restore", account.id)
          }
        );
        this.pendingTaskIds[account.id] = result.data.taskId;
        this.feedback = {
          kind: "restore",
          tone: "info",
          message: "恢复复检任务已提交，完成后刷新列表查看最终状态。",
          accountId: account.id,
          taskId: result.data.taskId,
          logId: null
        };
        notifyAccountDirectoryChanged(account.id, "restore-submitted");
        return result.data.taskId;
      });
    },
    async copyConfig(
      target: AccountDto,
      input: AccountCopyInput
    ): Promise<void> {
      await this.runMutation("copy", target.id, async () => {
        const result = await copyAccountConfig(target.id, input, {
          expectedRevision: target.revision,
          idempotencyKey: createOperationKey("account-copy", target.id)
        });
        await this.refreshAccount(target.id);
        const skipped = result.data.skippedSections.length;
        this.feedback = {
          kind: "copy",
          tone: skipped > 0 ? "info" : "success",
          message:
            skipped > 0
              ? `配置复制完成，${skipped} 个缺失分区未复制。`
              : "所选配置已复制。",
          accountId: target.id,
          taskId: null,
          logId: null
        };
        notifyAccountDirectoryChanged(target.id, "updated");
      });
    },
    async startHealthCheck(
      account: AccountDto,
      input: HealthCheckInput = {}
    ): Promise<string> {
      return this.runMutation("health", account.id, async () => {
        const result = await startAccountHealthChecks(account.id, input, {
          idempotencyKey: createOperationKey("account-health", account.id)
        });
        this.pendingTaskIds[account.id] = result.data.taskId;
        this.feedback = {
          kind: "health",
          tone: "info",
          message: "健康检查任务已提交，可稍后刷新查看结果。",
          accountId: account.id,
          taskId: result.data.taskId,
          logId: null
        };
        notifyAccountDirectoryChanged(account.id, "updated");
        return result.data.taskId;
      });
    },
    async loadConnectionCandidates(
      accountId: string
    ): Promise<ConnectionCandidatesDto> {
      try {
        const result = await listAccountConnectionCandidates(accountId);
        return result.data;
      } catch (error) {
        this.fail("真实执行环境候选加载失败。", "connection", accountId, error);
        throw error;
      }
    },
    async loadConnection(accountId: string): Promise<ConnectionDto> {
      try {
        const result = await getAccountConnection(accountId);
        return result.data;
      } catch (error) {
        this.fail("账号连接状态加载失败。", "connection", accountId, error);
        throw error;
      }
    },
    async bindConnection(
      account: AccountDto,
      environmentId: string,
      eligibilityRevision: number
    ): Promise<ConnectionDto> {
      return this.runMutation("connection", account.id, async () => {
        const result = await bindAccountConnection(
          account.id,
          { environmentId, eligibilityRevision },
          {
            expectedRevision: account.revision,
            idempotencyKey: createOperationKey("account-bind", account.id)
          }
        );
        await this.refreshAccount(account.id);
        this.feedback = {
          kind: "connection",
          tone: "success",
          message: "已绑定真实工作区与浏览器实例。",
          accountId: account.id,
          taskId: null,
          logId: null
        };
        notifyAccountDirectoryChanged(account.id, "updated");
        return result.data;
      });
    },
    async completeWizard(
      account: AccountDto,
      completedSteps: AccountWizardStep[]
    ): Promise<AccountDto> {
      return this.runMutation("wizard", account.id, async () => {
        const result = await completeAccountWizard(
          account.id,
          { completedSteps },
          {
            expectedRevision: account.revision,
            idempotencyKey: createOperationKey("account-wizard", account.id)
          }
        );
        this.replaceAccount(result.data);
        this.feedback = {
          kind: "wizard",
          tone: "success",
          message: "账号向导已完成，最终状态以真实就绪检查为准。",
          accountId: account.id,
          taskId: null,
          logId: null
        };
        notifyAccountDirectoryChanged(account.id, "wizard-completed");
        return result.data;
      });
    },

    clearFeedback(): void {
      this.feedback = null;
    },

    replaceAccount(account: AccountDto): void {
      const index = this.accounts.findIndex((item) => item.id === account.id);
      if (index >= 0) this.accounts.splice(index, 1, account);
      else this.accounts.unshift(account);
      if (this.collectionState === "empty" || this.collectionState === "filtered-empty") {
        this.collectionState = "ready";
      }
    },

    async runMutation<T>(
      kind: AccountOperationFeedback["kind"],
      accountId: string | null,
      operation: () => Promise<T>
    ): Promise<T> {
      const busyKey = `${kind}:${accountId ?? "new"}`;
      this.busyKey = busyKey;
      this.error = null;
      try {
        return await operation();
      } catch (error) {
        this.fail("账号操作失败，请根据提示重试。", kind, accountId, error);
        throw error;
      } finally {
        if (this.busyKey === busyKey) this.busyKey = null;
      }
    },

    fail(
      fallback: string,
      kind: AccountOperationFeedback["kind"],
      accountId: string | null,
      error: unknown
    ): void {
      const normalized = toAccountUiError(error, fallback);
      this.error = normalized;
      this.feedback = {
        kind,
        tone: "error",
        message: normalized.message,
        accountId,
        taskId: null,
        logId: normalized.logId
      };
    }
  }
});

function toListQuery(filters: AccountListFilters): AccountListQuery {
  return {
    q: filters.q.trim() || undefined,
    status: filters.status || undefined,
    limit: 200
  };
}
