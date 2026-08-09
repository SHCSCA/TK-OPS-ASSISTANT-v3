export type LicenseState =
  | "missing"
  | "active"
  | "expired"
  | "invalid"
  | "machine_mismatch";

export type LicenseBlockingIssueDto = {
  code: string;
  message: string;
};

export type LicenseStatusDto = {
  status: LicenseState;
  machineCode: string;
  machineCodeMasked: string;
  expiresAt: string | null;
  activatedAt: string | null;
  blockingIssue: LicenseBlockingIssueDto | null;
  revision: number;
  machineIdentityStatus: "verified" | "degraded" | "unavailable" | "mismatch";
  machineIdentityAlgorithm: string;
  matchedFactorCount: number;
  mismatchedFactorCount: number;
  unavailableFactorCount: number;
};

export type DirectoryAggregateState = "ready" | "attention" | "failed";
export type DirectoryItemState = "ready" | "created" | "failed";

export type DirectoryItemDto = {
  key: string;
  status: DirectoryItemState;
  writable: boolean;
};

export type DirectoryIssueDto = {
  code: string;
  message: string;
  logId: string | null;
};

export type DirectoryReportDto = {
  status: DirectoryAggregateState;
  workspaceRootDisplay: string;
  directories: DirectoryItemDto[];
  issues: DirectoryIssueDto[];
  revision: number;
};

export type RuntimeStatusDto = {
  status: "starting" | "ready" | "failed";
  version: string;
};

export type MediaToolsStatusDto = {
  status: "ready" | "attention" | "failed";
  issues: string[];
};

export type BootstrapBlockingIssueDto = {
  code: string;
  message: string;
  logId: string | null;
};

export type BootstrapStatusDto = {
  license: LicenseStatusDto;
  directories: DirectoryReportDto;
  runtime: RuntimeStatusDto;
  mediaTools: MediaToolsStatusDto;
  canContinue: boolean;
  blockingIssues: BootstrapBlockingIssueDto[];
  revision: number;
};

export type LicenseActivationInput = {
  licenseKey: string;
};

export type DirectoryInitializationInput = {
  workspaceRootRef: string | null;
};

export type SelfCheckKey = "database" | "directories" | "media_tools" | "runtime";

export type SelfCheckInput = {
  checks: SelfCheckKey[];
};
