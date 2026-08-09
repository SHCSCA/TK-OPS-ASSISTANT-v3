import { shallowReactive } from "vue";

import {
  AccountContextDisposedError,
  AccountSwitchSupersededError,
  normalizeAccountContextError
} from "./errors";
import {
  accountScopeKey,
  captureAccountGeneration,
  isAccountGenerationCurrent
} from "./generation";
import {
  isValidRoute,
  normalizeAccountId,
  normalizeRoute,
  normalizeRouteMap
} from "./account-context-normalizers";
import { PreparedAccountResourceStack } from "./switch-resources";
import { consoleAccountContextLogger } from "./unsaved-guard-registry";
import type {
  AccountContextGeneration,
  AccountContextState,
  AccountContextStorePorts,
  AccountRefreshResult,
  AccountScopedRequest,
  AccountSwitchOptions,
  AccountSwitchResult,
  AccountUnsavedGuardReason,
  AccountWorkspaceContextLike,
  UnsavedGuardRunResult
} from "./types";

export type ActiveSwitchIntent = {
  id: string;
  sequence: number;
  targetAccountId: string;
  controller: AbortController;
  resources: PreparedAccountResourceStack;
  committed: boolean;
  predecessorSettlement: Promise<void>;
  executionFinished: Promise<void>;
  resolveExecutionFinished: () => void;
  executionSettled: boolean;
};

export type ActiveOperation =
  | {
      kind: "switch";
      accountId: string;
      promise: Promise<AccountSwitchResult>;
    }
  | {
      kind: "refresh";
      accountId: string;
      promise: Promise<AccountRefreshResult>;
    };

export abstract class AccountContextStoreBase<
  TContext extends AccountWorkspaceContextLike
> {
  readonly state: AccountContextState<TContext>;

  protected readonly logger;
  protected readonly defaultAccountRoute;
  protected activeIntent: ActiveSwitchIntent | null = null;
  protected activeOperation: ActiveOperation | null = null;
  protected intentSequence = 0;
  protected readonly pendingGuardTokens = new Set<symbol>();
  private routeMemoryController: AbortController | null = null;
  protected disposed = false;

  constructor(
    protected readonly ports: AccountContextStorePorts<TContext>
  ) {
    this.logger = ports.logger ?? consoleAccountContextLogger;
    this.defaultAccountRoute = ports.defaultAccountRoute ?? "/workspace";
    this.state = shallowReactive<AccountContextState<TContext>>({
      currentAccountId: null,
      currentAccount: null,
      switchStatus: "idle",
      switchIntentId: null,
      targetAccountId: null,
      accountRevision: 0,
      subscriptionRevision: 0,
      lastRouteByAccount: {},
      pendingUnsavedGuard: false,
      error: null,
      retry: null
    });
  }

  abstract switchAccount(
    accountId: string,
    options?: AccountSwitchOptions
  ): Promise<AccountSwitchResult>;

  abstract refreshCurrentAccount(): Promise<AccountRefreshResult>;

  abstract retryLastFailure(): Promise<
    AccountSwitchResult | AccountRefreshResult | null
  >;

  async guardUnsaved(
    reason: AccountUnsavedGuardReason,
    targetAccountId: string | null = null,
    signal?: AbortSignal
  ): Promise<UnsavedGuardRunResult> {
    this.assertAvailable();
    const controller = signal ? null : new AbortController();
    const guardSignal = signal ?? controller!.signal;
    const guardToken = this.beginPendingGuard();
    try {
      return await this.ports.unsavedGuards.run({
        reason,
        sourceAccountId: this.state.currentAccountId,
        targetAccountId,
        signal: guardSignal
      });
    } finally {
      this.endPendingGuard(guardToken);
    }
  }

  captureGeneration(): AccountContextGeneration | null {
    return captureAccountGeneration(this.state);
  }

  isGenerationCurrent(
    generation: AccountContextGeneration,
    responseAccountId: string = generation.accountId
  ): boolean {
    return isAccountGenerationCurrent(
      this.state,
      generation,
      responseAccountId
    );
  }

  commitResponseIfCurrent<T>(
    generation: AccountContextGeneration,
    responseAccountId: string,
    response: T,
    commit: (value: T) => void
  ): boolean {
    if (!this.isGenerationCurrent(generation, responseAccountId)) {
      return false;
    }
    commit(response);
    return true;
  }

  async hydrateLastRoutes(): Promise<Record<string, string>> {
    this.assertAvailable();
    this.routeMemoryController?.abort();
    const controller = new AbortController();
    this.routeMemoryController = controller;
    try {
      const loaded = await this.ports.routeMemory.loadLastRoutes(
        controller.signal
      );
      if (
        controller.signal.aborted
        || this.routeMemoryController !== controller
      ) {
        return this.state.lastRouteByAccount;
      }
      const normalized = normalizeRouteMap(loaded);
      this.patchState({ lastRouteByAccount: normalized });
      return normalized;
    } catch (error) {
      if (!controller.signal.aborted) {
        this.logger.error(
          "[account-context] 从配置总线读取最近页面失败",
          error
        );
      }
      throw error;
    } finally {
      if (this.routeMemoryController === controller) {
        this.routeMemoryController = null;
      }
    }
  }

  async rememberRoute(accountId: string, route: string): Promise<void> {
    this.assertAvailable();
    const normalizedAccountId = normalizeAccountId(accountId);
    const normalizedRoute = normalizeRoute(route);
    try {
      await this.ports.routeMemory.saveLastRoute(
        normalizedAccountId,
        normalizedRoute
      );
      this.patchState({
        lastRouteByAccount: {
          ...this.state.lastRouteByAccount,
          [normalizedAccountId]: normalizedRoute
        }
      });
    } catch (error) {
      this.logger.error(
        "[account-context] 通过配置总线保存最近页面失败",
        {
          accountId: normalizedAccountId,
          route: normalizedRoute,
          error
        }
      );
      throw error;
    }
  }

  async forgetRoute(accountId: string): Promise<void> {
    this.assertAvailable();
    const normalizedAccountId = normalizeAccountId(accountId);
    try {
      await this.ports.routeMemory.removeLastRoute?.(normalizedAccountId);
      const nextRoutes = { ...this.state.lastRouteByAccount };
      delete nextRoutes[normalizedAccountId];
      this.patchState({ lastRouteByAccount: nextRoutes });
    } catch (error) {
      this.logger.error(
        "[account-context] 通过配置总线移除最近页面失败",
        {
          accountId: normalizedAccountId,
          error
        }
      );
      throw error;
    }
  }

  async clearCurrentAccount(): Promise<void> {
    this.assertAvailable();
    const cleanupErrors: unknown[] = [];
    const previous = this.activeIntent;
    if (previous) {
      previous.controller.abort(new AccountSwitchSupersededError());
      try {
        await Promise.all([
          this.settleSupersededIntent(previous),
          previous.executionFinished
        ]);
      } catch (error) {
        cleanupErrors.push(error);
        this.logger.error(
          "[account-context] 清空账号前收口切换事务失败",
          error
        );
      }
    }
    const currentAccountId = this.state.currentAccountId;
    if (currentAccountId) {
      try {
        this.ports.runtime.cancelAccountScope(currentAccountId);
      } catch (error) {
        cleanupErrors.push(error);
        this.logger.error(
          "[account-context] 清空账号时取消可见请求失败",
          error
        );
      }
      const controller = new AbortController();
      const nextAccountRevision = this.state.accountRevision + 1;
      const nextSubscriptionRevision = this.state.subscriptionRevision + 1;
      const results = await Promise.allSettled([
        this.ports.subscriptions.clearAccountTopics({
          accountId: currentAccountId,
          accountRevision: nextAccountRevision,
          subscriptionRevision: nextSubscriptionRevision,
          signal: controller.signal
        }),
        this.ports.surface.clearAccountSurface({
          accountId: currentAccountId,
          accountRevision: nextAccountRevision,
          subscriptionRevision: nextSubscriptionRevision,
          signal: controller.signal
        })
      ]);
      for (const result of results) {
        if (result.status === "rejected") {
          cleanupErrors.push(result.reason);
        }
      }
    }
    this.activeIntent = null;
    this.activeOperation = null;
    const cleanupError = cleanupErrors.length > 0
      ? normalizeAccountContextError(
          new AggregateError(cleanupErrors, "账号上下文清理不完整。"),
          "committing",
          "账号已清空，但可见订阅或页面状态清理不完整。"
        )
      : null;
    if (cleanupError) {
      this.logger.error(
        "[account-context] 账号上下文已清空但资源清理不完整",
        {
          accountId: currentAccountId,
          errors: cleanupErrors
        }
      );
    }
    this.patchState({
      currentAccountId: null,
      currentAccount: null,
      switchStatus: cleanupError ? "failed" : "idle",
      switchIntentId: null,
      targetAccountId: null,
      accountRevision: this.state.accountRevision + 1,
      subscriptionRevision: currentAccountId
        ? this.state.subscriptionRevision + 1
        : this.state.subscriptionRevision,
      pendingUnsavedGuard: this.pendingGuardTokens.size > 0,
      error: cleanupError,
      retry: null
    });
  }

  async dispose(): Promise<void> {
    if (this.disposed) return;
    this.disposed = true;
    this.routeMemoryController?.abort();
    const active = this.activeIntent;
    if (active) {
      active.controller.abort(new AccountContextDisposedError());
      try {
        await Promise.all([
          this.settleSupersededIntent(active),
          active.executionFinished
        ]);
      } catch (error) {
        this.logger.error("[account-context] 释放账号上下文资源失败", error);
      }
    }
    this.activeIntent = null;
    this.activeOperation = null;
  }

  protected beginIntent(targetAccountId: string): ActiveSwitchIntent {
    const previous = this.activeIntent;
    const controller = new AbortController();
    let resolveExecutionFinished: () => void = () => {};
    const executionFinished = new Promise<void>((resolve) => {
      resolveExecutionFinished = resolve;
    });
    const intent: ActiveSwitchIntent = {
      id: this.createIntentId(),
      sequence: ++this.intentSequence,
      targetAccountId,
      controller,
      resources: new PreparedAccountResourceStack(this.logger),
      committed: false,
      predecessorSettlement: Promise.resolve(),
      executionFinished,
      resolveExecutionFinished,
      executionSettled: false
    };
    this.activeIntent = intent;

    if (previous) {
      previous.controller.abort(new AccountSwitchSupersededError());
      intent.predecessorSettlement = Promise.all([
        this.settleSupersededIntent(previous),
        previous.executionFinished
      ]).then(() => undefined);
    }
    return intent;
  }

  protected async settleSupersededIntent(
    intent: ActiveSwitchIntent
  ): Promise<void> {
    if (intent.committed) {
      await intent.resources.finalize();
      return;
    }
    await intent.resources.rollback(new AccountSwitchSupersededError());
  }

  protected completeIntent(intent: ActiveSwitchIntent): void {
    if (this.activeIntent === intent) this.activeIntent = null;
    this.finishIntentExecution(intent);
  }

  protected finishIntentExecution(intent: ActiveSwitchIntent): void {
    if (intent.executionSettled) return;
    intent.executionSettled = true;
    intent.resolveExecutionFinished();
  }

  protected isCurrentIntent(intent: ActiveSwitchIntent): boolean {
    return (
      !this.disposed
      && this.activeIntent === intent
      && !intent.controller.signal.aborted
    );
  }

  protected assertCurrentIntent(intent: ActiveSwitchIntent): void {
    if (this.disposed) throw new AccountContextDisposedError();
    if (!this.isCurrentIntent(intent)) {
      throw new AccountSwitchSupersededError();
    }
  }

  protected toScopedRequest(
    intent: ActiveSwitchIntent
  ): AccountScopedRequest {
    return {
      accountId: intent.targetAccountId,
      scopeKey: accountScopeKey(intent.targetAccountId),
      switchIntentId: intent.id,
      switchRevision: intent.sequence,
      signal: intent.controller.signal
    };
  }

  protected resolvePreferredRoute(context: TContext): string {
    const remembered = this.state.lastRouteByAccount[context.account.id];
    for (const candidate of [
      remembered,
      context.navigation.lastRoute,
      this.defaultAccountRoute
    ]) {
      if (candidate && isValidRoute(candidate)) return candidate;
    }
    return "/workspace";
  }

  protected patchState(
    patch: Partial<AccountContextState<TContext>>
  ): void {
    Object.assign(this.state, patch);
  }

  protected beginPendingGuard(): symbol {
    const token = Symbol("account-unsaved-guard");
    this.pendingGuardTokens.add(token);
    this.patchState({ pendingUnsavedGuard: true });
    return token;
  }

  protected endPendingGuard(token: symbol): void {
    this.pendingGuardTokens.delete(token);
    this.patchState({
      pendingUnsavedGuard: this.pendingGuardTokens.size > 0
    });
  }

  protected assertAvailable(): void {
    if (this.disposed) throw new AccountContextDisposedError();
  }

  private createIntentId(): string {
    if (this.ports.createIntentId) {
      try {
        const candidate = this.ports.createIntentId().trim();
        if (candidate) return candidate;
      } catch (error) {
        this.logger.error(
          "[account-context] 生成切换意图 ID 失败，使用本地后备值",
          error
        );
      }
    }
    const suffix = globalThis.crypto?.randomUUID?.()
      ?? `${Date.now().toString(36)}-${this.intentSequence.toString(36)}`;
    return `account-switch-${suffix}`;
  }
}
