import { spawn, spawnSync } from "node:child_process";
import { access, mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  ".."
);

async function main() {
  const python = await resolvePython();
  const isolatedRoot = await mkdtemp(
    path.join(os.tmpdir(), "tk-ops-runtime-tests-")
  );
  try {
    const args = [
      "-m",
      "pytest",
      "tests/runtime",
      "tests/contracts",
      "--basetemp",
      path.join(isolatedRoot, "pytest"),
      ...process.argv.slice(2)
    ];
    const exitCode = await run(python, args, {
      ...process.env,
      PYTHONPYCACHEPREFIX: path.join(isolatedRoot, "pycache"),
      TK_OPS_RUNTIME_DATA_DIR: path.join(isolatedRoot, "runtime-data")
    });
    process.exitCode = exitCode;
  } finally {
    await rm(isolatedRoot, { force: true, recursive: true });
  }
}

async function resolvePython() {
  const candidates = [
    process.env.TK_OPS_PYTHON?.trim(),
    process.platform === "win32"
      ? path.join(repoRoot, "venv", "Scripts", "python.exe")
      : path.join(repoRoot, "venv", "bin", "python"),
    process.platform === "win32" ? "python" : "python3"
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (path.isAbsolute(candidate)) {
      try {
        await access(candidate);
      } catch {
        continue;
      }
    }
    const probe = spawnSync(candidate, ["-c", "import pytest"], {
      cwd: repoRoot,
      encoding: "utf8",
      windowsHide: true
    });
    if (probe.status === 0) {
      return candidate;
    }
  }
  throw new Error("未找到已安装 Runtime 测试依赖的 Python。");
}

function run(command, args, environment) {
  return new Promise((resolveRun, rejectRun) => {
    const child = spawn(command, args, {
      cwd: repoRoot,
      env: environment,
      stdio: "inherit",
      windowsHide: true
    });
    const timeoutMs = Number.parseInt(
      process.env.TK_OPS_TEST_TIMEOUT_MS || "1800000",
      10
    );
    const timer = setTimeout(() => {
      child.kill();
      rejectRun(new Error("Runtime 全量测试超过 30 分钟，已终止。"));
    }, Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 1_800_000);
    child.once("error", (error) => {
      clearTimeout(timer);
      rejectRun(error);
    });
    child.once("exit", (code) => {
      clearTimeout(timer);
      resolveRun(code ?? 1);
    });
  });
}

main().catch((error) => {
  console.error(
    `[runtime-tests] ${error instanceof Error ? error.message : String(error)}`
  );
  process.exit(1);
});
