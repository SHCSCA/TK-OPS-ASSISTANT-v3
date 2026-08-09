export const ACCOUNTS_CHANGED_EVENT = "tk-ops:accounts-changed";

export type AccountDirectoryChangeReason =
  | "created"
  | "updated"
  | "archived"
  | "archive-submitted"
  | "restore-submitted"
  | "wizard-completed";

export function notifyAccountDirectoryChanged(
  accountId: string,
  reason: AccountDirectoryChangeReason
): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(ACCOUNTS_CHANGED_EVENT, {
      detail: { accountId, reason }
    })
  );
}
