import type { InjectionKey } from "vue";

import type { UnsavedGuard } from "@/app/account-context";

export type AccountUnsavedGuardRegistrar = {
  register(guard: UnsavedGuard): () => void;
};

export const accountUnsavedGuardRegistrarKey: InjectionKey<AccountUnsavedGuardRegistrar> =
  Symbol("account-unsaved-guard-registrar");

