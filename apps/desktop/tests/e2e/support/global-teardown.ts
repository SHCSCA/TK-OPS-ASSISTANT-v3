import {
  access,
  readFile,
  writeFile
} from "node:fs/promises";
import path from "node:path";

import {
  assertSafeE2eDataDirectory,
  shutdownRequestName,
  statePath
} from "./e2e-paths.mjs";

const cleanupTimeoutMs = 15_000;
const pollIntervalMs = 100;

type RuntimeState = {
  dataDirectory: string;
};

export default async function globalTeardown(): Promise<void> {
  if (!await pathExists(statePath)) return;
  const state = JSON.parse(
    await readFile(statePath, "utf8")
  ) as RuntimeState;
  const dataDirectory = assertSafeE2eDataDirectory(
    state.dataDirectory
  );
  await access(dataDirectory);
  await writeFile(
    path.join(dataDirectory, shutdownRequestName),
    "shutdown\n",
    { encoding: "utf8", mode: 0o600 }
  );

  const deadline = Date.now() + cleanupTimeoutMs;
  while (Date.now() < deadline) {
    const [stateExists, dataExists] = await Promise.all([
      pathExists(statePath),
      pathExists(dataDirectory)
    ]);
    if (!stateExists && !dataExists) return;
    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }
  throw new Error("E2E 环境未在限定时间内完成进程与临时数据清理。");
}

async function pathExists(target: string): Promise<boolean> {
  try {
    await access(target);
    return true;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return false;
    throw error;
  }
}
