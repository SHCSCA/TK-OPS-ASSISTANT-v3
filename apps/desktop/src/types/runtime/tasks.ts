export type RuntimeTaskScope = "system" | "account";

export type TaskAcceptedDto = {
  taskId: string;
  scope: RuntimeTaskScope;
  accountId: string | null;
  taskType: string;
  status: "queued";
  cancellable: boolean;
  createdAt: string;
};

export type RuntimeTaskStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "failed"
  | "completed";

export type RuntimeTaskDto = {
  taskId: string;
  scope: RuntimeTaskScope;
  accountId: string | null;
  taskType: string;
  status: RuntimeTaskStatus;
  cancellable: boolean;
  createdAt: string;
  completionKind: "succeeded" | "cancelled" | null;
  failureKind: "error" | "timed_out" | "restart_interrupted" | null;
  progress: number;
  resultRef: string | null;
  errorCode: string | null;
  logId: string | null;
  revision: number;
};

export type RuntimeTaskListDto = {
  items: RuntimeTaskDto[];
};
