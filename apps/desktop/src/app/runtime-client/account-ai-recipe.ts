import type {
  AccountAIRecipeDto,
  AccountAIRecipeValidationDto,
  AccountAIRecipeVersionDto,
  AccountAIRecipeVersionInput,
  AccountAIRecipeVersionPageDto,
  AccountAIRecipeVersionQuery
} from "@/types/runtime/account-ai-recipe";
import type { RuntimeClientResult } from "@/types/runtime/common";

import {
  accountRequestScopeKey,
  assertRuntimeAccountScope,
  assertStableResourceId,
  requestRuntimeV1,
  RuntimeError,
  type RuntimeCallOptions,
  type RuntimeIdempotentOptions,
  type RuntimeRequestOptions,
  type RuntimeRevisionIdempotentOptions
} from "./core";

type AccountRecipeOptions = RuntimeCallOptions
  & Partial<RuntimeIdempotentOptions>
  & Partial<RuntimeRevisionIdempotentOptions>;

export function getAccountAIRecipe(
  accountId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<AccountAIRecipeDto>> {
  return requestRuntimeV1(recipePath(accountId), scopedOptions(
    accountId,
    options,
    validateRecipe(accountId)
  ));
}

export function listAccountAIRecipeVersions(
  accountId: string,
  query: AccountAIRecipeVersionQuery = {},
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<AccountAIRecipeVersionPageDto>> {
  const params = new URLSearchParams();
  if (query.cursor) params.set("cursor", query.cursor);
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  const serialized = params.toString();
  const path = `${recipePath(accountId)}/versions${serialized ? `?${serialized}` : ""}`;
  return requestRuntimeV1(path, scopedOptions(
    accountId,
    options,
    (data: AccountAIRecipeVersionPageDto) => {
      data.items.forEach(validateRecipeVersion(accountId));
    }
  ));
}

export function createAccountAIRecipeVersion(
  accountId: string,
  input: AccountAIRecipeVersionInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<AccountAIRecipeVersionDto>> {
  return requestRuntimeV1(`${recipePath(accountId)}/versions`, scopedOptions(
    accountId,
    options,
    validateRecipeVersion(accountId),
    { body: input, method: "POST" }
  ));
}

export function validateAccountAIRecipeVersion(
  accountId: string,
  version: number,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<AccountAIRecipeValidationDto>> {
  return requestRuntimeV1(
    `${recipePath(accountId)}/versions/${versionPath(version)}/validate`,
    scopedOptions(accountId, options, (data: AccountAIRecipeValidationDto) => {
      assertRuntimeAccountScope(accountId, data.accountId, "aiRecipe.accountId");
      assertPositiveInteger(data.version, "aiRecipe.version");
    }, { method: "POST" })
  );
}

export function activateAccountAIRecipeVersion(
  accountId: string,
  version: number,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<AccountAIRecipeDto>> {
  return requestRuntimeV1(
    `${recipePath(accountId)}/versions/${versionPath(version)}/activate`,
    scopedOptions(accountId, options, validateRecipe(accountId), { method: "POST" })
  );
}

function recipePath(accountId: string): string {
  assertStableResourceId(accountId, "account_id");
  return `/api/v1/accounts/${encodeURIComponent(accountId)}/ai-recipe`;
}

function versionPath(version: number): string {
  assertPositiveInteger(version, "version");
  return String(version);
}

function scopedOptions<T>(
  accountId: string,
  options: AccountRecipeOptions,
  validateData: (data: T) => void,
  request: { body?: unknown; method?: "GET" | "POST" } = {}
): RuntimeRequestOptions<T> {
  const scopeKey = accountRequestScopeKey(accountId);
  if (options.scopeKey && options.scopeKey !== scopeKey) {
    throw new RuntimeError("账号 AI 配方请求范围与目标账号不一致。", {
      errorCode: "ACCOUNT_SCOPE_MISMATCH",
      status: 403
    });
  }
  return { ...options, ...request, scopeKey, validateData };
}

function validateRecipe(accountId: string) {
  return (data: AccountAIRecipeDto): void => {
    assertRuntimeAccountScope(accountId, data.accountId, "aiRecipe.accountId");
    assertPositiveInteger(data.revision, "aiRecipe.revision");
  };
}

function validateRecipeVersion(accountId: string) {
  return (data: AccountAIRecipeVersionDto): void => {
    assertRuntimeAccountScope(accountId, data.accountId, "aiRecipeVersion.accountId");
    assertStableResourceId(data.id, "aiRecipeVersion.id");
    assertPositiveInteger(data.version, "aiRecipeVersion.version");
    assertPositiveInteger(data.revision, "aiRecipeVersion.revision");
  };
}

function assertPositiveInteger(value: number, field: string): void {
  if (Number.isInteger(value) && value > 0) return;
  throw new RuntimeError("Runtime 返回的账号 AI 配方修订无效。", {
    errorCode: "INTERNAL_ERROR",
    fieldErrors: [{
      field,
      code: "invalid_positive_integer",
      message: "必须为正整数"
    }],
    status: 500
  });
}
