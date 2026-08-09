import {
  AccountSwitchSupersededError,
  isAccountSwitchSuperseded,
  normalizeAccountContextError
} from "./errors";
import { assertWorkspaceContextScope } from "./generation";
import {
  isValidRoute,
  normalizeAccountId
} from "./account-context-normalizers";
import {
  AccountContextStoreBase,
  type ActiveOperation,
  type ActiveSwitchIntent
} from "./account-context-store-base";
import type {
  AccountContextStorePorts,
  AccountRefreshResult,
  AccountSwitchFailureStage,
  AccountSwitchOptions,
  AccountSwitchResult,
  AccountWorkspaceContextLike
} from "./types";

export class AccountContextStore<
  TContext extends AccountWorkspaceContextLike = AccountWorkspaceContextLike
> extends AccountContextStoreBase<TContext> {
  switchAccount(
    accountId: string,
    options: AccountSwitchOptions = {}
  ): Promise<AccountSwitchResult> {
    this.assertAvailable();
    let targetAccountId: string;
    try {
      targetAccountId = normalizeAccountId(accountId);
    } catch (error) {
      const normalized = normalizeAccountContextError(
        error,
        "preparing",
        "账号 ID 格式无效，无法切换工作区。"
      );
      this.logger.error("[account-context] 拒绝无效账号切换意图", {
        accountId,
        error
      });
      this.patchState({
        switchStatus: "failed",
        switchIntentId: null,
        targetAccountId: accountId.trim() || null,
        error: normalized,
        retry: null
      });
      return Promise.resolve({
        status: "failed",
        accountId,
        error: normalized
      });
    }
    if (
      !this.activeOperation
      && this.state.currentAccountId === targetAccountId
    ) {
      return Promise.resolve({
        status: "unchanged",
        accountId: targetAccountId
      });
    }
    if (
      this.activeOperation?.kind === "switch"
      && this.activeOperation.accountId === targetAccountId
    ) {
      return this.activeOperation.promise;
    }

    const promise = this.executeSwitch(targetAccountId, options);
    const operation: ActiveOperation = {
      kind: "switch",
      accountId: targetAccountId,
      promise
    };
    this.activeOperation = operation;
    void promise.then(
      () => {
        if (this.activeOperation === operation) {
          this.activeOperation = null;
        }
      },
      (error) => {
        if (this.activeOperation === operation) {
          this.activeOperation = null;
        }
        this.logger.error(
          "[account-context] 账号切换发生未捕获异常",
          error
        );
      }
    );
    return promise;
  }

  refreshCurrentAccount(): Promise<AccountRefreshResult> {
    this.assertAvailable();
    const accountId = this.state.currentAccountId;
    if (!accountId) {
      return Promise.resolve({ status: "unavailable" });
    }
    if (
      this.activeOperation?.kind === "refresh"
      && this.activeOperation.accountId === accountId
    ) {
      return this.activeOperation.promise;
    }

    const promise = this.executeRefresh(accountId);
    const operation: ActiveOperation = {
      kind: "refresh",
      accountId,
      promise
    };
    this.activeOperation = operation;
    void promise.then(
      () => {
        if (this.activeOperation === operation) {
          this.activeOperation = null;
        }
      },
      (error) => {
        if (this.activeOperation === operation) {
          this.activeOperation = null;
        }
        this.logger.error(
          "[account-context] 账号刷新发生未捕获异常",
          error
        );
      }
    );
    return promise;
  }

  retryLastFailure(): Promise<
    AccountSwitchResult | AccountRefreshResult | null
  > {
    const retry = this.state.retry;
    if (!retry) return Promise.resolve(null);
    return retry.kind === "switch"
      ? this.switchAccount(retry.accountId)
      : this.refreshCurrentAccount();
  }

  private async executeSwitch(
    targetAccountId: string,
    options: AccountSwitchOptions
  ): Promise<AccountSwitchResult> {
    const intent = this.beginIntent(targetAccountId);
    let stage: AccountSwitchFailureStage = "guarding";
    const guardToken = this.beginPendingGuard();
    this.patchState({
      switchStatus: "guarding",
      switchIntentId: intent.id,
      targetAccountId,
      error: null,
      retry: null
    });

    try {
      await intent.predecessorSettlement;
      this.assertCurrentIntent(intent);
      let guardResult;
      try {
        guardResult = await this.ports.unsavedGuards.run({
          reason: "account-switch",
          sourceAccountId: this.state.currentAccountId,
          targetAccountId,
          signal: intent.controller.signal
        });
      } finally {
        this.endPendingGuard(guardToken);
      }
      this.assertCurrentIntent(intent);
      if (guardResult.status === "cancelled") {
        await intent.resources.finalize();
        this.completeIntent(intent);
        this.patchState({
          switchStatus: "idle",
          switchIntentId: null,
          targetAccountId: null,
          error: null,
          retry: null
        });
        return { status: "cancelled", accountId: targetAccountId };
      }

      stage = "preparing";
      this.patchState({ switchStatus: "preparing" });
      const previousAccountId = this.state.currentAccountId;
      if (previousAccountId) {
        this.ports.runtime.cancelAccountScope(previousAccountId);
      }

      const request = this.toScopedRequest(intent);
      const context = assertWorkspaceContextScope(
        await this.ports.runtime.fetchWorkspaceContext(request),
        targetAccountId
      );
      this.assertCurrentIntent(intent);

      const nextAccountRevision = this.state.accountRevision + 1;
      const nextSubscriptionRevision =
        this.state.subscriptionRevision + 1;
      const topicResource =
        await this.ports.subscriptions.prepareAccountTopics({
          ...request,
          previousAccountId,
          context,
          subscriptionRevision: nextSubscriptionRevision,
          cursors: options.topicCursors ?? {}
        });
      intent.resources.add("topics", topicResource);
      this.assertCurrentIntent(intent);

      const surfaceResource =
        await this.ports.surface.prepareAccountSurface({
          ...request,
          previousContext: this.state.currentAccount,
          context,
          preferredRoute:
            options.preferredRoute
            && isValidRoute(options.preferredRoute)
              ? options.preferredRoute
              : this.resolvePreferredRoute(context),
          accountRevision: nextAccountRevision
        });
      intent.resources.add("surface", surfaceResource);
      this.assertCurrentIntent(intent);

      stage = "committing";
      this.patchState({ switchStatus: "committing" });
      await intent.resources.commitAll(
        () => this.assertCurrentIntent(intent)
      );
      this.assertCurrentIntent(intent);
      this.patchState({
        currentAccountId: targetAccountId,
        currentAccount: context,
        accountRevision: nextAccountRevision,
        subscriptionRevision: nextSubscriptionRevision,
        switchStatus: "refreshing"
      });
      intent.committed = true;

      stage = "refreshing";
      await this.ports.runtime.activateWorkspace?.(request, context);
      this.assertCurrentIntent(intent);
      const refreshed = assertWorkspaceContextScope(
        await this.ports.runtime.fetchWorkspaceContext(request),
        targetAccountId
      );
      this.assertCurrentIntent(intent);
      await this.ports.surface.refreshAccountSurface({
        ...request,
        context: refreshed,
        accountRevision: nextAccountRevision
      });
      this.assertCurrentIntent(intent);
      this.patchState({ currentAccount: refreshed });
      await intent.resources.finalize();
      this.completeIntent(intent);
      this.patchState({
        switchStatus: "idle",
        switchIntentId: null,
        targetAccountId: null,
        pendingUnsavedGuard: this.pendingGuardTokens.size > 0,
        error: null,
        retry: null
      });
      return {
        status: "switched",
        accountId: targetAccountId,
        switchIntentId: intent.id,
        accountRevision: nextAccountRevision
      };
    } catch (error) {
      this.endPendingGuard(guardToken);
      if (
        isAccountSwitchSuperseded(error)
        || !this.isCurrentIntent(intent)
      ) {
        try {
          await this.settleSupersededIntent(intent);
        } catch (settlementError) {
          this.logger.error(
            "[account-context] 过期账号切换资源收口失败",
            {
              targetAccountId,
              switchIntentId: intent.id,
              settlementError
            }
          );
        } finally {
          this.finishIntentExecution(intent);
        }
        return { status: "superseded", accountId: targetAccountId };
      }
      return this.failSwitch(intent, targetAccountId, stage, error);
    }
  }

  private async executeRefresh(
    accountId: string
  ): Promise<AccountRefreshResult> {
    const generation = this.captureGeneration();
    if (!generation || generation.accountId !== accountId) {
      return { status: "unavailable" };
    }
    const intent = this.beginIntent(accountId);
    this.patchState({
      switchStatus: "refreshing",
      switchIntentId: intent.id,
      targetAccountId: accountId,
      pendingUnsavedGuard: this.pendingGuardTokens.size > 0,
      error: null,
      retry: null
    });

    try {
      await intent.predecessorSettlement;
      this.assertCurrentIntent(intent);
      this.ports.runtime.cancelAccountScope(accountId);
      const request = this.toScopedRequest(intent);
      const context = assertWorkspaceContextScope(
        await this.ports.runtime.fetchWorkspaceContext(request),
        accountId
      );
      this.assertCurrentIntent(intent);
      if (!this.isGenerationCurrent(generation, accountId)) {
        throw new AccountSwitchSupersededError();
      }
      await this.ports.surface.refreshAccountSurface({
        ...request,
        context,
        accountRevision: generation.accountRevision
      });
      this.assertCurrentIntent(intent);
      if (!this.isGenerationCurrent(generation, accountId)) {
        throw new AccountSwitchSupersededError();
      }
      this.patchState({
        currentAccount: context,
        switchStatus: "idle",
        switchIntentId: null,
        targetAccountId: null,
        error: null,
        retry: null
      });
      this.completeIntent(intent);
      return {
        status: "refreshed",
        accountId,
        switchIntentId: intent.id,
        accountRevision: generation.accountRevision
      };
    } catch (error) {
      if (
        isAccountSwitchSuperseded(error)
        || !this.isCurrentIntent(intent)
      ) {
        try {
          await this.settleSupersededIntent(intent);
        } finally {
          this.finishIntentExecution(intent);
        }
        return { status: "superseded", accountId };
      }
      const normalized = normalizeAccountContextError(
        error,
        "refreshing",
        "刷新账号工作区失败，请稍后重试。"
      );
      this.logger.error("[account-context] 刷新账号工作区失败", {
        accountId,
        switchIntentId: intent.id,
        error
      });
      this.completeIntent(intent);
      this.patchState({
        switchStatus: "failed",
        pendingUnsavedGuard: this.pendingGuardTokens.size > 0,
        error: normalized,
        retry: normalized.retryable
          ? { kind: "refresh", accountId }
          : null
      });
      return {
        status: "failed",
        accountId,
        error: normalized
      };
    }
  }

  private async failSwitch(
    intent: ActiveSwitchIntent,
    targetAccountId: string,
    stage: AccountSwitchFailureStage,
    error: unknown
  ): Promise<AccountSwitchResult> {
    const normalized = normalizeAccountContextError(
      error,
      stage,
      "切换账号工作区失败，请检查 Runtime 状态后重试。"
    );
    this.logger.error("[account-context] 账号切换失败", {
      targetAccountId,
      switchIntentId: intent.id,
      stage,
      error
    });

    if (intent.committed) {
      await intent.resources.finalize();
    } else {
      try {
        await intent.resources.rollback(error);
      } catch (rollbackError) {
        this.logger.error(
          "[account-context] 账号切换失败后的回滚不完整",
          {
            targetAccountId,
            switchIntentId: intent.id,
            rollbackError
          }
        );
      }
    }
    this.completeIntent(intent);
    this.patchState({
      switchStatus: "failed",
      pendingUnsavedGuard: this.pendingGuardTokens.size > 0,
      error: normalized,
      retry: normalized.retryable
        ? {
            kind: intent.committed ? "refresh" : "switch",
            accountId: targetAccountId
          }
        : null
    });
    return {
      status: "failed",
      accountId: targetAccountId,
      error: normalized
    };
  }

}

export function createAccountContextStore<
  TContext extends AccountWorkspaceContextLike = AccountWorkspaceContextLike
>(
  ports: AccountContextStorePorts<TContext>
): AccountContextStore<TContext> {
  return new AccountContextStore(ports);
}
