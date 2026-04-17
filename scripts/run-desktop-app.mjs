import { spawn } from "node:child_process";
import { access } from "node:fs/promises";
import net from "node:net";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const runtimeUrl = "http://127.0.0.1:8000/api/settings/health";
const desktopDevUrl = "http://127.0.0.1:1420";
const runtimeStartupTimeoutMs = 30_000;
const runtimePollIntervalMs = 500;
const smokeExitAfterReady = process.env.TK_OPS_APP_DEV_EXIT_AFTER_READY === "1";
const nodeCommand = process.execPath;

let runtimeProcess = null;
let tauriProcess = null;
let shuttingDown = false;
let runtimeReady = false;
let reuseRuntime = false;
let reuseFrontendDevServer = false;

function info(message) {
  console.log(`[app:dev] ${message}`);
}

function error(message) {
  console.error(`[app:dev] ${message}`);
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function ensureSuccess(command, args, failureMessage) {
  return new Promise((resolve, reject) => {
    let child;
    try {
      child = spawn(command, args, {
        cwd: rootDir,
        stdio: "ignore",
        windowsHide: true,
      });
    } catch {
      reject(new Error(failureMessage));
      return;
    }

    child.once("error", () => {
      reject(new Error(failureMessage));
    });

    child.once("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }

      reject(new Error(failureMessage));
    });
  });
}

async function canRun(command, args) {
  try {
    await ensureSuccess(command, args, "");
    return true;
  } catch {
    return false;
  }
}

async function resolvePythonCommand() {
  const candidates =
    process.platform === "win32"
      ? [path.join(rootDir, "venv", "Scripts", "python.exe"), "python"]
      : [path.join(rootDir, "venv", "bin", "python3"), path.join(rootDir, "venv", "bin", "python"), "python3", "python"];

  for (const candidate of candidates) {
    const isAbsolutePath = candidate.includes(path.sep);
    if (isAbsolutePath) {
      try {
        await access(candidate);
      } catch {
        continue;
      }
    }

    if (await canRun(candidate, ["--version"])) {
      return candidate;
    }
  }

  throw new Error(
    "未找到可用 Python 解释器。请先执行 `python -m venv venv`，并安装依赖：`venv\\Scripts\\python.exe -m pip install -e \"./apps/py-runtime[dev]\"`。",
  );
}

function resolveNpmInvocation(args) {
  if (process.platform === "win32") {
    return {
      command: process.env.ComSpec || "cmd.exe",
      args: ["/d", "/s", "/c", "npm", ...args],
    };
  }

  return {
    command: "npm",
    args,
  };
}

function ensureNpmSuccess(args, failureMessage) {
  const invocation = resolveNpmInvocation(args);
  return ensureSuccess(invocation.command, invocation.args, failureMessage);
}

function spawnNpm(args, options) {
  const invocation = resolveNpmInvocation(args);
  return spawn(invocation.command, invocation.args, options);
}

function ensurePathExists(relativePath, failureMessage) {
  return access(path.join(rootDir, relativePath)).catch(() => {
    throw new Error(failureMessage);
  });
}

function ensurePortAvailable(port, label) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();

    server.once("error", (portError) => {
      if (portError.code === "EADDRINUSE") {
        reject(new Error(`${label} 端口 ${port} 已被占用，请先释放端口后再启动。`));
        return;
      }

      reject(new Error(`无法检查 ${label} 端口 ${port}：${portError.message}`));
    });

    server.listen(port, "127.0.0.1", () => {
      server.close((closeError) => {
        if (closeError) {
          reject(new Error(`无法完成 ${label} 端口 ${port} 检查：${closeError.message}`));
          return;
        }

        resolve();
      });
    });
  });
}

function isPortAvailable(port) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();

    server.once("error", (portError) => {
      if (portError.code === "EADDRINUSE") {
        resolve(false);
        return;
      }

      reject(new Error(`无法检查端口 ${port}：${portError.message}`));
    });

    server.listen(port, "127.0.0.1", () => {
      server.close((closeError) => {
        if (closeError) {
          reject(new Error(`无法完成端口 ${port} 检查：${closeError.message}`));
          return;
        }

        resolve(true);
      });
    });
  });
}

async function waitForRuntimeReady() {
  const startedAt = Date.now();

  while (Date.now() - startedAt < runtimeStartupTimeoutMs) {
    if (runtimeProcess?.exitCode !== null && runtimeProcess?.exitCode !== undefined) {
      throw new Error(
        "Runtime 在健康检查通过前已退出，请确认 venv 已安装依赖：`venv\\Scripts\\python.exe -m pip install -e \"./apps/py-runtime[dev]\"`。",
      );
    }

    try {
      const response = await fetch(runtimeUrl);
      if (response.ok) {
        runtimeReady = true;
        return;
      }
    } catch {}

    await sleep(runtimePollIntervalMs);
  }

  throw new Error("Runtime 健康检查在 30 秒内未就绪，请确认 8000 端口未被占用，且 Runtime 依赖已安装。");
}

async function isUrlReady(url) {
  try {
    const response = await fetch(url);
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForUrlReady(url, timeoutMs, failureMessage) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    if (tauriProcess?.exitCode !== null && tauriProcess?.exitCode !== undefined) {
      throw new Error("Tauri 桌面应用在开发服务器启动前已退出。");
    }

    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch {}

    await sleep(runtimePollIntervalMs);
  }

  throw new Error(failureMessage);
}

function waitForChildExit(child) {
  return new Promise((resolve) => {
    if (!child || child.exitCode !== null) {
      resolve();
      return;
    }

    child.once("exit", () => resolve());
  });
}

function killProcessTree(child) {
  if (!child || child.exitCode !== null) {
    return Promise.resolve();
  }

  if (process.platform === "win32") {
    return new Promise((resolve) => {
      const killer = spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], {
        cwd: rootDir,
        stdio: "ignore",
        windowsHide: true,
      });

      killer.once("error", () => resolve());
      killer.once("exit", () => resolve());
    });
  }

  child.kill("SIGTERM");
  return Promise.race([waitForChildExit(child), sleep(5_000)]).then(() => undefined);
}

async function shutdown(exitCode) {
  if (shuttingDown) {
    return;
  }

  shuttingDown = true;
  await Promise.all([killProcessTree(tauriProcess), killProcessTree(runtimeProcess)]);
  process.exit(exitCode);
}

function attachCommonChildHandlers(child, label) {
  child.once("error", (childError) => {
    error(`${label} 启动失败：${childError.message}`);
    void shutdown(1);
  });
}

async function run() {
  info("正在检查启动前置条件。");
  const pythonCommand = await resolvePythonCommand();
  info(`使用 Python 解释器：${pythonCommand}`);

  await ensureSuccess(nodeCommand, ["--version"], "未找到 node，请先安装 Node.js 并确认 `node` 在 PATH 中。");
  await ensureNpmSuccess(["--version"], "未找到 npm，请先安装 Node.js 并确认 `npm` 在 PATH 中。");
  await ensureSuccess(pythonCommand, ["-c", "import fastapi, uvicorn"], "Python Runtime 依赖缺失，请在 venv 中安装 `./apps/py-runtime[dev]`。");
  await ensureSuccess("cargo", ["--version"], "未找到 cargo，请先安装 Rust 工具链并确认 `cargo` 在 PATH 中。");
  await ensurePathExists(path.join("apps", "desktop", "node_modules"), "未找到 apps/desktop/node_modules，请先执行 `npm --prefix apps/desktop install`。");
  await ensureNpmSuccess(["--prefix", "apps/desktop", "run", "tauri", "--", "--version"], "Tauri CLI 不可用，请先执行 `npm --prefix apps/desktop install` 安装桌面端依赖。");

  const runtimePortFree = await isPortAvailable(8000);
  if (runtimePortFree) {
    await ensurePortAvailable(8000, "Runtime");
  } else if (await isUrlReady(runtimeUrl)) {
    reuseRuntime = true;
    runtimeReady = true;
    info("检测到已运行 Runtime，复用现有 8000 服务。");
  } else {
    throw new Error("Runtime 端口 8000 已被占用，且健康检查不可用。请释放端口后重试。");
  }

  const frontendPortFree = await isPortAvailable(1420);
  if (frontendPortFree) {
    await ensurePortAvailable(1420, "桌面开发服务器");
  } else if (await isUrlReady(desktopDevUrl)) {
    reuseFrontendDevServer = true;
    info("检测到已运行前端开发服务器，复用现有 1420 服务。");
  } else {
    throw new Error("桌面开发服务器端口 1420 已被占用，且页面不可访问。请释放端口后重试。");
  }

  if (!reuseRuntime) {
    info("正在启动 Python Runtime。");
    runtimeProcess = spawn(
      pythonCommand,
      ["-m", "uvicorn", "main:app", "--app-dir", "apps/py-runtime/src", "--host", "127.0.0.1", "--port", "8000", "--reload"],
      {
        cwd: rootDir,
        stdio: "inherit",
        windowsHide: false,
      },
    );
    attachCommonChildHandlers(runtimeProcess, "Python Runtime");

    runtimeProcess.once("exit", (code, signal) => {
      if (shuttingDown) {
        return;
      }

      if (!runtimeReady) {
        error(`Python Runtime 在健康检查通过前退出（code=${code ?? "null"}, signal=${signal ?? "null"}）。`);
      } else {
        error(`Python Runtime 意外退出（code=${code ?? "null"}, signal=${signal ?? "null"}）。`);
      }

      void shutdown(1);
    });

    info("正在等待 Runtime 健康检查通过。");
    await waitForRuntimeReady();
  }

  info("Runtime 已就绪，正在启动 Tauri 桌面应用。");
  const tauriArgs = ["--prefix", "apps/desktop", "run", "tauri", "--", "dev"];
  if (reuseFrontendDevServer) {
    tauriArgs.push("-c", "{\"build\":{\"beforeDevCommand\":\"\"}}");
  }

  tauriProcess = spawnNpm(tauriArgs, {
    cwd: rootDir,
    stdio: "inherit",
    windowsHide: false,
  });
  attachCommonChildHandlers(tauriProcess, "Tauri 桌面应用");

  tauriProcess.once("exit", (code, signal) => {
    if (shuttingDown) {
      return;
    }

    if (signal) {
      info(`Tauri 桌面应用已退出（signal=${signal}），正在回收 Runtime。`);
      void shutdown(1);
      return;
    }

    info(`Tauri 桌面应用已退出（code=${code ?? 0}），正在回收 Runtime。`);
    void shutdown(code ?? 0);
  });

  if (smokeExitAfterReady) {
    await waitForUrlReady(
      desktopDevUrl,
      runtimeStartupTimeoutMs,
      "Smoke 模式等待桌面前端开发服务器超时，请确认 1420 端口未被占用，且 Vite 能正常启动。",
    );
    info("Smoke 模式已确认 Runtime 与桌面前端都已就绪，3 秒后自动关闭桌面应用和 Runtime。");
    setTimeout(() => {
      void shutdown(0);
    }, 3_000);
  }
}

process.on("SIGINT", () => {
  error("收到 SIGINT，正在关闭桌面应用和 Runtime。");
  void shutdown(130);
});

process.on("SIGTERM", () => {
  error("收到 SIGTERM，正在关闭桌面应用和 Runtime。");
  void shutdown(143);
});

run().catch((runError) => {
  error(runError.message);
  void shutdown(1);
});
