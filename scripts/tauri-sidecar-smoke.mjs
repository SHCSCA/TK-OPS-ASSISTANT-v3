import { spawn } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import {
  mkdtemp,
  readFile,
  rm,
  stat
} from "node:fs/promises";
import http from "node:http";
import net from "node:net";
import os from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { computeRuntimeSourceSha256 } from "./runtime-sidecar-source.mjs";
import {
  createEvidenceCollector,
  readSafeMigrationFailure,
  readSafeRuntimeState
} from "./tauri-sidecar-smoke-evidence.mjs";

const scriptRoot = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(scriptRoot, "..");
const runtimeRoot = join(repoRoot, "apps", "py-runtime");
const target = join(
  repoRoot,
  "apps",
  "desktop",
  "src-tauri",
  "binaries",
  "tk-ops-runtime-x86_64-pc-windows-msvc.exe"
);
const manifestPath = join(
  repoRoot,
  "apps",
  "desktop",
  "src-tauri",
  "resources",
  "runtime",
  "tk-ops-runtime.manifest.json"
);
const targetTriple = "x86_64-pc-windows-msvc";
const runtimeReadyTimeoutMs = 90_000;
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
  requireWindowsX64();
  const manifest = await readAndVerifyArtifact();
  const version = await captureVersion();
  if (version !== manifest.version) {
    throw new Error(
      `Runtime 版本不一致：manifest=${manifest.version} binary=${version}`
    );
  }

  const dataDir = await mkdtemp(
    join(os.tmpdir(), "tk-ops-sidecar-smoke-")
  );
  const port = await reservePort();
  const token = randomBytes(32).toString("base64url");
  const wrongToken = randomBytes(32).toString("base64url");
  const expectedHost = `127.0.0.1:${port}`;
  let child;
  try {
    child = spawn(target, [], {
      cwd: dataDir,
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8",
        PYTHONUTF8: "1",
        TK_OPS_RUNTIME_ARTIFACT_BUILD_ID: manifest.buildId,
        TK_OPS_RUNTIME_DATA_DIR: dataDir,
        TK_OPS_RUNTIME_EXPECTED_HOST: expectedHost,
        TK_OPS_RUNTIME_MANAGED_SIDECAR: "1",
        TK_OPS_RUNTIME_MODE: "production",
        TK_OPS_RUNTIME_PORT: String(port),
        TK_OPS_RUNTIME_SESSION_TOKEN: token,
        TK_OPS_RUNTIME_VERSION: manifest.version
      },
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true
    });
    const evidence = createEvidenceCollector(
      child,
      [token, wrongToken]
    );
    try {
      await waitUntilReady({
        child,
        expectedHost,
        port,
        token,
        timeoutMs: runtimeReadyTimeoutMs
      });
    } catch (error) {
      const failure = await readSafeMigrationFailure(dataDir);
      const runtimeState = await readSafeRuntimeState(dataDir);
      const message = error instanceof Error
        ? error.message
        : "Runtime sidecar 未就绪";
      throw new Error(
        `${message} ${evidence.summary()}`
        + `${failure ? ` ${failure}` : ""}`
        + `${runtimeState ? ` ${runtimeState}` : ""}`
      );
    }
    await verifySecurityRejections({
      expectedHost,
      port,
      token,
      wrongToken
    });
    child.stdin.write("shutdown\n");
    child.stdin.end();
    const exit = await waitForExit(child, 15_000);
    if (exit.code !== 0) {
      throw new Error(
        `Runtime 未正常退出：code=${String(exit.code)} ${evidence.summary()}`
      );
    }
    evidence.assertComplete();
    console.log(
      `[sidecar-smoke] 通过 ${manifest.buildId}，动态端口 ${port}`
    );
  } finally {
    if (
      child
      && child.exitCode === null
      && child.signalCode === null
    ) {
      child.kill();
      await waitForExit(child, 5_000).catch(() => undefined);
    }
    await rm(dataDir, { force: true, recursive: true });
  }
}

async function readAndVerifyArtifact() {
  await requireFile(target, "Runtime sidecar 构建产物不存在");
  await requireFile(manifestPath, "Runtime sidecar manifest 不存在");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  const hash = await sha256(target);
  const sourceSha256 = await computeRuntimeSourceSha256(runtimeRoot);
  const expectedBuildId =
    `${manifest.version}-${targetTriple}-${hash.slice(0, 12).toLowerCase()}`;
  if (
    !hasExactManifestKeys(manifest)
    || manifest.apiVersion !== "v1"
    || manifest.binary !== "tk-ops-runtime.exe"
    || manifest.buildId !== expectedBuildId
    || manifest.formatVersion !== 1
    || !isManifestTimestamp(manifest.generatedAt)
    || manifest.lifecycleProtocol !== 1
    || manifest.schemaReadMin !== "0017_p0_enforce_and_cutover"
    || manifest.schemaReadMax !== "0022_p0g_production_hardening"
    || manifest.target !== targetTriple
    || manifest.sha256 !== hash
    || manifest.sourceSha256 !== sourceSha256
  ) {
    throw new Error("Runtime sidecar manifest 或 SHA-256 校验失败");
  }
  return manifest;
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

function captureVersion() {
  return new Promise((resolveCapture, rejectCapture) => {
    const child = spawn(target, ["--version"], {
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
    child.once("error", rejectCapture);
    child.once("exit", (code) => {
      if (code === 0) {
        resolveCapture(stdout.trim());
      } else {
        rejectCapture(
          new Error(`读取 Runtime 版本失败：${stderr.trim()}`)
        );
      }
    });
  });
}

async function waitUntilReady({
  child,
  expectedHost,
  port,
  token,
  timeoutMs
}) {
  const deadline = Date.now() + timeoutMs;
  let lastStatus = null;
  let lastErrorCode = "";
  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new Error(`Runtime 就绪前退出：${child.exitCode}`);
    }
    try {
      const response = await requestBootstrap({
        expectedHost,
        port,
        token
      });
      const payload = JSON.parse(response.body);
      if (payload?.ok === true) {
        return;
      }
      const errorCode = /^[A-Z0-9._-]{1,96}$/u.test(
        payload?.error_code
      )
        ? payload.error_code
        : "RUNTIME_READINESS_REJECTED";
      lastStatus = response.statusCode;
      lastErrorCode = errorCode;
    } catch {
      // 启动轮询期间连接失败属于预期状态。
    }
    await delay(200);
  }
  throw new Error(
    `Runtime sidecar 在 ${Math.ceil(timeoutMs / 1000)} 秒内未就绪`
    + `${lastStatus === null ? "" : ` lastStatus=${lastStatus}`}`
    + `${lastErrorCode ? ` lastErrorCode=${lastErrorCode}` : ""}`
  );
}

async function verifySecurityRejections({
  expectedHost,
  port,
  token,
  wrongToken
}) {
  const wrongTokenResponse = await requestBootstrap({
    expectedHost,
    port,
    token: wrongToken
  });
  assertRejectedResponse({
    expectedErrorCode: "RUNTIME_SESSION_INVALID",
    expectedStatus: 401,
    response: wrongTokenResponse,
    secrets: [token, wrongToken]
  });

  const wrongHostResponse = await requestBootstrap({
    expectedHost: `localhost:${port}`,
    port,
    token
  });
  assertRejectedResponse({
    expectedErrorCode: "RUNTIME_HOST_INVALID",
    expectedStatus: 400,
    response: wrongHostResponse,
    secrets: [token, wrongToken]
  });
}

function assertRejectedResponse({
  expectedErrorCode,
  expectedStatus,
  response,
  secrets
}) {
  const serializedHeaders = JSON.stringify(response.headers);
  if (
    secrets.some((secret) => (
      response.body.includes(secret)
      || serializedHeaders.includes(secret)
    ))
  ) {
    throw new Error("Runtime 拒绝响应泄露了会话令牌");
  }
  let payload;
  try {
    payload = JSON.parse(response.body);
  } catch {
    throw new Error("Runtime 拒绝响应不是有效 JSON");
  }
  if (
    response.statusCode !== expectedStatus
    || payload?.ok !== false
    || payload?.error_code !== expectedErrorCode
  ) {
    throw new Error(
      `Runtime 安全拒绝不符合契约：status=${response.statusCode}`
    );
  }
}

function requestBootstrap({ expectedHost, port, token }) {
  return new Promise((resolveRequest, rejectRequest) => {
    const request = http.request(
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Host: expectedHost
        },
        host: "127.0.0.1",
        method: "GET",
        path: "/api/v1/bootstrap/status",
        port,
        timeout: 2_000
      },
      (response) => {
        const chunks = [];
        let bodyBytes = 0;
        let oversized = false;
        response.on("data", (chunk) => {
          bodyBytes += chunk.length;
          if (bodyBytes > 1_048_576) {
            oversized = true;
            return;
          }
          chunks.push(chunk);
        });
        response.once("end", () => {
          if (oversized) {
            rejectRequest(new Error("Runtime 健康检查响应超出上限"));
            return;
          }
          resolveRequest({
            body: Buffer.concat(chunks).toString("utf8"),
            headers: response.headers,
            statusCode: response.statusCode
          });
        });
      }
    );
    request.once("error", rejectRequest);
    request.once("timeout", () => {
      request.destroy(new Error("Runtime 健康检查超时"));
    });
    request.end();
  });
}

function reservePort() {
  return new Promise((resolvePort, rejectPort) => {
    const server = net.createServer();
    server.once("error", rejectPort);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        server.close();
        rejectPort(new Error("无法分配 Runtime 动态端口"));
        return;
      }
      server.close((error) => {
        if (error) {
          rejectPort(error);
        } else {
          resolvePort(address.port);
        }
      });
    });
  });
}

function waitForExit(child, timeoutMs) {
  if (
    (child.exitCode !== null || child.signalCode !== null)
    && child.stdout.readableEnded
    && child.stderr.readableEnded
  ) {
    return Promise.resolve({
      code: child.exitCode,
      signal: child.signalCode
    });
  }
  return new Promise((resolveExit, rejectExit) => {
    const timer = setTimeout(() => {
      rejectExit(new Error("等待 Runtime 退出超时"));
    }, timeoutMs);
    child.once("close", (code, signal) => {
      clearTimeout(timer);
      resolveExit({ code, signal });
    });
  });
}

function requireWindowsX64() {
  if (process.platform !== "win32" || process.arch !== "x64") {
    throw new Error("sidecar smoke 当前只支持 Windows x64");
  }
}

async function requireFile(path, message) {
  try {
    if ((await stat(path)).isFile()) {
      return;
    }
  } catch {
    // 统一映射为稳定的制品缺失错误。
  }
  throw new Error(message);
}

async function sha256(path) {
  const content = await readFile(path);
  return createHash("sha256").update(content).digest("hex").toUpperCase();
}

function delay(milliseconds) {
  return new Promise((resolveDelay) => {
    setTimeout(resolveDelay, milliseconds);
  });
}

main().catch((error) => {
  console.error(
    `[sidecar-smoke] ${error instanceof Error ? error.message : String(error)}`
  );
  process.exit(1);
});
