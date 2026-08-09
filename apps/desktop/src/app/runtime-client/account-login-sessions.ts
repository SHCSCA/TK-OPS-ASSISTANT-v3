import type { RuntimeClientResult } from "@/types/runtime/common";
import type {
  LoginSessionAcceptedDto,
  LoginSessionDto
} from "@/types/runtime/account-login-sessions";

import {
  accountRequestScopeKey,
  assertRuntimeAccountScope,
  assertStableResourceId,
  requestRuntimeV1,
  type RuntimeCallOptions,
  type RuntimeIdempotentOptions
} from "./core";

export function createAccountLoginSession(
  accountId: string,
  environmentId: string,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<LoginSessionAcceptedDto>> {
  assertStableResourceId(environmentId, "environmentId");
  return requestRuntimeV1<LoginSessionAcceptedDto>(loginSessionsPath(accountId), {
    ...options,
    body: { environmentId },
    method: "POST",
    scopeKey: accountRequestScopeKey(accountId),
    validateData: validateAccepted
  });
}

export function getAccountLoginSession(
  accountId: string,
  sessionId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<LoginSessionDto>> {
  return requestRuntimeV1<LoginSessionDto>(loginSessionPath(accountId, sessionId), {
    ...options,
    scopeKey: accountRequestScopeKey(accountId),
    validateData: (data) => validateSession(accountId, data)
  });
}

export function probeAccountLoginSession(
  accountId: string,
  sessionId: string,
  revision: number,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<LoginSessionAcceptedDto>> {
  return requestRuntimeV1<LoginSessionAcceptedDto>(
    `${loginSessionPath(accountId, sessionId)}/probe`,
    {
      ...options,
      body: { revision },
      method: "POST",
      scopeKey: accountRequestScopeKey(accountId),
      validateData: validateAccepted
    }
  );
}

export function cancelAccountLoginSession(
  accountId: string,
  sessionId: string,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<LoginSessionDto>> {
  return requestRuntimeV1<LoginSessionDto>(loginSessionPath(accountId, sessionId), {
    ...options,
    method: "DELETE",
    scopeKey: accountRequestScopeKey(accountId),
    validateData: (data) => validateSession(accountId, data)
  });
}

function loginSessionsPath(accountId: string): string {
  assertStableResourceId(accountId, "account_id");
  return `/api/v1/accounts/${encodeURIComponent(accountId)}/connection/login-sessions`;
}

function loginSessionPath(accountId: string, sessionId: string): string {
  assertStableResourceId(sessionId, "session_id");
  return `${loginSessionsPath(accountId)}/${encodeURIComponent(sessionId)}`;
}

function validateAccepted(data: LoginSessionAcceptedDto): void {
  assertStableResourceId(data.sessionId, "sessionId");
  assertStableResourceId(data.taskId, "taskId");
}

function validateSession(accountId: string, data: LoginSessionDto): void {
  assertStableResourceId(data.id, "session.id");
  assertRuntimeAccountScope(accountId, data.accountId, "session.accountId");
  assertStableResourceId(data.environmentId, "session.environmentId");
  if (!Number.isInteger(data.revision) || data.revision < 1) {
    throw new Error("Runtime 返回的登录状态修订号无效。");
  }
}
