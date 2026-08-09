import type {
  RuntimeErrorShape,
  RuntimeFieldError,
  RuntimeMeta
} from "@/types/runtime/common";

export class RuntimeError extends Error {
  readonly aborted: boolean;
  readonly errorCode: string;
  readonly fieldErrors: RuntimeFieldError[];
  readonly logId: string | null;
  readonly meta: RuntimeMeta | null;
  readonly operationId: string | null;
  readonly path: string | null;
  readonly requestId: string | null;
  readonly status: number;

  constructor(message: string, shape: RuntimeErrorShape) {
    super(message);
    this.name = "RuntimeError";
    this.aborted = shape.aborted ?? false;
    this.errorCode = shape.errorCode;
    this.fieldErrors = shape.fieldErrors ? [...shape.fieldErrors] : [];
    this.logId = shape.logId ?? null;
    this.meta = shape.meta ?? null;
    this.operationId = shape.operationId ?? null;
    this.path = shape.path ?? null;
    this.requestId = shape.requestId ?? null;
    this.status = shape.status;
    if (shape.cause !== undefined) {
      Object.defineProperty(this, "cause", {
        configurable: true,
        value: shape.cause
      });
    }
  }
}
