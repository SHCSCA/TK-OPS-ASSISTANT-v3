export type RuntimeHealthSnapshot = {
  service: string;
  version: string;
  now: string;
  mode: string;
};

export type AppSettings = {
  revision: number;
  runtime: {
    mode: string;
    workspaceRoot: string;
  };
  paths: {
    cacheDir: string;
    exportDir: string;
    logDir: string;
  };
  logging: {
    level: string;
  };
  ai: {
    provider: string;
    model: string;
    voice: string;
    subtitleMode: string;
  };
};

export type AppSettingsUpdateInput = Omit<AppSettings, "revision">;

export type RuntimeDiagnostics = {
  databasePath: string;
  logDir: string;
  revision: number;
  mode: string;
  healthStatus: string;
};

export type RuntimeSuccessEnvelope<T> = {
  ok: true;
  data: T;
};

export type RuntimeErrorEnvelope = {
  ok: false;
  error: string;
  requestId?: string;
  details?: unknown;
};

export type RuntimeEnvelope<T> = RuntimeSuccessEnvelope<T> | RuntimeErrorEnvelope;

export type RuntimeRequestErrorShape = {
  message: string;
  requestId: string;
  status: number;
  details?: unknown;
};
