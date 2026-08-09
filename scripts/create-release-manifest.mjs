import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  mkdirSync,
  readFileSync,
  renameSync,
  statSync,
  writeFileSync
} from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { collectSourceSnapshot } from "./release-source-snapshot.mjs";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const inputFiles = {
  packageLockSha256: "apps/desktop/package-lock.json",
  cargoLockSha256: "apps/desktop/src-tauri/Cargo.lock",
  pyprojectSha256: "apps/py-runtime/pyproject.toml",
  tauriConfigSha256: "apps/desktop/src-tauri/tauri.conf.json",
  runtimePublicKeySha256: "apps/py-runtime/resources/license-public.pem"
};

try {
  const options = parseArgs(process.argv.slice(2));
  const rootPackage = readJson(path.join(repoRoot, "package.json"));
  const sourceSnapshot = collectSourceSnapshot(repoRoot);
  if (options.channel === "production" && sourceSnapshot.dirty) {
    throw new Error("production manifest 只允许从干净工作树生成。");
  }

  const manifest = {
    schemaVersion: 2,
    product: "TK-OPS",
    version: rootPackage.version,
    channel: options.channel,
    platform: "windows",
    architecture: "x86_64",
    git: {
      ...sourceSnapshot,
      branch: runGit(["branch", "--show-current"]).trim() || "detached",
    },
    inputs: Object.fromEntries(
      Object.entries(inputFiles).map(([key, relativePath]) => [
        key,
        sha256File(resolveRepoFile(relativePath))
      ])
    ),
    tests: options.testEvidence.map(readTestEvidence),
    artifacts: options.artifacts.map(readArtifact),
    builtAtUtc: new Date().toISOString()
  };

  if (
    options.channel === "production"
    && (manifest.tests.length === 0 || manifest.artifacts.length === 0)
  ) {
    throw new Error("production manifest 必须包含测试证据和制品。" );
  }

  const outputPath = resolveRepoFile(options.output);
  mkdirSync(path.dirname(outputPath), { recursive: true });
  const temporaryPath = `${outputPath}.tmp-${process.pid}`;
  writeFileSync(temporaryPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  renameSync(temporaryPath, outputPath);
  console.log(
    `[release-manifest] 已生成：${normalize(path.relative(repoRoot, outputPath))} `
    + `channel=${manifest.channel} dirty=${manifest.git.dirty} `
    + `tests=${manifest.tests.length} artifacts=${manifest.artifacts.length}`
  );
} catch (error) {
  console.error(
    `[release-manifest] 生成失败：${error instanceof Error ? error.message : "未知错误"}`
  );
  process.exitCode = 1;
}

function parseArgs(args) {
  const channel = readSingle(args, "--channel") || "test";
  if (!new Set(["test", "production"]).has(channel)) {
    throw new Error("--channel 只允许 test 或 production。");
  }
  const rootPackage = readJson(path.join(repoRoot, "package.json"));
  return {
    channel,
    output: readSingle(args, "--output")
      || `dist/releases/${rootPackage.version}/windows-x86_64/release-manifest.json`,
    artifacts: readMany(args, "--artifact").map((value) => {
      const separator = value.indexOf("=");
      if (separator <= 0 || separator === value.length - 1) {
        throw new Error("--artifact 必须使用 kind=relative/path 格式。");
      }
      return {
        kind: value.slice(0, separator),
        path: value.slice(separator + 1)
      };
    }),
    testEvidence: readMany(args, "--test-evidence")
  };
}

function readTestEvidence(relativePath) {
  const fullPath = resolveRepoFile(relativePath);
  const evidence = readJson(fullPath);
  const required = ["id", "command", "exitCode", "startedAt", "completedAt"];
  if (required.some((key) => !(key in evidence))) {
    throw new Error(`测试证据字段不完整：${relativePath}`);
  }
  if (evidence.exitCode !== 0) {
    throw new Error(`测试证据未通过：${evidence.id}`);
  }
  return {
    id: String(evidence.id),
    command: String(evidence.command),
    exitCode: 0,
    tests: Number.isInteger(evidence.tests) ? evidence.tests : null,
    startedAt: String(evidence.startedAt),
    completedAt: String(evidence.completedAt),
    evidencePath: normalize(path.relative(repoRoot, fullPath)),
    evidenceSha256: sha256File(fullPath),
    artifactBindings: normalizeArtifactBindings(evidence)
  };
}

function normalizeArtifactBindings(evidence) {
  const explicit = evidence.artifactBindings;
  if (explicit && typeof explicit === "object" && !Array.isArray(explicit)) {
    return Object.fromEntries(
      Object.entries(explicit).map(([kind, digest]) => [kind, String(digest)])
    );
  }
  const aliases = {
    desktop: evidence.desktopSha256,
    sidecar: evidence.runtimeSha256 ?? evidence.sidecarSha256,
    installer: evidence.installerSha256,
    portable: evidence.portableSha256
  };
  return Object.fromEntries(
    Object.entries(aliases)
      .filter(([, digest]) => typeof digest === "string" && digest.length > 0)
  );
}

function readArtifact(entry) {
  if (!/^[a-z][a-z0-9._-]{1,63}$/u.test(entry.kind)) {
    throw new Error(`制品 kind 不合法：${entry.kind}`);
  }
  const fullPath = resolveRepoFile(entry.path);
  const stat = statSync(fullPath);
  if (!stat.isFile() || stat.size <= 0) {
    throw new Error(`制品不存在或为空：${entry.path}`);
  }
  return {
    kind: entry.kind,
    path: normalize(path.relative(repoRoot, fullPath)),
    size: stat.size,
    sha256: sha256File(fullPath)
  };
}

function resolveRepoFile(value) {
  const resolved = path.resolve(repoRoot, value);
  const prefix = `${repoRoot}${path.sep}`;
  if (resolved !== repoRoot && !resolved.startsWith(prefix)) {
    throw new Error(`路径越过仓库边界：${value}`);
  }
  return resolved;
}

function runGit(args) {
  return execFileSync("git", args, {
    cwd: repoRoot,
    encoding: "utf8",
    windowsHide: true
  });
}

function readSingle(args, key) {
  const values = readMany(args, key);
  if (values.length > 1) throw new Error(`${key} 只能提供一次。`);
  return values[0];
}

function readMany(args, key) {
  const values = [];
  for (let index = 0; index < args.length; index += 1) {
    if (args[index] !== key) continue;
    const value = args[index + 1];
    if (!value || value.startsWith("--")) {
      throw new Error(`${key} 缺少值。`);
    }
    values.push(value);
    index += 1;
  }
  return values;
}

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8").replace(/^\uFEFF/u, ""));
}

function sha256File(filePath) {
  return sha256(readFileSync(filePath));
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex").toUpperCase();
}

function normalize(value) {
  return value.replaceAll("\\", "/");
}
