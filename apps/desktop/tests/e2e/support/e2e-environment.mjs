import { spawn, spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import {
  access,
  mkdtemp,
  rm,
  writeFile
} from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";

import {
  assertSafeE2eDataDirectory,
  desktopRoot,
  frontendBaseUrl,
  machineCode,
  providerBaseUrl,
  repoRoot,
  runtimeBaseUrl,
  statePath
} from "./e2e-paths.mjs";

const sessionToken = randomBytes(32).toString("hex");
const providerCredential = `e2e-${randomBytes(24).toString("hex")}`;
const dataDirectory = assertSafeE2eDataDirectory(
  await mkdtemp(path.join(os.tmpdir(), "tk-ops-e2e-"))
);
const licenseDirectory = path.join(dataDirectory, "licenses");
const publicKeyPath = path.join(licenseDirectory, "license-public.pem");
const privateKeyPath = path.join(licenseDirectory, "license-private.pem");
const startupTimeoutMs = 90_000;
const pollIntervalMs = 350;
const unexpectedExitGraceMs = 500;
const workspaceRootRegistryPath = path.join(
  dataDirectory,
  "workspace-roots.v1.json"
);

let runtimeProcess = null;
let frontendProcess = null;
let providerProcess = null;
let shuttingDown = false;

process.on("SIGINT", () => {
  void shutdown(130);
});
process.on("SIGTERM", () => {
  void shutdown(143);
});

try {
  await writeFile(
    workspaceRootRegistryPath,
    JSON.stringify({ revision: 0, roots: [], schemaVersion: 1 }, null, 2),
    { encoding: "utf8", mode: 0o600 }
  );
  const pythonCommand = await resolvePythonCommand();
  runPython(pythonCommand, [
    path.join(
      repoRoot,
      "apps",
      "py-runtime",
      "tools",
      "license-issuer",
      "generate_keypair.py"
    ),
    "--output-dir",
    licenseDirectory
  ]);
  const licenseKey = runPython(pythonCommand, [
    path.join(
      repoRoot,
      "apps",
      "py-runtime",
      "tools",
      "license-issuer",
      "issue_license.py"
    ),
    "--machine-code",
    machineCode,
    "--private-key",
    privateKeyPath,
    "--runtime-public-key",
    publicKeyPath,
    "--plain-output"
  ]).trim();

  await writeFile(
    statePath,
    JSON.stringify({
      dataDirectory,
      frontendBaseUrl,
      licenseKey,
      machineCode,
      providerBaseUrl,
      providerCredential,
      pythonCommand,
      runtimeBaseUrl,
      sessionToken,
      workspaceRootRegistryPath
    }),
    { encoding: "utf8", mode: 0o600 }
  );

  const sharedEnvironment = {
    ...process.env,
    TK_OPS_FFPROBE_PATH: path.join(
      desktopRoot,
      "tool",
      "ffmpeg",
      "bin",
      process.platform === "win32" ? "ffprobe.exe" : "ffprobe"
    ),
    TK_OPS_LICENSE_PUBLIC_KEY_PATH: publicKeyPath,
    TK_OPS_MACHINE_CODE_OVERRIDE: machineCode,
    TK_OPS_RUNTIME_ALLOWED_ORIGINS: frontendBaseUrl,
    TK_OPS_RUNTIME_DATA_DIR: dataDirectory,
    TK_OPS_RUNTIME_EXPECTED_HOST: new URL(runtimeBaseUrl).host,
    TK_OPS_RUNTIME_MODE: "development",
    TK_OPS_RUNTIME_SESSION_TOKEN: sessionToken,
    TK_OPS_WORKSPACE_ROOT_REGISTRY_PATH: workspaceRootRegistryPath,
    TK_OPS_E2E_TIKTOK_IDENTITY: "e2e_login_account",
    VITE_RUNTIME_BASE_URL: runtimeBaseUrl,
    VITE_RUNTIME_SESSION_TOKEN: sessionToken
  };

  providerProcess = spawn(
    process.execPath,
    [
      path.join(
        desktopRoot,
        "tests",
        "e2e",
        "support",
        "deterministic-provider.mjs"
      )
    ],
    {
      cwd: desktopRoot,
      env: {
        ...process.env,
        TK_OPS_E2E_PROVIDER_CREDENTIAL: providerCredential
      },
      stdio: "inherit",
      windowsHide: true
    }
  );
  attachProcess(providerProcess, "本地测试 Provider");
  await waitForReady(
    `${providerBaseUrl}/__e2e__/health`,
    {},
    "本地测试 Provider"
  );

  runtimeProcess = spawn(
    pythonCommand,
    [
      "-m",
      "uvicorn",
      "runtime-e2e-app:app",
      "--app-dir",
      path.join(desktopRoot, "tests", "e2e", "support"),
      "--host",
      "127.0.0.1",
      "--port",
      "18120"
    ],
    {
      cwd: repoRoot,
      env: sharedEnvironment,
      stdio: "inherit",
      windowsHide: true
    }
  );
  attachProcess(runtimeProcess, "Runtime");
  await waitForReady(
    `${runtimeBaseUrl}/api/v1/bootstrap/status`,
    {
      headers: {
        Authorization: `Bearer ${sessionToken}`
      }
    },
    "Runtime"
  );

  frontendProcess = spawnNpm(
    ["run", "dev", "--", "--port", "14173"],
    {
      cwd: desktopRoot,
      env: sharedEnvironment,
      stdio: "inherit",
      windowsHide: true
    }
  );
  attachProcess(frontendProcess, "Desktop 前端");
  await waitForReady(frontendBaseUrl, {}, "Desktop 前端");
  await new Promise(() => undefined);
} catch (error) {
  console.error(
    `[e2e-environment] ${
      error instanceof Error ? error.message : "启动失败"
    }`
  );
  await shutdown(1);
}

async function resolvePythonCommand() {
  const candidates = [
    process.env.TK_OPS_PYTHON,
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
    const result = spawnSync(candidate, ["--version"], {
      encoding: "utf8",
      windowsHide: true
    });
    if (result.status === 0) {
      return candidate;
    }
  }
  throw new Error("未找到已安装 Runtime 依赖的 Python 解释器。");
}

function runPython(command, args) {
  const result = spawnSync(command, args, {
    cwd: repoRoot,
    encoding: "utf8",
    windowsHide: true
  });
  if (result.status !== 0) {
    throw new Error(
      result.stderr.trim() || "准备 E2E 许可证失败。"
    );
  }
  return result.stdout;
}

function spawnNpm(args, options) {
  if (process.platform === "win32") {
    return spawn(
      process.env.ComSpec || "cmd.exe",
      ["/d", "/s", "/c", "npm", ...args],
      options
    );
  }
  return spawn("npm", args, options);
}

function attachProcess(child, label) {
  child.once("error", (error) => {
    console.error(`[e2e-environment] ${label}启动失败：${error.message}`);
    void shutdown(1);
  });
  child.once("exit", (code) => {
    if (shuttingDown) return;
    // Playwright 在结束 webServer 时会直接回收进程树，子进程可能先于父进程退出。
    // 短暂延迟可避免把正常回收误报为 Runtime 崩溃，同时仍会收敛真实异常。
    setTimeout(() => {
      if (shuttingDown) return;
      console.error(
        `[e2e-environment] ${label}意外退出（code=${code ?? "null"}）。`
      );
      void shutdown(code ?? 1);
    }, unexpectedExitGraceMs);
  });
}

async function waitForReady(url, init, label) {
  const deadline = Date.now() + startupTimeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, init);
      if (response.ok) return;
    } catch {
      // 服务启动阶段允许短暂连接失败。
    }
    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }
  throw new Error(`${label}未在限定时间内就绪。`);
}

async function shutdown(exitCode) {
  if (shuttingDown) return;
  shuttingDown = true;
  await Promise.all([
    terminateProcessTree(frontendProcess),
    terminateProcessTree(runtimeProcess),
    terminateProcessTree(providerProcess)
  ]);
  try {
    await rm(statePath, { force: true });
    assertSafeE2eDataDirectory(dataDirectory);
    await rm(dataDirectory, { force: true, recursive: true });
  } catch (error) {
    console.error(
      `[e2e-environment] 清理临时目录失败：${
        error instanceof Error ? error.message : "未知错误"
      }`
    );
  }
  process.exit(exitCode);
}

async function terminateProcessTree(child) {
  if (!child || child.exitCode !== null) return;
  if (process.platform === "win32") {
    await new Promise((resolve) => {
      const killer = spawn(
        "taskkill",
        ["/pid", String(child.pid), "/t", "/f"],
        { stdio: "ignore", windowsHide: true }
      );
      killer.once("error", resolve);
      killer.once("exit", resolve);
    });
    return;
  }
  child.kill("SIGTERM");
}
