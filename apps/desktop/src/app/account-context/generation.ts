import { AccountScopeMismatchError } from "./errors";
import type {
  AccountContextGeneration,
  AccountContextState,
  AccountWorkspaceContextLike
} from "./types";

export const ACCOUNT_CONTEXT_TOPIC_RESOURCES = [
  "workspace",
  "tasks",
  "connection",
  "knowledge"
] as const;

export function accountScopeKey(accountId: string): string {
  return `account:${accountId}`;
}

export function accountContextTopics(accountId: string): string[] {
  return ACCOUNT_CONTEXT_TOPIC_RESOURCES.map(
    (resource) => `account:${accountId}:${resource}`
  );
}

export function captureAccountGeneration(
  state: Pick<AccountContextState, "currentAccountId" | "accountRevision">
): AccountContextGeneration | null {
  if (!state.currentAccountId) return null;
  return {
    accountId: state.currentAccountId,
    accountRevision: state.accountRevision
  };
}

export function isAccountGenerationCurrent(
  state: Pick<AccountContextState, "currentAccountId" | "accountRevision">,
  generation: AccountContextGeneration,
  responseAccountId: string = generation.accountId
): boolean {
  return (
    responseAccountId === generation.accountId &&
    state.currentAccountId === generation.accountId &&
    state.accountRevision === generation.accountRevision
  );
}

export function assertWorkspaceContextScope<
  TContext extends AccountWorkspaceContextLike
>(context: TContext, expectedAccountId: string): TContext {
  if (context.account.id !== expectedAccountId) {
    throw new AccountScopeMismatchError(expectedAccountId, context.account.id);
  }
  return context;
}
