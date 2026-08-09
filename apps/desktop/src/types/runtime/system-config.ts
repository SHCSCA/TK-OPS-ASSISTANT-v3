export type SystemConfigDto = {
  values: Record<string, unknown>;
  writableKeys: string[];
  restartRequiredKeys: string[];
  revision: number;
};

export type SystemConfigPatchInput = {
  values: Record<string, unknown>;
};
