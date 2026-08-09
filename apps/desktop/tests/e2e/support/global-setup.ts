import { access, readFile } from "node:fs/promises";

import {
  assertSafeE2eDataDirectory,
  statePath
} from "./e2e-paths.mjs";

type RuntimeState = {
  dataDirectory: string;
  runtimeBaseUrl: string;
  sessionToken: string;
};

export default async function globalSetup(): Promise<void> {
  const state = JSON.parse(
    await readFile(statePath, "utf8")
  ) as RuntimeState;
  const dataDirectory = assertSafeE2eDataDirectory(
    state.dataDirectory
  );
  await access(dataDirectory);

  const response = await fetch(
    `${state.runtimeBaseUrl}/api/v1/bootstrap/status`,
    {
      headers: {
        Authorization: `Bearer ${state.sessionToken}`
      }
    }
  );
  if (!response.ok) {
    throw new Error(
      `E2E Runtime 启动检查失败（HTTP ${response.status}）。`
    );
  }
  const payload = await response.json() as {
    ok?: boolean;
    data?: { license?: { status?: string } };
  };
  if (
    payload.ok !== true
    || payload.data?.license?.status !== "missing"
  ) {
    throw new Error("E2E Runtime 未从全新未授权状态启动。");
  }
}
