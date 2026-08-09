import {
  requestRuntimeV1,
  type RuntimeCallOptions,
  type RuntimeIdempotentOptions
} from "./core";
import type {
  BootstrapStatusDto,
  DirectoryInitializationInput,
  DirectoryReportDto,
  LicenseActivationInput,
  LicenseStatusDto,
  SelfCheckInput
} from "@/types/runtime/bootstrap";
import type { RuntimeClientResult } from "@/types/runtime/common";
import type { TaskAcceptedDto } from "@/types/runtime/tasks";

export function fetchBootstrapStatus(
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<BootstrapStatusDto>> {
  return requestRuntimeV1<BootstrapStatusDto>("/api/v1/bootstrap/status", options);
}

export function fetchBootstrapLicense(
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<LicenseStatusDto>> {
  return requestRuntimeV1<LicenseStatusDto>("/api/v1/bootstrap/license", options);
}

export function activateBootstrapLicense(
  input: LicenseActivationInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<LicenseStatusDto>> {
  return requestRuntimeV1<LicenseStatusDto>("/api/v1/bootstrap/license/activate", {
    ...options,
    body: input,
    method: "POST"
  });
}

export function initializeBootstrapDirectories(
  input: DirectoryInitializationInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<DirectoryReportDto>> {
  return requestRuntimeV1<DirectoryReportDto>("/api/v1/bootstrap/directories/initialize", {
    ...options,
    body: input,
    method: "POST"
  });
}

export function startBootstrapSelfChecks(
  input: SelfCheckInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<TaskAcceptedDto>> {
  return requestRuntimeV1<TaskAcceptedDto>("/api/v1/bootstrap/self-checks", {
    ...options,
    body: input,
    method: "POST"
  });
}
