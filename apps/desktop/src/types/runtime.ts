export type RuntimeHealthSnapshot = {
  service: string;
  version: string;
  now: string;
  mode: string;
};

export type RuntimeEnvelope =
  | {
      ok: true;
      data: RuntimeHealthSnapshot;
    }
  | {
      ok: false;
      error: string;
    };
