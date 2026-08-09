export type LoginSessionState =
  | "preparing"
  | "waiting_user"
  | "probing"
  | "completed"
  | "cancelled"
  | "failed"
  | "timed_out";

export type LoginSessionDto = {
  id: string;
  accountId: string;
  environmentId: string;
  state: LoginSessionState;
  expectedIdentity: string;
  detectedIdentity: string | null;
  expiresAt: string;
  prepareTaskId: string | null;
  probeTaskId: string | null;
  errorCode: string | null;
  errorLogId: string | null;
  revision: number;
};

export type LoginSessionAcceptedDto = {
  sessionId: string;
  taskId: string;
  state: LoginSessionState;
};
