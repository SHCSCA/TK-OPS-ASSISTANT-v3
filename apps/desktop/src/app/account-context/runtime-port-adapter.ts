import {
  activateAccountWorkspace,
  getAccountWorkspaceContext
} from "@/app/runtime-client/accounts";
import { cancelAccountRuntimeRequests } from "@/app/runtime-client/core";
import type { AccountWorkspaceContextDto } from "@/types/runtime/accounts";

import type { AccountWorkspaceRuntimePort } from "./types";

export function createAccountWorkspaceRuntimePort(): AccountWorkspaceRuntimePort<AccountWorkspaceContextDto> {
  return {
    async fetchWorkspaceContext(request) {
      const result = await getAccountWorkspaceContext(request.accountId, {
        operationId: request.switchIntentId,
        scopeKey: request.scopeKey,
        signal: request.signal
      });
      return result.data;
    },
    async activateWorkspace(request, context) {
      await activateAccountWorkspace(request.accountId, {
        expectedRevision: context.account.revision,
        idempotencyKey: `workspace-active-${request.switchIntentId}`,
        operationId: request.switchIntentId,
        scopeKey: request.scopeKey,
        signal: request.signal
      });
    },
    cancelAccountScope(accountId) {
      return cancelAccountRuntimeRequests(accountId);
    }
  };
}
