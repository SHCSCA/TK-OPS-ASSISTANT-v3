export type ExecutionEnvironmentStatus =
  | "provisioning"
  | "active"
  | "inactive"
  | "failed"
  | "deleting"
  | "cleanup_failed";

export type ExecutionEnvironmentCreateInput = {
  name: string;
  rootRef: string;
  browser: {
    kind: "chrome" | "edge";
    selection: "auto";
  };
  activateWhenReady: boolean;
};

export type ExecutionEnvironmentAcceptedDto = {
  environmentId: string;
  taskId: string;
};

export type ExecutionEnvironmentRetryAcceptedDto = ExecutionEnvironmentAcceptedDto & {
  retryOfTaskId: string;
};

export type ExecutionEnvironmentRecoveryAction =
  | "retry_provision"
  | "check"
  | "reauthorize_root"
  | "view_log"
  | "delete_preserving_files";

export type ExecutionEnvironmentDto = {
  id: string;
  accountId: string;
  name: string;
  status: ExecutionEnvironmentStatus;
  workspace: {
    id: string;
    rootRef: string;
    displayName: string;
    status: string;
    ownershipState: string;
  };
  browser: {
    id: string;
    kind: "chrome" | "edge";
    displayName: string;
    status: string;
    ownershipVerified: boolean;
    lastCheckedAt: string | null;
  };
  eligibility: {
    eligible: boolean;
    blockingIssues: Array<{
      code: string;
      message: string;
      recoveryAction: string;
    }>;
    checkedAt: string;
    evidenceRevision: number;
  };
  revision: number;
  errorCode: string | null;
  errorLogId: string | null;
  errorMessage: string | null;
  lastTaskId: string | null;
  lastRetryOfTaskId: string | null;
  recoveryActions: ExecutionEnvironmentRecoveryAction[];
};

export type ExecutionEnvironmentListDto = {
  items: ExecutionEnvironmentDto[];
};
