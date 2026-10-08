import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));

export const desktopRoot = path.resolve(currentDirectory, "../../..");
export const repoRoot = path.resolve(desktopRoot, "../..");
export const statePath = path.join(
  desktopRoot,
  "tests",
  "e2e",
  ".runtime-state.json"
);
export const shutdownRequestName = "shutdown.request";
export const runtimeBaseUrl = "http://127.0.0.1:18120";
export const frontendBaseUrl = "http://127.0.0.1:14173";
export const providerBaseUrl = "http://127.0.0.1:18121";
export const machineCode = "TKOPS-E2E00-E2E00-E2E00-E2E00-E2E00";

export function assertSafeE2eDataDirectory(dataDirectory) {
  const resolved = path.resolve(dataDirectory);
  const temporaryRoot = path.resolve(os.tmpdir());
  const relative = path.relative(temporaryRoot, resolved);
  if (
    !relative
    || relative.startsWith("..")
    || path.isAbsolute(relative)
    || !path.basename(resolved).startsWith("tk-ops-e2e-")
  ) {
    throw new Error("E2E 临时目录超出受控范围。");
  }
  return resolved;
}
