import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import {
  copyFile,
  mkdir,
  readFile,
  rm,
  stat,
  writeFile
} from "node:fs/promises";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

import { computeRuntimeSourceSha256 } from "./runtime-sidecar-source.mjs";

const scriptRoot = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(scriptRoot, "..");
const runtimeRoot = join(repoRoot, "apps", "py-runtime");
const desktopRoot = join(repoRoot, "apps", "desktop");
const buildRoot = join(runtimeRoot, ".sidecar-build");
const distRoot = join(buildRoot, "dist");
const workRoot = join(buildRoot, "work");
const specPath = join(
  runtimeRoot,
  "packaging",
  "tk_ops_runtime.spec"
);
const builtBinary = join(distRoot, "tk-ops-runtime.exe");
const targetTriple = "x86_64-pc-windows-msvc";
const targetBinary = join(
  desktopRoot,
  "src-tauri",
  "binaries",
  `tk-ops-runtime-${targetTriple}.exe`
);
const manifestPath = join(
  desktopRoot,
  "src-tauri",
  "resources",
  "runtime",
  "tk-ops-runtime.manifest.json"
);
const manifestContract = {
  apiVersion: "v1",
  formatVersion: 1,
  lifecycleProtocol: 1,
  schemaReadMax: "0022_p0g_production_hardening",
  schemaReadMin: "0017_p0_enforce_and_cutover"
};
const manifestKeys = [
  "apiVersion",
  "binary",
  "buildId",
  "formatVersion",
  "generatedAt",
  "lifecycleProtocol",
  "schemaReadMax",
  "schemaReadMin",
  "sha256",
  "sourceSha256",
  "target",
  "version"
].sort();

async function main() {
  assertWindowsX64();
  assertWithin(runtimeRoot, buildRoot);
  assertWithin(desktopRoot, targetBinary);
  assertWithin(desktopRoot, manifestPath);

  const version = await readRootVersion();
  const sourceSha256 = await computeRuntimeSourceSha256(runtimeRoot);
  if (await hasValidPreparedSidecar(version, sourceSha256)) {
    console.log(
      `[runtime-sidecar] 已复用 ${relative(repoRoot, targetBinary)}`
    );
    return;
  }
  const python = await resolvePython();

  await rm(buildRoot, { force: true, recursive: true });
  await mkdir(distRoot, { recursive: true });
  await mkdir(workRoot, { recursive: true });

  await run(
    python,
    [
      "-m",
      "PyInstaller",
      "--noconfirm",
      "--clean",
      "--distpath",
      distRoot,
      "--workpath",
      workRoot,
      specPath
    ],
    runtimeRoot
  );

  await requireFile(builtBinary, "Runtime sidecar 构建产物缺失");
  const reportedVersion = (
    await runCapture(builtBinary, ["--version"], runtimeRoot)
  ).trim();
  if (reportedVersion !== version) {
    throw new Error(
      `Runtime sidecar 版本不一致：期望 ${version}，实际 ${reportedVersion}`
    );
  }

  await mkdir(dirname(targetBinary), { recursive: true });
  const builtHash = await sha256(builtBinary);
  await copyFile(builtBinary, targetBinary);
  const hash = await sha256(targetBinary);
  if (hash !== builtHash) {
    throw new Error("Runtime sidecar 复制后的 SHA-256 校验失败");
  }
  const sourceSha256AfterBuild =
    await computeRuntimeSourceSha256(runtimeRoot);
  if (sourceSha256AfterBuild !== sourceSha256) {
    throw new Error("Runtime 构建期间输入发生变化，请重新执行构建");
  }
  const manifest = {
    binary: "tk-ops-runtime.exe",
    buildId: `${version}-${targetTriple}-${hash.slice(0, 12).toLowerCase()}`,
    generatedAt: new Date().toISOString(),
    sha256: hash,
    sourceSha256,
    target: targetTriple,
    version,
    ...manifestContract
  };
  await mkdir(dirname(manifestPath), { recursive: true });
  await writeFile(
    manifestPath,
    `${JSON.stringify(manifest, null, 2)}\n`,
    "utf8"
  );
  await rm(buildRoot, { force: true, recursive: true });

  console.log(
    `[runtime-sidecar] 已准备 ${relative(repoRoot, targetBinary)}`
  );
  console.log(`[runtime-sidecar] SHA-256 ${hash}`);
}

async function hasValidPreparedSidecar(version, sourceSha256) {
  if (
    !await isFile(targetBinary)
    || !await isFile(manifestPath)
  ) {
    return false;
  }
  try {
    const manifest = JSON.parse(
      await readFile(manifestPath, "utf8")
    );
    const hash = await sha256(targetBinary);
    const reportedVersion = (
      await runCapture(targetBinary, ["--version"], runtimeRoot)
    ).trim();
    const expectedBuildId =
      `${version}-${targetTriple}-${hash.slice(0, 12).toLowerCase()}`;
    return (
      hasExactManifestKeys(manifest)
      && manifest.binary === "tk-ops-runtime.exe"
      && manifest.buildId === expectedBuildId
      && isManifestTimestamp(manifest.generatedAt)
      && manifest.version === version
      && manifest.target === targetTriple
      && manifest.sha256 === hash
      && manifest.sourceSha256 === sourceSha256
      && manifest.apiVersion === manifestContract.apiVersion
      && manifest.formatVersion === manifestContract.formatVersion
      && manifest.lifecycleProtocol === manifestContract.lifecycleProtocol
      && manifest.schemaReadMin === manifestContract.schemaReadMin
      && manifest.schemaReadMax === manifestContract.schemaReadMax
      && reportedVersion === version
    );
  } catch {
    return false;
  }
}

function hasExactManifestKeys(manifest) {
  return (
    manifest
    && typeof manifest === "object"
    && !Array.isArray(manifest)
    && Object.keys(manifest).sort().join("\n") === manifestKeys.join("\n")
  );
}

function isManifestTimestamp(value) {
  return (
    typeof value === "string"
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(value)
  );
}

function assertWindowsX64() {
  if (process.platform !== "win32" || process.arch !== "x64") {
    throw new Error("P0 Runtime sidecar 当前只支持 Windows x64 构建");
  }
}

function assertWithin(parent, target) {
  const normalized = relative(resolve(parent), resolve(target));
  if (
    normalized === ""
    || normalized.startsWith("..")
    || isAbsolute(normalized)
  ) {
    throw new Error(`构建目标超出受控目录：${target}`);
  }
}

async function readRootVersion() {
  const content = await readFile(join(repoRoot, "package.json"), "utf8");
  const value = JSON.parse(content).version;
  if (typeof value !== "string" || !value.trim()) {
    throw new Error("根 package.json 缺少有效版本");
  }
  return value.trim();
}

async function resolvePython() {
  const configured = process.env.TK_OPS_PYTHON?.trim();
  const candidates = [
    configured,
    join(repoRoot, "venv", "Scripts", "python.exe"),
    "python"
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (
      candidate !== "python"
      && !await isFile(candidate)
    ) {
      continue;
    }
    try {
      await runCapture(
        candidate,
        ["-c", "import PyInstaller"],
        runtimeRoot
      );
      return candidate;
    } catch {
      continue;
    }
  }
  throw new Error(
    "未找到安装 PyInstaller 的 Python。请先安装 py-runtime 的 packaging 依赖。"
  );
}

async function requireFile(path, message) {
  if (!await isFile(path)) {
    throw new Error(message);
  }
}

async function isFile(path) {
  try {
    return (await stat(path)).isFile();
  } catch {
    return false;
  }
}

function run(command, args, cwd) {
  return new Promise((resolveRun, rejectRun) => {
    const child = spawn(command, args, {
      cwd,
      stdio: "inherit",
      windowsHide: true
    });
    child.once("error", rejectRun);
    child.once("exit", (code) => {
      if (code === 0) {
        resolveRun();
      } else {
        rejectRun(
          new Error(`命令执行失败：${command}，退出码 ${String(code)}`)
        );
      }
    });
  });
}

function runCapture(command, args, cwd) {
  return new Promise((resolveRun, rejectRun) => {
    const child = spawn(command, args, {
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.once("error", rejectRun);
    child.once("exit", (code) => {
      if (code === 0) {
        resolveRun(stdout);
      } else {
        rejectRun(
          new Error(
            `命令执行失败：${command}，退出码 ${String(code)}，${stderr.trim()}`
          )
        );
      }
    });
  });
}

async function sha256(path) {
  const content = await readFile(path);
  return createHash("sha256").update(content).digest("hex").toUpperCase();
}

main().catch((error) => {
  console.error(
    `[runtime-sidecar] ${error instanceof Error ? error.message : String(error)}`
  );
  process.exit(1);
});
