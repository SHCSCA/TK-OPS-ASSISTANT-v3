export type ControlledFileFilters = {
  extensions?: string[];
  maxBytes?: number;
};

export type AccountControlledFile = {
  displayName: string;
  fileRef: string;
  kind: "document" | "image" | "video" | "audio" | "text";
  revision: number;
  rootRef: string;
  size: number;
  status: "active" | "revoked";
};

export class ControlledFileBridgeError extends Error {
  readonly errorCode: string;
  readonly logId: string | null;

  constructor(
    message: string,
    options: { errorCode: string; logId?: string | null; cause?: unknown }
  ) {
    super(message, { cause: options.cause });
    this.name = "ControlledFileBridgeError";
    this.errorCode = options.errorCode;
    this.logId = options.logId ?? null;
  }
}
