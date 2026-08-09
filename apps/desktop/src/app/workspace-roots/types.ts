export type AccountWorkspaceRoot = {
  displayName: string;
  displayPath: string;
  revision: number;
  rootRef: string;
  status: "active" | "revoked";
};

export class WorkspaceRootBridgeError extends Error {
  readonly errorCode: string;
  readonly logId: string | null;

  constructor(
    message: string,
    options: { errorCode: string; logId?: string | null; cause?: unknown }
  ) {
    super(message, { cause: options.cause });
    this.name = "WorkspaceRootBridgeError";
    this.errorCode = options.errorCode;
    this.logId = options.logId ?? null;
  }
}
