import { spawn } from "node:child_process";
import path from "node:path";

import { desktopRoot } from "./e2e-paths.mjs";
import { readE2eRuntimeState } from "./runtime-state";

export type ExecutionFixture = {
  bindingId: string;
  browserInstanceId: string;
  deviceWorkspaceId: string;
};

export async function seedExecutionBinding(
  accountId: string,
  fixtureKey: string
): Promise<ExecutionFixture> {
  const state = readE2eRuntimeState();
  const scriptPath = path.resolve(
    desktopRoot,
    "tests",
    "e2e",
    "support",
    "seed-execution-binding.py"
  );
  const output = await runFixture(state.pythonCommand, [
    scriptPath,
    "--data-dir",
    state.dataDirectory,
    "--account-id",
    accountId,
    "--fixture-key",
    fixtureKey
  ]);
  return JSON.parse(output) as ExecutionFixture;
}

function runFixture(command: string, args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    let stdout = "";
    let stderr = "";
    const child = spawn(command, args, {
      cwd: desktopRoot,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true
    });
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk: string) => {
      stderr += chunk;
    });
    child.once("error", (error) => {
      reject(new Error(`E2E 执行绑定夹具启动失败：${error.message}`));
    });
    child.once("exit", (code) => {
      if (code !== 0) {
        reject(
          new Error(
            `E2E 执行绑定夹具失败（code=${code ?? "null"}）：`
            + `${stderr.trim() || "无错误输出"}`
          )
        );
        return;
      }
      resolve(stdout.trim());
    });
  });
}
