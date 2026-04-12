import { spawn } from "node:child_process";
import { access } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");

let runtimeProcess = null;
let shuttingDown = false;

function info(message) {
  console.log(`[runtime:dev] ${message}`);
}

function error(message) {
  console.error(`[runtime:dev] ${message}`);
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

function shutdown(exitCode) {
  if (shuttingDown) {
    return;
  }

  shuttingDown = true;
  if (runtimeProcess && runtimeProcess.exitCode === null) {
    if (process.platform === "win32") {
      const killer = spawn("taskkill", ["/pid", String(runtimeProcess.pid), "/t", "/f"], {
        cwd: rootDir,
        stdio: "ignore",
        windowsHide: true,
      });
      killer.once("exit", () => process.exit(exitCode));
      killer.once("error", () => process.exit(exitCode));
      return;
    }

    runtimeProcess.kill("SIGTERM");
  }

  process.exit(exitCode);
}

async function run() {
  const pythonCommand = await resolvePythonCommand();
  info(`使用 Python 解释器：${pythonCommand}`);
  await ensureSuccess(
    pythonCommand,
    ["-c", "import fastapi, uvicorn"],
    "Python Runtime 依赖缺失，请在 venv 中安装 `./apps/py-runtime[dev]`。",
  );

  runtimeProcess = spawn(
    pythonCommand,
    ["-m", "uvicorn", "main:app", "--app-dir", "apps/py-runtime/src", "--host", "127.0.0.1", "--port", "8000", "--reload"],
    {
      cwd: rootDir,
      stdio: "inherit",
      windowsHide: false,
    },
  );

  runtimeProcess.once("error", (childError) => {
    error(`Runtime 启动失败：${childError.message}`);
    shutdown(1);
  });

  runtimeProcess.once("exit", (code) => {
    if (!shuttingDown) {
      process.exit(code ?? 0);
    }
  });
}

process.on("SIGINT", () => shutdown(130));
process.on("SIGTERM", () => shutdown(143));

run().catch((runError) => {
  error(runError.message);
  shutdown(1);
});
