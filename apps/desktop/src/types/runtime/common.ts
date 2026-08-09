export type RuntimeFieldError = {
  field: string;
  code: string;
  message: string;
};

export type RuntimeMeta = {
  revision?: number;
  invalidations?: string[];
  nextCursor?: string | null;
  idempotentReplay?: boolean;
  currentRevision?: number;
  taskId?: string;
  [key: string]: unknown;
};

export type RuntimeSuccessEnvelope<T> = {
  ok: true;
  data: T;
  meta?: RuntimeMeta;
};

export type RuntimeErrorEnvelope = {
  ok: false;
  error: string;
  error_code: string;
  log_id?: string;
  fieldErrors?: RuntimeFieldError[];
  meta?: RuntimeMeta;
};

export type RuntimeEnvelope<T> = RuntimeSuccessEnvelope<T> | RuntimeErrorEnvelope;

export type RuntimeClientResult<T> = {
  data: T;
  meta: RuntimeMeta | null;
  requestId: string | null;
  operationId: string | null;
  status: number;
};

export type RuntimeErrorShape = {
  errorCode: string;
  status: number;
  logId?: string | null;
  requestId?: string | null;
  operationId?: string | null;
  fieldErrors?: RuntimeFieldError[];
  meta?: RuntimeMeta | null;
  path?: string | null;
  aborted?: boolean;
  cause?: unknown;
};
