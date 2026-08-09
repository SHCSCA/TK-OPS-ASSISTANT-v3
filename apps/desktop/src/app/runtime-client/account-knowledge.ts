import type {
  BrandKitDto,
  BrandKitVersionInput,
  KnowledgeDto,
  KnowledgeIndexInput,
  KnowledgeRulesInput,
  KnowledgeSnapshotDto,
  KnowledgeSnapshotInput,
  KnowledgeSnapshotPageDto,
  KnowledgeSnapshotQuery,
  KnowledgeSourceDto,
  KnowledgeSourceInput,
  KnowledgeSourcePageDto,
  KnowledgeSourceQuery,
  PositioningDto,
  PositioningVersionDto,
  PositioningVersionInput
} from "@/types/runtime/account-knowledge";
import type { RuntimeClientResult } from "@/types/runtime/common";
import type { TaskAcceptedDto } from "@/types/runtime/tasks";

import {
  accountRequestScopeKey,
  assertRuntimeAccountScope,
  assertStableResourceId,
  requestRuntimeV1,
  RuntimeError,
  type RuntimeCallOptions,
  type RuntimeIdempotentOptions,
  type RuntimeRequestOptions,
  type RuntimeRevisionIdempotentOptions,
  type RuntimeRevisionOptions
} from "./core";

type AccountOptions = RuntimeCallOptions
  & Partial<RuntimeIdempotentOptions>
  & Partial<RuntimeRevisionOptions>;

export function getAccountPositioning(
  accountId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<PositioningDto>> {
  return requestRuntimeV1(
    `${accountPath(accountId)}/positioning`,
    scopedOptions(accountId, options, validatePositioning(accountId))
  );
}

export function getAccountPositioningVersion(
  accountId: string,
  version: number,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<PositioningVersionDto>> {
  assertPositiveInteger(version, "version");
  return requestRuntimeV1(
    `${accountPath(accountId)}/positioning/versions/${version}`,
    scopedOptions(
      accountId,
      options,
      validatePositioningVersion(accountId, version)
    )
  );
}

export function createAccountPositioningVersion(
  accountId: string,
  input: PositioningVersionInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<PositioningVersionDto>> {
  return requestRuntimeV1(
    `${accountPath(accountId)}/positioning/versions`,
    scopedOptions(accountId, options, validatePositioningVersion(accountId), {
      body: input,
      method: "POST"
    })
  );
}

export function activateAccountPositioningVersion(
  accountId: string,
  version: number,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<PositioningDto>> {
  assertPositiveInteger(version, "version");
  return requestRuntimeV1(
    `${accountPath(accountId)}/positioning/versions/${version}/activate`,
    scopedOptions(accountId, options, validatePositioning(accountId), {
      method: "POST"
    })
  );
}

export function getAccountKnowledge(
  accountId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<KnowledgeDto>> {
  return requestRuntimeV1(
    `${accountPath(accountId)}/knowledge`,
    scopedOptions(
      accountId,
      options,
      validateAccountDto<KnowledgeDto>(accountId, "knowledge")
    )
  );
}

export function updateAccountKnowledgeRules(
  accountId: string,
  input: KnowledgeRulesInput,
  options: RuntimeRevisionOptions
): Promise<RuntimeClientResult<KnowledgeDto>> {
  return requestRuntimeV1(
    `${accountPath(accountId)}/knowledge`,
    scopedOptions(
      accountId,
      options,
      validateAccountDto<KnowledgeDto>(accountId, "knowledge"),
      { body: input, method: "PATCH" }
    )
  );
}

export function listAccountKnowledgeSources(
  accountId: string,
  query: KnowledgeSourceQuery = {},
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<KnowledgeSourcePageDto>> {
  const path = withQuery(
    `${accountPath(accountId)}/knowledge/sources`,
    sourceQuery(query)
  );
  return requestRuntimeV1(
    path,
    scopedOptions(accountId, options, (data: KnowledgeSourcePageDto) => {
      const validate = validateKnowledgeSource(accountId);
      data.items.forEach(validate);
    })
  );
}

export function createAccountKnowledgeSource(
  accountId: string,
  input: KnowledgeSourceInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<KnowledgeSourceDto>> {
  return requestRuntimeV1(
    `${accountPath(accountId)}/knowledge/sources`,
    scopedOptions(accountId, options, validateKnowledgeSource(accountId), {
      body: input,
      method: "POST"
    })
  );
}

export function removeAccountKnowledgeSource(
  accountId: string,
  sourceId: string,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<KnowledgeSourceDto>> {
  assertStableResourceId(sourceId, "source_id");
  return requestRuntimeV1(
    `${accountPath(accountId)}/knowledge/sources/${encodeURIComponent(sourceId)}`,
    scopedOptions(accountId, options, validateKnowledgeSource(accountId), {
      method: "DELETE"
    })
  );
}

export function startAccountKnowledgeIndex(
  accountId: string,
  input: KnowledgeIndexInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<TaskAcceptedDto>> {
  input.sourceIds?.forEach((sourceId) => {
    assertStableResourceId(sourceId, "sourceIds");
  });
  return requestRuntimeV1(
    `${accountPath(accountId)}/knowledge/index-jobs`,
    scopedOptions(accountId, options, validateAccountTask(accountId), {
      body: input,
      method: "POST"
    })
  );
}

export function listAccountKnowledgeSnapshots(
  accountId: string,
  query: KnowledgeSnapshotQuery = {},
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<KnowledgeSnapshotPageDto>> {
  const path = withQuery(
    `${accountPath(accountId)}/knowledge/snapshots`,
    pageQuery(query)
  );
  return requestRuntimeV1(
    path,
    scopedOptions(accountId, options, (data: KnowledgeSnapshotPageDto) => {
      const validate = validateSnapshot(accountId);
      data.items.forEach(validate);
    })
  );
}

export function createAccountKnowledgeSnapshot(
  accountId: string,
  input: KnowledgeSnapshotInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<KnowledgeSnapshotDto>> {
  input.sourceIds.forEach((sourceId) => {
    assertStableResourceId(sourceId, "sourceIds");
  });
  return requestRuntimeV1(
    `${accountPath(accountId)}/knowledge/snapshots`,
    scopedOptions(accountId, options, validateSnapshot(accountId), {
      body: input,
      method: "POST"
    })
  );
}

export function getAccountKnowledgeSnapshot(
  accountId: string,
  snapshotId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<KnowledgeSnapshotDto>> {
  assertStableResourceId(snapshotId, "snapshot_id");
  return requestRuntimeV1(
    `${accountPath(accountId)}/knowledge/snapshots/${encodeURIComponent(snapshotId)}`,
    scopedOptions(accountId, options, validateSnapshot(accountId))
  );
}

export function getAccountBrandKit(
  accountId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<BrandKitDto>> {
  return requestRuntimeV1(
    `${accountPath(accountId)}/brand-kit`,
    scopedOptions(
      accountId,
      options,
      validateAccountDto<BrandKitDto>(accountId, "brandKit")
    )
  );
}

export function updateAccountBrandKit(
  accountId: string,
  input: BrandKitVersionInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<BrandKitDto>> {
  return requestRuntimeV1(
    `${accountPath(accountId)}/brand-kit`,
    scopedOptions(
      accountId,
      options,
      validateAccountDto<BrandKitDto>(accountId, "brandKit"),
      { body: input, method: "PUT" }
    )
  );
}

function accountPath(accountId: string): string {
  assertStableResourceId(accountId, "account_id");
  return `/api/v1/accounts/${encodeURIComponent(accountId)}`;
}

function scopedOptions<T>(
  accountId: string,
  options: AccountOptions,
  validateData: (data: T) => void,
  request: { body?: unknown; method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE" } = {}
): RuntimeRequestOptions<T> {
  const scopeKey = accountRequestScopeKey(accountId);
  if (options.scopeKey && options.scopeKey !== scopeKey) {
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
      fieldErrors: [{
        field: "If-Match",
        code: "invalid_account_revision",
        message: "账号修订号必须为正整数"
      }],
      status: 422
    });
  }
  return { ...options, ...request, scopeKey, validateData };
}

function validatePositioning(accountId: string) {
  return (data: PositioningDto): void => {
    assertRuntimeAccountScope(accountId, data.accountId, "positioning.accountId");
    assertPositiveInteger(data.revision, "positioning.revision");
  };
}

function validatePositioningVersion(
  accountId: string,
  expectedVersion?: number
) {
  return (data: PositioningVersionDto): void => {
    assertRuntimeAccountScope(accountId, data.accountId, "positioningVersion.accountId");
    assertStableResourceId(data.id, "positioningVersion.id");
    assertPositiveInteger(data.version, "positioningVersion.version");
    if (
      expectedVersion !== undefined
      && data.version !== expectedVersion
    ) {
      throw new RuntimeError("Runtime 返回的定位版本与请求不一致，请刷新后重试。", {
        errorCode: "INTERNAL_ERROR",
        fieldErrors: [{
          field: "positioningVersion.version",
          code: "response_version_mismatch",
          message: "响应版本必须与请求版本一致"
        }],
        status: 500
      });
    }
  };
}

function validateKnowledgeSource(accountId: string) {
  return (data: KnowledgeSourceDto): void => {
    assertRuntimeAccountScope(accountId, data.accountId, "knowledgeSource.accountId");
    assertStableResourceId(data.id, "knowledgeSource.id");
  };
}

function validateSnapshot(accountId: string) {
  return (data: KnowledgeSnapshotDto): void => {
    assertRuntimeAccountScope(accountId, data.accountId, "knowledgeSnapshot.accountId");
    assertStableResourceId(data.id, "knowledgeSnapshot.id");
  };
}

function validateAccountDto<T extends { accountId: string }>(
  accountId: string,
  field: string
) {
  return (data: T): void => {
    assertRuntimeAccountScope(accountId, data.accountId, `${field}.accountId`);
  };
}

function validateAccountTask(accountId: string) {
  return (data: TaskAcceptedDto): void => {
    assertRuntimeAccountScope(accountId, data.accountId ?? "", "task.accountId");
  };
}

function sourceQuery(query: KnowledgeSourceQuery): URLSearchParams {
  const params = pageQuery(query);
  if (query.kind) params.set("kind", query.kind);
  if (query.status) params.set("status", query.status);
  return params;
}

function pageQuery(query: KnowledgeSnapshotQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.cursor) params.set("cursor", query.cursor);
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  return params;
}

function withQuery(path: string, query: URLSearchParams): string {
  const serialized = query.toString();
  return serialized ? `${path}?${serialized}` : path;
}

function assertPositiveInteger(value: number, field: string): void {
  if (Number.isInteger(value) && value > 0) return;
  throw new RuntimeError("Runtime 返回了无效修订信息，请刷新后重试。", {
    errorCode: "INTERNAL_ERROR",
    fieldErrors: [{ field, code: "invalid_positive_integer", message: "必须为正整数" }],
    status: 500
  });
}
