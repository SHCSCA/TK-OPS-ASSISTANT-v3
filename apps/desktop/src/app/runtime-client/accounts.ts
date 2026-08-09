import {
  accountRequestScopeKey,
  assertRuntimeAccountScope,
  assertStableResourceId,
  requestRuntimeV1,
  RuntimeError,
  type RuntimeCallOptions,
  type RuntimeIdempotentOptions,
  type RuntimeRevisionIdempotentOptions,
  type RuntimeRevisionOptions
} from "./core";
import type {
  AccountConfigCopyResultDto,
  AccountCopyInput,
  AccountCreateInput,
  AccountDto,
  AccountListDto,
  AccountListQuery,
  AccountPatchInput,
  AccountReadinessDto,
  AccountWorkspaceContextDto,
  AccountWorkspaceInclude,
  ArchiveInput,
  CompleteWizardInput,
  ConnectionBindingInput,
  ConnectionCandidatesDto,
  ConnectionCheckInput,
  ConnectionDto,
  HealthCheckInput
} from "@/types/runtime/accounts";
import type { RuntimeClientResult } from "@/types/runtime/common";
import type { TaskAcceptedDto } from "@/types/runtime/tasks";

export type AccountWorkspaceContextRequest = RuntimeCallOptions & {
  include?: AccountWorkspaceInclude[];
};

export function listAccounts(
  query: AccountListQuery = {},
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<AccountListDto>> {
  const path = withQuery("/api/v1/accounts", buildAccountListQuery(query));
  return requestRuntimeV1<AccountListDto>(path, {
    ...options,
    validateData: validateAccountList
  });
}

export function createAccount(
  input: AccountCreateInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<AccountDto>> {
  return requestRuntimeV1<AccountDto>("/api/v1/accounts", {
    ...options,
    body: input,
    method: "POST",
    validateData: validateAccountDto
  });
}

export function getAccount(
  accountId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<AccountDto>> {
  const path = accountPath(accountId);
  return requestRuntimeV1<AccountDto>(path, accountRequestOptions(accountId, options, {
    validateData: (data) => validateAccountScope(accountId, data)
  }));
}

export function patchAccount(
  accountId: string,
  input: AccountPatchInput,
  options: RuntimeRevisionOptions
): Promise<RuntimeClientResult<AccountDto>> {
  const path = accountPath(accountId);
  return requestRuntimeV1<AccountDto>(path, accountRequestOptions(accountId, options, {
    body: input,
    method: "PATCH",
    validateData: (data) => validateAccountScope(accountId, data)
  }));
}

export function getAccountWorkspaceContext(
  accountId: string,
  options: AccountWorkspaceContextRequest = {}
): Promise<RuntimeClientResult<AccountWorkspaceContextDto>> {
  const query = new URLSearchParams();
  for (const include of options.include ?? []) {
    query.append("include", include);
  }
  const path = withQuery(`${accountPath(accountId)}/workspace-context`, query);
  return requestRuntimeV1<AccountWorkspaceContextDto>(
    path,
    accountRequestOptions(accountId, options, {
      validateData: (data) => {
        validateAccountScope(accountId, data.account);
        if (data.readiness !== data.account.readiness) {
          validateReadinessShape(data.readiness);
        }
      }
    })
  );
}

export function activateAccountWorkspace(
  accountId: string,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<AccountDto>> {
  const path = `${accountPath(accountId)}/workspace-activation`;
  return requestRuntimeV1<AccountDto>(
    path,
    accountRequestOptions(accountId, options, {
      method: "POST",
      validateData: (data) => validateAccountScope(accountId, data)
    })
  );
}

export function completeAccountWizard(
  accountId: string,
  input: CompleteWizardInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<AccountDto>> {
  const path = `${accountPath(accountId)}/complete-wizard`;
  return requestRuntimeV1<AccountDto>(path, accountRequestOptions(accountId, options, {
    body: input,
    method: "POST",
    validateData: (data) => validateAccountScope(accountId, data)
  }));
}

export function copyAccountConfig(
  targetAccountId: string,
  input: AccountCopyInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<AccountConfigCopyResultDto>> {
  assertStableResourceId(input.sourceAccountId, "sourceAccountId");
  const path = `${accountPath(targetAccountId)}/copy-config`;
  return requestRuntimeV1<AccountConfigCopyResultDto>(
    path,
    accountRequestOptions(targetAccountId, options, {
      body: input,
      method: "POST",
      validateData: (data) => {
        assertRuntimeAccountScope(
          targetAccountId,
          data.targetAccountId,
          "targetAccountId"
        );
      }
    })
  );
}

export function archiveAccount(
  accountId: string,
  input: ArchiveInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<TaskAcceptedDto>> {
  const path = `${accountPath(accountId)}/archive`;
  return requestRuntimeV1<TaskAcceptedDto>(path, accountRequestOptions(accountId, options, {
    body: input,
    method: "POST",
    validateData: (data) => validateTaskScope(accountId, data)
  }));
}

export function restoreAccount(
  accountId: string,
  input: HealthCheckInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<TaskAcceptedDto>> {
  const path = `${accountPath(accountId)}/restore`;
  return requestRuntimeV1<TaskAcceptedDto>(
    path,
    accountRequestOptions(accountId, options, {
      body: input,
      method: "POST",
      validateData: (data) => validateTaskScope(accountId, data)
    })
  );
}

export function getAccountHealth(
  accountId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<AccountReadinessDto>> {
  const path = `${accountPath(accountId)}/health`;
  return requestRuntimeV1<AccountReadinessDto>(
    path,
    accountRequestOptions(accountId, options, {
      validateData: validateReadinessShape
    })
  );
}

export function startAccountHealthChecks(
  accountId: string,
  input: HealthCheckInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<TaskAcceptedDto>> {
  const path = `${accountPath(accountId)}/health-checks`;
  return requestRuntimeV1<TaskAcceptedDto>(
    path,
    accountRequestOptions(accountId, options, {
      body: input,
      method: "POST",
      validateData: (data) => validateTaskScope(accountId, data)
    })
  );
}

export function getAccountConnection(
  accountId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<ConnectionDto>> {
  const path = `${accountPath(accountId)}/connection`;
  return requestRuntimeV1<ConnectionDto>(
    path,
    accountRequestOptions(accountId, options, {
      validateData: (data) => validateConnectionScope(accountId, data)
    })
  );
}

export function listAccountConnectionCandidates(
  accountId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<ConnectionCandidatesDto>> {
  const path = `${accountPath(accountId)}/connection/candidates`;
  return requestRuntimeV1<ConnectionCandidatesDto>(
    path,
    accountRequestOptions(accountId, options, {
      validateData: validateConnectionCandidates
    })
  );
}

export function bindAccountConnection(
  accountId: string,
  input: ConnectionBindingInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<ConnectionDto>> {
  assertStableResourceId(input.environmentId, "environmentId");
  if (!Number.isInteger(input.eligibilityRevision) || input.eligibilityRevision < 1) {
    throw new RuntimeError("执行环境资格修订号无效，请刷新候选后重试。", {
      errorCode: "REQUEST_VALIDATION_FAILED",
      status: 422
    });
  }
  const path = `${accountPath(accountId)}/connection/binding`;
  return requestRuntimeV1<ConnectionDto>(
    path,
    accountRequestOptions(accountId, options, {
      body: input,
      method: "PUT",
      validateData: (data) => validateConnectionScope(accountId, data)
    })
  );
}

export function unbindAccountConnection(
  accountId: string,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<ConnectionDto>> {
  const path = `${accountPath(accountId)}/connection/binding`;
  return requestRuntimeV1<ConnectionDto>(
    path,
    accountRequestOptions(accountId, options, {
      method: "DELETE",
      validateData: (data) => validateConnectionScope(accountId, data)
    })
  );
}

export function startAccountConnectionCheck(
  accountId: string,
  input: ConnectionCheckInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<TaskAcceptedDto>> {
  const path = `${accountPath(accountId)}/connection/checks`;
  return requestRuntimeV1<TaskAcceptedDto>(
    path,
    accountRequestOptions(accountId, options, {
      body: input,
      method: "POST",
      validateData: (data) => validateTaskScope(accountId, data)
    })
  );
}

function accountPath(accountId: string): string {
  assertStableResourceId(accountId, "account_id");
  return `/api/v1/accounts/${encodeURIComponent(accountId)}`;
}

function accountRequestOptions<T>(
  accountId: string,
  options: RuntimeCallOptions
    & Partial<RuntimeIdempotentOptions>
    & Partial<RuntimeRevisionOptions>,
  request: {
    body?: unknown;
    method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
    validateData?: (data: T) => void;
  }
): RuntimeCallOptions
  & Partial<RuntimeIdempotentOptions>
  & Partial<RuntimeRevisionOptions>
  & typeof request {
  const expectedScopeKey = accountRequestScopeKey(accountId);
  if (options.scopeKey && options.scopeKey !== expectedScopeKey) {
    throw new RuntimeError("账号请求范围与目标账号不一致。", {
      errorCode: "ACCOUNT_SCOPE_MISMATCH",
      status: 403
    });
  }
  if (
    options.expectedRevision !== undefined
    && (!Number.isInteger(options.expectedRevision) || options.expectedRevision < 1)
  ) {
    throw new RuntimeError("账号修订号无效，请重新加载后再试。", {
      errorCode: "REQUEST_VALIDATION_FAILED",
      fieldErrors: [
        {
          field: "If-Match",
          code: "invalid_account_revision",
          message: "账号修订号必须为正整数"
        }
      ],
      status: 422
    });
  }
  return {
    ...options,
    ...request,
    scopeKey: expectedScopeKey
  };
}

function buildAccountListQuery(query: AccountListQuery): URLSearchParams {
  const params = new URLSearchParams();
  const normalizedQuery = query.q?.trim();
  if (normalizedQuery) {
    params.set("q", normalizedQuery);
  }
  if (query.status) {
    params.set("status", query.status);
  }
  if (query.cursor) {
    params.set("cursor", query.cursor);
  }
  if (query.limit !== undefined) {
    params.set("limit", String(query.limit));
  }
  return params;
}

function withQuery(path: string, query: URLSearchParams): string {
  const serialized = query.toString();
  return serialized ? `${path}?${serialized}` : path;
}

function validateAccountList(data: AccountListDto): void {
  for (const account of data.items) {
    validateAccountDto(account);
  }
}

function validateAccountDto(account: AccountDto): void {
  assertStableResourceId(account.id, "account.id");
  if (
    !Object.prototype.hasOwnProperty.call(account, "positioningSummary") ||
    !Object.prototype.hasOwnProperty.call(account, "lastUsedAt")
  ) {
    throw new RuntimeError("Runtime 账号摘要字段不完整，请升级 Runtime 后重试。", {
      errorCode: "INTERNAL_ERROR",
      status: 502
    });
  }
  validateReadinessShape(account.readiness);
}

function validateAccountScope(accountId: string, account: AccountDto): void {
  validateAccountDto(account);
  assertRuntimeAccountScope(accountId, account.id, "account.id");
}

function validateConnectionScope(accountId: string, connection: ConnectionDto): void {
  assertRuntimeAccountScope(accountId, connection.accountId, "connection.accountId");
}

function validateConnectionCandidates(candidates: ConnectionCandidatesDto): void {
  for (const candidate of candidates.items) {
    assertStableResourceId(candidate.environmentId, "environmentId");
    assertStableResourceId(candidate.deviceWorkspace.id, "deviceWorkspace.id");
    assertStableResourceId(candidate.browserInstance.id, "browserInstance.id");
    assertStableResourceId(candidate.executionBinding.id, "executionBinding.id");
    if (
      candidate.environmentId !== candidate.executionBinding.id ||
      !Number.isInteger(candidate.eligibilityRevision) ||
      candidate.eligibilityRevision < 1 ||
      candidate.executionBinding.deviceWorkspaceId !==
        candidate.deviceWorkspace.id ||
      candidate.executionBinding.browserInstanceId !==
        candidate.browserInstance.id
    ) {
      throw new RuntimeError("Runtime 返回了不一致的执行连接候选，已阻止使用。", {
        errorCode: "EXECUTION_BINDING_INVALID",
        status: 409
      });
    }
  }
}

function validateTaskScope(accountId: string, task: TaskAcceptedDto): void {
  assertRuntimeAccountScope(accountId, task.accountId ?? "", "task.accountId");
}

function validateReadinessShape(readiness: AccountReadinessDto): void {
  const items = [readiness.connection, readiness.knowledge, readiness.ai];
  for (const item of items) {
    if (item.logId) {
      assertStableResourceId(item.logId, "readiness.logId");
    }
    if (item.suggestedAction?.taskId) {
      assertStableResourceId(item.suggestedAction.taskId, "readiness.taskId");
    }
  }
}
