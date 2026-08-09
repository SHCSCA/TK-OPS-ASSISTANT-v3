import { shallowReactive } from "vue";
import type { Router } from "vue-router";

import type { AccountWorkspaceContextDto } from "@/types/runtime/accounts";
import type { RuntimeEventDto } from "@/types/runtime/events";

import { AccountContextStore } from "./account-context-store";
import { AccountUiConfigGateway } from "./config-bus-route-memory";
import { normalizeAccountContextError } from "./errors";
import { createAccountWorkspaceRuntimePort } from "./runtime-port-adapter";
import type {
  AccountContextClearRequest,
  AccountContextError,
  AccountContextSurfacePort,
  AccountSurfacePrepareRequest,
  AccountSurfaceRefreshRequest,
  AccountTopicSubscriptionPort,
  ReversibleAccountSwitchResource
} from "./types";
import { AccountUnsavedDecisionController } from "./unsaved-decision-controller";
import {
  consoleAccountContextLogger,
  UnsavedGuardRegistry
} from "./unsaved-guard-registry";
import { RuntimeEventSocketManager } from "@/app/runtime-client/events";

const ACCOUNT_ROUTE_PREFIXES = [
  "/workspace",
  "/strategy-knowledge",
  "/scripts",
  "/storyboards",
  "/video-deconstruction",
  "/production/batches",
  "/content-library",
  "/media-tools",
  "/publishing",
  "/review"
];

export class AccountContextApplication {
  readonly uiConfig = new AccountUiConfigGateway();
  readonly eventSocket = new RuntimeEventSocketManager();
  readonly unsavedDecision = new AccountUnsavedDecisionController();
  readonly unsavedGuards = new UnsavedGuardRegistry(
    this.unsavedDecision,
    consoleAccountContextLogger
  );
  readonly navigationState = shallowReactive<{
    error: AccountContextError | null;
  }>({ error: null });
  readonly context: AccountContextStore<AccountWorkspaceContextDto>;

  private router: Router | null = null;
  private initializePromise: Promise<void> | null = null;
  private initialized = false;
  private routeAccountOverride: string | null | undefined;
  private refreshTimer: number | null = null;
  private removeBeforeRouteListener: (() => void) | null = null;
  private removeRouteListener: (() => void) | null = null;
  private removeEventListener: (() => void) | null = null;
  private removeSyncListener: (() => void) | null = null;

  constructor() {
    const subscriptions: AccountTopicSubscriptionPort<AccountWorkspaceContextDto> = {
      prepareAccountTopics: (request) =>
        this.eventSocket.prepareAccount(
          request.accountId,
          request.subscriptionRevision,
          request.cursors,
          request.signal
        ),
      clearAccountTopics: async () => this.eventSocket.clear()
    };
    const surface: AccountContextSurfacePort<AccountWorkspaceContextDto> = {
      prepareAccountSurface: (request) => this.prepareSurface(request),
      refreshAccountSurface: (request) => this.refreshSurface(request),
      clearAccountSurface: (request) => this.clearSurface(request)
    };
    this.context = new AccountContextStore({
      runtime: createAccountWorkspaceRuntimePort(),
      subscriptions,
      surface,
      routeMemory: this.uiConfig.routeMemory,
      unsavedGuards: this.unsavedGuards,
      logger: consoleAccountContextLogger,
      defaultAccountRoute: "/workspace"
    });
  }

  configureRouter(router: Router): void {
    if (this.router === router) return;
    this.removeBeforeRouteListener?.();
    this.removeRouteListener?.();
    this.router = router;
    this.removeBeforeRouteListener = router.beforeEach(async (to, from) => {
      if (
        this.routeAccountOverride !== undefined
        || to.fullPath === from.fullPath
        || !from.name
      ) {
        return true;
      }
      this.navigationState.error = null;
      try {
        const result = await this.context.guardUnsaved(
          "route-leave",
          this.context.state.currentAccountId
        );
        return result.status !== "cancelled";
      } catch (error) {
        const normalized = normalizeAccountContextError(
          error,
          "guarding",
          "处理未保存内容失败，已留在当前页面。"
        );
        this.navigationState.error = normalized;
        consoleAccountContextLogger.error(
          "[account-context] 路由离开守卫失败",
          error
        );
        return false;
      }
    });
    this.removeRouteListener = router.afterEach((route) => {
      const accountId =
        this.routeAccountOverride !== undefined
          ? this.routeAccountOverride
          : this.context.state.currentAccountId;
      if (!accountId || !isAccountRoute(route.path)) return;
      void this.context.rememberRoute(accountId, route.path).catch((error) => {
        consoleAccountContextLogger.error(
          "[account-context] 记录账号最近页面失败",
          error
        );
      });
    });
  }

  initialize(): Promise<void> {
    if (this.initialized) return Promise.resolve();
    if (this.initializePromise) return this.initializePromise;
    const operation = this.runInitialize();
    this.initializePromise = operation;
    void operation.finally(() => {
      if (this.initializePromise === operation) {
        this.initializePromise = null;
      }
    });
    return operation;
  }

  async dispose(): Promise<void> {
    if (this.refreshTimer !== null) {
      window.clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
    this.removeBeforeRouteListener?.();
    this.removeRouteListener?.();
    this.removeEventListener?.();
    this.removeSyncListener?.();
    this.removeBeforeRouteListener = null;
    this.removeRouteListener = null;
    this.removeEventListener = null;
    this.removeSyncListener = null;
    await this.context.dispose();
    await this.eventSocket.dispose();
  }

  private async runInitialize(): Promise<void> {
    await this.uiConfig.load();
    await this.context.hydrateLastRoutes();
    this.installEventListeners();
    const accountId = this.uiConfig.state.lastAccountId;
    if (!accountId) {
      this.initialized = true;
      return;
    }
    const currentRoute = this.requireRouter().currentRoute.value;
    const preferredRoute = isAccountRoute(currentRoute.path)
      ? undefined
      : currentRoute.fullPath;
    const result = await this.context.switchAccount(accountId, {
      preferredRoute
    });
    if (
      result.status === "failed"
      && (
        result.error.code === "ACCOUNT_NOT_FOUND"
        || result.error.code === "ACCOUNT_ARCHIVED"
      )
    ) {
      await this.context.clearCurrentAccount();
      await this.uiConfig.setActiveAccount(null);
      this.initialized = true;
      return;
    }
    if (result.status !== "failed") {
      this.initialized = true;
    }
  }

  private installEventListeners(): void {
    if (!this.removeEventListener) {
      this.removeEventListener = this.eventSocket.onEvent((event) =>
        this.handleRuntimeEvent(event)
      );
    }
    if (!this.removeSyncListener) {
      this.removeSyncListener = this.eventSocket.onSyncRequired(() =>
        this.scheduleRefresh()
      );
    }
  }

  private handleRuntimeEvent(event: RuntimeEventDto): void {
    if (
      event.accountId !== this.context.state.currentAccountId
      || event.revision < 1
    ) {
      return;
    }
    this.scheduleRefresh();
  }

  private scheduleRefresh(): void {
    if (this.refreshTimer !== null) {
      window.clearTimeout(this.refreshTimer);
    }
    this.refreshTimer = window.setTimeout(() => {
      this.refreshTimer = null;
      if (
        this.context.state.switchStatus !== "idle"
        && this.context.state.switchStatus !== "failed"
      ) {
        this.scheduleRefresh();
        return;
      }
      void this.context.refreshCurrentAccount();
    }, 180);
  }

  private async prepareSurface(
    request: AccountSurfacePrepareRequest<AccountWorkspaceContextDto>
  ): Promise<ReversibleAccountSwitchResource> {
    const router = this.requireRouter();
    const previousRoute = router.currentRoute.value.fullPath;
    const previousAccountId = this.uiConfig.state.lastAccountId;
    let committed = false;

    return {
      commit: async () => {
        const rememberedRoute = isAccountRoute(request.preferredRoute)
          ? request.preferredRoute
          : undefined;
        await this.uiConfig.setActiveAccount(
          request.accountId,
          rememberedRoute,
          request.signal
        );
        committed = true;
        this.routeAccountOverride = request.accountId;
        try {
          await router.replace(request.preferredRoute);
        } finally {
          this.routeAccountOverride = undefined;
        }
      },
      rollback: async () => {
        if (!committed) return;
        const failures: unknown[] = [];
        try {
          await this.uiConfig.setActiveAccount(
            previousAccountId,
            previousAccountId && isAccountRoute(previousRoute)
              ? previousRoute
              : undefined
          );
        } catch (error) {
          failures.push(error);
        }
        this.routeAccountOverride = previousAccountId;
        try {
          await router.replace(previousRoute);
        } catch (error) {
          failures.push(error);
        } finally {
          this.routeAccountOverride = undefined;
        }
        if (failures.length > 0) {
          throw new AggregateError(
            failures,
            "账号工作区界面回滚不完整。"
          );
        }
      }
    };
  }

  private async refreshSurface(
    _request: AccountSurfaceRefreshRequest<AccountWorkspaceContextDto>
  ): Promise<void> {
    // 账号实体、任务和就绪状态已经由刷新后的工作区快照原子替换。
  }

  private async clearSurface(
    request: AccountContextClearRequest
  ): Promise<void> {
    await this.uiConfig.setActiveAccount(null, undefined, request.signal);
  }

  private requireRouter(): Router {
    if (!this.router) {
      throw new Error("账号上下文尚未装配路由器。");
    }
    return this.router;
  }
}

function isAccountRoute(path: string): boolean {
  return ACCOUNT_ROUTE_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`)
  );
}

export const accountContextApplication = new AccountContextApplication();
