import { readFileSync } from "node:fs";

import { statePath } from "./e2e-paths.mjs";

export type E2eRuntimeState = {
  dataDirectory: string;
  frontendBaseUrl: string;
  licenseKey: string;
  machineCode: string;
  providerBaseUrl: string;
  providerCredential: string;
  pythonCommand: string;
  runtimeBaseUrl: string;
  sessionToken: string;
  workspaceRootRegistryPath: string;
};

export function readE2eRuntimeState(): E2eRuntimeState {
  return JSON.parse(
    readFileSync(statePath, "utf8")
  ) as E2eRuntimeState;
}
