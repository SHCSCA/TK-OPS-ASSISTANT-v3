export type AccountSwitchStatus =
  | "idle"
  | "guarding"
  | "preparing"
  | "committing"
  | "refreshing"
  | "failed";

export type AccountSwitchFailureStage =
  | "guarding"
  | "preparing"
  | "committing"
  | "refreshing";

export type AccountUnsavedGuardReason =
  | "account-switch"
  | "route-leave"
  | "editor-close"
  | "account-archive";

export type UnsavedGuardDecision = "save" | "discard" | "cancel";

export type AccountContextAccountLike = {
  id: string;
  status: string;
  revision: number;
};

export type AccountWorkspaceContextLike = {
  account: AccountContextAccountLike;
  readiness: unknown;
  navigation: {
    lastRoute: string;
    availableRoutes: string[];
  };
  taskSummary: {
    running: number;
    failed: number;
  };
  workspaceRevision: number;
};

export type AccountContextError = {
  code: string;
  message: string;
  logId: string | null;
  requestId: string | null;
  status: number | null;
  retryable: boolean;
  stage: AccountSwitchFailureStage;
  details?: unknown;
};

export type AccountSwitchRetry = {
  kind: "switch" | "refresh";
  accountId: string;
};

export type AccountContextState<
  TContext extends AccountWorkspaceContextLike = AccountWorkspaceContextLike
> = {
  currentAccountId: string | null;
  currentAccount: TContext | null;
  switchStatus: AccountSwitchStatus;
  switchIntentId: string | null;
  targetAccountId: string | null;
  accountRevision: number;
  subscriptionRevision: number;
  lastRouteByAccount: Record<string, string>;
  pendingUnsavedGuard: boolean;
  error: AccountContextError | null;
  retry: AccountSwitchRetry | null;
};

export type UnsavedGuard = {
  id: string;
  label: string;
  isDirty: () => boolean;
  save: () => Promise<void>;
  discard: () => Promise<void> | void;
};

export type UnsavedGuardPrompt = {
  reason: AccountUnsavedGuardReason;
  sourceAccountId: string | null;
  targetAccountId: string | null;
  guards: ReadonlyArray<Pick<UnsavedGuard, "id" | "label">>;
  signal: AbortSignal;
};

export type UnsavedGuardDecisionPort = {
  decide(prompt: UnsavedGuardPrompt): Promise<UnsavedGuardDecision>;
};

export type UnsavedGuardRunResult =
  | { status: "clean" }
  | { status: "saved"; guardIds: string[] }
  | { status: "discarded"; guardIds: string[] }
  | { status: "cancelled"; guardIds: string[] };

export type AccountScopedRequest = {
  accountId: string;
  scopeKey: string;
  switchIntentId: string;
  switchRevision: number;
  signal: AbortSignal;
};

export type AccountWorkspaceRuntimePort<
  TContext extends AccountWorkspaceContextLike = AccountWorkspaceContextLike
> = {
  fetchWorkspaceContext(request: AccountScopedRequest): Promise<TContext>;
  activateWorkspace?(
    request: AccountScopedRequest,
    context: TContext
  ): Promise<void>;
  cancelAccountScope(accountId: string): number | void;
};

export type ReversibleAccountSwitchResource = {
  commit(): Promise<void>;
  rollback(reason?: unknown): Promise<void>;
  finalize?(): Promise<void>;
};

export type AccountTopicCursor = {
  lastEventId: string | null;
  afterSequence: number | null;
};

export type AccountTopicSubscriptionPrepareRequest<
  TContext extends AccountWorkspaceContextLike = AccountWorkspaceContextLike
> = AccountScopedRequest & {
  previousAccountId: string | null;
  context: TContext;
  subscriptionRevision: number;
  cursors: Readonly<Record<string, AccountTopicCursor>>;
};

export type AccountTopicSubscriptionPort<
  TContext extends AccountWorkspaceContextLike = AccountWorkspaceContextLike
> = {
  prepareAccountTopics(
    request: AccountTopicSubscriptionPrepareRequest<TContext>
  ): Promise<ReversibleAccountSwitchResource>;
  clearAccountTopics(request: AccountContextClearRequest): Promise<void>;
};

export type AccountSurfacePrepareRequest<
  TContext extends AccountWorkspaceContextLike = AccountWorkspaceContextLike
> = AccountScopedRequest & {
  previousContext: TContext | null;
  context: TContext;
  preferredRoute: string;
  accountRevision: number;
};

export type AccountSurfaceRefreshRequest<
  TContext extends AccountWorkspaceContextLike = AccountWorkspaceContextLike
> = AccountScopedRequest & {
  context: TContext;
  accountRevision: number;
};

export type AccountContextSurfacePort<
  TContext extends AccountWorkspaceContextLike = AccountWorkspaceContextLike
> = {
  prepareAccountSurface(
    request: AccountSurfacePrepareRequest<TContext>
  ): Promise<ReversibleAccountSwitchResource>;
  refreshAccountSurface(request: AccountSurfaceRefreshRequest<TContext>): Promise<void>;
  clearAccountSurface(request: AccountContextClearRequest): Promise<void>;
};

export type AccountContextClearRequest = {
  accountId: string;
  accountRevision: number;
  subscriptionRevision: number;
  signal: AbortSignal;
};

export type AccountRouteMemoryPort = {
  loadLastRoutes(signal?: AbortSignal): Promise<Record<string, string>>;
  saveLastRoute(accountId: string, route: string, signal?: AbortSignal): Promise<void>;
  removeLastRoute?(accountId: string, signal?: AbortSignal): Promise<void>;
};

export type AccountContextLoggerPort = {
  debug(message: string, details?: unknown): void;
  info(message: string, details?: unknown): void;
  warn(message: string, details?: unknown): void;
  error(message: string, details?: unknown): void;
};

export type AccountContextGeneration = {
  accountId: string;
  accountRevision: number;
};

export type AccountSwitchResult =
  | {
      status: "switched";
      accountId: string;
      switchIntentId: string;
      accountRevision: number;
    }
  | { status: "unchanged"; accountId: string }
  | { status: "cancelled"; accountId: string }
  | { status: "superseded"; accountId: string }
  | { status: "failed"; accountId: string; error: AccountContextError };

export type AccountRefreshResult =
  | {
      status: "refreshed";
      accountId: string;
      switchIntentId: string;
      accountRevision: number;
    }
  | { status: "unavailable" }
  | { status: "superseded"; accountId: string }
  | { status: "failed"; accountId: string; error: AccountContextError };

export type AccountSwitchOptions = {
  topicCursors?: Readonly<Record<string, AccountTopicCursor>>;
  preferredRoute?: string;
};

export type AccountContextStorePorts<
  TContext extends AccountWorkspaceContextLike = AccountWorkspaceContextLike
> = {
  runtime: AccountWorkspaceRuntimePort<TContext>;
  subscriptions: AccountTopicSubscriptionPort<TContext>;
  surface: AccountContextSurfacePort<TContext>;
  routeMemory: AccountRouteMemoryPort;
  unsavedGuards: {
    run(
      prompt: Omit<UnsavedGuardPrompt, "guards">,
    ): Promise<UnsavedGuardRunResult>;
  };
  logger?: AccountContextLoggerPort;
  createIntentId?: () => string;
  defaultAccountRoute?: string;
};
