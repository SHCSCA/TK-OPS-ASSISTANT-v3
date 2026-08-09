import type { UnsavedGuard } from "@/app/account-context";
import type { AccountUnsavedGuardRegistrar } from "@/modules/accounts/account-guard-port";
import type { useAccountKnowledgeStore } from "./account-knowledge-store";

export type AccountUnsavedGuardRegister =
  AccountUnsavedGuardRegistrar["register"];

export function createAccountKnowledgeUnsavedGuard(
  store: ReturnType<typeof useAccountKnowledgeStore>,
  accountId: string
): UnsavedGuard {
  return {
    id: `strategy-knowledge:${accountId}`,
    label: "定位与知识",
    isDirty: () => store.hasUnsaved(accountId),
    save: () => store.saveUnsaved(accountId),
    discard: () => store.discardUnsaved(accountId)
  };
}
