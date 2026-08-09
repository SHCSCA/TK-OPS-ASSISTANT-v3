import { spawn, spawnSync } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { access, mkdtemp, readFile, rm, stat, writeFile } from "node:fs/promises";
import http from "node:http";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";


const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const options = parseArgs(process.argv.slice(2));
const startedAt = new Date().toISOString();


async function main() {
  const runtimePath = resolveRepoFile(options.runtime);
  const runtimeManifestPath = resolveRepoFile(options.runtimeManifest);
  const desktopPath = resolveRepoFile(options.desktop);
  const evidencePath = resolveRepoFile(options.evidence);
  await requireFile(runtimePath, "打包 Runtime 不存在");
  await requireFile(runtimeManifestPath, "打包 Runtime manifest 不存在");
  await requireFile(desktopPath, "打包 Desktop 不存在");
  const runtimeIdentity = await readRuntimeIdentity(
    runtimePath,
    runtimeManifestPath
  );
  const temporaryRoot = await mkdtemp(path.join(os.tmpdir(), "tk-ops-license-smoke-"));
  const dataDir = path.join(temporaryRoot, "data");
  const keyDir = path.join(temporaryRoot, "keys");
  const port = await reservePort();
  const host = `127.0.0.1:${port}`;
  const token = randomBytes(32).toString("base64url");
  let child;
  let diagnostics;
  try {
    const python = await resolvePython();
    generateKeypair(python, keyDir);
    child = spawn(runtimePath, [], {
      cwd: temporaryRoot,
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8",
        PYTHONUTF8: "1",
        TK_OPS_RUNTIME_ARTIFACT_BUILD_ID: runtimeIdentity.buildId,
        TK_OPS_LICENSE_PUBLIC_KEY_PATH: path.join(keyDir, "license-public.pem"),
        TK_OPS_RUNTIME_DATA_DIR: dataDir,
        TK_OPS_RUNTIME_EXPECTED_HOST: host,
        TK_OPS_RUNTIME_MANAGED_SIDECAR: "1",
        TK_OPS_RUNTIME_MODE: "production",
        TK_OPS_RUNTIME_PORT: String(port),
        TK_OPS_RUNTIME_SESSION_TOKEN: token,
        TK_OPS_RUNTIME_VERSION: runtimeIdentity.version
      },
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true
    });
    diagnostics = collectDiagnostics(child, [token]);
    const status = await waitForLicenseStatus({
      child,
      diagnostics,
      host,
      port,
      token
    });
    const machineCode = status?.data?.machineCode;
    if (typeof machineCode !== "string" || !machineCode.startsWith("TKOPS-")) {
      throw new Error("打包 Runtime 未返回有效机器码");
    }
    const licenseKey = issueLicense(python, keyDir, machineCode);
    const activated = await requestJson({
      body: { licenseKey, machineCode },
      host,
      method: "POST",
      pathName: "/api/v1/bootstrap/license/activate",
      port,
      token,
      idempotencyKey: `packaged-license-${randomBytes(12).toString("hex")}`
    });
    if (
      activated.statusCode !== 200
      || activated.payload?.ok !== true
      || activated.payload?.data?.status !== "active"
    ) {
      throw new Error("打包 Runtime 许可证激活未进入 active 状态");
    }
    const verified = await requestJson({
      host,
      method: "GET",
      pathName: "/api/v1/bootstrap/license",
      port,
      token
    });
    if (
      verified.statusCode !== 200
      || verified.payload?.data?.status !== "active"
      || verified.payload?.data?.machineCode !== machineCode
    ) {
      throw new Error("打包 Runtime 许可证激活后复核失败");
    }
    child.stdin.write("shutdown\n");
    child.stdin.end();
    await waitForExit(child, 15_000);
    const evidence = {
      id: "packaged-license-activation",
      command: "packaged Runtime + license issuer activation smoke",
      exitCode: 0,
      tests: 1,
      startedAt,
      completedAt: new Date().toISOString(),
      artifactBindings: {
        desktop: await sha256File(desktopPath),
        runtimeManifest: await sha256File(runtimeManifestPath),
        sidecar: runtimeIdentity.sha256
      },
      result: "passed"
    };
    await writeFile(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.log("[packaged-license-smoke] 打包 Runtime 真实签发与激活通过");
  } finally {
    if (child && child.exitCode === null && child.signalCode === null) {
      child.kill();
      await waitForExit(child, 5_000).catch(() => undefined);
    }
    await rm(temporaryRoot, { recursive: true, force: true });
  }
}


async function waitForLicenseStatus({
  child,
  diagnostics,
  host,
  port,
  token
}) {
  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new Error(
        `打包 Runtime 在许可证检查前退出：${diagnostics.summary()}`
      );
    }
    try {
      const response = await requestJson({
        host,
        method: "GET",
        pathName: "/api/v1/bootstrap/license",
        port,
        token
      });
      if (response.statusCode === 200 && response.payload?.ok === true) {
        return response.payload;
      }
    } catch {
      // Runtime 启动窗口内连接失败属于可重试状态。
    }
    await delay(250);
  }
  throw new Error("等待打包 Runtime 许可证接口就绪超时");
}


function requestJson({
  body,
  host,
  idempotencyKey,
  method,
  pathName,
  port,
  token
}) {
  return new Promise((resolveRequest, rejectRequest) => {
    const serialized = body === undefined ? "" : JSON.stringify(body);
    const headers = {
      Authorization: `Bearer ${token}`,
      Host: host,
      Origin: "tauri://localhost"
    };
    if (serialized) {
      headers["Content-Type"] = "application/json";
      headers["Content-Length"] = Buffer.byteLength(serialized);
    }
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    const request = http.request(
      {
        host: "127.0.0.1",
        port,
        method,
        path: pathName,
        headers,
        timeout: 5_000
      },
      (response) => {
        const chunks = [];
        response.on("data", (chunk) => chunks.push(chunk));
        response.once("end", () => {
          try {
            resolveRequest({
              statusCode: response.statusCode,
              payload: JSON.parse(Buffer.concat(chunks).toString("utf8"))
            });
          } catch (error) {
            rejectRequest(error);
          }
        });
      }
    );
    request.once("error", rejectRequest);
    request.once("timeout", () => request.destroy(new Error("Runtime 请求超时")));
    request.end(serialized);
  });
}


function generateKeypair(python, keyDir) {
  runPython(python, [
    "apps/py-runtime/tools/license-issuer/generate_keypair.py",
    "--output-dir",
    keyDir
  ]);
}


function issueLicense(python, keyDir, machineCode) {
  return runPython(python, [
    "apps/py-runtime/tools/license-issuer/issue_license.py",
    "--machine-code",
    machineCode,
    "--private-key",
    path.join(keyDir, "license-private.pem"),
    "--runtime-public-key",
    path.join(keyDir, "license-public.pem"),
    "--plain-output"
  ]).trim();
}


function runPython(python, args) {
  const result = spawnSync(python, args, {
    cwd: repoRoot,
    encoding: "utf8",
    windowsHide: true,
    maxBuffer: 4 * 1024 * 1024
  });
  if (result.error || result.status !== 0) {
    throw new Error("许可证发行器执行失败");
  }
  return result.stdout;
}


async function resolvePython() {
  const candidates = [
    process.env.TK_OPS_PYTHON?.trim(),
    path.join(repoRoot, "venv", "Scripts", "python.exe"),
    "python"
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (path.isAbsolute(candidate)) {
      try {
        await access(candidate);
      } catch {
        continue;
      }
    }
    const probe = spawnSync(candidate, ["-c", "import cryptography"], {
      cwd: repoRoot,
      windowsHide: true
    });
    if (probe.status === 0) return candidate;
  }
  throw new Error("未找到许可证发行器所需 Python 环境");
}


function reservePort() {
  return new Promise((resolvePort, rejectPort) => {
    const server = net.createServer();
    server.once("error", rejectPort);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        server.close();
        rejectPort(new Error("无法分配 Runtime 端口"));
        return;
      }
      server.close((error) => error ? rejectPort(error) : resolvePort(address.port));
    });
  });
}


function waitForExit(child, timeoutMs) {
  if (child.exitCode !== null || child.signalCode !== null) return Promise.resolve();
  return new Promise((resolveExit, rejectExit) => {
    const timer = setTimeout(() => rejectExit(new Error("等待 Runtime 退出超时")), timeoutMs);
    child.once("close", () => {
      clearTimeout(timer);
      resolveExit();
    });
  });
}


function parseArgs(args) {
  return {
    runtime: readArg(args, "--runtime"),
    runtimeManifest: readArg(args, "--runtime-manifest"),
    desktop: readArg(args, "--desktop"),
    evidence: readArg(args, "--evidence")
  };
}


function readArg(args, key) {
  const index = args.indexOf(key);
  const value = index >= 0 ? args[index + 1] : "";
  if (!value || value.startsWith("--")) throw new Error(`${key} 缺少值`);
  return value;
}


function resolveRepoFile(relativePath) {
  const resolved = path.resolve(repoRoot, relativePath);
  if (!resolved.startsWith(`${repoRoot}${path.sep}`)) {
    throw new Error(`路径越过仓库边界：${relativePath}`);
  }
  return resolved;
}


async function requireFile(filePath, message) {
  try {
    if ((await stat(filePath)).isFile()) return;
  } catch {
    // 统一映射为稳定错误。
  }
  throw new Error(message);
}


async function sha256File(filePath) {
  return createHash("sha256")
    .update(await readFile(filePath))
    .digest("hex")
    .toUpperCase();
}


async function readRuntimeIdentity(runtimePath, manifestPath) {
  let manifest;
  try {
    manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  } catch {
    throw new Error("打包 Runtime manifest 无法解析");
  }
  const runtimeSha256 = await sha256File(runtimePath);
  if (
    typeof manifest?.buildId !== "string"
    || !/^[A-Za-z0-9._:-]{8,160}$/u.test(manifest.buildId)
    || typeof manifest?.version !== "string"
    || !/^\d+\.\d+\.\d+$/u.test(manifest.version)
    || manifest.sha256 !== runtimeSha256
  ) {
    throw new Error("打包 Runtime manifest 与二进制身份不一致");
  }
  return {
    buildId: manifest.buildId,
    sha256: runtimeSha256,
    version: manifest.version
  };
}


function collectDiagnostics(child, secrets) {
  const maximumCharacters = 16 * 1024;
  let content = "";
  const append = (chunk) => {
    content = `${content}${chunk.toString("utf8")}`.slice(-maximumCharacters);
  };
  child.stdout.on("data", append);
  child.stderr.on("data", append);
  return {
    summary() {
      let safe = content.replace(/[\r\n]+/gu, " ").trim();
      for (const secret of secrets) {
        if (secret) safe = safe.split(secret).join("[REDACTED]");
      }
      return safe.slice(-2048) || "无可用启动诊断";
    }
  };
}


function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}


main().catch((error) => {
  console.error(
    `[packaged-license-smoke] ${error instanceof Error ? error.message : String(error)}`
  );
  process.exit(1);
});
