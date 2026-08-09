import {
  requestRuntimeV1,
  type RuntimeCallOptions,
  type RuntimeRevisionOptions
} from "./core";
import type { RuntimeClientResult } from "@/types/runtime/common";
import type {
  SystemConfigDto,
  SystemConfigPatchInput
} from "@/types/runtime/system-config";

export type SystemConfigRequest = RuntimeCallOptions & {
  prefix?: string;
};

export function fetchSystemConfig(
  options: SystemConfigRequest = {}
): Promise<RuntimeClientResult<SystemConfigDto>> {
  const query = new URLSearchParams();
  const prefix = options.prefix?.trim();
  if (prefix) {
    query.set("prefix", prefix);
  }
  const serialized = query.toString();
  const path = serialized
    ? `/api/v1/system/config?${serialized}`
    : "/api/v1/system/config";
  return requestRuntimeV1<SystemConfigDto>(path, options);
}

export function patchSystemConfig(
  input: SystemConfigPatchInput,
  options: RuntimeRevisionOptions
): Promise<RuntimeClientResult<SystemConfigDto>> {
  return requestRuntimeV1<SystemConfigDto>("/api/v1/system/config", {
    ...options,
    body: input,
    method: "PATCH"
  });
}
